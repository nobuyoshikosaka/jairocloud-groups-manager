#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Providers of decorators for client functions."""

# ruff: noqa: ANN001 ANN002 ANN003 ANN202 SLF001 D102

import hashlib
import inspect
import typing as t

from functools import wraps

from pydantic import BaseModel, TypeAdapter

from server.config import config
from server.datastore import datastore
from server.entities.map_error import MapError


@t.overload
def cache_resource[T: ModelReturner](f: T) -> T: ...
@t.overload
def cache_resource[T: ModelReturner](
    *, timeout: int | None = None
) -> t.Callable[[T], T]: ...


def cache_resource[T: t.Callable](
    f: T | None = None, *, timeout: int | None = None
) -> T | t.Callable:
    """Cache the response of the API client function using Redis.

    Args:
        f (Callable | None): The function to decorate.
        timeout (int):
            Timeout for the cache entry in seconds, overrides the default from config.

    Returns:
        Callable: Decorated function with caching.
    """
    prefix = config.REDIS.key_prefix
    timeout = timeout or config.REDIS.default_timeout

    def decorator(func):

        hints = t.get_type_hints(func)
        return_type: type[BaseModel] | None = hints.get("return")
        original_func = inspect.unwrap(func)
        import_name = f"{original_func.__module__}.{original_func.__qualname__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not args:
                return func(*args, **kwargs)
            identifier = str(args[0])

            relevant_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k not in {"access_token", "client_secret"}
            }

            hash_input = f"{args[1:]}-{sorted(str(relevant_kwargs.items()))}"
            args_hash = hashlib.md5(
                hash_input.encode(), usedforsecurity=False
            ).hexdigest()

            cache_key = f"{prefix}:{import_name}:{identifier}:{args_hash}"

            cached_data: str | None = datastore.get(cache_key)  # pyright: ignore[reportAssignmentType]
            if cached_data and return_type:
                adapter = TypeAdapter(return_type)
                return adapter.validate_json(cached_data)

            result = func(*args, **kwargs)

            nonlocal timeout
            if isinstance(result, MapError) or timeout is None:
                timeout = 3

            datastore.setex(cache_key, timeout, result.model_dump_json())
            return result

        wrapper._import_name = import_name  # pyright: ignore[reportAttributeAccessIssue]
        wrapper.clear_cache = lambda *resource_id: clear_cache(  # pyright: ignore[reportAttributeAccessIssue]
            wrapper, *resource_id
        )
        return wrapper

    if f is not None:
        return decorator(f)

    return decorator


def clear_cache(func: t.Callable, *resource_id: str) -> None:
    """Delete cached responses for the given function and resource id.

    Args:
        func (Callable): The decorated function whose cache to delete.
        resource_id (str): The resource id to delete cache for.

    Raises:
        ValueError: If the function is not decorated with @response_cache.
    """
    prefix = config.REDIS.key_prefix
    import_name = getattr(func, "_import_name", None)
    if not import_name:
        error = "Function is not decorated with @response_cache."
        raise ValueError(error)

    for rid in resource_id:
        match = f"{prefix}:{import_name}:{rid}:*"

        cursor = "0"
        while cursor != 0:
            cursor, keys = datastore.scan(  # pyright: ignore[reportGeneralTypeIssues]
                cursor=cursor,  # pyright: ignore[reportArgumentType]
                match=match,
                count=100,
            )
            if keys:
                datastore.delete(*keys)


class ModelReturner(t.Protocol):
    """Base model for return types of decorated functions."""

    def __call__(self, *args, **kwds) -> BaseModel: ...
