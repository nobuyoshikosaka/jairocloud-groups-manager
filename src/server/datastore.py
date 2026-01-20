#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Redis connection module for weko-group-cache-db."""

from flask import current_app
from redis import Redis, sentinel
from redis.exceptions import ConnectionError as RedisConnectionError

from .config import config
from .exc import ConfigurationError, DatastoreError


def connection() -> Redis:
    """Establish Redis connection.

    Returns:
        Redis: Redis store object.

    Raises:
        ConfigurationError: If configuration for Redis is invalid.
        DatastoreError: If failed to connect to Redis.

    """
    try:
        if config.REDIS.cache_type == "RedisCache":
            store = _redis_connection()
            store.ping()
        else:
            store = _sentinel_connection()
            store.ping()
    except ValueError as exc:
        error = "Failed to connect to Redis. Invalid configuration."
        current_app.logger.error(error)
        raise ConfigurationError(error) from exc
    except RedisConnectionError as exc:
        error = "Failed to connect to Redis."
        current_app.logger.error(error)
        raise DatastoreError(error) from exc

    return store


def _redis_connection() -> Redis:
    """Establish Redis connection and return Redis store object.

    Returns:
    Redis: Redis store object.

    """
    redis_url = config.REDIS.single.base_url
    return Redis.from_url(redis_url)


def _sentinel_connection() -> Redis:
    """Establish Redis sentinel connection.

    Returns:
        Redis: Redis store object

    """
    sentinels = sentinel.Sentinel(
        [(node.host, node.port) for node in config.REDIS.sentinel.sentinels],
        decode_responses=False,
    )
    return sentinels.master_for(
        config.REDIS.sentinel.master_name, db=config.REDIS.database.app_cache
    )


datastore = connection()
