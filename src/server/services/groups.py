#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing groups."""

import typing as t

from http import HTTPStatus

import requests

from flask import current_app
from pydantic_core import ValidationError

from server.clients import bulks, groups
from server.config import config
from server.entities.bulk_request import BulkOperation
from server.entities.group_detail import GroupDetail
from server.entities.map_error import MapError
from server.entities.map_group import Administrator, MemberUser, Service
from server.entities.summaries import GroupSummary
from server.exc import (
    CredentialsError,
    OAuthTokenError,
    RequestConflict,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)

from .token import get_access_token, get_client_secret
from .utils import build_patch_operations, build_update_member_operations


if t.TYPE_CHECKING:
    from server.entities.map_group import MapGroup
    from server.entities.patch_request import PatchOperation


def search(**query) -> list[GroupSummary]:
    # Placeholder implementation
    return [GroupSummary(id=group_id) for group_id in query["id"]]


def create(group: GroupDetail) -> GroupDetail:
    """Create group to mAP Core API.

    Args:
        group (GroupDetail):
            Detail information about the group created from the input data.

    Returns:
        GroupDetail: created group detail information.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    system_admins = get_system_admin()
    if not system_admins:
        error = "Failed to get system admin user id from mAP Core API."
        raise UnexpectedResponseError(error)
    map_group = group.to_map_group()
    map_group.members = [
        MemberUser(type="User", value=admin_id) for admin_id in system_admins
    ]
    map_group.administrators = [
        Administrator(value=admin_id) for admin_id in system_admins
    ]

    map_group.services = [
        Service(
            value="jairocloud-groups-manager_dev",
        )
    ]

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.post(
            map_group,
            exclude=({"external_id", "meta"}),
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return GroupDetail.from_map_group(result)


def get_by_id(group_id: str) -> GroupDetail | None:
    """Get group from mAP Core API by group_id.

    Args:
        group_id (str): ID of the Group resource.

    Returns:
        GroupDetail: get group detail.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.get_by_id(
            group_id, access_token=access_token, client_secret=client_secret
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        return None

    return GroupDetail.from_map_group(result)


def update(group: GroupDetail) -> GroupDetail:
    """Update group from mAP Core API by group_id.

    Args:
        group (GroupDetail):
            Detail information about the group update from the input data.

    Returns:
        GroupDetail: updated group detail

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        ResourceNotFound: If the Group resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    current: GroupDetail | None = get_by_id(group.id)
    if current is None:
        error = f"'{group.id}' Not Found"
        raise ResourceNotFound(error)

    operations: list[PatchOperation] = build_patch_operations(
        current.to_map_group(),
        group.to_map_group(),
        exclude={"schemas", "meta", "administrator", "memeber"},
    )

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.patch_by_id(
            group.id,
            operations,
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to update Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return GroupDetail.from_map_group(result)


def delete(group_ids: set[str]) -> set[str] | None:
    """Delete groups from mAP Core API by group_ids.

    Args:
        group_ids (list[str]): ID of the Group resource.

    Returns:
        list[str]: group id list of faild.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    operations = [
        BulkOperation(method="DELETE", path=f"/Groups/{group_id}")
        for group_id in group_ids
    ]
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result = bulks.post(operations, access_token, client_secret)
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to delete Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    failed_list = {
        o.path.removeprefix("Groups/")
        for o in result.operations
        if type(o.response) is MapError
    }
    return failed_list if failed_list != set() else None


def delete_by_id(group_id: str) -> None:
    """Delete group from mAP Core API by group_id.

    Args:
        group_id (str): ID of the Group resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result = groups.delete(
            group_id, access_token=access_token, client_secret=client_secret
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        raise ResourceInvalid


def update_member(group_id: str, add: set[str], remove: set[str]) -> GroupDetail:
    """Update group members by group_id in mAP Core API .

    Args:
        group_id (str): ID of the Group resource.
        add (list[str]): List of user IDs to add .
        remove (list[str]): List of user IDs to remove.

    Returns:
        GroupDetail: updated group detail

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        RequestConflict: If the User id exists in both "add" and "remove".
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if add & remove:
        raise RequestConflict
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        target: MapGroup | MapError = groups.get_by_id(
            group_id, access_token=access_token, client_secret=client_secret
        )
        if isinstance(target, MapError):
            current_app.logger.info(target.detail)
            raise ResourceInvalid(target.detail)
        user_list: set[str] = (
            {u.value for u in target.members if isinstance(u, MemberUser)}
            if target.members
            else set()
        )
        system_admins = get_system_admin()
        if not system_admins:
            error = "Failed to get system admin user id from mAP Core API."
            raise UnexpectedResponseError(error)
        add.difference_update(user_list)
        remove.difference_update(system_admins)
        remove.intersection_update(user_list)
        if remove.issuperset(user_list | add):
            add.update(system_admins)
        operations = build_update_member_operations(add, remove)
        if operations is None:
            return GroupDetail.from_map_group(target)

        result: MapGroup | MapError = groups.patch_by_id(
            group_id,
            operations,
            include=({"member"}),
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to update Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return GroupDetail.from_map_group(result)


def update_put(body: GroupDetail) -> GroupDetail:
    """Update group from mAP Core API by group_id.

    Args:
        body (GroupDetail):
            Detail information about the group update from the input data.

    Returns:
        GroupDetail: updated group detail

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        request_group = body.to_map_group()
        request_group.administrators = [
            Administrator(
                display="nobuyoshi.kosaka",
                value="5520cb7a-0d5e-4389-8644-68859becae82",
            ),
        ]
        request_group.services = [
            Service(
                value="jairocloud-groups-manager_dev",
            ),
        ]
        result: MapGroup | MapError = groups.put_by_id(
            request_group,
            include=({"administrators"}),
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to update Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return GroupDetail.from_map_group(result)


def get_system_admin() -> set[str] | None:
    """Get group from mAP Core API by group_id.

    Returns:
        GroupDetail: get group detail.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.get_by_id(
            config.GROUPS.id_patterns.system_admin,
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        return None

    return (
        {user.value for user in result.members if isinstance(user, MemberUser)}
        if result.members
        else None
    )
