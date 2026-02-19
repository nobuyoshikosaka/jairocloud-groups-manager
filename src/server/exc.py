#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Custom exceptions for the server application."""

from server.messages.base import LogMessage


class JAIROCloudGroupsManagerError(Exception):
    """Base exception for the server application."""

    def __init__(self, message: str | LogMessage) -> None:
        """Initialize the exception instance.

        Args:
            message (str | LogMessage): The error message.

        """
        self.code = ""
        if isinstance(message, LogMessage):
            self.code = message.code
            message = message.data
        super().__init__(message)

        self.message = message


class ConfigurationError(JAIROCloudGroupsManagerError):
    """Exception for configuration errors."""


class CertificatesError(JAIROCloudGroupsManagerError):
    """Exception for certificate errors.

    Errors caused by entity ID or certificates issues.
    """


class ServiceSettingsError(JAIROCloudGroupsManagerError):
    """Exception for service settings."""


class CredentialsError(ServiceSettingsError):
    """Exception for client credentials.

    Error caused by client ID and client secret issues.
    """


class OAuthTokenError(ServiceSettingsError):
    """Exception for OAuth token.

    Error caused by access token and refresh token issues.
    """


class UnsafeOperationError(JAIROCloudGroupsManagerError):
    """Exception for unsafe operations.

    Errors caused by operations that are considered unsafe.
    """


class SystemAdminNotFound(JAIROCloudGroupsManagerError):  # noqa: N818
    """Exception for system administrator not found.

    Errors caused by the absence of a system administrator in the system.
    """


class DatabaseError(JAIROCloudGroupsManagerError):
    """Exception for database errors.

    Errors caused by database operation issues.
    """


class RecordNotFound(DatabaseError):  # noqa: N818
    """Exception for record not found errors.

    Errors caused by requests for non-existing records.
    """


class DatastoreError(JAIROCloudGroupsManagerError):
    """Exception for datastore errors.

    Errors caused by datastore operation issues.
    """


class ApiClientError(JAIROCloudGroupsManagerError):
    """Exception for mAP Core API errors.

    Errors caused by mAP Core API server issues.
    """


class ResourceInvalid(ApiClientError):  # noqa: N818
    """Exception for resource invalid errors from mAP Core API server.

    Errors caused by invalid resource data in requests.
    """


class ResourceNotFound(ApiClientError):  # noqa: N818
    """Exception for resource not found errors from mAP Core API server.

    Errors caused by requests for non-existing resources.
    """


class UnexpectedResponseError(ApiClientError):
    """Exception for unexpected responses from mAP Core API server.

    Errors caused by unexpected response structure or data from mAP Core API server.
    """


class ApiRequestError(JAIROCloudGroupsManagerError):
    """Exception for the server application API errors.

    Errors caused by API request issues.
    """


class RequestConflict(ApiRequestError):  # noqa: N818
    """Exception for the request conflict errors.

    Errors caused by conflicts in the request content.
    """


class InvalidQueryError(JAIROCloudGroupsManagerError):
    """Exception for unexpected query construction errors.

    Errors caused by unexpected query structure or data during query construction.
    """


class InvalidFormError(JAIROCloudGroupsManagerError):
    """Exception for invalid form data errors.

    Errors caused by invalid form data in API requests.
    """


class ImmutableError(JAIROCloudGroupsManagerError):
    """Exception for immutable attribute modification errors.

    Errors caused by attempts to modify immutable attributes.
    """
