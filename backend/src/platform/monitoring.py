"""Monitoring & Health Services.

Monitoring Service tracks:
- Latency
- Queue size
- Worker health
- Failures
- Retries
- Provider availability
- Memory usage
- CPU usage

Health Service monitors:
- Generation Platform
- Rendering Platform
- Publishing Platform
- Database
- Redis
- Storage
- Third-party providers
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from src.platform.schema import (
    HealthCheck,
    HealthReport,
    HealthStatus,
    MonitoringMetric,
    MonitoringSnapshot,
)
from src.core.logging import get_logger


class MonitoringService:
    """Collects and exposes system monitoring metrics.

    Tracks latency, queue sizes, worker health, failures, retries,
    provider availability, and resource usage (memory, CPU, disk).
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._metrics: list[MonitoringMetric] = []
        self._snapshots: list[MonitoringSnapshot] = []
        self._health_checkers: dict[str, Callable[[], HealthCheck]] = {}

    def record_metric(self, metric: MonitoringMetric) -> None:
        """Record a monitoring metric.

        Args:
            metric: The metric to record.
        """
        self._metrics.append(metric)
        self._logger.debug(
            "metric_recorded",
            name=metric.name,
            value=metric.value,
            unit=metric.unit,
        )

    def record_latency(self, component: str, latency_ms: float) -> None:
        """Record a latency metric.

        Args:
            component: The component name.
            latency_ms: Latency in milliseconds.
        """
        self.record_metric(MonitoringMetric(
            name="latency",
            value=latency_ms,
            unit="ms",
            labels={"component": component},
        ))

    def record_queue_size(self, queue_name: str, size: int) -> None:
        """Record a queue size metric.

        Args:
            queue_name: The queue name.
            size: Current queue size.
        """
        self.record_metric(MonitoringMetric(
            name="queue_size",
            value=float(size),
            unit="count",
            labels={"queue": queue_name},
        ))

    def record_failure(self, component: str, error: str = "") -> None:
        """Record a failure.

        Args:
            component: The component that failed.
            error: Error message.
        """
        self.record_metric(MonitoringMetric(
            name="failure",
            value=1.0,
            unit="count",
            labels={"component": component, "error": error[:100]},
        ))

    def record_retry(self, component: str) -> None:
        """Record a retry event.

        Args:
            component: The component that retried.
        """
        self.record_metric(MonitoringMetric(
            name="retry",
            value=1.0,
            unit="count",
            labels={"component": component},
        ))

    def record_provider_availability(self, provider: str, available: bool) -> None:
        """Record provider availability.

        Args:
            provider: The provider name.
            available: Whether the provider is available.
        """
        self.record_metric(MonitoringMetric(
            name="provider_availability",
            value=1.0 if available else 0.0,
            unit="boolean",
            labels={"provider": provider},
        ))

    def record_resource_usage(
        self,
        *,
        memory_mb: float = 0.0,
        cpu_percent: float = 0.0,
        disk_percent: float = 0.0,
    ) -> None:
        """Record resource usage metrics.

        Args:
            memory_mb: Memory usage in MB.
            cpu_percent: CPU usage percentage.
            disk_percent: Disk usage percentage.
        """
        if memory_mb > 0:
            self.record_metric(MonitoringMetric(name="memory_usage", value=memory_mb, unit="MB"))
        if cpu_percent > 0:
            self.record_metric(MonitoringMetric(name="cpu_usage", value=cpu_percent, unit="%"))
        if disk_percent > 0:
            self.record_metric(MonitoringMetric(name="disk_usage", value=disk_percent, unit="%"))

    def take_snapshot(self) -> MonitoringSnapshot:
        """Take a snapshot of current monitoring state.

        Returns:
            A ``MonitoringSnapshot`` with current metrics.
        """
        # Calculate averages from recent metrics
        recent = self._metrics[-100:] if self._metrics else []

        latency_values = [m.value for m in recent if m.name == "latency"]
        queue_metrics = [m for m in recent if m.name == "queue_size"]
        failure_count = sum(1 for m in recent if m.name == "failure")
        retry_count = sum(1 for m in recent if m.name == "retry")
        provider_metrics = [m for m in recent if m.name == "provider_availability"]
        memory_values = [m.value for m in recent if m.name == "memory_usage"]
        cpu_values = [m.value for m in recent if m.name == "cpu_usage"]
        disk_values = [m.value for m in recent if m.name == "disk_usage"]

        provider_avail: dict[str, float] = {}
        for m in provider_metrics:
            provider = m.labels.get("provider", "unknown")
            provider_avail[provider] = m.value

        snapshot = MonitoringSnapshot(
            latency_ms=sum(latency_values) / len(latency_values) if latency_values else 0.0,
            queue_size=int(max((m.value for m in queue_metrics), default=0.0)),
            failure_count=failure_count,
            retry_count=retry_count,
            provider_availability=provider_avail,
            memory_usage_mb=sum(memory_values) / len(memory_values) if memory_values else 0.0,
            cpu_usage_percent=sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            disk_usage_percent=sum(disk_values) / len(disk_values) if disk_values else 0.0,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> MonitoringSnapshot | None:
        """Get the most recent monitoring snapshot.

        Returns:
            The latest ``MonitoringSnapshot``, or ``None``.
        """
        return self._snapshots[-1] if self._snapshots else None

    def get_metrics(
        self,
        name: str | None = None,
        limit: int = 100,
    ) -> list[MonitoringMetric]:
        """Get recent metrics, optionally filtered by name.

        Args:
            name: Optional metric name filter.
            limit: Maximum number to return.

        Returns:
            List of ``MonitoringMetric``.
        """
        if name:
            result = [m for m in self._metrics if m.name == name]
        else:
            result = list(self._metrics)
        return result[-limit:]

    @property
    def metric_count(self) -> int:
        """Total number of recorded metrics."""
        return len(self._metrics)

    @property
    def snapshot_count(self) -> int:
        """Number of snapshots taken."""
        return len(self._snapshots)

    def clear(self) -> None:
        """Clear all metrics and snapshots (primarily for testing)."""
        self._metrics.clear()
        self._snapshots.clear()


class HealthService:
    """Monitors the health of platform components.

    Registers health check functions for each component and aggregates
    results into a ``HealthReport``.
    """

    # Standard component names
    COMPONENTS = [
        "generation_platform",
        "rendering_platform",
        "publishing_platform",
        "database",
        "redis",
        "storage",
        "ai_providers",
    ]

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._checkers: dict[str, Callable[[], HealthCheck]] = {}
        self._last_report: HealthReport | None = None

    def register_check(self, component: str, checker: Callable[[], HealthCheck]) -> None:
        """Register a health check for a component.

        Args:
            component: The component name.
            checker: A callable that returns a ``HealthCheck``.
        """
        self._checkers[component] = checker
        self._logger.info("health_check_registered", component=component)

    def unregister_check(self, component: str) -> None:
        """Unregister a health check.

        Args:
            component: The component name.
        """
        self._checkers.pop(component, None)

    def check_component(self, component: str) -> HealthCheck:
        """Run a health check for a single component.

        Args:
            component: The component name.

        Returns:
            A ``HealthCheck`` result.
        """
        checker = self._checkers.get(component)
        if checker is None:
            return HealthCheck(
                component=component,
                status=HealthStatus.UNKNOWN,
                message="No health checker registered",
            )
        try:
            return checker()
        except Exception as exc:
            return HealthCheck(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
            )

    def check_all(self) -> HealthReport:
        """Run all registered health checks.

        Returns:
            A ``HealthReport`` with all check results.
        """
        checks: list[HealthCheck] = []
        for component in self._checkers:
            checks.append(self.check_component(component))

        # Determine overall status
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            overall = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in checks):
            overall = HealthStatus.DEGRADED
        elif all(c.status == HealthStatus.HEALTHY for c in checks) and checks:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        report = HealthReport(overall_status=overall, checks=checks)
        self._last_report = report

        self._logger.info(
            "health_check_completed",
            overall=overall.value,
            healthy=report.healthy_count,
            degraded=report.degraded_count,
            unhealthy=report.unhealthy_count,
        )

        return report

    def get_last_report(self) -> HealthReport | None:
        """Get the most recent health report.

        Returns:
            The last ``HealthReport``, or ``None``.
        """
        return self._last_report

    def is_healthy(self) -> bool:
        """Quick check if the platform is healthy.

        Returns:
            ``True`` if all components are healthy.
        """
        report = self.check_all()
        return report.overall_status == HealthStatus.HEALTHY

    @property
    def registered_components(self) -> list[str]:
        """List of registered component names."""
        return list(self._checkers.keys())

    @property
    def component_count(self) -> int:
        """Number of registered health checks."""
        return len(self._checkers)
