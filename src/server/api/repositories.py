#
# Copyright (C) 2025 National Institute of Informatics.
#

"""API router for managing repository management endpoints."""

from flask import Blueprint
from flask_pydantic import validate

from server.entities.search_request import SearchResult
from server.entities.summaries import RepositorySummary

from .schemas import RepositoriesQuery


bp = Blueprint("repositories", __name__)


@bp.get("")
@bp.get("/")
@validate(response_by_alias=True)
def get(query: RepositoriesQuery) -> tuple[SearchResult, int]:
    """Get a list of users based on query parameters.

    Args:
        query (UsersQuery): Query parameters for filtering users.

    Returns:
        tuple[dict, int]: A tuple containing the list of users and the HTTP status code.
    """
    results = SearchResult(
        total=2,
        page_size=10,
        offset=0,
        resources=[
            RepositorySummary(id="001", display_name="test-1"),
            RepositorySummary(id="002", display_name="test-2"),
        ],
    )  # repositories.search(query)
    return results, 200
