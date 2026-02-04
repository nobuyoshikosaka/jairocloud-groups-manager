#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing history."""

import typing as t

from datetime import timedelta
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from server.db.history import DownloadHistory, Files, UploadHistory
from server.db.utils import db
from server.entities.history_detail import (
    DownloadHistoryData,
    HistoryQuery,
    HistorySummary,
    Results,
    UploadHistoryData,
)
from server.entities.search_request import FilterOption
from server.entities.summaries import GroupSummary, RepositorySummary, UserSummary
from server.exc import DatabaseError, RecordNotFound
from server.services import permissions, repositories
from server.services.utils import search_queries


def get_upload_history_data(query: HistoryQuery) -> list[UploadHistoryData]:
    """Get history data for the specified user.

    Args:
        query : The query parameters for filtering history entries.

    Returns:
        list[UploadHistoryData]:

    """
    filters: list[t.Any] = []

    if permissions.is_current_user_system_admin():
        target_repositories = query.r or []
    else:
        permitted = permissions.get_permitted_repository_ids()
        target_repositories = (
            list(set(permitted) & set(query.r)) if query.r else permitted
        )

    if target_repositories:
        filters.append(
            or_(*[
                Files.file_content["repositories"].contains([{"id": rid}])
                for rid in target_repositories
            ])
        )

    if query.g:
        filters.append(
            or_(*[
                Files.file_content["groups"].contains([{"id": gid}]) for gid in query.g
            ])
        )

    if query.u:
        filters.append(
            or_(*[
                Files.file_content["users"].contains([{"id": uid}]) for uid in query.u
            ])
        )

    if query.o:
        filters.append(UploadHistory.operator_id.in_(query.o))

    if query.s and query.e:
        filters.append(UploadHistory.timestamp.between(query.s, query.e))
    elif query.s and not query.e:
        start = query.s
        end = start + timedelta(days=1)
        filters.extend((
            UploadHistory.timestamp >= start,
            UploadHistory.timestamp < end,
        ))
    elif query.e and not query.s:
        filters.append(UploadHistory.timestamp <= query.e)

    if not permissions.is_current_user_system_admin():
        filters.append(UploadHistory.public.is_(True))

    stmt = (
        select(
            UploadHistory.id.label("id"),
            UploadHistory.timestamp.label("timestamp"),
            UploadHistory.end_timestamp.label("end_timestamp"),
            UploadHistory.status.label("status"),
            UploadHistory.results.label("results"),
            UploadHistory.operator_id.label("operator_id"),
            UploadHistory.operator_name.label("operator_name"),
            UploadHistory.public.label("public"),
            Files.file_path.label("file_path"),
            Files.file_content.label("file_content"),
        )
        .join(Files, UploadHistory.file_id == Files.id)
        .order_by(desc(UploadHistory.timestamp))
    )

    if filters:
        stmt = stmt.filter(*filters)

    page = query.p or 1
    per_page = query.l or 10
    stmt = stmt.limit(per_page).offset((page - 1) * per_page)

    rows = db.session.execute(stmt).mappings().all()

    data: list[UploadHistoryData] = []
    for r in rows:
        fc: dict[str, t.Any] = r["file_content"] or {}
        repos_raw = fc.get("repositories") or []
        groups_raw = fc.get("groups") or []
        users_raw = fc.get("users") or []

        repositories_list = [RepositorySummary.model_validate(x) for x in repos_raw]
        groups_list = [GroupSummary.model_validate(x) for x in groups_raw]
        users_list = [UserSummary.model_validate(x) for x in users_raw]

        operator = UserSummary(id=r["operator_id"], user_name=r["operator_name"])

        summary, results_list = _parse_upload_results(r["results"])

        payload = {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "end_timestamp": r["end_timestamp"],
            "public": r["public"],
            "operator": operator,
            "status": r["status"],
            "results": results_list,
            "summary": summary,
            "file_path": r["file_path"],
            "repositories": repositories_list,
            "groups": groups_list,
            "users": users_list,
        }
        data.append(UploadHistoryData.model_validate(payload))

    return data


def _parse_upload_results(results_json: t.Any) -> tuple[HistorySummary, list[Results]]:
    def blank_summary() -> HistorySummary:
        return HistorySummary(create=0, update=0, delete=0, skip=0, error=0)

    if not isinstance(results_json, dict):
        return blank_summary(), []

    s = results_json.get("summary") or {}
    try:
        summary = HistorySummary(
            create=int(s.get("create", 0)),
            update=int(s.get("update", 0)),
            delete=int(s.get("delete", 0)),
            skip=int(s.get("skip", 0)),
            error=int(s.get("error", 0)),
        )
    except Exception:
        summary = blank_summary()

    items = results_json.get("results") or []
    result_list: list[Results] = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                payload = {
                    "user_id": it.get("id"),
                    "eppn": it.get("eppn"),
                    "user_name": it.get("userName"),
                    "group": it.get("group") or [],
                    "status": it.get("status"),
                    "code": it.get("code"),
                }
                result_list.append(Results.model_validate(payload))

    return summary, result_list


def get_download_history_data(query: HistoryQuery) -> list[DownloadHistoryData]:
    """Get history data for the specified user.

    Args:
        query : The query parameters for filtering history entries.

    Returns:
        list[DownloadHistoryData]:

    """
    filters: list[t.Any] = []

    if permissions.is_current_user_system_admin():
        target_repositories = query.r or []
    else:
        permitted = permissions.get_permitted_repository_ids()
        target_repositories = (
            list(set(permitted) & set(query.r)) if query.r else permitted
        )

    if target_repositories:
        filters.append(
            or_(*[
                Files.file_content["repositories"].contains([{"id": rid}])
                for rid in target_repositories
            ])
        )

    if query.g:
        filters.append(
            or_(*[
                Files.file_content["groups"].contains([{"id": gid}]) for gid in query.g
            ])
        )

    if query.u:
        filters.append(
            or_(*[
                Files.file_content["users"].contains([{"id": uid}]) for uid in query.u
            ])
        )

    if query.o:
        filters.append(DownloadHistory.operator_id.in_(query.o))

    if query.s and query.e:
        filters.append(DownloadHistory.timestamp.between(query.s, query.e))
    elif query.s and not query.e:
        start = query.s
        end = start + timedelta(days=1)
        filters.extend((
            DownloadHistory.timestamp >= start,
            DownloadHistory.timestamp < end,
        ))
    elif query.e and not query.s:
        filters.append(DownloadHistory.timestamp <= query.e)

    if not permissions.is_current_user_system_admin():
        filters.append(DownloadHistory.public.is_(True))

    if not query.i:
        filters.append(DownloadHistory.parent_id.is_(None))
        parent_ids: list[UUID] = []
    else:
        parent_ids = [UUID(str(s)) for s in query.i]
        filters.append(DownloadHistory.parent_id.in_(parent_ids))

    stmt = (
        select(
            DownloadHistory.id.label("id"),
            DownloadHistory.timestamp.label("timestamp"),
            DownloadHistory.operator_id.label("operator_id"),
            DownloadHistory.operator_name.label("operator_name"),
            DownloadHistory.public.label("public"),
            DownloadHistory.parent_id.label("parent_id"),
            Files.file_path.label("file_path"),
            Files.file_content.label("file_content"),
        )
        .join(Files, DownloadHistory.file_id == Files.id)
        .order_by(desc(DownloadHistory.timestamp))
    )
    if filters:
        stmt = stmt.filter(*filters)

    page = query.p or 1
    per_page = query.l or 10
    stmt = stmt.limit(per_page).offset((page - 1) * per_page)

    rows = db.session.execute(stmt).mappings().all()

    children_counts_map: dict[UUID, int] = {}
    if (not query.i) and rows:
        pid_list = [r["id"] for r in rows]
        cnt_stmt = (
            select(
                DownloadHistory.parent_id.label("pid"),
                func.count().label("cnt"),
            )
            .select_from(DownloadHistory)
            .where(DownloadHistory.parent_id.in_(pid_list))
            .group_by(DownloadHistory.parent_id)
        )
        cnt_rows = db.session.execute(cnt_stmt).mappings().all()
        children_counts_map = {r["pid"]: int(r["cnt"]) for r in cnt_rows}

    data: list[DownloadHistoryData] = []
    for r in rows:
        fc: dict[str, t.Any] = r["file_content"] or {}
        repos_raw = fc.get("repositories") or []
        groups_raw = fc.get("groups") or []
        users_raw = fc.get("users") or []

        repositories = [RepositorySummary.model_validate(x) for x in repos_raw]
        groups = [GroupSummary.model_validate(x) for x in groups_raw]
        users = [UserSummary.model_validate(x) for x in users_raw]

        operator = UserSummary(id=r["operator_id"], user_name=r["operator_name"])

        payload = {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "operator": operator,
            "public": r["public"],
            "parent_id": r["parent_id"],
            "file_path": r["file_path"],
            "repositories": repositories,
            "groups": groups,
            "users": users,
            "children_count": (
                children_counts_map.get(r["id"], 0) if not query.i else 0
            ),
        }
        data.append(DownloadHistoryData.model_validate(payload))

    return data


def get_filters(tub: t.Literal["download", "upload"]) -> list[FilterOption]:
    """Get available filters for download/upload history.

    Args:
        tub (Literal["download", "upload"]): The type of history to get filters for.

    Returns:
        dict[str, list[str]]: The available filters.

    Raises:
        RecordNotFound: If the record is not found.
    """
    if tub == "download":
        history_data = get_download_history_data(HistoryQuery())
    else:
        history_data = get_upload_history_data(HistoryQuery())

    if history_data is None:
        error = f"{tub} history data is not found"
        raise RecordNotFound(error)

    operators = {h.operator.id: h.operator for h in history_data if h.operator}
    repository_ids = permissions.get_permitted_repository_ids()
    query = search_queries.make_criteria_object("repositories", i=list(repository_ids))
    target_repositories = repositories.search(query).resources
    unique_groups = {g.id: g for h in history_data for g in h.groups}
    unique_users = {u.id: u for h in history_data for u in h.users}

    operator_items: list[t.Mapping[str, str]] = [
        {op.id: op.user_name or ""} for op in operators.values()
    ]

    repository_items: list[t.Mapping[str, str]] = [
        {r.id: r.service_name or ""} for r in target_repositories
    ]

    group_items: list[t.Mapping[str, str]] = [
        {g.id: g.display_name or ""} for g in unique_groups.values()
    ]

    user_items: list[t.Mapping[str, str]] = [
        {u.id: u.user_name or ""} for u in unique_users.values()
    ]

    filters: list[FilterOption] = [
        FilterOption(
            key="o",
            description="operator",
            type="string",
            multiple=True,
            items=operator_items,
        ),
        FilterOption(
            key="r",
            description="repositories",
            type="string",
            multiple=True,
            items=repository_items,
        ),
        FilterOption(
            key="g",
            description="groups",
            type="string",
            multiple=True,
            items=group_items,
        ),
        FilterOption(
            key="u",
            description="users",
            type="string",
            multiple=True,
            items=user_items,
        ),
    ]

    return filters


def update_public_status(
    *, tub: t.Literal["download", "upload"], history_id: UUID, public: bool
) -> bool:
    """Invert the public status of a download/upload history record.

    Args:
        tub (Literal["download", "upload"]): The type of history record.
        history_id (str): The ID of the history record to update.
        public (bool):Value to update.

    Returns:
        bool: public status of a download/upload history record

    Raises:
        RecordNotFound: If the record is not found.
        DatabaseError: If a database operation fails.
    """
    try:
        table = DownloadHistory if tub == "download" else UploadHistory

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
        file = db.session.query(Files).filter(Files.id == file_id).first()
    except SQLAlchemyError as exc:
        error = "Failed to retrieve the file path due to a database error."
        raise DatabaseError(error) from exc

    if not file:
        error = f"File with ID {file_id} not found."
        raise RecordNotFound(error)

    return file.file_path
