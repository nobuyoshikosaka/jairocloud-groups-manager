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
from server.config import config
from server.const import (
    MAP_ALREADY_TIED_PATTERN,
    MAP_DUPLICATE_ID_PATTERN,
    MAP_ILLEGAL_EPPN_PATTERN,
    MAP_NO_RIGHTS_APPEND_PATTERN,
    MAP_NO_RIGHTS_UPDATE_PATTERN,
    MAP_NOT_FOUND_PATTERN,
)
from server.entities.map_error import MapError
from server.entities.search_request import SearchResponse, SearchResult
from server.entities.summaries import UserSummary
from server.entities.user_detail import UserDetail
from server.exc import (
    ApiClientError,
    ApiRequestError,
    CredentialsError,
    InvalidFormError,
    InvalidQueryError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.messages import E, I
from server.signals import user_deleted, user_updated

from .token import get_access_token, get_client_secret
from .utils import (
    UsersCriteria,
    build_patch_operations,
    build_search_query,
    is_current_user_system_admin,
    make_criteria_object,
    prepare_user,
    validate_user_to_map_user,
)


if t.TYPE_CHECKING:
    from server.clients.users import UsersSearchResponse
    from server.entities.map_user import Group, MapUser
    from server.entities.patch_request import PatchOperation


@t.overload
def search(criteria: UsersCriteria) -> SearchResult[UserSummary]: ...
@t.overload
def search(
    criteria: UsersCriteria, *, raw: t.Literal[True]
) -> SearchResponse[MapUser]: ...


def search(
    criteria: UsersCriteria, *, raw: bool = False
) -> SearchResult[UserSummary] | SearchResponse[MapUser]:
    """Search for users based on given criteria.

    Args:
        criteria (UsersCriteria): Search criteria for filtering users.
        raw (bool):
            If True, return raw search response from mAP Core API. Defaults to False.

    Returns:
        object: Search results. The type depends on the `raw` argument.
        - SearchResult;
            Search result containing User summaries. It has members `total`,
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
        "user_name",
        "meta",
        "edu_person_principal_names",
        "emails",
        "groups",
    }

    query = build_search_query(criteria)
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        results: UsersSearchResponse = users.search(
            query,
            include=default_include,
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        current_app.logger.error(E.FAILED_SEARCH_USERS, {"filter": query.filter})
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(E.FAILED_SEARCH_USERS, {"filter": query.filter})
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(E.FAILED_SEARCH_USERS, {"filter": query.filter})
        error = E.FAILED_PARSE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(results, MapError):
        current_app.logger.error(E.FAILED_SEARCH_USERS, {"filter": query.filter})
        current_app.logger.error(
            E.RECEIVE_RESPONSE_MESSAGE, {"message": results.detail}
        )
        error = E.UNSUPPORTED_SEARCH_FILTER
        raise InvalidQueryError(error)

    if raw:
        return results

    return SearchResult(
        total=results.total_results,
        page_size=results.items_per_page,
        offset=results.start_index,
        resources=[UserSummary.from_map_user(result) for result in results.resources],
    )


@t.overload
def get_by_id(user_id: str, *, more_detail: bool = False) -> UserDetail | None: ...
@t.overload
def get_by_id(user_id: str, *, raw: t.Literal[True]) -> MapUser | None: ...


def get_by_id(
    user_id: str, *, raw: bool = False, more_detail: bool = False
) -> UserDetail | MapUser | None:
    """Get a User detail by its ID.

    Args:
        user_id (str): ID of the User detail.
        more_detail (bool):
            If True, include more detail such as groups and repositories name.
        raw (bool): If True, return raw MapUser object. Defaults to False.

    Returns:
        object: The User object if found, otherwise None. The type depends
            on the `raw` argument.
        - UserDetail: The User detail object.
        - MapUser: The raw User object from mAP Core API.

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
        current_app.logger.error(E.FAILED_GET_USER, {"id": user_id})
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(E.FAILED_GET_USER, {"id": user_id})
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(E.FAILED_GET_USER, {"id": user_id})
        error = E.FAILED_PARSE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.error(E.FAILED_GET_USER, {"id": user_id})
        current_app.logger.error(E.RECEIVE_RESPONSE_MESSAGE, {"message": result.detail})
        return None

    if raw:
        return result

    return UserDetail.from_map_user(result, more_detail=more_detail)


@t.overload
def get_by_eppn(eppn: str) -> UserDetail | None: ...
@t.overload
def get_by_eppn(eppn: str, *, raw: t.Literal[True]) -> MapUser | None: ...


def get_by_eppn(eppn: str, *, raw: bool = False) -> UserDetail | MapUser | None:
    """Get a User detail by its eduPersonPrincipalName.

    Args:
        eppn (str): eduPersonPrincipalName of the User detail.
        raw (bool): If True, return raw MapUser object. Defaults to False.

    Returns:
        object: The User object if found, otherwise None. The type depends
            on the `raw` argument.
        - UserDetail: The User detail object.
        - MapUser: The raw User object from mAP Core API.

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
        current_app.logger.error(E.FAILED_GET_USER_BY_EPPN, {"eppn": eppn})
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(E.FAILED_GET_USER_BY_EPPN, {"eppn": eppn})
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(E.FAILED_GET_USER_BY_EPPN, {"eppn": eppn})
        error = E.FAILED_PARSE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.error(E.FAILED_GET_USER_BY_EPPN, {"eppn": eppn})
        current_app.logger.error(E.RECEIVE_RESPONSE_MESSAGE, {"message": result.detail})
        return None

    if raw:
        return result

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
        InvalidFormError: If the form data to create is invalid.
        ResourceInvalid: If the User resource is invalid despite passing validation.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    primary_eppn = user.eppns[0] if user.eppns else "N/A"
    try:
        map_user = prepare_user(user)

        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.post(
            map_user,
            exclude={"meta"},
            access_token=access_token,
            client_secret=client_secret,
        )

    except requests.HTTPError as exc:
        current_app.logger.error(E.FAILED_CREATE_USER, {"eppn": primary_eppn})
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.FAILED_CREATE_USER
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(E.FAILED_CREATE_USER, {"eppn": primary_eppn})
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(E.FAILED_CREATE_USER, {"eppn": primary_eppn})
        error = E.FAILED_PARSE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError, InvalidFormError:
        raise

    if isinstance(result, MapError):
        current_app.logger.error(E.FAILED_CREATE_USER, {"eppn": primary_eppn})
        current_app.logger.error(E.RECEIVE_RESPONSE_MESSAGE, {"message": result.detail})
        if m := re.search(MAP_DUPLICATE_ID_PATTERN, result.detail):
            error = E.USER_DUPLICATE_ID % {"id": m.group(1)}
            raise ResourceInvalid(error)
        if m := re.search(MAP_ALREADY_TIED_PATTERN, result.detail):
            error = E.USER_ALREADY_TIED_EPPN % {"eppn": m.group(1)}
            raise ResourceInvalid(error)
        if m := re.search(MAP_ILLEGAL_EPPN_PATTERN, result.detail):
            error = E.USER_EPPN_ILLEGAL % {"eppn": m.group(1)}
            raise ResourceInvalid(error)

        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error)

    current_app.logger.info(
        I.SUCCESS_CREATE_USER, {"id": result.id, "eppn": primary_eppn}
    )
    return UserDetail.from_map_user(result)


def update(user: UserDetail) -> UserDetail:  # noqa: C901
    """Update a User resource.

    Args:
        user (UserDetail): The User resource to update.

    Returns:
        UserDetail: The updated User resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        InvalidFormError: If the form data to update is invalid.
        ResourceInvalid: If the User resource data is invalid.
        ResourceNotFound: If the User resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if not config.MAP_CORE.user_editable:
        return update_affiliations(user)

    if config.MAP_CORE.update_strategy == "put":
        return update_put(user)

    user_id = t.cast("str", user.id)
    current: UserDetail | None = get_by_id(user_id)
    if current is None:
        error = E.USER_NOT_FOUND % {"id": user_id}
        raise ResourceNotFound(error)

    if not is_current_user_system_admin() and current.is_system_admin:
        error = E.USER_NO_UPDATE_SYSTEM_ADMIN
        raise InvalidFormError(error)
    # promotion permission will be checked in validation process.

    primary_eppn = user.eppns[0] if user.eppns else "N/A"
    try:
        validated = validate_user_to_map_user(user, mode="update")

        operations: list[PatchOperation[MapUser]] = build_patch_operations(
            current.to_map_user(),
            validated,
            exclude={"schemas", "meta"},
        )

        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.patch_by_id(
            user_id,
            operations,
            exclude={"meta"},
            access_token=access_token,
            client_secret=client_secret,
        )

    except requests.HTTPError as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user_id, "eppn": primary_eppn}
        )
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.FAILED_UPDATE_USER
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user_id, "eppn": primary_eppn}
        )
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user_id, "eppn": primary_eppn}
        )
        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user_id, "eppn": primary_eppn}
        )
        current_app.logger.error(E.RECEIVE_RESPONSE_MESSAGE, {"message": result.detail})
        if m := re.search(MAP_NOT_FOUND_PATTERN, result.detail):
            error = E.USER_NOT_FOUND % {"id": m.group(1)}
            raise ResourceNotFound(error)
        if re.search(MAP_NO_RIGHTS_UPDATE_PATTERN, result.detail):
            error = E.NO_RIGHTS_UPDATE_USER % {"id": user_id}
            raise OAuthTokenError(error)

        raise ResourceInvalid(result.detail)

    current_app.logger.info(
        I.SUCCESS_UPDATE_USER, {"id": user_id, "eppn": primary_eppn}
    )
    return UserDetail.from_map_user(result)


def update_put(user: UserDetail) -> UserDetail:  # noqa: C901
    """Update a User resource using PUT method.

    Args:
        user (UserDetail): The User resource to update.

    Returns:
        UserDetail: The updated User resource.

    Raises:
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        InvalidFormError: If the form data to update is invalid.
        ResourceInvalid: If the User resource is invalid despite passing validation.
        ResourceNotFound: If the User resource is not found.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    if not config.MAP_CORE.user_editable:
        return update_affiliations(user)

    if config.MAP_CORE.update_strategy == "patch":
        return update(user)

    user_id = t.cast("str", user.id)
    current: UserDetail | None = get_by_id(user_id)
    if current is None:
        error = E.USER_NOT_FOUND % {"id": user_id}
        raise ResourceNotFound(error)

    if not is_current_user_system_admin() and current.is_system_admin:
        error = E.USER_NO_UPDATE_SYSTEM_ADMIN
        raise InvalidFormError(error)

    primary_eppn = user.eppns[0] if user.eppns else "N/A"
    try:
        validated = validate_user_to_map_user(user, mode="update")

        access_token = get_access_token()
        client_secret = get_client_secret()
        result: MapUser | MapError = users.put_by_id(
            validated,
            exclude={"external_id", "meta"},
            access_token=access_token,
            client_secret=client_secret,
        )

    except requests.HTTPError as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user.id, "eppn": primary_eppn}
        )
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.FAILED_UPDATE_USER
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user.id, "eppn": primary_eppn}
        )
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user.id, "eppn": primary_eppn}
        )
        error = E.FAILED_PARSE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(result, MapError):
        current_app.logger.error(
            E.FAILED_UPDATE_USER, {"id": user.id, "eppn": primary_eppn}
        )
        current_app.logger.error(E.RECEIVE_RESPONSE_MESSAGE, {"message": result.detail})
        if m := re.search(MAP_NOT_FOUND_PATTERN, result.detail):
            error = E.USER_NOT_FOUND % {"id": m.group(1)}
            raise ResourceNotFound(error)
        if re.search(MAP_NO_RIGHTS_UPDATE_PATTERN, result.detail) or re.search(
            MAP_NO_RIGHTS_APPEND_PATTERN, result.detail
        ):
            error = E.NO_RIGHTS_UPDATE_USER % {"id": user.id}
            raise OAuthTokenError(error)

        raise ResourceInvalid(result.detail)

    current_app.logger.info(
        I.SUCCESS_UPDATE_USER, {"id": user.id, "eppn": primary_eppn}
    )
    return UserDetail.from_map_user(result)


def update_affiliations(user: UserDetail) -> UserDetail:
    """Update a User's affiliations with groups and repositories.

    Args:
        user (UserDetail): The User resource to update.

    Returns:
        UserDetail: The updated User detail.

    Raises:
        ResourceNotFound: If the User resource is not found.
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        ExceptionGroup: If there are multiple errors while updating affiliations.
    """
    user_id = t.cast("str", user.id)
    current: UserDetail | None = get_by_id(user_id)
    if current is None:
        error = E.USER_NOT_FOUND % {"id": user_id}
        raise ResourceNotFound(error)

    validated = validate_user_to_map_user(user, mode="update")
    operations: list[PatchOperation[MapUser]] = build_patch_operations(
        current.to_map_user(),
        validated,
        include={"groups"},
    )

    from . import groups  # noqa: PLC0415

    primary_eppn = user.eppns[0] if user.eppns else "N/A"
    errors: list[Exception] = []
    for op in operations:
        if op.op == "replace":
            continue
        if op.op == "add":
            group_id = t.cast("Group", op.value).value
        elif match := re.search(r'groups\[value eq "(.*?)"\]', op.path):
            group_id = match.group(1)
        else:
            continue

        try:
            groups.update_member(group_id, **{op.op: {user_id}})

        except OAuthTokenError, CredentialsError:
            raise
        except (ApiClientError, ApiRequestError) as exc:
            errors.append(exc)

    user_updated.send(None, user=user)

    if errors:
        error = E.FAILED_UPDATE_USER_AFFILIATIONS % {
            "id": user_id,
            "eppn": primary_eppn,
        }
        raise ExceptionGroup(error, errors)

    current_app.logger.info(
        I.SUCCESS_UPDATE_USER_AFFILIATIONS, {"id": user_id, "eppn": primary_eppn}
    )
    return t.cast("UserDetail", get_by_id(user_id))


@t.overload
def get_system_admins() -> set[str]: ...
@t.overload
def get_system_admins(*, raw: t.Literal[True]) -> list[MapUser]: ...


def get_system_admins(*, raw: bool = False) -> set[str] | list[MapUser]:
    """Get system administrators.

    Args:
        raw (bool): If True, return raw MapUser objects. Defaults to False.

    Returns:
        list: The list of system administrators. The type of items depends on
            the `raw` argument.
        - str: The IDs of the system administrators.
        - MapUser: The raw User objects of system administrators from mAP Core API.
    """
    criteria = make_criteria_object("users", a=[0], super=True)
    try:
        result = search(criteria, raw=True)
    finally:
        current_app.logger.info(I.SEARCHED_SYSTEM_ADMINS)

    if raw:
        return result.resources

    return {t.cast("str", user.id) for user in result.resources}


def count(criteria: UsersCriteria) -> int:
    """Search for users based on given criteria.

    Args:
        criteria (UsersCriteria): Search criteria for filtering users.

    Returns:
        int: The count of users matching the given criteria.

    Raises:
        InvalidQueryError: If the query construction is invalid.
        OAuthTokenError: If the access token is invalid or expired.
        CredentialsError: If the client credentials are invalid.
        UnexpectedResponseError: If response from mAP Core API is unexpected.
    """
    criteria.l = 0
    query = build_search_query(criteria)
    try:
        access_token = get_access_token()
        client_secret = get_client_secret()
        results: UsersSearchResponse = users.search(
            query,
            include={"id"},
            access_token=access_token,
            client_secret=client_secret,
        )
    except requests.HTTPError as exc:
        current_app.logger.error(E.FAILED_COUNT_USERS, {"filter": query.filter})
        code = exc.response.status_code
        if code == HTTPStatus.UNAUTHORIZED:
            error = E.ACCESS_TOKEN_NOT_AVAILABLE
            raise OAuthTokenError(error) from exc

        error = E.RECEIVE_UNEXPECTED_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except requests.RequestException as exc:
        current_app.logger.error(E.FAILED_COUNT_USERS, {"filter": query.filter})
        error = E.FAILED_COMMUNICATE_API
        raise UnexpectedResponseError(error) from exc

    except ValidationError as exc:
        current_app.logger.error(E.FAILED_COUNT_USERS, {"filter": query.filter})
        error = E.FAILED_DECODE_RESPONSE
        raise UnexpectedResponseError(error) from exc

    except OAuthTokenError, CredentialsError:
        raise

    if isinstance(results, MapError):
        current_app.logger.error(E.FAILED_COUNT_USERS, {"filter": query.filter})
        current_app.logger.error(
            E.RECEIVE_RESPONSE_MESSAGE, {"message": results.detail}
        )
        raise InvalidQueryError(results.detail)

    return results.total_results


@user_updated.connect
@user_deleted.connect
def handle_user_updated(
    _sender: object,
    user: UserDetail | None = None,
    **kwargs,  # noqa: ANN003, ARG001
) -> None:
    """Handle user_updated signal to clear cache of the updated user.

    Args:
        sender: The sender of the signal.
        user (UserDetail): The updated User resource.
        **kwargs: Other keyword arguments passed with the signal.
    """
    if not isinstance(user, UserDetail):
        return
    users.get_by_id.clear_cache(user.id)  # pyright: ignore[reportFunctionMemberAccess]
    if user.eppns:
        users.get_by_eppn.clear_cache(*user.eppns)  # pyright: ignore[reportFunctionMemberAccess]
