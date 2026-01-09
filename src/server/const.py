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

MAP_ERROR_SCHEMA: Final = "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:Error"
"""Schema URI for mAP Error resources."""

MAP_PATCH_SCHEMA: Final = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
"""Schema URI for PATCH request payloads."""


MAP_OAUTH_ISSUE_ENDPOINT: Final = "/oauth/sslauth/issue.php"
"""Endpoint for issuing client credentials in mAP Core Authorization Server."""

MAP_OAUTH_AUTHORIZE_ENDPOINT: Final = "/oauth/shib/authrequest.php"
"""Endpoint for issuing authorization code from mAP Core Authorization Server."""

MAP_OAUTH_TOKEN_ENDPOINT: Final = "/oauth/token.php"  # noqa: S105
"""Endpoint for issuing access tokens from mAP Core Authorization Server."""


MAP_USERS_ENDPOINT: Final = "/api/v2/Users"
"""Endpoint for User resources in mAP Core API."""

MAP_EXIST_EPPN_ENDPOINT: Final = "/api/v2/Existeppn"
"""Endpoint to check existence of ePPN in mAP Core API."""

MAP_GROUPS_ENDPOINT: Final = "/api/v2/Groups"
"""Endpoint for Group resources in mAP Core API."""

MAP_SERVICES_ENDPOINT: Final = "/api/v2/Services"
"""Endpoint for Service resources in mAP Core API."""


MAP_NOT_FOUND_PATTERN: Final = r"'(.*)' Not Found"
"""Pattern to identify 'Not Found' errors from mAP Core API."""
