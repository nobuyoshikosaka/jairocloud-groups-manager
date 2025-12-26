#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for the server application."""

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from flask import Blueprint, Flask


def create_blueprints(app: Flask) -> None:
    """Register blueprints for API routers.

    Args:
        app (Flask): The Flask application instance.

    """
    bp_api = Blueprint("api", __name__)

    for _, name, _ in iter_modules([str(Path(__file__).parent)]):
        module = import_module(f"{__package__}.{name}")
        if hasattr(module, "bp"):
            bp_api.register_blueprint(module.bp, url_prefix=f"/{name}")

    app.register_blueprint(bp_api, url_prefix="/api")
