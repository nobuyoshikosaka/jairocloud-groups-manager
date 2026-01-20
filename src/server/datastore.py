#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Redis connection module for weko-group-cache-db."""

import typing as t

from flask import Flask, current_app
from redis import Redis, sentinel
from redis.exceptions import ConnectionError as RedisConnectionError
from werkzeug.local import LocalProxy

from .config import config as config_
from .exc import ConfigurationError, DatastoreError


if t.TYPE_CHECKING:
    from .config import RuntimeConfig


def setup_datastore(app: Flask, config: RuntimeConfig) -> dict[int, Redis]:
    """Setup Redis datastore connections for the application.

    Args:
        app (Flask): The Flask application instance.
        config (RuntimeConfig): The runtime configuration instance.

    Returns:
        dict: Dictionary of Redis connections.
    """
    return {
        db: connection(app, db=db, config=config)
        for db in (
            config.REDIS.database.app_cache,
            config.REDIS.database.account_store,
        )
    }


def connection(
    app: Flask | None = None, *, db: int, config: RuntimeConfig | None = None
) -> Redis:
    """Establish Redis connection.

    Args:
        app (Flask): The Flask application instance, or None to use current_app.
        db (int): Database number.
        config (RuntimeConfig): The runtime configuration instance.

    Returns:
        Redis: Redis store object.

    Raises:
        ConfigurationError: If configuration for Redis is invalid.
        DatastoreError: If failed to connect to Redis.

    """
    app = app or current_app
    config = config or config_
    try:
        if config.REDIS.cache_type == "RedisCache":
            base_url = config.REDIS.single.base_url.rstrip("/")
            store = Redis.from_url(f"{base_url}/{db}")
            store.ping()
            app.logger.info("Successfully connected to Redis.")
        else:
            sentinels = sentinel.Sentinel(
                [(node.host, node.port) for node in config.REDIS.sentinel.sentinels],
                decode_responses=False,
            )
            store = sentinels.master_for(config.REDIS.sentinel.master_name, db=db)
            store.ping()
            app.logger.info("Successfully connected to Redis Sentinel.")
    except ValueError as exc:
        error = "Failed to connect to Redis. Invalid configuration."
        app.logger.error(error)
        raise ConfigurationError(error) from exc
    except RedisConnectionError as exc:
        error = "Failed to connect to Redis."
        app.logger.error(error)
        raise DatastoreError(error) from exc

    return store


@LocalProxy
def _get_datastore() -> Redis:
    from server.config import config  # noqa: PLC0415

    ext = current_app.extensions["jairocloud-groups-manager"]
    return ext.datastore[config.REDIS.database.app_cache]


@LocalProxy
def _get_account_store() -> Redis:
    from server.config import config  # noqa: PLC0415

    ext = current_app.extensions["jairocloud-groups-manager"]
    return ext.datastore[config.REDIS.database.account_store]


datastore = t.cast("Redis", _get_datastore)
"""Redis datastore connection for application cache."""

account_store = t.cast("Redis", _get_account_store)
"""Redis datastore connection for storing account information."""

del _get_datastore, _get_account_store
