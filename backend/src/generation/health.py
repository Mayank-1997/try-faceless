"""Provider Health Monitor.

Tracks health metrics for all generation providers:
- Latency
- Timeouts
- Failures
- Availability
- Average cost
- Average quality
- Quota remaining

Automatically disables unhealthy providers and reroutes traffic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.logging import get_logger
from src.generation.schema import ProviderHealthMetrics


class ProviderHealthMonitor:
    """Monitors provider health and automatically disables unhealthy providers.

    Tracks per-provider metrics and uses configurable thresholds to
    determine when a provider should be disabled or rerouted.
    """

    # Thresholds
    MAX_FAILURE_RATE = 0.5  # Disable if > 50% failures
    MAX_LATENCY_MS = 30000  # Disable if avg latency > 30s
    MIN_AVAILABILITY = 0.5  # Disable if availability < 50%

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._metrics: dict[str, ProviderHealthMetrics] = {}

    def register_provider(self, name: str) -> None:
        """Register a provider for health monitoring.

        Args:
            name: Provider name.
        """
        if name not in self._metrics:
            self._metrics[name] = ProviderHealthMetrics(provider=name)
            self._logger.info("health_monitor_registered", provider=name)

    def get_metrics(self, name: str) -> ProviderHealthMetrics | None:
        """Get health metrics for a provider.

        Args:
            name: Provider name.

        Returns:
            Health metrics, or ``None`` if not registered.
        """
        return self._metrics.get(name)

    def record_success(
        self,
        name: str,
        *,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        quality: float = 0.0,
    ) -> None:
        """Record a successful generation.

        Args:
            name: Provider name.
            latency_ms: Request latency in milliseconds.
            cost: Cost in USD.
            quality: Quality score (0.0 to 1.0).
        """
        m = self._metrics.setdefault(name, ProviderHealthMetrics(provider=name))
        m.success_count += 1
        m.latency_ms = (m.latency_ms * (m.success_count - 1) + latency_ms) / m.success_count if m.success_count > 0 else latency_ms
        m.average_cost = (m.average_cost * (m.success_count - 1) + cost) / m.success_count if m.success_count > 0 else cost
        m.average_quality = (m.average_quality * (m.success_count - 1) + quality) / m.success_count if m.success_count > 0 else quality
        m.last_check = datetime.now(timezone.utc)
        self._check_thresholds(name)

    def record_failure(self, name: str, *, timeout: bool = False) -> None:
        """Record a failed generation.

        Args:
            name: Provider name.
            timeout: Whether the failure was a timeout.
        """
        m = self._metrics.setdefault(name, ProviderHealthMetrics(provider=name))
        m.failure_count += 1
        if timeout:
            m.timeout_count += 1
        m.last_failure = datetime.now(timezone.utc)
        m.last_check = datetime.now(timezone.utc)
        self._check_thresholds(name)

    def record_quota(self, name: str, remaining: int) -> None:
        """Update quota remaining for a provider.

        Args:
            name: Provider name.
            remaining: Quota remaining.
        """
        m = self._metrics.setdefault(name, ProviderHealthMetrics(provider=name))
        m.quota_remaining = remaining

    def is_disabled(self, name: str) -> bool:
        """Check if a provider is disabled.

        Args:
            name: Provider name.

        Returns:
            ``True`` if the provider is disabled.
        """
        m = self._metrics.get(name)
        return m.disabled if m else False

    def disable(self, name: str, reason: str = "") -> None:
        """Manually disable a provider.

        Args:
            name: Provider name.
            reason: Disable reason.
        """
        m = self._metrics.setdefault(name, ProviderHealthMetrics(provider=name))
        m.disabled = True
        m.healthy = False
        self._logger.warning("provider_disabled", provider=name, reason=reason)

    def enable(self, name: str) -> None:
        """Re-enable a disabled provider.

        Args:
            name: Provider name.
        """
        m = self._metrics.setdefault(name, ProviderHealthMetrics(provider=name))
        m.disabled = False
        m.healthy = True
        self._logger.info("provider_enabled", provider=name)

    def _check_thresholds(self, name: str) -> None:
        """Check if a provider should be auto-disabled."""
        m = self._metrics.get(name)
        if m is None or m.disabled:
            return

        # Calculate availability
        total = m.success_count + m.failure_count
        if total > 0:
            m.availability = m.success_count / total

        # Check failure rate
        if m.failure_rate > self.MAX_FAILURE_RATE and total >= 5:
            self.disable(name, f"Failure rate {m.failure_rate:.0%} exceeds threshold")
            return

        # Check latency
        if m.latency_ms > self.MAX_LATENCY_MS and m.success_count >= 3:
            self.disable(name, f"Latency {m.latency_ms:.0f}ms exceeds threshold")
            return

        # Check availability
        if m.availability < self.MIN_AVAILABILITY and total >= 5:
            self.disable(name, f"Availability {m.availability:.0%} below threshold")
            return

        m.healthy = True

    def get_all_metrics(self) -> dict[str, ProviderHealthMetrics]:
        """Get health metrics for all providers."""
        return dict(self._metrics)

    def get_healthy_providers(self) -> list[str]:
        """Get list of healthy provider names."""
        return [name for name, m in self._metrics.items() if m.healthy and not m.disabled]
