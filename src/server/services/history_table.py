#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Services for managing history table."""

import typing as t

from datetime import UTC, datetime
from uuid import UUID  # noqa: TC003

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from server.db import db
from server.db.history import Files, UploadHistory
from server.exc import InvalidQueryError, RecordNotFound


def get_upload_by_id(history_id: UUID) -> UploadHistory | None:
    """Get an upload history record by its ID.

    Args:
        history_id (UUID): The ID of the upload history.

    Returns:
        UploadHistory | None: The upload history record, or None if not found.
    """
    return db.session.get(
        UploadHistory, history_id, options=[selectinload(UploadHistory.file)]
    )


def get_upload_results(history_id: UUID, attribute: str) -> dict:
    """Get upload results by history ID and attribute.

    Args:
        history_id (UUID): The ID of the upload history.
        attribute (str): The attribute to retrieve from results.

    Returns:
        dict: The upload results for the specified attribute.
    """
    result = (
        db.session
        .query(UploadHistory.results[attribute])
        .filter(UploadHistory.id == history_id)
        .first()
    )
    return result[0] if result else {}


def get_paginated_upload_results(
    history_id: UUID, offset: int, size: int, status_filter: list[str]
) -> list[dict]:
    """Get paginated upload results with optional status filtering.

    Args:
        history_id (UUID): The ID of the upload history.
        offset (int): The page number (1-based).
        size (int): The number of items per page.
        status_filter (list[str]): List of status strings to filter results.

    Returns:
        list[dict]: A list of upload result items.

    Raises:
        InvalidQueryError: If offset or size is less than 1.
    """
    if offset < 1 or size < 1:
        error_message = "Invalid offset or size"
        raise InvalidQueryError(error_message)

    elements = func.jsonb_array_elements(
        UploadHistory.results["results"]
    ).column_valued("item")
    query = (
        db.session
        .query(elements)
        .select_from(UploadHistory)
        .filter(UploadHistory.id == history_id)
    )

    if status_filter:
        query = query.filter(elements.op("->>")("status").in_(status_filter))

    offset_val = (offset - 1) * size

    raw_results = query.limit(size).offset(offset_val).all()

    return [r[0] for r in raw_results]


def create_upload(
    file_id: UUID, results: dict, operator_id: str, operator_name: str
) -> UUID:
    """Create a new upload history record.

    Args:
        file_id (UUID): The ID of the associated file.
        results (dict): The results of the upload operation.
        operator_id (str): The ID of the operator performing the upload.
        operator_name (str): The name of the operator performing the upload.

    Returns:
        UUID: The ID of the newly created upload history record.
    """
    history_record = UploadHistory()
    history_record.file_id = file_id
    history_record.results = {
        "summary": results.get("summary", {}),
        "items": results.get("results", []),
        "missing_users": results.get("missing_users", []),
    }
    history_record.operator_id = operator_id
    history_record.operator_name = operator_name
    db.session.add(history_record)
    db.session.commit()
    return history_record.id


def update_upload_status(
    history_id: UUID,
    status: t.Literal["P", "S", "F"],
    new_results: dict | None = None,
    file_id: UUID | None = None,
) -> None:
    """Update the status of an upload history record.

    Args:
        history_id (UUID): The ID of the history record to update.
        status (Literal["P", "S", "F"]):
          The new status ("P": Progress, "S": Success, "F": Failed).
        new_results (dict | None): New results to update, if any.
        file_id (UUID | None): New file ID to update, if any.
    """
    obj = db.session.get(UploadHistory, history_id)
    if obj is None:
        return
    if new_results:
        obj.results = {
            "summary": new_results.get("summary", {}),
            "items": new_results.get("results", []),
            "missing_users": new_results.get("missing_users", []),
        }

    obj.status = status
    now = datetime.now(UTC)
    if status == "P":
        obj.timestamp = now
    else:
        obj.end_timestamp = now

    if file_id:
        obj.file_id = file_id

    db.session.commit()


def get_history_by_file_id(file_id: UUID) -> UploadHistory:
    """Get a history record by its file ID.

    Args:
        file_id (UUID): The ID of the file.

    Returns:
        UploadHistory: The history record.

    Raises:
        RecordNotFound: If no history record is found for the given file ID.
    """
    result = db.session.query(UploadHistory).filter_by(file_id=file_id).one_or_none()
    if result is None:
        error = f"History not found for file_id: {file_id}"
        current_app.logger.error(error)
        raise RecordNotFound(error)
    return result


def get_file_by_id(file_id: UUID) -> Files:
    """Get a file record by its ID.

    Args:
        file_id (UUID): The ID of the file to retrieve.

    Returns:
        Files: The file record.
    """
    return db.session.query(Files).filter_by(id=file_id).one()


def delete_file_by_id(file_id: UUID) -> None:
    """Delete a file record by its ID.

    Args:
        file_id (UUID): The ID of the file to delete.
    """
    Files.query.filter(Files.id == file_id).delete()
    db.session.commit()


def create_file(
    file_path: str, file_content: dict, file_id: UUID | None = None
) -> UUID:
    """Create or update a file record.

    Args:
        file_path (str): The path of the file.
        file_content (dict): The content of the file.
        file_id (UUID | None): The ID of the file to update.

    Returns:
        UUID: The ID of the created or updated file.
    """
    file_record = Files()
    if file_id:
        file_record.id = file_id
    file_record.file_path = str(file_path)
    file_record.file_content = {
        "repositories": file_content.get("repositories", []),
        "groups": file_content.get("groups", []),
        "users": file_content.get("users", []),
    }
    db.session.add(file_record)
    db.session.commit()
    return file_record.id
