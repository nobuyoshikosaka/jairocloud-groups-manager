#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Utilities for client operations."""

import hashlib
import time


def get_time_stamp() -> str:
    """Get the current timestamp as Unix time in seconds.

    Returns:
        str: The current timestamp.
    """
    return str(int(time.time()))


def compute_signature(client_secret: str, access_token: str, time_stamp: str) -> str:
    """Compute a SHA-256 signature.

    Args:
        client_secret (str): The client secret.
        access_token (str): The access token.
        time_stamp (str): The timestamp.

    Returns:
        str: The computed SHA-256 signature as a hexadecimal string.
    """
    return hashlib.sha256(
        f"{client_secret}{access_token}{time_stamp}".encode()
    ).hexdigest()
