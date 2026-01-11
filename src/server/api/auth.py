#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for authentication endpoints."""

from flask import Blueprint
from flask_pydantic import validate

from server.entities.login_user import LoginUser


bp = Blueprint("auth", __name__)


@bp.get("/check")
@validate(response_by_alias=True)
def check() -> tuple[LoginUser, int]:
    """Check the authentication status.

    Returns:
        dict: Authentication status.
    """
    # NOTE: Placeholder to keep the session alive.
    return LoginUser(
        id="anonymous", user_name="Anonymous User", is_system_admin=True
    ), 200
