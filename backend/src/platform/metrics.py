"""Metrics Service.

Collects:
- Business metrics
- Technical metrics
- Performance metrics
- Financial metrics
- Operational metrics
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.platform.schema import Metric, MetricCategory, MetricSummary, MetricType
from src.core.logging import get_logger


class MetricsService:
    """Collects and aggregates metrics across all categories.

    Provides a unified interface for recording and querying business,
    technical, performance, financial, and operational metrics.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._metrics: list[Metric] = []

    def record(self, metric: Metric) -> None:
        """Record a metric.

        Args:
            metric: The metric to record.
        """
        self._metrics.append(metric)
        self._logger.debug(
            "metric_recorded",
            name=metric.name,
            category=metric.category.value,
            value=metric.value,
        )

    def record_business(self, name: str, value: float, *, unit: str = "", labels: dict[str, str] | None = None) -> None:
        """Record a business metric.

        Args:
            name: Metric name.
            value: Metric value.
            unit: Optional unit.
            labels: Optional labels.
        """
        self.record(Metric(
            name=name,
            category=MetricCategory.BUSINESS,
            metric_type=MetricType.COUNTER,
            value=value,
            unit=unit,
            labels=labels or {},
        ))

    def record_technical(self, name: str, value: float, *, unit: str = "", labels: dict[str, str] | None = None) -> None:
        """Record a technical metric."""
        self.record(Metric(
            name=name,
            category=MetricCategory.TECHNICAL,
            metric_type=MetricType.GAUGE,
            value=value,
            unit=unit,
            labels=labels or {},
        ))

    def record_performance(self, name: str, value: float, *, unit: str = "", labels: dict[str, str] | None = None) -> None:
        """Record a performance metric."""
        self.record(Metric(
            name=name,
            category=MetricCategory.PERFORMANCE,
            metric_type=MetricType.HISTOGRAM,
            value=value,
            unit=unit,
            labels=labels or {},
        ))

    def record_financial(self, name: str, value: float, *, unit: str = "USD", labels: dict[str, str] | None = None) -> None:
        """Record a financial metric."""
        self.record(Metric(
            name=name,
            category=MetricCategory.FINANCIAL,
            metric_type=MetricType.COUNTER,
            value=value,
            unit=unit,
            labels=labels or {},
        ))

    def record_operational(self, name: str, value: float, *, unit: str = "", labels: dict[str, str] | None = None) -> None:
        """Record an operational metric."""
        self.record(Metric(
            name=name,
            category=MetricCategory.OPERATIONAL,
            metric_type=MetricType.GAUGE,
            value=value,
            unit=unit,
            labels=labels or {},
        ))

    def get_summary(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> MetricSummary:
        """Get aggregated metric summary by category.

        Args:
            start: Optional period start.
            end: Optional period end.

        Returns:
            A ``MetricSummary`` with aggregated values.
        """
        metrics = [
            m for m in self._metrics
            if (start is None or m.timestamp >= start)
            and (end is None or m.timestamp <= end)
        ]

        business: dict[str, float] = defaultdict(float)
        technical: dict[str, float] = defaultdict(float)
        performance: dict[str, float] = defaultdict(float)
        financial: dict[str, float] = defaultdict(float)
        operational: dict[str, float] = defaultdict(float)

        for m in metrics:
            if m.category == MetricCategory.BUSINESS:
                business[m.name] += m.value
            elif m.category == MetricCategory.TECHNICAL:
                technical[m.name] = m.value  # Gauge — take latest
            elif m.category == MetricCategory.PERFORMANCE:
                performance[m.name] += m.value
            elif m.category == MetricCategory.FINANCIAL:
                financial[m.name] += m.value
            elif m.category == MetricCategory.OPERATIONAL:
                operational[m.name] = m.value  # Gauge — take latest

        return MetricSummary(
            business=dict(business),
            technical=dict(technical),
            performance=dict(performance),
            financial=dict(financial),
            operational=dict(operational),
            period_start=start,
            period_end=end,
        )

    def get_metrics(
        self,
        *,
        category: MetricCategory | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[Metric]:
        """Get metrics with optional filters.

        Args:
            category: Optional category filter.
            name: Optional name filter.
            limit: Maximum number to return.

        Returns:
            List of ``Metric``.
        """
        result = self._metrics
        if category is not None:
            result = [m for m in result if m.category == category]
        if name is not None:
            result = [m for m in result if m.name == name]
        return result[-limit:]

    def get_metric_names(self, category: MetricCategory | None = None) -> list[str]:
        """Get unique metric names, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of unique metric names.
        """
        metrics = self._metrics
        if category is not None:
            metrics = [m for m in metrics if m.category == category]
        return list({m.name for m in metrics})

    @property
    def metric_count(self) -> int:
        """Total number of recorded metrics."""
        return len(self._metrics)

    def clear(self) -> None:
        """Clear all metrics (primarily for testing)."""
        self._metrics.clear()
