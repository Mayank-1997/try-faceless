"""API Key entity — hashed API keys for programmatic access."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.enums import ApiKeyStatus


class ApiKey:
    """An API key for programmatic (SDK) access.

    The raw key is shown to the user exactly once at creation time.
    Only the SHA-256 hash is stored. The key format is:
    ``avs_<base62_random>``.

    Attributes:
        id: UUID primary key.
        user_id: Owner of the key.
        name: Human-readable name for the key.
        key_hash: SHA-256 hash of the raw key.
        key_prefix: First 8 characters of the raw key (for display).
        status: Key lifecycle status.
        scopes: List of permission scopes (e.g. ["project.read", "video.generate"]).
        expires_at: Optional expiration timestamp.
        last_used_at: Timestamp of last API call with this key.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID,
        name: str,
        key_hash: str,
        key_prefix: str,
        status: ApiKeyStatus = ApiKeyStatus.ACTIVE,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        last_used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.name = name
        self.key_hash = key_hash
        self.key_prefix = key_prefix
        self.status = status
        self.scopes = scopes or []
        self.expires_at = expires_at
        self.last_used_at = last_used_at
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        """Check if the key is active and not expired."""
        if self.status != ApiKeyStatus.ACTIVE:
            return False
        if self.expires_at is not None:
            return datetime.now(timezone.utc) < self.expires_at
        return True

    def revoke(self) -> None:
        """Revoke the key."""
        self.status = ApiKeyStatus.REVOKED

    def record_usage(self) -> None:
        """Record that the key was used."""
        self.last_used_at = datetime.now(timezone.utc)

    def has_scope(self, scope: str) -> bool:
        """Check if the key has a specific scope."""
        if not self.scopes:
            return True  # No scope restriction = full access
        return scope in self.scopes

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "key_prefix": self.key_prefix,
            "status": self.status.value,
            "scopes": self.scopes,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
