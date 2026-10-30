"""Production router — composition, rendering, and publishing endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.services.authorization_service import require_authentication
from src.application.services.production_service import (
    CompositionResponse,
    CreatePublishingRequest,
    CreateRenderRequest,
    MessageResponse,
    PreviewResponse,
    ProductionService,
    ProjectPackageResponse,
    PublishingJobResponse,
    PublishingPlanResponse,
    PublishingReportResponse,
    RenderJobResponse,
    RenderProgressResponse,
    PublishingTaskResponse,
)

router = APIRouter(prefix="/projects", tags=["production"])

# Singleton service instance
_production_service: ProductionService | None = None


def _get_production_service() -> ProductionService:
    global _production_service
    if _production_service is None:
        _production_service = ProductionService()
    return _production_service


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------
@router.post("/{project_id}/composition", response_model=CompositionResponse, status_code=201)
async def build_composition(
    project_id: str,
    body: dict | None = None,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> CompositionResponse:
    """Build a composition document from project assets."""
    body = body or {}
    return await service.build_composition(
        project_id,
        export_preset=body.get("export_preset", "1080p"),
        resolution=body.get("resolution"),
        fps=body.get("fps", 30),
    )


@router.get("/{project_id}/composition", response_model=CompositionResponse)
async def get_project_composition(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> CompositionResponse:
    """Get the latest composition for a project."""
    return await service.get_project_composition(project_id)


@router.get("/{project_id}/composition/{composition_id}", response_model=CompositionResponse)
async def get_composition(
    project_id: str,
    composition_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> CompositionResponse:
    """Get a composition by ID."""
    return await service.get_composition(UUID(composition_id))


@router.patch("/{project_id}/composition/{composition_id}/timeline", response_model=CompositionResponse)
async def update_timeline(
    project_id: str,
    composition_id: str,
    body: dict,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> CompositionResponse:
    """Update the timeline of a composition."""
    timeline_data = body.get("timeline", body)
    return await service.update_timeline(UUID(composition_id), timeline_data)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
@router.post("/{project_id}/renders", response_model=RenderJobResponse, status_code=201)
async def submit_render(
    project_id: str,
    body: CreateRenderRequest,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> RenderJobResponse:
    """Submit a render job."""
    return await service.submit_render(
        UUID(body.composition_id),
        priority=body.priority or "normal",
        output_path=body.output_path or "",
    )


@router.get("/{project_id}/renders", response_model=list[RenderJobResponse])
async def list_renders(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> list[RenderJobResponse]:
    """List render jobs for a project."""
    return await service.list_renders(project_id)


@router.get("/{project_id}/renders/{job_id}", response_model=RenderJobResponse)
async def get_render_job(
    project_id: str,
    job_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> RenderJobResponse:
    """Get a render job by ID."""
    jobs = await service.list_renders(project_id)
    for j in jobs:
        if j.id == job_id:
            return j
    raise HTTPException(status_code=404, detail="Render job not found")


@router.get("/{project_id}/renders/{job_id}/progress", response_model=RenderProgressResponse)
async def get_render_progress(
    project_id: str,
    job_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> RenderProgressResponse:
    """Get progress for a render job."""
    return await service.get_render_progress(UUID(job_id))


@router.post("/{project_id}/renders/{job_id}/cancel", response_model=MessageResponse)
async def cancel_render(
    project_id: str,
    job_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> MessageResponse:
    """Cancel a render job."""
    return await service.cancel_render(UUID(job_id))


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
@router.post("/{project_id}/composition/{composition_id}/preview", response_model=PreviewResponse)
async def generate_preview(
    project_id: str,
    composition_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> PreviewResponse:
    """Generate a low-resolution preview."""
    return await service.generate_preview(UUID(composition_id))


# ---------------------------------------------------------------------------
# Project Package
# ---------------------------------------------------------------------------
@router.get("/{project_id}/package", response_model=ProjectPackageResponse)
async def get_project_package(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> ProjectPackageResponse:
    """Get the final project package (rendered video + assets)."""
    return await service.get_project_package(project_id)


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------
@router.post("/{project_id}/publishing/plans", response_model=PublishingPlanResponse, status_code=201)
async def create_publishing_plan(
    project_id: str,
    body: CreatePublishingRequest,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> PublishingPlanResponse:
    """Create a publishing plan."""
    return await service.create_publishing_plan(
        project_id,
        body.platform,
        body.mode,
        body.metadata,
        scheduled_at=body.scheduled_at,
    )


@router.get("/{project_id}/publishing/plans", response_model=list[PublishingPlanResponse])
async def list_publishing_plans(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> list[PublishingPlanResponse]:
    """List publishing plans for a project."""
    return await service.list_publishing_plans(project_id)


@router.get("/{project_id}/publishing/plans/{plan_id}", response_model=PublishingPlanResponse)
async def get_publishing_plan(
    project_id: str,
    plan_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> PublishingPlanResponse:
    """Get a publishing plan by ID."""
    return await service.get_publishing_plan(UUID(plan_id))


@router.post("/{project_id}/publishing/plans/{plan_id}/execute", response_model=list[PublishingJobResponse])
async def execute_publishing(
    project_id: str,
    plan_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> list[PublishingJobResponse]:
    """Execute a publishing plan."""
    return await service.execute_publishing(UUID(plan_id))


@router.get("/{project_id}/publishing/jobs", response_model=list[PublishingJobResponse])
async def list_publishing_jobs(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> list[PublishingJobResponse]:
    """List publishing jobs for a project."""
    return await service.list_publishing_jobs(project_id)


@router.post("/{project_id}/publishing/jobs/{job_id}/cancel", response_model=MessageResponse)
async def cancel_publishing_job(
    project_id: str,
    job_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> MessageResponse:
    """Cancel a publishing job."""
    return await service.cancel_publishing(UUID(job_id))


@router.get("/{project_id}/publishing/reports", response_model=list[PublishingReportResponse])
async def list_publishing_reports(
    project_id: str,
    user: dict = Depends(require_authentication),
    service: ProductionService = Depends(_get_production_service),
) -> list[PublishingReportResponse]:
    """List publishing reports for a project."""
    return await service.get_publishing_reports(project_id)
