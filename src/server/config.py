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


class RuntimeConfig(BaseSettings):
    """Schema for runtime configuration.

    Handles validation and loading of runtime config values.
    """

    SERVER_NAME: str = "localhost"
    """Server hostname of this application."""

    SECRET_KEY: str = "CHANGE ME"
    """Secret key for cryptographic operations."""

    MAP_CORE: MapCoreConfig
    """mAP Core service configuration."""

    SP: SpConfig
    """This application's Service Provider configuration."""

    REPOSITORIES: RepositoriesConfig
    """Repository related configuration values."""

    GROUPS: GroupsConfig
    """Group related configuration values."""

    CELERY: CeleryConfig = Field(default_factory=lambda: CeleryConfig())  # noqa: PLW0108
    """Celery configuration values."""

    POSTGRES: PostgresConfig = Field(
        default_factory=lambda: PostgresConfig(),  # noqa: PLW0108
        exclude=True,
    )
    """PostgreSQL database configuration values."""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> URL:
        """Database connection URI for SQLAlchemy."""
        pg = self.POSTGRES
        return make_url(
            f"postgresql+psycopg://{pg.user}:{pg.password}@{pg.host}:{pg.port}/{pg.db}"
        )

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

    custom_group: HasRepoAndCustomId
    """Pattern for custom group IDs."""


class MapCoreConfig(BaseModel):
    """Schema for mAP Core service configuration."""

    base_url: str
    """Base URL of the mAP Core service."""

    timeout: t.Annotated[int, "seconds"] = 10
    """Timeout (in seconds) for requests to mAP Core service."""


class CeleryConfig(BaseModel):
    """Celery configuration."""

    broker_url: str = "redis://localhost:6379/0"
    """URL of the Celery message broker."""

    result_backend: str = "redis://localhost:6379/0"
    """URL of the Celery result backend."""


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


HasRepoId = t.Annotated[str, StringConstraints(pattern=r".*\{repository_id\}.*")]
"""Pattern for role-based group IDs.
It should include `{repository_id}` placeholder.
"""


HasRepoAndCustomId = t.Annotated[
    str, StringConstraints(pattern=r".*\{repository_id\}.*\{custom_id\}.*")
]
"""Pattern for custom group IDs.
It should include `{repository_id}` followed by `{custom_id}` placeholders.
"""


def setup_config(path_or_obj: str | RuntimeConfig | None) -> RuntimeConfig:
    """Initialize and set the global server configuration instance.

    Args:
        path_or_obj (str | RuntimeConfig): Path to the TOML config file or a
            RuntimeConfig instance to use.

    Returns:
        RuntimeConfig: The initialized config instance.

    """
    if not isinstance(path_or_obj, RuntimeConfig):
        path_or_obj = RuntimeConfig(_toml_file=path_or_obj)  # pyright: ignore[reportCallIssue]

    return path_or_obj


config = t.cast(
    "RuntimeConfig",
    LocalProxy(lambda: current_app.extensions["jairocloud-groups-manager"].config),
)
"""The global server configuration instance."""
