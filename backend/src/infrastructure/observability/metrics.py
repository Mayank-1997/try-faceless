"""Metrics Collector — centralised observability for the AI platform.

Tracks:
- Execution time (per agent, per operation)
- Retries (count, backoff duration)
- Failures (error count, error types)
- Average cost (per project, per agent)
- Average tokens (per project, per agent)
- Average scene time
- Generation success rate

Metrics are accumulated in memory and can be exported to external
monitoring systems (Prometheus, Datadog) in future iterations.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.core.config_service import ConfigService
from src.core.enums import AgentType
from src.core.logging import get_logger


class MetricPoint(BaseModel):
    """A single metric data point."""

    name: str
    value: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: dict[str, str] = Field(default_factory=dict)
    unit: str = ""


class AgentMetrics(BaseModel):
    """Aggregated metrics for a single agent."""

    agent_type: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    total_execution_time_ms: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    @property
    def average_execution_time_ms(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time_ms / self.execution_count

    @property
    def average_cost_usd(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_cost_usd / self.execution_count

    @property
    def average_tokens(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_tokens / self.execution_count


class MetricsCollector:
    """Centralised metrics collection service.

    Accumulates metrics from all agents and operations.  Provides
    aggregated summaries for dashboards and monitoring.
    """

    def __init__(self, config: ConfigService) -> None:
        """Create the metrics collector.

        Args:
            config: The application configuration service.
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._agent_metrics: dict[str, AgentMetrics] = {}
        self._points: list[MetricPoint] = []
        self._error_counts: dict[str, int] = defaultdict(int)
        self._operation_timings: dict[str, list[int]] = defaultdict(list)

    def record_execution(
        self,
        agent_type: AgentType,
        *,
        success: bool,
        execution_time_ms: int,
        cost_usd: float = 0.0,
        tokens: int = 0,
        retries: int = 0,
    ) -> None:
        """Record an agent execution.

        Args:
            agent_type: The agent that executed.
            success: Whether the execution succeeded.
            execution_time_ms: Execution time in milliseconds.
            cost_usd: Cost incurred.
            tokens: Tokens consumed.
            retries: Number of retries before success/failure.
        """
        key = agent_type.value
        if key not in self._agent_metrics:
            self._agent_metrics[key] = AgentMetrics(agent_type=key)

        metrics = self._agent_metrics[key]
        metrics.execution_count += 1
        metrics.total_execution_time_ms += execution_time_ms
        metrics.total_cost_usd += cost_usd
        metrics.total_tokens += tokens
        metrics.retry_count += retries

        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1

        self._logger.debug(
            "metric_recorded",
            agent=agent_type.value,
            success=success,
            execution_time_ms=execution_time_ms,
            cost_usd=cost_usd,
            tokens=tokens,
        )

    def record_error(self, error_type: str, agent_type: AgentType | None = None) -> None:
        """Record an error occurrence.

        Args:
            error_type: The error type/exception class name.
            agent_type: Optional agent that caused the error.
        """
        key = f"{agent_type.value}:{error_type}" if agent_type else error_type
        self._error_counts[key] += 1

    def record_timing(self, operation: str, duration_ms: int) -> None:
        """Record a timing measurement for an operation.

        Args:
            operation: The operation name.
            duration_ms: Duration in milliseconds.
        """
        self._operation_timings[operation].append(duration_ms)

    def record_point(self, name: str, value: float, *, tags: dict[str, str] | None = None, unit: str = "") -> None:
        """Record a custom metric point.

        Args:
            name: Metric name.
            value: Metric value.
            tags: Optional tags for filtering.
            unit: Unit of measurement.
        """
        self._points.append(
            MetricPoint(name=name, value=value, tags=tags or {}, unit=unit)
        )

    def get_agent_metrics(self, agent_type: AgentType) -> AgentMetrics:
        """Get aggregated metrics for a specific agent.

        Args:
            agent_type: The agent type.

        Returns:
            ``AgentMetrics`` for the agent (empty if no executions recorded).
        """
        return self._agent_metrics.get(
            agent_type.value,
            AgentMetrics(agent_type=agent_type.value),
        )

    def get_all_agent_metrics(self) -> dict[str, AgentMetrics]:
        """Get aggregated metrics for all agents.

        Returns:
            Dictionary mapping agent type names to their metrics.
        """
        return dict(self._agent_metrics)

    def get_average_execution_time(self, agent_type: AgentType) -> float:
        """Get the average execution time for an agent in milliseconds."""
        return self.get_agent_metrics(agent_type).average_execution_time_ms

    def get_generation_success_rate(self) -> float:
        """Get the overall generation success rate across all agents.

        Returns:
            Success rate as a float between 0.0 and 1.0.
        """
        total_executions = sum(m.execution_count for m in self._agent_metrics.values())
        total_successes = sum(m.success_count for m in self._agent_metrics.values())
        if total_executions == 0:
            return 0.0
        return total_successes / total_executions

    def get_average_cost(self) -> float:
        """Get the average cost per execution across all agents."""
        total_executions = sum(m.execution_count for m in self._agent_metrics.values())
        total_cost = sum(m.total_cost_usd for m in self._agent_metrics.values())
        if total_executions == 0:
            return 0.0
        return total_cost / total_executions

    def get_average_tokens(self) -> float:
        """Get the average token usage per execution across all agents."""
        total_executions = sum(m.execution_count for m in self._agent_metrics.values())
        total_tokens = sum(m.total_tokens for m in self._agent_metrics.values())
        if total_executions == 0:
            return 0.0
        return total_tokens / total_executions

    def get_error_summary(self) -> dict[str, int]:
        """Get a summary of all recorded errors.

        Returns:
            Dictionary mapping error keys to their occurrence counts.
        """
        return dict(self._error_counts)

    def get_operation_average_time(self, operation: str) -> float:
        """Get the average duration for a specific operation.

        Args:
            operation: The operation name.

        Returns:
            Average duration in milliseconds, or 0.0 if no measurements.
        """
        timings = self._operation_timings.get(operation, [])
        if not timings:
            return 0.0
        return sum(timings) / len(timings)

    def get_recent_points(self, name: str | None = None, limit: int = 100) -> list[MetricPoint]:
        """Get recent metric points.

        Args:
            name: Optional filter by metric name.
            limit: Maximum number of points to return.

        Returns:
            List of recent metric points, newest first.
        """
        points = self._points
        if name:
            points = [p for p in points if p.name == name]
        return list(reversed(points[-limit:]))

    def get_summary(self) -> dict[str, Any]:
        """Get a complete observability summary.

        Returns:
            Dictionary containing all key metrics for dashboards.
        """
        return {
            "total_executions": sum(m.execution_count for m in self._agent_metrics.values()),
            "total_successes": sum(m.success_count for m in self._agent_metrics.values()),
            "total_failures": sum(m.failure_count for m in self._agent_metrics.values()),
            "total_retries": sum(m.retry_count for m in self._agent_metrics.values()),
            "generation_success_rate": self.get_generation_success_rate(),
            "average_cost_usd": self.get_average_cost(),
            "average_tokens": self.get_average_tokens(),
            "average_execution_time_ms": (
                sum(m.average_execution_time_ms for m in self._agent_metrics.values())
                / max(len(self._agent_metrics), 1)
            ),
            "error_summary": self.get_error_summary(),
            "agent_metrics": {
                key: metrics.model_dump()
                for key, metrics in self._agent_metrics.items()
            },
        }

    def clear(self) -> None:
        """Clear all metrics (primarily for testing)."""
        self._agent_metrics.clear()
        self._points.clear()
        self._error_counts.clear()
        self._operation_timings.clear()
