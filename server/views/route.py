from flask import Flask

from views.auth import bp as auth_bp


def create_blueprints(app: Flask):
    """Register all blueprints with the Flask application."""

    app.register_blueprint(auth_bp)
