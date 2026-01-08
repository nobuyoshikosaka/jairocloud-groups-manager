#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for Repository entity for client side."""

import typing as t

from pydantic import BaseModel, Field, HttpUrl, PrivateAttr

from server.config import config

from .common import camel_case_config, forbid_extra_config
from .map_service import MapService, ServiceEntityID
from .summaries import UserSummary


class RepositoryDetail(BaseModel):
    """Model for detailed Repository information in mAP Core API."""

    _fqdn: str | None = PrivateAttr(None)
    """The fully qualified domain name of the repository."""

    id: str
    """The unique identifier for the repository."""

    display_name: str
    """The name of the repository. Alias to 'displayName'."""

    service_url: HttpUrl | None = None
    """The URL of the service. Alias for 'serviceUrl'."""

    suspended: bool | None = None
    """Whether the service is suspended."""

    service_id: t.Annotated[
        str | None,
        Field(
            validation_alias="spConnecterId",
            serialization_alias="spConnecterId",
        ),
    ] = None
    """The ID of the corresponding resource. Alias to 'spConnecterId'."""

    entity_ids: list[str] | None = None
    """The entity IDs associated with the repository. Alias to 'entityID'."""

    _users: list[UserSummary] | None = PrivateAttr(None)
    """The users in the repository."""

    users_count: int | None = None
    """The number of users in the group. Alias to 'usersCount'."""

    groups_count: int | None = None
    """The number of groups in the repository. Alias to 'groupsCount'."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""

    @classmethod
    def from_map_service(cls, service: MapService) -> RepositoryDetail:
        """Create a RepositoryDetail instance from a MapService instance.

        Args:
            service (MapService): The MapService instance to convert.

        Returns:
            RepositoryDetail: The created RepositoryDetail instance.
        """
        return cls(
            id=resolve_repository_id(service_id=service.id),
            display_name=service.service_name or "",
            service_url=service.service_url,
            suspended=service.suspended,
            service_id=service.id,
            entity_ids=[eid.value for eid in service.entity_ids]
            if service.entity_ids
            else [],
        )

    def to_map_service(self) -> MapService:
        """Convert RepositoryDetail to MapService instance.

        Returns:
            MapService: The converted MapService instance.
        """
        service = MapService(id=resolve_service_id(repository_id=self.id))
        service.service_name = self.display_name
        service.service_url = self.service_url
        if self.suspended is not None:
            service.suspended = self.suspended
        if self.entity_ids:
            service.entity_ids = [ServiceEntityID(value=eid) for eid in self.entity_ids]
        return service


@t.overload
def resolve_repository_id(*, fqdn: str) -> str: ...
@t.overload
def resolve_repository_id(*, service_id: str) -> str: ...


def resolve_repository_id(
    *, fqdn: str | None = None, service_id: str | None = None
) -> str:
    """Resolve the repository ID from either FQDN or service ID.

    Args:
        fqdn (str): The fully qualified domain name.
        service_id (str): The service ID.

    Returns:
        str: The corresponding repository ID.

    Raises:
        ValueError: If neither `fqdn` nor `resource_id` is provided.
    """
    pattern = config.RESOURCES.sp_connecter_id_pattern
    prefix = pattern.split("{repository_id}")[0]
    suffix = pattern.split("{repository_id}")[1]

    if fqdn is not None:
        return fqdn.replace(".", "_").replace("-", "_")
    if service_id is not None:
        return service_id.removeprefix(prefix).removesuffix(suffix)

    error = "Either 'fqdn' or 'resource_id' must be provided."
    raise ValueError(error)


@t.overload
def resolve_service_id(*, fqdn: str) -> str: ...
@t.overload
def resolve_service_id(*, repository_id: str) -> str: ...


def resolve_service_id(
    *, fqdn: str | None = None, repository_id: str | None = None
) -> str:
    """Resolve the service ID from either FQDN or repository ID.

    Args:
        repository_id (str): The repository ID.
        fqdn (str): The fully qualified domain name.

    Returns:
        str: The corresponding service ID.

    Raises:
        ValueError: If neither `fqdn` nor `repository_id` is provided.
    """
    pattern = config.RESOURCES.sp_connecter_id_pattern

    if fqdn is not None:
        repository_id = resolve_repository_id(fqdn=fqdn)
    if repository_id is not None:
        return pattern.format(repository_id=repository_id)

    error = "Either 'fqdn' or 'repository_id' must be provided."
    raise ValueError(error)
