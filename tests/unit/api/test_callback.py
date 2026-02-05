import inspect
import typing as t

import pytest

from server.api.callback import auth_code
from server.api.schemas import OAuthTokenQuery
from server.exc import CredentialsError, OAuthTokenError


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_auth_code_redirect(mocker: MockerFixture):
    """Normal case: valid code should redirect"""
    mock_issue = mocker.patch("server.services.token.issue_access_token")
    query = OAuthTokenQuery(code="valid_code", state="abc123")
    expected_status_code = 302
    expected_location = "/"

    original_func = inspect.unwrap(auth_code)
    response = original_func(query)

    assert response.status_code == expected_status_code
    assert response.location == expected_location
    mock_issue.assert_called_once_with("valid_code")


def test_auth_code_credentials_error(mocker: MockerFixture):
    """Error case: token.issue_access_token raises CredentialsError"""
    mocker.patch("server.services.token.issue_access_token", side_effect=CredentialsError("Invalid code"))
    query = OAuthTokenQuery(code="", state="abc123")

    original_func = inspect.unwrap(auth_code)
    with pytest.raises(CredentialsError):
        original_func(query)


def test_auth_code_oauth_token_error(mocker: MockerFixture):
    """Error case: token.issue_access_token raises OAuthTokenError"""
    mocker.patch("server.services.token.issue_access_token", side_effect=OAuthTokenError("Invalid code"))
    query = OAuthTokenQuery(code="", state="abc123")

    original_func = inspect.unwrap(auth_code)
    with pytest.raises(OAuthTokenError):
        original_func(query)
