#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Permission-related services for the server application."""

import typing as t

from urllib.parse import urlparse

from flask_login import current_user

from server.config import config
from server.const import USER_ROLES
from server.entities.map_group import MapGroup
from server.entities.map_service import MapService


if t.TYPE_CHECKING:
    from server.entities.map_user import MapUser
    from server.services.utils.affiliations import Affiliations


def extract_group_ids(is_member_of: str) -> list[str]:
    """Extract group id from isMemberOf.

    Args:
        is_member_of (str):isMemberOf attribute of the login user

    Returns:
        list[str]: List of groups to which the login user belongs.
    """
    groups: list[str] = []
    for part in is_member_of.split(";"):
        url = part.strip()
        if not url:
            continue
        segs = [s for s in urlparse(url).path.split("/") if s]
        for i, s in enumerate(segs):
            if s.lower() == "gr" and i + 1 < len(segs):
                group = segs[i + 1]
                groups.append(group)
                break

    return list(dict.fromkeys(groups))


def is_current_user_system_admin() -> bool:
    """Determine whether the logged-in user is a system administrator.

    Returns:
        bool: if logged-in user is a system administrator, true
    """
    is_member_of = current_user.is_member_of
    group_ids = extract_group_ids(is_member_of)
    return config.GROUPS.id_patterns.system_admin in group_ids


def get_permitted_repository_ids() -> set[str]:
    """Get the list of repository IDs the current user has permission to access.

    Returns:
        list[str]: List of current user's permitted repository IDs.
    """
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

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
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

    repository_ids = get_permitted_repository_ids()
    _, affiliations = detect_affiliations(list(group_id))

    return {g.group_id for g in affiliations if g.repository_id in repository_ids}


def get_login_user_roles() -> Affiliations:
    """Retrieve the affiliations and roles of the currently logged-in user.

    Returns:
        Affiliations:
    """
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

    is_member_of = current_user.is_member_of
    group_ids = extract_group_ids(is_member_of)
    return detect_affiliations(group_ids)


def remove_info_outside_system(
    entity: MapService | MapGroup | MapUser,
) -> MapService | MapGroup | MapUser:
    """Remove information from the entity that is outside the system.

    Args:
        entity (MapService | MapGroup | MapUser): The entity to process.

    Returns:
        MapService | MapGroup | MapUser:
          The entity with external information removed as appropriate.
    """
    if isinstance(entity, MapService):
        return remove_external_info_service(entity)
    if isinstance(entity, MapGroup):
        return remove_external_info_group(entity)
    return remove_external_info_user(entity)


def remove_external_info_service(entity: MapService) -> MapService:
    """Remove external information from a MapService entity based on user permissions.

    Args:
        entity (MapService): The target MapService entity.

    Returns:
        MapService:
        The MapService entity with external information removed as appropriate.
    """
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

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


def remove_external_info_group(entity: MapGroup) -> MapGroup:
    """Remove external information from a MapGroup entity based on user permissions.

    Args:
        entity (MapGroup): The target MapGroup entity.

    Returns:
        MapGroup: The MapGroup entity with external information removed as appropriate.
    """
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

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


def remove_external_info_user(entity: MapUser) -> MapUser:
    """Remove external information from a MapUser entity based on user permissions.

    Args:
        entity (MapUser): The target MapUser entity.

    Returns:
        MapUser: The MapUser entity with external information removed as appropriate.
    """
    from .utils.affiliations import detect_affiliations  # noqa: PLC0415

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
