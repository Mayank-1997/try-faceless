"""YouTube Publisher.

Supports:
- Video upload
- Thumbnail upload
- Title, Description, Tags, Category, Language
- Privacy (public, unlisted, private)
- Playlist
- Audience settings (made for kids)
- License
- Publish immediately
- Schedule publishing
- Save draft
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.publishing.publisher import Publisher
from src.publishing.schema import (
    AuthCredential,
    AuthMethod,
    PlatformConfig,
    PublishingJobStatus,
    PublishingMetadata,
    PublishingMetrics,
    PublishingMode,
    PublishingPlatform,
    PublishingProgress,
    PublishingReport,
    PublishingTask,
)
from src.publishing.thumbnail import ThumbnailManager
from src.publishing.validator import PublishingValidator
from src.core.logging import get_logger


class YouTubePublisher(Publisher):
    """YouTube publishing implementation.

    Uploads videos to YouTube via the YouTube Data API v3.
    Supports video upload, thumbnail upload, metadata management,
    scheduling, and draft mode.

    Note: The actual API calls require the ``google-api-python-client``
    and ``google-auth-oauthlib`` packages. This implementation provides
    the full interface with simulated API calls for testability.
    """

    YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]

    def __init__(
        self,
        validator: PublishingValidator | None = None,
        thumbnail_manager: ThumbnailManager | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._validator = validator or PublishingValidator()
        self._thumbnail_manager = thumbnail_manager or ThumbnailManager()
        self._upload_progress: dict[UUID, float] = {}
        self._cancelled: set[UUID] = set()

    @property
    def platform_name(self) -> str:
        return "youtube"

    @property
    def platform(self) -> PublishingPlatform:
        return PublishingPlatform.YOUTUBE

    async def authenticate(self, config: PlatformConfig) -> AuthCredential:
        """Authenticate with YouTube via OAuth2.

        Args:
            config: Platform configuration with OAuth2 credentials.

        Returns:
            An ``AuthCredential`` with access/refresh tokens.

        Raises:
            ValueError: If required credentials are missing.
        """
        if not config.client_id:
            raise ValueError("YouTube requires client_id for OAuth2")

        # Simulate OAuth2 token exchange
        from datetime import timedelta
        credential = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            auth_method=AuthMethod.OAUTH2,
            access_token=f"ya29.{config.client_id[:8]}_{int(datetime.now(timezone.utc).timestamp())}",
            refresh_token=config.refresh_token or f"1//{config.client_id[:8]}_refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=self.YOUTUBE_SCOPES,
            metadata={"client_id": config.client_id},
        )

        self._logger.info("youtube_authenticated", client_id=config.client_id[:8])
        return credential

    async def validate(self, task: PublishingTask) -> list[str]:
        """Validate a task for YouTube.

        Args:
            task: The publishing task to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors, _ = self._validator.validate_task(task)
        return errors

    async def prepare(self, task: PublishingTask) -> PublishingTask:
        """Prepare assets for YouTube upload.

        Args:
            task: The publishing task to prepare.

        Returns:
            The prepared task.
        """
        # Validate thumbnail if provided
        if task.thumbnail_path:
            thumb_errors = self._thumbnail_manager.validate_thumbnail(
                task.thumbnail_path, PublishingPlatform.YOUTUBE
            )
            if thumb_errors:
                self._logger.warning(
                    "thumbnail_validation_issues",
                    task_id=str(task.id),
                    errors=thumb_errors,
                )

        # Set default YouTube metadata if not configured
        if not task.metadata.category:
            task.metadata.category = "27"  # Education
        if not task.metadata.license:
            task.metadata.license = "youtube"
        if not task.metadata.privacy_status:
            task.metadata.privacy_status = "private"

        self._logger.info("youtube_task_prepared", task_id=str(task.id))
        return task

    async def publish(self, task: PublishingTask, credential: AuthCredential) -> PublishingReport:
        """Publish a video to YouTube.

        Args:
            task: The publishing task.
            credential: Authentication credential.

        Returns:
            A ``PublishingReport`` with the result.
        """
        start_time = datetime.now(timezone.utc)
        report = PublishingReport(
            plan_id=task.plan_id,
            project_id=task.metadata.platform_metadata.get("project_id", ""),
            platform=PublishingPlatform.YOUTUBE,
        )

        try:
            # Check cancellation
            if task.id in self._cancelled:
                report.status = PublishingJobStatus.CANCELLED
                report.errors.append("Publishing was cancelled")
                return report

            # Validate
            errors = await self.validate(task)
            if errors:
                report.status = PublishingJobStatus.FAILED
                report.errors.extend(errors)
                return report

            # Prepare
            task = await self.prepare(task)

            # Simulate video upload
            report.status = PublishingJobStatus.UPLOADING
            video_size = os.path.getsize(task.video_path) if os.path.exists(task.video_path) else 0
            await self._simulate_upload(task.id, video_size)

            # Simulate video processing
            report.status = PublishingJobStatus.PUBLISHING
            await asyncio.sleep(0.1)

            # Generate video ID and URL
            video_id = f"vid_{task.id.hex[:11]}"
            report.video_id = video_id
            report.video_url = f"https://www.youtube.com/watch?v={video_id}"
            report.upload_duration_seconds = 2.0
            report.publish_duration_seconds = 0.5

            # Upload thumbnail if provided
            if task.thumbnail_path and os.path.exists(task.thumbnail_path):
                report.status = PublishingJobStatus.THUMBNAIL_UPLOADING
                await asyncio.sleep(0.1)
                report.thumbnail_uploaded = True

            # Update metadata
            report.status = PublishingJobStatus.METADATA_UPDATING
            await asyncio.sleep(0.05)
            report.metadata_updated = True

            # Handle mode
            if task.mode == PublishingMode.DRAFT:
                report.status = PublishingJobStatus.DRAFT_SAVED
            elif task.mode == PublishingMode.SCHEDULED and task.scheduled_at:
                report.status = PublishingJobStatus.SCHEDULED
            else:
                report.status = PublishingJobStatus.COMPLETED

            report.provider_response = {
                "id": video_id,
                "kind": "youtube#video",
                "status": {
                    "uploadStatus": "processed",
                    "privacyStatus": task.metadata.privacy_status,
                    "embeddable": task.metadata.embeddable,
                    "license": task.metadata.license,
                },
                "snippet": {
                    "title": task.metadata.title,
                    "description": task.metadata.description[:200],
                    "tags": task.metadata.tags[:10],
                    "categoryId": task.metadata.category,
                    "defaultLanguage": task.metadata.language,
                },
            }

            report.total_duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

            self._logger.info(
                "youtube_published",
                task_id=str(task.id),
                video_id=video_id,
                status=report.status.value,
            )

        except Exception as exc:
            report.status = PublishingJobStatus.FAILED
            report.errors.append(str(exc))
            self._logger.error("youtube_publish_failed", task_id=str(task.id), error=str(exc))

        return report

    async def schedule(
        self, task: PublishingTask, scheduled_at: datetime, credential: AuthCredential
    ) -> PublishingReport:
        """Schedule a YouTube video for future publishing.

        Args:
            task: The publishing task.
            scheduled_at: When to publish.
            credential: Authentication credential.

        Returns:
            A ``PublishingReport`` with scheduling result.
        """
        task.mode = PublishingMode.SCHEDULED
        task.scheduled_at = scheduled_at
        task.metadata.privacy_status = "private"  # Start as private

        # Upload as private first
        report = await self.publish(task, credential)

        if report.status not in (PublishingJobStatus.FAILED, PublishingJobStatus.CANCELLED):
            report.status = PublishingJobStatus.SCHEDULED
            report.provider_response["scheduled_at"] = scheduled_at.isoformat()
            report.warnings.append(
                f"Video scheduled for {scheduled_at.isoformat()}. "
                "Privacy will be updated at scheduled time."
            )

        return report

    async def cancel(self, task_id: UUID, credential: AuthCredential) -> bool:
        """Cancel a YouTube publishing operation.

        Args:
            task_id: The task ID to cancel.
            credential: Authentication credential.

        Returns:
            ``True`` if cancellation was successful.
        """
        self._cancelled.add(task_id)
        self._logger.info("youtube_cancelled", task_id=str(task_id))
        return True

    async def monitor(self, task: PublishingTask) -> PublishingProgress:
        """Monitor YouTube publishing progress.

        Args:
            task: The publishing task to monitor.

        Returns:
            Current ``PublishingProgress``.
        """
        progress = PublishingProgress(task_id=task.id)
        upload_pct = self._upload_progress.get(task.id, 0.0)

        if task.status == PublishingJobStatus.QUEUED:
            progress.status = PublishingJobStatus.QUEUED
            progress.current_stage = "queued"
        elif task.status == PublishingJobStatus.UPLOADING:
            progress.status = PublishingJobStatus.UPLOADING
            progress.current_stage = "uploading"
            progress.upload_progress = upload_pct
            progress.progress_percentage = upload_pct * 0.8  # Upload is 80% of work
        elif task.status == PublishingJobStatus.COMPLETED:
            progress.status = PublishingJobStatus.COMPLETED
            progress.current_stage = "completed"
            progress.progress_percentage = 100.0
        elif task.status == PublishingJobStatus.FAILED:
            progress.status = PublishingJobStatus.FAILED
            progress.current_stage = "failed"
        else:
            progress.status = task.status
            progress.current_stage = task.status.value

        return progress

    async def collect_metrics(self, task: PublishingTask) -> PublishingMetrics:
        """Collect YouTube publishing metrics.

        Args:
            task: The completed publishing task.

        Returns:
            ``PublishingMetrics`` with performance data.
        """
        video_size = 0
        if task.video_path and os.path.exists(task.video_path):
            video_size = os.path.getsize(task.video_path)

        return PublishingMetrics(
            upload_speed_mbps=video_size / (2.0 * 1024 * 1024) if video_size else 0.0,
            upload_bytes=video_size,
            thumbnail_upload_time_seconds=0.1 if task.thumbnail_path else 0.0,
            metadata_update_time_seconds=0.05,
            total_api_calls=3,
            failed_api_calls=0,
            retry_count=task.retry_count,
        )

    async def _simulate_upload(self, task_id: UUID, file_size: int) -> None:
        """Simulate an upload with progress tracking."""
        steps = 10
        for i in range(steps + 1):
            if task_id in self._cancelled:
                raise asyncio.CancelledError("Upload cancelled")
            progress = (i / steps) * 100.0
            self._upload_progress[task_id] = progress
            await asyncio.sleep(0.05)
        self._upload_progress[task_id] = 100.0
