#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Database configuration for the server application."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, util

NAMING_CONVENTION = util.immutabledict({
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})
"""Configuration for constraint naming conventions."""


metadata = MetaData(naming_convention=NAMING_CONVENTION)
"""Database metadata object holding associated schema constructs."""


db = SQLAlchemy(metadata=metadata)
"""Database instance using Flask-SQLAlchemy extension."""
