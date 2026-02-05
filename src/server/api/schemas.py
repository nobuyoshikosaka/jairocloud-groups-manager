#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Schema definitions for the API endpoints.

These schemas used in request and response validation.
"""

import typing as t

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from werkzeug.datastructures import FileStorage

from server.entities.common import camel_case_config
from server.entities.user_detail import UserDetail


ignore_extra_config = ConfigDict(
    extra="ignore",
    validate_assignment=True,
)
"""Common configuration dict to ignore extra fields.

- extra: "ignore" - Ignores extra fields not defined in the model.
- validate_assignment: True - Validates fields on assignment.
"""


class OAuthTokenQuery(BaseModel):
    """Schema for OAuth token query parameters."""

    code: str
    """Authorization code received from the Authorization Server."""

    state: str
    """State parameter to prevent CSRF attacks."""

    model_config = ignore_extra_config
    """Configure to ignore extra fields."""


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    code: str
    """Message code."""

    message: str
    """Error message."""


class RepositoriesQuery(BaseModel):
    """Schema for repositories search query parameters."""

    q: t.Annotated[str | None, "query"] = None
    """Search term to filter repositories."""

    i: t.Annotated[list[str] | None, "ids"] = None
    """Filter by repository IDs."""

    k: t.Annotated[str | None, "key"] = None
    """Attribute key to sort repositories."""

    d: t.Annotated[
        t.Literal["asc", "desc"] | None,
        "direction",
    ] = None
    """Sort order: 'asc' (ascending) or 'desc' (descending)."""

    p: t.Annotated[int | None, "page"] = None
    """Page number to retrieve."""

    l: t.Annotated[int | None, "length"] = None  # noqa: E741
    """Page size (number of items per page)."""

    model_config = ignore_extra_config
    """Configure to ignore extra fields."""


class GroupsQuery(BaseModel):
    """Schema for groups search query parameters."""

    q: t.Annotated[str | None, "query"] = None
    """Search term to filter groups."""

    i: t.Annotated[list[str] | None, "ids"] = None
    """Filter by group IDs."""

    r: t.Annotated[list[str] | None, "repositories"] = None
    """Filter by affiliated repository IDs."""

    u: t.Annotated[list[str] | None, "users"] = None
    """Filter by affiliated user IDs."""

    s: t.Annotated[t.Literal[0, 1] | None, "status"] = None
    """Filter by public status:

    0 (public), 1 (private).
    """

    v: t.Annotated[t.Literal[0, 1, 2] | None, "visibility"] = None
    """Filter by member list visibility:

    0 (public), 1 (private), 2 (hidden).
    """

    k: t.Annotated[str | None, "key"] = None
    """Attribute key to sort groups."""

    d: t.Annotated[
        t.Literal["asc", "desc"] | None,
        "direction",
    ] = None
    """Sort order: 'asc' (ascending) or 'desc' (descending)."""

    p: t.Annotated[int | None, "page"] = None
    """Page number to retrieve."""

    l: t.Annotated[int | None, "length"] = None  # noqa: E741
    """Page size (number of items per page)."""

    model_config = ignore_extra_config
    """Configure to ignore extra fields."""


class UsersQuery(BaseModel):
    """Schema for users search query parameters."""

    q: t.Annotated[str | None, "query"] = None
    """Search term to filter users."""

    i: t.Annotated[list[str] | None, "ids"] = None
    """Filter by user IDs."""

    r: t.Annotated[list[str] | None, "repositories"] = None
    """Filter by affiliated repository IDs."""

    g: t.Annotated[list[str] | None, "groups"] = None
    """Filter by affiliated group IDs."""

    a: t.Annotated[list[int] | None, "authorities"] = None
    """Filter by user roles:

    0 (system admin), 1 (repository admin), 2 (community admin),
    3 (contributor), 4 (general user).
    """

    s: t.Annotated[date | None, "start"] = None
    """Filter by last modified date (from)."""

    e: t.Annotated[date | None, "end"] = None
    """Filter by last modified date (to)."""

    k: t.Annotated[str | None, "key"] = None
    """Attribute key to sort users."""

    d: t.Annotated[
        t.Literal["asc", "desc"] | None,
        "direction",
    ] = None
    """Sort order: 'asc' (ascending) or 'desc' (descending)."""

    p: t.Annotated[int | None, "page"] = None
    """Page number to retrieve."""

    l: t.Annotated[int | None, "length"] = None  # noqa: E741
    """Page size (number of items per page)."""

    model_config = ignore_extra_config
    """Configure to ignore extra fields."""


class GroupPatchRequest(BaseModel):
    """Schema for patching group members."""

    op: t.Literal["add", "remove"]
    """The patch operation to perform."""
    path: str
    """The target path of the patch operation."""
    value: list[str]
    """Value to be changed."""


class DeleteGroupsRequest(BaseModel):
    """Schema for deleting multiple groups."""

    group_ids: set[str]
    """Set of group IDs to delete."""
    model_config = camel_case_config
    """Configure to use camelCase aliasing."""


class HistoryPublic(BaseModel):
    """History public status."""

    public: bool
    """Public status."""


class TargetRepository(BaseModel):
    """Schema for target repository."""

    repository_id: str
    """ID of the target repository."""

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""


class UploadFiles(BaseModel):
    """Schema for upload files."""

    bulk_file: FileStorage

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BulkBody(BaseModel):
    """Body schema for bulk upload response."""

    temp_file_id: UUID | None = None
    """Temporary ID for the bulk upload session."""
    history_id: UUID | None = None
    """History ID associated with the bulk upload."""
    task_id: str | None = None
    """Task ID associated with the bulk upload."""
    status: str | None = None
    """Status of the bulk upload."""


class UploadBody(BaseModel):
    """Body schema for upload requests."""

    temp_file_id: UUID | None = None
    """Temporary ID for the upload session."""
    repository_id: str | None = None
    """ID of the target repository."""
    task_id: str | None = None
    """Task ID associated with the upload."""
    delete_users: list[UserDetail] | None = None
    """List of users whose files are to be deleted."""


class UploadQuery(BaseModel):
    """Query parameters for upload history data."""

    f: list[int] | None = None
    """Filter by status.
    0:create, 1:update, 2:delete, 3:skip, 4:error"""

    p: int | None = None
    """Page number for pagination."""

    l: int | None = None  # noqa: E741
    """Number of users per page for pagination."""
