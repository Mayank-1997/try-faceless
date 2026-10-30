"""Project service — business logic for project CRUD and workflow management.

This service orchestrates repository calls, enforces business rules,
and converts between domain entities and DTOs.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.business_dtos import (
    AssetListResponse,
    AssetResponse,
    CreateProjectRequest,
    CreateScriptRequest,
    GenerationJobResponse,
    MessageResponse,
    ProjectListResponse,
    ProjectResponse,
    ResearchResponse,
    SceneListResponse,
    SceneResponse,
    ScriptResponse,
    StoryboardResponse,
    UpdateProjectRequest,
    WorkflowResponse,
    asset_to_response,
    project_to_response,
    scene_to_response,
    workflow_to_response,
)
from src.core.config import get_settings
from src.core.enums import (
    ContentType,
    ProjectStatus,
    VideoStyle,
    WorkflowStatus,
    WorkflowStep,
)
from src.core.exceptions import EntityNotFoundError, ValidationError
from src.core.logging import get_logger
from src.domain.entities.project import Project
from src.domain.entities.workflow import Workflow
from src.persistence.repositories.business_repositories import (
    SqlAlchemyAssetRepository,
    SqlAlchemyGenerationJobRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyResearchRepository,
    SqlAlchemySceneRepository,
    SqlAlchemyScriptRepository,
    SqlAlchemyStoryboardRepository,
    SqlAlchemyWorkflowRepository,
)


class ProjectService:
    """Service for project CRUD and workflow operations."""

    _logger = get_logger(__name__)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._project_repo = SqlAlchemyProjectRepository(session)
        self._workflow_repo = SqlAlchemyWorkflowRepository(session)
        self._research_repo = SqlAlchemyResearchRepository(session)
        self._script_repo = SqlAlchemyScriptRepository(session)
        self._storyboard_repo = SqlAlchemyStoryboardRepository(session)
        self._scene_repo = SqlAlchemySceneRepository(session)
        self._asset_repo = SqlAlchemyAssetRepository(session)
        self._job_repo = SqlAlchemyGenerationJobRepository(session)

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------
    async def create_project(
        self, owner_id: UUID, request: CreateProjectRequest
    ) -> ProjectResponse:
        """Create a new project."""
        # aspect_ratio rides inside the JSON ``metadata`` column so no
        # schema migration is needed; _build_initial_state reads it back.
        project = Project(
            owner_id=owner_id,
            title=request.title,
            description=request.description,
            language=request.language,
            audience=request.audience,
            content_type=ContentType(request.content_type),
            video_style=VideoStyle(request.video_style),
            target_duration_seconds=request.target_duration_seconds,
            tags=request.tags,
            metadata={
                **request.metadata,
                "aspect_ratio": request.aspect_ratio,
                "production_mode": request.production_mode,
                "visual_anchor": request.visual_anchor.strip(),
                "clip_beats": [beat.strip() for beat in request.clip_beats],
                "avoid": request.avoid.strip(),
                "narration_text": request.narration_text.strip(),
            },
            created_by=owner_id,
        )
        project = await self._project_repo.create(project)
        return project_to_response(project)

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        """Get a project by ID."""
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            raise EntityNotFoundError(f"Project {project_id} not found")
        return project_to_response(project)

    async def update_project(
        self, project_id: UUID, request: UpdateProjectRequest
    ) -> ProjectResponse:
        """Update a project."""
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            raise EntityNotFoundError(f"Project {project_id} not found")

        if request.title is not None:
            project.title = request.title
        if request.description is not None:
            project.description = request.description
        if request.language is not None:
            project.language = request.language
        if request.audience is not None:
            project.audience = request.audience
        if request.content_type is not None:
            project.content_type = ContentType(request.content_type)
        if request.video_style is not None:
            project.video_style = VideoStyle(request.video_style)
        if request.target_duration_seconds is not None:
            project.target_duration_seconds = request.target_duration_seconds
        if request.aspect_ratio is not None:
            if request.aspect_ratio not in {"16:9", "9:16"}:
                raise ValueError("Invalid aspect_ratio")
            project.metadata = {**(project.metadata or {}), "aspect_ratio": request.aspect_ratio}
        if request.tags is not None:
            project.tags = request.tags
        if request.metadata is not None:
            protected = {key: (project.metadata or {}).get(key) for key in (
                "aspect_ratio", "production_mode", "visual_anchor", "clip_beats", "avoid", "narration_text"
            ) if key in (project.metadata or {})}
            project.metadata = {**(project.metadata or {}), **request.metadata, **protected}

        project = await self._project_repo.update(project)
        return project_to_response(project)

    async def delete_project(
        self, project_id: UUID, deleted_by: UUID
    ) -> MessageResponse:
        """Soft-delete a project."""
        deleted = await self._project_repo.soft_delete(project_id, deleted_by)
        if not deleted:
            raise EntityNotFoundError(f"Project {project_id} not found")
        return MessageResponse(message="Project deleted successfully.")

    async def list_projects(
        self,
        *,
        status: str | None = None,
        content_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ProjectListResponse:
        """List projects with optional filters."""
        status_enum = ProjectStatus(status) if status else None
        ct_enum = ContentType(content_type) if content_type else None

        projects = await self._project_repo.list_projects(
            status=status_enum,
            content_type=ct_enum,
            offset=offset,
            limit=limit,
        )
        total = await self._project_repo.count_projects(
            status=status_enum,
        )

        return ProjectListResponse(
            items=[project_to_response(p) for p in projects],
            total=total,
            offset=offset,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    async def get_workflow(self, project_id: UUID) -> WorkflowResponse:
        """Get the latest workflow for a project (active or completed)."""
        self._logger.info("get_workflow_called", project_id=str(project_id))
        workflow = await self._workflow_repo.get_latest_workflow(project_id)
        if workflow is None:
            self._logger.warning("workflow_not_found", project_id=str(project_id))
            raise EntityNotFoundError(f"No workflow found for project {project_id}")
        self._logger.info("get_workflow_result", project_id=str(project_id), step=workflow.current_step, status=workflow.status)
        return workflow_to_response(workflow)

    async def start_workflow(self, project_id: UUID) -> WorkflowResponse:
        """Start a new workflow for a project."""
        self._logger.info("start_workflow_called", project_id=str(project_id))
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            self._logger.warning("start_workflow_project_not_found", project_id=str(project_id))
            raise EntityNotFoundError(f"Project {project_id} not found")

        self._logger.info("start_workflow_project_status", project_id=str(project_id), status=project.status)

        _active_statuses = (
            ProjectStatus.RESEARCHING,
            ProjectStatus.SCRIPTING,
            ProjectStatus.PLANNING,
            ProjectStatus.GENERATING,
            ProjectStatus.RENDERING,
            ProjectStatus.PUBLISHING,
        )
        if project.status in _active_statuses or project.status == ProjectStatus.COMPLETED:
            existing = await self._workflow_repo.get_active_workflow(project_id)
            if existing and existing.status == WorkflowStatus.RUNNING:
                self._logger.warning("start_workflow_already_running", project_id=str(project_id))
                # Mark stale workflow as failed and allow restart
                existing.status = WorkflowStatus.FAILED
                existing.failure_reason = "Workflow superseded by new workflow start"
                await self._workflow_repo.update(existing)
                self._logger.info("start_workflow_stale_failed", project_id=str(project_id), workflow_id=str(existing.id))

        workflow = Workflow(
            project_id=project_id,
            version=1,
            current_step=WorkflowStep.INITIALIZATION,
            status=WorkflowStatus.PENDING,
        )
        workflow.start()
        workflow = await self._workflow_repo.create(workflow)
        self._logger.info("start_workflow_created", project_id=str(project_id), workflow_id=str(workflow.id), step=workflow.current_step, status=workflow.status)

        project.status = ProjectStatus.RESEARCHING
        project.current_step = WorkflowStep.INITIALIZATION
        await self._project_repo.update(project)
        self._logger.info("start_workflow_project_updated", project_id=str(project_id), project_status=project.status)

        return workflow_to_response(workflow)

    async def cancel_workflow(self, project_id: UUID) -> MessageResponse:
        """Cancel the active workflow for a project."""
        self._logger.info("cancel_workflow_called", project_id=str(project_id))
        workflow = await self._workflow_repo.get_active_workflow(project_id)
        if workflow is None:
            self._logger.warning("cancel_workflow_not_found", project_id=str(project_id))
            raise EntityNotFoundError(f"No active workflow for project {project_id}")

        workflow.status = WorkflowStatus.CANCELLED
        await self._workflow_repo.update(workflow)
        self._logger.info("cancel_workflow_done", project_id=str(project_id), workflow_id=str(workflow.id))

        project = await self._project_repo.get_by_id(project_id)
        if project:
            project.status = ProjectStatus.CANCELLED
            await self._project_repo.update(project)
            self._logger.info("cancel_workflow_project_updated", project_id=str(project_id))

        return MessageResponse(message="Workflow cancelled successfully.")

    # ------------------------------------------------------------------
    # Workflow step control
    # ------------------------------------------------------------------
    _STEP_ORDER = [
        WorkflowStep.INITIALIZATION,
        WorkflowStep.RESEARCH,
        WorkflowStep.SCRIPTING,
        WorkflowStep.STORYBOARD,
        WorkflowStep.SCENE_PLANNING,
        WorkflowStep.ASSET_GENERATION,
        WorkflowStep.VOICE_GENERATION,
        WorkflowStep.SUBTITLE_GENERATION,
        WorkflowStep.RENDERING,
        WorkflowStep.THUMBNAIL,
        WorkflowStep.SEO,
        WorkflowStep.COMPLETED,
    ]

    _STEP_TO_PROJECT_STATUS: dict[WorkflowStep, ProjectStatus] = {
        WorkflowStep.INITIALIZATION: ProjectStatus.RESEARCHING,
        WorkflowStep.RESEARCH: ProjectStatus.RESEARCHING,
        WorkflowStep.SCRIPTING: ProjectStatus.SCRIPTING,
        WorkflowStep.STORYBOARD: ProjectStatus.PLANNING,
        WorkflowStep.SCENE_PLANNING: ProjectStatus.PLANNING,
        WorkflowStep.ASSET_GENERATION: ProjectStatus.GENERATING,
        WorkflowStep.VOICE_GENERATION: ProjectStatus.GENERATING,
        WorkflowStep.SUBTITLE_GENERATION: ProjectStatus.GENERATING,
        WorkflowStep.RENDERING: ProjectStatus.RENDERING,
        WorkflowStep.THUMBNAIL: ProjectStatus.RENDERING,
        WorkflowStep.SEO: ProjectStatus.PUBLISHING,
        WorkflowStep.COMPLETED: ProjectStatus.COMPLETED,
    }

    async def advance_workflow(self, project_id: UUID) -> WorkflowResponse:
        """Advance the workflow to the next step."""
        self._logger.info("advance_workflow_called", project_id=str(project_id))
        workflow = await self._workflow_repo.get_active_workflow(project_id)
        if workflow is None:
            self._logger.warning("advance_workflow_not_found", project_id=str(project_id))
            raise EntityNotFoundError(f"No active workflow for project {project_id}")

        self._logger.info("advance_workflow_current", project_id=str(project_id), current_step=workflow.current_step, status=workflow.status)

        current_idx = self._STEP_ORDER.index(workflow.current_step)
        if current_idx >= len(self._STEP_ORDER) - 1:
            self._logger.warning("advance_workflow_at_final_step", project_id=str(project_id))
            raise ValidationError("workflow", "Workflow is already at the final step")

        next_step = self._STEP_ORDER[current_idx + 1]
        workflow.advance_to(next_step)
        if workflow.status == WorkflowStatus.PENDING:
            workflow.start()
        if next_step == WorkflowStep.COMPLETED:
            workflow.complete()
        await self._workflow_repo.update(workflow)
        self._logger.info("advance_workflow_done", project_id=str(project_id), workflow_id=str(workflow.id), new_step=workflow.current_step, status=workflow.status)

        project = await self._project_repo.get_by_id(project_id)
        if project:
            project.current_step = next_step
            project.status = self._STEP_TO_PROJECT_STATUS.get(next_step, ProjectStatus.RESEARCHING)
            await self._project_repo.update(project)
            self._logger.info("advance_workflow_project_updated", project_id=str(project_id), project_status=project.status, project_step=project.current_step)

        return workflow_to_response(workflow)

    async def retry_step(self, project_id: UUID) -> WorkflowResponse:
        """Retry the current workflow step."""
        self._logger.info("retry_step_called", project_id=str(project_id))
        workflow = await self._workflow_repo.get_active_workflow(project_id)
        if workflow is None:
            self._logger.warning("retry_step_not_found", project_id=str(project_id))
            raise EntityNotFoundError(f"No active workflow for project {project_id}")

        self._logger.info("retry_step_current", project_id=str(project_id), step=workflow.current_step, retry_count=workflow.retry_count)
        workflow.retry()
        await self._workflow_repo.update(workflow)
        self._logger.info("retry_step_done", project_id=str(project_id), step=workflow.current_step, retry_count=workflow.retry_count)

        return workflow_to_response(workflow)

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------
    async def get_research(self, project_id: UUID) -> ResearchResponse:
        """Get the latest research for a project."""
        research = await self._research_repo.get_latest_version(project_id)
        if research is None:
            raise EntityNotFoundError(f"No research found for project {project_id}")

        from src.application.dto.business_dtos import ResearchResponse as R
        return R(
            id=research.id,
            project_id=research.project_id,
            workflow_id=research.workflow_id,
            summary=research.summary,
            timeline=research.timeline,
            interesting_facts=research.interesting_facts,
            sources=research.sources,
            keywords=research.keywords,
            references=research.references,
            statistics=research.statistics,
            audience_pain_points=research.audience_pain_points,
            version=research.version,
            status=research.status.value if hasattr(research.status, "value") else str(research.status),
            created_at=research.created_at,
            updated_at=research.updated_at,
        )

    async def list_research(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[ResearchResponse]:
        """List all research versions for a project."""
        versions = await self._research_repo.get_by_project(
            project_id, offset=offset, limit=limit
        )
        results = []
        for r in versions:
            from src.application.dto.business_dtos import ResearchResponse as R
            results.append(R(
                id=r.id,
                project_id=r.project_id,
                workflow_id=r.workflow_id,
                summary=r.summary,
                timeline=r.timeline,
                interesting_facts=r.interesting_facts,
                sources=r.sources,
                keywords=r.keywords,
                references=r.references,
                statistics=r.statistics,
                audience_pain_points=r.audience_pain_points,
                version=r.version,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                created_at=r.created_at,
                updated_at=r.updated_at,
            ))
        return results

    # ------------------------------------------------------------------
    # Script
    # ------------------------------------------------------------------
    async def get_script(self, project_id: UUID) -> ScriptResponse:
        """Get the latest script for a project."""
        script = await self._script_repo.get_latest_version(project_id)
        if script is None:
            raise EntityNotFoundError(f"No script found for project {project_id}")

        from src.application.dto.business_dtos import ScriptResponse as S
        return S(
            id=script.id,
            project_id=script.project_id,
            workflow_id=script.workflow_id,
            hook=script.hook,
            body=script.body,
            cta=script.cta,
            word_count=script.word_count,
            estimated_duration_seconds=script.estimated_duration_seconds,
            version=script.version,
            language=script.language,
            status=script.status.value if hasattr(script.status, "value") else str(script.status),
            created_at=script.created_at,
            updated_at=script.updated_at,
        )

    async def list_scripts(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[ScriptResponse]:
        """List all script versions for a project."""
        versions = await self._script_repo.get_by_project(
            project_id, offset=offset, limit=limit
        )
        results = []
        for s in versions:
            from src.application.dto.business_dtos import ScriptResponse as S
            results.append(S(
                id=s.id,
                project_id=s.project_id,
                workflow_id=s.workflow_id,
                hook=s.hook,
                body=s.body,
                cta=s.cta,
                word_count=s.word_count,
                estimated_duration_seconds=s.estimated_duration_seconds,
                version=s.version,
                language=s.language,
                status=s.status.value if hasattr(s.status, "value") else str(s.status),
                created_at=s.created_at,
                updated_at=s.updated_at,
            ))
        return results

    async def create_script(
        self, project_id: UUID, request: CreateScriptRequest
    ) -> ScriptResponse:
        """Create a new script version for a project."""
        from src.core.enums import ScriptStatus
        from src.domain.entities.script import Script

        existing = await self._script_repo.get_latest_version(project_id)
        version = (existing.version + 1) if existing else 1

        script = Script(
            project_id=project_id,
            hook=request.hook,
            body=request.body,
            cta=request.cta,
            language=request.language,
            version=version,
            status=ScriptStatus.DRAFT,
        )
        script = await self._script_repo.create(script)

        from src.application.dto.business_dtos import ScriptResponse as S
        return S(
            id=script.id,
            project_id=script.project_id,
            workflow_id=script.workflow_id,
            hook=script.hook,
            body=script.body,
            cta=script.cta,
            word_count=script.word_count,
            estimated_duration_seconds=script.estimated_duration_seconds,
            version=script.version,
            language=script.language,
            status=script.status.value if hasattr(script.status, "value") else str(script.status),
            created_at=script.created_at,
            updated_at=script.updated_at,
        )

    # ------------------------------------------------------------------
    # Storyboard
    # ------------------------------------------------------------------
    async def get_storyboard(self, project_id: UUID) -> StoryboardResponse:
        """Get the latest storyboard for a project."""
        sb = await self._storyboard_repo.get_latest_version(project_id)
        if sb is None:
            raise EntityNotFoundError(f"No storyboard found for project {project_id}")

        from src.application.dto.business_dtos import StoryboardResponse as SB
        return SB(
            id=sb.id,
            project_id=sb.project_id,
            workflow_id=sb.workflow_id,
            version=sb.version,
            scene_count=sb.scene_count,
            estimated_duration_seconds=sb.estimated_duration_seconds,
            style=sb.style,
            status=sb.status.value if hasattr(sb.status, "value") else str(sb.status),
            narrative_structure=sb.narrative_structure,
            pacing_notes=sb.pacing_notes,
            package_json=sb.package_json,
            created_at=sb.created_at,
            updated_at=sb.updated_at,
        )

    async def list_storyboards(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[StoryboardResponse]:
        """List all storyboard versions for a project."""
        versions = await self._storyboard_repo.get_by_project(
            project_id, offset=offset, limit=limit
        )
        results = []
        for sb in versions:
            from src.application.dto.business_dtos import StoryboardResponse as SB
            results.append(SB(
                id=sb.id,
                project_id=sb.project_id,
                workflow_id=sb.workflow_id,
                version=sb.version,
                scene_count=sb.scene_count,
                estimated_duration_seconds=sb.estimated_duration_seconds,
                style=sb.style,
                status=sb.status.value if hasattr(sb.status, "value") else str(sb.status),
                narrative_structure=sb.narrative_structure,
                pacing_notes=sb.pacing_notes,
                package_json=sb.package_json,
                created_at=sb.created_at,
                updated_at=sb.updated_at,
            ))
        return results

    # ------------------------------------------------------------------
    # Scenes
    # ------------------------------------------------------------------
    async def list_scenes(self, project_id: UUID) -> SceneListResponse:
        """List all scenes for a project."""
        scenes = await self._scene_repo.get_by_project(project_id)
        return SceneListResponse(
            items=[scene_to_response(s) for s in scenes],
            total=len(scenes),
        )

    async def get_scene(self, scene_id: UUID) -> SceneResponse:
        """Get a single scene by ID."""
        scene = await self._scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError(f"Scene {scene_id} not found")
        return scene_to_response(scene)

    async def update_scene(
        self, scene_id: UUID, updates: dict
    ) -> SceneResponse:
        """Update a scene (narration, camera, etc.)."""
        scene = await self._scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError(f"Scene {scene_id} not found")

        for key, value in updates.items():
            if hasattr(scene, key) and value is not None:
                setattr(scene, key, value)

        scene = await self._scene_repo.update(scene)
        return scene_to_response(scene)

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    async def list_assets(
        self,
        project_id: UUID,
        *,
        asset_type: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> AssetListResponse:
        """List assets for a project."""
        from src.core.enums import AssetType

        at_enum = AssetType(asset_type) if asset_type else None
        assets = await self._asset_repo.get_by_project(
            project_id, asset_type=at_enum, offset=offset, limit=limit
        )
        return AssetListResponse(
            items=[asset_to_response(a) for a in assets],
            total=len(assets),
        )

    async def get_asset(self, asset_id: UUID) -> AssetResponse:
        """Get a single asset by ID."""
        asset = await self._asset_repo.get_by_id(asset_id)
        if asset is None:
            raise EntityNotFoundError(f"Asset {asset_id} not found")
        return asset_to_response(asset)

    # ------------------------------------------------------------------
    # Generation Jobs
    # ------------------------------------------------------------------
    async def list_jobs(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[GenerationJobResponse]:
        """List generation jobs for a project."""
        from src.application.dto.business_dtos import GenerationJobResponse as GJ

        jobs = await self._job_repo.get_by_project(
            project_id, offset=offset, limit=limit
        )
        results = []
        for j in jobs:
            results.append(GJ(
                id=j.id,
                project_id=j.project_id,
                workflow_id=j.workflow_id,
                scene_id=j.scene_id,
                job_type=j.job_type.value if hasattr(j.job_type, "value") else str(j.job_type),
                status=j.status.value if hasattr(j.status, "value") else str(j.status),
                priority=j.priority.value if hasattr(j.priority, "value") else str(j.priority),
                payload=j.payload,
                result=j.result,
                error_message=j.error_message,
                retry_count=j.retry_count,
                max_retries=j.max_retries,
                queued_at=j.queued_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                execution_time_seconds=j.execution_time_seconds,
                created_at=j.created_at,
                updated_at=j.updated_at,
            ))
        return results

    async def build_outputs_zip(self, project_id: UUID) -> io.BytesIO:
        """Build a zip archive containing all generated workflow outputs."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            project = await self._project_repo.get_by_id(project_id)
            if project:
                zf.writestr(
                    "project.txt",
                    f"Title: {project.title}\n"
                    f"Description: {project.description}\n"
                    f"Language: {project.language}\n"
                    f"Content Type: {project.content_type}\n"
                    f"Audience: {project.audience}\n",
                )

            # Add the full WorkflowState JSON if the workflow persisted it.
            workflow_state_data: dict[str, Any] | None = None
            workflow = await self._workflow_repo.get_latest_workflow(project_id)
            if workflow and workflow.checkpoint_ref and workflow.checkpoint_ref.endswith(".json"):
                settings = get_settings()
                state_path = Path(settings.storage.local_path) / workflow.checkpoint_ref
                if state_path.exists():
                    try:
                        workflow_state_data = json.loads(
                            state_path.read_text(encoding="utf-8")
                        )
                        zf.writestr(
                            "workflow_state/workflow_state.json",
                            json.dumps(workflow_state_data, indent=2, default=str),
                        )
                    except Exception:
                        zf.write(str(state_path), "workflow_state/workflow_state.json")
                else:
                    zf.writestr(
                        "workflow_state/not_available.json",
                        json.dumps(
                            {
                                "status": "unavailable",
                                "reason": "workflow_state_file_not_found",
                                "checkpoint_ref": workflow.checkpoint_ref,
                            },
                            indent=2,
                        ),
                    )
            else:
                zf.writestr(
                    "workflow_state/not_available.json",
                    json.dumps(
                        {
                            "status": "unavailable",
                            "reason": "no_completed_workflow_state",
                        },
                        indent=2,
                    ),
                )

            research = await self._research_repo.get_latest_version(project_id)
            if research:
                lines = [
                    f"Summary: {research.summary}",
                    f"Timeline: {', '.join(research.timeline)}",
                    f"Interesting Facts: {', '.join(research.interesting_facts)}",
                    f"Sources: {', '.join(research.sources)}",
                    f"Keywords: {', '.join(research.keywords)}",
                    f"References: {', '.join(research.references)}",
                    f"Statistics: {json.dumps(research.statistics, indent=2)}",
                    f"Audience Pain Points: {', '.join(research.audience_pain_points)}",
                ]
                zf.writestr("research/research.txt", "\n\n".join(lines))
            else:
                zf.writestr("research/not_available.txt", "No research output available.")

            script = await self._script_repo.get_latest_version(project_id)
            if script:
                lines = [
                    f"Hook: {script.hook}",
                    f"Body:\n{script.body}",
                    f"Call to Action: {script.cta}",
                    f"Word Count: {script.word_count}",
                    f"Estimated Duration: {script.estimated_duration_seconds}s",
                    f"Language: {script.language}",
                ]
                zf.writestr("script/script.txt", "\n\n".join(lines))
            else:
                zf.writestr("script/not_available.txt", "No script output available.")

            storyboard = await self._storyboard_repo.get_latest_version(project_id)
            storyboard_package = None
            if storyboard and storyboard.package_json:
                try:
                    storyboard_package = json.loads(storyboard.package_json)
                except Exception:
                    storyboard_package = None
            elif workflow_state_data:
                sb_state = workflow_state_data.get("storyboard", {})
                storyboard_package = sb_state.get("metadata", {}).get("storyboard_package")

            if storyboard:
                lines = [
                    f"Scene Count: {storyboard.scene_count}",
                    f"Estimated Duration: {storyboard.estimated_duration_seconds}s",
                    f"Style: {storyboard.style}",
                ]
                if storyboard_package:
                    sa = storyboard_package.get("story_analysis", {})
                    sb = storyboard_package.get("story_beats", {})
                    cont = storyboard_package.get("continuity", {})
                    review = storyboard_package.get("review", {})
                    quality = storyboard_package.get("quality", {})
                    lines += [
                        f"Act Count: {sb.get('total_beats', 0)}",
                        f"Narrative Structure: {sa.get('narrative_flow', '')}",
                        f"Pacing Notes: {cont.get('transition_consistency', '')}",
                        f"Review Score: {review.get('overall_score')}",
                        f"Quality Score: {quality.get('overall_score')}",
                        (
                            f"Estimated Budget: "
                            f"{storyboard_package.get('estimated_budget', 0):.4f} USD"
                        ),
                        (
                            f"Estimated Timeline: "
                            f"{storyboard_package.get('estimated_timeline_minutes', 0)} min"
                        ),
                        "",
                        "Full package (all agent outputs) is in storyboard/storyboard_package.json",
                        "Beats:",
                        *[f"  - {beat.get('description', '')}" for beat in sb.get('beats', [])],
                        "",
                        "Scenes:",
                        *[f"  {sp.get('scene_number', 0)}. {sp.get('title', '')}"
                          for sp in storyboard_package.get('scene_packages', [])],
                    ]
                else:
                    lines += [
                        f"Narrative Structure: {storyboard.narrative_structure}",
                        f"Pacing Notes: {storyboard.pacing_notes}",
                    ]
                zf.writestr("storyboard/storyboard.txt", "\n".join(lines))

                if storyboard_package:
                    zf.writestr(
                        "storyboard/storyboard_package.json",
                        json.dumps(storyboard_package, indent=2),
                    )
            else:
                zf.writestr("storyboard/not_available.txt", "No storyboard output available.")

            # Filter scenes and assets to only the latest workflow run so we
            # don't include duplicate assets from previous workflow attempts
            # (which can produce a multi-GB zip and OOM the container).
            latest_workflow_id = workflow.id if workflow else None
            all_scenes = await self._scene_repo.get_by_project(project_id)
            if latest_workflow_id:
                scenes = [
                    s for s in all_scenes
                    if str(getattr(s, "workflow_id", "")) == str(latest_workflow_id)
                ]
            else:
                scenes = all_scenes
            if scenes:
                scene_data = []
                for s in scenes:
                    scene_data.append({
                        "scene_number": s.scene_number,
                        "title": s.title,
                        "duration_seconds": s.duration_seconds,
                        "narration": s.narration,
                        "emotion": s.emotion,
                        "visual_type": s.visual_type.value if hasattr(s.visual_type, "value") else str(s.visual_type),
                        "camera_angle": s.camera_angle.value if s.camera_angle and hasattr(s.camera_angle, "value") else str(s.camera_angle),
                        "camera_motion": s.camera_motion.value if s.camera_motion and hasattr(s.camera_motion, "value") else str(s.camera_motion),
                        "transition": s.transition.value if s.transition and hasattr(s.transition, "value") else str(s.transition),
                        "subtitle": s.subtitle,
                    })
                zf.writestr("scenes/scenes.json", json.dumps(scene_data, indent=2, default=str))
            else:
                zf.writestr("scenes/not_available.txt", "No scenes available.")

            # Only include assets whose scene belongs to the latest workflow.
            scene_ids = {str(s.id) for s in scenes} if scenes else set()
            all_assets = await self._asset_repo.get_by_project(
                project_id, asset_type=None, offset=0, limit=1000
            )
            assets = [
                a for a in all_assets
                if str(a.scene_id) in scene_ids
            ] if scene_ids else all_assets
            if assets:
                for asset in assets:
                    asset_type = asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type)
                    ref = asset.storage_ref or ""
                    if ref.startswith(("http://", "https://")):
                        zf.writestr(f"assets/{asset_type}_{asset.id}_url.txt", ref)
                        continue
                    local_path = ref
                    if ref.startswith("local://"):
                        local_path = ref[len("local://"):]
                    if local_path and os.path.isfile(local_path):
                        arcname = f"assets/{asset_type}_{asset.id}{os.path.splitext(local_path)[1]}"
                        zf.write(local_path, arcname)
                    else:
                        info = (
                            f"Asset Type: {asset_type}\n"
                            f"Storage Ref: {ref}\n"
                            f"Storage Type: {asset.storage_type}\n"
                        )
                        zf.writestr(f"assets/{asset_type}_{asset.id}_info.txt", info)
            else:
                zf.writestr(
                    "assets/not_available.txt",
                    "No generated assets (thumbnail/video) available. "
                    "This workflow is running in placeholder mode without real image/video generation.",
                )

            # Always include the final rendered video if it exists on disk.
            settings = get_settings()
            final_video_path = (
                Path(settings.storage.local_path)
                / f"projects/{project_id}/final_video.mp4"
            )
            if final_video_path.exists():
                zf.write(
                    str(final_video_path),
                    f"final_video/{final_video_path.name}",
                )
            else:
                zf.writestr(
                    "final_video/not_available.txt",
                    "Final video has not been rendered yet.",
                )

            # Include all per-project workflow log files if they exist.
            project_log_dir = Path(settings.storage.local_path) / "projects" / str(project_id) / "logs"
            if project_log_dir.exists():
                for log_file in sorted(project_log_dir.glob("workflow_*.txt")):
                    zf.write(str(log_file), f"logs/{log_file.name}")
            else:
                zf.writestr(
                    "logs/not_available.txt",
                    "No workflow log files available yet.",
                )

        buffer.seek(0)
        return buffer

    async def get_final_video_path(self, project_id: UUID) -> Path | None:
        """Return the path to the rendered ``final_video.mp4``, if it exists."""
        settings = get_settings()
        video_path = (
            Path(settings.storage.local_path)
            / f"projects/{project_id}/final_video.mp4"
        )
        return video_path if video_path.exists() else None
