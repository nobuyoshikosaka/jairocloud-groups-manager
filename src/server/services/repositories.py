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

from server.clients import groups, services
from server.config import config
from server.const import MAP_NOT_FOUND_PATTERN
from server.entities.map_error import MapError
from server.entities.repository_detail import RepositoryDetail
from server.entities.search_request import SearchResponse, SearchResult
from server.entities.summaries import RepositorySummary
from server.exc import (
    CredentialsError,
    InvalidFormError,
    InvalidQueryError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    SystemAdminNotFound,
    UnexpectedResponseError,
)

from .token import get_access_token, get_client_secret
from .users import get_system_admins
from .utils import (
    RepositoriesCriteria,
    build_patch_operations,
    build_search_query,
    prepare_role_groups,
    prepare_service,
    resolve_repository_id,
    resolve_service_id,
    validate_repository_to_map_service,
)


if t.TYPE_CHECKING:
    from server.clients.services import ServicesSearchResponse
    from server.entities.map_service import MapService
    from server.entities.patch_request import PatchOperation


@t.overload
def search(criteria: RepositoriesCriteria) -> SearchResult[RepositorySummary]: ...
@t.overload
def search(
    criteria: RepositoriesCriteria, *, raw: t.Literal[True]
) -> SearchResponse[MapService]: ...


def search(
    criteria: RepositoriesCriteria, *, raw: bool = False
) -> SearchResult[RepositorySummary] | SearchResponse[MapService]:
    """Search for repositories based on given criteria.

    Args:
        criteria (RepositoriesCriteria): Search criteria for filtering repositories.
        raw (bool):
            If True, return raw search response from mAP Core API. Defaults to False.

    Returns:
        object: Search results. The type depends on the `raw` argument.
        - SearchResult;
            Search result containing Repository summaries. It has members `total`,
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
    default_include = {"id", "service_name", "service_url", "entity_ids"}

    try:
        query = build_search_query(criteria)
        access_token = get_access_token()
        client_secret = get_client_secret()
        results: ServicesSearchResponse = services.search(
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

        error = "Failed to search Repository resources from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to communicate with mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse Repository resources from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except InvalidQueryError, OAuthTokenError, CredentialsError:
        raise

    if isinstance(results, MapError):
        current_app.logger.info(results.detail)
        raise InvalidQueryError(results.detail)

    if raw:
        return results

    repository_summaries = [
        RepositorySummary(
            id=resolve_repository_id(service_id=result.id),
            service_name=result.service_name,
            service_url=result.service_url,
            service_id=result.id,
            entity_ids=[eid.value for eid in result.entity_ids or []],
        )
        for result in results.resources
    ]

    return SearchResult(
        total=results.total_results,
        page_size=results.items_per_page,
        offset=results.start_index,
        resources=repository_summaries,
    )


@t.overload
def get_by_id(
    repository_id: str, *, more_detail: bool = False
) -> RepositoryDetail | None: ...
@t.overload
def get_by_id(repository_id: str, *, raw: t.Literal[True]) -> MapService | None: ...


def get_by_id(
    repository_id: str, *, raw: bool = False, more_detail: bool = False
) -> RepositoryDetail | MapService | None:
    """Get a Repository resource by its ID.

    Args:
        repository_id (str): ID of the Repository resource.
        more_detail (bool):
            If True, include more details such as groups and users count.
        raw (bool): If True, return raw MapService object. Defaults to False.

    Returns:
        object: The Repository resource if found, otherwise None. The type depends
            on the `raw` argument.
        - RepositoryDetail: The Repository detail object.
        - MapService: The raw Repository object from mAP Core API.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    service_id = resolve_service_id(repository_id=repository_id)
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

    if raw:
        return result

    return RepositoryDetail.from_map_service(result, more_detail=more_detail)


def create(repository: RepositoryDetail) -> RepositoryDetail:
    """Create a new Repository resource.

    Args:
        repository (RepositoryDetail): The Repository resource to create.

    Returns:
        RepositoryDetail: The created Repository resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        InvalidFormError: If failed to validate repository form data for creation.
        ResourceInvalid: If the Repository resource data is invalid.
        SystemAdminNotFound: If no system administrators are found in the system.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    admins = get_system_admins()

    role_groups = prepare_role_groups(
        t.cast("str", repository.id), t.cast("str", repository.service_name), admins
    )
    try:
        service = prepare_service(repository, admins)

        access_token = get_access_token()
        client_secret = get_client_secret()
        role_groups = [
            groups.post(group, access_token=access_token, client_secret=client_secret)
            for group in role_groups
        ]

        result: MapService | MapError = services.post(
            service,
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

    except OAuthTokenError, CredentialsError, InvalidFormError, SystemAdminNotFound:
        raise

    if isinstance(result, MapError):
        current_app.logger.info(result.detail)
        raise ResourceInvalid(result.detail)

    return RepositoryDetail.from_map_service(result)


def update(repository: RepositoryDetail) -> RepositoryDetail:  # noqa: C901
    """Update an existing Repository resource.

    Args:
        repository (RepositoryDetail):
            The Repository data to update. The `id` field is required.

    Returns:
        RepositoryDetail: The updated Repository resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        InvalidFormError: If failed to validate repository form data for update.
        ResourceInvalid: If the Repository resource data is invalid.
        ResourceNotFound: If the Repository resource does not exist.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if config.MAP_CORE.update_strategy == "put":
        return update_put(repository)

    validated = validate_repository_to_map_service(repository)

    repository_id = t.cast("str", repository.id)
    service_id = t.cast("str", validated.id)
    current = get_by_id(repository_id)
    if current is None:
        error = f"Repository '{repository_id}' Not Found"
        raise ResourceNotFound(error)

    if validated.service_url and validated.service_url != current.service_url:
        error = "Service URL could not be updated."
        raise InvalidFormError(error)

    operations: list[PatchOperation[MapService]] = build_patch_operations(
        current.to_map_service(),
        validated,
        include={"service_name", "suspended", "entity_ids"},
    )
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapService | MapError = services.patch_by_id(
            service_id,
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


def update_put(repository: RepositoryDetail) -> RepositoryDetail:  # noqa: C901
    """Update an existing Repository resource (replace with PUT).

    Args:
        repository (RepositoryDetail):
            The Repository data to update. The `id` field is required.


    Returns:
        RepositoryDetail: The updated Repository resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        InvalidFormError: If failed to validate repository form data for update.
        ResourceInvalid: If the Repository resource data is invalid.
        ResourceNotFound: If the Repository resource does not exist.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if config.MAP_CORE.update_strategy == "patch":
        return update(repository)

    validated = validate_repository_to_map_service(repository)

    repository_id = t.cast("str", repository.id)
    current = get_by_id(repository_id)
    if current is None:
        error = f"Repository '{repository_id}' Not Found"
        raise ResourceNotFound(error)

    if validated.service_url and validated.service_url != current.service_url:
        error = "Service URL could not be updated."
        raise InvalidFormError(error)

    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapService | MapError = services.put_by_id(
            validated,
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


def delete_by_id(repository_id: str) -> None:
    """Delete a Repository resource by its ID.

    Args:
        repository_id (str): ID of the Repository resource to delete.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ResourceNotFound: If the Repository resource does not exist.
        ResourceInvalid: If the Repository resource cannot be deleted.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    service_id = resolve_service_id(repository_id=repository_id)
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapError | None = services.delete_by_id(
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

        error = "Failed to delete Repository resource in mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        error = "Failed to connect to mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        error = "Failed to parse response from mAP Core API."
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if result is None:
        return

    if re.search(MAP_NOT_FOUND_PATTERN, result.detail):
        raise ResourceNotFound(result.detail)

    raise ResourceInvalid(result.detail)
