#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Configuration for the server application.

Provides validation, loading, and global access to runtime configuration.
"""

import typing as t

from contextvars import ContextVar

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from werkzeug.local import LocalProxy


class CeleryConfig(BaseModel):
    """Celery configuration."""

    broker_url: str = "redis://localhost:6379/0"
    """URL of the Celery message broker."""

    result_backend: str = "redis://localhost:6379/0"
    """URL of the Celery result backend."""


class RuntimeConfig(BaseSettings):
    """Schema for runtime configuration.

    Handles validation and loading of runtime config values.
    """

    SERVER_NAME: str = "localhost"
    """Server hostname of this application."""

    SECRET_KEY: str = "CHANGE ME"  # noqa: S105
    """Secret key for cryptographic operations."""

    CELERY: CeleryConfig = CeleryConfig()
    """Celery configuration values."""

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
