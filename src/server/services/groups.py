#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing groups."""

import re
import typing as t

from http import HTTPStatus

import requests

from flask import current_app
from pydantic_core import ValidationError

from server.clients import bulks, groups
from server.config import config
from server.const import MAP_NOT_FOUND_PATTERN
from server.entities.bulk_request import BulkOperation
from server.entities.group_detail import GroupDetail
from server.entities.map_error import MapError
from server.entities.map_group import Administrator, MemberUser, Service
from server.entities.search_request import SearchResult
from server.entities.summaries import GroupSummary
from server.exc import (
    CredentialsError,
    InvalidQueryError,
    OAuthTokenError,
    RequestConflict,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.services.utils.search_queries import GroupsCriteria, build_search_query

from .token import get_access_token, get_client_secret
from .utils import build_patch_operations, build_update_member_operations


if t.TYPE_CHECKING:
    from server.clients.groups import GroupsSearchResponse
    from server.entities.map_group import MapGroup
    from server.entities.patch_request import PatchOperation


def search(criteria: GroupsCriteria) -> SearchResult[GroupSummary]:
    """Search for groups based on given criteria.

    Args:
        criteria (GroupsCriteria): Search criteria for filtering groups.

    Returns:
        SearchResult: Search result containing Group summaries.

    Raises:
        InvalidQueryError: If the query construction is invalid.
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    default_include = {
        "id",
        "display_name",
        "public",
        "member_list_visibility",
        "members",
    }
    try:
        query = build_search_query(criteria)
        access_token = get_access_token()
        client_secret = get_client_secret()
        results: GroupsSearchResponse = groups.search(
            query,
            include=default_include,
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

        error = "Failed to search Group resources from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Group resources from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except InvalidQueryError, OAuthTokenError, CredentialsError:
        raise

    if isinstance(results, MapError):
        current_app.logger.info(results.detail)
        raise InvalidQueryError(results.detail)

    return SearchResult[GroupSummary](
        total=results.total_results,
        page_size=results.items_per_page,
        offset=results.start_index,
        resources=[GroupSummary.from_map_group(group) for group in results.resources],
    )


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


def delete_multiple(group_ids: set[str]) -> set[str] | None:
    """Delete groups from mAP Core API by group_ids.

    Args:
        group_ids (list[str]): ID of the Group resource.

    Returns:
        list[str]: group id list of failed.

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
        ResourceNotFound: If the Group resource is not found.
        ResourceInvalid: If the Group resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result = groups.delete_by_id(
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

    if result is None:
        return

    if re.search(MAP_NOT_FOUND_PATTERN, result.detail):
        raise ResourceNotFound(result.detail)

    raise ResourceInvalid(result.detail)


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
        error = "cannot add and remove the same user."
        raise RequestConflict(error)
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        target = groups.get_by_id(
            group_id, access_token=access_token, client_secret=client_secret
        )
        if isinstance(target, MapError):
            current_app.logger.info(target.detail)
            raise ResourceInvalid(target.detail)
        user_list: set[str] = {
            u.value for u in (target.members or []) if u.type == "User"
        }
        system_admins = get_system_admin()
        operations = build_update_member_operations(
            add=add, remove=remove, user_list=user_list, system_admins=system_admins
        )

        result: MapGroup | MapError = groups.patch_by_id(
            group_id,
            operations,
            include=({"members"}),
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
        system_admins = get_system_admin()
        request_group.members = [
            MemberUser(type="User", value=admin_id) for admin_id in system_admins
        ]
        request_group.administrators = [
            Administrator(value=admin_id) for admin_id in system_admins
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


def get_system_admin() -> set[str]:
    """Get group from mAP Core API by group_id.

    Returns:
        GroupDetail: get group detail.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
        ResourceInvalid: If the Group resource data is invalid.
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
        raise ResourceInvalid(result.detail)

    if not result.members:
        error = "System admin group has no members."
        current_app.logger.error(error)
        raise ResourceInvalid(error)

    return {members.value for members in result.members if members.type == "User"}
