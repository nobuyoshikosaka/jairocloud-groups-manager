#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Permission-related services for the server application."""

import re
import typing as t

from flask_login import current_user

from server.auth import is_user_logged_in
from server.const import IS_MEMBER_OF_PATTERN, USER_ROLES
from server.entities.map_group import MapGroup
from server.entities.map_service import MapService
from server.entities.map_user import MapUser

from .affiliations import detect_affiliations


if t.TYPE_CHECKING:
    from flask_login import AnonymousUserMixin

    from server.entities.login_user import LoginUser

    from .affiliations import Affiliations

    type CurrentUser = LoginUser | AnonymousUserMixin


def extract_group_ids(is_member_of: str) -> list[str]:
    """Extract group id from isMemberOf.

    Args:
        is_member_of (str):isMemberOf attribute of the login user

    Returns:
        list[str]: List of group IDs to which the login user belongs.
    """
    return re.findall(IS_MEMBER_OF_PATTERN, is_member_of)


def is_current_user_system_admin() -> bool:
    """Determine whether the logged-in user is a system administrator.

    Returns:
        bool: if logged-in user is a system administrator, true
    """
    if not is_user_logged_in(current_user):
        return False

    return current_user.is_system_admin


def get_permitted_repository_ids() -> set[str]:
    """Get the list of repository IDs the current user has permission to access.

    Returns:
        list[str]: List of current user's permitted repository IDs.
    """
    if not is_user_logged_in(current_user):
        return set()

    is_member_of: str = current_user.is_member_of
    group_ids = extract_group_ids(is_member_of)
    affiliations, _ = detect_affiliations(group_ids)

    return {
        aff.repository_id
        for aff in affiliations
        if aff.repository_id and aff.role == USER_ROLES.REPOSITORY_ADMIN
    }


def filter_permitted_group_ids(*group_id: str) -> set[str]:
    """Check if the given group ID is manageable by the current user.

    Args:
        group_id (str): The group ID.

    Returns:
        bool: True if manageable, otherwise False.
    """
    repository_ids = get_permitted_repository_ids()
    _, affiliations = detect_affiliations(list(group_id))

    return {g.group_id for g in affiliations if g.repository_id in repository_ids}


def get_current_user_affiliations() -> Affiliations:
    """Retrieve the affiliations and roles of the currently logged-in user.

    Returns:
        Affiliations:
            Detected affiliations including `roles` and `groups`.
            - roles: list of role-type groups.
              that is, (`repository_id`, `roles`, `type`="role")
            - groups: list of user-defined groups
              that is, (`repository_id`, `group_id`, `user_defined_id`, `type`="group").
    """
    is_member_of = ""
    if is_user_logged_in(current_user):
        is_member_of = current_user.is_member_of

    group_ids = extract_group_ids(is_member_of)
    return detect_affiliations(group_ids)


def remove_info_outside_system[T = MapService | MapGroup | MapUser](entity: T) -> T:
    """Remove external information.

    Remove information from the entity that is outside the system based
    on user permissions.

    Args:
        entity (T = MapService | MapGroup | MapUser): The target entity.

    Returns:
        T: The entity with external information removed as appropriate.
    """
    match entity:
        case MapService():
            return remove_info_outside_system_service(entity)
        case MapGroup():
            return remove_info_outside_system_group(entity)
        case MapUser():
            return remove_info_outside_system_user(entity)
        case _:
            return entity


def remove_info_outside_system_service(entity: MapService) -> MapService:
    """Remove external information from a MapService entity based on user permissions.

    Args:
        entity (MapService): The target MapService entity.

    Returns:
        MapService:
            The MapService entity with external information removed as appropriate.
    """
    if entity.groups:
        group_list = [g.value for g in entity.groups]
        _, groups = detect_affiliations(group_list)
        if current_user.is_system_admin:
            permitted_ids = {g.group_id for g in groups}
            entity.groups = [g for g in entity.groups if g.value in permitted_ids]
        else:
            permitted_repo_ids = get_permitted_repository_ids()
            permitted_ids = {
                g.group_id for g in groups if g.repository_id in permitted_repo_ids
            }
            entity.groups = [g for g in entity.groups if g.value in permitted_ids]
    return entity


def remove_info_outside_system_group(entity: MapGroup) -> MapGroup:
    """Remove external information from a MapGroup entity based on user permissions.

    Args:
        entity (MapGroup): The target MapGroup entity.

    Returns:
        MapGroup: The MapGroup entity with external information removed as appropriate.
    """
    if entity.members:
        group_list = [g.value for g in entity.members if g.type == "Group"]
        _, groups = detect_affiliations(group_list)
        if current_user.is_system_admin:
            permitted_ids = {g.group_id for g in groups}
            entity.members = [g for g in entity.members if g.value in permitted_ids]
        else:
            permitted_repo_ids = get_permitted_repository_ids()
            permitted_ids = {
                g.group_id for g in groups if g.repository_id in permitted_repo_ids
            }
            entity.members = [g for g in entity.members if g.value in permitted_ids]
    return entity


def remove_info_outside_system_user(entity: MapUser) -> MapUser:
    """Remove external information from a MapUser entity based on user permissions.

    Args:
        entity (MapUser): The target MapUser entity.

    Returns:
        MapUser: The MapUser entity with external information removed as appropriate.
    """
    if entity.groups:
        group_list = [g.value for g in entity.groups]
        _, groups = detect_affiliations(group_list)
        if current_user.is_system_admin:
            permitted_ids = {g.group_id for g in groups}
            entity.groups = [g for g in entity.groups if g.value in permitted_ids]
        else:
            permitted_repo_ids = get_permitted_repository_ids()
            permitted_ids = {
                g.group_id for g in groups if g.repository_id in permitted_repo_ids
            }
            entity.groups = [g for g in entity.groups if g.value in permitted_ids]
    return entity
