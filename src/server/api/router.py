#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for the server application."""

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from flask import Blueprint

from server.api.helper import refresh_session


def create_api_blueprint() -> Blueprint:
    """Register blueprints for API routers.

    Returns:
        Blueprint: Blueprint instance for API routers.
    """
    bp_api = Blueprint("api", __name__)

    for _, module_name, _ in iter_modules([str(Path(__file__).parent)]):
        module = import_module(f"{__package__}.{module_name}")
        if hasattr(module, "bp") and isinstance(module.bp, Blueprint):
            bp_api.register_blueprint(
                module.bp, url_prefix=f"/{module_name}", strict_slashes=False
            )

    bp_api.before_request(refresh_session)

    return bp_api
