"""Usage Tracking Service.

Tracks:
- Images generated
- Videos generated
- Voice minutes
- Rendering minutes
- Storage usage
- Bandwidth
- Projects created
- Publishing count
- Token usage
- Provider usage
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.platform.schema import UsageRecord, UsageResourceType, UsageSummary
from src.core.logging import get_logger


class UsageTracker:
    """Tracks resource usage for users and organizations.

    Records individual usage events and provides aggregated summaries
    for billing, quota enforcement, and dashboards.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._records: list[UsageRecord] = []

    def record(self, record: UsageRecord) -> None:
        """Record a usage event.

        Args:
            record: The usage record to store.
        """
        self._records.append(record)
        self._logger.info(
            "usage_recorded",
            user_id=record.user_id,
            resource_type=record.resource_type.value,
            amount=record.amount,
        )

    def record_image_generation(self, user_id: str, count: int = 1, **kwargs: Any) -> None:
        """Record image generation usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.IMAGES,
            amount=count,
            unit="images",
            **kwargs,
        ))

    def record_video_generation(self, user_id: str, count: int = 1, **kwargs: Any) -> None:
        """Record video generation usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.VIDEOS,
            amount=count,
            unit="videos",
            **kwargs,
        ))

    def record_voice_minutes(self, user_id: str, minutes: float, **kwargs: Any) -> None:
        """Record voice generation usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.VOICE_MINUTES,
            amount=minutes,
            unit="minutes",
            **kwargs,
        ))

    def record_rendering_minutes(self, user_id: str, minutes: float, **kwargs: Any) -> None:
        """Record rendering usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.RENDERING_MINUTES,
            amount=minutes,
            unit="minutes",
            **kwargs,
        ))

    def record_storage(self, user_id: str, bytes_used: int, **kwargs: Any) -> None:
        """Record storage usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.STORAGE,
            amount=bytes_used,
            unit="bytes",
            **kwargs,
        ))

    def record_publishing(self, user_id: str, count: int = 1, **kwargs: Any) -> None:
        """Record publishing usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.PUBLISHING,
            amount=count,
            unit="publishes",
            **kwargs,
        ))

    def record_tokens(self, user_id: str, tokens: int, **kwargs: Any) -> None:
        """Record token usage."""
        self.record(UsageRecord(
            user_id=user_id,
            resource_type=UsageResourceType.TOKENS,
            amount=tokens,
            unit="tokens",
            **kwargs,
        ))

    def get_summary(
        self,
        user_id: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> UsageSummary:
        """Get aggregated usage summary for a user.

        Args:
            user_id: The user ID.
            start: Optional period start.
            end: Optional period end.

        Returns:
            A ``UsageSummary`` with aggregated usage.
        """
        records = [
            r for r in self._records
            if r.user_id == user_id
            and (start is None or r.timestamp >= start)
            and (end is None or r.timestamp <= end)
        ]

        summary = UsageSummary(user_id=user_id, period_start=start, period_end=end)
        provider_usage: dict[str, int] = defaultdict(int)

        for r in records:
            if r.resource_type == UsageResourceType.IMAGES:
                summary.images_generated += int(r.amount)
            elif r.resource_type == UsageResourceType.VIDEOS:
                summary.videos_generated += int(r.amount)
            elif r.resource_type == UsageResourceType.VOICE_MINUTES:
                summary.voice_minutes += r.amount
            elif r.resource_type == UsageResourceType.RENDERING_MINUTES:
                summary.rendering_minutes += r.amount
            elif r.resource_type == UsageResourceType.STORAGE:
                summary.storage_bytes = max(summary.storage_bytes, int(r.amount))
            elif r.resource_type == UsageResourceType.BANDWIDTH:
                summary.bandwidth_bytes += int(r.amount)
            elif r.resource_type == UsageResourceType.PROJECTS:
                summary.projects_created += int(r.amount)
            elif r.resource_type == UsageResourceType.PUBLISHING:
                summary.publishing_count += int(r.amount)
            elif r.resource_type == UsageResourceType.TOKENS:
                summary.token_usage += int(r.amount)
            elif r.resource_type == UsageResourceType.PROVIDER_CALLS:
                if r.provider:
                    provider_usage[r.provider] += int(r.amount)

        summary.provider_usage = dict(provider_usage)
        return summary

    def get_org_summary(
        self,
        org_id: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> UsageSummary:
        """Get aggregated usage summary for an organization.

        Args:
            org_id: The organization ID.
            start: Optional period start.
            end: Optional period end.

        Returns:
            A ``UsageSummary`` with aggregated usage.
        """
        records = [
            r for r in self._records
            if r.org_id == org_id
            and (start is None or r.timestamp >= start)
            and (end is None or r.timestamp <= end)
        ]

        summary = UsageSummary(org_id=org_id, period_start=start, period_end=end)
        provider_usage: dict[str, int] = defaultdict(int)

        for r in records:
            if r.resource_type == UsageResourceType.IMAGES:
                summary.images_generated += int(r.amount)
            elif r.resource_type == UsageResourceType.VIDEOS:
                summary.videos_generated += int(r.amount)
            elif r.resource_type == UsageResourceType.VOICE_MINUTES:
                summary.voice_minutes += r.amount
            elif r.resource_type == UsageResourceType.RENDERING_MINUTES:
                summary.rendering_minutes += r.amount
            elif r.resource_type == UsageResourceType.STORAGE:
                summary.storage_bytes += int(r.amount)
            elif r.resource_type == UsageResourceType.BANDWIDTH:
                summary.bandwidth_bytes += int(r.amount)
            elif r.resource_type == UsageResourceType.PROJECTS:
                summary.projects_created += int(r.amount)
            elif r.resource_type == UsageResourceType.PUBLISHING:
                summary.publishing_count += int(r.amount)
            elif r.resource_type == UsageResourceType.TOKENS:
                summary.token_usage += int(r.amount)
            elif r.resource_type == UsageResourceType.PROVIDER_CALLS:
                if r.provider:
                    provider_usage[r.provider] += int(r.amount)

        summary.provider_usage = dict(provider_usage)
        return summary

    @property
    def record_count(self) -> int:
        """Total number of usage records."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all records (primarily for testing)."""
        self._records.clear()
