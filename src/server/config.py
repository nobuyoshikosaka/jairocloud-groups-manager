#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Configuration for the server application.

Provides validation, loading, and global access to runtime configuration.
"""

# ruff: noqa: S105, N802

import typing as t

from flask import current_app
from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    computed_field,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from sqlalchemy.engine import URL, make_url
from werkzeug.local import LocalProxy

from .const import HAS_REPO_ID_AND_USER_DEFINED_ID_PATTERN, HAS_REPO_ID_PATTERN


class RuntimeConfig(BaseSettings):
    """Schema for runtime configuration.

    Handles validation and loading of runtime config values.
    """

    SERVER_NAME: str = "localhost"
    """Server hostname of this application."""

    SECRET_KEY: str = "CHANGE ME"
    """Secret key for cryptographic operations."""

    LOG: LogConfig
    """Logging configuration."""

    MAP_CORE: MapCoreConfig
    """mAP Core service configuration."""

    SP: SpConfig
    """This application's Service Provider configuration."""

    REPOSITORIES: RepositoriesConfig
    """Repository related configuration values."""

    GROUPS: GroupsConfig
    """Group related configuration values."""

    POSTGRES: PostgresConfig = Field(
        default_factory=lambda: PostgresConfig(),  # noqa: PLW0108
        exclude=True,
    )
    """PostgreSQL database configuration values."""

    REDIS: RedisConfig
    """Redis cache configuration values."""

    RABBITMQ: RabbitmqConfig
    """RabbitMQ configuration values."""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> URL:
        """Database connection URI for SQLAlchemy."""
        pg = self.POSTGRES
        return make_url(
            f"postgresql+psycopg://{pg.user}:{pg.password}@{pg.host}:{pg.port}/{pg.db}"
        )

    @computed_field
    @property
    def CELERY(self) -> dict[str, t.Any]:
        """Celery configuration dictionary.

        Returns:
            dict[str, Any]: Configuration dictionary for Celery.
        """
        cache_type = self.REDIS.cache_type
        database = self.REDIS.database.result_backend
        config: dict[str, t.Any] = {"broker_url": self.RABBITMQ.url}

        if cache_type == "RedisCache" and self.REDIS.single:
            base_url = self.REDIS.single.base_url.rstrip("/")
            config["result_backend"] = f"{base_url}/{database}"

        elif cache_type == "RedisSentinelCache" and self.REDIS.sentinel:
            sentinels = [
                f"sentinel://{node.host}:{node.port}"
                for node in self.REDIS.sentinel.sentinels
            ]
            master_name = self.REDIS.sentinel.master_name
            config["result_backend"] = f"{';'.join(sentinels)}/{database}"
            config["result_backend_transport_options"] = {"master_name": master_name}

        return config

    @t.override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        origin = super().settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

        toml_file: str | None = init_settings().pop("_toml_file", None)
        if toml_file is None:
            return origin

        toml_settings = TomlConfigSettingsSource(cls, toml_file)
        return (*origin, toml_settings)

    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        alias_generator=lambda s: s.lower(),
        validate_default=True,
        validate_by_name=True,
    )
    """Base model configuration."""


class LogConfig(BaseModel):
    """Schema for logging configuration."""

    level: t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    """Log level for the application standard output."""

    format: str | None = None
    """Log format string for log messages.
    If not provided, default formats will be used.
    """

    datefmt: str | None = None
    """Date format string for log timestamps.
    If not provided, the default format will be used.
    """


class SpConfig(BaseModel):
    """Schema for Service Provider configuration."""

    entity_id: str
    """Entity ID of the Service Provider."""

    crt: str
    """Path to the Service Provider's certificate file."""

    key: str
    """Path to the Service Provider's private key file."""


class RepositoriesConfig(BaseModel):
    """Schema for repository related configuration."""

    id_patterns: RepositoriesIdPatternsConfig
    """Patterns for repository-related IDs."""


class RepositoriesIdPatternsConfig(BaseModel):
    """Schema for repository-related ID patterns."""

    sp_connecter: HasRepoId
    """SP Connecter ID pattern. It should include `{repository_id}` placeholder."""


class GroupsConfig(BaseModel):
    """Schema for Group resource ID configuration."""

    id_patterns: GroupIdPatternsConfig
    """Patterns for Group resource IDs."""


class GroupIdPatternsConfig(BaseModel):
    """Schema for Group resource ID patterns."""

    system_admin: str
    """ID of the system administrator group."""

    repository_admin: HasRepoId
    """Pattern for repository administrator group IDs."""

    community_admin: HasRepoId
    """Pattern for community administrator group IDs."""

    contributor: HasRepoId
    """Pattern for contributor group IDs."""

    general_user: HasRepoId
    """Pattern for general user group IDs."""

    user_defined: HasRepoAndUserDefinedId
    """Pattern for user-defined group IDs."""


class MapCoreConfig(BaseModel):
    """Schema for mAP Core service configuration."""

    base_url: str
    """Base URL of the mAP Core service."""

    timeout: t.Annotated[int, "seconds"] = 10
    """Timeout (in seconds) for requests to mAP Core service."""


class PostgresConfig(BaseModel):
    """Schema for PostgreSQL database configuration."""

    user: str = "jcgroups"
    """Database user name for authentication."""

    password: str = "jcpass"
    """Database user password for authentication."""

    host: str = "localhost"
    """Host name or IP address of the PostgreSQL server."""

    port: int = 5432
    """Port number for the PostgreSQL server."""

    db: str = "jcgroups"
    """Name of the PostgreSQL database."""


class RedisConfig(BaseModel):
    """Schema for Redis cache configuration."""

    cache_type: t.Literal["RedisCache", "RedisSentinelCache"] = "RedisCache"
    """Type of cache backend to use.

    Possible values are 'RedisCache' and 'RedisSentinelCache'.
    """

    default_timeout: t.Annotated[int, "seconds"] = 300
    """Default timeout (in seconds) for cached items."""

    key_prefix: str = "jcgroups_"
    """Prefix for cache keys used by the application."""

    database: RedisDatabaseConfig = Field(
        default_factory=lambda: RedisDatabaseConfig(),  # noqa: PLW0108
    )

    single: RedisSingleConfig
    """Configuration for single Redis server, when cache_type is "RedisCache"."""

    sentinel: RedisSentinelCacheConfig
    """Configuration for Redis Sentinel, when cache_type is "RedisSentinelCache"."""


class RedisDatabaseConfig(BaseModel):
    """Schema for Redis database configuration."""

    app_cache: int = 0
    """Database number for application cache."""

    account_store: int = 1
    """Database number for storing account information."""

    result_backend: int = 2
    """Database number for Celery result backend."""


class RedisSingleConfig(BaseModel):
    """Schema for single Redis server configuration."""

    base_url: str = "redis://localhost:6379"


class RedisSentinelCacheConfig(BaseModel):
    """Schema for Redis Sentinel configuration."""

    master_name: str = "mymaster"
    """Name of the Redis Sentinel master node."""

    sentinels: list[SentinelNodeConfig] = Field(default_factory=list)


class SentinelNodeConfig(BaseModel):
    """Schema for Redis Sentinel node configuration."""

    host: str
    """Hostname or IP address of the Sentinel node."""

    port: int
    """Port number of the Sentinel node."""


class RabbitmqConfig(BaseModel):
    """Schema for RabbitMQ configuration."""

    url: str = "amqp://guest:guest@localhost:5672//"
    """Hostname or IP address of the RabbitMQ server for Celery broker."""


type HasRepoId = t.Annotated[str, StringConstraints(pattern=HAS_REPO_ID_PATTERN)]
"""Pattern for role-based group IDs.

It should include `{repository_id}` placeholder.
"""


type HasRepoAndUserDefinedId = t.Annotated[
    str, StringConstraints(pattern=HAS_REPO_ID_AND_USER_DEFINED_ID_PATTERN)
]
"""Pattern for custom group IDs.

It should include `{repository_id}` followed by `{user_defined_id}` placeholders.
"""


def setup_config(path_or_obj: str | RuntimeConfig) -> RuntimeConfig:
    """Initialize and set the global server configuration instance.

    Args:
        path_or_obj (str | RuntimeConfig): Path to the TOML config file or a
            RuntimeConfig instance to use.

    Returns:
        RuntimeConfig: The initialized config instance.

    """
    if isinstance(path_or_obj, str):
        path_or_obj = RuntimeConfig(_toml_file=path_or_obj)  # pyright: ignore[reportCallIssue]

    return path_or_obj


config = t.cast(
    "RuntimeConfig",
    LocalProxy(lambda: current_app.extensions["jairocloud-groups-manager"].config),
)
"""The global server configuration instance."""
