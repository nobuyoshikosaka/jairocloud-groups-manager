#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for Group entity for client side."""

from datetime import datetime

from pydantic import BaseModel, PrivateAttr

from .common import camel_case_config, forbid_extra_config
from .map_group import Administrator, MapGroup, MemberUser, Visibility
from .summaries import UserSummary


class GroupDetail(BaseModel):
    """Model for detailed Group information in mAP Core API."""

    id: str
    """The unique identifier for the group."""

    display_name: str
    """The display name of the group. Alias to 'displayName'."""

    public: bool | None = None
    """Whether the group is public or private."""

    member_list_visibility: Visibility | None = None
    """The visibility of the member list. Alias to 'memberListVisibility'."""

    created: datetime | None = None
    """The creation timestamp of the group."""

    last_modified: datetime | None = None
    """The last modification timestamp of the group. Alias to 'lastModified'."""

    users_count: int | None = None
    """The number of users in the group. Alias to 'usersCount'."""

    _users: list[UserSummary] | None = PrivateAttr(None)
    """The users in the group."""

    _admins: list[UserSummary] | None = PrivateAttr(None)
    """The administrators of the group."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""

    @classmethod
    def from_map_group(cls, group: MapGroup) -> GroupDetail:
        """Create a GroupDetail instance from a MapGroup instance.

        Args:
            group (MapGroup): The MapGroup instance to convert.

        Returns:
            GroupDetail: The created GroupDetail instance.
        """
        users = [
            UserSummary(id=member.value, user_name=member.display)
            for member in group.members or []
            if isinstance(member, MemberUser)
        ]
        admins = [
            UserSummary(id=admin.value, user_name=admin.display)
            for admin in group.administrators or []
        ]
        group_detail = cls(
            id=group.id,
            display_name=group.display_name or "",
            public=group.public,
            member_list_visibility=group.member_list_visibility,
            created=group.meta.created if group.meta else None,
            last_modified=group.meta.last_modified if group.meta else None,
            users_count=len(users) if group.members else 0,
        )
        group_detail._users = users
        group_detail._admins = admins
        return group_detail

    def to_map_group(self) -> MapGroup:
        """Convert this GroupDetail instance to a MapGroup instance.

        Returns:
            MapGroup: The created MapGroup instance.
        """
        group = MapGroup(id=self.id)
        group.display_name = self.display_name
        if self.public is not None:
            group.public = self.public
        if self.member_list_visibility is not None:
            group.member_list_visibility = self.member_list_visibility
        if self._users:
            group.members = [
                MemberUser(type="User", value=user.id) for user in self._users
            ]
        if self._admins:
            group.administrators = [
                Administrator(value=admin.id) for admin in self._admins
            ]
        return group
