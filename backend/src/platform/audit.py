"""Platform Audit Service.

Tracks:
- Authentication
- Publishing
- Generation
- Deletion
- Billing
- Admin changes
- Role changes
- Settings changes

This is the platform-level audit service, complementing the existing
IAM-level ``AuditService`` in ``src/application/services/audit_service.py``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.platform.schema import PlatformAuditAction, PlatformAuditEntry
from src.core.logging import get_logger


class PlatformAuditService:
    """Records platform-level audit events.

    Append-only audit log for all platform operations. Entries are
    never modified or deleted.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._entries: list[PlatformAuditEntry] = []

    def record(
        self,
        *,
        user_id: str = "",
        org_id: str = "",
        action: PlatformAuditAction,
        resource_type: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        correlation_id: str | None = None,
    ) -> PlatformAuditEntry:
        """Record a platform audit entry.

        Args:
            user_id: User who performed the action.
            org_id: Organization context.
            action: Type of action.
            resource_type: Type of resource affected.
            resource_id: ID of the affected resource.
            details: Additional structured details.
            ip_address: Client IP.
            user_agent: Client User-Agent.
            correlation_id: Correlation ID for tracing.

        Returns:
            The created ``PlatformAuditEntry``.
        """
        entry = PlatformAuditEntry(
            user_id=user_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        self._entries.append(entry)
        self._logger.info(
            "platform_audit_recorded",
            action=action.value,
            resource_type=resource_type,
            user_id=user_id,
        )
        return entry

    def get_entries(
        self,
        *,
        user_id: str | None = None,
        org_id: str | None = None,
        action: PlatformAuditAction | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformAuditEntry]:
        """Query audit entries with optional filters.

        Args:
            user_id: Optional user filter.
            org_id: Optional org filter.
            action: Optional action filter.
            resource_type: Optional resource type filter.
            limit: Maximum entries to return.
            offset: Pagination offset.

        Returns:
            List of ``PlatformAuditEntry``.
        """
        result = self._entries

        if user_id is not None:
            result = [e for e in result if e.user_id == user_id]
        if org_id is not None:
            result = [e for e in result if e.org_id == org_id]
        if action is not None:
            result = [e for e in result if e.action == action]
        if resource_type is not None:
            result = [e for e in result if e.resource_type == resource_type]

        # Sort by created_at descending (newest first)
        result = sorted(result, key=lambda x: x.created_at, reverse=True)
        return result[offset:offset + limit]

    def get_entry(self, entry_id: UUID) -> PlatformAuditEntry | None:
        """Get a specific audit entry by ID.

        Args:
            entry_id: The entry ID.

        Returns:
            The ``PlatformAuditEntry`` if found.
        """
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    def get_user_history(self, user_id: str, limit: int = 50) -> list[PlatformAuditEntry]:
        """Get audit history for a user.

        Args:
            user_id: The user ID.
            limit: Maximum entries.

        Returns:
            List of ``PlatformAuditEntry``.
        """
        return self.get_entries(user_id=user_id, limit=limit)

    def get_resource_history(self, resource_type: str, resource_id: str, limit: int = 50) -> list[PlatformAuditEntry]:
        """Get audit history for a specific resource.

        Args:
            resource_type: The resource type.
            resource_id: The resource ID.
            limit: Maximum entries.

        Returns:
            List of ``PlatformAuditEntry``.
        """
        result = [
            e for e in self._entries
            if e.resource_type == resource_type and e.resource_id == resource_id
        ]
        return sorted(result, key=lambda x: x.created_at, reverse=True)[:limit]

    def count_by_action(self) -> dict[str, int]:
        """Count entries by action type.

        Returns:
            Dict mapping action name to count.
        """
        counts: dict[str, int] = {}
        for e in self._entries:
            key = e.action.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def entry_count(self) -> int:
        """Total number of audit entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries (primarily for testing)."""
        self._entries.clear()
