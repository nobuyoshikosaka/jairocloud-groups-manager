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

FAILED_CONNECT_REDIS = LogMessage(
    "E011",
    "Failed to connect to Redis: %(error)s",
)


FAILED_ISSUE_CREDENTIALS = LogMessage(
    "E020",
    "Failed to issue client credentials.",
)

FAILED_ISSUE_TOKEN = LogMessage(
    "E021",
    "Failed to issue access token.",
)

FAILED_CHECK_TOKEN = LogMessage(
    "E022",
    "Failed to check the validity of the access token.",
)

FAILED_REFRESH_TOKEN = LogMessage(
    "E023",
    "Failed to refresh access token.",
)

CREDENTIALS_NOT_STORED = LogMessage(
    "E024",
    "Client credentials are not stored on the server.",
)

ACCESS_TOKEN_NOT_STORED = LogMessage(
    "E025",
    "Access token is not stored on the server.",
)

REFRESH_TOKEN_NOT_STORED = LogMessage(
    "E026",
    "Refresh token is not stored on the server.",
)

ACCESS_TOKEN_NOT_AVAILABLE = LogMessage(
    "E027",
    "Access token is invalid or expired.",
)


RECEIVE_RESPONSE_MESSAGE = LogMessage(
    "E030",
    "Received error from mAP Core API: %(message)s",
)

RECEIVE_UNEXPECTED_RESPONSE = LogMessage(
    "E031",
    "Received unexpected response from mAP Core API.",
)

FAILED_DECODE_RESPONSE = LogMessage(
    "E032",
    "Failed to decode response from mAP Core API.",
)
