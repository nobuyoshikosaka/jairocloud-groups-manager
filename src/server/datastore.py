#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Redis connection module for weko-group-cache-db."""

from flask import current_app
from redis import Redis, sentinel
from redis.exceptions import ConnectionError as RedisConnectionError

from .config import config
from .exc import ConfigurationError, DatastoreError


def connection(db: int) -> Redis:
    """Establish Redis connection.

    Args:
        db (int): Database number.

    Returns:
        Redis: Redis store object.

    Raises:
        ConfigurationError: If configuration for Redis is invalid.
        DatastoreError: If failed to connect to Redis.

    """
    try:
        if config.REDIS.cache_type == "RedisCache":
            store = _redis_connection(db)
            store.ping()
            current_app.logger.info("Successfully connected to Redis.")
        else:
            store = _sentinel_connection(db)
            store.ping()
            current_app.logger.info("Successfully connected to Redis Sentinel.")
    except ValueError as exc:
        error = "Failed to connect to Redis. Invalid configuration."
        current_app.logger.error(error)
        raise ConfigurationError(error) from exc
    except RedisConnectionError as exc:
        error = "Failed to connect to Redis."
        current_app.logger.error(error)
        raise DatastoreError(error) from exc

    return store


def _redis_connection(db: int) -> Redis:
    """Establish Redis connection and return Redis store object.

    Args:
        db (int): Database number.

    Returns:
    Redis: Redis store object.

    """
    base_url = config.REDIS.single.base_url.rstrip("/")
    return Redis.from_url(f"{base_url}/{db}")


def _sentinel_connection(db: int) -> Redis:
    """Establish Redis sentinel connection.

    Args:
        db (int): Database number.

    Returns:
        Redis: Redis store object

    """
    sentinels = sentinel.Sentinel(
        [(node.host, node.port) for node in config.REDIS.sentinel.sentinels],
        decode_responses=False,
    )
    return sentinels.master_for(config.REDIS.sentinel.master_name, db=db)


datastore = connection(config.REDIS.database.app_cache)
"""Redis datastore connection for application cache."""

account_store = connection(config.REDIS.database.account_store)
"""Redis datastore connection for storing account information."""
