from typing import Final


MAP_USER_SCHEMA: Final = "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:User"
"""The schema URI for mAP User resources."""

MAP_GROUP_SCHEMA: Final = "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:Group"
"""The schema URI for mAP Group resources."""

MAP_SERVICE_SCHEMA: Final = (
    "urn:ietf:params:scim:schemas:mace:gakunin.jp:core:2.0:Service"
)
"""The schema URI for mAP Service resources."""

MAP_OAUTH_ISSUE_ENDPOINT: Final = "/oauth/sslauth/issue.php"
"""The OAuth endpoint for issuing client certificates from mAP Core."""

MAP_OAUTH_AUTHORIZE_ENDPOINT: Final = "/oauth/shib/authrequest.php"
"""The OAuth endpoint for authorizing clients with mAP Core."""

MAP_OAUTH_TOKEN_ENDPOINT: Final = "/oauth/token.php"
"""The OAuth endpoint for obtaining access tokens from mAP Core."""
