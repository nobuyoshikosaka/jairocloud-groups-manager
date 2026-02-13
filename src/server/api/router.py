#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for the server application."""

import traceback

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from flask import Blueprint
from flask_pydantic import validate

from server.auth import login_manager, refresh_session
from server.exc import CredentialsError, JAIROCloudGroupsManagerError, OAuthTokenError

from .schemas import ErrorResponse


def create_api_blueprint() -> Blueprint:
    """Register blueprints for API routers.

    Returns:
        Blueprint: Blueprint instance for API routers.
    """
    bp_api = Blueprint("api", __name__)

    for _, module_name, _ in iter_modules([str(Path(__file__).parent)]):
        module = import_module(f"{__package__}.{module_name}")
        if hasattr(module, "bp") and isinstance(module.bp, Blueprint):
            bp_api.register_blueprint(module.bp, url_prefix=f"/{module_name}")

    @bp_api.errorhandler(JAIROCloudGroupsManagerError)
    @validate()
    def handle_unexpected_error(
        error: JAIROCloudGroupsManagerError,
    ) -> tuple[ErrorResponse, int]:
        """Handle unexpected errors for the API.

        Args:
            error: The error object.

        Returns:
            dict: Response body.
        """
        traceback.print_exc()
        return ErrorResponse(code=error.code, message=error.message), 500

    @bp_api.errorhandler(OAuthTokenError)
    @bp_api.errorhandler(CredentialsError)
    @validate()
    def handle_service_settings_error(
        error: CredentialsError | OAuthTokenError,
    ) -> tuple[ErrorResponse, int]:
        """Handle service settings errors for the API.

        Args:
            error: The error object.

        Returns:
            dict: Response body.
        """
        traceback.print_exc()
        return ErrorResponse(code=error.code, message=error.message), 503

    bp_api.before_request(refresh_session)

    @login_manager.unauthorized_handler
    @validate()
    def unauthorized() -> tuple[ErrorResponse, int]:
        """Handle unauthorized access attempts.

        Returns:
            dict: Response body indicating unauthorized access.
        """
        return ErrorResponse(code="", message="Login required."), 401

    return bp_api
