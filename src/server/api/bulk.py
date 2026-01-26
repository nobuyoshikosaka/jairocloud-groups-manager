#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for bulk endpoints."""

from pathlib import Path
from uuid import UUID, uuid7

from flask import Blueprint, current_app
from flask_login import login_required
from flask_pydantic import validate
from redis import exceptions

from server.api.helper import roles_required
from server.api.schemas import (
    BulkBody,
    ErrorResponse,
    UploadBody,
    UploadFiles,
    UploadQuery,
)
from server.db.history import Files
from server.db.utils import db
from server.entities.bulk import ResultSummary, ValidateSummary
from server.entities.user_detail import UserDetail
from server.services import bulks


bp = Blueprint("bulk", __name__)


@bp.post("/upload-file")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def upload_file(
    form: UploadFiles,
) -> tuple[BulkBody | ErrorResponse, int]:
    """ """
    try:
        original_filename = form.files.filename or "upload_file"
        temp_id = uuid7()

        temp_dir = Path("/data/temporary_files")

        new_filename = f"{temp_id}_{Path(original_filename).name}"

        file_path = temp_dir / new_filename

        form.files.file.save(str(file_path))

        file_content = {"repositories": [form.repository_id]}  # type: ignore

        db.session.add(
            Files(id=temp_id, file_path=file_path, file_content=file_content)  # pyright: ignore[reportCallIssue]
        )
        db.session.commit()

        bulks.delete_temporary_file.apply_async(args=[temp_id], countdown=3600)

        async_result = bulks.validate_upload_data.delay(temp_id)

        return BulkBody(task_id=async_result.id, temporary_id=temp_id), 200

    except Exception as e:
        return ErrorResponse(code="", message=str(e)), 400


@bp.get("/validate/status/<string:task_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def validate_status(task_id: str) -> tuple[BulkBody | ErrorResponse, int]:
    """ """
    try:
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    return res.state, 200


@bp.get("/validate/result/<string:task_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def validate_result(
    task_id: str,
) -> tuple[ValidateSummary | ErrorResponse, int]:
    """ """
    try:
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    if not res.successful():
        return ErrorResponse(code="", message="Task not successful."), 400
    history_id = res.result
    return bulks.get_validate_result(history_id), 200


@bp.get("/not-included/<string:task_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def not_included_get(task_id: str) -> tuple[list[UserDetail] | ErrorResponse, int]:
    """"""
    try:
        res = current_app.extensions["celery"].AsyncResult(task_id)
    except exceptions.ConnectionError:
        return ErrorResponse(code="", message=""), 500
    if not res:
        return ErrorResponse(code="", message=f"{task_id} not found."), 404
    if not res.successful():
        return ErrorResponse(code="", message="Task not successful."), 400
    history_id = res.result
    return bulks.get_not_included_users(history_id), 200


@bp.post("/execute/<string:task_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def execute(body: UploadBody) -> tuple[BulkBody | ErrorResponse, int]:
    """ """

    return ErrorResponse(code="", message=""), 500


@bp.post("/upload-file/<string:task_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate()
def execute_status(task_id: str) -> tuple[str | ErrorResponse, int]:
    """ """
    res = current_app.extensions["celery"].AsyncResult(task_id)
    return res.state, 200


@bp.post("/result/<string:history_id>")
@login_required
@roles_required("system_admin", "repository_admin")
@validate(response_by_alias=True)
def result(
    history_id: UUID, query: UploadQuery
) -> tuple[ResultSummary | ErrorResponse, int]:
    """ """

    return ErrorResponse(code="", message=""), 500
