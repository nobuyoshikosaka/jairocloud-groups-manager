import typing as t
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from pydantic.alias_generators import to_camel

from server.const import MAP_USER_SCHEMA


class MapUser(BaseModel):
    """Schema for a user resource in the mAP API.

    Handles validation and (de)serialization of user resources.
    """

    schemas: t.Annotated[t.Sequence[str], Field(frozen=True)] = [MAP_USER_SCHEMA]
    """Schema URIs that define the attributes present in the user resource."""

    id: str
    """Unique identifier for the user."""

    external_id: str | None = None
    """External identifier for the user. Alias for 'externalId'."""

    user_name: str
    """User's name. Alias for 'userName'."""

    preferred_language: t.Literal["en", "ja"] | None = None
    """User's preferred language. Alias for 'preferredLanguage'."""

    meta: Meta | None = None
    """Metadata for the user."""

    edu_person_principal_names: list[EPPN] | None = None
    """List of ePPN values associated with the user.
    Alias for 'eduPersonPrincipalNames'.
    """

    emails: list[Email] | None = None
    """List of email addresses associated with the user."""

    groups: list[Group] | None = None
    """List of groups the user belongs to."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
    """Base model configuration."""


class Meta(BaseModel):
    """Schema for user resource metadata."""

    resource_type: t.Annotated[t.Literal["User"], Field(frozen=True)] = "User"
    """Type of resource. Always 'User'. Alias for 'resourceType'."""

    created: datetime
    """Date and time when the resource was created."""

    last_modified: datetime
    """Date and time when the resource was last modified.
    Alias for 'lastModified'.
    """

    created_by: str | None
    """ID of the user who created this resource. Alias for 'createdBy'."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
    """Base model configuration."""


class EPPN(BaseModel):
    """Schema for an eduPersonPrincipalName (ePPN) value associated with a user."""

    value: str
    """eduPersonPrincipalName value."""

    idp_entity_id: str | None = None
    """Entity ID of the Identity Provider that issued this ePPN.
    Alias for 'idpEntityId'.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
    """Base model configuration."""


class Email(BaseModel):
    """Schema for an email address of a user."""

    value: EmailStr
    """Email address."""


class Group(BaseModel):
    """Schema for a group associated with a user."""

    value: str
    """Group ID."""

    ref: t.Annotated[
        HttpUrl | None,
        Field(
            ...,
            # NOTE: not using `alias` because it changes the constructor arguments.
            validation_alias="$ref",
            serialization_alias="$ref",
        ),
    ] = None
    """URI of the corresponding Group resource. Alias for '$ref'."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        validate_by_name=True,
        validate_by_alias=True,
    )
    """Base model configuration."""
