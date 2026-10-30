"""Analytics Service.

Tracks:
- Projects (generation time, publishing time, rendering time, success/failure)
- Most used providers
- Top models
- Project growth
- User activity
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from src.platform.schema import AnalyticsSummary, ProjectAnalytics
from src.core.logging import get_logger


class AnalyticsService:
    """Collects and aggregates project analytics.

    Records analytics events as projects move through the pipeline
    and provides aggregated summaries for dashboards and reporting.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._records: list[ProjectAnalytics] = []

    def record(self, analytics: ProjectAnalytics) -> None:
        """Record a project analytics event.

        Args:
            analytics: The analytics record to store.
        """
        self._records.append(analytics)
        self._logger.info(
            "analytics_recorded",
            project_id=analytics.project_id,
            success=analytics.success,
            provider=analytics.provider,
        )

    def get_summary(
        self,
        *,
        user_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> AnalyticsSummary:
        """Get aggregated analytics summary.

        Args:
            user_id: Optional filter by user.
            start: Optional start datetime.
            end: Optional end datetime.

        Returns:
            An ``AnalyticsSummary`` with aggregated metrics.
        """
        records = self._filter_records(user_id=user_id, start=start, end=end)

        if not records:
            return AnalyticsSummary()

        total = len(records)
        successful = sum(1 for r in records if r.success)
        failed = total - successful

        gen_times = [r.generation_time_seconds for r in records if r.generation_time_seconds > 0]
        pub_times = [r.publishing_time_seconds for r in records if r.publishing_time_seconds > 0]
        render_times = [r.rendering_time_seconds for r in records if r.rendering_time_seconds > 0]

        providers: dict[str, int] = defaultdict(int)
        models: dict[str, int] = defaultdict(int)
        user_activity: dict[str, int] = defaultdict(int)

        for r in records:
            if r.provider:
                providers[r.provider] += 1
            if r.model:
                models[r.model] += 1
            if r.user_id:
                user_activity[r.user_id] += 1

        # Project growth (last 30 days)
        now = datetime.now(timezone.utc)
        growth: list[dict[str, Any]] = []
        for i in range(30, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = sum(
                1 for r in records
                if day_start <= r.created_at < day_end
            )
            growth.append({"date": day_start.date().isoformat(), "count": count})

        return AnalyticsSummary(
            total_projects=total,
            successful_projects=successful,
            failed_projects=failed,
            avg_generation_time=sum(gen_times) / len(gen_times) if gen_times else 0.0,
            avg_publishing_time=sum(pub_times) / len(pub_times) if pub_times else 0.0,
            avg_rendering_time=sum(render_times) / len(render_times) if render_times else 0.0,
            success_rate=(successful / total * 100) if total > 0 else 0.0,
            failure_rate=(failed / total * 100) if total > 0 else 0.0,
            most_used_providers=dict(sorted(providers.items(), key=lambda x: x[1], reverse=True)[:10]),
            top_models=dict(sorted(models.items(), key=lambda x: x[1], reverse=True)[:10]),
            project_growth=growth,
            user_activity=dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:20]),
        )

    def get_user_activity(self, user_id: str) -> list[ProjectAnalytics]:
        """Get all analytics records for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of ``ProjectAnalytics`` for the user.
        """
        return [r for r in self._records if r.user_id == user_id]

    def get_project_analytics(self, project_id: str) -> ProjectAnalytics | None:
        """Get analytics for a specific project.

        Args:
            project_id: The project ID.

        Returns:
            The ``ProjectAnalytics`` if found, ``None`` otherwise.
        """
        for r in reversed(self._records):
            if r.project_id == project_id:
                return r
        return None

    def _filter_records(
        self,
        *,
        user_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ProjectAnalytics]:
        """Filter records by criteria."""
        records = self._records
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        if start:
            records = [r for r in records if r.created_at >= start]
        if end:
            records = [r for r in records if r.created_at <= end]
        return records

    @property
    def record_count(self) -> int:
        """Total number of analytics records."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all records (primarily for testing)."""
        self._records.clear()
