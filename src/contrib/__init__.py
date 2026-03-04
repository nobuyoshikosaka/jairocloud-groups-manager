#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides utilities to contribute to development."""

# ruff: noqa: RUF067

from flask import current_app

from .dump import dump
from .messages import generate_type_stub


if current_app.config["ENV"] != "development" or not current_app.debug:
    error = "Contrib utilities can only be used in development mode."
    raise RuntimeError(error)
