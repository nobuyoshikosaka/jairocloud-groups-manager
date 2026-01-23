#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Permission-related services for the server application."""

from flask_login import current_user

from server.const import USER_ROLES

from .utils.affiliations import detect_affiliations


def extract_group_ids(is_member_of: str) -> list[str]: ...


def is_current_user_system_admin() -> bool:
    # placeholder implementation
    return True


def get_permitted_repository_ids() -> set[str]:
    """Get the list of repository IDs the current user has permission to access.

    Returns:
        list[str]: List of current user's permitted repository IDs.
    """
    is_member_of: str = current_user.is_member_of
    group_ids = extract_group_ids(is_member_of)
    affiliations, _ = detect_affiliations(group_ids)

    return {
        aff.repository_id
        for aff in affiliations
        if aff.repository_id and USER_ROLES.REPOSITORY_ADMIN in aff.roles
    }
