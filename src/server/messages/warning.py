#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides warning log messages used in the server application."""

from .base import LogMessage


DATABASE_NOT_EXIST = LogMessage(
    "W000",
    "The database does not exist. Application may not function correctly.",
)


FAILD_CONNECT_REDIS = LogMessage(
    "W010",
    "Failed to connect to Redis. Application may not function correctly: %(error)s",
)
