#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides informational log messages used in the server application."""

from .base import LogMessage


DATABASE_CREATED = LogMessage(
    "I000",
    "Database has been created.",
)

DATABASE_ALREADY_EXISTS = LogMessage(
    "I001",
    "Database already exists. No action taken.",
)

DATABASE_DESTROYED = LogMessage(
    "I002",
    "Database has been destroyed.",
)

DATABASE_NOT_EXIST = LogMessage(
    "I003",
    "Database does not exist. No action taken.",
)

TABLE_CREATED = LogMessage(
    "I004",
    "Database tables created.",
)

TABLE_DROPPED = LogMessage(
    "I005",
    "Database tables dropped.",
)


REQUEST_FOR_AUTH_CODE = LogMessage(
    "I020",
    "Please authenticate at the following URL to issue an access token: %(url)s",
)

SUCCESS_ISSUE_TOKEN = LogMessage(
    "I021",
    "Successfully issued access token for the mAP Core API.",
)

SUCCESS_REFRESH_TOKEN = LogMessage(
    "I022",
    "Successfully refreshed access token for the mAP Core API.",
)
