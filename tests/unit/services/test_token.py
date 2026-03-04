import json
import typing as t
import urllib.parse as urlparse

from unittest.mock import Mock

import pytest
import requests

from server.entities.auth import ClientCredentials, OAuthToken
from server.services import token


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture


def test_get_access_token(mocker: MockerFixture) -> None:
    """Test that get_access_token returns the correct access token value for a typical OAuthToken."""
    token_obj = OAuthToken(
        access_token="token_main",
        token_type="bearer",
        expires_in=3600,
        refresh_token=None,
        scope="",
    )
    expected = "token_main"
    mocker.patch("server.services.token.get_oauth_token", return_value=token_obj)

    actual = token.get_access_token()

    assert actual == expected


def test_get_access_token_error(mocker: MockerFixture) -> None:
    """Test that get_access_token raises OAuthTokenError when no token is found."""
    mocker.patch("server.services.token.get_oauth_token", return_value=None)

    with pytest.raises(token.OAuthTokenError):
        token.get_access_token()


def test_get_client_secret(mocker: MockerFixture) -> None:
    """Test that get_client_secret returns the correct client secret value for a typical ClientCredentials."""
    creds_obj = ClientCredentials(client_secret="client_secret_main", client_id="cid_main")
    expected = "client_secret_main"
    mocker.patch("server.services.token.get_client_credentials", return_value=creds_obj)

    actual = token.get_client_secret()

    assert actual == expected


def test_get_client_secret_error(mocker: MockerFixture) -> None:
    """Test that get_client_secret raises CredentialsError when no credentials are found."""
    mocker.patch("server.services.token.get_client_credentials", return_value=None)

    with pytest.raises(token.CredentialsError):
        token.get_client_secret()


def test_prepare_issuing_url(app: Flask, mocker: MockerFixture, test_config) -> None:
    """Test that prepare_issuing_url generates a valid issuing URL using client credentials and config."""
    mocker.patch(
        "server.services.token.get_client_credentials",
        return_value=ClientCredentials(client_id="cid", client_secret="s"),
    )

    with app.app_context():
        redirect_uri = app.url_for("api.callback.auth_code", _external=True)
        url = token.prepare_issuing_url()

    expected_redirect = urlparse.quote(redirect_uri, safe="")
    expected_state = urlparse.quote(test_config.SP.entity_id, safe="")

    assert isinstance(url, str)
    assert "client_id=cid" in url
    assert f"redirect_uri={expected_redirect}" in url
    assert f"state={expected_state}" in url


def test_prepare_issuing_url_http_error(app: Flask, mocker: MockerFixture) -> None:
    """Test that prepare_issuing_url raises CertificatesError on HTTP error."""
    mocker.patch(
        "server.services.token.get_client_credentials",
        return_value=None,
    )
    mocker.patch("server.services.token.save_client_credentials", return_value=None)

    mock_response = Mock()
    mock_response.json.return_value = {"error_description": "fail"}
    http_error = requests.HTTPError()
    http_error.response = mock_response
    mocker.patch(
        "server.services.token.auth.issue_client_credentials",
        side_effect=http_error,
    )

    with app.app_context(), pytest.raises(token.CertificatesError) as excinfo:
        token.prepare_issuing_url()

    assert "Failed to issue client credentials: fail" in str(excinfo.value)


def test_prepare_issuing_url_json_decode_error(app: Flask, mocker: MockerFixture) -> None:
    """Test that prepare_issuing_url raises CertificatesError on JSON decode error."""
    mocker.patch(
        "server.services.token.get_client_credentials",
        return_value=None,
    )
    mocker.patch("server.services.token.save_client_credentials", return_value=None)
    mocker.patch(
        "server.services.token.auth.issue_client_credentials",
        side_effect=json.decoder.JSONDecodeError("msg", "doc", 0),
    )

    with app.app_context(), pytest.raises(json.decoder.JSONDecodeError):
        token.prepare_issuing_url()


def test__create_issuing_url(app: Flask):
    """Test that _create_issuing_url generates a valid issuing URL with correct parameters."""
    with app.app_context():
        url = token._create_issuing_url(client_id="cid", redirect_uri="http://localhost/cb", entity_id="eid")  # noqa: SLF001

        assert isinstance(url, str)
        assert "client_id=cid" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcb" in url
        assert "state=eid" in url


def test_issue_access_token_success(mocker: MockerFixture) -> None:
    """Test that issue_access_token returns the access token on success."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    dummy_token = OAuthToken(access_token="tok", token_type="bearer", expires_in=3600, refresh_token=None, scope="")
    expected = dummy_token.access_token
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.auth.issue_oauth_token", return_value=dummy_token)
    mocker.patch("server.services.token.save_oauth_token", return_value=None)

    actual = token.issue_access_token("code")

    assert actual == expected


def test_issue_access_token_no_creds(mocker: MockerFixture) -> None:
    """Test that issue_access_token raises CredentialsError when credentials are missing."""
    mocker.patch("server.services.token.get_client_credentials", return_value=None)

    with pytest.raises(token.CredentialsError):
        token.issue_access_token("code")


def test_issue_access_token_http_error(app: Flask, mocker: MockerFixture) -> None:
    """Test that issue_access_token raises OAuthTokenError with correct message on HTTP error."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.save_oauth_token", return_value=None)
    mock_response = Mock()
    mock_response.json.return_value = {"error_description": "fail"}
    http_error = requests.HTTPError()
    http_error.response = mock_response
    mocker.patch("server.services.token.auth.issue_oauth_token", side_effect=http_error)

    with app.app_context(), pytest.raises(token.OAuthTokenError) as excinfo:
        token.issue_access_token("code")

    assert "Failed to issue OAuth token: fail" in str(excinfo.value)


def test_issue_access_token_json_decode_error(app: Flask, mocker: MockerFixture) -> None:
    """Test that issue_access_token raises JSONDecodeError when JSON decoding fails."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.save_oauth_token", return_value=None)
    mocker.patch(
        "server.services.token.auth.issue_oauth_token",
        side_effect=json.decoder.JSONDecodeError("msg", "doc", 0),
    )

    with app.app_context(), pytest.raises(json.decoder.JSONDecodeError):
        token.issue_access_token("code")


def test_refresh_access_token_success(mocker: MockerFixture) -> None:
    """Test that refresh_access_token returns the new access token on success."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    dummy_token = OAuthToken(access_token="tok", token_type="bearer", expires_in=3600, refresh_token="rft", scope="")
    dummy_new_token = OAuthToken(
        access_token="newtok", token_type="bearer", expires_in=3600, refresh_token=None, scope=""
    )
    expected = dummy_new_token.access_token
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.get_oauth_token", return_value=dummy_token)
    mocker.patch("server.services.token.auth.refresh_oauth_token", return_value=dummy_new_token)
    mocker.patch("server.services.token.save_oauth_token", return_value=None)

    actual = token.refresh_access_token()

    assert actual == expected


def test_refresh_access_token_no_creds(mocker: MockerFixture) -> None:
    """Test that refresh_access_token raises CredentialsError when credentials are missing."""
    mocker.patch("server.services.token.get_client_credentials", return_value=None)

    with pytest.raises(token.CredentialsError):
        token.refresh_access_token()


def test_refresh_access_token_no_token(mocker: MockerFixture) -> None:
    """Test that refresh_access_token raises OAuthTokenError when no token is found."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.get_oauth_token", return_value=None)

    with pytest.raises(token.OAuthTokenError):
        token.refresh_access_token()


def test_refresh_access_token_no_refresh_token(mocker: MockerFixture) -> None:
    """Test that refresh_access_token raises OAuthTokenError when no refresh token is available."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    dummy_token = OAuthToken(access_token="tok", token_type="bearer", expires_in=3600, refresh_token=None, scope="")
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.get_oauth_token", return_value=dummy_token)

    with pytest.raises(token.OAuthTokenError):
        token.refresh_access_token()


def test_refresh_access_token_json_decode_error(app: Flask, mocker: MockerFixture) -> None:
    """Test that refresh_access_token raises JSONDecodeError when JSON decoding fails."""
    dummy_creds = ClientCredentials(client_secret="secret", client_id="cid")
    dummy_token = OAuthToken(access_token="tok", token_type="bearer", expires_in=3600, refresh_token="rft", scope="")
    mocker.patch("server.services.token.get_client_credentials", return_value=dummy_creds)
    mocker.patch("server.services.token.get_oauth_token", return_value=dummy_token)
    mocker.patch("server.services.token.save_oauth_token", return_value=None)
    mocker.patch(
        "server.services.token.auth.refresh_oauth_token",
        side_effect=json.decoder.JSONDecodeError("msg", "doc", 0),
    )

    with app.app_context(), pytest.raises(json.decoder.JSONDecodeError):
        token.refresh_access_token()
