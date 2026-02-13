#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for history endpoints."""

import typing as t

from pathlib import Path
from uuid import UUID

from flask import Blueprint, Response, send_file
from flask_login import login_required
from flask_pydantic import validate

from server.api.helpers import roles_required
from server.api.schemas import ErrorResponse, HistoryPublic
from server.const import USER_ROLES
from server.entities.history_detail import HistoryQuery
from server.entities.search_request import FilterOption, SearchResult
from server.exc import DatabaseError, RecordNotFound
from server.services import history


bp = Blueprint("history", __name__)


@bp.get("/<tub>/filter-options")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_many=True)
def filter_options(
    tub: t.Literal["download", "upload"],
) -> tuple[list[FilterOption], int] | tuple[ErrorResponse, int]:
    """Get filter options for history data.

    Args:
        tub (t.Literal["download", "upload"]): Type of history (download or upload)

    Returns:
        HistoryDataFilter: if successful and status code 200
        ErrorResponse: if an error occurs  and status code 500
    """
    try:
        history_filter = history.get_filters(tub)
    except ValueError as ex:
        return ErrorResponse(code="", message=str(ex)), 500

    return history_filter, 200


@bp.get("/<string:tub>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
def get(
    tub: t.Literal["download", "upload"], query: HistoryQuery
) -> tuple[SearchResult | ErrorResponse, int]:
    """Get history data.

    Args:
        query (HistoryQuery): Query parameters for filtering history data
        tub (t.Literal["download", "upload"]): Type of history (download or upload)

    Returns:
        SearchResult: if successful and status code 200
        ErrorResponse: if a connection error occurs and status code 503
    """
    try:
        if tub == "download":
            result = history.get_download_history_data(query)
        else:
            result = history.get_upload_history_data(query)
    except DatabaseError:
        error = f"{tub} table connection error"
        return ErrorResponse(code="", message=error), 503
    return result, 200


@bp.put("/<tub>/<history_id>/public-status")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN)
@validate()
def public_status(
    tub: t.Literal["download", "upload"], history_id: UUID, body: HistoryPublic
) -> tuple[bool | ErrorResponse, int]:
    """Update the public status of a history item.

    Args:
        tub (t.Literal["download", "upload"]): Type of history (download or upload)
        history_id (UUID): Unique identifier of the history item
        body (HistoryPublic): Request body containing the new public status

    Returns:
        bool: True if the update was successful, False otherwise
        int: HTTP status code
    """
    try:
        result: bool = history.update_public_status(
            tub=tub, history_id=history_id, public=body.public
        )
    except RecordNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    return result, 200


@bp.get("/files/<file_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
def files(file_id: UUID) -> Response | tuple[ErrorResponse, int]:
    """Download a file associated with a history item.

    Args:
        file_id (UUID): Unique identifier of the file to be downloaded

    Returns:
        Response: Flask response object to send the file
    """
    try:
        path_str = history.get_file_path(file_id)
        file_path = Path(path_str)
    except RecordNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    return send_file(path_or_file=file_path)


@bp.get("/files/<file_id>/exists")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
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
    except RecordNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    if not Path(file_path).exists():
        return False, 200
    return True, 200
