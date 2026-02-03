#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for authentication endpoints."""

from urllib.parse import quote

from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    request,
    session,
)
from flask_login import login_user, logout_user
from flask_pydantic import validate

from server.api.helper import build_account_store_key
from server.config import config
from server.const import USER_ROLES
from server.datastore import account_store
from server.entities.login_user import LoginUser
from server.services import permissions, users
from server.services.utils import affiliations


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
        eppn="anonymous",
        user_name="Anonymous User",
        is_member_of="",
    ), 200


@bp.get("/login")
def login() -> Response:
    """Handle user login, validate authorization, create session.

    Returns:
        Response: if successful login, redirect to the top page.
    """
    eppn = request.headers.get("eppn")
    is_member_of = request.headers.get("IsMemberOf")
    user_name = request.headers.get("DisplayName")
    if not eppn:
        return make_response(redirect("/?error=401"))

    if not is_member_of or not user_name:
        user = users.get_by_eppn(eppn)
        if not user:
            return make_response(redirect("/?error=404"))
        groups = [group.id for group in user.groups or []]
        user_name = user.user_name or "Unknown User"
        is_member_of = ";".join(
            f"https://cg.gakunin.jp/gr/{quote(g, safe='')}" for g in groups
        )
    else:
        groups = permissions.extract_group_ids(is_member_of)
    user_roles = affiliations.detect_affiliations(groups).roles
    if not any(
        role in {USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN}
        for r in user_roles
        for role in r.roles
    ):
        return make_response(redirect("/?error=403"))

    user = LoginUser(eppn=eppn, is_member_of=is_member_of, user_name=user_name)

    login_user(user)
    session_id: str = session.get("_id")  # pyright: ignore[reportAssignmentType]
    user._session_id = session_id  # noqa: SLF001
    key = build_account_store_key(session_id)
    account_store.hset(
        key,
        mapping=user.model_dump(mode="json", by_alias=True),
    )
    session_ttl: int = config.SESSION.sliding_lifetime
    if session_ttl >= 0:
        account_store.expire(key, session_ttl)
    next_q = request.args.get("next")
    target = "/" if not next_q else f"/?next={next_q}"
    return make_response(redirect(target))


@bp.get("/logout")
def logout() -> Response:
    """Log out the current user and clear their session.

    Returns:
        Response: redirect login page
    """
    session_id: str = session.get("_id")  # pyright: ignore[reportAssignmentType]
    if session_id:
        key = build_account_store_key(session_id)
        account_store.delete(key)
    logout_user()

    return make_response(redirect("/"))
