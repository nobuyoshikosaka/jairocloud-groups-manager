#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for group endpoints."""

from flask import Blueprint, url_for
from flask_login import current_user, login_required
from flask_pydantic import validate

from server.api.helper import roles_required
from server.api.schema import DeleteGroupRequest, ErrorResponse, MemberPatchRequest
from server.entities.group_detail import GroupDetail
from server.exc import (
    ResourceInvalid,
    ResourceNotFound,
)
from server.services import groups, permission


bp = Blueprint("groups", __name__)


@bp.post("/")
@login_required
@roles_required("system_admin", "repository_admin")
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
@roles_required("system_admin", "repository_admin")
@validate()
def id_get(group_id: str) -> tuple[GroupDetail | ErrorResponse, int]:
    """Get information of group endpoint.

    Args:
        group_id(str): Group id

    Returns:
        - If succeeded in getting group information, group information and status code 200
        - If logged-in user does not have permission, status code 403
        - If group not found, status code 404
    """
    result = groups.get_by_id(group_id)

    if result is None:
        return ErrorResponse(code="", message=f"'{group_id}' Not Found"), 404
    if current_user.is_system_admin or permission.filter_permitted_group_ids(result.id):
        return result, 200
    return ErrorResponse(), 403


@bp.put("/<string:group_id>")
@login_required
@roles_required("system_admin", "repository_admin")
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
        current_user.is_system_admin or permission.filter_permitted_group_ids(body.id)
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
@roles_required("system_admin", "repository_admin")
@validate()
def id_patche(
    group_id: str, body: MemberPatchRequest
) -> tuple[GroupDetail | ErrorResponse, int]:
    """Update group member endpoint.

    Args:
        group_id(str): Group id
        body(MemberPatchRequest): Group member information

    Returns:
        - If succeeded in updating group member,
          group member and status code 200
        - If logged-in user does not have permission, status code 403
        - If group not found, status code 404
        - If coflicted group member, status code 409
    """
    if not (
        current_user.is_system_admin or permission.filter_permitted_group_ids(group_id)
    ):
        return ErrorResponse(), 403
    try:
        result = groups.update_member(group_id, body.add, body.remove)
    except ResourceInvalid as ex:
        return ErrorResponse(code="", message=str(ex)), 409
    except ResourceNotFound as ex:
        return ErrorResponse(code="", message=str(ex)), 404
    return result, 200


@bp.delete("/<string:group_id>")
@login_required
@roles_required("system_admin", "repository_admin")
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
        current_user.is_system_admin or permission.filter_permitted_group_ids(group_id)
    ):
        return ErrorResponse(), 403
    groups.delete_by_id(group_id)
    return None, 204


@bp.post("/delete")
@login_required
@roles_required("system_admin", "repository_admin")
@validate()
def delete_post(
    body: DeleteGroupRequest,
) -> tuple[None, int] | tuple[ErrorResponse, int]:
    """The multiple group deletion endpoint.

    Args:
        body(DeleteGroupRequest): Group id for delte

    Returns:
        - If succeeded in delete group ,
          status code 204
        - If logged-in user does not have permission, status code 403
    """
    group_id = body.group_ids
    if not (
        current_user.is_system_admin or permission.filter_permitted_group_ids(*group_id)
    ):
        return ErrorResponse(), 403
    group_list = groups.delete(body.group_ids)
    if group_list:
        message = f"{group_list} is failde"
        return ErrorResponse(code="", message=message), 500
    return None, 204
