#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing repositories."""

import re
import typing as t

from http import HTTPStatus

import requests

from flask import current_app
from pydantic_core import ValidationError

from server.clients import services
from server.const import MAP_NOT_FOUND_PATTERN
from server.entities.map_error import MapError
from server.entities.patch_request import PatchOperation
from server.entities.repository import RepositoryDetail
from server.exc import (
    CredentialsError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)

from .token import get_access_token, get_client_secret


if t.TYPE_CHECKING:
    from server.entities.map_service import MapService


def get_by_id(service_id: str) -> RepositoryDetail | None:
    """Get a Repository resource by its ID.

    Args:
        service_id (str): ID of the Repository resource.

    Returns:
        RepositoryDetail: The Repository resource if found, otherwise None.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapService | MapError = services.get_by_id(
            service_id,
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

        error = "Failed to get Repository resource from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to connect to mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse response from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        return None

    return RepositoryDetail.from_map_service(result)


def create(repository: RepositoryDetail) -> RepositoryDetail:
    """Create a new Repository resource.

    Args:
        repository (RepositoryDetail): The Repository resource to create.

    Returns:
        RepositoryDetail: The created Repository resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Repository resource data is invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapService | MapError = services.post(
            repository.to_map_service(),
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

        error = "Failed to create Repository resource in mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to connect to mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse response from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return RepositoryDetail.from_map_service(result)


def update(repository: RepositoryDetail) -> RepositoryDetail:
    """Update an existing Repository resource.

    Args:
        repository (RepositoryDetail): The Repository resource to update.

    Returns:
        RepositoryDetail: The updated Repository resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceInvalid: If the Repository resource data is invalid.
        ResourceNotFound: If the Repository resource does not exist.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()

        operations: list[PatchOperation] = [
            # Create patch operations for all updatable fields.
        ]
        result: MapService | MapError = services.patch_by_id(
            repository.id,
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

        error = "Failed to update Repository resource in mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to connect to mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse response from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        if re.search(MAP_NOT_FOUND_PATTERN, result.detail):
            raise ResourceNotFound(result.detail)

        raise ResourceInvalid(result.detail)

    return RepositoryDetail.from_map_service(result)
