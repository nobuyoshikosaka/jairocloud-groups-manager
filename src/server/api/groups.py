#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API endpoints for group-related operations."""

from flask import Blueprint, url_for
from flask_login import login_required
from flask_pydantic import validate

from server.api.helpers import roles_required
from server.const import USER_ROLES
from server.entities.group_detail import GroupDetail
from server.entities.search_request import FilterOption, SearchResult
from server.exc import (
    ResourceInvalid,
    ResourceNotFound,
)
from server.services import groups, permissions
from server.services.filter_options import search_groups_options

from .schemas import (
    DeleteGroupsRequest,
    ErrorResponse,
    GroupPatchRequest,
    GroupsQuery,
)


bp = Blueprint("groups", __name__)


@bp.get("")
@bp.get("/")
@validate(response_by_alias=True)
def get(query: GroupsQuery) -> tuple[SearchResult, int]:
    """Get a list of groups based on query parameters.

    Args:
        query (GroupsQuery): Query parameters for filtering groups.

    Returns:
        tuple[dict, int]:
            A tuple containing the list of groups and the HTTP status code.
    """
    results = groups.search(query)
    return results, 200


@bp.post("/")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
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
    if isinstance(groups.get_by_id(body.id), GroupDetail):
        return ErrorResponse(code="", message="id already exist"), 409
    try:
        result = groups.create(body)
    except ResourceInvalid:
        return ErrorResponse(code="", message="id already exist"), 400

    header = {
        "Location": url_for("api.groups.id_get", group_id=result.id, _external=True)
    }
    return result, 201, header


@bp.get("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
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
    if not (
        permissions.is_current_user_system_admin()
        or permissions.filter_permitted_group_ids(group_id)
    ):
        return ErrorResponse(code="", message=""), 403
    result = groups.get_by_id(group_id)

    if result is None:
        return ErrorResponse(code="", message=f"'{group_id}' Not Found"), 404
    return result, 200


@bp.put("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
def id_put(body: GroupDetail) -> tuple[GroupDetail | ErrorResponse, int]:
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
    if not (
        permissions.is_current_user_system_admin()
        or permissions.filter_permitted_group_ids(body.id)
    ):
        return ErrorResponse(
            code="", message=f"Not have permission to edit {body.id}."
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
@validate()
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
    if not (
        permissions.is_current_user_system_admin()
        or permissions.filter_permitted_group_ids(group_id)
    ):
        return ErrorResponse(code="", message=""), 403
    try:
        if body.path == "member":
            add_users = set(body.value) if body.op == "add" else set()
            remove_users = set(body.value) if body.op == "remove" else set()
            result = groups.update_member(group_id, add=add_users, remove=remove_users)
        else:
            error = "Changes cannot be made by non-members."
            return ErrorResponse(code="", message=error), 400
    except ResourceInvalid as ex:
        return ErrorResponse(code="", message=str(ex)), 409
    except ResourceNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    return result, 200


@bp.delete("/<string:group_id>")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
def id_delete(group_id: str) -> tuple[None, int] | tuple[ErrorResponse, int]:
    """Single group deletion endpoint.

    Args:
        group_id(str): Group id

    Returns:
        - If succeeded in delete group ,
          status code 204
        - If logged-in user does not have permission, status code 403
    """
    if not (
        permissions.is_current_user_system_admin()
        or permissions.filter_permitted_group_ids(group_id)
    ):
        return ErrorResponse(code="", message=""), 403
    groups.delete_by_id(group_id)
    return None, 204


@bp.post("/delete")
@login_required
@roles_required(USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN)
@validate()
def delete_post(
    body: DeleteGroupsRequest,
) -> tuple[None, int] | tuple[ErrorResponse, int]:
    """The multiple group deletion endpoint.

    Args:
        body(DeleteGroupsRequest): Group id for delte

    Returns:
        - If succeeded in delete group ,
          status code 204
        - If logged-in user does not have permission, status code 403
    """
    group_id = body.group_ids
    if not (
        permissions.is_current_user_system_admin()
        or permissions.filter_permitted_group_ids(*group_id)
    ):
        return ErrorResponse(code="", message=""), 403
    group_list = groups.delete(body.group_ids)
    if group_list:
        message = f"{group_list} is failed"
        return ErrorResponse(code="", message=message), 500
    return None, 204


@bp.get("/filter-options")
@validate(response_many=True)
def filter_options() -> list[FilterOption]:
    """Get filter options for groups search.

    Returns:
        list[FilterOption]: List of filter options for group search.
    """
    return search_groups_options()
