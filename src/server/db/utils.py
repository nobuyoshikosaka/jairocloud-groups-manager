#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Database utilities for the server application."""

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import cast

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.local import LocalProxy


def load_models() -> None:
    """Dynamically import all model modules to register them with SQLAlchemy."""
    for _, name, _ in iter_modules([Path(__file__).parent]):
        import_module(f"{__package__}.{name}")


db = cast(SQLAlchemy, LocalProxy(lambda: current_app.extensions["sqlalchemy"]))
"""Database instance proxy."""
