#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Extension for the server application."""

import typing as t

from .api.router import create_api_blueprint
from .auth import login_manager
from .cli.base import register_cli_commands
from .config import RuntimeConfig, setup_config
from .const import DEFAULT_CONFIG_PATH
from .datastore import setup_datastore
from .db.base import db
from .db.utils import load_models
from .exc import ConfigurationError
from .logger import setup_logger


if t.TYPE_CHECKING:
    from flask import Flask
    from redis import Redis


class JAIROCloudGroupsManager:
    """Flask extension for JAIRO Cloud Groups management."""

    def __init__(
        self, app: Flask | None = None, config: RuntimeConfig | str | None = None
    ) -> None:
        """Initialize this extension instance.

        Args:
            app (Flask | None): The Flask application instance.
            config (RuntimeConfig | str | None): The runtime configuration
                instance or path to the configuration file.

        """
        self._config = config or DEFAULT_CONFIG_PATH
        self.datastore: dict[str, Redis] = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize a Flask application for use with this extension instance.

        Args:
            app (Flask): The Flask application instance.

        """
        self.init_config(app)
        self.init_db_app(app)

        setup_logger(app, self.config)

        login_manager.init_app(app)

        self.datastore = setup_datastore(app, self.config)
        app.register_blueprint(create_api_blueprint(), url_prefix="/api")
        register_cli_commands(app)

        if app.debug or app.config.get("ENV") == "development":
            self.dev_contrib(app)

        app.extensions["jairocloud-groups-manager"] = self

    def init_config(self, app: Flask) -> None:
        """Initialize the configuration for this extension.

        Args:
            app (Flask): The Flask application instance.

        """
        self._config = setup_config(self._config)

        app.config.from_mapping(self.config.for_flask)
        app.config.from_prefixed_env()

    def init_db_app(self, app: Flask) -> None:  # noqa: PLR6301
        """Initialize the database for the this extension.

        Loads all model modules to register them with SQLAlchemy.

        Args:
            app (Flask): The Flask application instance.

        """
        db.init_app(app)
        load_models()

    @staticmethod
    def dev_contrib(app: Flask) -> None:
        """Provide development contribution utilities."""
        with app.app_context():
            from contrib import messages  # noqa: PLC0415

            messages.generate_type_stub()

    @property
    def config(self) -> RuntimeConfig:
        """Runtime configuration instance.

        Returns:
            RuntimeConfig: The runtime configuration instance.

        Raises:
            ConfigurationError: If the configuration has not been initialized.
        """
        if isinstance(self._config, str):
            error = "Configuration has not been initialized."
            raise ConfigurationError(error)

        return self._config
