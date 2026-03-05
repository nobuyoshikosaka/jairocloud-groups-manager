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


SUCCESS_ISSUE_CREDENTIALS = LogMessage(
    "I020",
    "Successfully issued client credentials for the mAP Core API.",
)

REQUEST_FOR_AUTH_CODE = LogMessage(
    "I021",
    "Please authenticate at the following URL to issue an access token: %(url)s",
)

SUCCESS_ISSUE_TOKEN = LogMessage(
    "I022",
    "Successfully issued access token for the mAP Core API.",
)

SUCCESS_REFRESH_TOKEN = LogMessage(
    "I023",
    "Successfully refreshed access token for the mAP Core API.",
)

ACCESS_TOKEN_AVAILABLE = LogMessage(
    "I024",
    "Access token is valid and available.",
)

SUCCESS_GET_TOKEN_OWNER = LogMessage(
    "I025",
    "Successfully get token owner's User resource from mAP Core API. \n%(user)s",
)


RECEIVE_RESPONSE_MESSAGE = LogMessage(
    "I030",
    "Received response from mAP Core API: %(message)s",
)


SUCCESS_CREATE_REPOSITORY = LogMessage(
    "I100",
    "Successfully created Service resource for Repository (id: %(service_id)s)",
)

SUCCESS_CREATE_ROLEGROUPS = LogMessage(
    "I101",
    "Successfully created role-type groups for Repository (id: %(service_id)s)",
)

SUCCESS_UPDATE_REPOSITORY = LogMessage(
    "I102",
    "Successfully updated Service resource for Repository (id: %(service_id)s)",
)

SUCCESS_DELETE_REPOSITORY = LogMessage(
    "I103",
    "Successfully deleted Service resource for Repository (id: %(service_id)s)",
)
