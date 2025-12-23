#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Configuration for the server application.

Provides validation, loading, and global access to runtime configuration.
"""

import typing as t

from contextvars import ContextVar

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from sqlalchemy.engine import URL, make_url
from werkzeug.local import LocalProxy

# ruff: noqa: S105, N802


class RuntimeConfig(BaseSettings):
    """Schema for runtime configuration.

    Handles validation and loading of runtime config values.
    """

    SERVER_NAME: str = "localhost"
    """Server hostname of this application."""

    SECRET_KEY: str = "CHANGE ME"
    """Secret key for cryptographic operations."""

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
    )
    """Base model configuration."""


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


_no_config_msg = "Config has not been initialized."
_current_config: ContextVar[RuntimeConfig] = ContextVar("current_config")


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

    _current_config.set(path_or_obj)
    return path_or_obj


config = t.cast(
    RuntimeConfig, LocalProxy(_current_config, unbound_message=_no_config_msg)
)
"""The global server configuration instance."""
