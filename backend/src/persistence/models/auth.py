"""SQLAlchemy ORM models for the IAM / authentication domain.

These models map to database tables and are used exclusively by
repository implementations. Domain entities are the public interface;
ORM models are never exposed to the application or presentation layers.

Tables:
- users
- roles
- permissions
- user_roles (association)
- role_permissions (association)
- refresh_tokens
- api_keys
- user_sessions
- password_reset_tokens
- email_verification_tokens
- user_preferences
- audit_logs
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Column,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import Base, BaseModel, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Association tables (many-to-many)
# ---------------------------------------------------------------------------
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Index("ix_user_roles_user_id", "user_id"),
    Index("ix_user_roles_role_id", "role_id"),
    extend_existing=True,
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", PGUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Index("ix_role_permissions_role_id", "role_id"),
    Index("ix_role_permissions_permission_id", "permission_id"),
    extend_existing=True,
)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserModel(BaseModel):
    """ORM model for the ``users`` table."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_email_verified", "email_verified"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    last_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(30), default="local", server_default="local", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", server_default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["RoleModel"]] = relationship(
        "RoleModel",
        secondary=user_roles,
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class RoleModel(BaseModel):
    """ORM model for the ``roles`` table."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    permissions: Mapped[list["PermissionModel"]] = relationship(
        "PermissionModel",
        secondary=role_permissions,
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
class PermissionModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``permissions`` table.

    Permissions are immutable system-defined entries — no soft-delete
    or timestamp mixin needed beyond creation.
    """

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    resource: Mapped[str] = mapped_column(String(50), default="", server_default="")
    action: Mapped[str] = mapped_column(String(50), default="", server_default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Refresh Tokens
# ---------------------------------------------------------------------------
class RefreshTokenModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``refresh_tokens`` table."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_revoked", "revoked"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
class ApiKeyModel(BaseModel):
    """ORM model for the ``api_keys`` table."""

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# User Sessions
# ---------------------------------------------------------------------------
class UserSessionModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``user_sessions`` table."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    refresh_token_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    device: Mapped[str] = mapped_column(String(200), default="", server_default="")
    browser: Mapped[str] = mapped_column(String(200), default="", server_default="")
    operating_system: Mapped[str] = mapped_column(String(100), default="", server_default="")
    ip_address: Mapped[str] = mapped_column(String(45), default="", server_default="")
    user_agent: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Password Reset Tokens
# ---------------------------------------------------------------------------
class PasswordResetTokenModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``password_reset_tokens`` table."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Email Verification Tokens
# ---------------------------------------------------------------------------
class EmailVerificationTokenModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``email_verification_tokens`` table."""

    __tablename__ = "email_verification_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------
class UserPreferencesModel(Base):
    """ORM model for the ``user_preferences`` table (1:1 with users)."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    theme: Mapped[str] = mapped_column(String(20), default="system", server_default="system")
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    default_ai_model: Mapped[str] = mapped_column(String(100), default="gemini-2.5-pro", server_default="gemini-2.5-pro")
    preferred_llm: Mapped[str] = mapped_column(String(50), default="gemini", server_default="gemini")
    preferred_voice: Mapped[str] = mapped_column(String(50), default="google_tts", server_default="google_tts")
    preferred_image_provider: Mapped[str] = mapped_column(String(50), default="imagen", server_default="imagen")
    preferred_video_provider: Mapped[str] = mapped_column(String(50), default="veo", server_default="veo")
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------
class AuditLogModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``audit_logs`` table (append-only)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), default="", server_default="")
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), default="", server_default="")
    user_agent: Mapped[str] = mapped_column(Text, default="", server_default="")
    details: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded dict
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
