#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides error log messages used in the server application."""

from .base import LogMessage


DATABASE_NOT_EXIST = LogMessage(
    "E000",
    "Database does not exist.",
)


INVALID_REDIS_CONFIG = LogMessage(
    "E010",
    "Failed to connect to Redis due to invalid configuration.",
)

FAILD_CONNECT_REDIS = LogMessage(
    "E011",
    "Failed to connect to Redis: %(error)s",
)
