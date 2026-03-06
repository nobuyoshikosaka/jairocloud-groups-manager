#
# Copyright (C) 2025 National Institute of Informatics.
#
"""API router for cache group endpoints."""

from ast import literal_eval
from datetime import datetime

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from server.api.helper import roles_required
from server.api.schemas import CacheQuery, CacheRequest, RepositoriesQuery
from server.config import config
from server.datastore import app_cache
from server.entities.cache import CacheResult, RepositoryCache, TaskDetail
from server.entities.search_request import SearchResult
from server.services.cache_groups import get_repository_cache, update
from server.services.repositories import search


bp = Blueprint("cache-groups", __name__)


@bp.get("/")
@login_required
@roles_required("system_admin")
@validate(response_by_alias=True)
def get(query: CacheQuery) -> SearchResult[RepositoryCache]:
    """Retrieve repository cache entries based on the provided query.

    Args:
        query (CacheQuery): Query parameters for filtering and pagination.

    Returns:
        list[RepositoryCache]: List of repository cache entries.
    """
    repository_query = RepositoriesQuery(
        q=query.q,
        k="id",
        d="asc",
        p=query.p if not query.f else -1,
        l=query.l,
    )

    repositories = search(repository_query)

    return get_repository_cache(repositories, query)


@bp.post("/")
@login_required
@roles_required("system_admin")
@validate()
def post(body: CacheRequest) -> str:
    """Update cache groups for the specified FQDNs.

    Args:
        body (CacheRequest): Request body containing FQDNs and operation.

    Returns:
        str: Success message.
    """
    fqdn_list = body.fqdn_list or []
    update(fqdn_list, body.op)
    return "Success"


@bp.get("/task")
@login_required
@roles_required("system_admin")
@validate()
def get_task_status() -> TaskDetail:
    """Get the status of the cache update task.

    Returns:
        TaskDetail: Details of the cache update task.
    """
    cache_key = config.CACHE_GROUPS.cache_redis_key.format(
        prefix=config.REDIS.key_prefix
    )
    task_status = app_cache.hgetall(cache_key)
    decode_task_status = {k.decode(): v.decode() for k, v in task_status.items()}  # pyright: ignore[reportAttributeAccessIssue]
    results = {}
    current = ""
    done = 0
    total = 0
    for key in decode_task_status:  # noqa: PLC0206
        if key == "current":
            current = decode_task_status[key]  # pyright: ignore[reportIndexIssue]
        elif key == "done":
            done = int(decode_task_status[key])  # pyright: ignore[reportIndexIssue]
        elif key == "total":
            total = int(decode_task_status[key])  # pyright: ignore[reportIndexIssue]
        else:
            result = literal_eval(decode_task_status[key])  # pyright: ignore[reportIndexIssue]
            fqdn = key.split("_")[0]
            repository_query = RepositoriesQuery(
                q=f"/{fqdn}/",
                k="id",
                d="asc",
                p=-1,
                l=1,
            )
            repository = search(repository_query).resources[0]
            results[fqdn] = CacheResult(
                type="cache",
                fqdn=fqdn,
                status=result["status"],
                code=result.get("code"),
                repository_cached=RepositoryCache(
                    id=repository.id,
                    name=repository.display_name,  # pyright: ignore[reportArgumentType]
                    url=str(repository.service_url),
                    updated=datetime.strptime(  # noqa: DTZ007
                        result.get("updated"), "%Y-%m-%dT%H:%M:%SZ"
                    ),
                ),
            )
    if total > 0 and total == done:
        # Clear the task status when the task is completed.
        app_cache.delete(cache_key)

    return TaskDetail(
        results=list(results.values()), current=current, done=done, total=total
    )
