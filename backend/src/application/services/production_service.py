"""Production service — composition, rendering, and publishing operations.

This service bridges the composition, rendering, and publishing subsystems
with the FastAPI presentation layer.  It exposes operations for:

- Composition management (build, get, update timeline)
- Render queue management (submit, cancel, list, progress)
- Preview generation
- Publishing (create plan, execute, schedule, cancel, list)
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from src.composition.builder import CompositionBuilder
from src.composition.export import ExportEngine
from src.composition.pipeline import RenderingPipeline
from src.composition.preview import PreviewEngine
from src.composition.render_queue import RenderQueue
from src.composition.schema import (
    CompositionDocument,
    ExportProfile,
    PreviewResult,
    ProjectPackage,
    RenderJob,
    RenderPriority,
    RenderProgress,
    RenderStatus,
    Timeline,
)
from src.composition.validator import CompositionValidator
from src.core.exceptions import EntityNotFoundError, ValidationError
from src.core.logging import get_logger
from src.publishing.schema import (
    PublishingJob,
    PublishingMetadata,
    PublishingMode,
    PublishingPlan,
    PublishingPlatform,
    PublishingReport,
    PublishingTask,
)
from src.publishing.queue import PublishingQueue


# ---------------------------------------------------------------------------
# Response models (lightweight DTOs for the API layer)
# ---------------------------------------------------------------------------
class CompositionResponse(BaseModel):
    id: str
    project_id: str
    version: int
    timeline: dict[str, Any]
    scenes: list[dict[str, Any]]
    export_profile: dict[str, Any]
    total_duration: float
    scene_count: int
    track_count: int
    is_valid: bool
    created_at: str
    metadata: dict[str, Any]


class RenderJobResponse(BaseModel):
    id: str
    composition_id: str
    project_id: str
    status: str
    priority: str
    output_path: str
    retry_count: int
    max_retries: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0
    metadata: dict[str, Any] = {}


class RenderProgressResponse(BaseModel):
    job_id: str
    status: str
    progress_percentage: float
    current_stage: str
    stages_completed: list[str]
    estimated_time_remaining: float
    frames_processed: int
    total_frames: int


class ProjectPackageResponse(BaseModel):
    id: str
    project_id: str
    final_video_path: str
    final_video_uri: str
    thumbnail_path: str
    thumbnail_uri: str
    subtitle_files: list[str]
    is_complete: bool
    render_report: dict[str, Any]
    quality_report: dict[str, Any]
    created_at: str
    version: int


class PreviewResponse(BaseModel):
    preview_path: str
    preview_uri: str
    resolution: str
    duration_seconds: float
    file_size_bytes: int


class PublishingTaskResponse(BaseModel):
    id: str
    plan_id: str
    platform: str
    mode: str
    metadata: dict[str, Any]
    video_path: str
    thumbnail_path: str
    scheduled_at: str | None = None
    status: str
    priority: str
    retry_count: int
    max_retries: int
    error: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    execution_time_seconds: float = 0.0


class PublishingPlanResponse(BaseModel):
    id: str
    project_id: str
    tasks: list[PublishingTaskResponse]
    mode: str
    platform_count: int
    validation_errors: list[str]
    validation_warnings: list[str]
    created_at: str


class PublishingJobResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    platform: str
    status: str
    priority: str
    scheduled_at: str | None = None
    retry_count: int
    max_retries: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0


class PublishingReportResponse(BaseModel):
    id: str
    plan_id: str
    project_id: str
    platform: str
    status: str
    video_url: str
    video_id: str
    upload_duration_seconds: float
    publish_duration_seconds: float
    total_duration_seconds: float
    warnings: list[str]
    errors: list[str]
    thumbnail_uploaded: bool
    metadata_updated: bool
    created_at: str


class MessageResponse(BaseModel):
    message: str


class CreateRenderRequest(BaseModel):
    composition_id: str
    priority: str = "normal"
    output_path: str = ""


class CreatePublishingRequest(BaseModel):
    platform: str = "youtube"
    mode: str = "publish"
    metadata: dict[str, Any] = {}
    scheduled_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _composition_to_response(comp: CompositionDocument) -> CompositionResponse:
    return CompositionResponse(
        id=str(comp.id),
        project_id=comp.project_id,
        version=comp.version,
        timeline=comp.timeline.model_dump(),
        scenes=[s.model_dump() for s in comp.scenes],
        export_profile=comp.export_profile.model_dump(),
        total_duration=comp.total_duration,
        scene_count=comp.scene_count,
        track_count=comp.track_count,
        is_valid=comp.is_valid,
        created_at=comp.created_at.isoformat(),
        metadata=comp.metadata,
    )


def _render_job_to_response(job: RenderJob) -> RenderJobResponse:
    return RenderJobResponse(
        id=str(job.id),
        composition_id=str(job.composition_id),
        project_id=job.project_id,
        status=job.status.value,
        priority=job.priority.name.lower(),
        output_path=job.output_path,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
        execution_time_seconds=job.execution_time_seconds,
        metadata=job.metadata,
    )


def _publishing_task_to_response(task: PublishingTask) -> PublishingTaskResponse:
    return PublishingTaskResponse(
        id=str(task.id),
        plan_id=str(task.plan_id),
        platform=task.platform.value,
        mode=task.mode.value,
        metadata=task.metadata.model_dump(),
        video_path=task.video_path,
        thumbnail_path=task.thumbnail_path,
        scheduled_at=task.scheduled_at.isoformat() if task.scheduled_at else None,
        status=task.status.value,
        priority=task.priority.name.lower(),
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        error=task.error,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        execution_time_seconds=task.execution_time_seconds,
    )


def _publishing_job_to_response(job: PublishingJob) -> PublishingJobResponse:
    return PublishingJobResponse(
        id=str(job.id),
        task_id=str(job.task_id),
        project_id=job.project_id,
        platform=job.platform.value,
        status=job.status.value,
        priority=job.priority.name.lower(),
        scheduled_at=job.scheduled_at.isoformat() if job.scheduled_at else None,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
        execution_time_seconds=job.execution_time_seconds,
    )


def _publishing_report_to_response(report: PublishingReport) -> PublishingReportResponse:
    return PublishingReportResponse(
        id=str(report.id),
        plan_id=str(report.plan_id),
        project_id=report.project_id,
        platform=report.platform.value,
        status=report.status.value,
        video_url=report.video_url,
        video_id=report.video_id,
        upload_duration_seconds=report.upload_duration_seconds,
        publish_duration_seconds=report.publish_duration_seconds,
        total_duration_seconds=report.total_duration_seconds,
        warnings=report.warnings,
        errors=report.errors,
        thumbnail_uploaded=report.thumbnail_uploaded,
        metadata_updated=report.metadata_updated,
        created_at=report.created_at.isoformat(),
    )


def _project_package_to_response(pkg: ProjectPackage) -> ProjectPackageResponse:
    return ProjectPackageResponse(
        id=str(pkg.id),
        project_id=pkg.project_id,
        final_video_path=pkg.final_video_path,
        final_video_uri=pkg.final_video_uri,
        thumbnail_path=pkg.thumbnail_path,
        thumbnail_uri=pkg.thumbnail_uri,
        subtitle_files=pkg.subtitle_files,
        is_complete=pkg.is_complete,
        render_report=pkg.render_report.model_dump(),
        quality_report=pkg.quality_report.model_dump(),
        created_at=pkg.created_at.isoformat(),
        version=pkg.version,
    )


def _preview_to_response(preview: PreviewResult) -> PreviewResponse:
    return PreviewResponse(
        preview_path=preview.preview_path,
        preview_uri=preview.preview_uri,
        resolution=preview.resolution,
        duration_seconds=preview.duration_seconds,
        file_size_bytes=preview.file_size_bytes,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class ProductionService:
    """Service for composition, rendering, and publishing operations."""

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._builder = CompositionBuilder()
        self._validator = CompositionValidator()
        self._pipeline = RenderingPipeline()
        self._export_engine = ExportEngine()
        self._preview_engine = PreviewEngine()
        self._render_queue = RenderQueue()
        self._publishing_queue = PublishingQueue()
        self._publishing_planner = PublishingPlanner()

        # In-memory stores (would be DB-backed in production)
        self._compositions: dict[UUID, CompositionDocument] = {}
        self._project_packages: dict[UUID, ProjectPackage] = {}
        self._render_progress: dict[UUID, RenderProgress] = {}
        self._publishing_plans: dict[UUID, PublishingPlan] = {}
        self._publishing_reports: dict[UUID, PublishingReport] = {}

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------
    async def build_composition(
        self,
        project_id: str,
        *,
        export_preset: str = "1080p",
        resolution: str | None = None,
        fps: int = 30,
    ) -> CompositionResponse:
        """Build a composition document from project assets."""
        preset = self._export_engine.get_preset(export_preset)
        if preset is None:
            raise ValidationError("export_preset", f"Unknown export preset: {export_preset}")

        export_profile = preset
        if resolution:
            export_profile = export_profile.model_copy(update={"resolution": resolution})

        # Create a minimal composition (in production, builder would use AssetManifest)
        composition = CompositionDocument(
            project_id=project_id,
            export_profile=export_profile,
        )

        # Validate
        validation = await self._validator.validate(composition)
        composition.validation_metadata = validation

        self._compositions[composition.id] = composition
        return _composition_to_response(composition)

    async def get_composition(self, composition_id: UUID) -> CompositionResponse:
        """Get a composition by ID."""
        comp = self._compositions.get(composition_id)
        if comp is None:
            raise EntityNotFoundError(f"Composition {composition_id} not found")
        return _composition_to_response(comp)

    async def get_project_composition(self, project_id: str) -> CompositionResponse:
        """Get the latest composition for a project."""
        for comp in reversed(list(self._compositions.values())):
            if comp.project_id == project_id:
                return _composition_to_response(comp)
        raise EntityNotFoundError(f"No composition found for project {project_id}")

    async def update_timeline(
        self, composition_id: UUID, timeline_data: dict[str, Any]
    ) -> CompositionResponse:
        """Update the timeline of a composition."""
        comp = self._compositions.get(composition_id)
        if comp is None:
            raise EntityNotFoundError(f"Composition {composition_id} not found")

        timeline = Timeline.model_validate(timeline_data)
        comp.timeline = timeline
        comp.version += 1

        # Re-validate
        validation = await self._validator.validate(comp)
        comp.validation_metadata = validation

        return _composition_to_response(comp)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    async def submit_render(
        self,
        composition_id: UUID,
        *,
        priority: str = "normal",
        output_path: str = "",
    ) -> RenderJobResponse:
        """Submit a render job to the queue."""
        comp = self._compositions.get(composition_id)
        if comp is None:
            raise EntityNotFoundError(f"Composition {composition_id} not found")

        if not comp.is_valid:
            raise ValidationError("composition", "Composition is not valid for rendering")

        priority_map = {
            "critical": RenderPriority.CRITICAL,
            "high": RenderPriority.HIGH,
            "normal": RenderPriority.NORMAL,
            "low": RenderPriority.LOW,
            "background": RenderPriority.BACKGROUND,
        }
        render_priority = priority_map.get(priority.lower(), RenderPriority.NORMAL)

        job = RenderJob(
            composition_id=composition_id,
            project_id=comp.project_id,
            priority=render_priority,
            output_path=output_path or f"/tmp/render_{composition_id}.mp4",
        )

        job = await self._render_queue.submit(job)
        self._render_progress[job.id] = RenderProgress(job_id=job.id)

        return _render_job_to_response(job)

    async def cancel_render(self, job_id: UUID) -> MessageResponse:
        """Cancel a render job."""
        success = await self._render_queue.cancel(job_id)
        if not success:
            raise EntityNotFoundError(f"Render job {job_id} not found or not cancellable")
        return MessageResponse(message="Render job cancelled.")

    async def list_renders(
        self, project_id: str | None = None
    ) -> list[RenderJobResponse]:
        """List render jobs, optionally filtered by project."""
        all_jobs: list[RenderJob] = []
        all_jobs.extend(self._render_queue._queue)
        all_jobs.extend(self._render_queue._active.values())
        all_jobs.extend(self._render_queue._completed)
        all_jobs.extend(self._render_queue._failed)

        if project_id:
            all_jobs = [j for j in all_jobs if j.project_id == project_id]

        return [_render_job_to_response(j) for j in all_jobs]

    async def get_render_progress(self, job_id: UUID) -> RenderProgressResponse:
        """Get progress for a render job."""
        progress = self._render_progress.get(job_id)
        if progress is None:
            raise EntityNotFoundError(f"No progress for render job {job_id}")

        return RenderProgressResponse(
            job_id=str(progress.job_id),
            status=progress.status.value,
            progress_percentage=progress.progress_percentage,
            current_stage=progress.current_stage,
            stages_completed=progress.stages_completed,
            estimated_time_remaining=progress.estimated_time_remaining,
            frames_processed=progress.frames_processed,
            total_frames=progress.total_frames,
        )

    async def get_project_package(self, project_id: str) -> ProjectPackageResponse:
        """Get the project package (final output) for a project."""
        for pkg in reversed(list(self._project_packages.values())):
            if pkg.project_id == project_id:
                return _project_package_to_response(pkg)
        raise EntityNotFoundError(f"No project package for project {project_id}")

    async def generate_preview(self, composition_id: UUID) -> PreviewResponse:
        """Generate a low-resolution preview."""
        comp = self._compositions.get(composition_id)
        if comp is None:
            raise EntityNotFoundError(f"Composition {composition_id} not found")

        preview_profile = self._preview_engine.create_preview_profile(comp)
        preview_path = f"/tmp/preview_{composition_id}.mp4"
        preview = self._preview_engine.create_preview_result(
            preview_path,
            resolution=f"{preview_profile.width}x{preview_profile.height}",
            duration=comp.total_duration,
            file_size=self._preview_engine.estimate_preview_size(comp),
        )
        return _preview_to_response(preview)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------
    async def create_publishing_plan(
        self,
        project_id: str,
        platform: str,
        mode: str,
        metadata: dict[str, Any],
        *,
        scheduled_at: str | None = None,
    ) -> PublishingPlanResponse:
        """Create a publishing plan for a project."""
        try:
            platform_enum = PublishingPlatform(platform)
            mode_enum = PublishingMode(mode)
        except ValueError as e:
            raise ValidationError("platform", str(e))

        pub_metadata = PublishingMetadata(
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            tags=metadata.get("tags", []),
            keywords=metadata.get("keywords", []),
            category=metadata.get("category", ""),
            hashtags=metadata.get("hashtags", []),
            language=metadata.get("language", "en"),
            privacy_status=metadata.get("privacy_status", "private"),
            license=metadata.get("license", "youtube"),
            made_for_kids=metadata.get("made_for_kids", False),
            embeddable=metadata.get("embeddable", True),
            public_stats_viewable=metadata.get("public_stats_viewable", True),
            notify_subscribers=metadata.get("notify_subscribers", True),
        )

        task = PublishingTask(
            plan_id=uuid4(),
            platform=platform_enum,
            mode=mode_enum,
            metadata=pub_metadata,
            scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
        )

        plan = PublishingPlan(
            project_id=project_id,
            tasks=[task],
            mode=mode_enum,
            platform_count=1,
        )

        self._publishing_plans[plan.id] = plan

        return PublishingPlanResponse(
            id=str(plan.id),
            project_id=plan.project_id,
            tasks=[_publishing_task_to_response(t) for t in plan.tasks],
            mode=plan.mode.value,
            platform_count=plan.platform_count,
            validation_errors=plan.validation_errors,
            validation_warnings=plan.validation_warnings,
            created_at=plan.created_at.isoformat(),
        )

    async def get_publishing_plan(self, plan_id: UUID) -> PublishingPlanResponse:
        """Get a publishing plan by ID."""
        plan = self._publishing_plans.get(plan_id)
        if plan is None:
            raise EntityNotFoundError(f"Publishing plan {plan_id} not found")

        return PublishingPlanResponse(
            id=str(plan.id),
            project_id=plan.project_id,
            tasks=[_publishing_task_to_response(t) for t in plan.tasks],
            mode=plan.mode.value,
            platform_count=plan.platform_count,
            validation_errors=plan.validation_errors,
            validation_warnings=plan.validation_warnings,
            created_at=plan.created_at.isoformat(),
        )

    async def list_publishing_plans(
        self, project_id: str | None = None
    ) -> list[PublishingPlanResponse]:
        """List publishing plans, optionally filtered by project."""
        plans = list(self._publishing_plans.values())
        if project_id:
            plans = [p for p in plans if p.project_id == project_id]

        return [
            PublishingPlanResponse(
                id=str(p.id),
                project_id=p.project_id,
                tasks=[_publishing_task_to_response(t) for t in p.tasks],
                mode=p.mode.value,
                platform_count=p.platform_count,
                validation_errors=p.validation_errors,
                validation_warnings=p.validation_warnings,
                created_at=p.created_at.isoformat(),
            )
            for p in plans
        ]

    async def execute_publishing(
        self, plan_id: UUID
    ) -> list[PublishingJobResponse]:
        """Execute a publishing plan — submit all tasks to the publishing queue."""
        plan = self._publishing_plans.get(plan_id)
        if plan is None:
            raise EntityNotFoundError(f"Publishing plan {plan_id} not found")

        jobs: list[PublishingJobResponse] = []
        for task in plan.tasks:
            job = PublishingJob(
                task_id=task.id,
                project_id=plan.project_id,
                platform=task.platform,
                priority=task.priority,
                scheduled_at=task.scheduled_at,
            )
            await self._publishing_queue.submit(job)
            jobs.append(_publishing_job_to_response(job))

        return jobs

    async def cancel_publishing(self, job_id: UUID) -> MessageResponse:
        """Cancel a publishing job."""
        success = await self._publishing_queue.cancel(job_id)
        if not success:
            raise EntityNotFoundError(f"Publishing job {job_id} not found or not cancellable")
        return MessageResponse(message="Publishing job cancelled.")

    async def list_publishing_jobs(
        self, project_id: str | None = None
    ) -> list[PublishingJobResponse]:
        """List publishing jobs, optionally filtered by project."""
        all_jobs: list[PublishingJob] = []
        all_jobs.extend(self._publishing_queue._queue)
        all_jobs.extend(self._publishing_queue._active.values())
        all_jobs.extend(self._publishing_queue._completed)
        all_jobs.extend(self._publishing_queue._failed)

        if project_id:
            all_jobs = [j for j in all_jobs if j.project_id == project_id]

        return [_publishing_job_to_response(j) for j in all_jobs]

    async def get_publishing_reports(
        self, project_id: str | None = None
    ) -> list[PublishingReportResponse]:
        """List publishing reports, optionally filtered by project."""
        reports = list(self._publishing_reports.values())
        if project_id:
            reports = [r for r in reports if r.project_id == project_id]

        return [_publishing_report_to_response(r) for r in reports]
