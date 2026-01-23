#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides utilities for search queries."""

# ruff: noqa: DOC201 DOC501

import re
import typing as t

from datetime import date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

from flask import current_app

from server.config import config
from server.const import (
    MAP_DEFAULT_SEARCH_COUNT,
    USER_ROLES,
)
from server.entities.map_group import MapGroup
from server.entities.map_service import MapService
from server.entities.map_user import MapUser
from server.entities.repository_detail import resolve_service_id
from server.entities.search_request import SearchRequestParameter
from server.exc import InvalidQueryError
from server.services.permissions import (
    get_permitted_repository_ids,
    is_current_user_system_admin,
)

from .affiliations import detect_affiliations


if t.TYPE_CHECKING:
    from pydantic import BaseModel


def build_search_query(criteria: Criteria) -> SearchRequestParameter:
    """Generate search query parameters from criteria model.

    Args:
        criteria (Criteria): The criteria model containing search parameters.

    Returns:
        SearchRequestParameter: The constructed search query parameters.

    Raises:
        InvalidQueryError: If criteria type is unsupported.
    """
    match criteria:
        case UsersCriteria():
            query = build_users_search_query(criteria)
        case GroupsCriteria():
            query = build_groups_search_query(criteria)
        case RepositoriesCriteria():
            query = build_repositories_search_query(criteria)
        case _:
            error = f"Unsupported criteria type: {type(criteria)}"
            current_app.logger.error(error)
            raise InvalidQueryError(error)

    return query


def build_repositories_search_query(
    criteria: RepositoriesCriteria,
) -> SearchRequestParameter:
    """Generate repository search query parameters from criteria model.

    Fileter will be constructed based on the following criteria:
    - Partial match search on id, service_name and service_url (q)
    - Force filter by logged-in user's permitted repository IDs
    - Sort by specified attribute key (k) and direction (d)
    - Pagination (p, l)

    Args:
        criteria (RepositoriesCriteria):
            The object containing repository search parameters.

    Returns:
        SearchRequestParameter: The constructed repository search query parameters.
    """
    path = _path_generator(MapService)
    filter_expr: list[str] = []

    if criteria.q:
        # partial match search on id, service_name and service_url
        filter_expr.append(
            " or ".join([
                f'({path("id")} co "{criteria.q}")',
                f'({path("service_name")} co "{criteria.q}")',
                f'({path("service_url")} co "{criteria.q}")',
            ])
        )

    if is_current_user_system_admin():
        pass  # no additional filter for system admin
    elif permitted := get_permitted_repository_ids():
        # force filter by logged-in user's permitted repository IDs
        filter_expr.append(
            " or ".join([
                f'{path("id")} eq "{resolve_service_id(repository_id=repo_id)}"'
                for repo_id in permitted
            ])
        )
    else:
        # no permitted repositories for non-system admin user
        filter_expr.append(_empty_filter(path("id")))

    filter_str = _combine_filter_exprs(filter_expr)

    options = _curculate_options(criteria, path)

    return SearchRequestParameter(
        filter=filter_str,
        start_index=options.start_index,
        count=options.page_count,
        sort_by=options.sort_by,
        sort_order=options.sort_order,
    )


def build_groups_search_query(criteria: GroupsCriteria) -> SearchRequestParameter:
    """Generate group search query parameters from criteria model.

    Fileter will be constructed based on the following criteria:
    - Partial match search on display_name(q)
    - Exact match search on IDs (i)
    - Force filter by logged-in user's permitted repository IDs
    - Filter by specified repository IDs (r)
    - Filter by specified affiliated user IDs (u)
    - Filter by public status (s)
    - Filter by member list visibility (v)
    - Sort by specified attribute key (k) and direction (d)
    - Pagination (p, l)

    Args:
        criteria (GroupsCriteria):
            The object containing group search parameters.

    Returns:
        SearchRequestParameter:
            The constructed group search query parameters.
    """
    path = _path_generator(MapGroup)
    filter_expr: list[str] = []

    if criteria.q:
        # partial match search on display_name
        filter_expr.append(f'({path("display_name")} co "{criteria.q}")')

    filter_expr.append(_group_groups_filter(criteria, path("id")))

    if criteria.u:
        # exact match search on affiliated user IDs
        filter_expr.append(
            " or ".join([
                f'{path("members.type")} eq "User" '
                f'and {path("members.value")} eq "{user_id}"'
                for user_id in criteria.u
            ])
        )

    match criteria.s:
        case 0:
            filter_expr.append(f"{path('public')} eq true")
        case 1:
            filter_expr.append(f"{path('public')} eq false")
        case _:
            pass

    match criteria.v:
        case 0:
            filter_expr.append(f"{path('member_list_visibility')} eq Public")
        case 1:
            filter_expr.append(f"{path('member_list_visibility')} eq Private")
        case 2:
            filter_expr.append(f"{path('member_list_visibility')} eq Hidden")
        case _:
            pass

    filter_str = _combine_filter_exprs(filter_expr)

    options = _curculate_options(criteria, path)

    return SearchRequestParameter(
        filter=filter_str,
        start_index=options.start_index,
        count=options.page_count,
        sort_by=options.sort_by,
        sort_order=options.sort_order,
    )


def _group_groups_filter(criteria: GroupsCriteria, id_path: str) -> str:
    """Generate a filter string for group IDs based on criteria."""  # noqa:
    criteria = _patch_falsey_to_none(criteria, {"r"})
    is_system_admin = is_current_user_system_admin()

    if is_system_admin:
        # no additional filter for system admin
        specified = criteria.r
    else:
        # force filter by logged-in user's permitted repository IDs
        permitted = get_permitted_repository_ids()
        specified = list(permitted.intersection(criteria.r or permitted))
        if not specified:
            return _empty_filter(id_path)

    match (criteria.i, specified):
        case (i, r) if i and r:
            return _specified_repository_specified_group_filter(id_path, r, i)
        case (i, None) if i:
            return _all_repository_specified_group_filter(id_path, i)
        case (None, r) if r:
            return _specified_repository_all_group_filter(id_path, r)
        case (None, None):
            return _all_repository_all_group_filter(id_path)
        case _:
            raise InvalidQueryError  # pragma: no cover


def build_users_search_query(criteria: UsersCriteria) -> SearchRequestParameter:
    """Generate user search query parameters from criteria model.

    Fileter will be constructed based on the following criteria:
    - Partial match search on user_name, emails, edu_person_principal_names (q)
    - Exact match search on IDs (i)
    - Force filter by logged-in user's permitted repository IDs
    - Filter by specified repository IDs (r) and affiliated roles (a)
    - Filter by specified affiliated group IDs (g)
    - Filter by last modified date (from) (s)
    - Filter by last modified date (to) (e)
    - Sort by specified attribute key (k) and direction (d)
    - Pagination (p, l)

    Args:
        criteria (UsersCriteria):
            The object containing user search parameters.

    Returns:
        SearchRequestParameter:
            The constructed user search query parameters.
    """
    path = _path_generator(MapUser)
    filter_expr: list[str] = []

    if criteria.q:
        # partial match search on user_name, emails, edu_person_principal_names
        filter_expr.append(
            " or ".join([
                f'({path("user_name")} co "{criteria.q}")',
                f'({path("emails.value")} co "{criteria.q}")',
                f'({path("edu_person_principal_names.value")} co "{criteria.q}")',
            ])
        )

    if criteria.i:
        # exact match search on IDs
        filter_expr.append(
            " or ".join([f'{path("id")} eq "{user_id}"' for user_id in criteria.i])
        )

    filter_expr.append(_user_groups_filter(criteria, path("groups.value")))

    if criteria.s:
        # filter by last modified date (from)
        datetime_str = jst_date_to_utc_datetime(criteria.s).isoformat()
        filter_expr.append(f'{path("meta.last_modified")} ge "{datetime_str}"')

    if criteria.e:
        # filter by last modified date (to)
        end_date = criteria.e + timedelta(days=1)
        datetime_str = jst_date_to_utc_datetime(end_date).isoformat()
        filter_expr.append(f'{path("meta.last_modified")} lt "{datetime_str}"')

    filter_str = _combine_filter_exprs(filter_expr)

    options = _curculate_options(criteria, path)

    return SearchRequestParameter(
        filter=filter_str,
        start_index=options.start_index,
        count=options.page_count,
        sort_by=options.sort_by,
        sort_order=options.sort_order,
    )


def _user_groups_filter(criteria: UsersCriteria, path: str) -> str:
    """Generate a filter string for user affiliated group IDs based on criteria."""
    if criteria.g:
        # reduce specified group IDs to only user-defined groups
        _, groups = detect_affiliations(criteria.g)
        criteria.g = [aff.group_id for aff in groups]

    specified_roles: list[str] = []
    if criteria.a:
        user_roles = list(USER_ROLES)
        specified_roles = [
            user_roles[i] for i in criteria.a if 0 <= i < len(user_roles)
        ]
        if not specified_roles:
            return _empty_filter(path)

    if is_current_user_system_admin():
        return _system_admin_user_groups_filter(criteria, path, specified_roles)

    permitted: set[str] = get_permitted_repository_ids()
    if criteria.r:
        permitted = permitted.intersection(set(criteria.r))

    if not permitted:
        return _empty_filter(path)

    return _repository_admin_user_groups_filter(
        criteria, path, permitted, specified_roles
    )


def _system_admin_user_groups_filter(  # noqa: PLR0911
    criteria: UsersCriteria, path: str, specified_roles: list[str]
) -> str:
    """Generate a filter string for user affiliated group IDs for system admin."""
    criteria = _patch_falsey_to_none(criteria, {"a", "r", "g"})

    match (criteria.a, criteria.r, criteria.g):
        case (a, r, g) if a and r and g:
            return _specified_repository_specified_role_specified_group_filter(
                path, r, specified_roles, g
            )
        case (a, r, None) if a and r:
            return _specified_repository_specified_role_filter(path, r, specified_roles)
        case (a, None, g) if a and g:
            return _all_repository_specified_role_specified_group_filter(
                path, specified_roles, g
            )
        case (a, None, None) if a:
            return _all_repository_specified_role_filter(path, specified_roles)

        case (None, r, g) if r and g:
            return _specified_repository_specified_group_filter(path, r, g)
        case (None, r, None) if r:
            return _specified_repository_all_group_filter(path, r)
        case (None, None, g) if g:
            return _all_repository_specified_group_filter(path, g)

        case (None, None, None):
            return _all_repository_all_group_filter(path)
        case _:
            raise InvalidQueryError  # pragma: no cover


def _repository_admin_user_groups_filter(
    criteria: UsersCriteria, path: str, permitted: set[str], specified_roles: list[str]
) -> str:
    """Generate a filter string for user affiliated group IDs for repository admin."""
    criteria = _patch_falsey_to_none(criteria, {"a", "g"})

    match (criteria.a, criteria.g):
        case (a, g) if a and g:
            return _specified_repository_specified_role_specified_group_filter(
                path, list(permitted), specified_roles, g
            )
        case (a, None) if a:
            return _specified_repository_specified_role_filter(
                path, list(permitted), specified_roles
            )
        case (None, g) if g:
            return _specified_repository_specified_group_filter(
                path, list(permitted), g
            )
        case (None, None):
            return _specified_repository_all_group_filter(path, list(permitted))
        case _:
            raise InvalidQueryError  # pragma: no cover


@cache
def _path_generator(model: type[BaseModel]) -> t.Callable[[str], str]:
    """Generate a function to create attribute paths with aliasing."""

    def _func(path: str) -> str:
        alias_generator = model.model_config.get("alias_generator")
        if alias_generator and not callable(alias_generator):
            alias_generator = alias_generator.serialization_alias
        if alias_generator is None:
            alias_generator = lambda x: x  # noqa: E731

        return ".".join([alias_generator(p) for p in path.split(".")])

    return _func


def _all_repository_all_group_filter(path: str) -> str:
    """Generate a filter string.

    Filter by prefix match for group IDs without specifying a repository.
    """
    prefix_patterns = _get_prefix_patterns()
    return " or ".join([f'{path} sw "{prefix}"' for prefix in prefix_patterns])


def _all_repository_specified_role_filter(path: str, roles: list[str]) -> str:
    """Generate a filter string.

    Filter by prefix/suffix match for role-type group IDs without specifying
    a repository.
    """
    id_patterns = _get_id_patterns()
    return " or ".join([
        f'{path} sw "{prefix}" and {path} ew "{suffix}"'
        for role in roles
        for prefix, suffix in [id_patterns[role]]
    ])


def _all_repository_specified_group_filter(path: str, group_ids: list[str]) -> str:
    """Generate a filter string.

    Filter by exact match for group IDs without specifying a repository.
    """
    return " or ".join([f'{path} eq "{group_id}"' for group_id in group_ids])


def _all_repository_specified_role_specified_group_filter(
    path: str, roles: list[str], group_ids: list[str]
) -> str:
    """Generate a filter string.

    Filter by exact match for group IDs and prefix/suffix match for role-type group IDs.
    """
    groups_filter = _all_repository_specified_group_filter(path, group_ids)
    roles_filter = _all_repository_specified_role_filter(path, roles)

    return " and ".join([f"({groups_filter})", f"({roles_filter})"])


def _specified_repository_all_group_filter(path: str, repository_ids: list[str]) -> str:
    """Generate a filter string.

    Filter by prefix match for group IDs within specified repositories.
    """
    prefix_patterns = _get_prefix_patterns()
    return " or ".join([
        f'{path} sw "{prefix}{repo_id}"'
        for prefix in prefix_patterns
        for repo_id in repository_ids
    ])


def _specified_repository_specified_role_filter(
    path: str, repository_ids: list[str], roles: list[str]
) -> str:
    """Generate a filter string.

    Filter by exact match for role-type group IDs within specified repositories.
    """
    id_patterns = _get_id_patterns()
    return " or ".join([
        f'{path} eq "{prefix}{repo_id}{suffix}"'
        for repo_id in repository_ids
        for role in roles
        for prefix, suffix in [id_patterns[role]]
    ])


def _specified_repository_specified_group_filter(
    path: str, repository_ids: list[str], group_ids: list[str]
) -> str:
    """Generate a filter string.

    Filter by exact match for group IDs within specified repositories.
    """
    _, groups = detect_affiliations(group_ids)
    # filter by repository IDs that the specified group belongs to
    filtered_groups = [aff for aff in groups if aff.repository_id in repository_ids]
    if filtered_groups:
        return " or ".join([f'{path} eq "{g.group_id}"' for g in filtered_groups])

    return _empty_filter(path)


def _specified_repository_specified_role_specified_group_filter(
    path: str, repository_ids: list[str], roles: list[str], group_ids: list[str]
) -> str:
    """Generate a filter string.

    Filter by exact match for group IDs and role-type group IDs within specified
    repositories.
    """
    groups_filter = _specified_repository_specified_group_filter(
        path, repository_ids, group_ids
    )
    roles_filter = _specified_repository_specified_role_filter(
        path, repository_ids, roles
    )
    if (empty_filter := _empty_filter(path)) in {groups_filter, roles_filter}:
        return empty_filter

    return " and ".join([f"{groups_filter}", f"{roles_filter}"])


def _empty_filter(path: str) -> str:
    """Generate a filter string that matches no results."""
    return f'{path} eq ""'


@cache
def _get_prefix_patterns() -> set[str]:
    """Get group ID prefix patterns for all group types.

    The return value of this is cached.

    Returns:
        set: A set of group ID prefix patterns.
    """
    id_patterns = config.GROUPS.id_patterns
    pattern = r"(.*)\{repository_id\}(.*)"
    return {
        match.group(1)
        for group_types in id_patterns.model_fields_set
        if (match := re.match(pattern, getattr(id_patterns, group_types))) and match
    }


@cache
def _get_id_patterns() -> dict[str, tuple[str, str]]:
    """Get group ID patterns for each group type.

    The return value of this is cached.

    Returns:
        dict: A dictionary mapping group types to their (prefix, suffix) patterns.
    """
    patterns = config.GROUPS.id_patterns
    pattern = r"(.*)\{repository_id\}(.*)"
    return {
        group_types: (match.group(1), match.group(2))
        for group_types in patterns.model_fields_set
        if (match := re.match(pattern, getattr(patterns, group_types))) and match
    }


def _combine_filter_exprs(filter_exprs: list[str]) -> str | None:
    """Combine multiple filter expressions into a single filter string.

    If only one expression is present, it is returned as is. Otherwise, expressions
    are combined using logical AND, with each expression enclosed in parentheses.

    Args:
        filter_exprs (list[str]): List of filter expressions.

    Returns:
        str: The combined filter string, or None if no expressions are provided.

    """
    if len(filter_exprs) == 1 and "or" not in filter_exprs[0]:
        return filter_exprs[0]
    return " and ".join(f"({expr})" for expr in filter_exprs) if filter_exprs else None


class _Options(t.NamedTuple):
    start_index: int | None
    page_count: int | None
    sort_by: str | None
    sort_order: t.Literal["ascending", "descending"] | None


def _curculate_options(
    criteria: Criteria, path_generator: t.Callable[[str], str]
) -> _Options:
    """Calculate search options from criteria.

    Args:
        criteria (Criteria): The criteria object.
        path_generator (Callable[[str], str]):
            A function to generate attribute paths.

    Returns:
        Options:
            The calculated search options that is, (`start_index`, `page_size`,
            `sort_by`, `sort_order`).
    """

    def _a(ks: set[str]) -> set[str]:
        return ks | {path_generator(k) for k in ks}

    if criteria.k in _a({
        "id",
        "service_name",
        "service_url",
        "display_name",
        "user_name",
        "public",
        "member_list_visibility",
    }):
        sort_by = path_generator(criteria.k)
    elif criteria.k in _a({"emails"}):
        sort_by = f"{path_generator('emails.value')}"
    elif criteria.k in _a({"eppns", "edu_person_principal_names"}):
        sort_by = f"{path_generator('edu_person_principal_names.value')}"
    else:
        sort_by = None

    match criteria.d:
        case "asc":
            sort_order = "ascending"
        case "desc":
            sort_order = "descending"
        case _:
            sort_order = None

    match (criteria.p, criteria.l):
        case (int() as p, int() as l) if p > 0 and l > 0:
            # both page number and page size are valid
            page_count = l
            start_index = (p - 1) * page_count + 1
        case (int() as p, 0 | None) if p > 0:
            # only page number is valid
            page_count = MAP_DEFAULT_SEARCH_COUNT
            start_index = (p - 1) * page_count + 1
        case (_, 0 | None):
            # page size is zero or not specified
            page_count = MAP_DEFAULT_SEARCH_COUNT
            start_index = None
        case _:
            # specified negative or zero page number
            page_count = None
            start_index = None

    return _Options(
        start_index=start_index,
        page_count=page_count,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def _patch_falsey_to_none[T: Criteria](value: T, attr: set[str]) -> T:
    """Patch falsey attribute values to None in the criteria object."""
    for key in attr:
        if hasattr(value, key) and not getattr(value, key):
            setattr(value, key, None)
    return value


def jst_date_to_utc_datetime(d: date) -> datetime:
    """Convert a date in JST to a datetime in UTC.

    Args:
        d (date): The date.

    Returns:
        datetime: The corresponding datetime in UTC.

    """
    dt_jst = datetime.combine(d, datetime.min.time(), tzinfo=ZoneInfo("Asia/Tokyo"))
    return dt_jst.astimezone(ZoneInfo("UTC"))


class Criteria(t.Protocol):
    """Protocol for search criteria."""

    q: str | None
    """Search term to filter results."""

    k: str | None
    """Attribute key to sort results."""

    d: t.Literal["asc", "desc"] | None
    """Sort order: 'asc' (ascending) or 'desc' (descending)."""

    p: int | None
    """Page number to retrieve."""

    l: int | None  # noqa: E741
    """Page size (number of items per page)."""


@t.runtime_checkable
class RepositoriesCriteria(Criteria, t.Protocol):
    """Protocol for search criteria."""


@t.runtime_checkable
class GroupsCriteria(Criteria, t.Protocol):
    """Protocol for search criteria."""

    i: list[str] | None
    """Filter by IDs."""

    r: list[str] | None
    """Filter by affiliated repository IDs."""

    u: list[str] | None
    """Filter by affiliated user IDs."""

    s: t.Literal[0, 1] | None
    """Filter by public status: 0 (public), 1 (private)."""

    v: t.Literal[0, 1, 2] | None
    """Filter by member list visibility: 0 (public), 1 (private), 2 (hidden)."""


@t.runtime_checkable
class UsersCriteria(Criteria, t.Protocol):
    """Protocol for search criteria."""

    i: list[str] | None
    """Filter by IDs."""

    r: list[str] | None
    """Filter by affiliated repository IDs."""

    g: list[str] | None
    """Filter by affiliated group IDs."""

    a: list[int] | None
    """Filter by user roles:

    0 (system admin), 1 (repository admin), 2 (community admin),
    3 (contributor), 4 (general user).
    """

    s: date | None
    """Filter by last modified date (from)."""

    e: date | None
    """Filter by last modified date (to)."""
