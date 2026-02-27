#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for authentication endpoints."""

import typing as t
import urllib.parse as urlparse

from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    request,
    session,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_pydantic import validate

from server.auth import build_account_store_key
from server.config import config
from server.const import SHIB_HEADERS, USER_ROLES
from server.datastore import account_store
from server.entities.login_user import LoginUser
from server.services import users
from server.services.utils import detect_affiliations, extract_group_ids

from .schemas import LoginUserState


bp = Blueprint("auth", __name__)


@bp.get("/check")
@login_required
@validate(response_by_alias=True, exclude_none=True)
def check() -> tuple[LoginUserState, int]:
    """Check the authentication status.

    Returns:
        dict: Authentication status.
    """
    user = t.cast("LoginUser", current_user)

    return LoginUserState(
        id=user.map_id,
        eppn=user.eppn,
        user_name=user.user_name,
        is_system_admin=user.is_system_admin,
    ), 200


@bp.get("/login")
def login() -> Response:
    """Handle user login, validate authorization, create session.

    Returns:
        Response: if successful login, redirect to the top page.
    """
    eppn = request.headers.get(SHIB_HEADERS.EPPN)
    is_member_of = request.headers.get(SHIB_HEADERS.IS_MEMBER_OF)
    user_name = request.headers.get(SHIB_HEADERS.DISPLAY_NAME)

    if not eppn:
        return make_response(redirect("/?error=401"))

    user = users.get_by_eppn(eppn)
    if not user:
        return make_response(redirect("/?error=401"))

    user_name = user.user_name if user_name is None else user_name
    is_member_of = (
        ";".join(
            f"https://cg.gakunin.jp/gr/{urlparse.quote(g.id, safe='')}"
            for g in user.groups or []
        )
        if is_member_of is None
        else is_member_of
    )

    groups = extract_group_ids(is_member_of)
    user_roles, _ = detect_affiliations(groups)
    if not any(
        r.role in {USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN}
        for r in user_roles
    ):
        return make_response(redirect("/?error=403"))

    user = LoginUser(
        eppn=eppn,
        is_member_of=is_member_of,
        user_name=user_name,
        map_id=t.cast("str", user.id),
        session_id="",
    )
    alias: t.Callable[[str], str] = LoginUser.model_config.get(
        "alias_generator", lambda x: x
    )  # pyright: ignore[reportAssignmentType]

    login_user(user)
    user.session_id = session_id = session["_id"]

    key = build_account_store_key(session_id)
    account_data = user.model_dump(mode="json", by_alias=True) | {
        alias("is_system_admin"): str(user.is_system_admin)
    }
    account_store.hset(key, mapping=account_data)
    session_ttl: int = config.SESSION.sliding_lifetime
    if session_ttl >= 0:
        account_store.expire(key, session_ttl)

    next_location = request.args.get("next")
    location = "/" if not next_location else f"/?next={next_location}"

    return make_response(redirect(location))


@bp.get("/logout")
@login_required
def logout() -> tuple[t.Literal[""], int]:
    """Log out the current user and clear their session.

    Returns:
        Response: redirect login page
    """
    session_id: str = session["_id"]
    if session_id:
        key = build_account_store_key(session_id)
        account_store.delete(key)

    logout_user()

    return "", 204
