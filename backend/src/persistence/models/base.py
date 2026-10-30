"""SQLAlchemy declarative base and shared column mixins.

Every ORM model inherits from ``Base`` (directly or via a mixin) to
gain:

- UUID primary key (UUID as native ``uuid`` type in PG).
- ``created_at`` / ``updated_at`` timestamps (auto-managed).
- ``is_deleted`` soft-delete flag with query filtering support.
- Indexes on ``created_at`` and ``updated_at`` for analytics queries.

Design decisions:
- We use ``uuid.uuid4`` (v4) for globally unique, URL-safe IDs.
- Timestamps are timezone-aware UTC.
- Soft-delete is a boolean column; repositories must filter on it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Boolean, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Centralises metadata so Alembic can autogenerate migrations that
    capture every table in a single pass.
    """

    pass


class UUIDPrimaryKeyMixin:
    """Provides a UUID primary key column.

    All domain tables use this mixin — no integer auto-increment IDs
    anywhere in the schema.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        sort_order=-10,
    )


class TimestampMixin:
    """Provides ``created_at`` and ``updated_at`` auto-managed timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        sort_order=9990,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        sort_order=9991,
    )


class SoftDeleteMixin:
    """Provides ``is_deleted`` soft-delete flag.

    Repositories must apply ``WHERE is_deleted = false`` in all read
    queries.  The ``delete`` operation sets this flag to ``true``
    rather than issuing a SQL ``DELETE``.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        sort_order=9992,
    )


class AuditMixin:
    """Provides ``created_by``, ``updated_by``, ``deleted_by`` audit columns.

    These are nullable UUIDs referencing the user who performed each
    action. For system-generated entities, these may be ``None``.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        sort_order=9993,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        sort_order=9994,
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        sort_order=9995,
    )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Full-featured abstract base combining all mixins.

    Inherit from this class for any table that needs UUID PK,
    timestamps, and soft-delete.  Use ``__abstract__ = True`` so
    SQLAlchemy does not create a table for this class itself.
    """

    __abstract__ = True

    # Note: Indexes on timestamp columns should be defined per-model
    # in __table_args__ with table-specific names to avoid conflicts.
