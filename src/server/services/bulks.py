#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing bulk."""

import csv
import typing as t

from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from uuid import UUID, uuid7

import requests

from celery import shared_task
from flask import Blueprint, current_app
from pydantic import ValidationError
from sqlalchemy import select

from server.clients import bulks, groups, users
from server.db.history import Files, UploadHistory
from server.db.utils import db
from server.entities.bulk import (
    CheckResult,
    RepositoryMember,
    ResultSummary,
    ValidateSummary,
)
from server.entities.bulk_request import BulkOperation
from server.entities.map_error import MapError
from server.entities.user_detail import UserDetail
from server.exc import (
    CredentialsError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.services.token import get_access_token, get_client_secret
from server.services.utils import search_queries


if t.TYPE_CHECKING:
    from server.entities.map_group import MapGroup
    from server.entities.search_request import SearchResponse

bp = Blueprint("bulk", __name__)


def save_file(temporary_id: UUID) -> UUID:
    """Save the temporary file as a permanent file for bulk operation.

    Args:
        temporary_id (UUID): The ID of the temporary file.

    Returns:
        UUID: The ID of the saved permanent file.

    Raises:
        ResourceNotFound: If the temporary file does not exist.
        ResourceInvalid: If the file format is invalid.
    """
    try:
        file_path = (
            db.session.query(Files.file_path).filter(Files.id == temporary_id).scalar()
        )
        repository_id = (
            db.session
            .query(Files.file_content)
            .filter(Files.id == temporary_id)
            .scalar()["repositories"][0]["id"]
        )
    except Exception as e:
        current_app.logger.error("Failed to retrieve temporary file: %s", e)
        raise

    if not file_path.exists():
        raise ResourceNotFound("")
    if file_path.suffix not in {".csv", ".tsv", ".xlsx"}:
        raise ResourceInvalid("")

    file_id = uuid7()
    target_dir = Path(f"/data/files/{datetime.now(UTC).strftime('%Y/%m')}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_path.name
    file_path.rename(target_path)
    file_record = Files(
        id=file_id,  # pyright: ignore[reportCallIssue]
        file_path=str(target_path),  # pyright: ignore[reportCallIssue]
        file_content={"repositories": repository_id},  # pyright: ignore[reportCallIssue]
    )
    db.session.add(file_record)
    db.session.commit()
    return file_id


@shared_task
def validate_upload_data(temporary_id: UUID):
    file_row = db.session.execute(
        select(Files.file_path, Files.file_content)
        .where(Files.id == temporary_id)
        .limit(1)
    ).one_or_none()
    if not file_row:
        raise ValueError

    file_path, file_content = file_row
    if not isinstance(file_content, dict):
        raise TypeError
    repository_id = str(file_content["repositories"][0]["id"])

    repository_member: RepositoryMember = get_repository_member(repository_id)
    update_users: list[UserDetail] = read_file(file_path)

    check_results: list[CheckResult] = []
    update_list: list[UserDetail] = []

    for u in update_users:
        user_group_ids = [g.id for g in u.groups or []]
        if user_group_ids not in repository_member.groups:
            check_results.append(
                CheckResult(
                    user_id=u.id,
                    eppn=u.eppns or [],
                    user_name=u.user_name,
                    groups=user_group_ids,
                    status="error",
                    code="E001",
                    bulk_operation=None,
                )
            )
            continue

        if u.id not in repository_member.users:
            check_results.append(
                CheckResult(
                    user_id=u.id,
                    eppn=u.eppns or [],
                    user_name=u.user_name,
                    groups=user_group_ids,
                    status="create",
                    code=None,
                    bulk_operation=BulkOperation(
                        method="POST", path="User", data=u.to_map_user()
                    ),
                )
            )

        else:
            update_list.append(u)
    access_token = get_access_token()
    client_secret = get_client_secret()
    query = search_queries.build_search_query(
        search_queries.make_criteria_object("users", i=[u.id for u in update_list])
    )
    users.search(query=query, access_token=access_token, client_secret=client_secret)
    history_id = uuid7()
    history_record = UploadHistory(
        id=history_id,  # pyright: ignore[reportCallIssue]
        file_id=temporary_id,  # pyright: ignore[reportCallIssue]
        results=check_results,  # pyright: ignore[reportCallIssue]
    )
    db.session.add(history_record)
    db.session.commit()

    return history_id


def read_file(file_path: str) -> list[UserDetail]:
    """Read user data from the specified file and return a list of UserDetail instances.

    Args:
        file_path (str): The path to the file containing user data.

    Returns:
        list[UserDetail]: A list of UserDetail instances representing the user data.

    Raises:
        ResourceNotFound: If the specified file does not exist.
        ResourceInvalid: If the file format is unsupported.
    """
    p = Path(file_path)
    if not p.exists():
        raise ResourceNotFound(f"{p}: File not found.")
    if p.suffix.lower() not in {".csv", ".tsv", ".xlsx"}:
        raise ResourceInvalid(f"{p.suffix}: Unsupported file format.")
    user_map: dict[str, dict] = {}
    if p.suffix.lower() in {".csv", ".tsv"}:
        with p.open(encoding="utf-8-sig") as f:
            data = csv.DictReader(
                f, delimiter="," if p.suffix.lower() == ".csv" else "\t"
            )

            for row in data:
                user_id: str = row.get("id") or ""
                group_id = row.get("groups[].id")
                group_name = row.get("groups[].name")
                eppn = row.get("edu_person_principal_names[]")
                emails = row.get("emails[]")
                if user_id not in user_map:
                    user_map[user_id] = {
                        "id": user_id,
                        "eppn": [],
                        "user_name": row.get("user_name"),
                        "emails": [],
                        "groups": [],
                    }

                if group_id and not any(
                    g["id"] == group_id for g in user_map[user_id]["groups"]
                ):
                    user_map[user_id]["groups"].append({
                        "id": group_id,
                        "name": group_name,
                    })
                if eppn and not any(
                    e["eduPersonPrincipalNames"] == eppn
                    for e in user_map[user_id]["eppn"]
                ):
                    user_map[user_id]["eppn"].append({"eduPersonPrincipalNames": eppn})
                if emails and not any(
                    em["value"] == emails for em in user_map[user_id]["emails"]
                ):
                    user_map[user_id]["emails"].append({"value": emails})

    return [UserDetail(**user_data) for user_data in user_map.values()]


def get_validate_result(history_id: UUID) -> ValidateSummary:
    """Get the validation result summary for the specified upload history ID.

    Args:
        history_id (UUID): The ID of the upload history.

    Returns:
        ValidateSummary: The summary of the validation result.
    """
    data = db.session.get(UploadHistory, history_id)

    if data is None or data.results is None:
        return ValidateSummary(check_result=[])

    check_result_list = data.results.get("results", [])

    return ValidateSummary(check_result=check_result_list)


@shared_task
def update_users(task_id: str, temporary_id: UUID, delete_users: list[str]) -> UUID:
    history_id = current_app.extensions["celery"].AsyncResult(task_id).result
    history = db.session.get(UploadHistory, history_id)
    """"""
    if not history:
        raise ValueError(f"History not found: {history_id}")

    check_results = history.results.get("results", [])
    bulk_ops: list[BulkOperation] = [
        item.get("bulkOperation") for item in check_results if "bulkOperation" in item
    ]

    for user_id in delete_users:
        remove_op = BulkOperation(method="DELETE", path=f"User/{user_id}")
        bulk_ops.append(remove_op)

    file_id = save_file(temporary_id)

    history.file_id = file_id
    history.status = "P"
    history.timestamp = datetime.now(UTC)
    db.session.commit()

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result = bulks.post(
            bulk_ops, access_token=access_token, client_secret=client_secret
        )
    except (
        requests.RequestException,
        ValidationError,
        OAuthTokenError,
        UnexpectedResponseError,
    ) as exc:
        history.status = "F"
        db.session.commit()
        current_app.logger.error(f"Bulk update failed: {exc!s}")
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)
    has_error = False
    for i, operation in enumerate(result.operations):
        status_code = int(operation.status) if operation.status else 200
        if status_code >= HTTPStatus.BAD_REQUEST:
            has_error = True
            if i < len(check_results):
                check_results[i]["status"] = "error"

    if has_error:
        history.results["results"] = check_results
        history.status = "F"
    else:
        history.status = "S"

    history.end_timestamp = datetime.now(UTC)
    db.session.commit()

    return history_id


def get_result(
    history_id: UUID, filters: list[str], size: int, offset: int
) -> ResultSummary:
    """Get the bulk operation result summary with filtering and pagination.

    Args:
        history_id (UUID): The ID of the upload history.
        filters (list[str]): The list of status filters to apply.
        size (int): The number of items to return.
        offset (int): The offset for pagination.

    Returns:
        ResultSummary: The summary of the bulk operation result.

    Raises:
        ResourceNotFound: If the upload history with the given ID does not exist.
    """
    data = (
        db.session
        .query(UploadHistory, Files.file_path)
        .join(Files, UploadHistory.file_id == Files.id)
        .filter(UploadHistory.id == history_id)
        .first()
    )

    if not data:
        raise ResourceNotFound(history_id)

    history, file_path = data

    all_items = history.results.get("items", []) if history.results else []

    filtered_items = [item for item in all_items if item.get("status") in filters]

    def count_status(action_type: str) -> int:
        return sum(1 for item in all_items if item.get("action") == action_type)

    return ResultSummary(
        upload_result=filtered_items[offset : offset + size],
        create=count_status("create"),
        update=count_status("update"),
        delete=count_status("delete"),
        skip=count_status("skip"),
        error=sum(1 for item in all_items if item.get("status") == "error"),
        file_id=history.file_id,
        file_name=Path(file_path).name,
        operator=history.operator_name,
        start_timestamp=history.timestamp,
        end_timestamp=history.end_timestamp,
    )


@shared_task
def delete_temporary_file(temporary_id: UUID) -> None:
    """Delete the temporary file with the given ID."""
    file_path = (
        db.session.query(Files.file_path).filter(Files.id == temporary_id).scalar()
    )
    if file_path and Path(file_path).exists():
        file_path.unlink()
    db.session.delete(Files(id=temporary_id))  # pyright: ignore[reportCallIssue]
    db.session.commit()


def get_repository_member(repository_id: str) -> RepositoryMember:
    """Get the members of the specified repository from mAP Core API.

    Args:
        repository_id (str): The ID of the repository.

    Returns:
        RepositoryMember: The members of the repository.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        UnexpectedResponseError:
            If an unexpected error occurs while communicating with mAP Core API.
        CredentialsError: If there is an issue with client credentials.
        ResourceInvalid: If the repository resource is invalid.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        query = search_queries.build_search_query(
            search_queries.make_criteria_object("groups", r=[repository_id])
        )
        result: SearchResponse[MapGroup] = groups.search(
            query=query, access_token=access_token, client_secret=client_secret
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    group_ids = {g.id for g in result.resources}
    user_ids = {
        m.value
        for g in result.resources
        for m in g.members  # pyright: ignore[reportOptionalIterable]
        if m.type == "User"
    }
    return RepositoryMember(groups=group_ids, users=user_ids)


def get_not_included_users(history_id: UUID) -> list[UserDetail]:
    """Get the list of users not included in the bulk operation.

    Args:
        history_id (UUID): The ID of the upload history.

    Returns:
        list[UserDetail]: The list of users not included in the bulk operation.
    """
    history = db.session.get(UploadHistory, history_id)
    if not history or not history.results:
        return []

    not_included_data = history.results.get("notIncludedUsers", [])
    return [UserDetail(**user_data) for user_data in not_included_data]
