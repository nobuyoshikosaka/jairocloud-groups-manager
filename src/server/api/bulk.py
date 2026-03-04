#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for bulk endpoints."""

from pathlib import Path
from uuid import UUID, uuid7

from flask import Blueprint, Response, current_app, send_file
from flask_login import current_user, login_required
from flask_pydantic import validate
from redis.exceptions import ConnectionError as RedisConnectionError

from server.api.helpers import roles_required
from server.api.schemas import (
    BulkBody,
    ErrorResponse,
    ExcuteRequest,
    TargetRepository,
    UploadFiles,
    UploadQuery,
)
from server.auth import is_user_logged_in
from server.config import config
from server.const import DEFAULT_SEARCH_COUNT, USER_ROLES
from server.entities.bulk import ExecuteResults, ValidateResults
from server.exc import InvalidExportError, RecordNotFound
from server.services import bulks, history_table, repositories
from server.services.utils import get_permitted_repository_ids


STATUS_MAP = {0: "create", 1: "update", 2: "delete", 3: "skip", 4: "error"}


bp = Blueprint("bulk", __name__)


@bp.post("/upload-file")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def upload_file(
    form: TargetRepository, files: UploadFiles
) -> tuple[BulkBody | ErrorResponse, int]:
    """Upload a file for bulk processing.

    Args:
        form (TargetRepository): Target repository ID for upload.
        files (UploadFiles): File to upload.

    Returns:
        BulkBody: The response containing task ID
        ErrorResponse: The response containing task ID or error message.
    """
    if repositories.get_by_id(form.repository_id) is None:
        error = f"Repository not found: {form.repository_id}"
        current_app.logger.error(error)
        return ErrorResponse(code="", message=error), 404
    if (
        not is_user_logged_in(current_user)
        or form.repository_id not in get_permitted_repository_ids()
    ):
        error = f"User does not have permission for repository: {form.repository_id}"
        current_app.logger.error(error)
        return ErrorResponse(code="", message=error), 403
    temp_id = uuid7()
    temp_dir = Path(config.STORAGE.local.temporary)
    original_filename = files.bulk_file.filename or "upload_file"
    new_filename = f"{temp_id}_{Path(original_filename).name}"
    file_path = temp_dir / new_filename
    files.bulk_file.save(str(file_path))
    file_content = {"repositories": [{"id": form.repository_id}]}
    history_table.create_file(
        file_id=temp_id, file_path=str(file_path), file_content=file_content
    )

    operator_id = current_user.map_id
    operator_name = current_user.user_name
    bulks.delete_temporary_file.apply_async((str(temp_id),), countdown=3600)
    task = bulks.validate_upload_data.apply_async(
        (operator_id, operator_name, temp_id),
        session_required=True,  # pyright: ignore[reportCallIssue]
    )
    return BulkBody(task_id=task.id, temp_file_id=temp_id), 200


@bp.get("/validate/status/<string:task_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def validate_status(task_id: str) -> tuple[BulkBody | ErrorResponse, int]:
    """Get the status of a validation task.

    Args:
        task_id (str): The ID of the validation task.

    Returns:
        BulkBody: The response containing task status
        ErrorResponse: The response containing task status or error message
    """
    try:
        res = bulks.validate_upload_data.AsyncResult(task_id)
    except RedisConnectionError:
        error = f"Failed to connect to Redis: {task_id}"
        return ErrorResponse(code="", message=error), 500
    if not res:
        error = f"Task not found: {task_id}"
        return ErrorResponse(code="", message=error), 404
    return BulkBody(status=res.state), 200


@bp.get("/validate/result/<string:task_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def validate_result(
    query: UploadQuery,
    task_id: str,
) -> tuple[ValidateResults | ErrorResponse, int]:
    """Get the result of a validation task.

    Args:
        query (UploadQuery): Query parameters for filtering results.
        task_id (str): The ID of the validation task.

    Returns:
        ValidateSummary: The response containing validation result
        ErrorResponse: The response containing validation result or error message.
    """
    try:
        res = bulks.validate_upload_data.AsyncResult(task_id)
    except RedisConnectionError:
        error = f"Failed to connect to Redis: {task_id}"
        return ErrorResponse(code="", message=error), 500
    if not res:
        error = f"Task not found: {task_id}"
        return ErrorResponse(code="", message=error), 404
    if not isinstance(res.result, UUID) or not res.successful():
        error = f"Task failed: {res.result}"
        return ErrorResponse(code="", message=error), 400
    history_id = res.result
    status_filter = [STATUS_MAP[status] for status in query.f] if query.f else []
    offset = query.p or 1
    size = query.l or DEFAULT_SEARCH_COUNT
    try:
        if not is_user_logged_in(
            current_user
        ) or not bulks.chack_permission_to_operation(history_id, current_user.map_id):
            error = f"User does not have permission for history: {history_id}"
            current_app.logger.error(error)
            return ErrorResponse(code="", message=error), 403
        result = bulks.get_validate_result(
            history_id=history_id, status_filter=status_filter, offset=offset, size=size
        )
    except RecordNotFound as exc:
        return ErrorResponse(code="", message=str(exc)), 404
    return result, 200


@bp.post("/execute")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def execute(body: ExcuteRequest) -> tuple[BulkBody | ErrorResponse, int]:
    """Execute a bulk upload.

    Args:
        body (UploadBody):
          The request body containing temporary ID, repository ID, task ID,
          and users to delete.

    Returns:
        BulkBody: The response containing task ID
        ErrorResponse: The response containing task ID or error message
    """
    try:
        history_id = history_table.get_history_by_file_id(body.temp_file_id).id
        if not is_user_logged_in(
            current_user
        ) or not bulks.chack_permission_to_operation(history_id, current_user.map_id):
            error = f"User does not have permission for history: {history_id}"
            current_app.logger.error(error)
            return ErrorResponse(code="", message=error), 403
        task = bulks.update_users.apply_async(
            kwargs={
                "history_id": history_id,
                "temp_file_id": body.temp_file_id,
                "delete_users": body.delete_users,
            },
        )
    except RecordNotFound as exc:
        return ErrorResponse(code="", message=str(exc)), 404
    return BulkBody(task_id=task.id, history_id=history_id), 200


@bp.get("/execute/status/<string:task_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def execute_status(task_id: str) -> tuple[BulkBody | ErrorResponse, int]:
    """Get the status of an execution task.

    Args:
        task_id (str): The ID of the execution task.

    Returns:
        str: The response containing task status
        ErrorResponse: The response containing task status or error message
    """
    try:
        res = bulks.update_users.AsyncResult(task_id)
    except RedisConnectionError:
        error = f"Failed to connect to Redis: {task_id}"
        return ErrorResponse(code="", message=error), 500
    if not res:
        error = f"Task not found: {task_id}"
        return ErrorResponse(code="", message=error), 404
    return BulkBody(status=res.state), 200


@bp.get("/result/<string:history_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def result(
    history_id: UUID, query: UploadQuery
) -> tuple[ExecuteResults | ErrorResponse, int]:
    """Get the result of a bulk upload.

    Args:
        history_id (UUID):ID of the history to get.
        query(UploadQuery): Query parameters for filtering results.

    Returns:
        ExecuteResults: Summary of displayed history If the get is successful
        ErrorResponse: If the get is failed
    """
    status_filter = [STATUS_MAP[status] for status in query.f] if query.f else []
    offset = query.p or 1
    size = query.l or DEFAULT_SEARCH_COUNT
    try:
        if not bulks.chack_permission_to_view(history_id):
            error = f"User does not have permission for history: {history_id}"
            current_app.logger.error(error)
            return ErrorResponse(code="", message=error), 403
        result = bulks.get_upload_result(
            history_id=history_id, status_filter=status_filter, offset=offset, size=size
        )
    except RecordNotFound as exc:
        return ErrorResponse(code="", message=str(exc)), 404

    return result, 200


@bp.get("/user-export")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def user_export(user_ids: list[str]) -> Response | tuple[ErrorResponse, int]:
    """Export users to a file for bulk processing.

    Args:
        user_ids (list[str]): The IDs of the users to export.

    Returns:
        Response: The response containing the exported file
        ErrorResponse: The response containing an error message if the export fails
    """
    try:
        files = bulks.make_export_file(user_ids)
    except InvalidExportError as exc:
        return ErrorResponse(code="", message=str(exc)), 500
    return send_file(files)
