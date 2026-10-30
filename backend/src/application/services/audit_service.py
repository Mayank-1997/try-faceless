"""Audit service — records security-relevant events.

Called by other services to log auditable actions. Entries are
append-only and never modified or deleted.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import AuditLogResponse
from src.core.enums import AuditAction
from src.core.logging import get_logger
from src.domain.entities.audit_log import AuditLog
from src.persistence.repositories.auth_repositories import SqlAlchemyAuditLogRepository


class AuditService:
    """Service for recording and querying audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logger = get_logger(__name__)
        self._repo = SqlAlchemyAuditLogRepository(session)

    async def record(
        self,
        *,
        user_id: UUID | None = None,
        action: AuditAction,
        resource_type: str = "",
        resource_id: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> AuditLog:
        """Record an audit log entry.

        Args:
            user_id: User who performed the action.
            action: Type of action.
            resource_type: Type of resource affected.
            resource_id: ID of the affected resource.
            ip_address: Client IP.
            user_agent: Client User-Agent.
            details: Additional structured details.
            correlation_id: Correlation ID for tracing.

        Returns:
            The created ``AuditLog`` entity.
        """
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            correlation_id=correlation_id,
        )
        log = await self._repo.create(log)
        return log

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLogResponse]:
        """List audit logs for a specific user."""
        logs = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        return [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action.value,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                details=log.details,
                correlation_id=log.correlation_id,
                created_at=log.created_at,
            )
            for log in logs
        ]

    async def list_recent(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLogResponse]:
        """List recent audit logs (admin view)."""
        logs = await self._repo.list_recent(offset=offset, limit=limit)
        return [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action.value,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                details=log.details,
                correlation_id=log.correlation_id,
                created_at=log.created_at,
            )
            for log in logs
        ]
