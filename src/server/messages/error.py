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

FAILED_COMMUNICATE_API = LogMessage(
    "E033",
    "Failed to communicate with mAP Core API.",
)

FAILED_PARSE_RESPONSE = LogMessage(
    "E034",
    "Failed to parse response from mAP Core API.",
)


INVALID_SERVER_CONFIG = LogMessage(
    "E040",
    "Server configuration is invalid or incomplete.",
)


UNSUPPORTED_SEARCH_FILTER = LogMessage(
    "E050",
    "Unsupported search filter or combination of filters.",
)

UNRECOGNIZED_SEARCH_CRITERIA = LogMessage(
    "E051",
    "Unrecognized search criteria.",
)


FAILED_SEARCH_REPOSITORIES = LogMessage(
    "E100",
    "Failed to search Service resources for Repositories.",
)

REPOSITORY_FORBIDDEN = LogMessage(
    "E103",
    "You do not have permission to access this Repository (id: %(id)s).",
)

FAILED_GET_REPOSITORY = LogMessage(
    "E105",
    "Failed to get Service resource for Repository (id: %(id)s).",
)

FAILED_CREATE_REPOSITORY = LogMessage(
    "E110",
    "Failed to create Service for Repository (id: %(id)s).",
)

DUPLICATE_REPOSITORY = LogMessage(
    "E111",
    "A Service resource for Repository (id: %(id)s) already exists.",
)

NO_RIGHTS_CREATE_REPOSITORY = LogMessage(
    "E113",
    "No creation rights for Repository with current access token.",
)

FAILED_UPDATE_REPOSITORY = LogMessage(
    "E120",
    "Failed to update Service resource for Repository (id: %(id)s).",
)

NO_RIGHTS_UPDATE_REPOSITORY = LogMessage(
    "E123",
    "No update rights for Repository (id: %(id)s) with current access token.",
)

REPOSITORY_NOT_FOUND = LogMessage(
    "E124",
    "Service resource for Repository (id: %(id)s) not found.",
)

FAILED_DELETE_REPOSITORY = LogMessage(
    "E130",
    "Failed to delete Service resource for Repository (id: %(id)s).",
)

REPOSITORY_NAME_NOT_MATCH = LogMessage(
    "E131",
    "Confirmed Service name does not match to delete Repository (id: %(id)s).",
)

REPOSITORY_REQUIRES_SYSTEM_ADMIN = LogMessage(
    "E140",
    "At least one System Administrator is required for a Repository.",
)

REPOSITORY_REQUIRES_SERVICE_NAME = LogMessage(
    "E141",
    "Service name is required for a Repository.",
)

REPOSITORY_REQUIRES_SERVICE_URL = LogMessage(
    "E142",
    "Service URL is required for a Repository.",
)

REPOSITORY_INVALID_SERVICE_URL = LogMessage(
    "E143",
    "Service URL must contain a valid hostname",
)

REPOSITORY_TOO_LONG_URL = LogMessage(
    "E144",
    "Service URL is too long (maximum length: %(max)s characters).",
)

REPOSITORY_REQUIRES_ENTITY_ID = LogMessage(
    "E145",
    "At least one entity ID is required for a Repository.",
)


UNCHANGEABLE_REPOSITORY_URL = LogMessage(
    "E150",
    "Service URL of Repository cannot be updated.",
)


UNAUTHORIZED = LogMessage(
    "E401",
    "Login required to access this resource.",
)

UNEXPECTED_SERVER_ERROR = LogMessage(
    "E500",
    "An unexpected error occurred in the server application.",
)

SERVER_UNAVAILABLE = LogMessage(
    "E503",
    "The server application is currently unavailable.",
)
