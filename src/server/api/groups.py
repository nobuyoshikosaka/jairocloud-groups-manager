#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API endpoints for group-related operations."""

import typing as t

from flask import Blueprint, url_for
from flask_login import login_required
from flask_pydantic import validate

from server.api.helpers import roles_required
from server.const import USER_ROLES
from server.entities.group_detail import GroupDetail
from server.entities.search_request import FilterOption, SearchResult
from server.exc import (
    InvalidQueryError,
    ResourceInvalid,
    ResourceNotFound,
)
from server.services import groups
from server.services.filter_options import search_groups_options
from server.services.utils import (
    filter_permitted_group_ids,
    is_current_user_system_admin,
)

from .schemas import (
    DeleteGroupsRequest,
    ErrorResponse,
    GroupPatchRequest,
    GroupsQuery,
)


bp = Blueprint("groups", __name__)


@bp.get("")
@bp.get("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def get(query: GroupsQuery) -> tuple[SearchResult | ErrorResponse, int]:
    """Get a list of groups based on query parameters.

    Args:
        query (GroupsQuery): Query parameters for filtering groups.

    Returns:
        - If succeeded in getting groups, search result and status code 200
        - If query is invalid, error message and status code 400
    """
    try:
        results = groups.search(query)
    except InvalidQueryError as exc:
        return ErrorResponse(code="", message=str(exc)), 400

    return results, 200


@bp.get("")
@bp.post("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def post(
    body: GroupDetail,
) -> tuple[GroupDetail, int, dict[str, str]] | tuple[ErrorResponse, int]:
    """Create group endpoint.

    Args:
        body(GroupDetail): Group information

    Returns:
        - If succeeded in creating group, group information
            and status code 201 and location header
        - If logged-in user does not have permission, status code 403
        - If id already exist, status code 409
    """
    repository_id = body.repository.id if body.repository else None
    if not repository_id:
        return ErrorResponse(code="", message="repository id is required"), 400

    if not has_permission(repository_id):
        return ErrorResponse(code="", message="not has permission"), 403

    try:
        result = groups.create(body)
    except ResourceInvalid:
        return ErrorResponse(code="", message="id already exist"), 409

    location = url_for("api.groups.id_get", group_id=result.id, _external=True)
    return result, 201, {"Location": location}


@bp.get("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_get(group_id: str) -> tuple[GroupDetail | ErrorResponse, int]:
    """Get information of group endpoint.

    Args:
        group_id(str): Group id

    Returns:
        - If succeeded in getting group information,
          group information and status code 200
        - If logged-in user does not have permission, status code 403
        - If group not found, status code 404
    """
    if not has_permission(group_id):
        return ErrorResponse(code="", message=""), 403

    result = groups.get_by_id(group_id)

    if result is None:
        return ErrorResponse(code="", message=f"'{group_id}' Not Found"), 404
    return result, 200


@bp.put("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_put(group_id: str, body: GroupDetail) -> tuple[GroupDetail | ErrorResponse, int]:
    """Update group information endpoint.

    Args:
        group_id(str): Group id
        body(GroupDetail): Group information

    Returns:
        - If succeeded in updating group informaion,
          group information and status code 200
        - If logged-in user does not have permission, status code 403
        - If group not found, status code 404
        - If coflicted group information, status code 409
    """
    if not has_permission(group_id):
        return ErrorResponse(
            code="", message=f"Not have permission to edit {group_id}."
        ), 403

    try:
        result = groups.update(body)
    except ResourceInvalid as ex:
        return ErrorResponse(code="", message=str(ex)), 409
    except ResourceNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    return result, 200


@bp.patch("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_patch(
    group_id: str, body: GroupPatchRequest
) -> tuple[GroupDetail | ErrorResponse, int]:
    """Update group member endpoint.

    Args:
        group_id(str): Group id
        body(GroupPatchRequest): Group member information

    Returns:
        - If succeeded in updating group member,
          group member and status code 200
        - If logged-in user does not have permission, status code 403
        - If group not found, status code 404
        - If coflicted group member, status code 409
    """
    if not has_permission(group_id):
        return ErrorResponse(code="", message=""), 403

    adding = set()
    removing = set()
    for operation in body.operations:
        if operation.path != "member":
            error = f"Unsupported attribute to update: {operation.path}"
            return ErrorResponse(code="", message=error), 400

        if operation.op == "add":
            adding.update(set(operation.value))
        elif operation.op == "remove":
            removing.update(set(operation.value))

    try:
        result = groups.update_member(group_id, add=adding, remove=removing)
    except ResourceInvalid as ex:
        return ErrorResponse(code="", message=str(ex)), 409
    except ResourceNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404

    return result, 200


@bp.delete("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def id_delete(group_id: str) -> tuple[t.Literal[""], int] | tuple[ErrorResponse, int]:
    """Single group deletion endpoint.

    Args:
        group_id(str): Group id

    Returns:
        - If succeeded in delete group ,
          status code 204
        - If logged-in user does not have permission, status code 403
    """
    if not has_permission(group_id):
        return ErrorResponse(code="", message=""), 403

    groups.delete_by_id(group_id)
    return "", 204


@bp.post("/delete")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate(response_by_alias=True)
def delete_post(
    body: DeleteGroupsRequest,
) -> tuple[t.Literal[""], int] | tuple[ErrorResponse, int]:
    """The multiple group deletion endpoint.

    Args:
        body(DeleteGroupsRequest): Group id for delte

    Returns:
        - If succeeded in delete group ,
          status code 204
        - If logged-in user does not have permission, status code 403
    """
    group_ids = body.group_ids
    if not has_permission(*group_ids):
        return ErrorResponse(code="", message=""), 403

    group_list = groups.delete_multiple(group_ids)
    if group_list:
        message = f"{group_list} is failed"
        return ErrorResponse(code="", message=message), 500
    return "", 204


@bp.get("/filter-options")
@validate(response_many=True)
def filter_options() -> list[FilterOption]:
    """Get filter options for groups search.

    Returns:
        list[FilterOption]: List of filter options for group search.
    """
    return search_groups_options()


def has_permission(*group_id: str) -> bool:
    """Check user controll permmision.

    If the logged-in user is a system administrator or
    an administrator of the target group, that user has permission.

    Args:
        group_id (str): Group ID to check permission for.

    Returns:
        bool:
        - True: logged-in user has permission
        - False: logged-in user does not have permission
    """
    if is_current_user_system_admin():
        return True

    return bool(filter_permitted_group_ids(*group_id))
