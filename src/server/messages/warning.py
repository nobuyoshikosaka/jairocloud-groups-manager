#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides warning log messages used in the server application."""

from .base import LogMessage


DATABASE_NOT_EXIST = LogMessage(
    "W000",
    "The database does not exist. Application may not function correctly.",
)


FAILED_CONNECT_REDIS = LogMessage(
    "W010",
    "Failed to connect to Redis. Application may not function correctly: %(error)s",
)


ACCESS_TOKEN_NOT_AVAILABLE = LogMessage(
    "W020",
    "Access token is invalid or expired.",
)


FAILED_SET_CACHE = LogMessage(
    "W070",
    "Failed to set cache (func %(func)s, id: %(id)s).",
)

FAILED_GET_CACHE = LogMessage(
    "W071",
    "Failed to get cache (func %(func)s, id: %(id)s).",
)

FAILED_PARSE_CACHE = LogMessage(
    "W072",
    "Failed to parse cache (func %(func)s, id: %(id)s).",
)

FAILED_DELETE_CACHE = LogMessage(
    "W073",
    "Failed to delete cache (func %(func)s, id: %(id)s).",
)
