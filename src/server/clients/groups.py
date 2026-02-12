#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Client for Group resources of mAP Core API."""

import typing as t

from http import HTTPStatus

import requests

from pydantic import TypeAdapter

from server.config import config
from server.const import MAP_GROUPS_ENDPOINT
from server.entities.map_error import MapError
from server.entities.map_group import MapGroup
from server.entities.patch_request import PatchOperation, PatchRequestPayload
from server.entities.search_request import SearchRequestParameter, SearchResponse

from .decoraters import cache_resource
from .utils import compute_signature, get_time_stamp


type GetMapGroupResponse = MapGroup | MapError
"""Type alias for response of getting a MapGroup."""
adapter: TypeAdapter[GetMapGroupResponse] = TypeAdapter(GetMapGroupResponse)


type GroupsSearchResponse = SearchResponse[MapGroup] | MapError
"""Type alias for search response containing MapGroup resources."""
adapter_search: TypeAdapter[GroupsSearchResponse] = TypeAdapter(GroupsSearchResponse)


def search(
    query: SearchRequestParameter,
    /,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> GroupsSearchResponse:
    """Search for Group resources in mAP API.

    Args:
        query (SearchRequestParameter): The search query parameters.
        include (set[str] | None):
            Attribute names to include in the response. Optional.
        exclude (set[str] | None):
            Attribute names to exclude from the response. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Basic Authentication.

    Returns:
        GroupsSearchResponse: The search response containing Group resources.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    attributes_params: dict[str, str] = {}
    if include:
        attributes_params[alias_generator("attributes")] = ",".join([
            alias_generator(name) for name in include | {"id"}
        ])
    if exclude:
        attributes_params[alias_generator("excludeAttributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    query_params = query.model_dump(
        mode="json",
        by_alias=True,
    )

    response = requests.get(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}",
        params=auth_params | attributes_params | query_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=config.MAP_CORE.timeout,
    )
    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    return adapter_search.validate_json(response.text, extra="ignore")


@cache_resource
def get_by_id(
    group_id: str,
    /,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> GetMapGroupResponse:
    """Get a Group resource by its ID from mAP API.

    Args:
        group_id (str): ID of the Group resource.
        include (set[str] | None):
            Attribute names to include in the response. Optional.
        exclude (set[str] | None):
            Attribute names to exclude from the response. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        GetMapGroupResponse: The Group resource if found, otherwise Error response.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    attributes_params: dict[str, str] = {}
    if include:
        attributes_params[alias_generator("attributes")] = ",".join([
            alias_generator(name) for name in include | {"id"}
        ])
    if exclude:
        attributes_params[alias_generator("excluded_attributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.get(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}/{group_id}",
        params=auth_params | attributes_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    return adapter.validate_json(response.text)


def post(
    group: MapGroup,
    /,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> GetMapGroupResponse:
    """Create a Group resource in mAP API.

    Args:
        group (MapGroup): The Group resource to create.
        include (set[str] | None):
            Attribute names to include in creation. Optional.
        exclude (set[str] | None):
            Attribute names to exclude from creation. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        GetMapGroupResponse:
            The created Group resource if successful, otherwise Error response.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    payload = group.model_dump(
        mode="json",
        exclude=set(exclude or ()),
        by_alias=True,
        exclude_unset=True,
    )

    attributes_params: dict[str, str] = {}
    if include:
        attributes_params[alias_generator("attributes")] = ",".join([
            alias_generator(name) for name in include
        ])
    if exclude:
        attributes_params[alias_generator("excluded_attributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.post(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}",
        params=attributes_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={"request": auth_params} | payload,
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    return adapter.validate_json(response.text)


def put_by_id(
    group: MapGroup,
    /,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> GetMapGroupResponse:
    """Update a Group resource by its ID in mAP API.

    Args:
        group (MapGroup): The Group resource to update.
        include (set[str] | None):
            Attribute names to include in update. Optional.
        exclude (set[str] | None):
            Attribute names to exclude from update. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        GetMapGroupResponse:
            The updated Group resource if successful, otherwise Error response.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    payload = group.model_dump(
        mode="json",
        exclude=set(exclude or ()),
        by_alias=True,
        exclude_unset=True,
    )

    attributes_params: dict[str, str] = {}
    if include:
        attributes_params[alias_generator("attributes")] = ",".join([
            alias_generator(name) for name in include
        ])
    if exclude:
        attributes_params[alias_generator("excluded_attributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.put(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}/{group.id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={"request": auth_params} | payload | attributes_params,
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    resource = adapter.validate_json(response.text)

    if isinstance(resource, MapGroup):
        get_by_id.clear_cache(resource.id)  # pyright: ignore[reportFunctionMemberAccess]

    return resource


def patch_by_id(
    group_id: str,
    operations: list[PatchOperation],
    /,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> GetMapGroupResponse:
    """Patch a Group resource by its ID in mAP API.

    Args:
        group_id (str): ID of the Group resource.
        operations (list[PatchOperation]): List of patch operations to apply.
        include (set[str] | None):
            Attribute names to include in update. Optional.
        exclude (set[str] | None):
            Attribute names to exclude from update. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Basic Authentication.

    Returns:
        GetMapGroupResponse:
            The updated Group resource if successful, otherwise Error response.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    payload = PatchRequestPayload(operations=operations).model_dump(
        mode="json",
        by_alias=True,
        exclude_unset=False,
    )

    attributes_params: dict[str, str] = {}
    if include:
        attributes_params[alias_generator("attributes")] = ",".join([
            alias_generator(name) for name in include
        ])
    if exclude:
        attributes_params[alias_generator("excluded_attributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.patch(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}/{group_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={"request": auth_params} | payload | attributes_params,
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    resource = adapter.validate_json(response.text)

    if isinstance(resource, MapGroup):
        get_by_id.clear_cache(resource.id)  # pyright: ignore[reportFunctionMemberAccess]

    return resource


def delete_by_id(
    group_id: str,
    *,
    access_token: str,
    client_secret: str,
) -> MapError | None:
    """Delete a Group resource by its ID in mAP API.

    Args:
        group_id (str): ID of the Group resource.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Basic Authentication.

    Returns:
        MapError:
            The None if successful, otherwise Error response.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    response = requests.delete(
        f"{config.MAP_CORE.base_url}{MAP_GROUPS_ENDPOINT}/{group_id}",
        params=auth_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    if not response.text:
        get_by_id.clear_cache(group_id)  # pyright: ignore[reportFunctionMemberAccess]
        return None

    return MapError.model_validate_json(response.text)


def _get_alias_generator() -> t.Callable[[str], str]:
    generator = MapGroup.model_config.get("alias_generator")
    if generator and not callable(generator):
        generator = generator.serialization_alias
    if generator is None:
        generator = lambda x: x  # noqa: E731

    return generator


alias_generator: t.Callable[[str], str] = _get_alias_generator()
del _get_alias_generator
