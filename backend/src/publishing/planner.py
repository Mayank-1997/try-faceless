"""Publishing Planner.

Responsibilities:
- Validate ProjectPackage
- Prepare publishing metadata
- Prepare platform-specific assets
- Generate publishing tasks
- Validate provider requirements
- Estimate publishing time
- Generate PublishingPlan
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from src.publishing.metadata import MetadataEngine
from src.publishing.schema import (
    FailoverStrategy,
    PlatformConfig,
    PublishingMetadata,
    PublishingMode,
    PublishingPlan,
    PublishingPlatform,
    PublishingPriority,
    PublishingStrategy,
    PublishingTask,
    RetryStrategy,
    ScheduleConfig,
    ThumbnailSpec,
)
from src.publishing.thumbnail import ThumbnailManager
from src.publishing.validator import PublishingValidator
from src.core.logging import get_logger


class PublishingPlanner:
    """Generates a PublishingPlan from a ProjectPackage.

    The planner validates the package, generates platform-specific
    metadata, creates publishing tasks for each target platform, and
    estimates publishing time.
    """

    def __init__(
        self,
        metadata_engine: MetadataEngine | None = None,
        thumbnail_manager: ThumbnailManager | None = None,
        validator: PublishingValidator | None = None,
    ) -> None:
        self._metadata_engine = metadata_engine or MetadataEngine()
        self._thumbnail_manager = thumbnail_manager or ThumbnailManager()
        self._validator = validator or PublishingValidator()
        self._logger = get_logger(__name__)

    def plan(
        self,
        project_package: Any,
        strategy: PublishingStrategy,
        *,
        project_metadata: dict[str, Any] | None = None,
    ) -> PublishingPlan:
        """Generate a publishing plan from a project package.

        Args:
            project_package: The completed ProjectPackage from Phase 10.
            strategy: Publishing strategy configuration.
            project_metadata: Additional metadata (title, description, keywords).

        Returns:
            A ``PublishingPlan`` with tasks for each platform.
        """
        project_metadata = project_metadata or {}

        # 1. Validate ProjectPackage
        package_errors = self._validator.validate_project_package(project_package)
        if package_errors:
            self._logger.error("project_package_invalid", errors=package_errors)

        # 2. Prepare publishing metadata
        raw_title = project_metadata.get("title", project_package.metadata.get("title", ""))
        raw_description = project_metadata.get("description", "")
        raw_keywords = project_metadata.get("keywords", [])
        category = project_metadata.get("category", "")
        language = project_metadata.get("language", "en")

        # 3. Generate tasks for each platform
        tasks: list[PublishingTask] = []
        thumbnail_specs: dict[str, ThumbnailSpec] = {}

        for platform in strategy.platforms:
            # Generate platform-specific metadata
            metadata = self._metadata_engine.generate_metadata(
                title=raw_title,
                description=raw_description,
                keywords=raw_keywords,
                category=category,
                language=language,
                platform=platform,
                project_metadata=project_metadata,
            )

            # Apply privacy and other settings
            metadata.privacy_status = project_metadata.get("privacy_status", "private")
            metadata.license = project_metadata.get("license", "youtube")
            metadata.made_for_kids = project_metadata.get("made_for_kids", False)
            metadata.playlist_id = project_metadata.get("playlist_id")

            # Get thumbnail spec
            spec = self._thumbnail_manager.get_spec(platform)
            thumbnail_specs[platform.value] = spec

            # Create task
            task = PublishingTask(
                id=uuid4(),
                plan_id=uuid4(),  # Will be updated with plan ID
                platform=platform,
                mode=strategy.mode,
                metadata=metadata,
                video_path=project_package.final_video_path,
                thumbnail_path=project_package.thumbnail_path or "",
                scheduled_at=strategy.schedule.scheduled_at if strategy.mode == PublishingMode.SCHEDULED else None,
                priority=PublishingPriority.NORMAL,
                max_retries=strategy.max_retries,
                retry_strategy=strategy.retry_strategy,
            )
            tasks.append(task)

        # 4. Validate each task
        all_errors: list[str] = list(package_errors)
        all_warnings: list[str] = []

        for task in tasks:
            errors, warnings = self._validator.validate_task(task)
            all_errors.extend([f"[{task.platform.value}] {e}" for e in errors])
            all_warnings.extend([f"[{task.platform.value}] {w}" for w in warnings])

        # 5. Estimate publishing time
        estimated_time = self._estimate_publishing_time(tasks, project_package)

        # 6. Generate plan
        plan = PublishingPlan(
            id=uuid4(),
            project_id=project_package.project_id,
            project_package_id=project_package.id,
            tasks=tasks,
            mode=strategy.mode,
            failover_strategy=strategy.failover_strategy,
            estimated_publishing_time=estimated_time,
            platform_count=len(tasks),
            thumbnail_specs=thumbnail_specs,
            validation_errors=all_errors,
            validation_warnings=all_warnings,
        )

        # Update task plan_ids
        for task in tasks:
            task.plan_id = plan.id

        self._logger.info(
            "publishing_plan_generated",
            plan_id=str(plan.id),
            project_id=plan.project_id,
            task_count=len(tasks),
            estimated_time=estimated_time,
            errors=len(all_errors),
        )

        return plan

    def _estimate_publishing_time(self, tasks: list[PublishingTask], project_package: Any) -> float:
        """Estimate total publishing time.

        Args:
            tasks: Publishing tasks.
            project_package: The project package.

        Returns:
            Estimated time in seconds.
        """
        video_size = 0
        if hasattr(project_package, "final_video_path") and project_package.final_video_path:
            if os.path.exists(project_package.final_video_path):
                video_size = os.path.getsize(project_package.final_video_path)

        # Rough estimate: 10MB/s upload speed
        upload_time = video_size / (10 * 1024 * 1024) if video_size else 5.0
        per_task_overhead = 2.0  # Auth, metadata, thumbnail
        thumbnail_time = 1.0

        total = 0.0
        for task in tasks:
            total += upload_time + per_task_overhead
            if task.thumbnail_path:
                total += thumbnail_time

        return max(total, len(tasks) * 3.0)  # At least 3s per task
