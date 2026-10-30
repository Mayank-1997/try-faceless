"""Admin Service.

Supports:
- User management
- Project management
- Billing overview
- Usage dashboard
- Provider health
- System health
- Logs
- Support tools
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.platform.schema import HealthStatus, MonitoringSnapshot
from src.core.logging import get_logger


class AdminService:
    """Administrative service for platform management.

    Provides aggregated views and management tools for administrators.
    Delegates to specialized services for actual operations.
    """

    def __init__(
        self,
        analytics_service: Any | None = None,
        usage_tracker: Any | None = None,
        billing_service: Any | None = None,
        monitoring_service: Any | None = None,
        health_service: Any | None = None,
        audit_service: Any | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._analytics = analytics_service
        self._usage = usage_tracker
        self._billing = billing_service
        self._monitoring = monitoring_service
        self._health = health_service
        self._audit = audit_service

    def get_platform_overview(self) -> dict[str, Any]:
        """Get a high-level platform overview for admin dashboard.

        Returns:
            A dict with aggregated platform metrics.
        """
        overview: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._analytics:
            summary = self._analytics.get_summary()
            overview["analytics"] = {
                "total_projects": summary.total_projects,
                "success_rate": summary.success_rate,
                "failure_rate": summary.failure_rate,
                "avg_generation_time": summary.avg_generation_time,
            }

        if self._usage:
            overview["usage"] = {
                "total_records": self._usage.record_count,
            }

        if self._billing:
            overview["billing"] = {
                "plans_available": len(self._billing.list_plans()),
                "total_invoices": len(self._billing.get_invoices()),
            }

        if self._monitoring:
            snapshot = self._monitoring.get_latest_snapshot()
            if snapshot:
                overview["monitoring"] = {
                    "latency_ms": snapshot.latency_ms,
                    "queue_size": snapshot.queue_size,
                    "failure_count": snapshot.failure_count,
                    "provider_availability": snapshot.provider_availability,
                }

        if self._health:
            report = self._health.get_last_report()
            if report:
                overview["health"] = {
                    "overall_status": report.overall_status.value,
                    "healthy_count": report.healthy_count,
                    "degraded_count": report.degraded_count,
                    "unhealthy_count": report.unhealthy_count,
                }

        if self._audit:
            overview["audit"] = {
                "total_entries": self._audit.entry_count,
                "actions": self._audit.count_by_action(),
            }

        return overview

    def get_user_overview(self, user_id: str) -> dict[str, Any]:
        """Get an overview for a specific user.

        Args:
            user_id: The user ID.

        Returns:
            A dict with user-specific metrics.
        """
        overview: dict[str, Any] = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._usage:
            overview["usage"] = self._usage.get_summary(user_id).model_dump()

        if self._billing:
            sub = self._billing.get_subscription(user_id)
            if sub:
                overview["subscription"] = {
                    "plan_id": sub.plan_id,
                    "plan_type": sub.plan_type.value,
                    "status": sub.status.value,
                    "is_active": sub.is_active,
                }
            balance = self._billing.get_credit_balance(user_id)
            overview["credits"] = balance.credits

        if self._analytics:
            records = self._analytics.get_user_activity(user_id)
            overview["project_count"] = len(records)

        return overview

    def get_provider_health(self) -> dict[str, Any]:
        """Get health status of all AI providers.

        Returns:
            A dict with provider health information.
        """
        if self._monitoring is None:
            return {}

        snapshot = self._monitoring.get_latest_snapshot()
        if snapshot is None:
            return {}

        return {
            "provider_availability": snapshot.provider_availability,
            "timestamp": snapshot.timestamp.isoformat(),
        }

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health.

        Returns:
            A dict with system health information.
        """
        if self._health is None:
            return {"status": HealthStatus.UNKNOWN.value}

        report = self._health.check_all()
        return {
            "overall_status": report.overall_status.value,
            "checks": [
                {
                    "component": c.component,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                }
                for c in report.checks
            ],
            "checked_at": report.checked_at.isoformat(),
        }

    def get_recent_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit log entries for admin review.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of audit entries as dicts.
        """
        if self._audit is None:
            return []

        entries = self._audit.get_entries(limit=limit)
        return [
            {
                "id": str(e.id),
                "user_id": e.user_id,
                "action": e.action.value,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]

    def get_billing_overview(self) -> dict[str, Any]:
        """Get billing overview for admin dashboard.

        Returns:
            A dict with billing summary.
        """
        if self._billing is None:
            return {}

        invoices = self._billing.get_invoices()
        total_revenue = sum(inv.total for inv in invoices if inv.status.value == "paid")
        pending_amount = sum(inv.total for inv in invoices if inv.status.value == "pending")

        return {
            "total_invoices": len(invoices),
            "total_revenue": total_revenue,
            "pending_amount": pending_amount,
            "plans": [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.plan_type.value,
                    "price_monthly": p.price_monthly,
                }
                for p in self._billing.list_plans()
            ],
        }

    def get_usage_dashboard(self) -> dict[str, Any]:
        """Get usage dashboard data.

        Returns:
            A dict with usage metrics.
        """
        if self._usage is None:
            return {}

        return {
            "total_records": self._usage.record_count,
        }

    def suspend_user(self, user_id: str) -> bool:
        """Suspend a user (admin action).

        Args:
            user_id: The user ID.

        Returns:
            ``True`` if action was recorded.
        """
        from src.platform.schema import PlatformAuditAction

        if self._audit:
            self._audit.record(
                user_id=user_id,
                action=PlatformAuditAction.ADMIN_CHANGE,
                resource_type="user",
                resource_id=user_id,
                details={"action": "suspended"},
            )
        self._logger.info("user_suspended", user_id=user_id)
        return True

    def activate_user(self, user_id: str) -> bool:
        """Activate a user (admin action).

        Args:
            user_id: The user ID.

        Returns:
            ``True`` if action was recorded.
        """
        from src.platform.schema import PlatformAuditAction

        if self._audit:
            self._audit.record(
                user_id=user_id,
                action=PlatformAuditAction.ADMIN_CHANGE,
                resource_type="user",
                resource_id=user_id,
                details={"action": "activated"},
            )
        self._logger.info("user_activated", user_id=user_id)
        return True
