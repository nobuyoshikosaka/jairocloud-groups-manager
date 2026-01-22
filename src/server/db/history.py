#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Model definition for history tables."""

from __future__ import annotations

import typing as t
import uuid  # noqa: TC003

from datetime import datetime  # noqa: TC003

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from .base import db


class Files(db.Model):
    """Model for a files stored as a key-value pair.

    Attributes:
        id (UUID): id (primary key).
        file_path (str): file path.
        location (str): file location.
        file_content (dict[str, t.Any]): file content mapped JSONB.
    """

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
    )
    """File identifier (UUID)."""

    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    """File path."""

    file_content: Mapped[dict[str, t.Any]] = mapped_column(
        MutableDict.as_mutable(JSON().with_variant(postgresql.JSONB, "postgresql")),
    )
    """Repositories, groups, and users contained in the file."""

    __table_args__ = (
        Index("ix_files_file_content", "file_content", postgresql_using="gin"),
    )


class DownloadHistory(db.Model):
    """Model for a download history stored as a key-value pair."""

    __tablename__ = "download_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
    )
    """History record ID (uuid.UUID)."""

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.timezone("UTC", func.now()),
    )
    """Download timestamp in UTC (TIMESTAMPTZ(6); server default UTC now)."""

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("files.id"),
        nullable=False,
    )
    """Foreign key to files.id (downloaded file ID)."""

    operator_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    """Operator identifier (VARCHAR(50); indexed)."""

    operator_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    """Operator name (VARCHAR(50))."""

    public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    """Public/private flag (BOOLEAN NOT NULL DEFAULT true)."""

    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("download_history.id"),
        nullable=True,
    )
    """Self-referencing FK to the first download record (nullable)."""


class UploadHistory(db.Model):
    """Model for a upload history stored as a key-value pair."""

    __tablename__ = "upload_history"

    type Status = t.Literal["S", "P", "F"]
    """Allowed status values for the upload history.
    - 'S': Success
    - 'P': In Progress
    - 'F': Failed
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
    )
    """History record ID (UUID)."""

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.timezone("UTC", func.now()),
    )
    """Upload start timestamp in UTC (TIMESTAMPTZ(6); server default UTC now)."""

    end_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """Upload end timestamp in UTC (TIMESTAMPTZ(6); nullable)."""

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("files.id"),
        nullable=False,
    )
    """Foreign key to files.id (uploaded file ID)."""

    operator_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    """Operator identifier (VARCHAR(50); indexed)."""

    operator_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    """Operator name (VARCHAR(50))."""

    public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    """Public/private flag (BOOLEAN NOT NULL DEFAULT true)."""

    status: Mapped[Status] = mapped_column(
        String(1),
        nullable=False,
    )
    """Status: 'S' (success), 'F' (failure), 'P' (in progress)."""

    results: Mapped[dict[str, t.Any]] = mapped_column(
        MutableDict.as_mutable(JSON().with_variant(postgresql.JSONB, "postgresql")),
        nullable=True,
    )
    """import result data."""

    __table_args__ = (
        CheckConstraint(
            status.in_(t.get_args(Status.__value__)),
            name="status",
        ),
        Index("ix_upload_history_results", "results", postgresql_using="gin"),
    )
