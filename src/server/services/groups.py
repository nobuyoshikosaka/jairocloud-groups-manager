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
from server.entities.search_request import SearchResponse, SearchResult
from server.entities.summaries import GroupSummary
from server.exc import (
    CredentialsError,
    InvalidFormError,
    InvalidQueryError,
    OAuthTokenError,
    RequestConflict,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.services.utils import validate_group_to_map_group

from .token import get_access_token, get_client_secret
from .users import get_system_admins
from .utils import (
    GroupsCriteria,
    build_patch_operations,
    build_search_query,
    build_update_member_operations,
    prepare_group,
)


if t.TYPE_CHECKING:
    from server.clients.groups import GroupsSearchResponse
    from server.entities.map_group import MapGroup
    from server.entities.patch_request import PatchOperation


@t.overload
def search(criteria: GroupsCriteria) -> SearchResult[GroupSummary]: ...
@t.overload
def search(
    criteria: GroupsCriteria, *, raw: t.Literal[True]
) -> SearchResponse[MapGroup]: ...


def search(
    criteria: GroupsCriteria, *, raw: bool = False
) -> SearchResult[GroupSummary] | SearchResponse[MapGroup]:
    """Search for groups based on given criteria.

    Args:
        criteria (GroupsCriteria): Search criteria for filtering groups.
        raw (bool):
            If True, return raw search response from mAP Core API. Defaults to False.

    Returns:
        object: Search results. The type depends on the `raw` argument.
        - SearchResult;
            Search result containing Group summaries. It has members `total`,
            `page_size`, `offset`, and `resources`.
        - SearchResponse;
            Raw search response from mAP Core API. It has members `schemas`,
            `total_results`, `start_index`, `items_per_page`, and `resources`.

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

    if raw:
        return results

    group_summaries = [
        GroupSummary(
            id=t.cast("str", group.id),
            display_name=group.display_name,
            public=group.public,
            member_list_visibility=group.member_list_visibility,
            users_count=len(group.members) if group.members else 0,
        )
        for group in results.resources
    ]

    return SearchResult[GroupSummary](
        total=results.total_results,
        page_size=results.items_per_page,
        offset=results.start_index,
        resources=group_summaries,
    )


@t.overload
def get_by_id(group_id: str) -> GroupDetail | None: ...
@t.overload
def get_by_id(group_id: str, *, raw: t.Literal[True]) -> MapGroup | None: ...


def get_by_id(group_id: str, *, raw: bool = False) -> GroupDetail | MapGroup | None:
    """Get group from mAP Core API by group_id.

    Args:
        group_id (str): ID of the Group resource.
        raw (bool): If True, return raw MapGroup object. Defaults to False.

    Returns:
        object: The Group resource if found, otherwise None. The type depends
            on the `raw` argument.
        - GroupDetail: The Group detail object.
        - MapGroup: The raw Group object from mAP Core API.

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

    if raw:
        return result

    return GroupDetail.from_map_group(result)


def create(group: GroupDetail) -> GroupDetail:
    """Create group to mAP Core API.

    Args:
        group (GroupDetail):
            Detail information about the group created from the input data.

    Returns:
        GroupDetail: The created Group detail object.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        InvalidFormError: If failed to prepare MapGroup from GroupDetail.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    admins = get_system_admins()

    try:
        map_group = prepare_group(group, administrators=admins)

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

    except OAuthTokenError, CredentialsError, InvalidFormError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return GroupDetail.from_map_group(result)


def update(group: GroupDetail) -> GroupDetail:
    """Update group from mAP Core API by group_id.

    Args:
        group (GroupDetail):
            Detail information about the group update from the input data.

    Returns:
        GroupDetail: The updated Group detail object.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        ResourceNotFound: If the Group resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if config.MAP_CORE.update_strategy == "put":
        return update_put(group)

    validated = validate_group_to_map_group(group, mode="update")

    group_id = t.cast("str", group.id)
    current: GroupDetail | None = get_by_id(group_id)
    if current is None:
        error = f"'Group {group_id}' Not Found"
        raise ResourceNotFound(error)

    operations: list[PatchOperation[MapGroup]] = build_patch_operations(
        current.to_map_group(),
        validated,
        include={"display_name", "public", "description", "member_list_visibility"},
    )
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.patch_by_id(
            group_id,
            operations,
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


def update_put(group: GroupDetail) -> GroupDetail:
    """Update group from mAP Core API by group_id (replace with PUT).

    Args:
        group (GroupDetail):
            Detail information about the group update from the input data.

    Returns:
        GroupDetail: The updated Group detail object.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Group resource data is invalid.
        ResourceNotFound: If the Group resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if config.MAP_CORE.update_strategy == "patch":
        return update(group)

    validated = validate_group_to_map_group(group, mode="update")

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapGroup | MapError = groups.put_by_id(
            validated,
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
        if re.search(MAP_NOT_FOUND_PATTERN, result.detail):
            raise ResourceNotFound(result.detail)

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
        system_admins = get_system_admins()
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
