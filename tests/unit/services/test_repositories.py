import typing as t

from http import HTTPStatus

import pytest
import requests

from pydantic import HttpUrl
from pydantic_core import ValidationError
from requests import Response

from server import const
from server.entities.map_error import MapError
from server.entities.map_service import MapService, ServiceEntityID
from server.entities.repository_detail import RepositoryDetail
from server.entities.search_request import SearchResponse, SearchResult
from server.entities.summaries import RepositorySummary
from server.services import repositories


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture
from server.services.utils import make_criteria_object


def test_search_success(app, mocker: MockerFixture, test_config) -> None:
    """Tests successful search for repositories and validates the returned SearchResult."""

    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    map_service = MapService(
        id="repo1",
        service_name="TestRepo",
        service_url=service_url,
        schemas=[const.MAP_SERVICE_SCHEMA],
        entity_ids=[],
    )
    expected_result = SearchResponse[MapService](
        total_results=1,
        items_per_page=1,
        start_index=1,
        resources=[map_service],
    )
    expected = expected_result.resources[0]
    mocker.patch("server.services.repositories.resolve_repository_id", return_value="repo1")
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.search", return_value=expected_result)

    result = repositories.search(criteria)

    actual = result.resources[0]
    assert isinstance(result, SearchResult)
    assert result.total == expected_result.total_results
    assert result.page_size == expected_result.items_per_page
    assert result.offset == expected_result.start_index
    assert len(result.resources) == len(expected_result.resources)
    assert isinstance(result.resources[0], RepositorySummary)
    assert actual.id == expected.id
    assert actual.service_name == expected.service_name
    assert actual.service_url == expected.service_url
    assert actual.entity_ids == [eid.value for eid in (expected.entity_ids or [])]


def test_search_returns_raw_response(app, mocker: MockerFixture, test_config) -> None:
    """Tests that the raw SearchResponse is returned when raw=True is specified."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id="repo1")
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    map_service = MapService(
        id=service_id,
        service_name=service_name,
        service_url=service_url,
        schemas=[service_schema],
        entity_ids=[],
    )
    expected_result = SearchResponse[MapService](
        total_results=1,
        items_per_page=1,
        start_index=1,
        resources=[map_service],
    )
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.search", return_value=expected_result)

    result = repositories.search(criteria, raw=True)

    assert result is expected_result


def test_search_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised when search receives an unauthorized response."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.search", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.search(criteria)

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_search_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during search."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.search", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.search(criteria)

    assert "mAP Core API server error" in str(excinfo.value)


def test_search_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on non-500 HTTP errors during search."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.search", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.search(criteria)

    assert "Failed to search Repository resources from mAP Core API" in str(excinfo.value)


def test_search_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during search."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.search", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.search(criteria)

    assert "Failed to communicate with mAP Core API" in str(excinfo.value)


def test_search_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during search."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.search", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.search(criteria)

    assert "Failed to parse Repository resources from mAP Core API" in str(excinfo.value)


def test_search_raises_invalid_query_error_direct(mocker: MockerFixture) -> None:
    """Tests that InvalidQueryError is raised directly from build_search_query."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.repositories.build_search_query", side_effect=repositories.InvalidQueryError("criteria error")
    )

    with pytest.raises(repositories.InvalidQueryError) as excinfo:
        repositories.search(criteria)

    assert "criteria error" in str(excinfo.value)


def test_search_raises_oauth_token_error_direct(mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised directly from build_search_query."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.repositories.build_search_query", side_effect=repositories.OAuthTokenError("token error")
    )

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.search(criteria)

    assert "token error" in str(excinfo.value)


def test_search_raises_credentials_error_direct(mocker: MockerFixture) -> None:
    """Tests that CredentialsError is raised directly from build_search_query."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.repositories.build_search_query", side_effect=repositories.CredentialsError("cred error")
    )

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.search(criteria)

    assert "cred error" in str(excinfo.value)


def test_search_raises_invalid_query_error_on_map_error(app, mocker: MockerFixture) -> None:
    """Tests that InvalidQueryError is raised when MapError is returned from search."""
    criteria = make_criteria_object("repositories", q="test", i=["repo1"])
    map_error = MapError(detail="invalid query", status="400", scim_type="invalidSyntax")
    mocker.patch("server.services.repositories.build_search_query", return_value=criteria)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.search", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.InvalidQueryError) as excinfo:
        repositories.search(criteria)

    assert mock_logger.called
    assert "invalid query" in str(excinfo.value)


def test_get_by_id_success(app, mocker: MockerFixture, test_config) -> None:
    """Tests successful retrieval of a repository by ID with raw response."""

    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id="repo1")
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    map_service = MapService(
        id=service_id,
        service_name=service_name,
        service_url=service_url,
        schemas=[service_schema],
        entity_ids=[],
    )
    mocker.patch("server.services.repositories.resolve_service_id", return_value=service_id)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", return_value=map_service)

    result = repositories.get_by_id("repo1", raw=True)

    assert result is map_service


def test_get_by_id_returns_repository_detail(app, mocker: MockerFixture, test_config) -> None:
    """Tests that get_by_id returns RepositoryDetail when raw is False (default)."""
    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id="repo1")
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    map_service = MapService(
        id=service_id,
        service_name=service_name,
        service_url=service_url,
        schemas=[service_schema],
        entity_ids=[ServiceEntityID(value="e1"), ServiceEntityID(value="e2")],
    )
    mocker.patch("server.services.repositories.resolve_service_id", return_value=service_id)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", return_value=map_service)

    result = repositories.get_by_id("repo1")

    assert isinstance(result, RepositoryDetail)
    assert result.id == repository_id
    assert result.service_name == service_name
    assert str(result.service_url) == str(service_url)
    assert result.entity_ids == ["e1", "e2"]


def test_get_by_id_more_detail(app, mocker: MockerFixture, test_config) -> None:
    """Tests that get_by_id returns RepositoryDetail with more_detail=True."""
    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id=repository_id)
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    map_service = MapService(
        id=service_id,
        service_name=service_name,
        service_url=service_url,
        schemas=[service_schema],
        entity_ids=[],
    )
    mocker.patch("server.services.repositories.resolve_service_id", return_value=service_id)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", return_value=map_service)

    result = repositories.get_by_id("repo1", more_detail=True)

    assert isinstance(result, RepositoryDetail)
    assert result.id == repository_id
    assert result.service_name == service_name
    assert str(result.service_url) == str(service_url)


def test_get_by_id_returns_none_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that get_by_id returns None when MapError is returned."""
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id="repo1")
    map_error = MapError(detail="not found", status="404", scim_type="invalidSyntax")
    mocker.patch("server.services.repositories.resolve_service_id", return_value=service_id)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    result = repositories.get_by_id("repo1")

    assert result is None
    assert mock_logger.called


def test_get_by_id_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised when get_by_id receives an unauthorized response."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.get_by_id", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.get_by_id("repo1")

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_get_by_id_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.get_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.get_by_id("repo1")

    assert "mAP Core API server error" in str(excinfo.value)


def test_get_by_id_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.get_by_id("repo1")

    assert "Failed to connect to mAP Core API" in str(excinfo.value)


def test_get_by_id_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.get_by_id("repo1")

    assert "Failed to parse response from mAP Core API" in str(excinfo.value)


def test_get_by_id_raises_oauth_token_error_direct(mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised directly from get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", side_effect=repositories.OAuthTokenError("token error"))

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.get_by_id("repo1")

    assert "token error" in str(excinfo.value)


def test_get_by_id_raises_credentials_error_direct(mocker: MockerFixture) -> None:
    """Tests that CredentialsError is raised directly from get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.get_by_id", side_effect=repositories.CredentialsError("cred error"))

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.get_by_id("repo1")

    assert "cred error" in str(excinfo.value)


def test_get_by_id_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture) -> None:
    """Tests that UnexpectedResponseError is raised on non-401/500 HTTP errors during get_by_id."""
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.get_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.get_by_id("repo1")

    assert "Failed to get Repository resource from mAP Core API" in str(excinfo.value)


def test_create_success(app, mocker: MockerFixture, test_config) -> None:
    """Tests successful creation of a repository and validates the returned RepositoryDetail."""

    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id=repository_id)
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    repo = RepositoryDetail(id=service_id, service_name=service_name, service_url=service_url, entity_ids=[])
    map_service = MapService(
        id=service_id, service_name=service_name, service_url=service_url, schemas=[service_schema], entity_ids=[]
    )
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(map_service, service_id))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", return_value=map_service)

    result = repositories.create(repo)

    assert isinstance(result, RepositoryDetail)
    assert result.id == repository_id
    assert result.service_name == service_name
    assert str(result.service_url) == str(service_url)


def test_create_raises_oauth_token_error_on_unauthorized(mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised when create receives an unauthorized response."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.post", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.create(repo)

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_create_raises_unexpected_response_error_on_internal_server_error(mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.post", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.create(repo)

    assert "mAP Core API server error" in str(excinfo.value)


def test_create_raises_unexpected_response_error_on_request_exception(mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.create(repo)

    assert "Failed to connect to mAP Core API" in str(excinfo.value)


def test_create_raises_unexpected_response_error_on_validation_error(mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.create(repo)

    assert "Failed to parse response from mAP Core API" in str(excinfo.value)


def test_create_raises_resource_invalid_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceInvalid is raised when MapError is returned from create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.ResourceInvalid) as excinfo:
        repositories.create(repo)

    assert mock_logger.called
    assert "invalid" in str(excinfo.value)


def test_create_raises_oauth_token_error_direct(mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised directly from create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=repositories.OAuthTokenError("token error"))

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.create(repo)

    assert "token error" in str(excinfo.value)


def test_create_raises_credentials_error_direct(mocker: MockerFixture, test_config) -> None:
    """Tests that CredentialsError is raised directly from create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=repositories.CredentialsError("cred error"))

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.create(repo)

    assert "cred error" in str(excinfo.value)


def test_create_raises_invalid_form_error_direct(mocker: MockerFixture, test_config) -> None:
    """Tests that InvalidFormError is raised directly from create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=repositories.InvalidFormError("form error"))

    with pytest.raises(repositories.InvalidFormError) as excinfo:
        repositories.create(repo)

    assert "form error" in str(excinfo.value)


def test_create_raises_system_admin_not_found_direct(mocker: MockerFixture, test_config) -> None:
    """Tests that SystemAdminNotFound is raised directly from create."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", side_effect=repositories.SystemAdminNotFound("admin not found"))

    with pytest.raises(repositories.SystemAdminNotFound) as excinfo:
        repositories.create(repo)

    assert "admin not found" in str(excinfo.value)


def test_create_raises_unexpected_response_error_on_other_http_error(mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on non-401/500 HTTP errors during create."""
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=[])
    mocker.patch("server.services.repositories.prepare_service", return_value=(mocker.MagicMock(), "repo1"))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.groups.post")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.post", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.create(repo)

    assert "Failed to create Repository resource in mAP Core API" in str(excinfo.value)


@pytest.mark.parametrize(
    "role_groups",
    [
        [["group1"], ["group2"]],
        [[]],
    ],
    ids=["multiple-groups", "empty-groups"],
)
def test_create_calls_groups_post_for_each_group(app, mocker: MockerFixture, test_config, role_groups: list) -> None:
    """Tests that groups.post is called for each group in role_groups during create."""
    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id=repository_id)
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    repo = RepositoryDetail(id=service_id, service_name=service_name, service_url=service_url, entity_ids=[])
    map_service = MapService(
        id=service_id, service_name=service_name, service_url=service_url, schemas=[service_schema], entity_ids=[]
    )
    mocker.patch("server.services.repositories.get_system_admins", return_value=["admin"])
    mocker.patch("server.services.repositories.prepare_role_groups", return_value=role_groups)
    mocker.patch("server.services.repositories.prepare_service", return_value=(map_service, service_id))
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mock_groups_post = mocker.patch("server.clients.groups.post")
    mocker.patch("server.clients.services.post", return_value=map_service)

    repositories.create(repo)

    assert mock_groups_post.call_count == len(role_groups)


def test_update_success(app, mocker: MockerFixture, test_config) -> None:
    """Tests successful update of a repository and validates the returned RepositoryDetail."""

    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id=repository_id)
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/repo1")
    service_schema = const.MAP_SERVICE_SCHEMA
    repo = RepositoryDetail(id=service_id, service_name=service_name, service_url=service_url, entity_ids=[])
    map_service = MapService(
        id=service_id, service_name=service_name, service_url=service_url, schemas=[service_schema], entity_ids=[]
    )
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=map_service)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.patch_by_id", return_value=map_service)
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    result = repositories.update(repo)
    assert isinstance(result, RepositoryDetail)
    assert result.id == repository_id
    assert result.service_name == service_name
    assert str(result.service_url) == str(service_url)


def test_update_calls_update_put_when_strategy_put(app, mocker: MockerFixture, test_config) -> None:
    """Tests that update delegates to update_put when config.MAP_CORE.update_strategy == 'put'."""
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")
    mock_update_put = mocker.patch("server.services.repositories.update_put", return_value="called")

    result = repositories.update(repo)

    assert result == "called"
    assert mock_update_put.called


def test_update_raises_oauth_token_error_on_unauthorized(app, mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised when update receives an unauthorized response."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.patch_by_id", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.update(repo)

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_update_raises_unexpected_response_error_on_internal_server_error(
    app, mocker: MockerFixture, test_config
) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.patch_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update(repo)

    assert "mAP Core API server error" in str(excinfo.value)


def test_update_raises_unexpected_response_error_on_request_exception(app, mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    mocker.patch("server.clients.services.patch_by_id", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update(repo)

    assert "Failed to connect to mAP Core API" in str(excinfo.value)


def test_update_raises_unexpected_response_error_on_validation_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    mocker.patch("server.clients.services.patch_by_id", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update(repo)

    assert "Failed to parse response from mAP Core API" in str(excinfo.value)


def test_update_raises_oauth_token_error_direct(app, mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised directly from update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    mocker.patch("server.clients.services.patch_by_id", side_effect=repositories.OAuthTokenError("token error"))

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.update(repo)

    assert "token error" in str(excinfo.value)


def test_update_raises_credentials_error_direct(app, mocker: MockerFixture, test_config) -> None:
    """Tests that CredentialsError is raised directly from update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    mocker.patch("server.clients.services.patch_by_id", side_effect=repositories.CredentialsError("cred error"))

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.update(repo)

    assert "cred error" in str(excinfo.value)


def test_update_raises_resource_not_found_on_none(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceNotFound is raised when get_by_id returns None during update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.update(repo)

    assert "Not Found" in str(excinfo.value)


def test_update_raises_invalid_form_error_on_service_url_update(app, mocker: MockerFixture, test_config) -> None:
    """Tests that InvalidFormError is raised when service_url is updated during update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    current_url: HttpUrl = HttpUrl("https://other.com")
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    current = RepositoryDetail(id="repo1", service_name="s", service_url=current_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=current)

    with pytest.raises(repositories.InvalidFormError) as excinfo:
        repositories.update(repo)

    assert "Service URL could not be updated" in str(excinfo.value)


def test_update_raises_resource_invalid_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceInvalid is raised when MapError is returned from update."""

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.patch_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.ResourceInvalid) as excinfo:
        repositories.update(repo)

    assert mock_logger.called
    assert "invalid" in str(excinfo.value)


def test_update_raises_unexpected_response_error_on_other_http_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that UnexpectedResponseError is raised on non-401/500 HTTP errors during update."""
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.patch_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update(repo)

    assert "Failed to update Repository resource in mAP Core API" in str(excinfo.value)


def test_update_raises_resource_not_found_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceNotFound is raised when MapError.detail matches MAP_NOT_FOUND_PATTERN during update."""
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.build_patch_operations", return_value=[])
    map_error = MapError(detail="Repository 'repo1' Not Found", status="404", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.patch_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.update(repo)

    assert mock_logger.called
    assert "not found" in str(excinfo.value).lower()


def test_update_put_success(app, mocker: MockerFixture, test_config) -> None:
    """Tests successful update (PUT) of a repository and validates the returned RepositoryDetail."""

    repository_id = "repo1"
    service_id = test_config.REPOSITORIES.id_patterns.sp_connector.format(repository_id=repository_id)
    service_name = test_config.SP.entity_id
    service_url: HttpUrl = HttpUrl(f"https://{test_config.POSTGRES.host}/{repository_id}")
    service_schema = const.MAP_SERVICE_SCHEMA
    repo = RepositoryDetail(id=service_id, service_name=service_name, service_url=service_url, entity_ids=[])
    map_service = MapService(
        id=service_id, service_name=service_name, service_url=service_url, schemas=[service_schema], entity_ids=[]
    )
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=map_service)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.put_by_id", return_value=map_service)
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")
    result = repositories.update_put(repo)
    assert isinstance(result, RepositoryDetail)
    assert result.id == repository_id
    assert result.service_name == service_name
    assert str(result.service_url) == str(service_url)


def test_update_put_calls_update_when_strategy_patch(app, mocker: MockerFixture, test_config) -> None:
    """Tests that update_put delegates to update when config.MAP_CORE.update_strategy == 'patch'."""
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "patch")
    mock_update = mocker.patch("server.services.repositories.update", return_value="called")

    result = repositories.update_put(repo)

    assert result == "called"
    assert mock_update.called


def test_update_put_raises_oauth_token_error_on_unauthorized(app, mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised when update_put receives an unauthorized response."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.put_by_id", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.update_put(repo)

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_update_put_raises_unexpected_response_error_on_internal_server_error(
    app, mocker: MockerFixture, test_config
) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during update_put."""

    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.put_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update_put(repo)

    assert "mAP Core API server error" in str(excinfo.value)


def test_update_put_raises_unexpected_response_error_on_request_exception(
    app, mocker: MockerFixture, test_config
) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.put_by_id", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update_put(repo)

    assert "Failed to connect to mAP Core API" in str(excinfo.value)


def test_update_put_raises_unexpected_response_error_on_validation_error(
    app, mocker: MockerFixture, test_config
) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during update_put."""

    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.put_by_id", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update_put(repo)

    assert "Failed to parse response from mAP Core API" in str(excinfo.value)


def test_update_put_raises_oauth_token_error_direct(app, mocker: MockerFixture, test_config) -> None:
    """Tests that OAuthTokenError is raised directly from update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.put_by_id", side_effect=repositories.OAuthTokenError("token error"))

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.update_put(repo)

    assert "token error" in str(excinfo.value)


def test_update_put_raises_credentials_error_direct(app, mocker: MockerFixture, test_config) -> None:
    """Tests that CredentialsError is raised directly from update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.clients.services.put_by_id", side_effect=repositories.CredentialsError("cred error"))

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.update_put(repo)

    assert "cred error" in str(excinfo.value)


def test_update_put_raises_resource_not_found_on_none(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceNotFound is raised when get_by_id returns None during update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.update_put(repo)

    assert "Not Found" in str(excinfo.value)


def test_update_put_raises_invalid_form_error_on_service_url_update(app, mocker: MockerFixture, test_config) -> None:
    """Tests that InvalidFormError is raised when service_url is updated during update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    current_url: HttpUrl = HttpUrl("https://other.com")
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    current = RepositoryDetail(id="repo1", service_name="s", service_url=current_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=current)

    with pytest.raises(repositories.InvalidFormError) as excinfo:
        repositories.update_put(repo)

    assert "Service URL could not be updated" in str(excinfo.value)


def test_update_put_raises_resource_invalid_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceInvalid is raised when MapError is returned from update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")

    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.put_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.ResourceInvalid) as excinfo:
        repositories.update_put(repo)

    assert mock_logger.called
    assert "invalid" in str(excinfo.value)


def test_update_put_raises_unexpected_response_error_on_other_http_error(
    app, mocker: MockerFixture, test_config
) -> None:
    """Tests that UnexpectedResponseError is raised on non-401/500 HTTP errors during update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.put_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.update_put(repo)

    assert "Failed to update Repository resource in mAP Core API" in str(excinfo.value)


def test_update_put_raises_resource_not_found_on_map_error(app, mocker: MockerFixture, test_config) -> None:
    """Tests that ResourceNotFound is raised when MapError.detail matches MAP_NOT_FOUND_PATTERN during update_put."""
    mocker.patch("server.config.config.MAP_CORE.update_strategy", "put")
    service_url: HttpUrl = HttpUrl(test_config.MAP_CORE.base_url)
    repo = RepositoryDetail(id="repo1", service_name="s", service_url=service_url, entity_ids=[])
    mocker.patch("server.services.repositories.validate_repository_to_map_service", return_value=repo)
    mocker.patch("server.services.repositories.get_by_id", return_value=repo)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    map_error = MapError(detail="Repository 'repo1' Not Found", status="404", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.put_by_id", return_value=map_error)
    mock_logger = mocker.patch("flask.current_app.logger.info")

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.update_put(repo)

    assert mock_logger.called
    assert "not found" in str(excinfo.value).lower()


def test_delete_by_id_success(app, test_config, mocker: MockerFixture) -> None:
    """Tests successful deletion of a repository by ID and verifies the correct call arguments."""

    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)

    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mock_delete = mocker.patch("server.clients.services.delete_by_id", return_value=None)

    repositories.delete_by_id("repo1", test_config.SP.entity_id)

    mock_delete.assert_called_once_with("repo1", access_token="token", client_secret="secret")


def test_delete_by_id_raises_oauth_token_error_on_unauthorized(app, test_config, mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised when delete_by_id receives an unauthorized response."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.delete_by_id", side_effect=http_error)

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "Access token is invalid or expired" in str(excinfo.value)


def test_delete_by_id_raises_unexpected_response_error_on_internal_server_error(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that UnexpectedResponseError is raised on internal server error during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    response = Response()
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.delete_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "mAP Core API server error" in str(excinfo.value)


def test_delete_by_id_raises_unexpected_response_error_on_request_exception(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that UnexpectedResponseError is raised on request exception during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.clients.services.delete_by_id", side_effect=requests.RequestException("fail"))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "Failed to connect to mAP Core API" in str(excinfo.value)


def test_delete_by_id_raises_unexpected_response_error_on_validation_error(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that UnexpectedResponseError is raised on validation error during delete_by_id."""
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.clients.services.delete_by_id", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "Failed to parse response from mAP Core API" in str(excinfo.value)


def test_delete_by_id_raises_oauth_token_error_direct(app, test_config, mocker: MockerFixture) -> None:
    """Tests that OAuthTokenError is raised directly from delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.clients.services.delete_by_id", side_effect=repositories.OAuthTokenError("token error"))

    with pytest.raises(repositories.OAuthTokenError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "token error" in str(excinfo.value)


def test_delete_by_id_raises_credentials_error_direct(app, test_config, mocker: MockerFixture) -> None:
    """Tests that CredentialsError is raised directly from delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.clients.services.delete_by_id", side_effect=repositories.CredentialsError("cred error"))

    with pytest.raises(repositories.CredentialsError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "cred error" in str(excinfo.value)


def test_delete_by_id_raises_resource_not_found_on_map_error(app, test_config, mocker: MockerFixture) -> None:
    """Tests that ResourceNotFound is raised when MapError indicates not found during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    map_error = MapError(detail="Repository 'repo1' Not Found", status="404", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.delete_by_id", return_value=map_error)

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "not found" in str(excinfo.value).lower()


def test_delete_by_id_raises_resource_invalid_on_map_error(app, test_config, mocker: MockerFixture) -> None:
    """Tests that ResourceInvalid is raised when MapError indicates invalid during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.clients.services.get_by_id", return_value=dummy_map_service)

    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    map_error = MapError(detail="invalid", status="400", scim_type="invalidSyntax")
    mocker.patch("server.clients.services.delete_by_id", return_value=map_error)

    with pytest.raises(repositories.ResourceInvalid) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "invalid" in str(excinfo.value)


def test_delete_by_id_raises_resource_not_found_if_repo_missing(app, test_config, mocker: MockerFixture) -> None:
    """Tests that ResourceNotFound is raised if get_by_id returns None in delete_by_id."""
    mocker.patch("server.services.repositories.get_by_id", return_value=None)

    with pytest.raises(repositories.ResourceNotFound) as excinfo:
        repositories.delete_by_id("missing_repo", test_config.SP.entity_id)

    assert "Not Found" in str(excinfo.value)


def test_delete_by_id_raises_invalid_form_error_if_service_name_mismatch(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that InvalidFormError is raised if service_name does not match in delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name="actual_service",
    )
    mocker.patch("server.services.repositories.get_by_id", return_value=dummy_map_service)

    with pytest.raises(repositories.InvalidFormError) as excinfo:
        repositories.delete_by_id("repo1", "wrong_service")

    assert "does not match" in str(excinfo.value)


def test_delete_by_id_raises_unexpected_response_error_on_other_http_error(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that UnexpectedResponseError is raised on non-401/500 HTTP errors during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.services.repositories.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    response = Response()
    response.status_code = HTTPStatus.BAD_REQUEST
    http_error = requests.HTTPError(response=response)
    mocker.patch("server.clients.services.delete_by_id", side_effect=http_error)

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "Failed to delete Repository resource in mAP Core API." in str(excinfo.value)


def test_delete_by_id_raises_unexpected_response_error_on_validation_error_(
    app, test_config, mocker: MockerFixture
) -> None:
    """Tests that UnexpectedResponseError is raised on ValidationError during delete_by_id."""
    dummy_map_service = MapService(
        id="repo1",
        service_name=test_config.SP.entity_id,
    )
    mocker.patch("server.services.repositories.get_by_id", return_value=dummy_map_service)
    mocker.patch("server.services.repositories.get_access_token", return_value="token")
    mocker.patch("server.services.repositories.get_client_secret", return_value="secret")
    mocker.patch("server.services.repositories.resolve_service_id", return_value="repo1")
    mocker.patch("server.clients.services.delete_by_id", side_effect=ValidationError("fail", []))

    with pytest.raises(repositories.UnexpectedResponseError) as excinfo:
        repositories.delete_by_id("repo1", test_config.SP.entity_id)

    assert "Failed to parse response from mAP Core API." in str(excinfo.value)
