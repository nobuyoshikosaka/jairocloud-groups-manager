import typing as t

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
import requests

from pydantic_core import ValidationError
from requests import Response

from server.const import USER_ROLES
from server.entities.map_error import MapError
from server.entities.map_user import MapUser
from server.entities.search_request import SearchRequestParameter, SearchResponse, SearchResult
from server.entities.summaries import UserSummary
from server.entities.user_detail import RepositoryRole, UserDetail
from server.exc import (
    ApiClientError,
    CredentialsError,
    InvalidQueryError,
    OAuthTokenError,
    ResourceInvalid,
    ResourceNotFound,
    UnexpectedResponseError,
)
from server.services import users
from server.services.users import update, update_affiliations, update_put
from server.services.utils import (
    UsersCriteria,
    make_criteria_object,
)
from tests.helpers import load_json_data


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_search_success(app, mocker: MockerFixture) -> None:
    """Test that search returns SearchResponse[MapUser] with correct params."""

    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    search_param = SearchRequestParameter(
        filter='displayName co "Test"',
        start_index=11,
        count=10,
        sort_by="display_name",
        sort_order="ascending",
    )
    user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    expected_result = SearchResponse[MapUser](
        total_results=1,
        items_per_page=1,
        start_index=1,
        resources=[user],
    )

    mocker.patch("server.services.users.build_search_query", return_value=search_param)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", return_value=expected_result)
    result = users.search(criteria, raw=True)
    assert isinstance(result, SearchResponse)
    assert result == expected_result


def test_search_returns_search_result_user_summary(app, mocker: MockerFixture) -> None:
    """Test that search returns SearchResult[UserSummary] when raw=False (default)."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    search_param = SearchRequestParameter(filter='userName eq "u"')
    user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    expected_result = SearchResponse[MapUser](
        total_results=1,
        items_per_page=1,
        start_index=1,
        resources=[user],
    )
    mocker.patch("server.services.users.build_search_query", return_value=search_param)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", return_value=expected_result)
    result = users.search(criteria)
    summary = result.resources[0]
    user = expected_result.resources[0]

    assert isinstance(result, SearchResult)
    assert result.total == expected_result.total_results
    assert result.page_size == expected_result.items_per_page
    assert result.offset == expected_result.start_index
    assert len(result.resources) == len(expected_result.resources)
    assert isinstance(result.resources[0], UserSummary)

    assert summary.id == user.id
    assert summary.user_name == user.user_name
    assert summary.emails == user.emails


def test_search_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Test that OAuthTokenError is raised when HTTP 401 occurs."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch(
        "server.services.users.build_search_query", return_value=SearchRequestParameter(filter='userName eq "u"')
    )
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")

    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.search(criteria)


def test_search_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Test that UnexpectedResponseError is raised when HTTP 500 occurs."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch(
        "server.services.users.build_search_query", return_value=SearchRequestParameter(filter='userName eq "u"')
    )
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")

    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.search(criteria)


def test_search_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Test that UnexpectedResponseError is raised for other HTTP errors."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch(
        "server.services.users.build_search_query", return_value=SearchRequestParameter(filter='userName eq "u"')
    )
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")

    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.search(criteria)


def test_search_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Test that UnexpectedResponseError is raised on requests.RequestException."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch(
        "server.services.users.build_search_query", return_value=SearchRequestParameter(filter='userName eq "u"')
    )
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.search(criteria)


def test_search_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Test that UnexpectedResponseError is raised on ValidationError."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch(
        "server.services.users.build_search_query", return_value=SearchRequestParameter(filter='userName eq "u"')
    )
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.search(criteria)


def test_search_reraises_invalid_query_error(mocker: MockerFixture) -> None:
    """Test that search re-raises InvalidQueryError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=InvalidQueryError("fail"))
    with pytest.raises(InvalidQueryError):
        users.search(criteria)


def test_search_reraises_oauth_token_error(mocker: MockerFixture) -> None:
    """Test that search re-raises OAuthTokenError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.search(criteria)


def test_search_reraises_credentials_error(mocker: MockerFixture) -> None:
    """Test that search re-raises CredentialsError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.search(criteria)


def test_search_raises_invalid_query_error_on_map_error(app, mocker: MockerFixture) -> None:
    """Test that InvalidQueryError is raised when MapError is returned."""
    criteria: UsersCriteria = make_criteria_object("users", q='userName eq "u"')
    search_param = SearchRequestParameter(filter='userName eq "u"')
    map_error = MapError(detail="invalid query", status="400", scim_type="invalidSyntax")
    mocker.patch("server.services.users.build_search_query", return_value=search_param)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")
    with pytest.raises(InvalidQueryError):
        users.search(criteria)
    assert mock_logger.called


def test_get_by_id_success(app, mocker: MockerFixture) -> None:
    """Test get_by_id returns UserDetail on success."""

    user_id = "u1"
    map_user = MapUser(id=user_id, user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_id", return_value=map_user)
    result = users.get_by_id(user_id)
    assert isinstance(result, UserDetail)
    assert result.id == user_id


def test_get_by_id_success_raw(app, mocker: MockerFixture) -> None:
    """Test get_by_id returns MapUser when raw=True."""

    user_id = "u1"
    map_user = MapUser(id=user_id, user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_id", return_value=map_user)
    result = users.get_by_id(user_id, raw=True)
    assert isinstance(result, MapUser)
    assert result.id == user_id


def test_get_by_id_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Test get_by_id raises OAuthTokenError on HTTP 401."""
    user_id = "u1"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_id", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.get_by_id(user_id)


def test_get_by_id_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError on HTTP 500."""
    user_id = "u1"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_id", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.get_by_id(user_id)


def test_get_by_id_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError on other HTTP errors."""
    user_id = "u1"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_id", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.get_by_id(user_id)


def test_get_by_id_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError on requests.RequestException."""
    user_id = "u1"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_id", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.get_by_id(user_id)


def test_get_by_id_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Test get_by_id raises UnexpectedResponseError on ValidationError."""
    user_id = "u1"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_id", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.get_by_id(user_id)


def test_get_by_id_reraises_oauth_token_error(mocker: MockerFixture) -> None:
    """Test get_by_id re-raises OAuthTokenError directly from try block."""
    mocker.patch("server.services.users.get_access_token", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.get_by_id("u1")


def test_get_by_id_reraises_credentials_error(mocker: MockerFixture) -> None:
    """Test get_by_id re-raises CredentialsError directly from try block."""
    mocker.patch("server.services.users.get_access_token", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.get_by_id("u1")


def test_get_by_id_returns_none_on_map_error(app, mocker: MockerFixture) -> None:
    """Test get_by_id returns None and logs when MapError is returned."""

    user_id = "u1"
    map_error = MapError(detail="not found", status="404", scim_type="noTarget")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")
    result = users.get_by_id(user_id)
    assert result is None
    assert mock_logger.called


def test_get_by_eppn_success(app, mocker: MockerFixture) -> None:
    """Test get_by_eppn returns UserDetail on success."""

    eppn = "user@example.jp"
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_eppn", return_value=map_user)
    result = users.get_by_eppn(eppn)
    assert isinstance(result, UserDetail)
    assert result.id == "u1"


def test_get_by_eppn_success_raw(app, mocker: MockerFixture) -> None:
    """Test get_by_eppn returns MapUser when raw=True."""

    eppn = "user@example.jp"
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_eppn", return_value=map_user)
    result = users.get_by_eppn(eppn, raw=True)
    assert isinstance(result, MapUser)
    assert result.id == "u1"


def test_get_by_eppn_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Test get_by_eppn raises OAuthTokenError on HTTP 401."""
    eppn = "user@example.jp"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_eppn", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.get_by_eppn(eppn)


def test_get_by_eppn_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Test get_by_eppn raises UnexpectedResponseError on HTTP 500."""
    eppn = "user@example.jp"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_eppn", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.get_by_eppn(eppn)


def test_get_by_eppn_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Test get_by_eppn raises UnexpectedResponseError on other HTTP errors."""
    eppn = "user@example.jp"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.get_by_eppn", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.get_by_eppn(eppn)


def test_get_by_eppn_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Test get_by_eppn raises UnexpectedResponseError on requests.RequestException."""
    eppn = "user@example.jp"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_eppn", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.get_by_eppn(eppn)


def test_get_by_eppn_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Test get_by_eppn raises UnexpectedResponseError on ValidationError."""
    eppn = "user@example.jp"
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_eppn", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.get_by_eppn(eppn)


def test_get_by_eppn_returns_none_on_map_error(app, mocker: MockerFixture) -> None:
    """Test get_by_eppn returns None and logs when MapError is returned."""

    eppn = "user@example.jp"
    map_error = MapError(detail="not found", status="404", scim_type="noTarget")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.get_by_eppn", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")
    result = users.get_by_eppn(eppn)
    assert result is None
    assert mock_logger.called


def test_get_by_eppn_reraises_oauth_token_error(mocker: MockerFixture) -> None:
    """Test get_by_eppn re-raises OAuthTokenError directly from try block."""
    mocker.patch("server.services.users.get_access_token", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.get_by_eppn("user@example.jp")


def test_get_by_eppn_reraises_credentials_error(mocker: MockerFixture) -> None:
    """Test get_by_eppn re-raises CredentialsError directly from try block."""
    mocker.patch("server.services.users.get_access_token", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.get_by_eppn("user@example.jp")


def test_create_success(app, mocker: MockerFixture) -> None:
    """Test create returns UserDetail on success."""
    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.clients.users.post", return_value=map_user)
    result = users.create(user)
    assert isinstance(result, UserDetail)
    assert result.id == "u1"


def test_create_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.post", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.create(user)


def test_create_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.post", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.create(user)


def test_create_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.post", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.create(user)


def test_create_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.post", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.create(user)


def test_create_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.post", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.create(user)


def test_create_reraises_oauth_token_error(mocker: MockerFixture) -> None:
    """Test create re-raises OAuthTokenError directly from try block."""
    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.create(user)


def test_create_reraises_credentials_error(mocker: MockerFixture) -> None:
    """Test create re-raises CredentialsError directly from try block."""
    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.create(user)


def test_create_raises_resource_invalid_on_map_error(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.services.users.prepare_user", return_value=map_user)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.post", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")
    with pytest.raises(users.ResourceInvalid):
        users.create(user)
    assert mock_logger.called


def test_update_success(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mocker.patch("server.clients.users.patch_by_id", return_value=map_user)
    result = users.update(user)
    assert isinstance(result, UserDetail)
    assert result.id == "u1"


def test_update_raises_resource_not_found_on_none(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    mocker.patch("server.services.users.get_by_id", return_value=None)
    with pytest.raises(users.ResourceNotFound):
        users.update(user)


def test_update_raises_oauth_token_error_on_unauthorized(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.patch_by_id", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.update(user)


def test_update_raises_unexpected_response_error_on_internal_server_error(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.patch_by_id", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.update(user)


def test_update_raises_unexpected_response_error_on_other_http_error(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.patch_by_id", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.update(user)


def test_update_raises_unexpected_response_error_on_request_exception(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mocker.patch("server.clients.users.patch_by_id", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.update(user)


def test_update_raises_unexpected_response_error_on_validation_error(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mocker.patch("server.clients.users.patch_by_id", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.update(user)


def test_update_reraises_oauth_token_error(app, mocker: MockerFixture) -> None:
    """Test update re-raises OAuthTokenError directly from try block."""
    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mocker.patch("server.services.users.get_access_token", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.update(user)


def test_update_reraises_credentials_error(app, mocker: MockerFixture) -> None:
    """Test update re-raises CredentialsError directly from try block."""
    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mocker.patch("server.services.users.get_access_token", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.update(user)


def test_update_raises_resource_not_found_on_map_error_with_not_found_pattern(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    map_error = MapError(detail="'u1' Not Found", status="404", scim_type="noTarget")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mocker.patch("server.clients.users.patch_by_id", return_value=map_error)
    with pytest.raises(users.ResourceNotFound):
        users.update(user)
    assert mock_logger.called


def test_update_raises_resource_invalid_on_map_error(app, mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[])
    map_user = MapUser(id="u1", user_name="u", schemas=["a"], emails=[])
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.get_by_id", return_value=user)
    mocker.patch("server.services.users.validate_user_to_map_user", return_value=map_user)
    mocker.patch("server.services.users.build_patch_operations", return_value=["patchop"])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mocker.patch("server.clients.users.patch_by_id", return_value=map_error)
    with pytest.raises(users.ResourceInvalid):
        users.update(user)
    assert mock_logger.called


@pytest.mark.parametrize(
    ("editable", "strategy"), [(False, "patch"), (False, "put")], ids=["editable_false_patch", "editable_false_put"]
)
def test_update_put_affiliations_called(
    app, test_config, mocker: MockerFixture, *, editable: bool, strategy: str
) -> None:
    user = MagicMock(spec=UserDetail)
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=editable)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", new=strategy)
    update_affiliations = mocker.patch("server.services.users.update_affiliations", return_value="updated")

    result = update_put(user)
    assert result == "updated"
    update_affiliations.assert_called_once_with(user)


@pytest.mark.parametrize(("editable", "strategy"), [(True, "patch")], ids=["editable_true_patch"])
def test_update_put_patch_called(app, test_config, mocker: MockerFixture, *, editable: bool, strategy: str) -> None:
    user = MagicMock(spec=UserDetail)
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=editable)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", new=strategy)
    update = mocker.patch("server.services.users.update", return_value="patched")

    result = update_put(user)
    assert result == "patched"
    update.assert_called_once_with(user)


def test_update_put_success(app, test_config, mocker: MockerFixture) -> None:

    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", "put")
    validated = MagicMock()
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=validated)
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    result_map = MagicMock(spec=MapUser)

    mocker.patch("server.services.users.users.put_by_id", return_value=result_map)
    mocker.patch("server.services.users.UserDetail.from_map_user", return_value="user_detail")

    result = update_put(user)
    assert result == "user_detail"


@pytest.mark.parametrize(
    ("status", "exc_type", "expected"),
    [
        (HTTPStatus.UNAUTHORIZED, OAuthTokenError, "Access token is invalid or expired."),
        (HTTPStatus.INTERNAL_SERVER_ERROR, UnexpectedResponseError, "mAP Core API server error."),
        (HTTPStatus.BAD_REQUEST, UnexpectedResponseError, "Failed to update User resource in mAP Core API."),
    ],
    ids=["unauthorized", "server_error", "other_http_error"],
)
def test_update_put_http_error(
    app, test_config, mocker: MockerFixture, status: int, exc_type: type[Exception], expected: str
) -> None:

    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.get_by_id", return_value=True)

    http_exc = MagicMock()
    http_exc.response.status_code = status
    mocker.patch(
        "server.services.users.users.put_by_id",
        side_effect=requests.HTTPError(response=http_exc.response),
    )

    with pytest.raises(exc_type) as e:
        update_put(user)
    assert expected in str(e.value)


def test_update_put_request_exception(app, test_config, mocker: MockerFixture) -> None:
    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.users.put_by_id", side_effect=requests.RequestException())
    mocker.patch("server.services.repositories.get_by_id", return_value=True)

    with pytest.raises(UnexpectedResponseError) as e:
        update_put(user)
    assert "Failed to communicate with mAP Core API." in str(e.value)


def test_update_put_validation_error(app, test_config, mocker: MockerFixture) -> None:
    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.users.put_by_id", side_effect=ValidationError("fail", []))
    mocker.patch("server.services.repositories.get_by_id", return_value=True)

    with pytest.raises(UnexpectedResponseError) as e:
        update_put(user)
    assert "Failed to parse User resource from mAP Core API." in str(e.value)


@pytest.mark.parametrize("exc_type", [OAuthTokenError, CredentialsError], ids=["oauth_error", "credentials_error"])
def test_update_put_token_or_credentials_error(
    app, test_config, mocker: MockerFixture, exc_type: type[Exception]
) -> None:
    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", "put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.users.users.put_by_id", side_effect=exc_type("fail"))
    mocker.patch("server.services.repositories.get_by_id", return_value=True)

    with pytest.raises(exc_type):
        update_put(user)


@pytest.mark.parametrize("editable", [False], ids=["user_editable_false"])
def test_update_delegates_to_update_affiliations(app, test_config, mocker, editable):
    user = MagicMock(spec=UserDetail)
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=editable)
    mock_update_affiliations = mocker.patch.object(users, "update_affiliations", return_value="affiliated")
    result = update(user)
    assert result == "affiliated"
    mock_update_affiliations.assert_called_once_with(user)


@pytest.mark.parametrize("strategy", ["put"], ids=["update_strategy_put"])
def test_update_delegates_to_update_put(app, test_config, mocker, strategy):
    user = MagicMock(spec=UserDetail)
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", new=strategy)
    mock_update_affiliations = mocker.patch.object(users, "update_put", return_value="put_result")
    result = update(user)
    assert result == "put_result"
    mock_update_affiliations.assert_called_once_with(user)


@pytest.mark.parametrize("detail", ["User 'u1' Not Found"], ids=["map_not_found_pattern"])
def test_update_put_map_error_not_found(app, test_config, mocker, detail):
    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    map_error = MagicMock(spec=users.MapError)
    map_error.detail = detail
    mocker.patch("server.services.users.users.put_by_id", return_value=map_error)
    mocker.patch("flask.current_app.logger.info")
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    with pytest.raises(ResourceNotFound):
        update_put(user)


@pytest.mark.parametrize("detail", ["invalid"], ids=["map_error_invalid"])
def test_update_put_map_error_invalid(app, test_config, mocker, detail):
    repo_role = RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)
    user = UserDetail(id="u1", user_name="u", emails=[], repository_roles=[repo_role])
    mocker.patch.object(test_config.MAP_CORE, "user_editable", new=True)
    mocker.patch.object(test_config.MAP_CORE, "update_strategy", new="put")
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    map_error = MagicMock(spec=users.MapError)
    map_error.detail = detail
    mocker.patch("server.services.users.users.put_by_id", return_value=map_error)
    mocker.patch("flask.current_app.logger.info")
    with pytest.raises(ResourceInvalid):
        update_put(user)


def test_update_affiliations_get_by_id_none(app, mocker):
    user = MagicMock(spec=UserDetail)
    user.id = "u1"
    mocker.patch("server.services.users.get_by_id", return_value=None)
    with pytest.raises(ResourceNotFound):
        update_affiliations(user)


def test_update_affiliations_add_op_success(app, mocker):
    user = UserDetail(
        id="u1",
        user_name="u",
        emails=[],
        repository_roles=[RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    patch_op = MagicMock()
    patch_op.op = "add"
    patch_op.value = MagicMock()
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mock_groups = mocker.patch("server.services.groups.update_member")
    mock_user_updated = mocker.patch("server.services.users.user_updated.send")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    result = users.update_affiliations(user)
    mock_groups.assert_called()
    assert mock_logger.called
    mock_user_updated.assert_called()
    assert result == current


def test_update_affiliations_replace_op_skipped(app, mocker):
    user = UserDetail(
        id="u2",
        user_name="u2",
        emails=[],
        repository_roles=[RepositoryRole(id="repo2", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    patch_op = MagicMock()
    patch_op.op = "replace"
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mock_groups = mocker.patch("server.services.groups.update_member")
    mock_user_updated = mocker.patch("server.services.users.user_updated.send")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    result = users.update_affiliations(user)
    mock_groups.assert_not_called()
    assert mock_logger.called
    mock_user_updated.assert_called()
    assert result == current


def test_update_affiliations_remove_op_regex_success(app, mocker):
    user = UserDetail(
        id="u3",
        user_name="u3",
        emails=[],
        repository_roles=[RepositoryRole(id="repo3", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    patch_op = MagicMock()
    patch_op.op = "remove"
    patch_op.path = 'groups[value eq "group1"]'
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mock_groups = mocker.patch("server.services.groups.update_member")
    mock_user_updated = mocker.patch("server.services.users.user_updated.send")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    result = users.update_affiliations(user)
    mock_groups.assert_called()
    assert mock_logger.called
    mock_user_updated.assert_called()
    assert result == current


def test_update_affiliations_remove_op_regex_fail(app, mocker):
    user = UserDetail(
        id="u4",
        user_name="u4",
        emails=[],
        repository_roles=[RepositoryRole(id="repo4", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    patch_op = MagicMock()
    patch_op.op = "remove"
    patch_op.path = 'groups[invalid eq "group1"]'
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mock_groups = mocker.patch("server.services.groups.update_member")
    mock_user_updated = mocker.patch("server.services.users.user_updated.send")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    result = users.update_affiliations(user)
    mock_groups.assert_not_called()
    assert mock_logger.called
    mock_user_updated.assert_called()
    assert result == current


def test_update_affiliations_group_update_error_collects_and_raises(app, mocker):
    user = UserDetail(
        id="u5",
        user_name="u5",
        emails=[],
        repository_roles=[RepositoryRole(id="repo5", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.repositories.get_by_id", return_value=True)
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=MagicMock())
    patch_op = MagicMock()
    patch_op.op = "add"
    patch_op.value = MagicMock()
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mock_logger = mocker.patch("flask.current_app.logger.info")
    mocker.patch("server.services.groups.update_member", side_effect=ApiClientError("fail"))
    mock_user_updated = mocker.patch("server.services.users.user_updated.send")
    mocker.patch("server.services.users.get_by_id", return_value=current)
    with pytest.raises(ExceptionGroup) as exc_info:
        users.update_affiliations(user)
    assert any(isinstance(e, ApiClientError) for e in exc_info.value.exceptions)
    assert mock_logger.called
    mock_user_updated.assert_called()


def test_update_affiliations_not_found(app, mocker):
    user = UserDetail(
        id="u6",
        user_name="u6",
        emails=[],
        repository_roles=[RepositoryRole(id="repo6", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    mocker.patch("server.services.users.get_by_id", return_value=None)
    with pytest.raises(ResourceNotFound):
        users.update_affiliations(user)


def test_get_system_admins_success(mocker: MockerFixture) -> None:

    map_user1 = MapUser(id="u1", user_name="u1", schemas=["a"], emails=[])
    map_user2 = MapUser(id="u2", user_name="u2", schemas=["a"], emails=[])
    mocker.patch("server.services.users.search", return_value=type("obj", (), {"resources": [map_user1, map_user2]})())
    result = users.get_system_admins()
    assert isinstance(result, set)
    assert result == {"u1", "u2"}


def test_get_system_admins_success_raw(mocker: MockerFixture) -> None:

    map_user1 = MapUser(id="u1", user_name="u1", schemas=["a"], emails=[])
    map_user2 = MapUser(id="u2", user_name="u2", schemas=["a"], emails=[])
    mocker.patch("server.services.users.search", return_value=type("obj", (), {"resources": [map_user1, map_user2]})())
    result = users.get_system_admins(raw=True)
    assert isinstance(result, list)
    assert all(isinstance(u, MapUser) for u in result)
    assert {u.id for u in result} == {"u1", "u2"}


def test_count_success(mocker: MockerFixture) -> None:
    """Test count returns total_results on success."""
    total_results = 42
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mock_result = type("obj", (), {"total_results": total_results})()
    mocker.patch("server.clients.users.search", return_value=mock_result)
    result = users.count(criteria)
    assert result == total_results


def test_count_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Test count raises OAuthTokenError on HTTP 401."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(OAuthTokenError):
        users.count(criteria)


def test_count_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Test count raises UnexpectedResponseError on HTTP 500."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.count(criteria)


def test_count_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Test count raises UnexpectedResponseError on other HTTP errors."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.users.search", side_effect=http_error)
    with pytest.raises(UnexpectedResponseError):
        users.count(criteria)


def test_count_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Test count raises UnexpectedResponseError on requests.RequestException."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", side_effect=requests.RequestException("fail"))
    with pytest.raises(UnexpectedResponseError):
        users.count(criteria)


def test_count_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Test count raises UnexpectedResponseError on ValidationError."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    mocker.patch("server.clients.users.search", side_effect=ValidationError("fail", []))
    with pytest.raises(UnexpectedResponseError):
        users.count(criteria)


def test_count_reraises_invalid_query_error(mocker: MockerFixture) -> None:
    """Test count re-raises InvalidQueryError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=InvalidQueryError("fail"))
    with pytest.raises(InvalidQueryError):
        users.count(criteria)


def test_count_reraises_oauth_token_error(mocker: MockerFixture) -> None:
    """Test count re-raises OAuthTokenError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=OAuthTokenError("fail"))
    with pytest.raises(OAuthTokenError):
        users.count(criteria)


def test_count_reraises_credentials_error(mocker: MockerFixture) -> None:
    """Test count re-raises CredentialsError directly from try block."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", side_effect=users.CredentialsError("fail"))
    with pytest.raises(users.CredentialsError):
        users.count(criteria)


def test_count_raises_invalid_query_error_on_map_error(app, mocker: MockerFixture) -> None:
    """Test count raises InvalidQueryError and logs when MapError is returned."""
    criteria = make_criteria_object("users", q='userName eq "u"')
    mocker.patch("server.services.users.build_search_query", return_value="query")
    mocker.patch("server.services.users.get_access_token", return_value="token")
    mocker.patch("server.services.users.get_client_secret", return_value="secret")
    map_error = MapError(detail="invalid query", status="400", scim_type="invalidSyntax")
    mocker.patch("server.clients.users.search", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")
    with pytest.raises(InvalidQueryError):
        users.count(criteria)
    assert mock_logger.called


@pytest.fixture
def user_data() -> tuple[dict[str, t.Any], MapUser]:
    json_data = load_json_data("data/map_user.json")
    user = MapUser.model_validate(json_data)
    return json_data, user


def test_handle_user_updated_eppns_true(mocker: MockerFixture) -> None:

    user = UserDetail(id="u1", user_name="u", emails=[], eppns=["eppn1"])
    mock_clear_id = mocker.patch("server.services.users.users.get_by_id.clear_cache")
    mock_clear_eppn = mocker.patch("server.services.users.users.get_by_eppn.clear_cache")
    users.handle_user_updated(_sender=None, user=user)
    mock_clear_id.assert_called_once_with("u1")
    mock_clear_eppn.assert_called_once_with("eppn1")


def test_handle_user_updated_eppns_false(mocker: MockerFixture) -> None:

    user = UserDetail(id="u2", user_name="u2", emails=[], eppns=[])
    mock_clear_id = mocker.patch("server.services.users.users.get_by_id.clear_cache")
    mock_clear_eppn = mocker.patch("server.services.users.users.get_by_eppn.clear_cache")

    users.handle_user_updated(_sender=None, user=user)
    mock_clear_id.assert_called_once_with("u2")
    mock_clear_eppn.assert_not_called()


def test_update_affiliations_raises_oauth_token_error(app, mocker):
    user = UserDetail(
        id="u1",
        user_name="u",
        emails=[],
        repository_roles=[RepositoryRole(id="repo1", user_role=USER_ROLES.SYSTEM_ADMIN)],
        is_system_admin=False,
    )
    current = MagicMock(spec=UserDetail)
    mocker.patch("server.services.users.get_by_id", return_value=current)
    mocker.patch("server.services.utils.transformers.validate_user_to_map_user", return_value=current)
    patch_op = MagicMock()
    patch_op.op = "add"
    patch_op.value = MagicMock()
    mocker.patch("server.services.users.build_patch_operations", return_value=[patch_op])
    mocker.patch("server.services.groups.update_member", side_effect=OAuthTokenError("fail"))
    mocker.patch("server.services.repositories.get_by_id", return_value=object())
    mocker.patch("server.services.users.user_updated.send")
    with pytest.raises(OAuthTokenError):
        users.update_affiliations(user)
