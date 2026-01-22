#
# Copyright (C) 2025 National Institute of Informatics.
#

"""helper for api decorator."""

import typing as t

from functools import wraps

from flask import abort, session
from flask_login import current_user, login_required

from server.config import config
from server.datastore import account_store
from server.services import permission


def roles_required(*roles: str) -> t.Callable:
    """Verify that the user has the requested role."""

    def decorator(func):
        @wraps(func)
        @login_required
        def decorated_view(*args, **kwargs):
            user_roles, _ = permission.get_login_user_roles() or []
            if not any(role in user_roles for role in roles):
                abort(403)

            return func(*args, **kwargs)

        return decorated_view

    return decorator


def refresh_session() -> None:
    """Extend the TTL of the Redis login state for login users."""
    if not current_user.is_authenticated:
        return

    session_id = getattr(current_user, "_session_id", None) or session.get("_id")
    if not session_id:
        return

    key = f"{config.REDIS.key_prefix}_login_{session_id}"

    account_store.expire(key, config.REDIS.session_ttl)
