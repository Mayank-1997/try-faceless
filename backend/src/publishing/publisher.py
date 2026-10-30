"""Publisher Interface — abstract base class for all publishers.

Every publisher must implement:
- authenticate() — Authenticate with the platform
- validate() — Validate assets and metadata for this platform
- prepare() — Prepare assets for upload
- publish() — Publish the video
- schedule() — Schedule publishing for a future time
- cancel() — Cancel a scheduled or in-progress publish
- monitor() — Monitor publishing progress
- collect_metrics() — Collect publishing metrics
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.publishing.schema import (
    AuthCredential,
    PlatformConfig,
    PublishingMetadata,
    PublishingMetrics,
    PublishingProgress,
    PublishingReport,
    PublishingTask,
)
from src.core.logging import get_logger


class Publisher(ABC):
    """Abstract interface for publishing platforms.

    Implementations: YouTube (current), LinkedIn, Medium, WordPress,
    Twitter/X, Facebook, Instagram, TikTok, Podcast (future).

    The publisher consumes a ``PublishingTask`` and produces a
    ``PublishingReport``.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g. "youtube", "linkedin")."""

    @property
    @abstractmethod
    def platform(self) -> Any:
        """Return the ``PublishingPlatform`` enum value."""

    @abstractmethod
    async def authenticate(self, config: PlatformConfig) -> AuthCredential:
        """Authenticate with the platform.

        Args:
            config: Platform configuration with credentials.

        Returns:
            An ``AuthCredential`` with access/refresh tokens.
        """

    @abstractmethod
    async def validate(self, task: PublishingTask) -> list[str]:
        """Validate the task for this platform.

        Args:
            task: The publishing task to validate.

        Returns:
            List of validation errors (empty if valid).
        """

    @abstractmethod
    async def prepare(self, task: PublishingTask) -> PublishingTask:
        """Prepare assets for upload.

        Args:
            task: The publishing task to prepare.

        Returns:
            The prepared task (may have modified paths/metadata).
        """

    @abstractmethod
    async def publish(self, task: PublishingTask, credential: AuthCredential) -> PublishingReport:
        """Publish the video to the platform.

        Args:
            task: The publishing task.
            credential: Authentication credential.

        Returns:
            A ``PublishingReport`` with the result.
        """

    @abstractmethod
    async def schedule(self, task: PublishingTask, scheduled_at: Any, credential: AuthCredential) -> PublishingReport:
        """Schedule publishing for a future time.

        Args:
            task: The publishing task.
            scheduled_at: When to publish.
            credential: Authentication credential.

        Returns:
            A ``PublishingReport`` with scheduling result.
        """

    @abstractmethod
    async def cancel(self, task_id: Any, credential: AuthCredential) -> bool:
        """Cancel a scheduled or in-progress publish.

        Args:
            task_id: The task or video ID to cancel.
            credential: Authentication credential.

        Returns:
            ``True`` if cancellation was successful.
        """

    @abstractmethod
    async def monitor(self, task: PublishingTask) -> PublishingProgress:
        """Monitor publishing progress.

        Args:
            task: The publishing task to monitor.

        Returns:
            Current ``PublishingProgress``.
        """

    @abstractmethod
    async def collect_metrics(self, task: PublishingTask) -> PublishingMetrics:
        """Collect publishing metrics after completion.

        Args:
            task: The completed publishing task.

        Returns:
            ``PublishingMetrics`` with performance data.
        """
