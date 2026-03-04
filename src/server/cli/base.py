#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Base of command-line interface."""

import typing as t

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules


if t.TYPE_CHECKING:
    from flask import Flask


def register_cli_commands(app: Flask) -> None:
    """Register all CLI commands to the Flask application.

    In each module, only objects with the same name as the module itself
    are treated as subcommands.

    Args:
        app (Flask): The Flask application instance.
    """
    for _, name, _ in iter_modules([str(Path(__file__).parent)]):
        module = import_module(f"{__package__}.{name}")
        cmd = getattr(module, name, None)
        if cmd is not None:
            app.cli.add_command(cmd)
