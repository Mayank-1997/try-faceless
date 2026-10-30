"""Retry policies for workflow node execution.

Provides composable retry strategies with exponential backoff,
jitter, and configurable limits.  Policies can be applied globally
or per-node.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.workflow.exceptions import ErrorSeverity, classify_error


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for a node or workflow.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries).
        initial_delay_seconds: Delay before the first retry.
        max_delay_seconds: Maximum delay between retries (cap).
        backoff_multiplier: Multiplier applied to delay after each retry.
        jitter: If True, adds random jitter to delay to avoid thundering herd.
        retryable_errors: Set of error severity levels that should be retried.
            Defaults to retryable and provider errors.
        node_name: Optional node name this policy applies to.
    """

    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: frozenset[str] = frozenset({
        ErrorSeverity.RETRYABLE,
        ErrorSeverity.PROVIDER,
    })
    node_name: str | None = None

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error should be retried.

        Args:
            error: The exception that occurred.
            attempt: The current attempt number (0-indexed).

        Returns:
            True if the error should be retried.
        """
        if attempt >= self.max_retries:
            return False
        severity = classify_error(error)
        return severity in self.retryable_errors

    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry.

        Uses exponential backoff with optional jitter.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay_seconds)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay

    async def wait(self, attempt: int) -> None:
        """Asynchronously wait before the next retry.

        Args:
            attempt: The current attempt number (0-indexed).
        """
        delay = self.get_delay(attempt)
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Pre-defined policies
# ---------------------------------------------------------------------------
class RetryPolicies:
    """Common retry policy presets."""

    NO_RETRY = RetryPolicy(max_retries=0)
    """No retries — fail immediately on error."""

    STANDARD = RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=60.0,
        backoff_multiplier=2.0,
    )
    """Standard retry with exponential backoff (3 retries, 1s→2s→4s)."""

    AGGRESSIVE = RetryPolicy(
        max_retries=5,
        initial_delay_seconds=0.5,
        max_delay_seconds=30.0,
        backoff_multiplier=1.5,
    )
    """Aggressive retry for transient failures (5 retries, fast backoff)."""

    CONSERVATIVE = RetryPolicy(
        max_retries=2,
        initial_delay_seconds=5.0,
        max_delay_seconds=120.0,
        backoff_multiplier=3.0,
    )
    """Conservative retry for expensive operations (2 retries, slow backoff)."""

    PROVIDER = RetryPolicy(
        max_retries=4,
        initial_delay_seconds=2.0,
        max_delay_seconds=90.0,
        backoff_multiplier=2.0,
        retryable_errors=frozenset({ErrorSeverity.PROVIDER, ErrorSeverity.RETRYABLE}),
    )
    """Retry policy for AI provider calls (4 retries, medium backoff)."""

    VALIDATION = RetryPolicy(
        max_retries=1,
        initial_delay_seconds=0.0,
        max_delay_seconds=1.0,
        backoff_multiplier=1.0,
        retryable_errors=frozenset({ErrorSeverity.VALIDATION}),
    )
    """Retry policy for validation errors (1 retry, no delay)."""


# ---------------------------------------------------------------------------
# Retry execution result
# ---------------------------------------------------------------------------
@dataclass
class RetryResult:
    """Result of a retry execution.

    Attributes:
        success: Whether the execution ultimately succeeded.
        attempts: Total number of attempts (including the first).
        total_delay_seconds: Total time spent waiting between retries.
        last_error: The last error encountered, if any.
        execution_time_ms: Total execution time in milliseconds.
    """

    success: bool
    attempts: int
    total_delay_seconds: float
    last_error: Exception | None
    execution_time_ms: int
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Retry executor
# ---------------------------------------------------------------------------
class RetryExecutor:
    """Executes a callable with retry logic.

    Wraps an async callable and applies a ``RetryPolicy`` to handle
    transient failures with exponential backoff.
    """

    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy
        self._logger = None

    async def execute(
        self,
        func: Any,
        *args: Any,
        logger: Any = None,
        **kwargs: Any,
    ) -> RetryResult:
        """Execute a callable with retry logic.

        Args:
            func: The async callable to execute.
            *args: Positional arguments to pass to the callable.
            logger: Optional logger for retry events.
            **kwargs: Keyword arguments to pass to the callable.

        Returns:
            A ``RetryResult`` with execution details.
        """
        self._logger = logger
        last_error: Exception | None = None
        total_delay: float = 0.0
        attempts = 0
        start = datetime.now(timezone.utc)

        for attempt in range(self._policy.max_retries + 1):
            attempts = attempt + 1
            try:
                await func(*args, **kwargs)
                end = datetime.now(timezone.utc)
                return RetryResult(
                    success=True,
                    attempts=attempts,
                    total_delay_seconds=total_delay,
                    last_error=None,
                    execution_time_ms=int((end - start).total_seconds() * 1000),
                    started_at=start,
                    completed_at=end,
                )
            except Exception as exc:
                last_error = exc
                if not self._policy.should_retry(exc, attempt):
                    if self._logger:
                        self._logger.warning(
                            "retry_not_retryable",
                            error=str(exc),
                            attempt=attempts,
                            policy=self._policy.node_name or "default",
                        )
                    break
                if attempt < self._policy.max_retries:
                    delay = self._policy.get_delay(attempt)
                    total_delay += delay
                    if self._logger:
                        self._logger.info(
                            "retry_attempting",
                            attempt=attempts,
                            delay_seconds=delay,
                            error=str(exc),
                            policy=self._policy.node_name or "default",
                        )
                    await asyncio.sleep(delay)

        end = datetime.now(timezone.utc)
        return RetryResult(
            success=False,
            attempts=attempts,
            total_delay_seconds=total_delay,
            last_error=last_error,
            execution_time_ms=int((end - start).total_seconds() * 1000),
            started_at=start,
            completed_at=end,
        )
