#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Schemas for authentication and authorization.

These are used in the mAP Core Authorization Server.
"""

from pydantic import BaseModel, ConfigDict


class ClientCredentials(BaseModel):
    """Schema for client credentials."""

    client_id: str
    """Client identifier."""

    client_secret: str
    """Client secret."""

    model_config = ConfigDict(extra="ignore")


class OAuthToken(BaseModel):
    """Schema for OAuth 2.0 tokens."""

    access_token: str
    """Access token string."""

    token_type: str
    """Type of the access token (e.g., 'Bearer')."""

    expires_in: int
    """Lifetime in seconds of the access token."""

    refresh_token: str | None = None
    """Refresh token that can be used to obtain new access tokens, if provided."""

    scope: str | None = None
    """Scopes granted by the access token, if any."""

    model_config = ConfigDict(extra="ignore")
