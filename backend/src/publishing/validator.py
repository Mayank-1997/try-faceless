"""Publishing Validator.

Validates:
- Video format
- Thumbnail
- Metadata
- Title length
- Description limits
- Platform requirements
- Authentication
- Scheduling
"""

from __future__ import annotations

import os
from typing import Any

from src.publishing.metadata import MetadataEngine
from src.publishing.schema import (
    AuthCredential,
    PlatformRequirements,
    PublishingJobStatus,
    PublishingMetadata,
    PublishingMode,
    PublishingPlatform,
    PublishingTask,
    ScheduleConfig,
)
from src.publishing.thumbnail import ThumbnailManager
from src.core.logging import get_logger


class PublishingValidator:
    """Validates publishing tasks before execution.

    Performs comprehensive checks on video files, thumbnails, metadata,
    authentication, and scheduling to ensure a task is ready for publishing.
    """

    # Platform requirements
    PLATFORM_REQUIREMENTS: dict[PublishingPlatform, PlatformRequirements] = {
        PublishingPlatform.YOUTUBE: PlatformRequirements(
            platform=PublishingPlatform.YOUTUBE,
            max_title_length=100,
            max_description_length=5000,
            max_tags=500,
            max_tag_length=30,
            supported_video_formats=["mp4", "mov", "avi", "wmv", "flv", "mkv", "webm"],
            max_video_size_bytes=256 * 1024 * 1024 * 1024,
            thumbnail_width=1280,
            thumbnail_height=720,
            thumbnail_formats=["jpg", "png", "bmp"],
            thumbnail_max_size_bytes=2 * 1024 * 1024,
            requires_auth=True,
            requires_thumbnail=False,
        ),
        PublishingPlatform.LINKEDIN: PlatformRequirements(
            platform=PublishingPlatform.LINKEDIN,
            max_title_length=100,
            max_description_length=3000,
            max_tags=50,
            max_tag_length=60,
            supported_video_formats=["mp4", "mov", "avi"],
            max_video_size_bytes=5 * 1024 * 1024 * 1024,
            thumbnail_width=1200,
            thumbnail_height=627,
            thumbnail_formats=["jpg", "png"],
            thumbnail_max_size_bytes=5 * 1024 * 1024,
            requires_auth=True,
            requires_thumbnail=True,
        ),
        PublishingPlatform.TWITTER: PlatformRequirements(
            platform=PublishingPlatform.TWITTER,
            max_title_length=100,
            max_description_length=1000,
            max_tags=30,
            max_tag_length=50,
            supported_video_formats=["mp4", "mov"],
            max_video_size_bytes=512 * 1024 * 1024,
            thumbnail_width=1200,
            thumbnail_height=675,
            thumbnail_formats=["jpg", "png"],
            thumbnail_max_size_bytes=5 * 1024 * 1024,
            requires_auth=True,
            requires_thumbnail=True,
        ),
    }

    def __init__(
        self,
        metadata_engine: MetadataEngine | None = None,
        thumbnail_manager: ThumbnailManager | None = None,
    ) -> None:
        self._metadata_engine = metadata_engine or MetadataEngine()
        self._thumbnail_manager = thumbnail_manager or ThumbnailManager()
        self._logger = get_logger(__name__)

    def get_requirements(self, platform: PublishingPlatform) -> PlatformRequirements:
        """Get requirements for a platform.

        Args:
            platform: Target platform.

        Returns:
            ``PlatformRequirements`` for the platform.
        """
        return self.PLATFORM_REQUIREMENTS.get(
            platform,
            PlatformRequirements(platform=platform),
        )

    def validate_task(self, task: PublishingTask) -> tuple[list[str], list[str]]:
        """Validate a publishing task comprehensively.

        Args:
            task: The publishing task to validate.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Video format validation
        video_errors = self._validate_video(task)
        errors.extend(video_errors)

        # 2. Thumbnail validation
        thumb_errors, thumb_warnings = self._validate_thumbnail(task)
        errors.extend(thumb_errors)
        warnings.extend(thumb_warnings)

        # 3. Metadata validation
        meta_errors = self._validate_metadata(task)
        errors.extend(meta_errors)

        # 4. Title length
        title_errors = self._validate_title(task)
        errors.extend(title_errors)

        # 5. Description limits
        desc_errors = self._validate_description(task)
        errors.extend(desc_errors)

        # 6. Platform requirements
        platform_errors = self._validate_platform_requirements(task)
        errors.extend(platform_errors)

        # 7. Authentication validation
        auth_warnings = self._validate_auth(task)
        warnings.extend(auth_warnings)

        # 8. Scheduling validation
        sched_errors = self._validate_scheduling(task)
        errors.extend(sched_errors)

        self._logger.info(
            "task_validated",
            task_id=str(task.id),
            platform=task.platform.value,
            errors=len(errors),
            warnings=len(warnings),
        )

        return errors, warnings

    def _validate_video(self, task: PublishingTask) -> list[str]:
        """Validate the video file."""
        errors: list[str] = []
        req = self.get_requirements(task.platform)

        if not task.video_path:
            errors.append("Video path is empty")
            return errors

        if not os.path.exists(task.video_path):
            errors.append(f"Video file not found: {task.video_path}")
            return errors

        file_size = os.path.getsize(task.video_path)
        if file_size == 0:
            errors.append("Video file is empty")
        elif file_size > req.max_video_size_bytes:
            errors.append(
                f"Video size {file_size} bytes exceeds limit {req.max_video_size_bytes} bytes"
            )

        ext = os.path.splitext(task.video_path)[1].lower().lstrip(".")
        if ext and ext not in req.supported_video_formats:
            errors.append(
                f"Unsupported video format: {ext}. Supported: {', '.join(req.supported_video_formats)}"
            )

        return errors

    def _validate_thumbnail(self, task: PublishingTask) -> tuple[list[str], list[str]]:
        """Validate the thumbnail."""
        errors: list[str] = []
        warnings: list[str] = []
        req = self.get_requirements(task.platform)

        if not task.thumbnail_path:
            if req.requires_thumbnail:
                errors.append("Thumbnail is required for this platform")
            else:
                warnings.append("No thumbnail provided (optional for this platform)")
            return errors, warnings

        thumb_errors = self._thumbnail_manager.validate_thumbnail(task.thumbnail_path, task.platform)
        errors.extend(thumb_errors)

        return errors, warnings

    def _validate_metadata(self, task: PublishingTask) -> list[str]:
        """Validate metadata for the platform."""
        return self._metadata_engine.validate_metadata(task.metadata, task.platform)

    def _validate_title(self, task: PublishingTask) -> list[str]:
        """Validate title length."""
        errors: list[str] = []
        req = self.get_requirements(task.platform)

        if not task.metadata.title:
            errors.append("Title is required")
        elif len(task.metadata.title) > req.max_title_length:
            errors.append(
                f"Title exceeds {req.max_title_length} characters (got {len(task.metadata.title)})"
            )

        return errors

    def _validate_description(self, task: PublishingTask) -> list[str]:
        """Validate description length."""
        errors: list[str] = []
        req = self.get_requirements(task.platform)

        if len(task.metadata.description) > req.max_description_length:
            errors.append(
                f"Description exceeds {req.max_description_length} characters "
                f"(got {len(task.metadata.description)})"
            )

        return errors

    def _validate_platform_requirements(self, task: PublishingTask) -> list[str]:
        """Validate platform-specific requirements."""
        errors: list[str] = []
        req = self.get_requirements(task.platform)

        if len(task.metadata.tags) > req.max_tags:
            errors.append(f"Too many tags: {len(task.metadata.tags)} (max {req.max_tags})")

        for tag in task.metadata.tags:
            if len(tag) > req.max_tag_length:
                errors.append(f"Tag '{tag}' exceeds {req.max_tag_length} characters")

        return errors

    def _validate_auth(self, task: PublishingTask) -> list[str]:
        """Validate authentication (returns warnings)."""
        warnings: list[str] = []
        req = self.get_requirements(task.platform)

        if req.requires_auth:
            warnings.append("Authentication required — ensure credentials are configured")

        return warnings

    def _validate_scheduling(self, task: PublishingTask) -> list[str]:
        """Validate scheduling configuration."""
        errors: list[str] = []

        if task.mode == PublishingMode.SCHEDULED:
            if task.scheduled_at is None:
                errors.append("Scheduled mode requires a scheduled_at datetime")
            else:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if task.scheduled_at <= now:
                    errors.append("Scheduled time must be in the future")

        return errors

    def validate_project_package(self, package: Any) -> list[str]:
        """Validate that a ProjectPackage is ready for publishing.

        Args:
            package: The ProjectPackage to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not hasattr(package, "final_video_path"):
            errors.append("ProjectPackage missing final_video_path")
            return errors

        if not package.final_video_path:
            errors.append("ProjectPackage has no final video path")
        elif not os.path.exists(package.final_video_path):
            errors.append(f"Final video not found: {package.final_video_path}")

        if not hasattr(package, "quality_report") or not package.quality_report.overall_pass:
            errors.append("ProjectPackage quality report indicates failures")

        if not package.project_id:
            errors.append("ProjectPackage has no project_id")

        return errors
