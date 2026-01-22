#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Schema definitions for the API endpoints.

These schemas used in request and response validation.
"""

from pydantic import BaseModel, ConfigDict

from server.entities.common import camel_case_config


class OAuthTokenQuery(BaseModel):
    """Schema for OAuth token query parameters."""

    code: str
    """Authorization code received from the Authorization Server."""

    state: str
    """State parameter to prevent CSRF attacks."""

    model_config = ConfigDict(extra="ignore")


class ErrorResponse(BaseModel):
    code: str = ""
    message: str = ""


class MemberPatchRequest(BaseModel):
    add: set[str]
    remove: set[str]


class DeleteGroupRequest(BaseModel):
    group_ids: set[str]
    model_config = camel_case_config
