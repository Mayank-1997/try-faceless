"""Session entity — tracks an active user session."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.enums import SessionStatus


class UserSession:
    """An active or historical user session.

    Tracks device, browser, OS, and IP information for security and
    session management. Users can view and revoke individual sessions.

    Attributes:
        id: UUID primary key.
        user_id: The user who owns this session.
        token_jti: JWT ID of the access token (for revocation lookup).
        refresh_token_id: ID of the associated refresh token.
        device: Device name (e.g. "iPhone 15 Pro").
        browser: Browser name and version.
        operating_system: OS name.
        ip_address: Last known IP address.
        user_agent: Raw User-Agent header.
        status: Session lifecycle status.
        created_at: When the session was created.
        last_activity_at: Timestamp of last activity.
        expires_at: When the session expires.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID,
        token_jti: str,
        refresh_token_id: UUID | None = None,
        device: str = "",
        browser: str = "",
        operating_system: str = "",
        ip_address: str = "",
        user_agent: str = "",
        status: SessionStatus = SessionStatus.ACTIVE,
        created_at: datetime | None = None,
        last_activity_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.token_jti = token_jti
        self.refresh_token_id = refresh_token_id
        self.device = device
        self.browser = browser
        self.operating_system = operating_system
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_activity_at = last_activity_at or datetime.now(timezone.utc)
        self.expires_at = expires_at

    @property
    def is_active(self) -> bool:
        """Check if the session is active."""
        return self.status == SessionStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def revoke(self) -> None:
        """Revoke the session."""
        self.status = SessionStatus.REVOKED

    def update_activity(self, ip_address: str | None = None) -> None:
        """Update the last activity timestamp."""
        self.last_activity_at = datetime.now(timezone.utc)
        if ip_address:
            self.ip_address = ip_address

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "device": self.device,
            "browser": self.browser,
            "operating_system": self.operating_system,
            "ip_address": self.ip_address,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
