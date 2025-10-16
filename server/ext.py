from flask import Flask

from db.shared import db
from db.loader import load_models
from views.route import create_blueprints


class MapWebUI:
    """Main application class for the mAP Web UI."""

    def __init__(self, app: Flask | None = None):
        """Initialize the MapWebUI application.

        Args:
            app (Flask | None): The Flask application instance.
        """
        self.app = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize the MapWebUI application with a Flask app.

        Args:
            app (Flask): The Flask application instance.
        """
        self.app = app
        self.init_db_app(app)

        create_blueprints(app)

        app.extensions["map_web_ui"] = self

    def init_db_app(self, app: Flask):
        """Initialize the database with the Flask application.

        Args:
            app (Flask): The Flask application instance.
        """
        db.init_app(app)
        load_models()
