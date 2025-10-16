import traceback
from typing import Protocol

import requests
from flask import current_app, url_for
from pydantic_core import ValidationError

from config import config
from const import MAP_OAUTH_ISSUE_ENDPOINT, MAP_OAUTH_TOKEN_ENDPOINT
from schema.others import ClientCert, OAuthToken


def issue_certificate(entity_id: str) -> ClientCert:
    """Issue a sample certificate.

    Args:
        entity_id (str): The entity ID for which to issue the certificate.

    Returns:
        ClientCert: The issued client certificate.
    """
    redirect_uri = url_for("auth.redirect", _external=True)

    try:
        response = requests.post(
            f"{config.MAP_CORE_BASE_URL}{MAP_OAUTH_ISSUE_ENDPOINT}",
            params={
                "entityid": entity_id,
                "redirect_uri": redirect_uri,
            },
            cert=(config.WEB_UI_SP_CERT_PATH, config.WEB_UI_SP_KEY_PATH),
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError, requests.JSONDecodeError:
        current_app.logger.error(f"Failed to issue certificate for {entity_id}.")
        traceback.print_exc()
        raise

    try:
        return ClientCert.model_validate(data, extra="ignore")
    except ValidationError:
        current_app.logger.error("Received invalid certificate data.")
        traceback.print_exc()
        raise


class _OAuthCode(Protocol):
    code: str
    state: str


class _ClientCert(Protocol):
    client_id: str
    client_secret: str


def get_access_token(code: _OAuthCode, cert: _ClientCert) -> OAuthToken:
    """Exchange an authorization code for an access token.

    Args:
        code (OAuthCode): The authorization code received from the OAuth provider.
        cert (ClientCert): The client certificate containing client_id and client_secret.

    Returns:
        OAuthToken: The obtained OAuth access token.
    """
    redirect_uri = url_for("auth.redirect", _external=True)

    try:
        response = requests.post(
            f"{config.MAP_CORE_BASE_URL}{MAP_OAUTH_TOKEN_ENDPOINT}",
            data={
                "grant_type": "authorization_code",
                "code": code.code,
                "redirect_uri": redirect_uri,
            },
            auth=(cert.client_id, cert.client_secret),
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError, requests.JSONDecodeError:
        current_app.logger.error("Failed to obtain access token.")
        traceback.print_exc()
        raise

    try:
        return OAuthToken.model_validate(data, extra="ignore")
    except ValidationError:
        current_app.logger.error("Received invalid access token data.")
        traceback.print_exc()
        raise
