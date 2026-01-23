#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for managing user management endpoints."""

from flask import Blueprint
from flask_pydantic import validate

from server.entities.search_request import SearchResult
from server.services import users

from .schemas import UsersQuery


bp = Blueprint("users", __name__)


@bp.get("")
@bp.get("/")
@validate(response_by_alias=True)
def get(query: UsersQuery) -> tuple[SearchResult, int]:
    """Get a list of users based on query parameters.

    Args:
        query (UsersQuery): Query parameters for filtering users.

    Returns:
        tuple[dict, int]: A tuple containing the list of users and the HTTP status code.
    """
    results = users.search(query)
    return results, 200
