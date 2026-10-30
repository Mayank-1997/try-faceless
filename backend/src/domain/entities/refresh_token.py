"""Refresh token entity — tracks JWT refresh tokens for rotation."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4


class RefreshToken:
    """A refresh token for JWT token rotation.

    When a user logs in, an access token and a refresh token are issued.
    When the access token expires, the client uses the refresh token to
    get a new access token (and a new refresh token — rotation).
    The old refresh token is revoked.

    Attributes:
        id: UUID primary key.
        user_id: Owner of the token.
        token_hash: SHA-256 hash of the raw refresh token.
        session_id: Associated session ID.
        expires_at: When the token expires.
        revoked: Whether the token has been revoked.
        revoked_at: Timestamp of revocation.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID,
        token_hash: str,
        session_id: UUID | None = None,
        expires_at: datetime | None = None,
        revoked: bool = False,
        revoked_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.token_hash = token_hash
        self.session_id = session_id
        self.expires_at = expires_at
        self.revoked = revoked
        self.revoked_at = revoked_at
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not revoked, not expired)."""
        if self.revoked:
            return False
        if self.expires_at is not None:
            now = datetime.now(timezone.utc)
            expires = self.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return now < expires
        return True

    def revoke(self) -> None:
        """Revoke the token."""
        self.revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
