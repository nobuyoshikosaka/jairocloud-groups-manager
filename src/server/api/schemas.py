#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Schema definitions for the API endpoints.

These schemas used in request and response validation.
"""

import typing as t

from datetime import date

from pydantic import BaseModel, ConfigDict


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


class RepositoriesQuery(BaseModel):
    """Schema for repositories search query parameters."""

    q: t.Annotated[str | None, "query"] = None
    """Search term to filter repositories."""

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
