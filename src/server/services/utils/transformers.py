#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services to provide resource transformers for entities."""

# ruff: noqa: SLF001

import typing as t

from server.config import config
from server.const import (
    GROUP_DEFAULT_MEMBER_LIST_VISIBILITY,
    GROUP_DEFAULT_PUBLIC,
    USER_ROLES,
)
from server.entities.group_detail import (
    GroupDetail,
    Repository as GroupRepository,
    Service as GroupService_,
)
from server.entities.map_group import (
    Administrator as GroupAdministrator,
    MapGroup,
    MemberUser,
    Service as GroupService,
)
from server.entities.map_service import (
    Administrator,
    Group as MapServiceGroup,
    MapService,
    ServiceEntityID,
)
from server.entities.repository_detail import RepositoryDetail
from server.entities.summaries import UserSummary
from server.exc import InvalidFormError, SystemAdminNotFound

from .affiliations import detect_affiliation
from .resolvers import resolve_repository_id, resolve_service_id
from .search_queries import make_criteria_object


def prepare_service(
    repository: RepositoryDetail, administrators: set[str]
) -> MapService:
    """Prepare MapService instance from RepositoryDetail to create.

    Args:
        repository (RepositoryDetail): The repository detail to be converted.
        administrators (set[str]): The set of administrator user IDs.

    Returns:
        MapService: The converted MapService instance.

    Raises:
        SystemAdminNotFound: If no administrators are provided.
    """
    service = validate_repository_to_map_service(repository)
    repository_id = resolve_repository_id(service_id=service.id)

    if not administrators:
        error = "At least one administrator is required to create a repository."
        raise SystemAdminNotFound(error)

    service.administrators = [
        Administrator(value=user_id) for user_id in administrators
    ]
    service.groups = [
        MapServiceGroup(
            value=config.GROUPS.id_patterns[role].format(repository_id=repository_id)
        )
        for role in USER_ROLES
    ]
    return service


def prepare_role_groups(
    repository_id: str, service_name: str, administrators: set[str]
) -> list[MapGroup]:
    """Prepare role groups for a repository creation.

    Args:
        repository_id (str): The ID of the repository.
        service_name (str): The name of the service.
        administrators (set[str]): The set of administrator user IDs.

    Returns:
        list[MapGroup]: A list of MapGroup instances representing the role groups.
    """
    role_groups = []
    for role in USER_ROLES:
        if role == USER_ROLES.SYSTEM_ADMIN:
            continue  # System admin group is not necessary.

        id_pattern = config.GROUPS.id_patterns[role]
        name_pattern = config.GROUPS.name_patterns[role]
        role_groups.append(
            MapGroup(
                id=id_pattern.format(repository_id=repository_id),
                display_name=name_pattern.format(repository_name=service_name),
                public=False,
                member_list_visibility="Private",
                administrators=[
                    GroupAdministrator(value=user_id) for user_id in administrators
                ],
            )
        )
    return role_groups


def make_repository_detail(
    service: MapService, *, more_detail: bool = False
) -> RepositoryDetail:
    """Convert a MapService instance to a RepositoryDetail instance.

    Args:
        service (MapService): The MapService instance to convert.
        more_detail (bool): Whether to include more details such as groups and users.

    Returns:
        RepositoryDetail: The converted RepositoryDetail instance.
    """
    repository_id = resolve_repository_id(service_id=service.id)

    entity_ids = None
    if service.entity_ids:
        entity_ids = [eid.value for eid in service.entity_ids]

    repository = RepositoryDetail(
        id=repository_id,
        service_id=service.id,
        service_name=service.service_name,
        service_url=service.service_url,
        active=not service.suspended if service.suspended is not None else None,
        entity_ids=entity_ids,
    )

    if not more_detail or not service.groups:
        return repository

    from server.services import users  # noqa: PLC0415

    valid_groups = [
        (g.value, detected)
        for g in service.groups
        if (detected := detect_affiliation(g.value)) is not None
    ]
    detected_rolegroups = [i for i, g in valid_groups if g.type == "role"]
    detected_groups = [i for i, g in valid_groups if g.type == "group"]

    groups_count = len(detected_groups)
    users_count = users.count(make_criteria_object("users", g=detected_groups))

    repository.groups_count = groups_count
    repository.users_count = users_count
    repository.created = service.meta.created if service.meta else None
    repository._groups = detected_groups
    repository._rolegroups = detected_rolegroups
    repository._admins = (
        [admin.value for admin in service.administrators]
        if service.administrators
        else None
    )

    return repository


def validate_repository_to_map_service(repository: RepositoryDetail) -> MapService:
    """Validate the RepositoryDetail instance and convert it to a MapService instance.

    Args:
        repository (RepositoryDetail): The RepositoryDetail instance to convert.

    Returns:
        MapService: The converted MapService instance.

    Raises:
        InvalidFormError:  If the repository cannot be converted to a MapService.
    """
    repository_id = repository.id
    service_url = repository.service_url

    if repository.service_name is None:
        error = "Service name is required to create a repository."
        raise InvalidFormError(error)

    if service_url is None:
        error = "Service URL is required to create a repository."
        raise InvalidFormError(error)

    if repository_id is None:
        fqdn = service_url.host
        repository_id = resolve_repository_id(fqdn=fqdn) if fqdn else None

    if repository_id is None:
        error = "Service URL must contain a valid host."
        raise InvalidFormError(error)

    max_url_length = config.REPOSITORIES.max_url_length
    without_scheme_url = str(service_url).replace(f"{service_url.scheme}://", "")
    if len(without_scheme_url) > max_url_length:
        error = "Service URL is too long."
        raise InvalidFormError(error)

    if not repository.entity_ids:
        error = "At least one entity ID is required to create a repository."
        raise InvalidFormError(error)

    repository.service_id = resolve_service_id(repository_id=repository_id)
    return make_map_service(repository)


def make_map_service(repository: RepositoryDetail) -> MapService:
    """Convert a RepositoryDetail instance to a MapService instance.

    Args:
        repository (RepositoryDetail): The RepositoryDetail instance to convert.

    Returns:
        MapService: The converted MapService instance.
    """
    service_id = repository.service_id or resolve_service_id(
        repository_id=t.cast("str", repository.id)
    )
    service = MapService(
        id=service_id,
        service_name=repository.service_name,
        service_url=repository.service_url,
    )
    if repository.active is not None:
        service.suspended = repository.active is False
    if repository.entity_ids:
        service.entity_ids = [
            ServiceEntityID(value=eid) for eid in repository.entity_ids
        ]
    return service


def prepare_group(
    detail: GroupDetail,
    administrators: set[str],
) -> MapGroup:
    """Prepare a MapServiceGroup instance from a GroupDetail instance.

    Args:
        detail (GroupDetail): The GroupDetail instance to convert.
        administrators (set[str]): The set of administrator user IDs.

    Returns:
        MapGroup: The created MapServiceGroup instance.

    Raises:
        SystemAdminNotFound: If no administrators are found.
    """
    map_group, repository_id = validate_group_to_map_group(detail, mode="create")
    service_id = resolve_service_id(repository_id=repository_id)

    if not administrators:
        error = "At least one administrator is required to create a repository."
        raise SystemAdminNotFound(error)

    map_group.administrators = [
        GroupAdministrator(value=user_id) for user_id in administrators
    ]
    map_group.services = [
        GroupService(value=config.SP.connecter_id),
        GroupService(value=service_id),
    ]

    return map_group


def make_group_detail(group: MapGroup, *, more_detail: bool = False) -> GroupDetail:
    """Convert a MapGroup instance to a GroupDetail instance.

    Args:
        group (MapGroup): The MapGroup instance to convert.
        more_detail (bool): Whether to include more detailed information.

    Returns:
        GroupDetail: The created GroupDetail instance.
    """
    users, user_count = None, None
    if group.members:
        users = [member for member in group.members if member.type == "User"]
        user_count = len(users)

    detail = GroupDetail(
        id=group.id,
        display_name=group.display_name,
        description=group.description,
        public=group.public,
        member_list_visibility=group.member_list_visibility,
    )

    if group.members:
        users = [member for member in group.members if member.type == "User"]
        user_count = len(users)
        detail.users_count = user_count
        detail._users = [
            UserSummary(id=member.value, user_name=member.display) for member in users
        ]

    if group.administrators:
        detail._admins = [
            UserSummary(id=admin.value, user_name=admin.display)
            for admin in group.administrators
        ]

    if group.services:
        detail._services = [
            GroupService_(id=service.value, service_name=service.display)
            for service in group.services
        ]

    if group.meta:
        detail.created = group.meta.created
        detail.last_modified = group.meta.last_modified

    if not more_detail:
        return detail

    detected = detect_affiliation(t.cast("str", group.id))
    repository_id = detected.repository_id if detected else None
    detail.user_defined_id = (
        detected.user_defined_id if detected and detected.type == "group" else None
    )
    repository_id = detected.repository_id if detected else None
    if repository_id:
        from server.services import repositories  # noqa: PLC0415

        if repo := repositories.get_by_id(repository_id):
            detail.repository = GroupRepository(
                id=repository_id, service_name=repo.service_name
            )

    return detail


@t.overload
def validate_group_to_map_group(
    group: GroupDetail, *, mode: t.Literal["create"]
) -> tuple[MapGroup, str]: ...
@t.overload
def validate_group_to_map_group(
    group: GroupDetail, *, mode: t.Literal["update"]
) -> MapGroup: ...


def validate_group_to_map_group(  # noqa: C901
    group: GroupDetail, *, mode: t.Literal["create", "update"]
) -> tuple[MapGroup, str] | MapGroup:
    """Validate the GroupDetail instance and convert it to a MapGroup instance.

    Args:
        group (GroupDetail): The GroupDetail instance to convert.
        mode (Literal["create", "update"]):
            The mode of operation, either "create" or "update".

    Returns:
        tuple: The converted MapGroup instance and the repository ID associated with it.

    Raises:
        InvalidFormError: If the GroupDetail instance cannot be converted to a MapGroup.
    """
    if not group.display_name:
        error = "Display name is required to create a group."
        raise InvalidFormError(error)

    if mode == "update":
        if not group.id:
            error = "Group ID is required to update a group."
            raise InvalidFormError(error)

        return make_map_group(group)

    repository_id = group.repository.id if group.repository else None
    if not repository_id:
        error = "Repository ID is required to create a group."
        raise InvalidFormError(error)

    from server.services import repositories  # noqa: PLC0415

    if repositories.get_by_id(repository_id) is None:
        error = f"Repository with ID '{repository_id}' does not exist."
        raise InvalidFormError(error)

    user_defined_id = group.user_defined_id
    if not user_defined_id:
        error = "Group ID is required to create a group."
        raise InvalidFormError(error)

    if user_defined_id:
        max_id_length = config.GROUPS.max_id_length - len(repository_id)
        if len(user_defined_id) > max_id_length:
            error = "Group ID is too long."
            raise InvalidFormError(error)

        id_pattern = config.GROUPS.id_patterns.user_defined
        group.id = id_pattern.format(
            repository_id=repository_id, user_defined_id=user_defined_id
        )

    if group.public is None:
        group.public = GROUP_DEFAULT_PUBLIC
    if group.member_list_visibility is None:
        group.member_list_visibility = GROUP_DEFAULT_MEMBER_LIST_VISIBILITY

    return make_map_group(group), repository_id


def make_map_group(group: GroupDetail) -> MapGroup:
    """Convert a GroupDetail instance to a MapGroup instance.

    Args:
        group (GroupDetail): The GroupDetail instance to convert.

    Returns:
        MapGroup: The converted MapGroup instance.
    """
    map_group = MapGroup(
        id=group.id,
        display_name=group.display_name,
        public=group.public,
        description=group.description,
        member_list_visibility=group.member_list_visibility,
    )

    if group._users:
        map_group.members = [
            MemberUser(type="User", value=user.id, display=user.user_name)
            for user in group._users
        ]

    if group._admins:
        map_group.administrators = [
            GroupAdministrator(value=admin.id, display=admin.user_name)
            for admin in group._admins
        ]

    if group._services:
        map_group.services = [
            GroupService(value=service.id, display=service.service_name)
            for service in group._services
        ]

    return map_group
