#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing users."""

import re
import typing as t

from http import HTTPStatus

import requests

from flask import current_app
from pydantic_core import ValidationError

from server.clients import users
from server.const import MAP_NOT_FOUND_PATTERN
from server.entities.map_error import MapError
from server.entities.user_detail import UserDetail
from server.exc import (
    CredentialsError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)

from .token import get_access_token, get_client_secret
from .utils import build_patch_operations


if t.TYPE_CHECKING:
    from server.entities.map_user import MapUser
    from server.entities.patch_request import PatchOperation


def get_by_id(user_id: str) -> UserDetail | None:
    """Get a User detail by its ID.

    Args:
        user_id (str): ID of the User detail.

    Returns:
        UserDetail: The User detail if found, otherwise None.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.get_by_id(
            user_id, access_token=access_token, client_secret=client_secret
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        return None

    return UserDetail.from_map_user(result)


def get_by_eppn(eppn: str) -> UserDetail | None:
    """Get a User detail by its eduPersonPrincipalName.

    Args:
        eppn (str): eduPersonPrincipalName of the User detail.

    Returns:
        UserDetail: The User detail if found, otherwise None.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.get_by_eppn(
            eppn, access_token=access_token, client_secret=client_secret
        )
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = "Access token is invalid or expired."
            raise OAuthTokenError(error) from exc

        if code == HTTPStatus.INTERNAL_SERVER_ERROR:
            error = "mAP Core API server error."
            raise UnexpectedResponseError(error) from exc

        error = "Failed to get User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        return None

    return UserDetail.from_map_user(result)


def create(user: UserDetail) -> UserDetail:
    """Create a User detail.

    Args:
       user (UserDetail): The User detail to create.

    Returns:
        UserDetail: The created User detail.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the User resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.post(
            user.to_map_user(),
            exclude={"meta"},
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

        error = "Failed to create User resource in mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return UserDetail.from_map_user(result)


def update(user: UserDetail) -> UserDetail:
    """Update a User resource.

    Args:
        user (UserDetail): The User resource to update.

    Returns:
        MapUser: The updated User resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the User resource data is invalid.
        ResourceNotFound: If the User resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    current: UserDetail | None = get_by_id(user.id)
    if current is None:
        error = f"'{user.id}' Not Found"
        raise ResourceNotFound(error)

    operations: list[PatchOperation[MapUser]] = build_patch_operations(
        current.to_map_user(),
        user.to_map_user(),
        exclude={"schemas", "meta"},
    )

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.patch_by_id(
            user.id,
            operations,
            exclude={"meta"},
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

        error = "Failed to update User resource in mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse User resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        if re.search(MAP_NOT_FOUND_PATTERN, result.detail):
            raise ResourceNotFound(result.detail)

        raise ResourceInvalid(result.detail)

    return UserDetail.from_map_user(result)
