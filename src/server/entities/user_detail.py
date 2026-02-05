#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for User entity for client side."""

import typing as t

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator
from pydantic.alias_generators import to_snake

from server.const import USER_ROLES

from .common import camel_case_config, forbid_extra_config
from .map_user import EPPN, Email, Group, MapUser
from .summaries import GroupSummary


class UserDetail(BaseModel):
    """Model for detailed User information in mAP Core API."""

    id: str | None = None
    """The unique identifier for the user."""

    eppns: list[str] | None = None
    """The eduPersonPrincipalNames of the user."""

    user_name: str
    """The username of the user. Alias to 'userName'."""

    emails: list[EmailStr] | None = None
    """The email addresses of the user."""

    preferred_language: t.Literal["en", "ja", ""] | None = None
    """The preferred language of the user. Alias to 'preferredLanguage'."""

    is_system_admin: bool | None = None
    """Whether the user is a system administrator. Alias to 'isSystemAdmin'."""

    repository_roles: list[RepositoryRole] | None = None
    """The affiliated repositories of the user."""

    groups: list[GroupSummary] | None = None
    """The affiliated user-defined groups of the user."""

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
        from server.services import groups, repositories  # noqa: PLC0415
        from server.services.utils import (  # noqa: PLC0415
            detect_affiliations,
            make_criteria_object,
        )

        resolved_groups: list[GroupSummary] | None = None
        resolved_repos: list[RepositoryRole] | None = None
        is_system_admin = False

        if user.groups:
            detected_repos, detected_groups = detect_affiliations([
                group.value for group in user.groups
            ])

            user_role_map = {repo.repository_id: repo.role for repo in detected_repos}
            if None in user_role_map:
                # System Administrator did not affiliate with any repository
                is_system_admin = user_role_map[None] == USER_ROLES.SYSTEM_ADMIN

            if detected_groups:
                group_query = make_criteria_object(
                    "groups", i=[grp.group_id for grp in detected_groups]
                )
                resolved_groups = groups.search(criteria=group_query).resources

            if detected_repos:
                repositories_query = make_criteria_object(
                    "repositories", i=[r for r in user_role_map if r]
                )
                resolved_repos = [
                    RepositoryRole(
                        id=repo.id,
                        service_name=repo.service_name,
                        user_role=user_role_map[repo.id],
                    )
                    for repo in repositories.search(
                        criteria=repositories_query
                    ).resources
                ]

        return cls(
            id=user.id,
            eppns=[eppn.value for eppn in user.edu_person_principal_names or []],
            user_name=user.user_name or "",
            emails=[email.value for email in user.emails or []],
            preferred_language=user.preferred_language,
            is_system_admin=is_system_admin,
            repository_roles=resolved_repos,
            groups=resolved_groups,
            created=user.meta.created if user.meta else None,
            last_modified=user.meta.last_modified if user.meta else None,
        )

    def to_map_user(self) -> MapUser:
        """Convert this UserDetail instance to a MapUser instance.

        Returns:
            MapUser: The created MapUser instance.
        """
        user = MapUser()
        user.id = self.id
        user.user_name = self.user_name
        if self.preferred_language:
            user.preferred_language = self.preferred_language
        if self.eppns:
            user.edu_person_principal_names = [EPPN(value=eppn) for eppn in self.eppns]
        if self.emails:
            user.emails = [Email(value=email) for email in self.emails]
        if self.groups:
            user.groups = [Group(value=group.id) for group in self.groups]
        return user


class RepositoryRole(BaseModel):
    """Model for summary Repository information in mAP Core API."""

    id: str
    """The unique identifier for the repository."""

    service_name: str | None = None
    """The name of the repository. Alias to 'serviceName'."""

    user_role: USER_ROLES | None = None
    """The role of the user in the repository. Alias to 'userRole'."""

    @field_validator("user_role", mode="before")
    @classmethod
    def transform_user_role(cls, v: t.Any) -> t.Any:  # noqa: ANN401
        """Transform the user_role field to USER_ROLES enum.

        Args:
            v (Any): The value to transform.

        Returns:
            Any: The transformed value.
        """
        if isinstance(v, str):
            return to_snake(v)
        return v

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""
