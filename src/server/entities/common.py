#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides common configuration for resource schemas."""

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


camel_case_config = ConfigDict(
    validate_assignment=True,
    alias_generator=to_camel,
    validate_by_name=True,
    validate_by_alias=True,
)
"""Common configuration dict for camelCase aliasing.

- validate_assignment: True - Validates fields on assignment.
- alias_generator: to_camel - Converts field names to camelCase.
- validate_by_name: True - Validates fields using their Python names.
- validate_by_alias: True - Validates fields using their alias names.
"""


forbid_extra_config = ConfigDict(
    extra="forbid",
    validate_assignment=True,
)
"""Common configuration dict to forbid extra fields.

- extra: "forbid" - Forbids extra fields not defined in the model.
- validate_assignment: True - Validates fields on assignment.
"""
