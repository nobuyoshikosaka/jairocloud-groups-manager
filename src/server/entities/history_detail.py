#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for history entity for client side."""

import typing as t

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from server.entities.summaries import GroupSummary, RepositorySummary, UserSummary


class DownloadHistory(BaseModel):
    sum_download: int
    first_download: int
    re_download: int
    download_history_data: list[DownloadHistoryData]

    def __init__(self, download_history_data: list[DownloadHistoryData]) -> None:
        self.sum_download = len(download_history_data)
        self.first_download = sum(
            1 for item in download_history_data if item.pearnt_id is None
        )
        self.re_download = self.sum_download - self.first_download
        self.download_history_data = download_history_data


class UploadHistory(BaseModel):
    sum_upload: int
    success_upload: int
    failed_upload: int
    proggres_upload: int
    upload_history_data: list[UploadHistoryData]

    def __init__(self, upload_history_data: list[UploadHistoryData]) -> None:
        self.sum_upload = len(upload_history_data)
        self.success_upload = sum(
            1 for item in upload_history_data if item.status == "S"
        )
        self.failed_upload = sum(
            1 for item in upload_history_data if item.status == "F"
        )
        self.proggres_upload = sum(
            1 for item in upload_history_data if item.status == "P"
        )
        self.upload_history_data = upload_history_data


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

    pearnt_id: UUID | None = None
    """Parent download history ID, if applicable."""

    file_path: str
    """Path of the downloaded file."""

    location: str
    """Location from where the file was downloaded."""

    repositories: list[RepositorySummary]
    """List of repository IDs involved in the download."""

    groups: list[GroupSummary]
    """List of group IDs involved in the download."""

    users: list[UserSummary]
    """List of user IDs involved in the download."""


class UploadHistoryData(BaseModel):
    """Upload history data model."""

    id: UUID
    """Upload history ID."""

    timestamp: datetime
    """Timestamp of the upload event."""

    end_timestamp: datetime
    """Timestamp end of the upload event."""

    public: bool
    """Indicates if the upload was public."""

    operator: UserSummary
    """Operator who performed the upload."""

    status: t.Literal["S", "F", "P"]
    """Status of the upload operation."""

    results: list[Results]
    """ """

    summary: HistorySummary
    """ """

    file_path: str
    """Path of the uploaded file."""

    location: str
    """Location to where the file was uploaded."""

    repositories: list[RepositorySummary]
    """List of repository IDs involved in the upload."""

    groups: list[GroupSummary]
    """List of group IDs involved in the upload."""

    users: list[UserSummary]
    """List of user IDs involved in the upload."""


class Results(BaseModel):
    """"""

    user_id: str
    """"""
    eppn: str
    """"""
    user_name: str
    """"""
    group: list[str]
    """"""
    status: str
    """"""
    code: str
    """"""


class HistorySummary(BaseModel):
    """"""

    create: int
    """"""
    updatte: int
    """"""
    delete: int
    """"""
    skip: int
    """"""
    error: int
    """"""


class HistoryQuery(BaseModel):
    """Query parameters for searching history data."""

    model_config = ConfigDict(populate_by_name=True)

    s: datetime | None = Field(default=None, description="start_date")
    """Start date for filtering history records."""

    e: datetime | None = Field(default=None, description="end_date")
    """End date for filtering history records."""

    u: list[str] | None = Field(default=None, description="user_id")
    """List of user IDs to filter history records."""

    r: list[str] | None = Field(default=None, description="repository_id")
    """List of repository IDs to filter history records."""

    g: list[str] | None = Field(default=None, description="group_id")
    """List of group IDs to filter history records."""

    o: list[str] | None = Field(default=None, description="operator")
    """List of operators to filter history records."""


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


class HistoryPublic(BaseModel):
    pblic: bool
