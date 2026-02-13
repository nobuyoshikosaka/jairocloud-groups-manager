#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for history entity for client side."""

import typing as t

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from server.entities.summaries import GroupSummary, RepositorySummary, UserSummary

from .common import camel_case_config


ignore_extra_config = ConfigDict(
    extra="ignore",
    validate_assignment=True,
)


class DownloadHistoryData(BaseModel):
    """Download history data model."""

    id: UUID
    """Download history ID."""

    timestamp: datetime
    """Timestamp of the download event."""

    operator: UserSummary
    """Operator who performed the download."""

    public: bool
    """Indicates if the download was public."""

    parent_id: UUID | None = None
    """Parent download history ID, if applicable."""

    file_path: str
    """Path of the downloaded file."""

    repositories: list[RepositorySummary]
    """List of repository IDs involved in the download."""

    groups: list[GroupSummary]
    """List of group IDs involved in the download."""

    users: list[UserSummary]
    """List of user IDs involved in the download."""

    children_count: int = 0
    """Number of related child elements."""

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""


class UploadHistoryData(BaseModel):
    """Upload history data model."""

    id: UUID
    """Upload history ID."""

    timestamp: datetime
    """Timestamp of the upload event."""

    end_timestamp: datetime | None = None
    """Timestamp end of the upload event."""

    public: bool
    """Indicates if the upload was public."""

    operator: UserSummary
    """Operator who performed the upload."""

    status: t.Literal["S", "F", "P"]
    """Status of the upload operation."""

    results: list[Results] = Field(default_factory=list)
    """ """

    summary: HistorySummary | None = None
    """ """

    file_path: str
    """Path of the uploaded file."""

    repositories: list[RepositorySummary]
    """List of repository IDs involved in the upload."""

    groups: list[GroupSummary]
    """List of group IDs involved in the upload."""

    users: list[UserSummary]
    """List of user IDs involved in the upload."""

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""


class Results(BaseModel):
    """Result of the upload operation."""

    user_id: str
    """User ID."""

    eppn: list[str]
    """User EPPN."""

    emails: list[str]
    """ User emails"""

    user_name: str
    """User name."""

    group: list[str]
    """Group list."""

    status: t.Literal["C", "U", "S", "D", "E"]
    """Status of the upload operation."""

    code: str | None
    """Error code if the upload failed."""

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""


class HistorySummary(BaseModel):
    """Summary of the history operation."""

    create: int
    """Number of created items."""

    update: int
    """Number of updated items."""

    delete: int
    """Number of deleted items."""

    skip: int
    """Number of skipped items."""

    error: int
    """Number of error items."""


class HistoryQuery(BaseModel):
    """Query parameters for searching history data."""

    s: t.Annotated[date | None, "start"] = None
    """Filter by last modified date (from)."""

    e: t.Annotated[date | None, "end"] = None
    """Filter by last modified date (to)."""

    u: t.Annotated[list[str] | None, "users"] = None
    """Filter by affiliated user IDs."""

    r: t.Annotated[list[str] | None, "repositories"] = None
    """Filter by affiliated repository IDs."""

    g: t.Annotated[list[str] | None, "groups"] = None
    """Filter by affiliated group IDs."""

    o: t.Annotated[list[str] | None, "operator"] = None
    """Filter by operator IDs"""

    i: t.Annotated[str | None, "id"] = None
    """Filter by Parent ID to retrieve child elements """

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


class HistoryDataFilter(BaseModel):
    """Available filters for history data."""

    operators: list[UserSummary]
    """List of operators."""

    target_repositories: list[RepositorySummary]
    """List of target repositories."""

    target_groups: list[GroupSummary]
    """List of target groups."""

    target_users: list[UserSummary]
    """List of target users."""
