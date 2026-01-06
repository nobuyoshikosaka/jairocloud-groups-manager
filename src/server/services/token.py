#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing OAuth tokens."""

import requests

from flask import url_for

from server.clients import auth
from server.config import config
from server.const import MAP_OAUTH_AUTHORIZE_ENDPOINT
from server.exc import CertificatesError, CredentialsError, OAuthTokenError

from .service_settings import (
    get_client_credentials,
    get_oauth_token,
    save_client_credentials,
    save_oauth_token,
)


def get_access_token() -> str:
    """Get the OAuth access token.

    Returns:
        str: The access token if available, otherwise None.

    Raises:
        OAuthTokenError: If the token is not available.
    """
    token = get_oauth_token()
    if token is None:
        error = "OAuth tokens are not stored on the server."
        raise OAuthTokenError(error)

    return token.access_token


def prepare_issuing_url() -> str:
    """Prepare the URL to issue authorization code.

    If client credentials are not stored, issue them first.

    Returns:
        str: The URL to redirect the user for issuing client credentials.

    Raises:
        CertificatesError: If invalid config for entity ID or certificates is provided.
    """
    entity_id = config.SP.entity_id

    certs = get_client_credentials()
    if certs is None:
        try:
            certs = auth.issue_client_credentials(entity_id, config.SP)
        except requests.HTTPError as exc:
            json = exc.response.json()
            error = f"Failed to issue client credentials: {json['error_description']}"
            raise CertificatesError(error) from exc

        save_client_credentials(certs)

    redirect_uri = url_for("api.callback.auth_code", _external=True)
    return _create_issuing_url(certs.client_id, redirect_uri, entity_id)


def _create_issuing_url(client_id: str, redirect_uri: str, entity_id: str) -> str:
    """Create the URL to issue authorization code.

    Args:
        client_id (str): The client ID.
        redirect_uri (str): The redirect URI.
        entity_id (str): The entity ID of the Service Provider.

    Returns:
        str: The URL to redirect the user for issuing authorization code.
    """
    req = requests.Request(
        url=f"{config.MAP_CORE.base_url}{MAP_OAUTH_AUTHORIZE_ENDPOINT}",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": entity_id,
        },
    )
    return req.prepare().url  # pyright: ignore[reportReturnType]


def issue_access_token(code: str) -> str:
    """Issue a new OAuth access token.

    Args:
        code (str): The authorization code.

    Returns:
        str: The newly issued access token.

    Raises:
        CredentialsError: If client credentials are not available.
        OAuthTokenError: If issuing the token fails.
    """
    certs = get_client_credentials()
    if certs is None:
        error = "Client credentials are not stored on the server."
        raise CredentialsError(error)

    try:
        token = auth.issue_oauth_token(code, certs)
    except requests.HTTPError as exc:
        json = exc.response.json()
        error = f"Failed to issue OAuth token: {json['error_description']}"
        raise OAuthTokenError(error) from exc

    save_oauth_token(token)

    return token.access_token
