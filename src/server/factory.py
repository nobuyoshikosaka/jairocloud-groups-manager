#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Factory for creating and configuring the Flask application."""

import typing as t

from uuid import uuid7

from celery import Celery, Task
from flask import Flask

from .ext import JAIROCloudGroupsManager


if t.TYPE_CHECKING:
    from .config import RuntimeConfig


@t.overload
def create_app(import_name: str) -> Flask: ...
@t.overload
def create_app(import_name: str, *, config_path: str) -> Flask: ...
@t.overload
def create_app(import_name: str, *, config: RuntimeConfig) -> Flask: ...


def create_app(
    import_name: str,
    config_path: str | None = None,
    config: RuntimeConfig | None = None,
) -> Flask:
    """Factory function to create and configure the Flask application.

    Args:
        import_name (str): The name of the application package.
        config_path (str | None): The path to the configuration TOML file.
        config (RuntimeConfig | None): The runtime configuration instance.

    Returns:
        Flask: The configured Flask application instance.

    """
    app = Flask(import_name)
    JAIROCloudGroupsManager(app, config=config or config_path)
    celery_init_app(app)

    return app


def celery_init_app(app: Flask) -> Celery:
    """Initialize and configure a Celery application with the Flask app context.

    Args:
        app (Flask): The Flask application instance.

    Returns:
        Celery: The configured Celery application instance.
    """

    class FlaskTask(Task):
        """Task with Flask application context."""

        # ruff : noqa: ANN001 ANN002 ANN003 ANN204 ANN202
        @t.override
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

        @t.override
        def apply_async(self, *args, task_id=None, **kwargs):
            task_id = task_id or str(uuid7())
            return super().apply_async(args, kwargs, task_id=task_id)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app

    return celery_app
