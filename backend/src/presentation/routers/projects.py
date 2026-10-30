"""Projects router — project CRUD, workflow, and content generation endpoints.

Endpoints:
  POST   /projects                         Create project
  GET    /projects                         List projects
  GET    /projects/{id}                    Get project
  PATCH  /projects/{id}                    Update project
  DELETE /projects/{id}                    Delete project
  GET    /projects/{id}/workflow           Get active workflow
  POST   /projects/{id}/workflow/start     Start workflow
  POST   /projects/{id}/workflow/cancel    Cancel workflow
  GET    /projects/{id}/research           Get latest research
  GET    /projects/{id}/research/versions  List research versions
  GET    /projects/{id}/script             Get latest script
  GET    /projects/{id}/script/versions    List script versions
  POST   /projects/{id}/script             Create script version
  GET    /projects/{id}/storyboard         Get latest storyboard
  GET    /projects/{id}/storyboard/versions List storyboard versions
  GET    /projects/{id}/scenes             List scenes
  GET    /projects/{id}/scenes/{scene_id}  Get scene
  PATCH  /projects/{id}/scenes/{scene_id}  Update scene
  GET    /projects/{id}/assets             List assets
  GET    /projects/{id}/assets/{asset_id}  Get asset
  GET    /projects/{id}/jobs               List generation jobs
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.business_dtos import (
    CreateProjectRequest,
    MessageResponse,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectRequest,
    WorkflowResponse,
    ResearchResponse,
    ScriptResponse,
    CreateScriptRequest,
    StoryboardResponse,
    SceneResponse,
    SceneListResponse,
    AssetResponse,
    AssetListResponse,
    GenerationJobResponse,
)
from src.application.services.authorization_service import require_authentication
from src.application.services.project_service import ProjectService
from src.core.logging import get_logger
from src.infrastructure.database.engine import get_db_session

router = APIRouter(prefix="/projects", tags=["Projects"])
_logger = get_logger(__name__)


def _get_project_service(db: AsyncSession = Depends(get_db_session)) -> ProjectService:
    return ProjectService(db)


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------
@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    http_request: Request,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Create a new project."""
    result = await service.create_project(UUID(user["id"]), request)
    await service._session.commit()
    return result


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List projects with optional filters."""
    result = await service.list_projects(
        status=status,
        content_type=content_type,
        offset=offset,
        limit=limit,
    )
    await service._session.commit()
    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get a project by ID."""
    result = await service.get_project(project_id)
    await service._session.commit()
    return result


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: UpdateProjectRequest,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Update a project."""
    result = await service.update_project(project_id, request)
    await service._session.commit()
    return result


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Soft-delete a project."""
    result = await service.delete_project(project_id, UUID(user["id"]))
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
@router.get("/{project_id}/workflow", response_model=WorkflowResponse)
async def get_workflow(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get the active workflow for a project."""
    result = await service.get_workflow(project_id)
    await service._session.commit()
    return result


@router.post("/{project_id}/workflow/start", response_model=WorkflowResponse)
async def start_workflow(
    project_id: UUID,
    http_request: Request,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Start a new workflow for a project."""
    _logger.info("endpoint_start_workflow", project_id=str(project_id), user_id=user.get("id"))
    result = await service.start_workflow(project_id)
    await service._session.commit()
    _logger.info("endpoint_start_workflow_done", project_id=str(project_id), step=result.current_step, status=result.status)
    from src.infrastructure.tasks.workflow_tasks import execute_workflow_task
    execute_workflow_task.delay(str(project_id), str(result.id))
    return result


@router.post("/{project_id}/workflow/cancel", response_model=MessageResponse)
async def cancel_workflow(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Cancel the active workflow."""
    result = await service.cancel_workflow(project_id)
    await service._session.commit()
    return result


@router.post("/{project_id}/workflow/advance", response_model=WorkflowResponse)
async def advance_workflow(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Advance the workflow to the next step."""
    _logger.info("endpoint_advance_workflow", project_id=str(project_id), user_id=user.get("id"))
    result = await service.advance_workflow(project_id)
    await service._session.commit()
    _logger.info("endpoint_advance_workflow_done", project_id=str(project_id), step=result.current_step, status=result.status)
    return result


@router.post("/{project_id}/workflow/retry", response_model=WorkflowResponse)
async def retry_step(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Retry the current workflow step."""
    _logger.info("endpoint_retry_step", project_id=str(project_id), user_id=user.get("id"))
    result = await service.retry_step(project_id)
    await service._session.commit()
    _logger.info("endpoint_retry_step_done", project_id=str(project_id), step=result.current_step, retry_count=result.retry_count)
    return result


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------
@router.get("/{project_id}/research", response_model=ResearchResponse)
async def get_research(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get the latest research for a project."""
    result = await service.get_research(project_id)
    await service._session.commit()
    return result


@router.get("/{project_id}/research/versions", response_model=list[ResearchResponse])
async def list_research_versions(
    project_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List all research versions for a project."""
    result = await service.list_research(project_id, offset=offset, limit=limit)
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------
@router.get("/{project_id}/script", response_model=ScriptResponse)
async def get_script(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get the latest script for a project."""
    result = await service.get_script(project_id)
    await service._session.commit()
    return result


@router.get("/{project_id}/script/versions", response_model=list[ScriptResponse])
async def list_script_versions(
    project_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List all script versions for a project."""
    result = await service.list_scripts(project_id, offset=offset, limit=limit)
    await service._session.commit()
    return result


@router.post("/{project_id}/script", response_model=ScriptResponse, status_code=201)
async def create_script(
    project_id: UUID,
    request: CreateScriptRequest,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Create a new script version."""
    result = await service.create_script(project_id, request)
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Storyboard
# ---------------------------------------------------------------------------
@router.get("/{project_id}/storyboard", response_model=StoryboardResponse)
async def get_storyboard(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get the latest storyboard for a project."""
    result = await service.get_storyboard(project_id)
    await service._session.commit()
    return result


@router.get("/{project_id}/storyboard/versions", response_model=list[StoryboardResponse])
async def list_storyboard_versions(
    project_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List all storyboard versions for a project."""
    result = await service.list_storyboards(project_id, offset=offset, limit=limit)
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------
@router.get("/{project_id}/scenes", response_model=SceneListResponse)
async def list_scenes(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List all scenes for a project."""
    result = await service.list_scenes(project_id)
    await service._session.commit()
    return result


@router.get("/{project_id}/scenes/{scene_id}", response_model=SceneResponse)
async def get_scene(
    project_id: UUID,
    scene_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get a single scene by ID."""
    result = await service.get_scene(scene_id)
    await service._session.commit()
    return result


@router.patch("/{project_id}/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    project_id: UUID,
    scene_id: UUID,
    updates: dict,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Update a scene (narration, camera, etc.)."""
    result = await service.update_scene(scene_id, updates)
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
@router.get("/{project_id}/assets", response_model=AssetListResponse)
async def list_assets(
    project_id: UUID,
    asset_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List assets for a project."""
    result = await service.list_assets(
        project_id, asset_type=asset_type, offset=offset, limit=limit
    )
    await service._session.commit()
    return result


@router.get("/{project_id}/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    project_id: UUID,
    asset_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Get a single asset by ID."""
    result = await service.get_asset(asset_id)
    await service._session.commit()
    return result


# ---------------------------------------------------------------------------
# Generation Jobs
# ---------------------------------------------------------------------------
@router.get("/{project_id}/jobs", response_model=list[GenerationJobResponse])
async def list_jobs(
    project_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """List generation jobs for a project."""
    result = await service.list_jobs(project_id, offset=offset, limit=limit)
    await service._session.commit()
    return result


@router.get("/{project_id}/download")
async def download_outputs(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Download all workflow outputs as a zip archive."""
    zip_buffer = await service.build_outputs_zip(project_id)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={project_id}_outputs.zip"
        },
    )


@router.get("/{project_id}/download/video")
async def download_final_video(
    project_id: UUID,
    user: dict = Depends(require_authentication),
    service: ProjectService = Depends(_get_project_service),
):
    """Stream the rendered ``final_video.mp4`` for a project.

    Returns 404 when the workflow has not produced a final render yet.
    """
    video_path = await service.get_final_video_path(project_id)
    if video_path is None:
        raise HTTPException(status_code=404, detail="Final video not available")
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{project_id}_final_video.mp4",
    )
