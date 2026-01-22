#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for authentication endpoints."""

from urllib.parse import quote

from flask import (
    Blueprint,
    Response,
    current_app,
    make_response,
    redirect,
    request,
    session,
)
from flask_login import LoginManager, login_user, logout_user
from flask_pydantic import validate

from server.config import config
from server.const import USER_ROLES
from server.datastore import account_store
from server.entities.login_user import LoginUser
from server.exc import (
    ResourceInvalid,
    ResourceNotFound,
)
from server.services import permission, users
from server.services.utils.affiliations import detect_affiliations


bp = Blueprint("auth", __name__)
login_manager = LoginManager()


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

    try:
        if not is_member_of:
            groups = users.extract_groups_with_eppn(eppn)
            is_member_of = ";".join(
                f"https://cg.gakunin.jp/gr/{quote(g, safe='')}" for g in groups
            )
        if not user_name:
            user_name = users.get_user_name_from_eppn(eppn)
    except (
        ResourceInvalid,
        ResourceNotFound,
    ):
        current_app.logger.error(eppn)
        return make_response(redirect("/?error=401"))
    groups = permission.extract_group_ids(is_member_of)
    user_roles, _ = detect_affiliations(groups)
    if not any(
        role in {USER_ROLES.SYSTEM_ADMIN, USER_ROLES.REPOSITORY_ADMIN}
        for r in user_roles
        for role in r.roles
    ):
        return make_response(redirect("/?error=403"))

    user = LoginUser(eppn=eppn, is_member_of=is_member_of, user_name=user_name)

    login_user(user)
    session_id: str = session.get("_id")  # pyright: ignore[reportAssignmentType]
    user._session_id = session_id
    key = f"{config.REDIS.key_prefix}_login_{session_id}"
    account_store.hset(
        key,
        mapping=user.model_dump(mode="json", by_alias=True),
    )
    if config.REDIS.session_ttl >= 0:
        account_store.expire(key, config.REDIS.session_ttl)
    next_q = request.args.get("next")
    target = "/" if not next_q else f"/?next={next_q}"
    return make_response(redirect(target))


@login_manager.user_loader
def load_user(user_id: str) -> LoginUser | None:
    """Load a user from the session using the user_id.

    Args:
        user_id (str): The unique identifier for the user.

    Returns:
        LoginUser | None: The loaded user object if found, otherwise None.
    """
    if not user_id:
        return None

    session_id: str = session.get("_id")  # pyright: ignore[reportAssignmentType]
    if not session_id:
        return None

    key = f"{config.REDIS.key_prefix}_login_{session_id}"
    data: dict = account_store.hgetall(key)
    if not data:
        return None

    if not data["eppn"] or data["eppn"] != user_id:
        return None

    user = LoginUser(
        eppn=data["eppn"],
        login_date=data["login_date"],
        user_name=data["user_name"],
        is_member_of=data["is_member_of"],
    )
    user._session_id = session_id
    return user


@bp.get("/logout")
def logout() -> Response:
    """Log out the current user and clear their session.

    Returns:
        Response: redirect login page
    """
    session_id: str = session.get("_id")  # pyright: ignore[reportAssignmentType]
    if session_id:
        key = f"{config.REDIS.key_prefix}_login_{session_id}"
        account_store.delete(key)
    logout_user()

    return make_response(redirect("/login"))
