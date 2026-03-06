#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Service module for managing cache groups."""

import typing as t

from datetime import datetime

from celery import shared_task
from weko_group_cache_db.groups import fetch_all, fetch_one
from weko_group_cache_db.signals import update_count_signal, update_result_signal

from server.api.schemas import CacheOperation, CacheQuery
from server.config import config
from server.datastore import app_cache, group_cache
from server.entities.cache import RepositoryCache
from server.entities.search_request import SearchResult


if t.TYPE_CHECKING:
    from server.entities.summaries import RepositorySummary


def get_repository_cache(
    repositories: SearchResult[RepositorySummary], query: CacheQuery
) -> SearchResult[RepositoryCache]:
    """Retrieve repository cache entries based on the provided query.

    Args:
        repositories (SearchResult[RepositorySummary]): List of repository summaries.
        query (CacheQuery): Query parameters for filtering and pagination.

    Returns:
        SearchResult[RepositoryCache]: List of repository cache entries.
    """

    def _get_repository_redis_key(fqdn: str) -> str:
        replaced_fqdn = fqdn.replace("-", "_").replace(".", "_")
        return config.CACHE_GROUPS.gakunin_redis_key.format(fqdn=replaced_fqdn)

    repository_cache_list = []
    cursor = 0
    redis_key_list = []
    while True:
        cursor, keys = group_cache.scan(
            cursor=cursor,
            match=config.CACHE_GROUPS.gakunin_redis_key.format(fqdn="*"),
            count=100,
        )  # pyright: ignore[reportGeneralTypeIssues]
        redis_key_list.extend([key.decode("utf-8") for key in keys])
        if cursor == 0:
            break

    # filter by cache existence
    if query.f:
        target_repositories = []
        start_index = (query.p - 1) * query.l if query.p and query.l else 0
        end_index = start_index + query.l if query.l else len(repositories.resources)

        for repository in repositories.resources:
            repository_redis_key = _get_repository_redis_key(
                repository.service_url.host  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
            )
            repository_updated = None
            if repository_redis_key in redis_key_list:
                repository_updated = group_cache.hget(
                    repository_redis_key, "updated_at"
                )

                repo_cache = RepositoryCache(
                    id=repository.id,
                    name=repository.display_name,  # pyright: ignore[reportArgumentType],
                    url=str(repository.service_url),
                    updated=datetime.fromisoformat(repository_updated),  # pyright: ignore[reportArgumentType]
                )
                if "cache" in query.f:
                    target_repositories.append(repo_cache)
            else:
                repo_cache = RepositoryCache(
                    id=repository.id,
                    name=repository.display_name,  # pyright: ignore[reportArgumentType],
                    url=str(repository.service_url),
                    updated=None,
                )
                if "no_cache" in query.f:
                    target_repositories.append(repo_cache)
        return SearchResult(
            resources=target_repositories[start_index:end_index],
            total=len(target_repositories),
            page_size=query.l or len(target_repositories),
            offset=start_index + 1,
        )
    repository_cache_list = []
    for repository in repositories.resources:
        repository_redis_key = _get_repository_redis_key(
            repository.service_url.host  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]
        )
        repository_updated = None
        if repository_redis_key in redis_key_list:
            repository_updated = group_cache.hget(repository_redis_key, "updated_at")

        repo_cache = RepositoryCache(
            id=repository.id,
            name=repository.display_name,  # pyright: ignore[reportArgumentType],
            url=str(repository.service_url),
            updated=datetime.fromisoformat(repository_updated)  # pyright: ignore[reportArgumentType]
            if repository_updated
            else None,
        )
        repository_cache_list.append(repo_cache)

    return SearchResult(
        resources=repository_cache_list,
        total=repositories.total,
        page_size=query.l or repositories.page_size,
        offset=(query.p - 1) * query.l + 1 if query.p and query.l else 1,
    )


def update(fqdn_list: list[str], op: CacheOperation) -> None:
    """Update cache groups based on the operation type.

    Args:
        fqdn_list (list[str]): List of fully qualified domain names.
        op (CacheOperation): Operation type, either 'all' or 'id-specified'.

    Raises:
        RuntimeError: If a cache update task is already running.
    """
    if check_updating_cache_is_running():
        err = "A cache update task is already running."
        raise RuntimeError(err)

    update_task.apply_async(fqdn_list, op)  # pyright: ignore[reportArgumentType]


@shared_task()
def update_task(fqdn_list: list[str], op: CacheOperation) -> None:
    """Celery task to update cache groups.

    Args:
        fqdn_list (list[str]): List of fully qualified domain names.
        op (CacheOperation): Operation type, either 'all' or 'id-specified'.
    """

    def _receive_update_count(_: object, **kwargs: dict[str, t.Any]) -> None:
        """Receive update count signal and update task status in Redis.

        Args:
            _: The sender of the signal.
            **kwargs: Additional keyword arguments containing task details.
        """
        update_dict = {
            "total": kwargs.get("total", 0),
            "done": kwargs.get("done", 0),
            "current": kwargs.get("current", ""),
        }
        app_cache.hset(cache_key, mapping=update_dict)

    def _receive_update_result(_: object, **kwargs: dict[str, t.Any]) -> None:
        """Receive update result signal and update task result in Redis.

        Args:
            _: The sender of the signal.
            **kwargs: Additional keyword arguments containing task details.
        """
        task_result = {
            "status": kwargs.get("status", ""),
            "code": kwargs.get("code", ""),
            "updated": kwargs.get("updated", ""),
        }
        update_dict = {str(kwargs.get("task_name", "")): str(task_result)}
        app_cache.hset(cache_key, mapping=update_dict)

    cache_key = config.CACHE_GROUPS.cache_redis_key.format(
        prefix=config.REDIS.key_prefix
    )

    update_count_signal.connect(_receive_update_count)
    update_result_signal.connect(_receive_update_result)

    if op == "all":
        update_run_task()
    else:
        update_one_task(fqdn_list)


def update_run_task() -> None:
    """Task to update all cache groups."""
    cache_key = config.CACHE_GROUPS.cache_redis_key.format(
        prefix=config.REDIS.key_prefix
    )
    run_task_init_data = {"total": "", "done": 0, "current": ""}
    app_cache.hset(cache_key, mapping=run_task_init_data)
    if config.CACHE_GROUPS.toml_path:
        fetch_all(toml_path=config.CACHE_GROUPS.toml_path)
    else:
        fetch_all(
            directory_path=config.CACHE_GROUPS.directory_path,
            fqdn_list_file=config.CACHE_GROUPS.fqdn_list_file,
        )


def update_one_task(fqdn_list: list[str]) -> None:
    """Task to update cache groups for specified FQDNs.

    Args:
        fqdn_list (list[str]): List of fully qualified domain names to update.
    """
    cache_key = config.CACHE_GROUPS.cache_redis_key.format(
        prefix=config.REDIS.key_prefix
    )
    one_task_init_data = {"total": len(fqdn_list), "done": 0, "current": ""}
    app_cache.hset(cache_key, mapping=one_task_init_data)
    for i, fqdn in enumerate(fqdn_list):
        if config.CACHE_GROUPS.toml_path:
            fetch_one(fqdn, toml_path=config.CACHE_GROUPS.toml_path)
        else:
            fetch_one(
                fqdn,
                directory_path=config.CACHE_GROUPS.directory_path,
                fqdn_list_file=config.CACHE_GROUPS.fqdn_list_file,
            )
        task_result = {
            "done": i + 1,
            "current": fqdn,
        }
        app_cache.hset(cache_key, mapping=task_result)


def check_updating_cache_is_running() -> bool:
    """Check if a cache update task is currently running.

    Returns:
        bool: True if a cache update task is running, False otherwise.
    """
    cache_key = config.CACHE_GROUPS.cache_redis_key.format(
        prefix=config.REDIS.key_prefix
    )
    return bool(app_cache.exists(cache_key))
