#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Token management command-line interface."""

import click

from flask import current_app

from server.messages import I
from server.services.token import prepare_issuing_url, refresh_access_token


@click.group()
def token() -> None:
    """Manage OAuth tokens."""


@token.command()
def issue() -> None:
    """Issue access token."""
    url = prepare_issuing_url()
    current_app.logger.info(I.REQUEST_FOR_AUTH_CODE, {"url": url})


@token.command()
def refresh() -> None:
    """Refresh access token."""
    refresh_access_token()
    current_app.logger.info(I.SUCCESS_REFRESH_TOKEN)
