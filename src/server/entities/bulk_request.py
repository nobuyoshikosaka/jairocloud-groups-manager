#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for schema and entity definition of mAP Core API Bulk resources."""

import typing as t

from pydantic import BaseModel, Field

from server.const import MAP_BULK_REQUEST_SCHEMA, MAP_BULK_RESPONSE_SCHEMA
from server.entities.map_error import MapError
from server.entities.map_group import MapGroup
from server.entities.map_service import MapService
from server.entities.map_user import MapUser
from server.entities.patch_request import PatchOperation

from .common import camel_case_config, forbid_extra_config


class BulkRequestPayload(BaseModel):
    """Bulk request entity in mAP API."""

    schemas: t.Annotated[t.Sequence[str], Field(frozen=True)] = [
        MAP_BULK_REQUEST_SCHEMA
    ]
    """Schema URIs that define the attributes present in the bulk resource."""

    operations: list[BulkOperation]
    """ bulk operations """

    fail_on_errors: int | None = None
    """ The number of errors allowed before returning an error response. """

    model_config = camel_case_config | forbid_extra_config
    """Configure camelCase aliasing and forbid extra fields."""


class BulkResponse(BaseModel):
    """Bulk request entity in mAP API."""

    schemas: t.Annotated[t.Sequence[str], Field(frozen=True)] = [
        MAP_BULK_RESPONSE_SCHEMA
    ]
    """Schema URIs that define the attributes present in the bulk resource."""

    operations: list[BulkOperation]
    """ bulk operations """

    model_config = camel_case_config | forbid_extra_config
    """Configure camelCase aliasing and forbid extra fields."""


class BulkOperation(BaseModel):
    """Handles a single HTTP request to the resource endpoint."""

    method: t.Literal["POST", "PUT", "PATCH", "DELETE"]
    """The HTTP method of the current operation."""

    bulk_id: str | None = None
    """REQUIRED when "method" is "POST". """

    path: str
    """The resource's relative path to the SCIM service provider's root."""

    data: MapService | MapGroup | MapUser | PatchOperation | None = None
    """Resource data used in a single operation."""

    location: str | None = None
    """The resource endpoint URL."""

    response: MapError | MapService | MapGroup | MapUser | None = None
    """The HTTP response body."""

    status: str | None = None
    """The HTTP response status code."""

    model_config = camel_case_config | forbid_extra_config
    """Configure camelCase aliasing and forbid extra fields."""
