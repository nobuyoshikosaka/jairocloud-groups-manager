#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Custom exceptions for the server application."""


class JAIROCloudGroupsManagerError(Exception):
    """Base exception for the server application."""


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


class DatabaseError(JAIROCloudGroupsManagerError):
    """Exception for database errors.

    Errors caused by database operation issues.
    """
