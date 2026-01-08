#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Client for User resources of mAP Core API."""

import typing as t

from http import HTTPStatus

import requests

from pydantic import TypeAdapter

from server.config import config
from server.const import MAP_EXIST_EPPN_ENDPOINT, MAP_USERS_ENDPOINT
from server.entities.map_error import MapError
from server.entities.map_user import MapUser

from .utils import compute_signature, get_time_stamp


type GetMapUserResponse = MapUser | MapError


def get_by_id(
    user_id: str,
    /,
    include: t.Sequence[str] | None = None,
    exclude: t.Sequence[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> MapUser | None:
    """Get a User resource by its ID from mAP API.

    Args:
        user_id (str): ID of the User resource.
        include (Sequence[str] | None):
            Attribute names to include in the response. Optional.
        exclude (Sequence[str] | None):
            Attribute names to exclude from the response. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        MapUser: The User resource if found, otherwise None.
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
            alias_generator(name) for name in include
        ])
    if exclude:
        attributes_params[alias_generator("excludedAttributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.get(
        f"{config.MAP_CORE.base_url}{MAP_USERS_ENDPOINT}/{user_id}",
        params=auth_params | attributes_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    adapter: TypeAdapter[GetMapUserResponse] = TypeAdapter(GetMapUserResponse)
    result = adapter.validate_json(response.text)

    if isinstance(result, MapError):
        return None
    return result


def get_by_eppn(
    eppn: str,
    include: t.Sequence[str] | None = None,
    exclude: t.Sequence[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> MapUser | None:
    """Get a User resource by its ePPN from mAP API.

    Args:
        eppn (str): ePPN of the User resource.
        include (Sequence[str] | None):
            Attribute names to include in the response. Optional.
        exclude (Sequence[str] | None):
            Attribute names to exclude from the response. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        MapUser: The User resource if found, otherwise None.
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
            alias_generator(name) for name in include
        ])
    if exclude:
        attributes_params[alias_generator("excludedAttributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.get(
        f"{config.MAP_CORE.base_url}{MAP_EXIST_EPPN_ENDPOINT}/{eppn}",
        params=auth_params | attributes_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=config.MAP_CORE.timeout,
    )

    if response.status_code > HTTPStatus.BAD_REQUEST:
        response.raise_for_status()

    adapter: TypeAdapter[GetMapUserResponse] = TypeAdapter(GetMapUserResponse)
    result = adapter.validate_json(response.text, extra="ignore")

    if isinstance(result, MapError):
        return None
    return result


def post(
    user: MapUser,
    /,
    include: t.Sequence[str] | None = None,
    exclude: t.Sequence[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> MapUser:
    """Create a User resource in mAP API.

    Args:
        user (MapUser): The User resource to create.
        include (Sequence[str] | None):
            Attribute names to include in creation. Optional.
        exclude (Sequence[str] | None):
            Attribute names to exclude from creation. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        MapUser: The created User resource.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    payload = user.model_dump(
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
        attributes_params[alias_generator("excludedAttributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.post(
        f"{config.MAP_CORE.base_url}{MAP_USERS_ENDPOINT}",
        params=attributes_params,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={"request": auth_params} | payload,
        timeout=config.MAP_CORE.timeout,
    )
    response.raise_for_status()

    return MapUser.model_validate_json(response.text)


def put_by_id(
    user: MapUser,
    /,
    include: t.Sequence[str] | None = None,
    exclude: t.Sequence[str] | None = None,
    *,
    access_token: str,
    client_secret: str,
) -> MapUser:
    """Update a User resource by its ID in mAP API.

    Args:
        user (MapUser): The User resource to update.
        include (Sequence[str] | None):
            Attribute names to include in update. Optional.
        exclude (Sequence[str] | None):
            Attribute names to exclude from update. Optional.
        access_token (str): OAuth access token for authorization.
        client_secret (str): Client secret for Authentication.

    Returns:
        MapUser: The updated User resource.
    """
    time_stamp = get_time_stamp()
    signature = compute_signature(client_secret, access_token, time_stamp)
    auth_params = {
        "time_stamp": time_stamp,
        "signature": signature,
    }

    payload = user.model_dump(
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
        attributes_params[alias_generator("excludedAttributes")] = ",".join([
            alias_generator(name) for name in exclude
        ])

    response = requests.put(
        f"{config.MAP_CORE.base_url}{MAP_USERS_ENDPOINT}/{user.id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={"request": auth_params} | payload | attributes_params,
        timeout=config.MAP_CORE.timeout,
    )
    response.raise_for_status()

    return MapUser.model_validate_json(response.text)


def _get_alias_generator() -> t.Callable[[str], str]:
    generator = MapUser.model_config.get("alias_generator")
    if generator and not callable(generator):
        generator = generator.serialization_alias
    if generator is None:
        generator = lambda x: x  # noqa: E731

    return generator


alias_generator: t.Callable[[str], str] = _get_alias_generator()
del _get_alias_generator
