"""User aggregate root — the central identity entity.

This is a pure domain entity with no ORM dependencies. Repositories
convert between this and the SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from src.core.enums import AuthProvider, UserStatus

if TYPE_CHECKING:
    from src.domain.entities.role import Role


class User:
    """User aggregate root.

    Encapsulates identity, authentication state, and profile data.
    Roles are managed through the ``Role`` aggregate via the
    ``UserRepository`` — the User entity holds only role IDs for
    performance; the repository resolves them to ``Role`` objects.

    Attributes:
        id: UUID primary key.
        email: Unique email address.
        username: Unique username.
        first_name: Given name.
        last_name: Family name.
        profile_image_url: URL to avatar image.
        phone: Phone number (optional).
        status: Account lifecycle status.
        auth_provider: How the account was created.
        timezone: IANA timezone string.
        language: Preferred language code.
        email_verified: Whether email has been verified.
        two_factor_enabled: Whether 2FA is active.
        role_ids: Set of role UUIDs assigned to this user.
        last_login_at: Timestamp of last successful login.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        deleted_at: Soft-delete timestamp (None if active).
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        email: str,
        username: str,
        first_name: str = "",
        last_name: str = "",
        profile_image_url: str | None = None,
        phone: str | None = None,
        status: UserStatus = UserStatus.PENDING,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        timezone: str = "UTC",
        language: str = "en",
        email_verified: bool = False,
        two_factor_enabled: bool = False,
        role_ids: set[UUID] | None = None,
        last_login_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.email = email
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.profile_image_url = profile_image_url
        self.phone = phone
        self.status = status
        self.auth_provider = auth_provider
        self.timezone = timezone
        self.language = language
        self.email_verified = email_verified
        self.two_factor_enabled = two_factor_enabled
        self.role_ids: set[UUID] = role_ids or set()
        self.last_login_at = last_login_at
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)
        self.deleted_at = deleted_at

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_deleted(self) -> bool:
        """Check if the user has been soft-deleted."""
        return self.deleted_at is not None

    @property
    def is_locked(self) -> bool:
        """Check if the user account is locked."""
        return self.status == UserStatus.LOCKED

    def activate(self) -> None:
        """Transition the user to active status."""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(dt_timezone.utc)

    def deactivate(self) -> None:
        """Transition the user to inactive status."""
        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now(dt_timezone.utc)

    def suspend(self) -> None:
        """Suspend the user account."""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now(dt_timezone.utc)

    def lock(self) -> None:
        """Lock the user account (e.g. after brute-force attempts)."""
        self.status = UserStatus.LOCKED
        self.updated_at = datetime.now(dt_timezone.utc)

    def soft_delete(self) -> None:
        """Soft-delete the user account."""
        self.status = UserStatus.DELETED
        self.deleted_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    def verify_email(self) -> None:
        """Mark the email as verified."""
        self.email_verified = True
        self.updated_at = datetime.now(dt_timezone.utc)

    def record_login(self) -> None:
        """Record a successful login."""
        self.last_login_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    def update_profile(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        profile_image_url: str | None = None,
        phone: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
    ) -> None:
        """Update profile fields. Only non-None values are changed."""
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if profile_image_url is not None:
            self.profile_image_url = profile_image_url
        if phone is not None:
            self.phone = phone
        if timezone is not None:
            self.timezone = timezone
        if language is not None:
            self.language = language
        self.updated_at = datetime.now(dt_timezone.utc)

    def assign_role(self, role_id: UUID) -> None:
        """Assign a role to the user."""
        self.role_ids.add(role_id)
        self.updated_at = datetime.now(dt_timezone.utc)

    def revoke_role(self, role_id: UUID) -> None:
        """Remove a role from the user."""
        self.role_ids.discard(role_id)
        self.updated_at = datetime.now(dt_timezone.utc)

    def has_role(self, role_id: UUID) -> bool:
        """Check if the user has a specific role."""
        return role_id in self.role_ids

    def to_dict(self) -> dict[str, object]:
        """Serialize to a dictionary (for logging / DTO mapping)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "profile_image_url": self.profile_image_url,
            "phone": self.phone,
            "status": self.status.value,
            "auth_provider": self.auth_provider.value,
            "timezone": self.timezone,
            "language": self.language,
            "email_verified": self.email_verified,
            "two_factor_enabled": self.two_factor_enabled,
            "role_ids": [str(r) for r in self.role_ids],
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
