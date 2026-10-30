"""Cost Analytics Service.

Tracks:
- Cost per project
- Cost per user
- Cost per provider
- Cost per asset
- Cost per workflow
- Monthly costs
- Daily costs
- Profit margin
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from src.platform.schema import CostBreakdown
from src.core.logging import get_logger


class CostAnalyticsService:
    """Aggregates cost data across multiple dimensions.

    Works alongside the existing ``CostTracker`` to provide higher-level
    analytics and reporting for financial dashboards.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._cost_entries: list[dict[str, Any]] = []

    def record_cost(
        self,
        *,
        user_id: str = "",
        project_id: str = "",
        provider: str = "",
        asset_id: str = "",
        workflow_id: str = "",
        cost_usd: float = 0.0,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a cost entry for analytics.

        Args:
            user_id: User who incurred the cost.
            project_id: Project associated with the cost.
            provider: Provider used.
            asset_id: Asset associated with the cost.
            workflow_id: Workflow that generated the cost.
            cost_usd: Cost in USD.
            timestamp: When the cost was incurred.
        """
        entry = {
            "user_id": user_id,
            "project_id": project_id,
            "provider": provider,
            "asset_id": asset_id,
            "workflow_id": workflow_id,
            "cost_usd": cost_usd,
            "timestamp": timestamp or datetime.now(timezone.utc),
        }
        self._cost_entries.append(entry)
        self._logger.info(
            "cost_analytics_recorded",
            project_id=project_id,
            provider=provider,
            cost_usd=cost_usd,
        )

    def get_breakdown(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        revenue: float = 0.0,
    ) -> CostBreakdown:
        """Get cost breakdown across all dimensions.

        Args:
            start: Optional period start.
            end: Optional period end.
            revenue: Total revenue for profit margin calculation.

        Returns:
            A ``CostBreakdown`` with all cost dimensions.
        """
        entries = [
            e for e in self._cost_entries
            if (start is None or e["timestamp"] >= start)
            and (end is None or e["timestamp"] <= end)
        ]

        per_project: dict[str, float] = defaultdict(float)
        per_user: dict[str, float] = defaultdict(float)
        per_provider: dict[str, float] = defaultdict(float)
        per_asset: dict[str, float] = defaultdict(float)
        per_workflow: dict[str, float] = defaultdict(float)
        daily: dict[str, float] = defaultdict(float)
        monthly: dict[str, float] = defaultdict(float)
        total = 0.0

        for e in entries:
            cost = e["cost_usd"]
            total += cost

            if e["project_id"]:
                per_project[e["project_id"]] += cost
            if e["user_id"]:
                per_user[e["user_id"]] += cost
            if e["provider"]:
                per_provider[e["provider"]] += cost
            if e["asset_id"]:
                per_asset[e["asset_id"]] += cost
            if e["workflow_id"]:
                per_workflow[e["workflow_id"]] += cost

            ts = e["timestamp"]
            daily[ts.date().isoformat()] += cost
            monthly[ts.strftime("%Y-%m")] += cost

        profit_margin = 0.0
        if revenue > 0:
            profit_margin = ((revenue - total) / revenue) * 100.0

        return CostBreakdown(
            cost_per_project=dict(per_project),
            cost_per_user=dict(per_user),
            cost_per_provider=dict(per_provider),
            cost_per_asset=dict(per_asset),
            cost_per_workflow=dict(per_workflow),
            daily_costs=dict(daily),
            monthly_costs=dict(monthly),
            total_cost=total,
            revenue=revenue,
            profit_margin=profit_margin,
        )

    def get_project_cost(self, project_id: str) -> float:
        """Get total cost for a project.

        Args:
            project_id: The project ID.

        Returns:
            Total cost in USD.
        """
        return sum(e["cost_usd"] for e in self._cost_entries if e["project_id"] == project_id)

    def get_user_cost(self, user_id: str) -> float:
        """Get total cost for a user.

        Args:
            user_id: The user ID.

        Returns:
            Total cost in USD.
        """
        return sum(e["cost_usd"] for e in self._cost_entries if e["user_id"] == user_id)

    def get_daily_costs(self, days: int = 30) -> dict[str, float]:
        """Get daily costs for the last N days.

        Args:
            days: Number of days to include.

        Returns:
            Dict mapping date string to cost.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        breakdown = self.get_breakdown(start=start, end=now)
        return breakdown.daily_costs

    def get_monthly_costs(self, months: int = 12) -> dict[str, float]:
        """Get monthly costs for the last N months.

        Args:
            months: Number of months to include.

        Returns:
            Dict mapping month string to cost.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=months * 30)
        breakdown = self.get_breakdown(start=start, end=now)
        return breakdown.monthly_costs

    @property
    def entry_count(self) -> int:
        """Total number of cost entries."""
        return len(self._cost_entries)

    def clear(self) -> None:
        """Clear all entries (primarily for testing)."""
        self._cost_entries.clear()
