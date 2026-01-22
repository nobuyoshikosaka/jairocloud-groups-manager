#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing history."""

import typing as t

from flask_login import current_user

from server.db.history import DownloadHistory, Files, UploadHistory
from server.db.utils import db
from server.entities.history_detail import (
    DownloadHistoryData,
    HistoryDataFilter,
    HistoryQuery,
    UploadHistoryData,
)
from server.exc import DatabaseError
from server.services import permission, repositories


if t.TYPE_CHECKING:
    from uuid import UUID


def get_upload_history_data(query: HistoryQuery) -> list[UploadHistoryData]:
    """Get history data for the specified user.

    Args:
        query : The query parameters for filtering history entries.

    Returns:
        list[UploadHistoryData]:

    """
    filters = []
    if current_user.is_system_admin() and query.r:
        filters.append(Files.file_content["repositories"].overlap(query.r))
    if not current_user.is_system_admin():
        repository = permission.get_permitted_repository_ids()
        target_repositories = list(repository & set(query.r)) if query.r else repository
        filters.append(Files.file_content["repositories"].overlap(target_repositories))

    if query.g:
        filters.append(Files.file_content["groups"].overlap(query.g))
    if query.u:
        filters.append(Files.file_content["users"].overlap(query.u))

    if query.o:
        filters.append(UploadHistory.operator_id.in_(query.o))
    if query.s and query.e:
        filters.append(UploadHistory.timestamp.between(query.s, query.e))
    if not current_user.is_system_admin:
        filters.append(UploadHistory.public.is_(True))

    q = db.session.query(UploadHistory, Files).join(
        Files, UploadHistory.file_id == Files.id
    )
    if filters:
        q = q.filter(*filters)
    results = q.all()

    return [UploadHistoryData.model_validate(row) for row in results]


def get_download_history_data(query: HistoryQuery) -> list[DownloadHistoryData]:
    """Get history data for the specified user.

    Args:
        query : The query parameters for filtering history entries.

    Returns:
        list[UploadHistoryData]:
    """
    filters = []

    if current_user.is_system_admin() and query.r:
        filters.append(Files.file_content["repositories"].overlap(query.r))
    if not current_user.is_system_admin():
        repository = permission.get_permitted_repository_ids()
        target_repositories = (
            list(set(repository) & set(query.r)) if query.r else repository
        )
        filters.append(Files.file_content["repositories"].overlap(target_repositories))

    if query.g:
        filters.append(Files.file_content["groups"].overlap(query.g))
    if query.u:
        filters.append(Files.file_content["users"].overlap(query.u))

    if query.o:
        filters.append(DownloadHistory.operator_id.in_(query.o))
    if query.s and query.e:
        filters.append(DownloadHistory.timestamp.between(query.s, query.e))
    if not current_user.is_system_admin:
        filters.append(DownloadHistory.public.is_(True))

    q = db.session.query(DownloadHistory, Files).join(
        Files, DownloadHistory.file_id == Files.id
    )
    if filters:
        q = q.filter(*filters)
    results = q.all()
    return [DownloadHistoryData.model_validate(row) for row in results]


def get_filters(tub: t.Literal["download", "upload"]) -> HistoryDataFilter:
    """Get available filters for download/upload history.

    Args:
        tub (Literal["download", "upload"]): The type of history to get filters for.

    Returns:
        dict[str, list[str]]: The available filters.

    Raises:
        ValueError: If the record is not found.
    """
    if tub == "download":
        history_data = get_download_history_data(HistoryQuery())
    else:
        history_data = get_upload_history_data(HistoryQuery())
    if history_data is None:
        raise ValueError
    operators = [h.operator for h in history_data]
    target_repositories = repositories.search()
    target_groups = [g for h in history_data for g in h.groups]
    target_users = [u for h in history_data for u in h.users]
    return HistoryDataFilter(
        operators=operators,
        target_repositories=target_repositories,
        target_groups=target_groups,
        target_users=target_users,
    )


def update_public_status(
    *, tub: t.Literal["download", "upload"], history_id: UUID, public: bool
) -> bool:
    """Invert the public status of a download/upload history record.

    Args:
        tub (Literal["download", "upload"]): The type of history record.
        history_id (str): The ID of the history record to update.

    Returns:
        bool: public status of a download/upload history record

    Raises:
        ValueError: If the record is not found.
    """
    if tub == "download":
        record = db.session.query(DownloadHistory).get(history_id)
    else:
        record = db.session.query(UploadHistory).get(history_id)

    if record is None:
        raise ValueError(history_id)
    record.public = public
    db.session.commit()
    return record.public


def get_file_path(file_id: UUID) -> str:
    file_path = db.session.query(Files.file_path).filter(Files.id == file_id).scalar()
    if not (file_path and isinstance(file_path, str)):
        raise DatabaseError
    return file_path
