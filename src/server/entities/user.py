#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for User entity for client side."""

import typing as t

from datetime import datetime

from pydantic import BaseModel, EmailStr

from .common import camel_case_config, forbid_extra_config
from .map_user import EPPN, Email, Group, MapUser
from .summaries import GroupSummary


class UserDetail(BaseModel):
    """Model for detailed User information in mAP Core API."""

    id: str
    """The unique identifier for the user."""

    eppn: list[str] | None = None
    """The eduPersonPrincipalNames of the user."""

    user_name: str
    """The username of the user. Alias to 'userName'."""

    emails: list[EmailStr] | None = None
    """The email addresses of the user."""

    preferred_language: t.Literal["en", "ja", ""] | None = None
    """The preferred language of the user. Alias to 'preferredLanguage'."""

    groups: list[GroupSummary] | None = None
    """The groups the user belongs to."""

    created: datetime | None = None
    """The creation timestamp of the user."""

    last_modified: datetime | None = None
    """The last modification timestamp of the user. Alias to 'lastModified'."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""

    @classmethod
    def from_map_user(cls, user: MapUser) -> UserDetail:
        """Create a UserDetail instance from a MapUser instance.

        Args:
            user (MapUser): The MapUser instance to convert.

        Returns:
            UserDetail: The created UserDetail instance.
        """
        from server.services import groups  # noqa: PLC0415

        resolved_groups: list[GroupSummary] = []
        if user.groups:
            group_ids = [group.value for group in user.groups]
            resolved_groups = groups.search(id=group_ids)

        return cls(
            id=user.id,
            eppn=[eppn.value for eppn in user.edu_person_principal_names or []],
            user_name=user.user_name or "",
            emails=[email.value for email in user.emails or []],
            preferred_language=user.preferred_language,
            groups=resolved_groups,
            created=user.meta.created if user.meta else None,
            last_modified=user.meta.last_modified if user.meta else None,
        )

    def to_map_user(self) -> MapUser:
        """Convert this UserDetail instance to a MapUser instance.

        Returns:
            MapUser: The created MapUser instance.
        """
        user = MapUser(id=self.id)
        user.user_name = self.user_name
        if self.preferred_language:
            user.preferred_language = self.preferred_language
        if self.eppn:
            user.edu_person_principal_names = [EPPN(value=eppn) for eppn in self.eppn]
        if self.emails:
            user.emails = [Email(value=email) for email in self.emails]
        if self.groups:
            user.groups = [Group(value=group.id) for group in self.groups]
        return user
