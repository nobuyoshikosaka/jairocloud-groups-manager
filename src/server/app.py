#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Entry point for the server application."""

from .factory import create_app


app = create_app(__name__)
