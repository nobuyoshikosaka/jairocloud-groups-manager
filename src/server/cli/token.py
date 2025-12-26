#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Token management command-line interface."""

import click

from server.services.token import prepare_issuing_url


@click.group()
def token() -> None:
    """Manage OAuth tokens."""


@token.command()
def issue() -> None:
    """Issue access token."""
    url = prepare_issuing_url()
    click.echo(
        "Please access the following URL to authenticate. "
        f"An access token will be issued:\n{url}"
    )
