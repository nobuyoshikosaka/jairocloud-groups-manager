#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API endpoints for user-related operations."""

import inspect
import typing as t

from flask import Blueprint, url_for
from flask_login import current_user, login_required
from flask_pydantic import validate

from server.const import USER_ROLES
from server.entities.login_user import LoginUser
from server.entities.search_request import FilterOption, SearchResult
from server.entities.user_detail import UserDetail
from server.exc import (
    InvalidQueryError,
    RequestConflict,
    ResourceInvalid,
    ResourceNotFound,
)
from server.services import users
from server.services.utils import (
    get_permitted_repository_ids,
    is_current_user_system_admin,
    search_users_options,
)

from .auth import logout
from .helpers import roles_required
from .schemas import ErrorResponse, UsersQuery


bp = Blueprint("users", __name__)


@bp.get("")
@bp.get("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def get(query: UsersQuery) -> tuple[SearchResult | ErrorResponse, int]:
    """Get a list of users based on query parameters.

    Args:
        query (UsersQuery): Query parameters for filtering users.

    Returns:
        - If succeeded in getting users, search result and status code 200
        - If query is invalid, error message and status code 400
    """
    try:
        results = users.search(query)
    except InvalidQueryError as exc:
        return ErrorResponse(code="", message=str(exc)), 400

    return results, 200


@bp.post("")
@bp.post("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def post(
    body: UserDetail,
) -> tuple[UserDetail, int, dict[str, str]] | tuple[ErrorResponse, int]:
    """Create user endpoint.

    Args:
        body(UserDetail): User information

    Returns:
        - If succeeded in creating user, user information
            and status code 201 and location header
        - If logged-in user does not have permission, status code 403
        - If id or eppn already exist, status code 409
        - If other error, status code 500

    """
    if not has_permission(body):
        return ErrorResponse(code="", message="not has permission"), 403

    try:
        created = users.create(body)
    except ResourceInvalid as exv:
        return ErrorResponse(code="", message=str(exv)), 409

    header = {
        "Location": url_for("api.users.id_get", user_id=created.id, _external=True)
    }
    return (created, 201, header)


@bp.get("/<string:user_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_get(user_id: str) -> tuple[UserDetail | ErrorResponse, int]:
    """Get information of user endpoint.

    Args:
        user_id(str): User id

    Returns:
        - If succeeded in getting user information, user information and status code 200
        - If logged-in user does not have permission, status code 403
        - If user not found, status code 404
        - If other error, status code 500
    """
    user = users.get_by_id(user_id, more_detail=True)
    if user is None:
        return ErrorResponse(code="", message="user not found"), 404

    if not has_permission(user):
        return ErrorResponse(code="", message="not has permission"), 403

    return user, 200


@bp.put("/<string:user_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_put(user_id: str, body: UserDetail) -> tuple[UserDetail | ErrorResponse, int]:
    """Update user information endpoint.

    Args:
        user_id(str): User id
        body(UserDetail): User information

    Returns:
        - If succeeded in updating user informaion,
          user information and status code 200
        - If logged-in user does not have permission, status code 403
        - If user not found, status code 404
        - If coflicted user information, status code 409
        - If other error, status code 500

    """
    if body.is_system_admin and not is_current_user_system_admin():
        return ErrorResponse(code="", message="not has permission"), 403

    if not has_permission(body):
        return ErrorResponse(code="", message="not has permission"), 403

    is_self = t.cast("LoginUser", current_user).map_id == user_id
    body.id = user_id
    try:
        updated = users.update(body)
    except* ResourceNotFound as e:
        error = ErrorResponse(code="", message=str(e)), 404
    except* (ResourceInvalid, RequestConflict) as e:
        error = ErrorResponse(code="", message=str(e)), 409
    else:
        if is_self:
            inspect.unwrap(logout)()
        return updated, 200

    return error


def has_permission(user: UserDetail) -> bool:
    """Check user controll permmision.

    If the logged-in user is a system administrator or
    an administrator of the target repository, that user has permission.

    Args:
       user (UserDetail): User information.

    Returns:
        bool:
        - True: logged-in user has permission
        - False: logged-in user does not have permission
    """
    if is_current_user_system_admin():
        return True

    if user.is_system_admin:
        return False

    roles = user.repository_roles or []
    permitted_repository_ids = get_permitted_repository_ids()
    return any(repo.id in permitted_repository_ids for repo in roles)


@bp.get("/filter-options")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_many=True)
def filter_options() -> list[FilterOption]:
    """Get filter options for searching users.

    Returns:
        list[FilterOption]: List of filter options for user search.
    """
    return search_users_options()
