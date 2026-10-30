"""Publishing Strategy Engine.

Supports:
- Immediate Publishing
- Scheduled Publishing
- Draft Mode
- Manual Approval
- Multi-platform Publishing
- Retry Strategy
- Failover Strategy
- Future Campaign Publishing
"""

from __future__ import annotations

from typing import Any

from src.publishing.schema import (
    FailoverStrategy,
    PublishingMode,
    PublishingPlatform,
    PublishingStrategy,
    RetryStrategy,
    ScheduleConfig,
)
from src.core.logging import get_logger


class PublishingStrategyEngine:
    """Engine for creating and managing publishing strategies.

    Provides preset strategies and custom strategy creation.
    """

    # Preset strategies
    PRESETS: dict[str, PublishingStrategy] = {
        "immediate": PublishingStrategy(
            mode=PublishingMode.IMMEDIATE,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=3,
            failover_strategy=FailoverStrategy.SKIP_FAILED,
        ),
        "scheduled": PublishingStrategy(
            mode=PublishingMode.SCHEDULED,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=3,
            failover_strategy=FailoverStrategy.SKIP_FAILED,
            schedule=ScheduleConfig(mode=PublishingMode.SCHEDULED),
        ),
        "draft": PublishingStrategy(
            mode=PublishingMode.DRAFT,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.NONE,
            max_retries=0,
            failover_strategy=FailoverStrategy.NONE,
        ),
        "manual_approval": PublishingStrategy(
            mode=PublishingMode.MANUAL_APPROVAL,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.NONE,
            max_retries=0,
            failover_strategy=FailoverStrategy.ABORT_ALL,
        ),
        "multi_platform": PublishingStrategy(
            mode=PublishingMode.MULTI_PLATFORM,
            platforms=[PublishingPlatform.YOUTUBE, PublishingPlatform.LINKEDIN],
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=3,
            failover_strategy=FailoverStrategy.SKIP_FAILED,
        ),
        "youtube_only": PublishingStrategy(
            mode=PublishingMode.IMMEDIATE,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=5,
            failover_strategy=FailoverStrategy.SKIP_FAILED,
        ),
        "conservative": PublishingStrategy(
            mode=PublishingMode.DRAFT,
            platforms=[PublishingPlatform.YOUTUBE],
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            max_retries=2,
            retry_delay_seconds=120.0,
            failover_strategy=FailoverStrategy.ABORT_ALL,
        ),
        "aggressive": PublishingStrategy(
            mode=PublishingMode.MULTI_PLATFORM,
            platforms=[
                PublishingPlatform.YOUTUBE,
                PublishingPlatform.LINKEDIN,
                PublishingPlatform.TWITTER,
            ],
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=5,
            retry_delay_seconds=30.0,
            failover_strategy=FailoverStrategy.SKIP_FAILED,
        ),
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def get_preset(self, name: str) -> PublishingStrategy | None:
        """Get a preset strategy by name.

        Args:
            name: Preset name.

        Returns:
            The preset ``PublishingStrategy``, or ``None``.
        """
        return self.PRESETS.get(name)

    def list_presets(self) -> list[str]:
        """List all preset strategy names."""
        return list(self.PRESETS.keys())

    def create_strategy(
        self,
        *,
        mode: PublishingMode = PublishingMode.IMMEDIATE,
        platforms: list[PublishingPlatform] | None = None,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        max_retries: int = 3,
        retry_delay_seconds: float = 60.0,
        failover_strategy: FailoverStrategy = FailoverStrategy.SKIP_FAILED,
        schedule: ScheduleConfig | None = None,
    ) -> PublishingStrategy:
        """Create a custom publishing strategy.

        Args:
            mode: Publishing mode.
            platforms: Target platforms.
            retry_strategy: Retry strategy for failures.
            max_retries: Maximum retry attempts.
            retry_delay_seconds: Delay between retries.
            failover_strategy: Failover strategy for multi-platform.
            schedule: Scheduling configuration.

        Returns:
            A ``PublishingStrategy``.
        """
        return PublishingStrategy(
            mode=mode,
            platforms=platforms or [PublishingPlatform.YOUTUBE],
            retry_strategy=retry_strategy,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            failover_strategy=failover_strategy,
            schedule=schedule or ScheduleConfig(mode=mode),
        )

    def create_schedule(
        self,
        scheduled_at: Any,
        *,
        timezone: str = "UTC",
        recurring: bool = False,
        recurring_cron: str | None = None,
    ) -> ScheduleConfig:
        """Create a scheduling configuration.

        Args:
            scheduled_at: When to publish.
            timezone: Timezone string.
            recurring: Whether this is recurring.
            recurring_cron: Cron expression for recurring publishes.

        Returns:
            A ``ScheduleConfig``.
        """
        return ScheduleConfig(
            mode=PublishingMode.SCHEDULED,
            scheduled_at=scheduled_at,
            timezone=timezone,
            recurring=recurring,
            recurring_cron=recurring_cron,
        )

    def validate_strategy(self, strategy: PublishingStrategy) -> list[str]:
        """Validate a publishing strategy.

        Args:
            strategy: The strategy to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not strategy.platforms:
            errors.append("Strategy must specify at least one platform")

        if strategy.mode == PublishingMode.SCHEDULED:
            if strategy.schedule.scheduled_at is None:
                errors.append("Scheduled mode requires a scheduled_at time in the schedule config")

        if strategy.mode == PublishingMode.MULTI_PLATFORM and len(strategy.platforms) < 2:
            errors.append("Multi-platform mode requires at least 2 platforms")

        if strategy.max_retries < 0:
            errors.append("max_retries cannot be negative")

        if strategy.retry_delay_seconds < 0:
            errors.append("retry_delay_seconds cannot be negative")

        return errors

    def get_retry_delay(self, strategy: PublishingStrategy, retry_count: int) -> float:
        """Calculate the delay before the next retry.

        Args:
            strategy: The publishing strategy.
            retry_count: Current retry count (0-based).

        Returns:
            Delay in seconds.
        """
        if strategy.retry_strategy == RetryStrategy.NONE:
            return 0.0
        elif strategy.retry_strategy == RetryStrategy.FIXED_DELAY:
            return strategy.retry_delay_seconds
        elif strategy.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return strategy.retry_delay_seconds * (retry_count + 1)
        elif strategy.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return strategy.retry_delay_seconds * (2 ** retry_count)
        return strategy.retry_delay_seconds
