from flask import Flask


def create_app(config_object="config.config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    @app.route("/")
    def home():
        return "Welcome to the mAP Web UI!"

    return app
