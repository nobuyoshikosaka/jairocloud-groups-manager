import typing as t

from server.cli.token import issue, refresh


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture


def test_token_issue_calls_prepare_issuing_url(app: Flask, test_config, mocker: MockerFixture) -> None:
    """Tests token issue command calls prepare_issuing_url and logs info."""

    issuing_url = test_config.MAP_CORE.base_url
    prepare_mock = mocker.patch("server.cli.token.prepare_issuing_url", return_value=issuing_url)
    logger_mock = mocker.patch("server.cli.token.current_app.logger.info")

    issue.main(args=[], standalone_mode=False)

    prepare_mock.assert_called_once()
    logger_mock.assert_called_once_with(mocker.ANY, {"url": issuing_url})


def test_token_refresh_calls_refresh_access_token(app: Flask, mocker: MockerFixture) -> None:
    """Tests token refresh command calls refresh_access_token and logs info."""
    refresh_mock = mocker.patch("server.cli.token.refresh_access_token")
    logger_mock = mocker.patch("server.cli.token.current_app.logger.info")

    refresh.main(args=[], standalone_mode=False)

    refresh_mock.assert_called_once()
    logger_mock.assert_called_once_with(mocker.ANY)
