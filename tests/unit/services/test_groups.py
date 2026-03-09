import typing as t

from http import HTTPStatus

import pytest
import requests

from flask import Flask
from pydantic_core import ValidationError
from pytest_mock import MockerFixture
from requests.models import Response

from server.entities.bulk_request import BulkOperation, BulkResponse
from server.entities.group_detail import GroupDetail, Repository
from server.entities.map_error import MapError
from server.entities.map_group import Administrator, MapGroup, MemberUser, Service
from server.entities.search_request import SearchRequestParameter, SearchResponse, SearchResult
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
from server.services import groups
from server.services.groups import update_put
from server.services.utils.search_queries import GroupsCriteria, make_criteria_object
from tests.helpers import UnexpectedError


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture

    from server.config import RuntimeConfig
import typing as t

from unittest.mock import MagicMock


def test_search_successa(gen_group_id, mocker: MockerFixture) -> None:
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
                repository_name="repo1",
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
    mocker.patch(
        "server.services.groups.detect_repository", return_value=Service(display="repo1", value="repo1", ref=None)
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


def test_search_raw_true_success(gen_group_id, mocker):
    criteria = make_criteria_object("groups", q="Test")
    query_param = SearchRequestParameter(filter='displayName co "Test"')
    mocker.patch("server.services.groups.build_search_query", return_value=query_param)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_groups_search = mocker.patch("server.services.groups.groups.search")
    resources = [
        MapGroup(id=gen_group_id("g2"), display_name="TestGroup2", public=False, member_list_visibility="Private")
    ]
    mock_groups_search.return_value = SearchResponse[MapGroup](
        total_results=1, items_per_page=1, start_index=1, resources=resources
    )
    result = groups.search(criteria, raw=True)
    assert isinstance(result, SearchResponse)
    assert result.resources == resources


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


def test_search_map_error_invalid_query(app: Flask, mocker: MockerFixture) -> None:
    criteria = make_criteria_object("groups", q="Test")
    query_param = SearchRequestParameter(filter='displayName co "Test"')
    mocker.patch("server.services.groups.build_search_query", return_value=query_param)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.groups.groups.search",
        return_value=MapError(detail="invalid query", status="400", scim_type="invalidSyntax"),
    )
    with pytest.raises(InvalidQueryError):
        groups.search(criteria)


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


def test_create_success(app, gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation succeeds with valid input and correct interaction with mAP Core API."""

    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")
    sysadmin_id: str = "sysadmin"
    service_name: str = "jairocloud-groups-manager_dev"
    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g2"),
        display_name="ArbitraryGroup",
        user_defined_id="arb001",
        description="A test group for arbitrary info.",
        public=False,
        member_list_visibility="Private",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=5,
        type="group",
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
        type="group",
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

    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
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
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")
    group_info = GroupDetail(
        id=gen_group_id("g7"),
        display_name="NoSysAdminGroup",
        user_defined_id="arb006",
        description="A test group for no sysadmin.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    mocker.patch(
        "server.clients.groups.get_by_id",
        return_value=MapGroup(
            id="system_admin", display_name="", public=True, member_list_visibility="Public", members=[]
        ),
    )
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.clients.groups.post")
    mocker.patch(
        "server.clients.groups.post",
        return_value=MapError(detail="System admin group has no members.", status="400", scim_type="invalidValue"),
    )

    with pytest.raises(ResourceInvalid) as exc_info:
        groups.create(group_info)

    assert str(exc_info.value) == "System admin group has no members."


def test_create_raises_oauth_token_error_on_http_401(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises OAuthTokenError with correct message when mAP Core API returns HTTP 401."""
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")
    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g6"),
        display_name="UnauthorizedGroup",
        user_defined_id="arb005",
        description="A test group for unauthorized error.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g4"),
        display_name="ForbiddenGroup",
        user_defined_id="arb003",
        description="A test group for forbidden error.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")

    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
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
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g9"),
        display_name="ServerErrorGroup",
        user_defined_id="arb008",
        description="A test group for server error.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g10"),
        display_name="RequestExceptionGroup",
        user_defined_id="arb009",
        description="A test group for RequestException.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Failed to communicate with mAP Core API."


def test_create_raises_unexpected_response_error_on_validation_error(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises UnexpectedResponseError with correct message"""
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g11"),
        display_name="ValidationErrorGroup",
        user_defined_id="arb010",
        description="A test group for ValidationError.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_create_raises_oauth_token_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises OAuthTokenError and it is propagated as is when sysadmin is present."""
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g12"),
        display_name="OAuthTokenErrorGroup",
        user_defined_id="arb011",
        description="A test group for OAuthTokenError.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "token error"


def test_create_raises_credentials_error_propagation(gen_group_id, mocker: MockerFixture) -> None:
    """Test group creation raises CredentialsError and it is propagated as is when sysadmin is present."""
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g13"),
        display_name="CredentialsErrorGroup",
        user_defined_id="arb012",
        description="A test group for CredentialsError.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")

    arbitrary_group_info = GroupDetail(
        id=gen_group_id("g14"),
        display_name="UnexpectedExceptionGroup",
        user_defined_id="arb013",
        description="A test group for unexpected Exception.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )

    sysadmin_id = "sysadmin"
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)
    mocker.patch("server.services.groups.prepare_group")
    mocker.patch("server.services.utils.detect_affiliation", return_value=None)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_post = mocker.patch("server.clients.groups.post")
    mock_post.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.create(arbitrary_group_info)

    assert str(exc_info.value) == "unexpected error"


def test_create_invalid_form_error(app, gen_group_id, mocker):
    repository = Repository(id="repo1", service_name="jairocloud-groups-manager_dev")
    group_info = GroupDetail(
        id=gen_group_id("g7"),
        display_name="NoSysAdminGroup",
        user_defined_id="arb006",
        description="A test group for no sysadmin.",
        public=True,
        member_list_visibility="Public",
        repository=repository,
        created=None,
        last_modified=None,
        users_count=2,
        type="group",
    )
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.services.groups.prepare_group", side_effect=InvalidFormError("invalid form"))
    with pytest.raises(InvalidFormError):
        groups.create(group_info)


def test_get_by_id_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Test get_by_id returns group info when found."""

    group_id = gen_group_id("g100")
    expected_group = GroupDetail(
        id=group_id,
        display_name="TestGroupById",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Hidden",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
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


def test_get_by_id_raw_true_success(gen_group_id, mocker):
    group_id = gen_group_id("g100")
    map_group = MapGroup(id=group_id, display_name="TestGroupById", public=True, member_list_visibility="Hidden")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.get_by_id", return_value=None)
    mocker.patch("server.clients.groups.get_by_id", return_value=map_group)
    result = groups.get_by_id(group_id, raw=True)
    assert result == map_group


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
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
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
        type="group",
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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=None)
    mocker.patch("server.clients.groups.patch_by_id", return_value=None)

    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == f"Group '{group_id}' Not Found"


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
        type="group",
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
        type="group",
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
        type="group",
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
        type="group",
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
        type="group",
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
        type="group",
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
        type="group",
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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update(updated_group)

    assert str(exc_info.value) == "unexpected error"


def test_update_delegates_to_update_put(app, gen_group_id, mocker):
    group = MagicMock(spec=GroupDetail)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mock_update_put = mocker.patch("server.services.groups.update_put", return_value="put_result")
    result = groups.update(group)
    assert result == "put_result"
    mock_update_put.assert_called_once_with(group)


def test_update_invalid_form_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g200")
    group = GroupDetail(
        id=group_id,
        display_name="UpdatedGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.patch_by_id", side_effect=InvalidFormError("invalid form"))
    with pytest.raises(InvalidFormError):
        groups.update(group)


def test_update_put_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests successful group update with arbitrary info, administrators, and services."""
    group_id = gen_group_id("g_put_1")
    updated_group = GroupDetail(
        id=group_id,
        display_name="UpdatedGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
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


def test_update_put_direct_success(app, gen_group_id, mocker):

    group_id = gen_group_id("g200")

    map_group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    group = GroupDetail(
        id=group_id,
        display_name="UpdatedGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=None,
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.prepare_group", return_value=group)
    mocker.patch("server.clients.groups.put_by_id", return_value=group)
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.clients.groups.patch_by_id", return_value=map_group)
    result = groups.update_put(group)
    assert isinstance(result, GroupDetail)
    assert result.model_dump() == group.model_dump()


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
        type="group",
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
        groups.update_put(updated_group)

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
        type="group",
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
        groups.update_put(updated_group)

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
        type="group",
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
        groups.update_put(updated_group)

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
        type="group",
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
        groups.update_put(updated_group)

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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = requests.RequestException()

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_put(updated_group)

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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = ValidationError("validation error", [])

    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_put(updated_group)

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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = OAuthTokenError("token error")

    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update_put(updated_group)

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
        type="group",
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
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = UnexpectedError("unexpected error")

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update_put(updated_group)

    assert str(exc_info.value) == "unexpected error"
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_401_unauthorized(app, mocker):
    group = GroupDetail(
        id="g_test",
        display_name="TestGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.validate_group_to_map_group", return_value=group)

    mock_put = mocker.patch("server.clients.groups.put_by_id")
    response = requests.Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mock_put.side_effect = http_error
    with pytest.raises(OAuthTokenError):
        update_put(group)


def test_update_put_500_internal_server_error(app, mocker):
    group = GroupDetail(
        id="g_test",
        display_name="TestGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.validate_group_to_map_group", return_value=group)
    mock_put = mocker.patch("server.clients.groups.put_by_id")

    mock_put.side_effect = None
    response = requests.Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mock_put.side_effect = http_error
    with pytest.raises(UnexpectedResponseError) as exc_info:
        update_put(group)
    assert "mAP Core API server error." in str(exc_info.value)


def test_update_put_http_error(app, mocker):
    group = GroupDetail(
        id="g_test",
        display_name="TestGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.validate_group_to_map_group", return_value=group)
    mock_put = mocker.patch("server.clients.groups.put_by_id")

    mock_put.side_effect = None
    response = requests.Response()
    response.status_code = HTTPStatus.FORBIDDEN
    http_error = requests.HTTPError(response=response)
    mock_put.side_effect = http_error
    with pytest.raises(UnexpectedResponseError) as exc_info:
        update_put(group)
    assert "Failed to update Group resource from mAP Core API." in str(exc_info.value)


def test_update_put_success_direc(app, mocker):
    group = GroupDetail(
        id="g_test",
        display_name="TestGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.validate_group_to_map_group", return_value=group)
    mock_put = mocker.patch("server.clients.groups.put_by_id")

    map_group = MapGroup(id="g_test", display_name="TestGroup", public=True, member_list_visibility="Public")
    mock_put.side_effect = None
    mock_put.return_value = map_group
    result = update_put(group)
    assert result.display_name == "TestGroup"


def test_update_put_all_branches(app, mocker):
    group = GroupDetail(
        id="g_test",
        display_name="TestGroup",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.validate_group_to_map_group", return_value=group)
    mock_put = mocker.patch("server.clients.groups.put_by_id")

    # RequestException
    mock_put.side_effect = requests.RequestException()
    with pytest.raises(UnexpectedResponseError) as exc_info:
        update_put(group)
    assert "Failed to communicate with mAP Core API." in str(exc_info.value)

    # ValidationError
    mock_put.side_effect = ValidationError("validation error", [])
    with pytest.raises(UnexpectedResponseError) as exc_info:
        update_put(group)
    assert "Failed to parse Group resource from mAP Core API." in str(exc_info.value)

    # OAuthTokenError
    mock_put.side_effect = OAuthTokenError("token error")
    with pytest.raises(OAuthTokenError):
        update_put(group)

    # CredentialsError
    mock_put.side_effect = CredentialsError("cred error")
    with pytest.raises(CredentialsError):
        update_put(group)

    # InvalidFormError
    mock_put.side_effect = InvalidFormError("form error")
    with pytest.raises(InvalidFormError):
        update_put(group)


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


def test_delete_by_id_map_error_not_found(gen_group_id, mocker):
    group_id = gen_group_id("g200")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch(
        "server.clients.groups.delete_by_id",
        return_value=MapError(detail=f"Group '{group_id}' Not Found", status="404", scim_type="noTarget"),
    )
    with pytest.raises(ResourceNotFound):
        groups.delete_by_id(group_id)


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
        user_defined_id=None,
        public=True,
        member_list_visibility="Public",
        users_count=2,
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", return_value=group_info)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mocker.patch("server.clients.groups.patch_by_id", return_value=updated_map_group)
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    result = groups.update_member(group_id, add={member_id}, remove=set())
    assert result.model_dump() == expected.model_dump()


def test_update_member_add_and_remove(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    group_id: str = gen_group_id("g113")
    same_user: str = "user12"

    with pytest.raises(RequestConflict) as exc_info:
        groups.update_member(group_id, add={same_user}, remove={same_user})

    assert str(exc_info.value) == "Conflict user IDs in add and remove."


def test_update_member_raises_oauth_token_error_on_http_401(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    group_id: str = gen_group_id("g113")
    sysadmin_id: str = "sysadmin"
    response = Response()
    response.status_code = 401
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.get_by_id", side_effect=http_error)
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
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
    mocker.patch("server.services.users.get_system_admins", return_value=[sysadmin_id])
    mock_patch = mocker.patch("server.clients.groups.patch_by_id", side_effect=UnexpectedError("unexpected error"))
    mocker.patch("server.datastore.app_cache", new=mocker.Mock())
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    with pytest.raises(UnexpectedError) as exc_info:
        groups.update_member(group_id, add={"user19"}, remove=set())

    assert str(exc_info.value) == "unexpected error"
    assert mock_patch.call_args[0][0] == group_id


def test_update_member_delegates_to_update_member_put(app, gen_group_id, mocker):
    group_id = gen_group_id("g300")
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mock_update_member_put = mocker.patch("server.services.groups.update_member_put", return_value="put_result")
    result = groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert result == "put_result"
    mock_update_member_put.assert_called_once_with(group_id, {"u1"}, {"u2"})


def test_update_member_get_by_id_none(app, gen_group_id, mocker):
    group_id = gen_group_id("g301")
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mocker.patch("server.services.groups.get_by_id", return_value=None)
    with pytest.raises(ResourceNotFound):
        groups.update_member(group_id, add={"u1"}, remove={"u2"})


def test_update_member_map_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g302")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail="invalid", status="400", scim_type="invalidValue"),
    )
    with pytest.raises(ResourceInvalid):
        groups.update_member(group_id, add={"u1"}, remove={"u2"})


def test_update_member_all_branches(app, mocker):
    group_id = "g_test"
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mock_update_member_put = mocker.patch("server.services.groups.update_member_put", return_value="put_result")
    result = groups.update_member(group_id, add={"u1"}, remove={"u2"})
    assert result == "put_result"
    mock_update_member_put.assert_called_once_with(group_id, {"u1"}, {"u2"})


def test_update_member_patch_oauth_token_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g303")
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "patch")
    group = MapGroup(id=group_id, display_name="TestGroup", public=True, member_list_visibility="Public")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=[])
    response = requests.Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.groups.patch_by_id", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        groups.update_member(group_id, add={"u1"}, remove={"u2"})


def test_update_member_put_direct_success(app, gen_group_id, mocker):

    group_id = gen_group_id("g400")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    group.members = []
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.clients.groups.patch_by_id", return_value=group)
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", return_value=group)
    result = groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert isinstance(result, GroupDetail)
    assert (
        result.model_dump()
        == GroupDetail(
            id=group_id,
            user_defined_id=None,
            display_name="UpdatedGroup",
            description=None,
            public=True,
            member_list_visibility="Public",
            repository=None,
            type="group",
            created=None,
            last_modified=None,
            users_count=None,
        ).model_dump()
    )


def test_update_member_put_not_found(app, gen_group_id, mocker):
    group_id = gen_group_id("g401")
    mocker.patch("server.services.groups.get_by_id", return_value=None)
    with pytest.raises(ResourceNotFound):
        groups.update_member_put(group_id, {"u1"}, {"u2"})


def test_update_member_put_map_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g402")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", return_value=group)
    mocker.patch(
        "server.clients.groups.patch_by_id",
        return_value=MapError(detail="invalid", status="400", scim_type="invalidValue"),
    )
    with pytest.raises(ResourceInvalid):
        groups.update_member_put(group_id, {"u1"}, {"u2"})


def test_update_member_put_oauth_token_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g403")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", side_effect=OAuthTokenError("token error"))
    mocker.patch("server.clients.groups.patch_by_id", side_effect=OAuthTokenError("token error"))
    with pytest.raises(OAuthTokenError) as exc_info:
        groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert str(exc_info.value) == "token error"


def test_update_member_put_unexpected_response_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g404")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    response = Response()
    response.status_code = 403
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.groups.put_by_id", side_effect=http_error)
    mocker.patch("server.clients.groups.patch_by_id", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert str(exc_info.value) == "Failed to update Group resource from mAP Core API."


def test_update_member_put_validation_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g405")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", side_effect=ValidationError("validation error", []))
    mocker.patch("server.clients.groups.patch_by_id", side_effect=ValidationError("validation error", []))
    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert str(exc_info.value) == "Failed to parse Group resource from mAP Core API."


def test_update_member_put_credentials_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g406")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", side_effect=CredentialsError("credentials error"))
    mocker.patch("server.clients.groups.patch_by_id", side_effect=CredentialsError("credentials error"))
    with pytest.raises(CredentialsError) as exc_info:
        groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert str(exc_info.value) == "credentials error"


def test_update_member_put_unexpected_error(app, gen_group_id, mocker):
    group_id = gen_group_id("g407")
    group = MapGroup(
        id=group_id,
        display_name="UpdatedGroup",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=["sysadmin"])
    mocker.patch("server.clients.groups.put_by_id", side_effect=UnexpectedError("unexpected error"))
    mocker.patch("server.clients.groups.patch_by_id", side_effect=UnexpectedError("unexpected error"))
    with pytest.raises(UnexpectedError) as exc_info:
        groups.update_member_put(group_id, {"u1"}, {"u2"})
    assert str(exc_info.value) == "unexpected error"


def test_update_put_delegates_to_update_patch(app, gen_group_id, mocker):
    """Test update_put delegates to update when strategy is 'patch'."""
    group = MagicMock(spec=GroupDetail)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mock_update = mocker.patch("server.services.groups.update", return_value="patch_result")
    result = groups.update_put(group)
    assert result == "patch_result"
    mock_update.assert_called_once_with(group)


def test_update_put_map_error_resource_not_found(app, gen_group_id, mocker):
    """Test update_put raises ResourceNotFound when MapError.detail matches MAP_NOT_FOUND_PATTERN."""
    group_id = gen_group_id("g_put_nf")
    group = GroupDetail(
        id=group_id,
        display_name="NFGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    logger_mock = mocker.patch("flask.current_app.logger.info")
    map_error = MapError(detail="Group not found", status="404", scim_type="invalidValue")
    mocker.patch("server.clients.groups.put_by_id", return_value=map_error)

    mocker.patch("server.clients.groups.patch_by_id", return_value=map_error)
    mocker.patch("re.search", return_value=True)
    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update_put(group)
    assert str(exc_info.value) == map_error.detail
    logger_mock.assert_called_once_with(map_error.detail)


def test_update_member_put_delegates_to_update_member(app, gen_group_id, mocker):
    """Test update_member_put delegates to update_member when strategy is 'patch'."""
    group_id = gen_group_id("g_mem_patch")
    add = {"user1"}
    remove = {"user2"}
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mock_update_member = mocker.patch("server.services.groups.update_member", return_value="patch_result")
    result = groups.update_member_put(group_id, add, remove)
    assert result == "patch_result"
    mock_update_member.assert_called_once_with(group_id, add, remove)


def test_update_member_put_request_conflict(app, gen_group_id, mocker):
    """Test update_member_put raises RequestConflict when add & remove overlap."""
    group_id = gen_group_id("g_mem_conflict")
    add = {"user1", "user2"}
    remove = {"user2", "user3"}
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    with pytest.raises(RequestConflict) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert "Conflict user IDs" in str(exc_info.value)


def test_update_member_put_map_error_resource_not_found(app, gen_group_id, mocker):
    """Test update_member_put raises ResourceNotFound when MapError.detail matches MAP_NOT_FOUND_PATTERN."""
    group_id = gen_group_id("g_mem_nf")
    add = {"user1"}
    remove = set()
    dummy_group = MapGroup(
        id=group_id,
        display_name="ValidationErrorGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=dummy_group)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    logger_mock = mocker.patch("flask.current_app.logger.info")
    map_error = MapError(detail="Group not found", status="404", scim_type="invalidValue")
    mocker.patch("server.clients.groups.put_by_id", return_value=map_error)
    mocker.patch("re.search", return_value=True)
    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert str(exc_info.value) == map_error.detail
    logger_mock.assert_called_once_with(map_error.detail)


@pytest.mark.parametrize(
    ("status_code", "expected_exc", "expected_msg"),
    [
        (401, OAuthTokenError, "Access token is invalid or expired."),
        (500, UnexpectedResponseError, "mAP Core API server error."),
        (403, UnexpectedResponseError, "Failed to update Group resource from mAP Core API."),
    ],
    ids=["401", "500", "other"],
)
def test_update_member_put_http_error(app, gen_group_id, mocker, status_code, expected_exc, expected_msg):
    """Test update_member_put HTTP error handling for 401, 500, and other codes."""
    expected_status_code = 401
    group_id = gen_group_id("g_mem_http")
    add = {"user1"}
    remove = set()

    updated_group = MapGroup(
        id=group_id,
        display_name="ValidationErrorGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mock_put = mocker.patch("server.clients.groups.put_by_id")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = status_code
    http_error = requests.HTTPError(response=response)
    mock_put.side_effect = http_error
    if status_code == expected_status_code:
        with pytest.raises(OAuthTokenError) as exc_info:
            groups.update_member_put(group_id, add, remove)
        assert str(exc_info.value) == expected_msg
    else:
        with pytest.raises(expected_exc) as exc_info:
            groups.update_member_put(group_id, add, remove)
        assert str(exc_info.value) == expected_msg


@pytest.fixture
def gen_group_id(test_config: RuntimeConfig) -> t.Callable[[str], str]:

    def _gen_group_id(user_defined_id: str) -> str:
        pattern = test_config.GROUPS.id_patterns.user_defined
        return pattern.format(repository_id="repo_id", user_defined_id=user_defined_id)

    return _gen_group_id


def test_update_put_raises_invalid_form_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group update raises InvalidFormError and it is propagated as is."""
    group_id = gen_group_id("g_put_11")
    updated_group = GroupDetail(
        id=group_id,
        display_name="InvalidFormErrorGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=updated_group)
    mock_patch = mocker.patch("server.clients.groups.patch_by_id")
    mock_patch.side_effect = InvalidFormError("invalid form error")

    with pytest.raises(InvalidFormError) as exc_info:
        groups.update_put(updated_group)

    assert str(exc_info.value) == "invalid form error"
    assert mock_patch.call_args[0][0] == updated_group.id


def test_update_put_resource_invalid_when_map_error_and_not_found_pattern_false(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_put raises ResourceInvalid when MapError.detail does not match MAP_NOT_FOUND_PATTERN."""
    group_id = gen_group_id("g_put_inv")
    group = GroupDetail(
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
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    logger_mock = mocker.patch("flask.current_app.logger.info")
    map_error = MapError(detail="Some other error", status="400", scim_type="invalidValue")
    mocker.patch("server.clients.groups.put_by_id", return_value=map_error)
    mocker.patch("re.search", return_value=False)
    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_put(group)
    assert str(exc_info.value) == map_error.detail
    logger_mock.assert_called_once_with(map_error.detail)


def test_update_put_validation_error_on_validate_group_to_map_group(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_put raises UnexpectedResponseError when validate_group_to_map_group raises ValidationError."""
    group_id = gen_group_id("g_put_valerr")
    group = GroupDetail(
        id=group_id,
        display_name="ValErrGroupPUT",
        user_defined_id=None,
        description=None,
        public=True,
        member_list_visibility="Public",
        repository=None,
        created=None,
        last_modified=None,
        users_count=1,
        type="group",
    )
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch(
        "server.services.groups.validate_group_to_map_group", side_effect=ValidationError("validation error", [])
    )
    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_put(group)
    assert "Failed to parse Group resource from mAP Core API." in str(exc_info.value)


def test_update_member_put_credentials_error_propagation(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests update_member_put raises CredentialsError and it is propagated as is."""
    group_id = gen_group_id("g_mem_cred")
    add = {"user1"}
    remove = set()
    group = MapGroup(
        id=group_id,
        display_name="CredGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.put_by_id", side_effect=CredentialsError("credentials error"))
    with pytest.raises(CredentialsError) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert str(exc_info.value) == "credentials error"


def test_update_member_put_resource_invalid_when_map_error_and_not_found_pattern_false(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member_put raises ResourceInvalid when MapError.detail does not match MAP_NOT_FOUND_PATTERN."""
    group_id = gen_group_id("g_mem_inv")
    add = {"user1"}
    remove = set()
    group = MapGroup(
        id=group_id,
        display_name="InvalidGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    logger_mock = mocker.patch("flask.current_app.logger.info")
    map_error = MapError(detail="Some other error", status="400", scim_type="invalidValue")
    mocker.patch("server.clients.groups.put_by_id", return_value=map_error)
    mocker.patch("re.search", return_value=False)
    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert str(exc_info.value) == map_error.detail
    logger_mock.assert_called_once_with(map_error.detail)


def test_update_member_put_validation_error_on_validate_group_to_map_group(
    app: Flask, gen_group_id, mocker: MockerFixture
) -> None:
    """Test update_member_put raises UnexpectedResponseError when validate_group_to_map_group raises ValidationError."""
    group_id = gen_group_id("g_mem_valerr")
    add = {"user1"}
    remove = set()
    group = MapGroup(
        id=group_id,
        display_name="ValErrGroupPUT",
        public=True,
        member_list_visibility="Public",
        members=[],
        administrators=[],
        services=[],
    )
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.put_by_id", side_effect=ValidationError("validation error", []))
    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert "Failed to parse Group resource from mAP Core API." in str(exc_info.value)


def test_update_put_patch_strategy_propagates_exceptions(app, gen_group_id, mocker):

    group = MagicMock(spec=GroupDetail)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mocker.patch("server.services.groups.update", side_effect=ResourceInvalid("patch error"))
    with pytest.raises(ResourceInvalid) as exc_info:
        groups.update_put(group)
    assert str(exc_info.value) == "patch error"


def test_update_member_put_patch_strategy_propagates_exceptions(app, gen_group_id, mocker):
    group_id = gen_group_id("g_mem_patch2")
    add = {"user1"}
    remove = {"user2"}
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", new="patch")
    mocker.patch("server.services.groups.update_member", side_effect=ResourceNotFound("patch error"))
    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update_member_put(group_id, add, remove)
    assert str(exc_info.value) == "patch error"


def test_update_member_put_success(app, gen_group_id, mocker):
    group_id = gen_group_id("g_put_success")
    group = MapGroup(id=group_id, display_name="TestGroup", public=True, member_list_visibility="Public")
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=[])
    mocker.patch("server.clients.groups.put_by_id", return_value=group)
    # 追加で patch_by_id も mock する
    mocker.patch("server.clients.groups.patch_by_id", return_value=group)
    result = groups.update_member_put(group_id, add={"u1"}, remove={"u2"})
    assert isinstance(result, GroupDetail)
    assert result.display_name == "TestGroup"


def test_update_member_put_resource_not_found(app, mocker):
    group_id = "g_test"
    mocker.patch("server.services.groups.get_by_id", return_value=None)
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    with pytest.raises(ResourceNotFound) as exc_info:
        groups.update_member_put(group_id, add=None, remove=None)
    assert f"Group '{group_id}' Not Found" in str(exc_info.value)


def test_update_member_put_request_exception(app, gen_group_id, mocker):
    """Test update_member_put raises UnexpectedResponseError when RequestException occurs."""
    group_id = gen_group_id("g_put_reqexc")
    group = MapGroup(id=group_id, display_name="TestGroup", public=True, member_list_visibility="Public")
    mocker.patch.object(groups.config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.groups.get_by_id", return_value=group)
    mocker.patch("server.services.groups.get_access_token", return_value="token")
    mocker.patch("server.services.groups.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_system_admins", return_value=[])
    mocker.patch("server.clients.groups.put_by_id", side_effect=requests.RequestException("req error"))
    mocker.patch("server.clients.groups.patch_by_id", return_value=group)
    with pytest.raises(UnexpectedResponseError) as exc_info:
        groups.update_member_put(group_id, add={"u1"}, remove={"u2"})
    assert "Failed to communicate with mAP Core API." in str(exc_info.value)
