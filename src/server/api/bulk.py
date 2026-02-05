#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for bulk endpoints."""

from pathlib import Path
from uuid import UUID, uuid7

from flask import Blueprint, current_app
from flask_login import current_user
from flask_pydantic import validate
from redis import exceptions

from server.api.helpers import validate_files
from server.api.schemas import (
    BulkBody,
    ErrorResponse,
    TargetRepository,
    UploadBody,
    UploadFiles,
    UploadQuery,
)
from server.config import config
from server.entities.bulk import ResultSummary, ValidateSummary
from server.services import bulks, history_table


bp = Blueprint("bulk", __name__)


@bp.post("/upload-file")
@validate_files
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
    temp_id = uuid7()
    temp_dir = Path(config.temp_file_dir)
    current_app.logger.info("files %s", files)
    original_filename = files.bulk_file.filename or "upload_file"
    operator_id = current_user.id
    operator_name = current_user.user_name
    new_filename = f"{temp_id}_{Path(original_filename).name}"
    file_path = temp_dir / new_filename
    files.bulk_file.save(str(file_path))
    file_content = {"repositories": [{"id": form.repository_id}]}
    history_table.create_file(
        file_id=temp_id, file_path=str(file_path), file_content=file_content
    )

    bulks.delete_temporary_file.apply_async((str(temp_id),), countdown=3600)  # pyright: ignore[reportCallIssue]
    async_result = bulks.validate_upload_data.delay(
        temp_file_id=temp_id, operator_id=operator_id, operator_name=operator_name
    )  # pyright: ignore[reportCallIssue]
    return BulkBody(task_id=async_result.id, temp_file_id=temp_id), 200


@bp.get("/validate/status/<string:task_id>")
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
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    return BulkBody(status=res.state), 200


@bp.get("/validate/result/<string:task_id>")
@validate(response_by_alias=True)
def validate_result(
    query: UploadQuery,
    task_id: str,
) -> tuple[ValidateSummary | ErrorResponse, int]:
    """Get the result of a validation task.

    Args:
        query (UploadQuery): Query parameters for filtering results.
        task_id (str): The ID of the validation task.

    Returns:
        ValidateSummary: The response containing validation result
        ErrorResponse: The response containing validation result or error message.
    """
    try:
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    if not res.successful():
        return ErrorResponse(code="", message="Task not successful."), 400
    history_id = res.result
    status_filter = (
        [
            {0: "create", 1: "update", 2: "delete", 3: "skip", 4: "error"}[status]
            for status in query.f
        ]
        if query.f
        else []
    )
    offset = query.p or 1
    size = query.l or 20
    return bulks.get_validate_result(
        history_id=history_id, status_filter=status_filter, offset=offset, size=size
    ), 200


@bp.get("/missing-user-get/<string:task_id>")
@validate(response_by_alias=True)
def missing_user_get(task_id: str) -> tuple[UploadBody | ErrorResponse, int]:
    """Get the list of users not included in a validation task.

    Args:
        task_id (str): The ID of the validation task.

    Returns:
        list[UserDetail]: The response containing list of users not included
        ErrorResponse: The response containing error message
    """
    try:
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    if not res.successful():
        return ErrorResponse(code="", message="Task not successful."), 400
    history_id = res.result
    return UploadBody(delete_users=bulks.get_missing_users(history_id)), 200


@bp.post("/execute")
@validate(response_by_alias=True)
def execute(body: UploadBody) -> tuple[BulkBody | ErrorResponse, int]:
    """Execute a bulk upload.

    Args:
        body (UploadBody):
          The request body containing temporary ID, repository ID, task ID,
          and users to delete.

    Returns:
        BulkBody: The response containing task ID
        ErrorResponse: The response containing task ID or error message
    """
    async_result = bulks.update_users.delay(  # pyright: ignore[reportFunctionMemberAccess]
        task_id=body.task_id,
        temp_file_id=body.temp_file_id,
        delete_users=body.delete_users,
    )
    history_id = (
        history_table.get_history_by_file_id(body.temp_file_id).id
        if body.temp_file_id
        else None
    )
    return BulkBody(task_id=async_result.id, history_id=history_id), 200


@bp.get("/execute/status/<string:task_id>")
@validate()
def execute_status(task_id: str) -> tuple[BulkBody | ErrorResponse, int]:
    """Get the status of an execution task.

    Args:
        task_id (str): The ID of the execution task.

    Returns:
        str: The response containing task status
        ErrorResponse: The response containing task status or error message
    """
    res = current_app.extensions["celery"].AsyncResult(task_id)
    return BulkBody(status=res.state), 200


@bp.get("/result/<string:history_id>")
@validate(response_by_alias=True)
def result(
    history_id: UUID, query: UploadQuery
) -> tuple[ResultSummary | ErrorResponse, int]:
    """Get the result of a bulk upload.

    Args:
        history_id (UUID):ID of the history to get.
        query(UploadQuery): Query parameters for filtering results.

    Returns:
        ResultSummary: Summary of displayed history If the get is successful
        ErrorResponse: If the get is failed
    """
    status_filter = (
        [
            {0: "create", 1: "update", 2: "delete", 3: "skip", 4: "error"}[status]
            for status in query.f
        ]
        if query.f
        else []
    )
    offset = query.p or 1
    size = query.l or 10
    return bulks.get_upload_result(
        history_id=history_id, status_filter=status_filter, offset=offset, size=size
    ), 200
