"""Audit log entity — immutable record of security-relevant events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import AuditAction


class AuditLog:
    """An immutable audit log entry.

    Records security-relevant events for compliance and forensics.
    Entries are never updated or deleted — they are append-only.

    Attributes:
        id: UUID primary key.
        user_id: The user who performed the action (None for system events).
        action: The type of action performed.
        resource_type: The type of resource affected (e.g. "user", "api_key").
        resource_id: ID of the affected resource.
        ip_address: IP address of the requester.
        user_agent: User-Agent header of the request.
        details: Additional structured details.
        correlation_id: Correlation ID for tracing.
        created_at: When the event occurred.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        action: AuditAction,
        resource_type: str = "",
        resource_id: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details or {}
        self.correlation_id = correlation_id
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
