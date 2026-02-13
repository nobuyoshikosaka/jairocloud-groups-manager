#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Configuration for the server application.

Provides validation, loading, and global access to runtime configuration.
"""

# ruff: noqa: S105, N802

import typing as t

from datetime import timedelta

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

    SESSION: SessionConfig = Field(
        default_factory=lambda: SessionConfig(),  # noqa: PLW0108
    )
    """Session configuration."""

    API: ApiConfig = Field(
        default_factory=lambda: ApiConfig(),  # noqa: PLW0108
    )
    """API configuration."""

    STORAGE: StorageConfig = Field(
        default_factory=lambda: StorageConfig(),  # noqa: PLW0108
    )
    """Storage configuration."""

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

    DEVELOP: DevelopConfig | None = None

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
            dict: Configuration dictionary for Celery.
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

    @computed_field
    @property
    def PERMANENT_SESSION_LIFETIME(self) -> timedelta:
        """Duration (in seconds) for permanent sessions."""
        return timedelta(seconds=self.SESSION.absolute_lifetime)

    @computed_field
    @property
    def REMEMBER_COOKIE_DURATION(self) -> timedelta:
        """Duration (in seconds) for 'remember me' cookies."""
        match self.SESSION.strategy:
            case "absolute":
                lifetime = timedelta(seconds=self.SESSION.absolute_lifetime)
            case "sliding":
                lifetime = timedelta(seconds=self.SESSION.sliding_lifetime)

        return lifetime

    @computed_field
    @property
    def REMEMBER_COOKIE_REFRESH_EACH_REQUEST(self) -> bool:
        """Whether to refresh 'remember me' cookies on each request."""
        return self.SESSION.strategy == "sliding"

    @property
    def for_flask(self) -> dict[str, t.Any]:
        """Configuration dictionary suitable for Flask app.config.

        Returns:
            dict: Configuration dictionary for Flask.
        """
        return self.model_dump(
            include={
                "SERVER_NAME",
                "SECRET_KEY",
                "CELERY",
                "PERMANENT_SESSION_LIFETIME",
                "REMEMBER_COOKIE_DURATION",
                "REMEMBER_COOKIE_REFRESH_EACH_REQUEST",
            }
        ) | {
            "SQLALCHEMY_DATABASE_URI": self.SQLALCHEMY_DATABASE_URI,
            "SESSION_COOKIE_SECURE": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
        }

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


class SessionConfig(BaseModel):
    """Schema for session configuration."""

    strategy: t.Literal["absolute", "sliding"] = "sliding"
    """Strategy for session expiration."""

    sliding_lifetime: t.Annotated[int, "seconds"] = 1 * 60 * 60
    """Sliding session lifetime (in seconds)."""

    absolute_lifetime: t.Annotated[int, "seconds"] = 24 * 60 * 60
    """Absolute session lifetime (in seconds)."""


class ApiConfig(BaseModel):
    """Schema for API configuration."""

    max_upload_size: t.Annotated[int, "bytes"] = 10 * 1024**2
    """Maximum allowed file upload size (in bytes)."""


class StorageConfig(BaseModel):
    """Schema for storage configuration."""

    type: t.Literal["local"] = "local"
    """Type of storage backend to use."""

    local: LocalStorageConfig = Field(
        default_factory=lambda: LocalStorageConfig(),  # noqa: PLW0108
    )
    """Configuration for local storage backend."""


class LocalStorageConfig(BaseModel):
    """Schema for local storage configuration."""

    temporary: str = "/var/tmp/jcgroups"  # noqa: S108
    """Path to the temporary directory."""

    storage: str = "/data/jcgroups"
    """Path to the storage directory."""


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

    single: RedisSingleConfig = Field(
        default_factory=lambda: RedisSingleConfig(),  # noqa: PLW0108
    )
    """Configuration for single Redis server, when cache_type is "RedisCache"."""

    sentinel: RedisSentinelCacheConfig = Field(
        default_factory=lambda: RedisSentinelCacheConfig(),  # noqa: PLW0108
    )
    """Configuration for Redis Sentinel, when cache_type is "RedisSentinelCache"."""


class RedisDatabaseConfig(BaseModel):
    """Schema for Redis database configuration."""

    app_cache: int = 0
    """Database number for application cache."""

    account_store: int = 1
    """Database number for storing account information."""

    result_backend: int = 2
    """Database number for Celery result backend."""

    group_cache: int = 4
    """Database number for group informations cache.

    refer to https://github.com/RCOSDP/weko-group-cache-db
    """


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


class DevelopConfig(BaseModel):
    """Schema for development environment configuration."""

    developer_login: bool = False
    """Whether to enable developer login in development mode."""

    accounts: list[DevAccountConfig] = Field(default_factory=list)
    """List of development accounts."""


class DevAccountConfig(BaseModel):
    """Schema for development account configuration."""

    eppn: str
    """EPPN of the development account."""

    is_member_of: str
    """isMemberOf attribute of the development account."""

    user_name: str
    """User name of the development account."""


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


@LocalProxy
def _get_config() -> RuntimeConfig:
    return current_app.extensions["jairocloud-groups-manager"].config


config = t.cast("RuntimeConfig", _get_config)
"""The global server configuration instance."""

del _get_config
