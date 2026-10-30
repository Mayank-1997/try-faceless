"""Token entities — password reset and email verification tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4


class PasswordResetToken:
    """A password reset token issued to a user.

    Attributes:
        id: UUID primary key.
        user_id: The user who requested the reset.
        token_hash: SHA-256 hash of the raw token.
        expires_at: When the token expires (default 1 hour).
        used: Whether the token has been used.
        used_at: Timestamp when the token was used.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime | None = None,
        used: bool = False,
        used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at or datetime.now(timezone.utc) + timedelta(hours=1)
        self.used = used
        self.used_at = used_at
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used, not expired)."""
        if self.used:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now < expires

    def mark_used(self) -> None:
        """Mark the token as used."""
        self.used = True
        self.used_at = datetime.now(timezone.utc)


class EmailVerificationToken:
    """An email verification token issued to a user.

    Attributes:
        id: UUID primary key.
        user_id: The user to verify.
        token_hash: SHA-256 hash of the raw token.
        email: The email address being verified.
        expires_at: When the token expires (default 24 hours).
        used: Whether the token has been used.
        used_at: Timestamp when the token was used.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID,
        token_hash: str,
        email: str,
        expires_at: datetime | None = None,
        used: bool = False,
        used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.token_hash = token_hash
        self.email = email
        self.expires_at = expires_at or datetime.now(timezone.utc) + timedelta(hours=24)
        self.used = used
        self.used_at = used_at
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used, not expired)."""
        if self.used:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now < expires

    def mark_used(self) -> None:
        """Mark the token as used."""
        self.used = True
        self.used_at = datetime.now(timezone.utc)
