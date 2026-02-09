#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API endpoints for repository-related operations."""

import typing as t

from flask import Blueprint, url_for
from flask_login import login_required
from flask_pydantic import validate

from server.const import USER_ROLES
from server.entities.repository_detail import RepositoryDetail
from server.entities.search_request import SearchResult
from server.exc import InvalidQueryError, ResourceInvalid, ResourceNotFound
from server.services import repositories
from server.services.utils import (
    get_permitted_repository_ids,
    is_current_user_system_admin,
)

from .helpers import roles_required
from .schemas import ErrorResponse, RepositoriesQuery


bp = Blueprint("repositories", __name__)


@bp.get("")
@bp.get("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def get(
    query: RepositoriesQuery,
) -> tuple[SearchResult, int] | tuple[ErrorResponse, int]:
    """Get a list of repositories based on query parameters.

    Args:
        query (RepositoriesQuery): Query parameters for filtering repositories.

    Returns:
        - If succeeded in getting repositories, search result and status code 200
        - If query is invalid, error message and status code 400
    """
    try:
        results = repositories.search(query)
    except InvalidQueryError as exc:
        return ErrorResponse(code="", message=str(exc)), 400

    return results, 200


@bp.post("")
@bp.post("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN)
@validate(response_by_alias=True)
def post(
    body: RepositoryDetail,
) -> tuple[RepositoryDetail, int, dict[str, str]] | tuple[ErrorResponse, int]:
    """Create repository endpoint.

    Args:
        body(RepositoryDetail): Repository information

    Returns:
        - If succeeded in creating repository, repository information
            and status code 201 and location header
        - If logged-in user does not have permission, status code 403
        - If id already exists, status code 409
    """
    try:
        created = repositories.create(body)
    except ResourceInvalid as exc:
        return ErrorResponse(code="", message=str(exc)), 409

    location = url_for(
        "api.repositories.id_get", repository_id=created.id, _external=True
    )
    return created, 201, {"Location": location}


@bp.get("/<string:repository_id>")
@validate(response_by_alias=True)
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
def id_get(repository_id: str) -> tuple[RepositoryDetail | ErrorResponse, int]:
    """Get information of repository endpoint.

    Args:
        repository_id(str): Repository id

    Returns:
        - If succeeded in getting repository information,
            repository information and status code 200
        - If logged-in user does not have permission, status code 403
        - If repository not found, status code 404
    """
    if not has_permission(repository_id):
        return ErrorResponse(code="", message="not has permission"), 403

    result = repositories.get_by_id(repository_id)
    if result is None:
        return ErrorResponse(code="", message="repository not found"), 404

    return result, 200


@bp.put("/<string:repository_id>")
@validate(response_by_alias=True)
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
def id_put(
    repository_id: str, body: RepositoryDetail
) -> tuple[RepositoryDetail | ErrorResponse, int]:
    """Update repository endpoint.

    Args:
        repository_id(str): Repository id
        body(RepositoryDetail): Repository information

    Returns:
        - If succeeded in updating repository, repository information
            and status code 200
        - If logged-in user does not have permission, status code 403
        - If repository not found, status code 404
    """
    if not has_permission(repository_id):
        return ErrorResponse(code="", message="not has permission"), 403

    try:
        updated = repositories.update(body)
    except ResourceNotFound as exc:
        return ErrorResponse(code="", message=str(exc)), 404
    except ResourceInvalid as exc:
        return ErrorResponse(code="", message=str(exc)), 409

    return updated, 200


@bp.delete("/<string:repository_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN)
@validate(response_by_alias=True)
def id_delete(
    repository_id: str,
) -> tuple[t.Literal[""], int] | tuple[ErrorResponse, int]:
    """Delete repository endpoint.

    Args:
        repository_id(str): Repository id

    Returns:
        - If succeeded in deleting repository, status code 204
        - If repository not found, status code 404
    """
    try:
        repositories.delete_by_id(repository_id)
    except ResourceNotFound as exc:
        return ErrorResponse(code="", message=str(exc)), 404
    except ResourceInvalid as exc:
        return ErrorResponse(code="", message=str(exc)), 400

    return "", 204


def has_permission(repository_id: str) -> bool:
    """Check user controll permmision.

    If the logged-in user is a system administrator or
    an administrator of the target repository, that user has permission.

    Args:
        repository_id (str): Repository ID to check permission for.

    Returns:
        bool:
        - True: logged-in user has permission
        - False: logged-in user does not have permission
    """
    if is_current_user_system_admin():
        return True

    permitted_repository_ids = get_permitted_repository_ids()
    return repository_id in permitted_repository_ids
