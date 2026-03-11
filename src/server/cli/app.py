#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Application command-line interface."""

import pathlib
import tomllib

import click

from flask import current_app


@click.group()
def app() -> None:
    """Manage application."""


@app.command()
def version() -> None:
    """Display application version."""
    with pathlib.Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    version = pyproject["project"]["version"]
    current_app.logger.info(version)
