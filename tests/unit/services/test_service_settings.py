import typing as t

from unittest.mock import ANY

import pytest

from server.db.service_settings import ServiceSettings
from server.entities.auth import ClientCredentials
from server.exc import CredentialsError
from server.services.service_settings import (
    _get_setting,
    _save_setting,
    get_client_credentials,
    save_client_credentials,
)


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_client_credentials(mocker: MockerFixture):
    setting = {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
    }
    mock_get = mocker.patch("server.services.service_settings._get_setting", return_value=setting)

    creds = get_client_credentials()

    assert creds is not None
    assert creds.client_id == "test_client_id"
    assert creds.client_secret == "test_client_secret"
    mock_get.assert_called_once_with("client_credentials")


def test_get_client_credentials_no_setting(mocker: MockerFixture):
    mock_get = mocker.patch("server.services.service_settings._get_setting", return_value=None)
    creds = get_client_credentials()
    assert creds is None
    mock_get.assert_called_once_with("client_credentials")


def test_get_client_credentials_invalid_setting(mocker: MockerFixture):
    setting = {
        "client_id": "test_client_id",
        # Missing client_secret
    }
    mock_get = mocker.patch("server.services.service_settings._get_setting", return_value=setting)

    with pytest.raises(CredentialsError) as exc_info:
        get_client_credentials()

    mock_get.assert_called_once_with("client_credentials")
    exc_info.match("Invalid client credentials in service settings.")


def test_save_client_credentials(mocker: MockerFixture):
    creds = ClientCredentials(
        client_id="save_client_id",
        client_secret="save_client_secret",
    )
    mock_save = mocker.patch("server.services.service_settings._save_setting")

    save_client_credentials(creds)

    mock_save.assert_called_once_with("client_credentials", ANY)
    json_value = mock_save.call_args[0][1]
    assert json_value["client_id"] == "save_client_id"
    assert json_value["client_secret"] == "save_client_secret"


def test__get_setting(app, mocker: MockerFixture):
    setting_value = {"foo": "bar"}
    setting = ServiceSettings(key="test_key", value=setting_value)  # pyright: ignore[reportCallIssue]
    mocker.patch("server.services.service_settings.db.session.get", return_value=setting)

    result = _get_setting("test_key")
    assert result == setting_value


def test__get_setting_not_found(app, mocker: MockerFixture):
    mocker.patch("server.services.service_settings.db.session.get", return_value=None)

    result = _get_setting("nonexistent_key")
    assert result is None


def test__save_setting_create(app, mocker: MockerFixture):
    mock_session_get = mocker.patch("server.services.service_settings.db.session.get", return_value=None)
    mock_add = mocker.patch("server.services.service_settings.db.session.add")
    mock_commit = mocker.patch("server.services.service_settings.db.session.commit")

    setting_key = "new_key"
    setting_value = {"new": "value"}

    _save_setting(setting_key, setting_value)

    mock_session_get.assert_called_once_with(ServiceSettings, setting_key)
    mock_commit.assert_called_once()
    mock_add.assert_called_once()
    added_setting = mock_add.call_args[0][0]
    assert added_setting.key == setting_key
    assert added_setting.value == setting_value


def test__save_setting_update(app, mocker: MockerFixture):
    setting_key = "existing_key"
    setting_value = {"existing": "value"}
    existing_setting = ServiceSettings(key=setting_key, value=setting_value)  # pyright: ignore[reportCallIssue]
    mock_session_get = mocker.patch("server.services.service_settings.db.session.get", return_value=existing_setting)
    mock_commit = mocker.patch("server.services.service_settings.db.session.commit")

    updated_value = {"updated": "value"}

    _save_setting(setting_key, updated_value)

    mock_session_get.assert_called_once_with(ServiceSettings, setting_key)
    mock_commit.assert_called_once()
    assert existing_setting.value == updated_value
