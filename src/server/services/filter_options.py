#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services to provide filter options for search requests."""

import re
import typing as t

from server.const import USER_ROLES
from server.entities.search_request import FilterOption
from server.services import groups, repositories
from server.services.permissions import (
    is_current_user_system_admin,
)
from server.services.utils.search_queries import (
    UsersCriteria,
    make_criteria_object,
    user_sortable_keys,
)


if t.TYPE_CHECKING:
    from server.entities.summaries import UserSummary


def search_users_options() -> list[FilterOption[UserSummary]]:
    """Provide filter options for searching users.

    Returns:
        list[FilterOption]: List of filter options for user search.
    """
    alias = FilterOption._alias_generator  # noqa: SLF001
    is_system_admin = is_current_user_system_admin()

    options: list[FilterOption] = [
        # search term
        FilterOption(
            key="q",
            description=_get_description(UsersCriteria, "q"),
            type=_get_type(UsersCriteria, "q"),
            multiple=_allow_multiple(UsersCriteria, "q"),
        ),
        # IDs
        FilterOption(
            key="i",
            description=_get_description(UsersCriteria, "i"),
            type=_get_type(UsersCriteria, "i"),
            multiple=_allow_multiple(UsersCriteria, "i"),
        ),
    ]

    repos: list[dict[str, str]] = [
        {"value": repo.id, "label": t.cast("str", repo.service_name)}
        for repo in repositories.search(
            make_criteria_object("repositories", l=-1)
        ).resources
    ]

    if repos:
        options.append(
            # affiliated repositories
            FilterOption(
                key="r",
                description=_get_description(UsersCriteria, "r"),
                type=_get_type(UsersCriteria, "r"),
                multiple=_allow_multiple(UsersCriteria, "r"),
                items=repos,
            )
        )

    gros: list[dict[str, str]] = [
        {"value": group.id, "label": t.cast("str", group.display_name)}
        for group in groups.search(make_criteria_object("groups", l=-1)).resources
    ]

    if gros:
        options.append(
            # affiliated groups
            FilterOption(
                key="g",
                description=_get_description(UsersCriteria, "g"),
                type=_get_type(UsersCriteria, "g"),
                multiple=_allow_multiple(UsersCriteria, "g"),
                items=gros,
            )
        )

    roles = list(USER_ROLES)
    options.append(
        # user roles
        FilterOption(
            key="a",
            description=_get_description(UsersCriteria, "a"),
            type=_get_type(UsersCriteria, "a"),
            multiple=_allow_multiple(UsersCriteria, "a"),
            items=[
                {"value": i, "label": alias(name)}
                for i, name in enumerate(roles)
                if is_system_admin or name != USER_ROLES.SYSTEM_ADMIN
            ],
        )
    )

    options.extend((
        # last modified date (from)
        FilterOption(
            key="s",
            description=_get_description(UsersCriteria, "s"),
            type=_get_type(UsersCriteria, "s"),
            multiple=_allow_multiple(UsersCriteria, "s"),
        ),
        # last modified date (to)
        FilterOption(
            key="e",
            description=_get_description(UsersCriteria, "e"),
            type=_get_type(UsersCriteria, "e"),
            multiple=_allow_multiple(UsersCriteria, "e"),
        ),
        # sort key
        FilterOption(
            key="k",
            description=_get_description(UsersCriteria, "k"),
            type=_get_type(UsersCriteria, "k"),
            multiple=_allow_multiple(UsersCriteria, "k"),
            items=[{"value": alias(key)} for key in user_sortable_keys],
        ),
        # sort order
        FilterOption(
            key="d",
            description=_get_description(UsersCriteria, "d"),
            type=_get_type(UsersCriteria, "d"),
            multiple=_allow_multiple(UsersCriteria, "d"),
            items=[
                {"value": "asc", "label": "Ascending"},
                {"value": "desc", "label": "Descending"},
            ],
        ),
        # page number
        FilterOption(
            key="p",
            description=_get_description(UsersCriteria, "p"),
            type=_get_type(UsersCriteria, "p"),
            multiple=_allow_multiple(UsersCriteria, "p"),
        ),
        # page size
        FilterOption(
            key="l",
            description=_get_description(UsersCriteria, "l"),
            type=_get_type(UsersCriteria, "l"),
            multiple=_allow_multiple(UsersCriteria, "l"),
        ),
    ))

    return options


type OptionType = t.Literal["string", "number", "date"]


def _get_description(cls: type, attr_name: str) -> str | None:
    hints = t.get_type_hints(cls, include_extras=True)
    hint = hints.get(attr_name)

    if t.get_origin(hint) is t.Annotated:
        return t.get_args(hint)[1]

    return None


def _get_type(protocol_cls: type, attr_name: str) -> OptionType:
    hints = t.get_type_hints(protocol_cls)
    hint_str = str(hints.get(attr_name, ""))

    if "date" in hint_str:
        return "date"
    if "int" in hint_str or "float" in hint_str or re.search(r"\d", hint_str):
        return "number"

    return "string"


def _allow_multiple(protocol_cls: type, attr_name: str) -> bool:
    hints = t.get_type_hints(protocol_cls)

    if attr_name not in hints:
        return False

    arg_type = hints[attr_name]
    origin = t.get_origin(arg_type)

    if origin is t.Union or (
        hasattr(t, "UnionType") and isinstance(arg_type, t.UnionType)  # pyright: ignore[reportAttributeAccessIssue]
    ):
        args = t.get_args(arg_type)
        return any(t.get_origin(arg) is list or arg is list for arg in args)

    return origin is list or arg_type is list
