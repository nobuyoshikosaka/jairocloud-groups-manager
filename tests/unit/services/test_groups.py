import typing as t

from unittest.mock import patch

import pytest
import requests

from flask import Flask
from pydantic_core import ValidationError
from pytest_mock import MockerFixture
from requests.models import Response

from server.entities.bulk_request import BulkOperation, BulkResponse
from server.entities.group_detail import GroupDetail
from server.entities.map_error import MapError
from server.entities.map_group import Administrator, MapGroup, Member, MemberGroup, MemberUser, Service
from server.entities.search_request import SearchRequestParameter, SearchResponse, SearchResult
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
from server.services import groups
from server.services.utils.search_queries import GroupsCriteria, make_criteria_object
from tests.helpers import UnexpectedError


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture

    from server.config import RuntimeConfig


def test_search_with_empty_criteria(gen_group_id, mocker: MockerFixture) -> None:
    """Test group search with empty criteria (all fields None or empty)."""

    empty_criteria: GroupsCriteria = make_criteria_object("groups")
    expected_result = SearchResult[GroupSummary](
        total=1,
        page_size=30,
        offset=1,
        resources=[
            GroupSummary(
                id=gen_group_id("g1"),
                display_name="TestGroup",
                public=True,
                member_list_visibility="Public",
                users_count=0,
            )
        ],
    )
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    build_query_mock = mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    resources = [
        MapGroup(
            id=gen_group_id("g1"),
            display_name="TestGroup",
            public=True,
            member_list_visibility="Public",
        )
    ]
    mock_groups_search.return_value = SearchResponse[MapGroup](
        total_results=1,
        items_per_page=30,
        start_index=1,
        resources=resources,
    )

    result = groups.search(empty_criteria)

    build_query_mock.assert_called_once_with(empty_criteria)
    assert result == expected_result
    assert build_query_mock.return_value is mock_groups_search.call_args[0][0]


def test_search_with_criteria(gen_group_id, mocker: MockerFixture) -> None:
    """Test group search with arbitrary criteria."""
    criteria: GroupsCriteria = make_criteria_object(
        "groups", q="Test", r=["repo1"], u=["user1"], s=0, v=1, k="display_name", d="asc", p=2, l=10
    )
    expected_result = SearchResult[GroupSummary](
        total=1,
        page_size=10,
        offset=11,
        resources=[
            GroupSummary(
                id=gen_group_id("g2"),
                display_name="TestGroup2",
                public=False,
                member_list_visibility="Private",
                users_count=0,
            )
        ],
    )
    query_param = SearchRequestParameter(
        filter='displayName co "Test"',
        start_index=11,
        count=10,
        sort_by="display_name",
        sort_order="ascending",
    )
    build_query_mock = mocker.patch("server.services.groups.build_search_query", return_value=query_param)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    resources = [
        MapGroup(id=gen_group_id("g2"), display_name="TestGroup2", public=False, member_list_visibility="Private")
    ]
    mock_groups_search.return_value = SearchResponse[MapGroup](
        total_results=1, items_per_page=10, start_index=11, resources=resources
    )

    result = groups.search(criteria)

    build_query_mock.assert_called_once_with(criteria)
    assert build_query_mock.return_value.filter.startswith('displayName co "Test"')
    assert result == expected_result
    assert build_query_mock.return_value is mock_groups_search.call_args[0][0]


def test_search_raises_oauth_token_error_401(mocker: MockerFixture) -> None:
    """Test group search raises OAuthTokenError with status 401 and correct message."""
    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(
        filter="", start_index=1, count=30, sort_by=None, sort_order="descending"
    )
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_groups_search.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "Access token is invalid or expired."
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_unexpected_response_error_403(mocker: MockerFixture) -> None:
    """Test group search raises UnexpectedResponseError with status 403 and correct message."""
    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_groups_search.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "Failed to search Group resources from mAP Core API."
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_unexpected_response_error_500(mocker: MockerFixture) -> None:
    """Test group search raises UnexpectedResponseError with status 500 and correct message."""
    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_groups_search.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "mAP Core API server error."
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_unexpected_response_error_request_exception(mocker: MockerFixture) -> None:
    """Test group search raises UnexpectedResponseError on RequestException with correct message."""
    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Test group search raises UnexpectedResponseError with correct message when ValidationError occurs."""
    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "Failed to parse Group resources from mAP Core API."
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_invalid_query_error(mocker: MockerFixture) -> None:
    """Test group search raises InvalidQueryError and it is propagated as is."""

    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = InvalidQueryError("invalid query")

    with pytest.raises(InvalidQueryError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "invalid query"
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_oauth_token_error_propagation(mocker: MockerFixture) -> None:
    """Test group search raises OAuthTokenError and it is propagated as is."""

    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "token error"
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_credentials_error_propagation(mocker: MockerFixture) -> None:
    """Test group search raises CredentialsError and it is propagated as is."""

    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "credentials error"
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_search_raises_unexpected_exception_propagation(mocker: MockerFixture) -> None:
    """Test group search raises an unexpected Exception and it is propagated as is."""

    criteria: GroupsCriteria = make_criteria_object("groups")
    return_value_query = SearchRequestParameter(filter="", start_index=1, count=30, sort_by=None, sort_order=None)
    mocker.patch("server.services.groups.build_search_query", return_value=return_value_query)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    mock_groups_search.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.search(criteria)

    assert str(exc_info.value) == "unexpected error"
    assert mock_groups_search.call_args[0][0] is return_value_query


def test_create_with_empty_group_info(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation with empty group info sets sysadmin as member and administrator."""
    sysadmin_id: str = "sysadmin"
    service_name: str = "jairocloud-groups-manager_dev"
    expected_group = GroupDetail(
        id=gen_group_id("g1"),
        display_name="",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    expected_map_group = MapGroup(
        id=gen_group_id("g1"),
        display_name="",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
        administrators=[Administrator(value=sysadmin_id)],
        services=[Service(value=service_name)],
    )
    empty_group_info: GroupDetail = GroupDetail(id="", display_name="")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.return_value = MapGroup(
        id=gen_group_id("g1"),
        display_name="",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
        administrators=[Administrator(value=sysadmin_id)],
        services=[Service(value=service_name)],
    )

    result = groups.create(empty_group_info)

    created_group: MapGroup = mock_post.return_value
    mock_post.assert_called_once()
    assert result.model_dump() == expected_group.model_dump()
    assert created_group == expected_map_group


def test_create_with_arbitrary_group_info(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation with arbitrary group info sets sysadmin as member and administrator, and service name."""
    sysadmin_id: str = "sysadmin"
    service_name: str = "jairocloud-groups-manager_dev"
    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g2"),
        display_name="ArbitraryGroup",
        user_defined_id="arb001",
        description="A test group for arbitrary info.",
        public=False,
        member_list_visibility="Private",
        repository=None,
        created=None,
        last_modified=None,
        users_count=5,
    )
    expected_group = GroupDetail(
        id=gen_group_id("g2"),
        display_name="ArbitraryGroup",
        user_defined_id=None,
        description=None,
        public=False,
        member_list_visibility="Private",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    expected_map_group = MapGroup(
        id=gen_group_id("g2"),
        display_name="ArbitraryGroup",
        public=False,
        member_list_visibility="Private",
        members=[MemberUser(type="User", value=sysadmin_id)],
        administrators=[Administrator(value=sysadmin_id)],
        services=[Service(value=service_name)],
    )

    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.return_value = MapGroup(
        id=gen_group_id("g2"),
        display_name="ArbitraryGroup",
        public=False,
        member_list_visibility="Private",
        members=[MemberUser(type="User", value=sysadmin_id)],
        administrators=[Administrator(value=sysadmin_id)],
        services=[Service(value=service_name)],
    )

    result = groups.create(arbitrary_group_info)

    mock_post.assert_called_once()
    assert result.model_dump() == expected_group.model_dump()
    assert mock_post.return_value == expected_map_group


def test_create_raises_unexpected_response_error_when_no_sysadmin(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test group creation raises UnexpectedResponseError with correct message when system admin cannot be retrieved."""

    group_info = GroupDetail(
        id=gen_group_id("g7"),
        display_name="NoSysAdminGroup",
        user_defined_id="arb006",
        description="A test group for no sysadmin.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=[]),
    )

    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.clients.groups.post")

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.create(group_info)

    assert str(exc_info.value) == "System admin group has no members."


def test_create_raises_resource_invalid_when_map_error_with_sysadmin(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test group creation raises ResourceInvalid and logs the error when MapError is returne"""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g8"),
        display_name="MapErrorGroupWithSysadmin",
        user_defined_id="arb007",
        description="A test group for MapError with sysadmin.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    error_detail = "mAP Core API returned error on create."

    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    logger_mock = mocker.patch("flask.current_app.logger.info")

    mocker.patch(
        "server.clients.groups.post", return_value=MapError(detail=error_detail, status="400", scim_type="invalidValue")
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called_once_with(error_detail)


def test_create_raises_oauth_token_error_on_http_401(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises OAuthTokenError with correct message when mAP Core API returns HTTP 401."""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g6"),
        display_name="UnauthorizedGroup",
        user_defined_id="arb005",
        description="A test group for unauthorized error.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")

    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_create_raises_unexpected_response_error_on_http_403(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises UnexpectedResponseError with correct message when mAP Core API returns HTTP 403."""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g4"),
        display_name="ForbiddenGroup",
        user_defined_id="arb003",
        description="A test group for forbidden error.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=["sysadmin"])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")

    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Failed to get Group resource from mAP Core API."


def test_create_raises_unexpected_response_error_on_http_500(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises UnexpectedResponseError with correct message"""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g9"),
        display_name="ServerErrorGroup",
        user_defined_id="arb008",
        description="A test group for server error.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")

    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "mAP Core API server error."


def test_create_raises_unexpected_response(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises UnexpectedResponseError with correct message"""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g10"),
        display_name="RequestExceptionGroup",
        user_defined_id="arb009",
        description="A test group for RequestException.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_create_raises_unexpected_response_error_on_validation_error(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises UnexpectedResponseError with correct message"""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g11"),
        display_name="ValidationErrorGroup",
        user_defined_id="arb010",
        description="A test group for ValidationError.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_create_raises_oauth_token_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises OAuthTokenError and it is propagated as is when sysadmin is present."""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g12"),
        display_name="OAuthTokenErrorGroup",
        user_defined_id="arb011",
        description="A test group for OAuthTokenError.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "token error"


def test_create_raises_credentials_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises CredentialsError and it is propagated as is when sysadmin is present."""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g13"),
        display_name="CredentialsErrorGroup",
        user_defined_id="arb012",
        description="A test group for CredentialsError.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "credentials error"
    mock_post.assert_called_once()


def test_create_raises_unexpected_exception_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises an unexpected Exception and it is propagated as is when sysadmin is present."""

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g14"),
        display_name="UnexpectedExceptionGroup",
        user_defined_id="arb013",
        description="A test group for unexpected Exception.",
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=2,
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "unexpected error"


def test_get_by_id_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id returns group info when found."""

    group_id = gen_group_id("g100")
    expected_group = GroupDetail(
        id=group_id,
        display_name="TestGroupById",
        user_defined_id="g100",
        description=None,
        public=True,
        member_list_visibility="Hidden",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )

    map_group = MapGroup(
        id=group_id,
        display_name="TestGroupById",
        public=True,
        member_list_visibility="Hidden",
        members=[MemberUser(type="User", value="sysadmin")],
        administrators=[Administrator(value="sysadmin")],
        services=[Service(value="jairocloud-groups-manager_dev")],
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.return_value = map_group

    result = groups.get_by_id(group_id)

    assert result is not None
    assert result.model_dump() == expected_group.model_dump()


def test_get_by_id_not_found_logs_and_returns_none(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id logs and returns None when group not found."""
    group_id = gen_group_id("g101")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapError(detail="not found", status="404", scim_type="invalidValue"),
    )
    logger_mock = mocker.patch("flask.current_app.logger.info")

    result = groups.get_by_id(group_id)

    assert result is None
    logger_mock.assert_called()


def test_get_by_id_raises_oauth_token_error_on_http_401(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises OAuthTokenError with correct message when HTTP 401 occurs."""

    group_id = gen_group_id("g102")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_get_by_id.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_get_by_id_raises_unexpected_response_error_on_http_403(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError with correct message when HTTP 403 occurs."""

    group_id = gen_group_id("g103")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_get_by_id.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "Failed to get Group resource from mAP Core API."


def test_get_by_id_raises_unexpected_response_error_on_http_500(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError with correct message when HTTP 500 occurs."""

    group_id = gen_group_id("g104")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_get_by_id.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "mAP Core API server error."


def test_get_by_id_raises_unexpected_response_error_on_request_exception(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError with correct message when RequestException occurs."""

    group_id = gen_group_id("g105")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_get_by_id_raises_unexpected_response_error_on_validation_error(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError with correct message when ValidationError occurs."""

    group_id = gen_group_id("g106")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_get_by_id_raises_oauth_token_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises OAuthTokenError and it is propagated as is."""

    group_id = gen_group_id("g107")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "token error"


def test_get_by_id_raises_credentials_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises CredentialsError and it is propagated as is."""

    group_id = gen_group_id("g108")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "credentials error"


def test_get_by_id_raises_unexpected_exception_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id raises an unexpected Exception and it is propagated as is."""
    group_id = gen_group_id("g109")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.get_by_id(group_id)

    assert str(exc_info.value) == "unexpected error"


def test_update_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update returns updated group info when group exists and update succeeds."""

    group_id = gen_group_id("g200")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UpdatedGroup",
        user_defined_id="g200",
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    map_group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value="sysadmin")],
        administrators=[Administrator(value="sysadmin")],
        services=[Service(value="jairocloud-groups-manager_dev")],
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.clients.groups.patch_by_id", return_value=map_group)

    result = groups.update(updated_group)

    assert result.model_dump() == updated_group.model_dump()


def test_update_raises_resource_invalid_and_logs(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises ResourceInvalid and logs when MapError is returned."""

    group_id = gen_group_id("g201")
    updated_group = GroupDetail(
        id=group_id,
        display_name="InvalidGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Hidden",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    error_detail = "Update failed due to invalid data."
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    logger_mock = mocker.patch("flask.current_app.logger.info")
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail=error_detail, status="400", scim_type="invalidValue"),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called_once_with(error_detail)


def test_update_raises_resource_not_found(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises ResourceNotFound when group does not exist."""

    group_id = gen_group_id("g202")
    updated_group = GroupDetail(
        id=group_id,
        display_name="NotFoundGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=None)
    mocker.patch("server.clients.groups.patch_by_id", return_value=None)

    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == f"'{group_id}' Not Found"


def test_update_raises_oauth_token_error_on_http_401(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises OAuthTokenError with correct message when HTTP 401 occurs."""

    group_id = gen_group_id("g203")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UnauthorizedGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_update_raises_unexpected_response_error_on_http_403(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises UnexpectedResponseError with correct message when HTTP 403 occurs."""

    group_id = gen_group_id("g204")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ForbiddenGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to update Group resource from mAP Core API."


def test_update_raises_unexpected_response_error_on_http_500(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises UnexpectedResponseError with correct message when HTTP 500 occurs."""

    group_id = gen_group_id("g205")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ServerErrorGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "mAP Core API server error."


def test_update_raises_unexpected_response_error_on_request_exception(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update raises UnexpectedResponseError with correct message when RequestException occurs."""

    group_id = gen_group_id("g206")
    updated_group = GroupDetail(
        id=group_id,
        display_name="RequestExceptionGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_update_raises_unexpected_response_error_on_validation_error(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update raises UnexpectedResponseError with correct message when ValidationError occurs."""

    group_id = gen_group_id("g207")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ValidationErrorGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_update_raises_oauth_token_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises OAuthTokenError and it is propagated as is when group exists."""

    group_id = gen_group_id("g208")
    updated_group = GroupDetail(
        id=group_id,
        display_name="OAuthTokenErrorGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "token error"


def test_update_raises_credentials_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises CredentialsError and it is propagated as is when group exists."""

    group_id = gen_group_id("g209")
    updated_group = GroupDetail(
        id=group_id,
        display_name="CredentialsErrorGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "credentials error"


def test_update_raises_unexpected_exception_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update raises an unexpected Exception and it is propagated as is when group exists."""

    group_id = gen_group_id("g210")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UnexpectedExceptionGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "unexpected error"


def test_delete_multiple_all_success(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple returns None when all groups are deleted successfully."""
    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2"), gen_group_id("g3")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")

    ops = [BulkOperation(method="DELETE", path=f"/Groups/{gid}") for gid in group_ids]
    for op in ops:
        op.response = MapGroup(
            id=op.path.removeprefix("/Groups/"), display_name="", public=True, member_list_visibility="Public"
        )
    mock_post.return_value = BulkResponse(operations=ops)

    result = groups.delete_multiple(group_ids)

    assert result is None


def test_delete_multiple_partial_failure(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple returns failed group IDs when some deletions fail."""
    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2"), gen_group_id("g3")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")

    ops = [
        BulkOperation(method="DELETE", path=f"/Groups/{gen_group_id('g1')}"),
        BulkOperation(method="DELETE", path=f"/Groups/{gen_group_id('g2')}"),
        BulkOperation(method="DELETE", path=f"/Groups/{gen_group_id('g3')}"),
    ]
    ops[0].response = MapGroup(id=gen_group_id("g1"), display_name="", public=True, member_list_visibility="Public")
    ops[1].response = MapError(detail="fail", status="400", scim_type="invalidValue")
    ops[2].response = MapError(detail="fail", status="400", scim_type="invalidValue")
    mock_post.return_value = BulkResponse(operations=ops)

    result = groups.delete_multiple(group_ids)

    assert result == {f"/Groups/{gen_group_id('g2')}", f"/Groups/{gen_group_id('g3')}"}


def test_delete_multiple_all_failure(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple returns all group IDs when all deletions fail."""
    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2"), gen_group_id("g3")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")

    ops = [BulkOperation(method="DELETE", path=f"/Groups/{gid}") for gid in group_ids]
    for op in ops:
        op.response = MapError(detail="fail", status="400", scim_type="invalidValue")
    mock_post.return_value = BulkResponse(operations=ops)

    result = groups.delete_multiple(group_ids)

    assert result == {f"/Groups/{gen_group_id('g1')}", f"/Groups/{gen_group_id('g2')}", f"/Groups/{gen_group_id('g3')}"}


def test_delete_multiple_raises_resource_invalid_and_logs(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple raises ResourceInvalid and logs when MapError is returned."""
    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    logger_mock = mocker.patch("flask.current_app.logger.info")
    mocker.patch(
        "server.clients.bulks.post",
        return_value=MapError(detail="delete failed", status="400", scim_type="invalidValue"),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "delete failed"
    logger_mock.assert_called_once_with("delete failed")


def test_delete_multiple_raises_oauth_token_error_on_http_401(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple raises OAuthTokenError with correct message when HTTP 401 occurs."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_delete_multiple_raises_unexpected_response_error_on_http_403(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_multiple raises UnexpectedResponseError with correct message when HTTP 403 occurs."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "Failed to delete Group resource from mAP Core API."


def test_delete_multiple_raises_unexpected_response_error_on_http_500(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_multiple raises UnexpectedResponseError with correct message when HTTP 500 occurs."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_post.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "mAP Core API server error."


def test_delete_multiple_raises_unexpected_response_error_on_request_exception(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_multiple raises UnexpectedResponseError with correct message when RequestException occurs."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    mock_post.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_delete_multiple_raises_unexpected_response_error_on_validation_error(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_multiple raises UnexpectedResponseError with correct message when ValidationError occurs."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    mock_post.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_delete_multiple_raises_oauth_token_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple raises OAuthTokenError and it is propagated as is."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    mock_post.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "token error"


def test_delete_multiple_raises_credentials_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_multiple raises CredentialsError and it is propagated as is."""

    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    mock_post.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "credentials error"


def test_delete_multiple_raises_unexpected_exception_propagation(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_multiple raises an unexpected Exception and it is propagated as is."""
    group_ids: set[str] = {gen_group_id("g1"), gen_group_id("g2")}
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.bulks.post")
    mock_post.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.delete_multiple(group_ids)

    assert str(exc_info.value) == "unexpected error"


def test_delete_by_id_success(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id returns None when group deletion succeeds."""
    group_id: str = gen_group_id("g1")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.return_value = None

    result = groups.delete_by_id(group_id)

    assert result is None


def test_delete_by_id_failure_resource_invalid(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises ResourceInvalid when MapError is returned."""
    group_id: str = gen_group_id("g2")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.return_value = MapError(detail="delete failed", status="400", scim_type="invalidValue")

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "delete failed"


def test_delete_by_id_raises_oauth_token_error_on_http_401(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises OAuthTokenError with correct message when HTTP 401 occurs."""

    group_id: str = gen_group_id("g3")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_delete.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_delete_by_id_raises_unexpected_response_error_on_http_403(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises UnexpectedResponseError with correct message when HTTP 403 occurs."""

    group_id: str = gen_group_id("g4")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_delete.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "Failed to delete Group resource from mAP Core API."


def test_delete_by_id_raises_unexpected_response_error_on_http_500(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises UnexpectedResponseError with correct message when HTTP 500 occurs."""

    group_id: str = gen_group_id("g5")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_delete.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "mAP Core API server error."


def test_delete_by_id_raises_unexpected_response_error_on_request_exception(
    gen_group_id, mocker: MockerFixture
) -> None:
    """Test delete_by_id raises UnexpectedResponseError with correct message when RequestException occurs."""

    group_id: str = gen_group_id("g6")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_delete_by_id_raises_unexpected_response_error_on_validation_error(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises UnexpectedResponseError with correct message when ValidationError occurs."""

    group_id: str = gen_group_id("g7")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_delete_by_id_raises_oauth_token_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises OAuthTokenError and it is propagated as is."""
    group_id: str = gen_group_id("g8")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "token error"


def test_delete_by_id_raises_credentials_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises CredentialsError and it is propagated as is."""
    group_id: str = gen_group_id("g9")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "credentials error"


def test_delete_by_id_raises_unexpected_exception_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test delete_by_id raises an unexpected Exception and it is propagated as is."""
    group_id: str = gen_group_id("g10")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_delete = mocker.patch("server.clients.groups.delete_by_id")
    mock_delete.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.delete_by_id(group_id)

    assert str(exc_info.value) == "unexpected error"


def test_update_member_add_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member adds a member successfully and returns updated group info."""
    group_id: str = gen_group_id("g100")
    sysadmin_id: str = "sysadmin"
    member_id: str = "g100"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    updated_map_group = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id), MemberUser(type="User", value=member_id)],
    )
    expected = GroupDetail(
        id=group_id,
        display_name="TestGroup",
        user_defined_id="g100",
        public=True,
        member_list_visibility="Public",
        users_count=2,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id", return_value=updated_map_group)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result = groups.update_member(group_id, add={member_id}, remove=set())
    assert result.model_dump() == expected.model_dump()


def test_update_member_add_failure_resource_invalid(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises ResourceInvalid and logs when MapError is returned on add."""
    group_id: str = gen_group_id("g101")
    sysadmin_id: str = "sysadmin"
    member_id: str = "user2"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    error_detail = "add failed"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    logger_mock = mocker.patch("flask.current_app.logger.info")
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail=error_detail, status="400", scim_type="invalidValue"),
    )
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add={member_id}, remove=set())

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called_once_with(error_detail)


def test_update_member_add_failure_no_sysadmin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises UnexpectedResponseError when system admin cannot be retrieved on add."""

    patch.stopall()
    group_id: str = gen_group_id("g102")
    member_id: str = "user3"
    sysadmin_id: str = "sysadmin"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=[]),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add={member_id}, remove=set())

    assert str(exc_info.value) == "System admin group has no members."


def test_update_member_add_failure_group_not_found(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises ResourceInvalid and logs when group info cannot be retrieved on add."""
    group_id: str = gen_group_id("g103")
    member_id: str = "user4"
    error_detail = "search failed"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapError(detail=error_detail, status="404", scim_type="invalidValue"),
    )
    logger_mock = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add={member_id}, remove=set())

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called()


def test_update_member_remove_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member removes a member successfully and returns updated group info."""
    group_id: str = gen_group_id("g104")
    sysadmin_id: str = "sysadmin"
    member_id: str = "user5"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id), MemberUser(type="User", value=member_id)],
    )
    updated_map_group = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    expected = GroupDetail(
        id=group_id,
        display_name="TestGroup",
        user_defined_id="g104",
        public=True,
        member_list_visibility="Public",
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id", return_value=updated_map_group)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result = groups.update_member(group_id, add=set(), remove={member_id})

    assert result.model_dump() == expected.model_dump()


def test_update_member_remove_all_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member removes all members successfully and sysadmin remains as member."""
    group_id: str = gen_group_id("g105")
    sysadmin_id: str = "sysadmin"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[
            MemberUser(type="User", value=sysadmin_id),
            MemberUser(type="User", value="user6"),
            MemberUser(type="User", value="user7"),
        ],
    )
    updated_map_group = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    expected = GroupDetail(
        id=group_id,
        display_name="TestGroup",
        user_defined_id="g105",
        public=True,
        member_list_visibility="Public",
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id", return_value=updated_map_group)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result = groups.update_member(group_id, add=set(), remove={"user6", "user7"})

    assert result.model_dump() == expected.model_dump()


def test_update_member_remove_failure_resource_invalid(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises ResourceInvalid and logs when MapError is returned on remove."""
    group_id: str = gen_group_id("g106")
    sysadmin_id: str = "sysadmin"
    member_id: str = "user8"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id), MemberUser(type="User", value=member_id)],
    )
    error_detail = "remove failed"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    logger_mock = mocker.patch("flask.current_app.logger.info")
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail=error_detail, status="400", scim_type="invalidValue"),
    )
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add=set(), remove={member_id})

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called_once_with(error_detail)


def test_update_member_remove_failure_no_sysadmin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises ResourceInvalid when system admin cannot be retrieved on remove."""
    patch.stopall()
    group_id: str = gen_group_id("g107")
    member_id: str = "user9"

    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=[]),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add=set(), remove={member_id})

    assert str(exc_info.value) == "System admin group has no members."


def test_update_member_remove_failure_group_not_found(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises ResourceInvalid and logs when group info cannot be retrieved on remove."""
    group_id: str = gen_group_id("g108")
    member_id: str = "user10"
    error_detail = "search failed"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapError(detail=error_detail, status="404", scim_type="invalidValue"),
    )
    logger_mock = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add=set(), remove={member_id})

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called()


def test_update_member_conflict(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises RequestConflict when both add and remove members are set."""
    group_id: str = gen_group_id("g109")
    sysadmin_id: str = "sysadmin"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(RequestConflict):
        groups.update_member(group_id, add={"user11"}, remove={"user11"})


def test_update_member_no_members_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member with no add/remove members returns group info when sysadmin is present."""
    group_id: str = gen_group_id("g110")
    sysadmin_id: str = "sysadmin"
    group_info = MapGroup(
        id=group_id,
        display_name="TestGroup",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value=sysadmin_id)],
    )
    expected = GroupDetail(
        id=group_id,
        display_name="TestGroup",
        public=True,
        user_defined_id="g110",
        member_list_visibility="Public",
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id", return_value=group_info)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result = groups.update_member(group_id, add=set(), remove=set())

    assert result.model_dump() == expected.model_dump()


def test_update_member_no_members_failure_no_sysadmin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member with no add/remove members raises ResourceInvalid"""
    patch.stopall()
    group_id: str = gen_group_id("g111")

    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=[]),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add=set(), remove=set())

    assert str(exc_info.value) == "System admin group has no members."


def test_update_member_no_members_failure_group_not_found(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member with no add/remove members raises ResourceInvalid and logs"""
    group_id: str = gen_group_id("g112")
    error_detail = "search failed"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapError(detail=error_detail, status="404", scim_type="invalidValue"),
    )
    logger_mock = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member(group_id, add=set(), remove=set())

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called()
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_oauth_token_error_on_http_401(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    group_id: str = gen_group_id("g113")
    sysadmin_id: str = "sysadmin"
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=http_error)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update_member(group_id, add={"user12"}, remove=set())

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_update_member_raises_unexpected_response_error_on_http_403(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member raises UnexpectedResponseError with correct message when HTTP 403 occurs."""
    group_id: str = gen_group_id("g114")
    sysadmin_id: str = "sysadmin"
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=http_error)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member(group_id, add={"user13"}, remove=set())

    assert str(exc_info.value) == "Failed to update Group resource from mAP Core API."
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_unexpected_response_error_on_http_500(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member raises UnexpectedResponseError with correct message when HTTP 500 occurs."""

    group_id: str = gen_group_id("g115")
    sysadmin_id: str = "sysadmin"
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=http_error)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member(group_id, add={"user14"}, remove=set())

    assert str(exc_info.value) == "mAP Core API server error."
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_unexpected_response_error_on_request_exception(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member raises UnexpectedResponseError with correct message when RequestException occurs."""

    group_id: str = gen_group_id("g116")
    sysadmin_id: str = "sysadmin"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=requests.RequestException())
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member(group_id, add={"user15"}, remove=set())

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_unexpected_response_error_on_validation_error(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member raises UnexpectedResponseError with correct message when ValidationError occurs."""

    group_id: str = gen_group_id("g117")
    sysadmin_id: str = "sysadmin"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=ValidationError("validation error", []))
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member(group_id, add={"user16"}, remove=set())

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_oauth_token_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises OAuthTokenError and it is propagated as is."""
    group_id: str = gen_group_id("g118")
    sysadmin_id: str = "sysadmin"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=OAuthTokenError("token error"))
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update_member(group_id, add={"user17"}, remove=set())

    assert str(exc_info.value) == "token error"
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_credentials_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises CredentialsError and it is propagated as is."""
    group_id: str = gen_group_id("g119")
    sysadmin_id: str = "sysadmin"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=CredentialsError("credentials error"))
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())

    with pytest.raises(CredentialsError) as exc_info:
        groups.update_member(group_id, add={"user18"}, remove=set())

    assert str(exc_info.value) == "credentials error"
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_raises_unexpected_exception_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test update_member raises an unexpected Exception and it is propagated as is."""
    group_id: str = gen_group_id("g120")
    sysadmin_id: str = "sysadmin"
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=None)
    mocker.patch("server.services.groups.get_system_admin", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=UnexpectedError("unexpected error"))
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update_member(group_id, add={"user19"}, remove=set())

    assert str(exc_info.value) == "unexpected error"
    assert mock_patch.call_args[0][0] == group_id


def test_update_put_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests successful group update with arbitrary info, administrators, and services."""
    group_id = gen_group_id("g_put_1")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UpdatedGroupPUT",
        user_defined_id="g_put_1",
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    map_group = MapGroup(
        id=group_id,
        display_name="UpdatedGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[MemberUser(type="User", value="sysadmin")],
        administrators=[Administrator(value="admin1")],
        services=[Service(value="service1")],
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mocker.patch("server.clients.groups.patch_by_id", return_value=map_group)
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result: GroupDetail = groups.update(updated_group)

    assert result.model_dump() == updated_group.model_dump()
    assert map_group.administrators is not None
    assert map_group.administrators[0].value == "admin1"
    assert map_group.services is not None
    assert map_group.services[0].value == "service1"


def test_update_put_failure_resource_invalid_and_logs(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update failure with ResourceInvalid and log output."""
    group_id = gen_group_id("g_put_2")
    updated_group = GroupDetail(
        id=group_id,
        display_name="InvalidGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    error_detail = "PUT update failed due to invalid data."
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    logger_mock = mocker.patch("flask.current_app.logger.info")
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail=error_detail, status="400", scim_type="invalidValue"),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == error_detail
    logger_mock.assert_called_once_with(error_detail)


def test_update_put_raises_oauth_token_error_on_http_401(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update raises OAuthTokenError on HTTP 401."""
    group_id = gen_group_id("g_put_3")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UnauthorizedGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Access token is invalid or expired."
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_unexpected_response_error_on_http_403(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Tests group update raises UnexpectedResponseError on HTTP 403."""
    group_id = gen_group_id("g_put_4")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ForbiddenGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to update Group resource from mAP Core API."
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_unexpected_response_error_on_http_500(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Tests group update raises UnexpectedResponseError on HTTP 500."""
    group_id = gen_group_id("g_put_5")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ServerErrorGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)
    mock_patch.side_effect = http_error

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "mAP Core API server error."
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_unexpected_response_error_on_request_exception(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Tests group update raises UnexpectedResponseError on RequestException."""
    group_id = gen_group_id("g_put_6")
    updated_group = GroupDetail(
        id=group_id,
        display_name="RequestExceptionGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_unexpected_response_error_on_validation_error(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Tests group update raises UnexpectedResponseError on ValidationError."""
    group_id = gen_group_id("g_put_7")
    updated_group = GroupDetail(
        id=group_id,
        display_name="ValidationErrorGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_oauth_token_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update raises OAuthTokenError and it is propagated as is."""
    group_id = gen_group_id("g_put_8")
    updated_group = GroupDetail(
        id=group_id,
        display_name="OAuthTokenErrorGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "token error"
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_credentials_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update raises CredentialsError and it is propagated as is."""
    group_id = gen_group_id("g_put_9")
    updated_group = GroupDetail(
        id=group_id,
        display_name="CredentialsErrorGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = CredentialsError("credentials error")

    with pytest.raises(CredentialsError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "credentials error"
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_raises_unexpected_exception_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update raises an unexpected Exception and it is propagated as is."""
    group_id = gen_group_id("g_put_10")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UnexpectedExceptionGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "unexpected error"
    assert mock_patch.call_args[0][0] == updated_group.id


def test_get_system_admin_all_user_types(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin returns all values when all type=User."""
    sysadmins: list[Member] = [MemberUser(type="User", value="user1"), MemberUser(type="User", value="user2")]
    expected: list[str] = ["user1", "user2"]
    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(
            id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=sysadmins
        ),
    )
    mocker.patch("server.services.groups.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.groups.get_client_secret", return_value="dummy_secret")

    result = groups.get_system_admin()

    assert sorted(result) == sorted(expected)


def test_get_system_admin_some_user_types(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin returns only type=User values when mixed types."""
    expected: list[str] = ["user1", "user2"]
    sysadmins: list[Member] = [
        MemberUser(type="User", value="user1"),
        MemberUser(type="User", value="user2"),
    ]
    get_by_id_mock = mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(
            id="sysadmin",
            display_name="",
            public=True,
            member_list_visibility="Public",
            members=sysadmins,
        ),
    )
    called_map_group = get_by_id_mock.return_value
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_access_token", return_value="token")

    result = groups.get_system_admin()

    assert sorted(result) == sorted(expected)
    assert called_map_group.members == sysadmins


def test_get_system_admin_no_user_types(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin returns nothing when no type=User."""
    sysadmins: list[Member] = [
        MemberGroup(type="Group", value="user1"),
    ]
    get_by_id_mock = mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(
            id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=sysadmins
        ),
    )
    called_map_group = get_by_id_mock.return_value
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    result = groups.get_system_admin()

    assert not result
    assert called_map_group.members == sysadmins


def test_get_system_admin_failure(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin returns nothing on failure."""
    sysadmins: list[Member] = [
        MemberGroup(type="Group", value="user1"),
    ]
    get_by_id_mock = mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(
            id="sysadmin", display_name="", public=True, member_list_visibility="Public", members=sysadmins
        ),
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    result = groups.get_system_admin()

    assert not result
    called_map_group = get_by_id_mock.return_value
    assert called_map_group.members == sysadmins


def test_get_system_admin_raises_oauth_token_error_on_http_401(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises OAuthTokenError on HTTP 401."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mock_get_by_id.side_effect = http_error

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "Access token is invalid or expired."


def test_get_system_admin_raises_unexpected_response_error_on_http_403(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises UnexpectedResponseError on HTTP 403."""
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)

    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = http_error
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "Failed to get Group resource from mAP Core API."


def test_get_system_admin_raises_unexpected_response_error_on_http_500(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises UnexpectedResponseError on HTTP 500."""
    response = Response()
    response.status_code = 500
    http_error = requests.HTTPError(response=response)

    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = http_error
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "mAP Core API server error."


def test_get_system_admin_raises_unexpected_response_error_on_request_exception(
    app: Flask, mocker: MockerFixture
) -> None:
    """Tests get_system_admin raises UnexpectedResponseError on RequestException."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = requests.RequestException()
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_get_system_admin_raises_unexpected_response_error_on_validation_error(
    app: Flask, mocker: MockerFixture
) -> None:
    """Tests get_system_admin raises UnexpectedResponseError on ValidationError."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_get_system_admin_raises_oauth_token_error_propagation(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises OAuthTokenError and it is propagated as is."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_get_by_id.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "token error"


def test_get_system_admin_raises_credentials_error_propagation(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises CredentialsError and it is propagated as is."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = CredentialsError("credentials error")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    with pytest.raises(CredentialsError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "credentials error"


def test_get_system_admin_raises_unexpected_exception_propagation(app: Flask, mocker: MockerFixture) -> None:
    """Tests get_system_admin raises an unexpected Exception and it is propagated as is."""
    mock_get_by_id = mocker.patch("server.clients.groups.get_by_id")
    mock_get_by_id.side_effect = UnexpectedError("unexpected error")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.get_system_admin()

    assert str(exc_info.value) == "unexpected error"


@pytest.fixture
def gen_group_id(test_config: RuntimeConfig) -> t.Callable[[str], str]:

    def _gen_group_id(user_defined_id: str) -> str:
        pattern = test_config.GROUPS.id_patterns.user_defined
        return pattern.format(repository_id="repo_id", user_defined_id=user_defined_id)

    return _gen_group_id
