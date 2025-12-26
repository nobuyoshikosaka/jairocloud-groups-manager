#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Constant values for the server application."""

from typing import Final

DEFAULT_CONFIG_PATH: Final = "configs/server.config.toml"
"""Default path to the server configuration TOML file."""


MAP_USER_SCHEMA: Final = "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:User"
"""Schema URI for mAP User resources."""

MAP_GROUP_SCHEMA: Final = "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:Group"
"""Schema URI for mAP Group resources."""

MAP_SERVICE_SCHEMA: Final = (
    "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:Service"
)
"""Schema URI for mAP Service resources."""


MAP_OAUTH_ISSUE_ENDPOINT: Final = "/oauth/sslauth/issue.php"
"""Endpoint for issuing client credentials in mAP Core Authorization Server."""

MAP_OAUTH_AUTHORIZE_ENDPOINT: Final = "/oauth/shib/authrequest.php"
"""Endpoint for issuing authorization code from mAP Core Authorization Server."""

MAP_OAUTH_TOKEN_ENDPOINT: Final = "/oauth/token.php"  # noqa: S105
"""Endpoint for issuing access tokens from mAP Core Authorization Server."""
