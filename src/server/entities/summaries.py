#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for Summary entities for client side."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, HttpUrl

from .common import camel_case_config, forbid_extra_config
from .map_group import Visibility


class RepositorySummary(BaseModel):
    """Model for summary Repository information in mAP Core API."""

    id: str
    """The unique identifier for the repository."""

    display_name: str | None = None
    """The name of the repository. Alias to 'displayName'."""

    service_url: HttpUrl | None = None
    """The URL of the service. Alias for 'serviceUrl'."""

    sp_connecter_id: str | None = None
    """The SP Connecter ID of the repository. Alias to 'spConnecterId'."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""


class GroupSummary(BaseModel):
    """Model for summary Group information in mAP Core API."""

    id: str
    """The unique identifier for the group."""

    display_name: str | None = None
    """The display name of the group. Alias to 'displayName'."""

    public: bool | None = None
    """Whether the group is public or private."""

    member_list_visibility: Visibility | None = None
    """The visibility of the member list. Alias to 'memberListVisibility'."""

    users_count: int | None = None
    """The number of users in the group. Alias to 'usersCount'."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""


class UserSummary(BaseModel):
    """Model for summary User information in mAP Core API."""

    id: str
    """The unique identifier for the user."""

    user_name: str | None = None
    """The username of the user. Alias to 'userName'."""

    email: EmailStr | None = None
    """The first email address of the user."""

    eppn: str | None = None
    """The first eduPersonPrincipalName of the user."""

    lask_modified: datetime | None = None
    """The last modification timestamp of the user. Alias to 'lastModified'."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""
