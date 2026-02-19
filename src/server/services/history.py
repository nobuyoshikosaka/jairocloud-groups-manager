#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing history."""

import typing as t

from datetime import date, timedelta
from types import SimpleNamespace
from uuid import UUID

from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from server.const import DEFAULT_SEARCH_COUNT
from server.db.history import DownloadHistory, Files, UploadHistory
from server.db.utils import db
from server.entities.history_detail import (
    DownloadHistoryData,
    UploadHistoryData,
)
from server.entities.search_request import FilterOption, SearchResult
from server.entities.summaries import UserSummary
from server.exc import DatabaseError, InvalidQueryError, RecordNotFound

from .utils import (
    get_permitted_repository_ids,
    is_current_user_system_admin,
)


if t.TYPE_CHECKING:
    from sqlalchemy import sql

    type FilterArg = sql._typing.ColumnExpressionArgument[bool]  # noqa: SLF001


def get_upload_history_data(
    criteria: HistoryCriteria,
) -> SearchResult[UploadHistoryData]:
    """Get history data for the specified user.

    Args:
        criteria : The search criteria for filtering history entries.

    Returns:
        SearchResult: upload history data with pagination.

    """
    filters = _build_filters_for_history(criteria, history_type="upload")

    base_stmt = select(UploadHistory, Files).join(UploadHistory.file).filter(*filters)
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.session.execute(count_stmt).scalar_one()

    if criteria.d == "desc":
        stmt = base_stmt.order_by(UploadHistory.timestamp.desc())
    else:
        stmt = base_stmt.order_by(UploadHistory.timestamp.asc())

    page = criteria.p or 1
    page_size = criteria.l or DEFAULT_SEARCH_COUNT
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)

    rows = db.session.execute(stmt).all()
    data = [
        {
            **history.__dict__,
            "operator": {"id": history.operator_id, "user_name": history.operator_name},
            "summary": history.results.get("summary"),
            "file_id": file.id,
            "file_path": file.file_path,
            "repository_count": len(file.file_content.get("repositories", [])),
            "group_count": len(file.file_content.get("groups", [])),
            "user_count": len(file.file_content.get("users", [])),
        }
        for history, file in t.cast("t.Sequence[tuple[UploadHistory, Files]]", rows)
    ]

    return SearchResult[UploadHistoryData].model_validate(
        {
            "total": total,
            "page_size": page_size,
            "offset": offset,
            "resources": data,
        },
        extra="ignore",
    )


def _build_filters_for_history(
    criteria: HistoryCriteria, history_type: t.Literal["upload", "download"]
) -> list[FilterArg]:
    history_model = UploadHistory if history_type == "upload" else DownloadHistory
    filters: list[FilterArg] = []

    if is_current_user_system_admin():
        filters.append(
            or_(*[
                Files.file_content["repositories"].contains([{"id": rid}])
                for rid in criteria.r or []
            ])
        )
    else:
        filters.append(history_model.public.is_(True))
        permitted = get_permitted_repository_ids()
        target_repositories = permitted & set(criteria.r) if criteria.r else permitted
        filters.append(
            or_(*[
                Files.file_content["repositories"].contains([{"id": rid}])
                for rid in target_repositories
            ])
        )

    if criteria.g:
        filters.append(
            or_(*[
                Files.file_content["groups"].contains([{"id": gid}])
                for gid in criteria.g
            ])
        )

    if criteria.u:
        filters.append(
            or_(*[
                Files.file_content["users"].contains([{"id": uid}])
                for uid in criteria.u
            ])
        )

    if criteria.o:
        filters.append(history_model.operator_id.in_(criteria.o))

    if criteria.s and criteria.e:
        filters.append(history_model.timestamp.between(criteria.s, criteria.e))
    elif criteria.s and not criteria.e:
        start = criteria.s
        end = start + timedelta(days=1)
        filters.extend((
            history_model.timestamp >= start,
            history_model.timestamp < end,
        ))
    elif criteria.e and not criteria.s:
        filters.append(history_model.timestamp <= criteria.e)

    if history_type == "download":
        if not criteria.i:
            filters.append(DownloadHistory.parent_id.is_(None))
        else:
            parent_id = UUID(criteria.i)
            filters.append(DownloadHistory.parent_id == parent_id)

    return filters


def get_download_history_data(
    criteria: HistoryCriteria,
) -> SearchResult[DownloadHistoryData]:
    """Get history data for the specified user.

    Args:
        criteria : The search criteria for filtering history entries.

    Returns:
        SearchResult: download history data with pagination.

    """
    filters = _build_filters_for_history(criteria, history_type="download")

    base_stmt = (
        select(DownloadHistory, Files).join(DownloadHistory.file).filter(*filters)
    )
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.session.execute(count_stmt).scalar_one()

    subq = (
        select(func.count(DownloadHistory.id))
        .where(DownloadHistory.parent_id == DownloadHistory.id)
        .scalar_subquery()
    )
    stmt = base_stmt.add_columns(subq)

    if criteria.d == "desc":
        stmt = stmt.order_by(DownloadHistory.timestamp.desc())
    else:
        stmt = stmt.order_by(DownloadHistory.timestamp.asc())

    page = criteria.p or 1
    page_size = criteria.l or DEFAULT_SEARCH_COUNT
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)

    rows = db.session.execute(stmt).all()
    data = [
        {
            **history.__dict__,
            "operator": {"id": history.operator_id, "user_name": history.operator_name},
            "file_id": file.id,
            "file_path": file.file_path,
            "repository_count": len(file.file_content.get("repositories", [])),
            "group_count": len(file.file_content.get("groups", [])),
            "user_count": len(file.file_content.get("users", [])),
            "children_count": children_count,
        }
        for history, file, children_count in t.cast(
            "t.Sequence[tuple[DownloadHistory, Files, int]]", rows
        )
    ]
    return SearchResult[DownloadHistoryData].model_validate(
        {
            "total": total,
            "pageSize": page_size,
            "offset": offset,
            "resources": data,
        },
        extra="ignore",
    )


def get_filters() -> list[FilterOption]:
    """Get available filters for history.

    Returns:
        list[FilterOption]: The available filters.
    """
    filters: list[FilterOption] = [
        FilterOption(
            key="o",
            description="operator",
            type="string",
            multiple=True,
            items=[],
        ),
        FilterOption(
            key="r",
            description="repositories",
            type="string",
            multiple=True,
            items=[],
        ),
        FilterOption(
            key="g",
            description="groups",
            type="string",
            multiple=True,
            items=[],
        ),
        FilterOption(
            key="u",
            description="users",
            type="string",
            multiple=True,
            items=[],
        ),
    ]

    return filters


def get_filter_option(
    tab: t.Literal["download", "upload"], key: str, criteria: OperatorsCriteria
) -> SearchResult[UserSummary]:
    """Get filter options for history data.

    Args:
        tab (Literal["download", "upload"]): Type of history (download or upload)
        key (str): The key of the filter option to retrieve.
        criteria (OperatorsCriteria): The search criteria for filtering operators.

    Returns:
        SearchResult: filter options for history data.

    Raises:
        InvalidQueryError: If the filter key is invalid.
    """
    table = UploadHistory if tab == "upload" else DownloadHistory
    if key == "o":
        stmt = select(table.operator_id, table.operator_name).distinct()
        page = criteria.p or 1
        page_size = criteria.l or DEFAULT_SEARCH_COUNT
        offset = (page - 1) * page_size
        stmt = stmt.limit(page_size).offset(offset)

        results = db.session.execute(stmt).all()
        items = [
            UserSummary(id=operator_id, user_name=operator_name)
            for operator_id, operator_name in results
        ]
        return SearchResult(
            resources=items, total=0, page_size=page_size, offset=offset
        )

    error = f"Unsupported criteria type: {type(criteria)}"
    current_app.logger.error(error)
    raise InvalidQueryError(error)


def update_public_status(
    *, tab: t.Literal["download", "upload"], history_id: UUID, public: bool
) -> bool:
    """Invert the public status of a download/upload history record.

    Args:
        tab (Literal["download", "upload"]): The type of history record.
        history_id (UUID): The ID of the history record to update.
        public (bool):Value to update.

    Returns:
        bool: public status of a download/upload history record

    Raises:
        RecordNotFound: If the record is not found.
        DatabaseError: If a database operation fails.
    """
    try:
        table = DownloadHistory if tab == "download" else UploadHistory

        record = db.session.get(table, history_id)
        if record is None:
            error = f"{history_id} is not found"
            raise RecordNotFound(error)

        record.public = public
    except SQLAlchemyError as exc:
        error = "Failed to update the public status due to a database error."
        raise DatabaseError(error) from exc
    db.session.commit()
    return record.public


def get_file_path(file_id: UUID) -> str:
    """Get the file path for the given file ID.

    Args:
        file_id (UUID): The ID of the file.

    Returns:
        str: The file path.

    Raises:
        DatabaseError: If the file path could not be retrieved.
        RecordNotFound: If the file is not found.
    """
    try:
        file = db.session.get(Files, file_id)
    except SQLAlchemyError as exc:
        error = "Failed to retrieve the file path due to a database error."
        raise DatabaseError(error) from exc

    if not file:
        error = f"File with ID {file_id} not found."
        raise RecordNotFound(error)

    return file.file_path


class HistoryCriteria(t.Protocol):
    """Criteria for searching history records."""

    i: t.Annotated[str | None, "history ID (parent ID)"]
    """Filter by parent history ID."""

    r: t.Annotated[list[str] | None, "repositories"]
    """Filter by affiliated repository IDs."""

    g: t.Annotated[list[str] | None, "groups"]
    """Filter by affiliated group IDs."""

    u: t.Annotated[list[str] | None, "users"]
    """Filter by affiliated user IDs."""

    o: t.Annotated[list[str] | None, "operators"]
    """Filter by operator user IDs."""

    s: t.Annotated[date | None, "last modified date (from)"]
    """Filter by last modified date (from)."""

    e: t.Annotated[date | None, "last modified date (to)"]
    """Filter by last modified date (to)."""

    d: t.Annotated[t.Literal["asc", "desc"] | None, "sort order"]
    """Sort order: 'asc' (ascending) or 'desc' (descending)."""

    p: t.Annotated[int | None, "page number"]
    """Page number to retrieve."""

    l: t.Annotated[int | None, "page size"]  # noqa: E741
    """Page size (number of items per page)."""


class OperatorsCriteria(t.Protocol):
    """Criteria for searching operators in history records."""

    q: t.Annotated[str | None, "query"] = None
    """Search term to filter operators."""

    p: t.Annotated[int | None, "page number"] = None
    """Page number to retrieve."""

    l: t.Annotated[int | None, "page size"] = None  # noqa: E741
    """Page size (number of items per page)."""


def empty_history_criteria() -> HistoryCriteria:
    """Create an empty HistoryCriteria object.

    Returns:
        HistoryCriteria: An empty HistoryCriteria object.
    """
    hints = t.get_type_hints(HistoryCriteria)
    attrs = dict.fromkeys(hints)
    return t.cast("HistoryCriteria", SimpleNamespace(**attrs))
