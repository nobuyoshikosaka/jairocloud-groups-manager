#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for login user entity for client side."""

from datetime import UTC, datetime
from functools import cached_property
from typing import override

from flask_login import UserMixin
from pydantic import BaseModel, Field, PrivateAttr

from server.services import permission

from .common import camel_case_config


class LoginUser(BaseModel, UserMixin):
    """Model for login user information."""

    eppn: str
    """The unique identifier for the user."""

    login_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Login date and time. Cached in ISO 6018 format."""

    is_member_of: str
    """login user isMemberOf attribute"""

    user_name: str = Field(exclude=True)

    _session_id: str | None = PrivateAttr(None)

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""

    @cached_property
    def is_system_admin(self) -> bool:
        """If the logged-in user is a system administrator, then True."""
        return permission.is_current_user_system_admin()

    @override
    def get_id(self) -> str:
        return self.eppn
