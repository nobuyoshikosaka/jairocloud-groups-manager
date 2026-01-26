#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for Bulk entity for client side."""

import typing as t

from datetime import datetime
from functools import cached_property
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from server.entities.bulk_request import BulkOperation


class RepositoryMember(BaseModel):
    """Model for members of a repository."""

    groups: set[str]
    """The groups belonging to the repository."""

    users: set[str]
    """The users belonging to the repository."""


class ValidateSummary(BaseModel):
    """Model for summary of bulk validation result."""

    check_result: list[CheckResult]
    """The list of validation results for each user."""

    @computed_field
    @cached_property
    def create(self) -> int:
        """The number of users created."""
        return sum(1 for r in self.check_result if r.status == "create")

    @computed_field
    @cached_property
    def update(self) -> int:
        """The number of users updated."""
        return sum(1 for r in self.check_result if r.status == "update")

    @computed_field
    @cached_property
    def delete(self) -> int:
        """The number of users deleted."""
        return sum(1 for r in self.check_result if r.status == "delete")

    @computed_field
    @cached_property
    def skip(self) -> int:
        """The number of users skipped."""
        return sum(1 for r in self.check_result if r.status == "skip")

    @computed_field
    @cached_property
    def error(self) -> int:
        """The number of errors."""
        return sum(1 for r in self.check_result if r.status == "error")


class CheckResult(BaseModel):
    """Model for result of validation check for each user."""

    user_id: str
    """The unique identifier for the user."""

    eppn: list[str]
    """The eduPersonPrincipalNames of the user."""

    user_name: str
    """The username of the user."""

    groups: list[str]
    """The groups of the user."""

    bulk_operation: BulkOperation | None = Field(exclude=True)
    """The bulk operation to be performed for the user."""

    status: t.Literal["create", "update", "delete", "skip", "error"]
    """The status of the validation check."""

    code: str | None
    """The code representing the result of the validation check."""


class ResultSummary(BaseModel):
    """Model for summary of bulk upload result."""

    upload_result: list[CheckResult]
    """The list of upload results for each user."""

    create: int
    """The number of users created."""

    update: int
    """The number of users updated."""

    delete: int
    """The number of users deleted."""

    skip: int
    """The number of users skipped."""

    error: int
    """The number of errors."""

    file_id: UUID
    """The ID of the uploaded file."""

    file_name: str
    """The name of the uploaded file."""

    operator: str
    """The operator who performed the upload."""

    start_timestamp: datetime
    """The timestamp when the upload started."""

    end_timestamp: datetime
    """The timestamp when the upload ended."""
