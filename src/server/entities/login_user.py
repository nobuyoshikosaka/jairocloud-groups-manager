#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for login user entity for client side."""

from pydantic import BaseModel

from .common import camel_case_config


class LoginUser(BaseModel):
    """Model for login user information."""

    id: str
    """The unique identifier for the user."""

    user_name: str
    """The username of the user."""

    is_system_admin: bool = False
    """Indicates if the user has roles of System Administrator."""

    model_config = camel_case_config
    """Configure to use camelCase aliasing."""
