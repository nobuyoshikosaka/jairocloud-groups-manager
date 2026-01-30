#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for User entity for client side."""

import typing as t

from datetime import datetime

from pydantic import BaseModel, EmailStr

from server.const import USER_ROLES

from .common import camel_case_config, forbid_extra_config
from .map_user import EPPN, Email, Group, MapUser
from .summaries import GroupSummary, RepositorySummary


class UserDetail(BaseModel):
    """Model for detailed User information in mAP Core API."""

    id: str
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

    repositories: list[RepositorySummary] | None = None

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
        from server.services import groups, repositories  # noqa: PLC0415
        from server.services.utils import detect_affiliations  # noqa: PLC0415

        resolved_groups: list[GroupSummary] = []
        resolved_repos: list[RepositorySummary] = []
        is_system_admin = False

        if user.groups:
            detected_repos, detected_groups = detect_affiliations([
                group.value for group in user.groups
            ])

            repo_role_map = {repo.repository_id: repo.roles for repo in detected_repos}
            if None in repo_role_map:
                # System Administrator did not affiliate with any repository
                is_system_admin = USER_ROLES.SYSTEM_ADMIN in repo_role_map[None]
                del repo_role_map[None]

            resolved_groups = groups.search(
                ids=[grp.group_id for grp in detected_groups]
            )
            resolved_repos += [
                repo.model_copy(update={"user_roles": repo_role_map.get(repo.id)})
                for repo in repositories.search(
                    ids=[r.repository_id for r in detected_repos]
                )
            ]

        return cls(
            id=user.id,
            eppns=[eppn.value for eppn in user.edu_person_principal_names or []],
            user_name=user.user_name or "",
            emails=[email.value for email in user.emails or []],
            preferred_language=user.preferred_language,
            is_system_admin=is_system_admin,
            repositories=resolved_repos,
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
        if self.eppns:
            user.edu_person_principal_names = [EPPN(value=eppn) for eppn in self.eppns]
        if self.emails:
            user.emails = [Email(value=email) for email in self.emails]
        if self.groups:
            user.groups = [Group(value=group.id) for group in self.groups]
        return user

    def __add__(self, other: UserDetail) -> UserDetail:
        if not isinstance(other, UserDetail):
            return NotImplemented
        if self.id != other.id:
            raise ValueError(f"Cannot merge different users: {self.id} != {other.id}")

        def choose_scalar(lhs, rhs):
            # 右辺が None なら lhs、文字列は空なら lhs、それ以外は rhs
            if rhs is None:
                return lhs
            if isinstance(rhs, str) and rhs.strip() == "":
                return lhs
            return rhs

        def merge_list(lhs: t.Sequence | None, rhs: t.Sequence | None):
            if not lhs and not rhs:
                return None
            s = set(lhs or [])
            s.update(rhs or [])
            return list(s)

        def merge_models_by_id(
            lhs: t.Sequence[BaseModel] | None, rhs: t.Sequence[BaseModel] | None
        ):
            if not lhs and not rhs:
                return None
            by_id: dict[str, BaseModel] = {}
            for x in lhs or []:
                by_id[x.id] = x
            for x in rhs or []:
                by_id[x.id] = x
            out = list(by_id.values())
            out.sort(key=lambda m: m.id)
            return out

        return UserDetail(
            id=self.id,
            eppns=merge_list(self.eppns, other.eppns),
            user_name=choose_scalar(self.user_name, other.user_name),
            emails=merge_list(self.emails, other.emails),
            preferred_language=choose_scalar(
                self.preferred_language, other.preferred_language
            ),
            is_system_admin=choose_scalar(self.is_system_admin, other.is_system_admin),
            repositories=merge_models_by_id(self.repositories, other.repositories),
            groups=merge_models_by_id(self.groups, other.groups),
            created=choose_scalar(self.created, other.created),
            last_modified=choose_scalar(self.last_modified, other.last_modified),
        )

    def __iadd__(self, other: UserDetail) -> UserDetail:
        return self + other
