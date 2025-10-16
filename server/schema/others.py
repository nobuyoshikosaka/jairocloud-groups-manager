from pydantic import BaseModel


class ClientCert(BaseModel):
    """Client certificate information."""

    client_id: str
    """Client identifier."""
    client_secret: str
    """Client secret."""


class OAuthCodeArgs(BaseModel):
    """OAuth authorization code arguments."""

    state: str
    """State parameter."""
    code: str
    """Authorization code."""


class OAuthToken(BaseModel):
    """OAuth token response."""

    access_token: str
    """Access token."""
    token_type: str
    """Type of the token, typically 'Bearer'."""
    expires_in: int
    """Time in seconds until the token expires."""
    refresh_token: str | None = None
    """Refresh token, if provided."""
    scope: str | None = None
    """Scopes associated with the access token, if any."""
