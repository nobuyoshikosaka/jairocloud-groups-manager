#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for history endpoints."""

import typing as t

from uuid import UUID

from flask import Blueprint, Response, send_file
from flask_pydantic import validate

from server.api.schemas import ErrorResponse, HistoryPublic
from server.entities.history_detail import (
    DownloadHistory,
    HistoryDataFilter,
    HistoryQuery,
    UploadHistory,
)
from server.services import history


bp = Blueprint("history", __name__)


@bp.get("/<tub>/filter-options")
@validate(response_many=True)
def filter_options(
    tub: t.Literal["download", "upload"],
) -> tuple[HistoryDataFilter, int] | tuple[ErrorResponse, int]:
    try:
        history_filter = history.get_filters(tub)
    except ValueError:
        return ErrorResponse(code="", message=""), 500

    return history_filter, 200


@bp.get("/<string:tub>")
@validate()
def get(
    query: HistoryQuery, tub: t.Literal["download", "upload"]
) -> tuple[DownloadHistory | UploadHistory | ErrorResponse, int]:
    try:
        if tub == "download":
            history_data = history.get_download_history_data(query)
            result = DownloadHistory(history_data)
        else:
            history_data = history.get_upload_history_data(query)
            result = UploadHistory(history_data)
    except ConnectionError:
        return ErrorResponse(code="", message=""), 503
    return result, 200


@bp.put("/<tub>/<history_id>/public-status")
@validate()
def public_status(
    tub: t.Literal["download", "upload"], history_id: UUID, body: HistoryPublic
) -> tuple[bool, int]:
    """"""
    result: bool = history.update_public_status(
        tub=tub, history_id=history_id, public=body.public
    )

    return result, 200


@bp.get("/files/<file_id>")
@validate()
def files(file_id: UUID) -> Response:
    file_path = history.get_file_path(file_id)

    return send_file(path_or_file=file_path)


@bp.get("/files/<file_id>/exists")
@validate()
def is_exist_files(file_id: UUID) -> tuple[bool | ErrorResponse, int]:
    """Check if the file exists.

    Args:
        file_id (UUID): Unique identifier of the file

    Returns:
        bool:Whether to check if the file exists
    """
    try:
        file_path = Path(history.get_file_path(file_id))
    except DatabaseError as ex:
        return ErrorResponse(code="", message=str(ex)), 503
    if not Path(file_path).exists():
        return False, 200
    return True, 200
