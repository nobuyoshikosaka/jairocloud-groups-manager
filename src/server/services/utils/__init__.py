#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides utilities for service."""

from .affiliations import detect_affiliation, detect_affiliations
from .decoraters import session_required
from .patch_operations import build_patch_operations, build_update_member_operations
from .permissions import (
    extract_group_ids,
    filter_permitted_group_ids,
    get_current_user_affiliations,
    get_permitted_repository_ids,
    is_current_user_system_admin,
    is_user_logged_in,
    remove_info_outside_system,
)
from .resolvers import resolve_repository_id, resolve_service_id
from .roles import get_highest_role
from .search_queries import (
    GroupsCriteria,
    RepositoriesCriteria,
    UsersCriteria,
    build_search_query,
    make_criteria_object,
)
from .transformers import (
    prepare_group,
    prepare_role_groups,
    prepare_service,
    validate_group_to_map_group,
    validate_repository_to_map_service,
)
