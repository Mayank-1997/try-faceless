"""SQLAlchemy repository implementations for the business domain.

Each repository converts between ORM models and domain entities.
ORM models are never exposed outside this layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import (
    AIProvider,
    AssetGenerationStatus,
    AssetType,
    ContentType,
    JobPriority,
    JobStatus,
    JobType,
    ProjectStatus,
    PromptExecutionStatus,
    ResearchStatus,
    SceneGenerationStatus,
    SceneReviewStatus,
    ScriptStatus,
    StoryboardStatus,
    StorageType,
    TransitionType,
    VideoStyle,
    VisualType,
    WorkflowStatus,
    WorkflowStep,
    CameraAngle,
    CameraMotion,
)
from src.domain.entities.asset import (
    BaseAsset,
    ImageAsset,
    SubtitleAsset,
    ThumbnailAsset,
    VideoAsset,
    VoiceAsset,
)
from src.domain.entities.cost_tracking import CostRecord
from src.domain.entities.generation_job import GenerationJob
from src.domain.entities.project import Project
from src.domain.entities.prompt_execution import PromptExecution
from src.domain.entities.research import Research
from src.domain.entities.scene import Scene
from src.domain.entities.script import Script
from src.domain.entities.storyboard import Storyboard
from src.domain.entities.token_tracking import TokenUsageRecord
from src.domain.entities.workflow import Workflow
from src.domain.repositories.business_repositories import (
    AnalyticsRepository,
    AssetRepository,
    GenerationJobRepository,
    ProjectRepository,
    PromptExecutionRepository,
    ResearchRepository,
    SceneRepository,
    ScriptRepository,
    StoryboardRepository,
    WorkflowRepository,
)
from src.persistence.models.business import (
    AssetModel,
    CostRecordModel,
    GenerationJobModel,
    ImageAssetModel,
    ProjectModel,
    PromptExecutionModel,
    ResearchModel,
    SceneModel,
    ScriptModel,
    StoryboardModel,
    SubtitleAssetModel,
    ThumbnailAssetModel,
    TokenUsageRecordModel,
    VideoAssetModel,
    VoiceAssetModel,
    WorkflowModel,
)


def _json_loads(value: str, default: object) -> object:
    """Safely parse JSON, returning default on failure."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _json_dumps(value: object) -> str:
    """Safely serialize to JSON."""
    return json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# ORM → Domain mappers
# ---------------------------------------------------------------------------
def _map_project(orm: ProjectModel) -> Project:
    return Project(
        id=orm.id,
        owner_id=orm.owner_id,
        title=orm.title,
        description=orm.description,
        language=orm.language,
        audience=orm.audience,
        content_type=ContentType(orm.content_type),
        video_style=VideoStyle(orm.video_style),
        target_duration_seconds=orm.target_duration_seconds,
        status=ProjectStatus(orm.status),
        current_step=WorkflowStep(orm.current_step),
        tags=_json_loads(orm.tags, []) if isinstance(orm.tags, str) else (orm.tags or []),
        metadata=_json_loads(orm.metadata_, {}) if isinstance(orm.metadata_, str) else (orm.metadata_ or {}),
        created_by=orm.created_by,
        updated_by=orm.updated_by,
        deleted_by=orm.deleted_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        deleted_at=orm.deleted_at,
    )


def _map_workflow(orm: WorkflowModel) -> Workflow:
    return Workflow(
        id=orm.id,
        project_id=orm.project_id,
        version=orm.version,
        current_step=WorkflowStep(orm.current_step),
        status=WorkflowStatus(orm.status),
        started_at=orm.started_at,
        completed_at=orm.completed_at,
        execution_time_seconds=orm.execution_time_seconds,
        failure_reason=orm.failure_reason,
        retry_count=orm.retry_count,
        checkpoint_ref=orm.checkpoint_ref,
        created_by=orm.created_by,
        updated_by=orm.updated_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_research(orm: ResearchModel) -> Research:
    return Research(
        id=orm.id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        summary=orm.summary,
        timeline=_json_loads(orm.timeline, []),
        interesting_facts=_json_loads(orm.interesting_facts, []),
        sources=_json_loads(orm.sources, []),
        keywords=_json_loads(orm.keywords, []),
        references=_json_loads(orm.references, []),
        statistics=_json_loads(orm.statistics, {}),
        audience_pain_points=_json_loads(orm.audience_pain_points, []),
        version=orm.version,
        status=ResearchStatus(orm.status),
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_script(orm: ScriptModel) -> Script:
    return Script(
        id=orm.id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        hook=orm.hook,
        body=orm.body,
        cta=orm.cta,
        word_count=orm.word_count,
        estimated_duration_seconds=orm.estimated_duration_seconds,
        version=orm.version,
        language=orm.language,
        status=ScriptStatus(orm.status),
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_storyboard(orm: StoryboardModel) -> Storyboard:
    return Storyboard(
        id=orm.id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        version=orm.version,
        scene_count=orm.scene_count,
        estimated_duration_seconds=orm.estimated_duration_seconds,
        style=VideoStyle(orm.style),
        status=StoryboardStatus(orm.status),
        narrative_structure=orm.narrative_structure,
        pacing_notes=orm.pacing_notes,
        package_json=orm.package_json or "",
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_scene(orm: SceneModel) -> Scene:
    return Scene(
        id=orm.id,
        project_id=orm.project_id,
        storyboard_id=orm.storyboard_id,
        workflow_id=orm.workflow_id,
        scene_number=orm.scene_number,
        title=orm.title,
        duration_seconds=orm.duration_seconds,
        narration=orm.narration,
        importance_score=orm.importance_score,
        emotion=orm.emotion,
        visual_type=VisualType(orm.visual_type),
        camera_angle=CameraAngle(orm.camera_angle) if orm.camera_angle else None,
        camera_motion=CameraMotion(orm.camera_motion) if orm.camera_motion else None,
        lens=orm.lens,
        lighting=orm.lighting,
        composition=orm.composition,
        transition=TransitionType(orm.transition) if orm.transition else None,
        subtitle=orm.subtitle,
        voice_timing=_json_loads(orm.voice_timing, {}),
        background_music=orm.background_music,
        sound_effects=_json_loads(orm.sound_effects, []),
        generation_status=SceneGenerationStatus(orm.generation_status),
        review_status=SceneReviewStatus(orm.review_status),
        created_by=orm.created_by,
        updated_by=orm.updated_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_asset(orm: AssetModel) -> BaseAsset:
    """Map an ORM asset to the correct domain subtype based on discriminator."""
    common = dict(
        id=orm.id,
        project_id=orm.project_id,
        scene_id=orm.scene_id,
        provider=orm.provider,
        prompt_version=orm.prompt_version,
        generation_cost_usd=orm.generation_cost_usd,
        generation_time_seconds=orm.generation_time_seconds,
        generation_status=AssetGenerationStatus(orm.generation_status),
        storage_type=StorageType(orm.storage_type),
        storage_ref=orm.storage_ref,
        metadata=_json_loads(orm.metadata_, {}),
        quality_score=orm.quality_score,
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
    asset_type = orm.asset_type
    if isinstance(orm, ImageAssetModel):
        return ImageAsset(
            width=orm.width, height=orm.height, format=orm.format,
            prompt=orm.prompt, negative_prompt=orm.negative_prompt, **common,
        )
    if isinstance(orm, VideoAssetModel):
        return VideoAsset(
            width=orm.width, height=orm.height, duration_seconds=orm.duration_seconds,
            fps=orm.fps, format=orm.format, prompt=orm.prompt, **common,
        )
    if isinstance(orm, VoiceAssetModel):
        return VoiceAsset(
            duration_seconds=orm.duration_seconds, language=orm.language,
            voice_name=orm.voice_name, speaking_rate=orm.speaking_rate,
            pitch=orm.pitch, format=orm.format, **common,
        )
    if isinstance(orm, SubtitleAssetModel):
        return SubtitleAsset(
            language=orm.language, format=orm.format, word_count=orm.word_count, **common,
        )
    if isinstance(orm, ThumbnailAssetModel):
        return ThumbnailAsset(
            width=orm.width, height=orm.height, format=orm.format,
            is_default=orm.is_default, **common,
        )
    return BaseAsset(asset_type=AssetType(orm.asset_type), **common)


def _map_job(orm: GenerationJobModel) -> GenerationJob:
    return GenerationJob(
        id=orm.id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        scene_id=orm.scene_id,
        job_type=JobType(orm.job_type),
        status=JobStatus(orm.status),
        priority=JobPriority(orm.priority),
        payload=_json_loads(orm.payload, {}),
        result=_json_loads(orm.result, {}),
        error_message=orm.error_message,
        retry_count=orm.retry_count,
        max_retries=orm.max_retries,
        queued_at=orm.queued_at,
        started_at=orm.started_at,
        completed_at=orm.completed_at,
        execution_time_seconds=orm.execution_time_seconds,
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_prompt_execution(orm: PromptExecutionModel) -> PromptExecution:
    return PromptExecution(
        id=orm.id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        scene_id=orm.scene_id,
        agent_type=orm.agent_type,
        prompt_template=orm.prompt_template,
        prompt_variables=_json_loads(orm.prompt_variables, {}),
        rendered_prompt=orm.rendered_prompt,
        provider=orm.provider,
        model=orm.model,
        temperature=orm.temperature,
        response=orm.response,
        latency_ms=orm.latency_ms,
        cost_usd=orm.cost_usd,
        input_tokens=orm.input_tokens,
        output_tokens=orm.output_tokens,
        cached_tokens=orm.cached_tokens,
        status=PromptExecutionStatus(orm.status),
        error_message=orm.error_message,
        created_at=orm.created_at,
    )


def _map_cost_record(orm: CostRecordModel) -> CostRecord:
    return CostRecord(
        id=orm.id,
        user_id=orm.user_id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        job_id=orm.job_id,
        scene_id=orm.scene_id,
        asset_id=orm.asset_id,
        provider=orm.provider,
        cost_usd=orm.cost_usd,
        cost_category=orm.cost_category,
        period=orm.period,
        period_start=orm.period_start,
        period_end=orm.period_end,
        metadata=_json_loads(orm.metadata_, {}),
        created_at=orm.created_at,
    )


def _map_token_record(orm: TokenUsageRecordModel) -> TokenUsageRecord:
    return TokenUsageRecord(
        id=orm.id,
        user_id=orm.user_id,
        project_id=orm.project_id,
        workflow_id=orm.workflow_id,
        provider=orm.provider,
        agent_type=orm.agent_type,
        model=orm.model,
        input_tokens=orm.input_tokens,
        output_tokens=orm.output_tokens,
        cached_tokens=orm.cached_tokens,
        metadata=_json_loads(orm.metadata_, {}),
        created_at=orm.created_at,
    )


# ---------------------------------------------------------------------------
# Project Repository Implementation
# ---------------------------------------------------------------------------
class ProjectRepositoryImpl(ProjectRepository):
    """SQLAlchemy implementation of ``ProjectRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project: Project) -> Project:
        orm = ProjectModel(
            owner_id=project.owner_id,
            title=project.title,
            description=project.description,
            language=project.language,
            audience=project.audience,
            content_type=project.content_type.value,
            video_style=project.video_style.value,
            target_duration_seconds=project.target_duration_seconds,
            status=project.status.value,
            current_step=project.current_step.value,
            tags=_json_dumps(project.tags),
            metadata_=_json_dumps(project.metadata),
            created_by=project.created_by,
            updated_by=project.updated_by,
            deleted_at=project.deleted_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_project(orm)

    async def get_by_id(self, project_id: UUID) -> Project | None:
        stmt = select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_project(orm) if orm else None

    async def get_by_owner(
        self, owner_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Project]:
        stmt = (
            select(ProjectModel)
            .where(
                ProjectModel.owner_id == owner_id,
                ProjectModel.deleted_at.is_(None),
            )
            .order_by(ProjectModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_project(orm) for orm in result.scalars().all()]

    async def update(self, project: Project) -> Project:
        stmt = select(ProjectModel).where(ProjectModel.id == project.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.title = project.title
        orm.description = project.description
        orm.language = project.language
        orm.audience = project.audience
        orm.content_type = project.content_type.value
        orm.video_style = project.video_style.value
        orm.target_duration_seconds = project.target_duration_seconds
        orm.status = project.status.value
        orm.current_step = project.current_step.value
        orm.tags = _json_dumps(project.tags)
        orm.metadata_ = _json_dumps(project.metadata)
        orm.updated_by = project.updated_by
        orm.deleted_at = project.deleted_at
        orm.deleted_by = project.deleted_by
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_project(orm)

    async def soft_delete(self, project_id: UUID, deleted_by: UUID) -> bool:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return False
        orm.deleted_at = datetime.now(timezone.utc)
        orm.deleted_by = deleted_by
        orm.status = ProjectStatus.CANCELLED.value
        await self._session.flush()
        return True

    async def list_projects(
        self,
        *,
        status: ProjectStatus | None = None,
        content_type: ContentType | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        stmt = select(ProjectModel).where(ProjectModel.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(ProjectModel.status == status.value)
        if content_type is not None:
            stmt = stmt.where(ProjectModel.content_type == content_type.value)
        stmt = stmt.order_by(ProjectModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [_map_project(orm) for orm in result.scalars().all()]

    async def count_projects(
        self,
        *,
        status: ProjectStatus | None = None,
        owner_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count(ProjectModel.id)).where(ProjectModel.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(ProjectModel.status == status.value)
        if owner_id is not None:
            stmt = stmt.where(ProjectModel.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ---------------------------------------------------------------------------
# Workflow Repository Implementation
# ---------------------------------------------------------------------------
class WorkflowRepositoryImpl(WorkflowRepository):
    """SQLAlchemy implementation of ``WorkflowRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workflow: Workflow) -> Workflow:
        orm = WorkflowModel(
            project_id=workflow.project_id,
            version=workflow.version,
            current_step=workflow.current_step.value,
            status=workflow.status.value,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            execution_time_seconds=workflow.execution_time_seconds,
            failure_reason=workflow.failure_reason,
            retry_count=workflow.retry_count,
            checkpoint_ref=workflow.checkpoint_ref,
            created_by=workflow.created_by,
            updated_by=workflow.updated_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_workflow(orm)

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_workflow(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Workflow]:
        stmt = (
            select(WorkflowModel)
            .where(WorkflowModel.project_id == project_id)
            .order_by(WorkflowModel.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_workflow(orm) for orm in result.scalars().all()]

    async def get_active_workflow(self, project_id: UUID) -> Workflow | None:
        active_statuses = [
            WorkflowStatus.PENDING.value,
            WorkflowStatus.RUNNING.value,
            WorkflowStatus.PAUSED.value,
        ]
        stmt = (
            select(WorkflowModel)
            .where(
                WorkflowModel.project_id == project_id,
                WorkflowModel.status.in_(active_statuses),
            )
            .order_by(WorkflowModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_workflow(orm) if orm else None

    async def get_latest_workflow(self, project_id: UUID) -> Workflow | None:
        stmt = (
            select(WorkflowModel)
            .where(WorkflowModel.project_id == project_id)
            .order_by(WorkflowModel.version.desc(), WorkflowModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_workflow(orm) if orm else None

    async def update(self, workflow: Workflow) -> Workflow:
        stmt = select(WorkflowModel).where(WorkflowModel.id == workflow.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.current_step = workflow.current_step.value
        orm.status = workflow.status.value
        orm.started_at = workflow.started_at
        orm.completed_at = workflow.completed_at
        orm.execution_time_seconds = workflow.execution_time_seconds
        orm.failure_reason = workflow.failure_reason
        orm.retry_count = workflow.retry_count
        orm.checkpoint_ref = workflow.checkpoint_ref
        orm.updated_by = workflow.updated_by
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_workflow(orm)

    async def list_by_status(
        self, status: WorkflowStatus, *, offset: int = 0, limit: int = 50
    ) -> list[Workflow]:
        stmt = (
            select(WorkflowModel)
            .where(WorkflowModel.status == status.value)
            .order_by(WorkflowModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_workflow(orm) for orm in result.scalars().all()]


# ---------------------------------------------------------------------------
# Research Repository Implementation
# ---------------------------------------------------------------------------
class ResearchRepositoryImpl(ResearchRepository):
    """SQLAlchemy implementation of ``ResearchRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, research: Research) -> Research:
        orm = ResearchModel(
            project_id=research.project_id,
            workflow_id=research.workflow_id,
            summary=research.summary,
            timeline=_json_dumps(research.timeline),
            interesting_facts=_json_dumps(research.interesting_facts),
            sources=_json_dumps(research.sources),
            keywords=_json_dumps(research.keywords),
            references=_json_dumps(research.references),
            statistics=_json_dumps(research.statistics),
            audience_pain_points=_json_dumps(research.audience_pain_points),
            version=research.version,
            status=research.status.value,
            created_by=research.created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_research(orm)

    async def get_by_id(self, research_id: UUID) -> Research | None:
        stmt = select(ResearchModel).where(ResearchModel.id == research_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_research(orm) if orm else None

    async def get_latest_version(self, project_id: UUID) -> Research | None:
        stmt = (
            select(ResearchModel)
            .where(ResearchModel.project_id == project_id)
            .order_by(ResearchModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_research(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Research]:
        stmt = (
            select(ResearchModel)
            .where(ResearchModel.project_id == project_id)
            .order_by(ResearchModel.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_research(orm) for orm in result.scalars().all()]

    async def update(self, research: Research) -> Research:
        stmt = select(ResearchModel).where(ResearchModel.id == research.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.summary = research.summary
        orm.timeline = _json_dumps(research.timeline)
        orm.interesting_facts = _json_dumps(research.interesting_facts)
        orm.sources = _json_dumps(research.sources)
        orm.keywords = _json_dumps(research.keywords)
        orm.references = _json_dumps(research.references)
        orm.statistics = _json_dumps(research.statistics)
        orm.audience_pain_points = _json_dumps(research.audience_pain_points)
        orm.status = research.status.value
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_research(orm)

    async def supersede_previous_versions(self, project_id: UUID, keep_version: int) -> int:
        stmt = (
            select(ResearchModel)
            .where(
                ResearchModel.project_id == project_id,
                ResearchModel.version < keep_version,
                ResearchModel.status != ResearchStatus.SUPERSEDED.value,
            )
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        count = 0
        for orm in orms:
            orm.status = ResearchStatus.SUPERSEDED.value
            count += 1
        if count:
            await self._session.flush()
        return count


# ---------------------------------------------------------------------------
# Script Repository Implementation
# ---------------------------------------------------------------------------
class ScriptRepositoryImpl(ScriptRepository):
    """SQLAlchemy implementation of ``ScriptRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, script: Script) -> Script:
        orm = ScriptModel(
            project_id=script.project_id,
            workflow_id=script.workflow_id,
            hook=script.hook,
            body=script.body,
            cta=script.cta,
            word_count=script.word_count,
            estimated_duration_seconds=script.estimated_duration_seconds,
            version=script.version,
            language=script.language,
            status=script.status.value,
            created_by=script.created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_script(orm)

    async def get_by_id(self, script_id: UUID) -> Script | None:
        stmt = select(ScriptModel).where(ScriptModel.id == script_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_script(orm) if orm else None

    async def get_latest_version(self, project_id: UUID) -> Script | None:
        stmt = (
            select(ScriptModel)
            .where(ScriptModel.project_id == project_id)
            .order_by(ScriptModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_script(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Script]:
        stmt = (
            select(ScriptModel)
            .where(ScriptModel.project_id == project_id)
            .order_by(ScriptModel.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_script(orm) for orm in result.scalars().all()]

    async def update(self, script: Script) -> Script:
        stmt = select(ScriptModel).where(ScriptModel.id == script.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.hook = script.hook
        orm.body = script.body
        orm.cta = script.cta
        orm.word_count = script.word_count
        orm.estimated_duration_seconds = script.estimated_duration_seconds
        orm.status = script.status.value
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_script(orm)


# ---------------------------------------------------------------------------
# Storyboard Repository Implementation
# ---------------------------------------------------------------------------
class StoryboardRepositoryImpl(StoryboardRepository):
    """SQLAlchemy implementation of ``StoryboardRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, storyboard: Storyboard) -> Storyboard:
        orm = StoryboardModel(
            project_id=storyboard.project_id,
            workflow_id=storyboard.workflow_id,
            version=storyboard.version,
            scene_count=storyboard.scene_count,
            estimated_duration_seconds=storyboard.estimated_duration_seconds,
            style=storyboard.style.value,
            status=storyboard.status.value,
            narrative_structure=storyboard.narrative_structure,
            pacing_notes=storyboard.pacing_notes,
            package_json=storyboard.package_json,
            created_by=storyboard.created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_storyboard(orm)

    async def get_by_id(self, storyboard_id: UUID) -> Storyboard | None:
        stmt = select(StoryboardModel).where(StoryboardModel.id == storyboard_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_storyboard(orm) if orm else None

    async def get_latest_version(self, project_id: UUID) -> Storyboard | None:
        stmt = (
            select(StoryboardModel)
            .where(StoryboardModel.project_id == project_id)
            .order_by(StoryboardModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_storyboard(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Storyboard]:
        stmt = (
            select(StoryboardModel)
            .where(StoryboardModel.project_id == project_id)
            .order_by(StoryboardModel.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_storyboard(orm) for orm in result.scalars().all()]

    async def update(self, storyboard: Storyboard) -> Storyboard:
        stmt = select(StoryboardModel).where(StoryboardModel.id == storyboard.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.scene_count = storyboard.scene_count
        orm.estimated_duration_seconds = storyboard.estimated_duration_seconds
        orm.style = storyboard.style.value
        orm.status = storyboard.status.value
        orm.narrative_structure = storyboard.narrative_structure
        orm.pacing_notes = storyboard.pacing_notes
        orm.package_json = storyboard.package_json
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_storyboard(orm)


# ---------------------------------------------------------------------------
# Scene Repository Implementation
# ---------------------------------------------------------------------------
class SceneRepositoryImpl(SceneRepository):
    """SQLAlchemy implementation of ``SceneRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, scene: Scene) -> Scene:
        orm = SceneModel(
            project_id=scene.project_id,
            storyboard_id=scene.storyboard_id,
            workflow_id=scene.workflow_id,
            scene_number=scene.scene_number,
            title=scene.title,
            duration_seconds=scene.duration_seconds,
            narration=scene.narration,
            importance_score=scene.importance_score,
            emotion=scene.emotion,
            visual_type=scene.visual_type.value,
            camera_angle=scene.camera_angle.value if scene.camera_angle else None,
            camera_motion=scene.camera_motion.value if scene.camera_motion else None,
            lens=scene.lens,
            lighting=scene.lighting,
            composition=scene.composition,
            transition=scene.transition.value if scene.transition else None,
            subtitle=scene.subtitle,
            voice_timing=_json_dumps(scene.voice_timing),
            background_music=scene.background_music,
            sound_effects=_json_dumps(scene.sound_effects),
            generation_status=scene.generation_status.value,
            review_status=scene.review_status.value,
            created_by=scene.created_by,
            updated_by=scene.updated_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_scene(orm)

    async def get_by_id(self, scene_id: UUID) -> Scene | None:
        stmt = select(SceneModel).where(SceneModel.id == scene_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_scene(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 200
    ) -> list[Scene]:
        stmt = (
            select(SceneModel)
            .where(SceneModel.project_id == project_id)
            .order_by(SceneModel.scene_number.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_scene(orm) for orm in result.scalars().all()]

    async def get_by_storyboard(self, storyboard_id: UUID) -> list[Scene]:
        stmt = (
            select(SceneModel)
            .where(SceneModel.storyboard_id == storyboard_id)
            .order_by(SceneModel.scene_number.asc())
        )
        result = await self._session.execute(stmt)
        return [_map_scene(orm) for orm in result.scalars().all()]

    async def update(self, scene: Scene) -> Scene:
        stmt = select(SceneModel).where(SceneModel.id == scene.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.title = scene.title
        orm.duration_seconds = scene.duration_seconds
        orm.narration = scene.narration
        orm.importance_score = scene.importance_score
        orm.emotion = scene.emotion
        orm.visual_type = scene.visual_type.value
        orm.camera_angle = scene.camera_angle.value if scene.camera_angle else None
        orm.camera_motion = scene.camera_motion.value if scene.camera_motion else None
        orm.lens = scene.lens
        orm.lighting = scene.lighting
        orm.composition = scene.composition
        orm.transition = scene.transition.value if scene.transition else None
        orm.subtitle = scene.subtitle
        orm.voice_timing = _json_dumps(scene.voice_timing)
        orm.background_music = scene.background_music
        orm.sound_effects = _json_dumps(scene.sound_effects)
        orm.generation_status = scene.generation_status.value
        orm.review_status = scene.review_status.value
        orm.updated_by = scene.updated_by
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_scene(orm)

    async def bulk_create(self, scenes: list[Scene]) -> list[Scene]:
        orms = []
        for scene in scenes:
            orm = SceneModel(
                project_id=scene.project_id,
                storyboard_id=scene.storyboard_id,
                workflow_id=scene.workflow_id,
                scene_number=scene.scene_number,
                title=scene.title,
                duration_seconds=scene.duration_seconds,
                narration=scene.narration,
                importance_score=scene.importance_score,
                emotion=scene.emotion,
                visual_type=scene.visual_type.value,
                camera_angle=scene.camera_angle.value if scene.camera_angle else None,
                camera_motion=scene.camera_motion.value if scene.camera_motion else None,
                lens=scene.lens,
                lighting=scene.lighting,
                composition=scene.composition,
                transition=scene.transition.value if scene.transition else None,
                subtitle=scene.subtitle,
                voice_timing=_json_dumps(scene.voice_timing),
                background_music=scene.background_music,
                sound_effects=_json_dumps(scene.sound_effects),
                generation_status=scene.generation_status.value,
                review_status=scene.review_status.value,
                created_by=scene.created_by,
                updated_by=scene.updated_by,
            )
            self._session.add(orm)
            orms.append(orm)
        await self._session.flush()
        for orm in orms:
            await self._session.refresh(orm)
        return [_map_scene(orm) for orm in orms]

    async def delete_by_project(self, project_id: UUID) -> int:
        stmt = select(SceneModel).where(SceneModel.project_id == project_id)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        count = len(orms)
        for orm in orms:
            await self._session.delete(orm)
        if count:
            await self._session.flush()
        return count

    async def list_by_generation_status(
        self, project_id: UUID, status: SceneGenerationStatus
    ) -> list[Scene]:
        stmt = (
            select(SceneModel)
            .where(
                SceneModel.project_id == project_id,
                SceneModel.generation_status == status.value,
            )
            .order_by(SceneModel.scene_number.asc())
        )
        result = await self._session.execute(stmt)
        return [_map_scene(orm) for orm in result.scalars().all()]

    async def list_by_review_status(
        self, project_id: UUID, status: SceneReviewStatus
    ) -> list[Scene]:
        stmt = (
            select(SceneModel)
            .where(
                SceneModel.project_id == project_id,
                SceneModel.review_status == status.value,
            )
            .order_by(SceneModel.scene_number.asc())
        )
        result = await self._session.execute(stmt)
        return [_map_scene(orm) for orm in result.scalars().all()]


# ---------------------------------------------------------------------------
# Asset Repository Implementation
# ---------------------------------------------------------------------------
class AssetRepositoryImpl(AssetRepository):
    """SQLAlchemy implementation of ``AssetRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, asset: BaseAsset) -> BaseAsset:
        common = dict(
            project_id=asset.project_id,
            scene_id=asset.scene_id,
            asset_type=asset.asset_type.value,
            provider=asset.provider.value if hasattr(asset.provider, "value") else str(asset.provider),
            prompt_version=asset.prompt_version,
            generation_cost_usd=asset.generation_cost_usd,
            generation_time_seconds=asset.generation_time_seconds,
            generation_status=asset.generation_status.value,
            storage_type=asset.storage_type.value,
            storage_ref=asset.storage_ref,
            metadata_=_json_dumps(asset.metadata),
            quality_score=asset.quality_score,
            created_by=asset.created_by,
        )
        if isinstance(asset, ImageAsset):
            orm = ImageAssetModel(
                width=asset.width, height=asset.height, format=asset.format,
                prompt=asset.prompt, negative_prompt=asset.negative_prompt, **common,
            )
        elif isinstance(asset, VideoAsset):
            orm = VideoAssetModel(
                width=asset.width, height=asset.height, duration_seconds=asset.duration_seconds,
                fps=asset.fps, format=asset.format, prompt=asset.prompt, **common,
            )
        elif isinstance(asset, VoiceAsset):
            orm = VoiceAssetModel(
                duration_seconds=asset.duration_seconds, language=asset.language,
                voice_name=asset.voice_name, speaking_rate=asset.speaking_rate,
                pitch=asset.pitch, format=asset.format, **common,
            )
        elif isinstance(asset, SubtitleAsset):
            orm = SubtitleAssetModel(
                language=asset.language, format=asset.format, word_count=asset.word_count, **common,
            )
        elif isinstance(asset, ThumbnailAsset):
            orm = ThumbnailAssetModel(
                width=asset.width, height=asset.height, format=asset.format,
                is_default=asset.is_default, **common,
            )
        else:
            orm = AssetModel(**common)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_asset(orm)

    async def get_by_id(self, asset_id: UUID) -> BaseAsset | None:
        stmt = select(AssetModel).where(AssetModel.id == asset_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_asset(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, asset_type: AssetType | None = None,
        offset: int = 0, limit: int = 100,
    ) -> list[BaseAsset]:
        stmt = select(AssetModel).where(AssetModel.project_id == project_id)
        if asset_type is not None:
            stmt = stmt.where(AssetModel.asset_type == asset_type.value)
        stmt = stmt.order_by(AssetModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [_map_asset(orm) for orm in result.scalars().all()]

    async def get_by_scene(self, scene_id: UUID) -> list[BaseAsset]:
        stmt = (
            select(AssetModel)
            .where(AssetModel.scene_id == scene_id)
            .order_by(AssetModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_map_asset(orm) for orm in result.scalars().all()]

    async def update(self, asset: BaseAsset) -> BaseAsset:
        stmt = select(AssetModel).where(AssetModel.id == asset.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.provider = asset.provider.value if hasattr(asset.provider, "value") else str(asset.provider)
        orm.prompt_version = asset.prompt_version
        orm.generation_cost_usd = asset.generation_cost_usd
        orm.generation_time_seconds = asset.generation_time_seconds
        orm.generation_status = asset.generation_status.value
        orm.storage_type = asset.storage_type.value
        orm.storage_ref = asset.storage_ref
        orm.metadata_ = _json_dumps(asset.metadata)
        orm.quality_score = asset.quality_score
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_asset(orm)

    async def list_by_status(
        self, project_id: UUID, status: AssetGenerationStatus
    ) -> list[BaseAsset]:
        stmt = (
            select(AssetModel)
            .where(
                AssetModel.project_id == project_id,
                AssetModel.generation_status == status.value,
            )
            .order_by(AssetModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_map_asset(orm) for orm in result.scalars().all()]


# ---------------------------------------------------------------------------
# Generation Job Repository Implementation
# ---------------------------------------------------------------------------
class GenerationJobRepositoryImpl(GenerationJobRepository):
    """SQLAlchemy implementation of ``GenerationJobRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: GenerationJob) -> GenerationJob:
        orm = GenerationJobModel(
            project_id=job.project_id,
            workflow_id=job.workflow_id,
            scene_id=job.scene_id,
            job_type=job.job_type.value,
            status=job.status.value,
            priority=job.priority.value,
            payload=_json_dumps(job.payload),
            result=_json_dumps(job.result),
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            queued_at=job.queued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            execution_time_seconds=job.execution_time_seconds,
            created_by=job.created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_job(orm)

    async def get_by_id(self, job_id: UUID) -> GenerationJob | None:
        stmt = select(GenerationJobModel).where(GenerationJobModel.id == job_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_job(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[GenerationJob]:
        stmt = (
            select(GenerationJobModel)
            .where(GenerationJobModel.project_id == project_id)
            .order_by(GenerationJobModel.queued_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_job(orm) for orm in result.scalars().all()]

    async def update(self, job: GenerationJob) -> GenerationJob:
        stmt = select(GenerationJobModel).where(GenerationJobModel.id == job.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.status = job.status.value
        orm.priority = job.priority.value
        orm.payload = _json_dumps(job.payload)
        orm.result = _json_dumps(job.result)
        orm.error_message = job.error_message
        orm.retry_count = job.retry_count
        orm.started_at = job.started_at
        orm.completed_at = job.completed_at
        orm.execution_time_seconds = job.execution_time_seconds
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_job(orm)

    async def list_by_status(
        self, status: JobStatus, *, offset: int = 0, limit: int = 100
    ) -> list[GenerationJob]:
        stmt = (
            select(GenerationJobModel)
            .where(GenerationJobModel.status == status.value)
            .order_by(GenerationJobModel.queued_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_job(orm) for orm in result.scalars().all()]

    async def list_by_type(
        self, project_id: UUID, job_type: JobType
    ) -> list[GenerationJob]:
        stmt = (
            select(GenerationJobModel)
            .where(
                GenerationJobModel.project_id == project_id,
                GenerationJobModel.job_type == job_type.value,
            )
            .order_by(GenerationJobModel.queued_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_map_job(orm) for orm in result.scalars().all()]

    async def get_next_queued(self) -> GenerationJob | None:
        priority_order = [
            JobPriority.URGENT.value,
            JobPriority.HIGH.value,
            JobPriority.NORMAL.value,
            JobPriority.LOW.value,
        ]
        stmt = (
            select(GenerationJobModel)
            .where(GenerationJobModel.status == JobStatus.QUEUED.value)
            .order_by(
                GenerationJobModel.priority.in_(priority_order),
                GenerationJobModel.queued_at.asc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_job(orm) if orm else None


# ---------------------------------------------------------------------------
# Prompt Execution Repository Implementation
# ---------------------------------------------------------------------------
class PromptExecutionRepositoryImpl(PromptExecutionRepository):
    """SQLAlchemy implementation of ``PromptExecutionRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, execution: PromptExecution) -> PromptExecution:
        orm = PromptExecutionModel(
            project_id=execution.project_id,
            workflow_id=execution.workflow_id,
            scene_id=execution.scene_id,
            agent_type=execution.agent_type,
            prompt_template=execution.prompt_template,
            prompt_variables=_json_dumps(execution.prompt_variables),
            rendered_prompt=execution.rendered_prompt,
            provider=execution.provider.value if hasattr(execution.provider, "value") else str(execution.provider),
            model=execution.model,
            temperature=execution.temperature,
            response=execution.response,
            latency_ms=execution.latency_ms,
            cost_usd=execution.cost_usd,
            input_tokens=execution.input_tokens,
            output_tokens=execution.output_tokens,
            cached_tokens=execution.cached_tokens,
            status=execution.status.value,
            error_message=execution.error_message,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_prompt_execution(orm)

    async def get_by_id(self, execution_id: UUID) -> PromptExecution | None:
        stmt = select(PromptExecutionModel).where(PromptExecutionModel.id == execution_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_prompt_execution(orm) if orm else None

    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[PromptExecution]:
        stmt = (
            select(PromptExecutionModel)
            .where(PromptExecutionModel.project_id == project_id)
            .order_by(PromptExecutionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_prompt_execution(orm) for orm in result.scalars().all()]

    async def get_by_workflow(
        self, workflow_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[PromptExecution]:
        stmt = (
            select(PromptExecutionModel)
            .where(PromptExecutionModel.workflow_id == workflow_id)
            .order_by(PromptExecutionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_prompt_execution(orm) for orm in result.scalars().all()]

    async def update(self, execution: PromptExecution) -> PromptExecution:
        stmt = select(PromptExecutionModel).where(PromptExecutionModel.id == execution.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None  # type: ignore[return-value]
        orm.response = execution.response
        orm.latency_ms = execution.latency_ms
        orm.cost_usd = execution.cost_usd
        orm.input_tokens = execution.input_tokens
        orm.output_tokens = execution.output_tokens
        orm.cached_tokens = execution.cached_tokens
        orm.status = execution.status.value
        orm.error_message = execution.error_message
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_prompt_execution(orm)


# ---------------------------------------------------------------------------
# Analytics Repository Implementation
# ---------------------------------------------------------------------------
class AnalyticsRepositoryImpl(AnalyticsRepository):
    """SQLAlchemy implementation of ``AnalyticsRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Cost tracking ---

    async def create_cost_record(self, record: CostRecord) -> CostRecord:
        orm = CostRecordModel(
            user_id=record.user_id,
            project_id=record.project_id,
            workflow_id=record.workflow_id,
            job_id=record.job_id,
            scene_id=record.scene_id,
            asset_id=record.asset_id,
            provider=record.provider.value if hasattr(record.provider, "value") else str(record.provider),
            cost_usd=record.cost_usd,
            cost_category=record.cost_category,
            period=record.period.value,
            period_start=record.period_start,
            period_end=record.period_end,
            metadata_=_json_dumps(record.metadata),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_cost_record(orm)

    async def get_project_costs(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[CostRecord]:
        stmt = (
            select(CostRecordModel)
            .where(CostRecordModel.project_id == project_id)
            .order_by(CostRecordModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_cost_record(orm) for orm in result.scalars().all()]

    async def get_total_cost_by_project(self, project_id: UUID) -> float:
        stmt = select(func.coalesce(func.sum(CostRecordModel.cost_usd), 0.0)).where(
            CostRecordModel.project_id == project_id
        )
        result = await self._session.execute(stmt)
        return float(result.scalar_one())

    async def get_total_cost_by_user(
        self, user_id: UUID, *, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> float:
        stmt = select(func.coalesce(func.sum(CostRecordModel.cost_usd), 0.0)).where(
            CostRecordModel.user_id == user_id
        )
        if start_date is not None:
            stmt = stmt.where(CostRecordModel.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(CostRecordModel.created_at <= end_date)
        result = await self._session.execute(stmt)
        return float(result.scalar_one())

    async def get_cost_breakdown_by_provider(self, project_id: UUID) -> dict[str, float]:
        stmt = (
            select(CostRecordModel.provider, func.sum(CostRecordModel.cost_usd))
            .where(CostRecordModel.project_id == project_id)
            .group_by(CostRecordModel.provider)
        )
        result = await self._session.execute(stmt)
        return {provider: float(total) for provider, total in result.all()}

    async def get_cost_breakdown_by_category(self, project_id: UUID) -> dict[str, float]:
        stmt = (
            select(CostRecordModel.cost_category, func.sum(CostRecordModel.cost_usd))
            .where(CostRecordModel.project_id == project_id)
            .group_by(CostRecordModel.cost_category)
        )
        result = await self._session.execute(stmt)
        return {category: float(total) for category, total in result.all()}

    # --- Token tracking ---

    async def create_token_record(self, record: TokenUsageRecord) -> TokenUsageRecord:
        orm = TokenUsageRecordModel(
            user_id=record.user_id,
            project_id=record.project_id,
            workflow_id=record.workflow_id,
            provider=record.provider.value if hasattr(record.provider, "value") else str(record.provider),
            agent_type=record.agent_type,
            model=record.model,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cached_tokens=record.cached_tokens,
            metadata_=_json_dumps(record.metadata),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_token_record(orm)

    async def get_project_tokens(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[TokenUsageRecord]:
        stmt = (
            select(TokenUsageRecordModel)
            .where(TokenUsageRecordModel.project_id == project_id)
            .order_by(TokenUsageRecordModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_token_record(orm) for orm in result.scalars().all()]

    async def get_total_tokens_by_project(self, project_id: UUID) -> int:
        stmt = select(
            func.coalesce(func.sum(TokenUsageRecordModel.input_tokens + TokenUsageRecordModel.output_tokens), 0)
        ).where(TokenUsageRecordModel.project_id == project_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_total_tokens_by_user(
        self, user_id: UUID, *, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> int:
        stmt = select(
            func.coalesce(func.sum(TokenUsageRecordModel.input_tokens + TokenUsageRecordModel.output_tokens), 0)
        ).where(TokenUsageRecordModel.user_id == user_id)
        if start_date is not None:
            stmt = stmt.where(TokenUsageRecordModel.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(TokenUsageRecordModel.created_at <= end_date)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_token_breakdown_by_provider(self, project_id: UUID) -> dict[str, int]:
        stmt = (
            select(
                TokenUsageRecordModel.provider,
                func.sum(TokenUsageRecordModel.input_tokens + TokenUsageRecordModel.output_tokens),
            )
            .where(TokenUsageRecordModel.project_id == project_id)
            .group_by(TokenUsageRecordModel.provider)
        )
        result = await self._session.execute(stmt)
        return {provider: int(total) for provider, total in result.all()}


# Aliases for backward-compatible imports
SqlAlchemyProjectRepository = ProjectRepositoryImpl
SqlAlchemyWorkflowRepository = WorkflowRepositoryImpl
SqlAlchemyResearchRepository = ResearchRepositoryImpl
SqlAlchemyScriptRepository = ScriptRepositoryImpl
SqlAlchemyStoryboardRepository = StoryboardRepositoryImpl
SqlAlchemySceneRepository = SceneRepositoryImpl
SqlAlchemyAssetRepository = AssetRepositoryImpl
SqlAlchemyGenerationJobRepository = GenerationJobRepositoryImpl
SqlAlchemyPromptExecutionRepository = PromptExecutionRepositoryImpl
SqlAlchemyAnalyticsRepository = AnalyticsRepositoryImpl
