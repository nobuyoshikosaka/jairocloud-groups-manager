#
# Copyright (C) 2025 National Institute of Informatics.
#

"""helper for api decorator."""

import typing as t

from datetime import UTC, datetime

from flask import session
from flask_login import LoginManager, current_user

from server.config import config
from server.datastore import account_store
from server.entities.login_user import LoginUser


if t.TYPE_CHECKING:
    from flask_login import AnonymousUserMixin
    from werkzeug.local import LocalProxy

    type CurrentUser = LoginUser | AnonymousUserMixin

login_manager = LoginManager()


def is_user_logged_in(current_user: LocalProxy) -> t.TypeGuard[LoginUser]:
    """Guard to check if the current_user is of type LoginUser.

    Args:
        current_user: The current user object.

    Returns:
        TypeGuard[LoginUser]: True if current_user is LoginUser, else False.
    """
    return t.cast("CurrentUser", current_user).is_authenticated


def refresh_session() -> None:
    """Extend the TTL of the Redis login state for login users."""
    if not is_user_logged_in(current_user):
        return

    session_id: str = current_user.session_id or session["_id"]

    key = build_account_store_key(session_id)
    login_date_raw = account_store.hget(key, "loginDate")
    if isinstance(login_date_raw, bytes):
        login_date_raw = login_date_raw.decode("utf-8")
    if not isinstance(login_date_raw, str):
        return

    login_date = datetime.fromisoformat(login_date_raw)
    time_since_login = datetime.now(UTC) - login_date
    if time_since_login.total_seconds() > config.SESSION.absolute_lifetime:
        account_store.delete(key)
        return

    session_ttl: int = config.SESSION.sliding_lifetime
    if session_ttl >= 0:
        account_store.expire(key, session_ttl)


@login_manager.user_loader
def load_user(eppn: str) -> LoginUser | None:
    """Load a user from the session using the eppn.

    Args:
        eppn (str): The unique identifier for the user.

    Returns:
        LoginUser | None: The loaded user object if found, otherwise None.
    """
    if not eppn:
        return None

    session_id: str | None = session.get("_id")
    if not session_id:
        return None

    user = get_user_from_store(session_id)
    if user and user.eppn != eppn:
        return None
    return user


def get_user_from_store(session_id: str) -> LoginUser | None:
    """Retrieve a user from the account store using eppn and session_id.

    Args:
        session_id (str): The unique identifier for the user's session.

    Returns:
        LoginUser | None: The user object if found, otherwise None.
    """
    key = build_account_store_key(session_id)
    raw = account_store.hgetall(key)
    if not raw:
        return None

    data = {
        k.decode("utf-8"): v.decode("utf-8")
        for k, v in t.cast("dict[bytes, bytes]", raw).items()
    }

    return LoginUser.model_validate(data | {"session_id": session_id})


def build_account_store_key(session_id: str) -> str:
    """Build the account_store key.

    Args:
        session_id(str):Logged-in user's session ID

    Returns:
        str:Session information key for account_store
    """
    return f"{config.REDIS.key_prefix}_login_{session_id}"
