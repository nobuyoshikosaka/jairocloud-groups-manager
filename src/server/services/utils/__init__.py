#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides utilities for service."""

from .affiliations import detect_affiliation, detect_affiliations
from .patch_operations import build_patch_operations
from .search_queries import (
    GroupsCriteria,
    RepositoriesCriteria,
    UsersCriteria,
    build_search_query,
)
