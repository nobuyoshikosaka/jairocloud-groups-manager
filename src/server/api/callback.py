#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for callback endpoints."""

from flask import Blueprint, redirect
from flask_pydantic import validate
from werkzeug.wrappers import Response as ResponseBase  # noqa: TC002

from server.services import token

from .schema import OAuthTokenQuery  # noqa: TC001

bp = Blueprint("callback", __name__)


@bp.get("/auth-code")
@validate()
def auth_code(query: OAuthTokenQuery) -> ResponseBase:
    """Handle the authorization code callback.

    This endpoint receives the authorization code from the
    mAP Core Authorization Server following user operation.

    Returns:
        Response: Redirect response to the home page.
    """
    token.issue_access_token(query.code)
    return redirect("/")
