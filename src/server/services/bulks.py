#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing bulk."""

import csv
import re
import typing as t

from datetime import UTC, datetime
from http import HTTPStatus
from itertools import zip_longest
from pathlib import Path
from uuid import UUID

import openpyxl
import requests

from celery import shared_task
from flask import current_app
from pydantic import ValidationError

from server.clients import bulks
from server.config import config
from server.const import ValidationEntity
from server.entities.bulk import (
    CheckResult,
    HistorySummary,
    RepositoryMember,
    ResultSummary,
    UserAggregated,
    ValidateSummary,
)
from server.entities.bulk_request import BulkOperation
from server.entities.map_error import MapError
from server.entities.map_user import EPPN, Email, Group, MapUser
from server.entities.patch_request import RemoveOperation
from server.entities.summaries import GroupSummary
from server.entities.user_detail import UserDetail
from server.exc import (
    ImmutableError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.services import groups, history_table, users, utils
from server.services.token import get_access_token, get_client_secret


@shared_task()
def validate_upload_data(
    operator_id: str, operator_name: str, temp_file_id: UUID
) -> UUID:
    """Validate the uploaded file data for bulk operation.

    Args:
        operator_id (str): The ID of the operator performing the upload.
        operator_name (str): The name of the operator performing the upload.
        temp_file_id (UUID): The ID of the temporary file.

    Returns:
        UUID: The ID of the upload history record.
    """
    record = history_table.get_file_by_id(temp_file_id)
    file_path = record.file_path
    repository_id = record.file_content["repositories"][0]["id"]
    repository_member = get_repository_member(repository_id)

    file_users: list[UserDetail] = build_user_from_file(file_path).root
    file_users_id = {u.id for u in file_users}
    missing_users = _get_missing_users(repository_member, file_users_id)
    repo_user_by_id = _get_repo_user_by_id(repository_member, file_users_id)

    check_results, summary = _build_check_results(
        file_users, repository_member, repo_user_by_id
    )

    results = ValidateSummary(
        results=check_results, summary=summary, missing_user=missing_users
    )
    return history_table.create_upload(
        operator_id=operator_id,
        operator_name=operator_name,
        file_id=temp_file_id,
        results=results.model_dump(mode="json"),
    )


def _get_missing_users(
    repository_member: RepositoryMember, file_users_id: set[str]
) -> list[UserDetail]:
    missing_user_ids = list(repository_member.users - file_users_id)
    user_list = users.search(
        utils.make_criteria_object("users", i=missing_user_ids), raw=True
    ).resources
    return [UserDetail.from_map_user(u) for u in user_list]


def _get_repo_user_by_id(
    repository_member: RepositoryMember, file_users_id: set[str]
) -> dict[str, UserDetail]:
    update_users_ids = list(repository_member.users & file_users_id)
    user_list = users.search(
        utils.make_criteria_object("users", i=update_users_ids), raw=True
    ).resources
    repo_users = [UserDetail.from_map_user(u) for u in user_list]
    return {repo_user.id: repo_user for repo_user in repo_users if repo_user.id}


def _build_check_results(
    file_users: list[UserDetail],
    repository_member: RepositoryMember,
    repo_user_by_id: dict[str, UserDetail],
) -> tuple[list[CheckResult], HistorySummary]:
    count_create = 0
    count_update = 0
    count_delete = 0
    count_skip = 0
    count_error = 0
    check_results: list[CheckResult] = []
    for u in file_users:
        code = None
        user_group_ids = {g.id for g in u.groups} if u.groups else set()

        if not user_group_ids.issubset(repository_member.groups):
            code = "E001"
            check_results.append(
                CheckResult(
                    id=u.id,
                    eppn=u.eppns or [],
                    user_name=u.user_name,
                    email=u.emails or [],
                    groups=user_group_ids,
                    status="error",
                    code=code,
                )
            )
            count_error += 1
            continue

        if not check_value(u):
            code = "E002"
            check_results.append(
                CheckResult(
                    id=u.id,
                    eppn=u.eppns or [],
                    user_name=u.user_name,
                    groups=user_group_ids,
                    email=u.emails or [],
                    status="error",
                    code=code,
                )
            )
            count_error += 1
            continue

        repo_user = repo_user_by_id.get(u.id)
        if repo_user is None:
            check_results.append(
                CheckResult(
                    id=u.id,
                    eppn=u.eppns or [],
                    user_name=u.user_name,
                    groups=user_group_ids,
                    email=u.emails or [],
                    status="create",
                    code=code,
                )
            )
            count_create += 1
            continue

        repo_group_ids = {g.id for g in repo_user.groups} if repo_user.groups else set()
        if repo_group_ids != user_group_ids:
            status = "update"
            count_update += 1
        else:
            status = "skip"
            count_skip += 1
        code = is_immutable_attribute(repo_user, u)
        check_results.append(
            CheckResult(
                id=u.id,
                eppn=repo_user.eppns or [],
                user_name=repo_user.user_name,
                email=u.emails or [],
                groups=user_group_ids,
                status=status,
                code=code,
            )
        )
    summary = HistorySummary(
        create=count_create,
        update=count_update,
        delete=count_delete,
        skip=count_skip,
        error=count_error,
    )
    return check_results, summary


def get_repository_member(repository_id: str) -> RepositoryMember:
    """Get the members of the specified repository from mAP Core API.

    Args:
        repository_id (str): The ID of the repository.

    Returns:
        RepositoryMember: The members of the repository.
    """
    result = groups.search(
        utils.make_criteria_object("groups", r=[repository_id]), raw=True
    ).resources
    group_ids = {g.id for g in result}
    user_ids = {
        m.value for g in result if g.members for m in g.members if m.type == "User"
    }

    return RepositoryMember(groups=group_ids, users=user_ids)


def read_file(file_path: str) -> t.Generator:
    """Read a user data file and return a list of `UserDetail` instances.

    Args:
        file_path (str): Path to the inpatch file containing user data.


    Raises:
        ResourceNotFound: If the file does not exist.
        ResourceInvalid : If the format is unsupported or parsing fails.
    """
    path = Path(file_path)
    if not path.exists():
        error = f"{path}: File not found."
        raise ResourceNotFound(error)

    iterator = None
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "," if suffix == ".csv" else "\t"
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            iterator = csv.reader(f, delimiter=delimiter)
            yield iterator
    elif suffix == ".xlsx":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if ws:
            iterator = ws.iter_rows(values_only=True)
    if iterator is None:
        error = f"{path.suffix}: Unsupported file format."
        raise ResourceInvalid(error)

    yield iterator


def build_user_from_file(file_path: str) -> UserAggregated:
    """Build UserAggregated from a user data file.

    Args:
        file_path (str): Path to the input file containing user data.

    Returns:
        UserAggregated: The aggregated user details built from the file.

    Raises:
        ResourceNotFound: If the file does not exist.
    """
    try:
        gen = read_file(file_path)
    except (ResourceInvalid, ResourceNotFound) as e:
        current_app.logger.error(e)
        raise ResourceNotFound from e
    it = next(gen)
    header = [("" if h is None else str(h).strip()) for h in next(it)]
    _ = next(it)
    id_idx = header.index("id")
    idx_of = {name: i for i, name in enumerate(header)}

    data = {}
    for row in it:
        if row is None:
            continue
        r = list(row)

        rid = r[id_idx]

        bucket = data.setdefault(rid, {})
        for col, j in idx_of.items():
            if col != "id":
                bucket.setdefault(col, []).append(r[j])
    return build_user_detail_from_dict(data)


def build_user_detail_from_dict(
    data: dict[str, dict[str, list[str]]],
) -> UserAggregated:
    """Build UserAggregated from a dictionary of user data.

    Args:
        data (dict[str, dict[str, list[str]]]):
            A dictionary where the key is the user ID and the value is another
            dictionary containing user attributes.

    Returns:
        UserAggregated:
            The aggregated user details built from the input dictionary.
    """
    users: list[UserDetail] = []

    for raw_uid, columns in data.items():
        uid = str(raw_uid).strip() if raw_uid else ""
        if not uid:
            continue

        user_name: str = columns.get("user_name")[0]
        preferred_language: str = columns.get("preferred_language")[0]

        eppns: set[str] = set(columns.get("edu_person_principal_names[]"))
        emails: set[str] = set(columns.get("emails[]"))

        gid_list: list[str] = columns.get("groups[].id")
        gname_list: list[str] = columns.get("groups[].name")
        groups: list[GroupSummary] = []
        seen = set()
        for gid, gname in zip_longest(gid_list, gname_list, fillvalue=None):
            if not gid or gid in seen:
                continue
            seen.add(gid)
            groups.append(
                GroupSummary.model_construct(
                    id=gid,
                    display_name=gname,
                )
            )

        users.append(
            UserDetail.model_construct(
                id=uid,
                eppns=eppns,
                user_name=user_name,
                emails=emails,
                preferred_language=preferred_language,
                groups=groups,
            )
        )

    return UserAggregated(root=users)


def check_value(user: UserDetail) -> bool:
    """Check if the user detail has valid values.

    Args:
        user (UserDetail): The user detail to be checked.

    Returns:
        bool: True if the user detail has valid values, False otherwise.
    """
    if not user.id:
        return False
    if not re.compile(r"^[A-Za-z0-9]{1,50}$").fullmatch(user.id):
        return False
    return len(user.user_name) <= ValidationEntity.USER_NAME_MAX_LENGTH


def is_immutable_attribute(
    original: UserDetail, update_user: UserDetail
) -> (
    t.Literal["emails", "eppns", "preferred_language", "last_modified", "created"]
    | None
):
    """Verify whether the immutable attribute is indeed immutable.

    Args:
        original (UserDetail): The original user detail.
        update_user (UserDetail): The updated user detail.

    Returns:
        str | None: The name of the immutable attribute if found, None otherwise.

    Raises:
        ImmutableError: If the user ID is attempted to be changed.
    """
    if original.id != update_user.id:
        error = "User ID is immutable."
        raise ImmutableError(error)
    if original.emails != update_user.emails:
        return "emails"
    if original.eppns != update_user.eppns:
        return "eppns"
    if original.preferred_language != update_user.preferred_language:
        return "preferred_language"
    if original.last_modified != update_user.last_modified:
        return "last_modified"
    if original.created != update_user.created:
        return "created"
    return None


def get_validate_result(
    history_id: UUID, status_filter: list[str], offset: int, size: int
) -> ValidateSummary:
    """Get the validation result summary for the specified upload history ID.

    Args:
        history_id (UUID): The ID of the upload history.
        status_filter (list[str]): Filter for Displayed Status
        offset (int): the offset for pagination
        size (int): page size

    Returns:
        ValidateSummary: The summary of the validation result.
    """
    results = history_table.get_paginated_upload_results(
        history_id, offset, size, status_filter
    )
    current_app.logger.info("results %s", results)
    check_results = [CheckResult.model_validate(it) for it in results]

    summary = history_table.get_upload_results(history_id, "summary")
    missing_user = history_table.get_upload_results(history_id, "missingUser")
    current_app.logger.info("results: %s", check_results)
    current_app.logger.info("summary: %s", summary)
    current_app.logger.info("missingUser: %s", missing_user)
    return ValidateSummary.model_validate({
        "results": check_results,
        "summary": summary,
        "missingUser": missing_user or [],
    })


def get_missing_users(history_id: UUID) -> list[UserDetail]:
    """Get the list of users not included in the bulk operation.

    Args:
        history_id (UUID): The ID of the upload history.

    Returns:
        list[UserDetail]: The list of users not included in the bulk operation.
    """
    missing_user = history_table.get_upload_results(history_id, "missingUser")
    if not isinstance(missing_user, list):
        return []

    return [UserDetail.model_validate(user_data) for user_data in missing_user]


@shared_task
def update_users(
    task_id: str, temp_file_id: UUID, delete_users: list[UserDetail]
) -> UUID:
    """Perform bulk update of users based on the validation results.

    Args:
        task_id (str): The ID of the validation task.
        temp_file_id (UUID): The ID of the temporary file.
        delete_users (list[UserDetail]): The list of user detail to be deleted.

    Returns:
        UUID: The ID of the upload history record.

    Raises:
        ResourceNotFound: If the upload history does not exist.
        requests.RequestException: If there is an error communicating with mAP Core API.
        ValidationError: If there is an error parsing the response from mAP Core API.
        OAuthTokenError: If there is an issue with the access token.
        UnexpectedResponseError: If there is an unexpected response from mAP Core API.
        ResourceInvalid: If there is an invalid resource error from mAP Core API.
        ValueError:
    """
    history_id = current_app.extensions["celery"].AsyncResult(task_id).result
    upload_data = history_table.get_upload_by_id(history_id)
    if not upload_data:
        error = f"History not found: {history_id}"
        raise ResourceNotFound(error)
    repository_id = upload_data.file.file_content["repositories"][0]["id"]
    check_results: list[CheckResult] = upload_data.results.get("results", [])
    summary = upload_data.results.get("summary", {})
    if summary.get("error") > 0:
        raise ValueError
    bulk_ops, count_delete = _build_bulk_operations_from_check_results(
        repository_id, check_results, delete_users
    )
    summary.update({"delete": count_delete})
    file_id = save_file(temp_file_id)
    history_table.update_upload_status(
        history_id=history_id,
        status="P",
        file_id=file_id,
        new_results={"results": check_results, "summary": summary},
    )
    history_table.delete_file_by_id(temp_file_id)
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
        history_table.update_upload_status(history_id=history_id, status="F")
        current_app.logger.error(exc)
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)
    count_error = 0
    for i, operation in enumerate(result.operations):
        if (
            operation.status
            and int(operation.status) >= HTTPStatus.BAD_REQUEST
            and i < len(check_results)
        ):
            check_results[i].status = "error"
            count_error += 1

    summary.update({"error": count_error})
    if count_error > 0:
        history_table.update_upload_status(
            history_id=history_id,
            status="F",
            new_results={"results": check_results, "summary": summary},
        )
    else:
        history_table.update_upload_status(
            history_id=history_id,
            status="S",
        )

    return history_id


def save_file(temp_file_id: UUID) -> UUID:
    """Save the temporary file as a permanent file for bulk operation.

    Args:
        temp_file_id (UUID): The ID of the temporary file.

    Returns:
        UUID: The ID of the saved permanent file.

    Raises:
        ResourceNotFound: If the temporary file does not exist.
        ResourceInvalid: If the file format is invalid.
    """
    try:
        files = history_table.get_file_by_id(temp_file_id)
        repository_id = files.file_content["repositories"][0]["id"]
    except (KeyError, AttributeError) as e:
        current_app.logger.error("Failed to retrieve temporary file: %s", temp_file_id)
        raise ResourceNotFound(str(e)) from e

    file_path = Path(files.file_path)
    if file_path.parent != Path(config.temp_file_dir):
        return files.id
    if not file_path.exists():
        error_msg = f"File not found: {file_path}"
        raise ResourceNotFound(error_msg)
    if file_path.suffix not in {".csv", ".tsv", ".xlsx"}:
        error = "not supported file format."
        raise ResourceInvalid(error)

    target_dir = Path(config.file_dir) / datetime.now(UTC).strftime("%Y/%m")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_path.name
    file_path.rename(target_path)
    return history_table.create_file(
        file_path=str(target_path),
        file_content={"repositories": [{"id": repository_id}]},
    )


def build_map_user_from_check_result(user: CheckResult) -> MapUser:
    """Build MapUser from CheckResult.

    Args:
        user (CheckResult): The check result containing user information.

    Returns:
        MapUser: The map user built from the check result.
    """
    user_emails = [Email(value=email) for email in user.email]
    user_eppns = [EPPN(value=eppn) for eppn in user.eppn]
    user_groups = [Group(value=group_id) for group_id in user.groups]
    return MapUser(
        id=user.id,
        user_name=user.user_name,
        emails=user_emails,
        edu_person_principal_names=user_eppns,
        groups=user_groups,
    )


def build_user_detail_from_check_result(user: CheckResult) -> UserDetail:
    """Build UserDetail from CheckResult.

    Args:
        user (CheckResult): The check result containing user information.

    Returns:
        UserDetail: The user detail built from the check result.
    """
    user_groups = [GroupSummary(id=group_id) for group_id in user.groups]
    return UserDetail(
        id=user.id,
        user_name=user.user_name,
        emails=user.email,
        eppns=user.eppn,
        groups=user_groups,
    )


def build_remove_user_path(user: UserDetail, repository_id: str) -> BulkOperation:
    """Remove the user from the group belong to the repository.

    Args:
        user (UserDetail):
            The user to be removed from the repository.
        repository_id (str):
            The ID of the repository from which the user will be removed.

    Returns:
        BulkOperation:
            request body representing the bulk remove operation.
    """
    user_groups = [g.id for g in user.groups] if user.groups else []
    affiliations = utils.detect_affiliations(user_groups)
    group_list = affiliations.groups

    condition = " or ".join(
        f"(value eq '{g.group_id}')"
        for g in group_list
        if g.repository_id == repository_id
    )

    path = f"groups[{condition}]"
    remove_op = RemoveOperation(path=path)
    return BulkOperation(method="PATCH", path=f"Users/{user.id}", data=remove_op)


def _build_bulk_operations_from_check_results(
    repository_id: str, check_results: list[CheckResult], delete_users: list[UserDetail]
) -> tuple[list[BulkOperation], int]:
    repository_member = get_repository_member(repository_id)

    update_users_ids = set(
        repository_member.users & {user.id for user in check_results}
    )
    repo_user_by_id = _get_repo_user_by_id(repository_member, update_users_ids)
    bulk_ops: list[BulkOperation] = []
    count_delete = 0
    for user in check_results:
        match user.status:
            case "create":
                bulk_ops.append(
                    BulkOperation(
                        method="POST",
                        path="/Users",
                        data=build_map_user_from_check_result(user),
                    )
                )
            case "update":
                original = repo_user_by_id.get(user.id)
                if not original:
                    raise ValueError
                update_user = build_user_detail_from_check_result(user)
                patch_ops = utils.build_patch_operations(original, update_user)
                for patch_op in patch_ops:
                    bulk_op = BulkOperation(
                        method="PATCH",
                        path=f"/Users/{user.id}",
                        data=patch_op,
                    )
                    bulk_ops.append(bulk_op)

    for user in delete_users:
        bulk_op = build_remove_user_path(user, repository_id)
        bulk_ops.append(bulk_op)
        check_results.append(
            CheckResult(
                id=user.id,
                eppn=user.eppns or [],
                user_name=user.user_name,
                email=user.emails or [],
                groups={g.id for g in user.groups} if user.groups else set(),
                status="delete",
                code=None,
            )
        )
        count_delete += 1
    return bulk_ops, count_delete


def get_upload_result(
    history_id: UUID, status_filter: list[str], offset: int, size: int
) -> ResultSummary:
    """Get the bulk operation result summary with filtering and pagination.

    Args:
        history_id (UUID): The ID of the upload history.
        status_filter (list[str]): The list of status filters to apply.
        size (int): The number of items to return.
        offset (int): The offset for pagination.

    Returns:
        ResultSummary: The summary of the bulk operation result.

    Raises:
        ResourceNotFound: If the upload history with the given ID does not exist.
    """
    upload = history_table.get_upload_by_id(history_id)
    if not upload:
        error = f"upload history not found: {history_id}"
        raise ResourceNotFound(error)

    raw_results: list[dict] = history_table.get_paginated_upload_results(
        history_id, offset, size, status_filter or []
    )

    summary = history_table.get_upload_results(history_id, "summary")

    payload = {
        "results": raw_results,
        "summary": summary,
        "fileId": upload.file_id,
        "fileName": Path(upload.file.file_path).name,
        "operator": upload.operator_name or upload.operator_id,
        "startTimestamp": upload.timestamp,
        "endTimestamp": upload.end_timestamp,
    }
    current_app.logger.info("payload: %s", payload)
    return ResultSummary.model_validate(payload)


@shared_task()
def delete_temporary_file(temp_id: str) -> None:
    """Delete the temporary file with the given ID.

    Args:
        temp_id(str): delete file id
    """
    temp_file_id = UUID(temp_id)
    file_path = history_table.get_file_by_id(temp_file_id).file_path
    if file_path and Path(file_path).exists():
        Path(file_path).unlink()
        history_table.delete_file_by_id(temp_file_id)
