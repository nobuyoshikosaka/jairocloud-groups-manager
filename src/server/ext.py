#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Extension for the server application."""

import typing as t

from .api.router import create_blueprints
from .config import RuntimeConfig, setup_config
from .const import DEFAULT_CONFIG_PATH
from .db.base import db
from .db.utils import load_models

if t.TYPE_CHECKING:
    from flask import Flask


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
        self.app = app
        self.config = config or DEFAULT_CONFIG_PATH

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize a Flask application for use with this extension instance.

        Args:
            app (Flask): The Flask application instance.

        """
        self.app = app
        self.init_config(app)
        self.init_db_app(app)

        create_blueprints(app)

        app.extensions["jairocloud-groups-manager"] = self

    def init_config(self, app: Flask) -> None:
        """Initialize the configuration for this extension.

        Args:
            app (Flask): The Flask application instance.

        """
        self.config = setup_config(self.config)

        app.config.from_object(self.config)
        app.config.from_prefixed_env()

    def init_db_app(self, app: Flask) -> None:  # noqa: PLR6301
        """Initialize the database for the this extension.

        Loads all model modules to register them with SQLAlchemy.

        Args:
            app (Flask): The Flask application instance.

        """
        db.init_app(app)
        load_models()
