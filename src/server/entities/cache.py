#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Models for updating cache db entities."""

import typing as t

from datetime import datetime

from pydantic import BaseModel

from .common import camel_case_config, forbid_extra_config


class RepositoryCache(BaseModel):
    """Model for repository cache entity."""

    id: str
    """The unique identifier for the repository."""

    name: str
    """The name of the repository."""

    url: str
    """The URL of the repository."""

    updated: datetime | None = None
    """The update timestamp of the repository cache entry."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""


class TaskDetail(BaseModel):
    """Model for task detail entity."""

    results: list[Result]
    """The list of results from the task."""

    current: str
    """Identifier of the object currently being processed."""

    done: int
    """The number of completed items."""

    total: int
    """The total number of items to process."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""


type TaskStatus = t.Literal["success", "failed"]


class CacheResult(BaseModel):
    """Model for cache update result."""

    type: t.Literal["cache"]
    """The type of the result, always "cache"."""

    fqdn: str
    """The fully qualified domain name of the cached repository."""

    status: TaskStatus
    """The status of the cache update task."""

    code: str | None = None
    """The result code of the cache update task."""

    repository_cached: RepositoryCache | None = None
    """The cached repository information."""

    model_config = camel_case_config | forbid_extra_config
    """Configure to use camelCase aliasing and forbid extra fields."""


Result = CacheResult
