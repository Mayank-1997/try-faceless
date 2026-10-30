"""Business domain DTOs — request and response data transfer objects.

Pydantic v2 models for validating input and shaping output for the
AI Video Studio business domain. ORM models are never exposed through
these DTOs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Generic DTOs
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# ---------------------------------------------------------------------------
# Project DTOs
# ---------------------------------------------------------------------------
class CreateProjectRequest(BaseModel):
    """POST /projects request body."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="")
    language: str = Field(default="en", max_length=10)
    audience: str = Field(default="")
    content_type: str = Field(default="youtube_video")
    video_style: str = Field(default="mixed")
    target_duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    aspect_ratio: str = Field(default="16:9", max_length=10)
    production_mode: Literal["explainer", "direct_cinematic"] = "explainer"
    visual_anchor: str = Field(default="")
    clip_beats: list[str] = Field(default_factory=list, max_length=100)
    avoid: str = Field(default="")
    narration_text: str = Field(default="")
    tags: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_direct_cinematic(self) -> CreateProjectRequest:
        if self.production_mode == "direct_cinematic":
            if self.content_type != "youtube_video" or not self.description.strip():
                raise ValueError("Direct cinematic video requires a YouTube video description")
            if not self.target_duration_seconds or not 4 <= self.target_duration_seconds <= 120:
                raise ValueError("Direct cinematic duration must be between 4 and 120 seconds")
            if not self.visual_anchor.strip() or not self.clip_beats or any(not beat.strip() for beat in self.clip_beats):
                raise ValueError("Direct cinematic video requires a visual anchor and ordered clip beats")
            from src.application.services.direct_cinematic import (
                MAX_KLING_PROMPT_CHARS,
                MAX_VEO_PROMPT_CHARS,
                _active_video_provider,
                max_direct_prompt_chars,
                plan_direct_segments,
            )

            provider = _active_video_provider()
            prompt_limit = MAX_KLING_PROMPT_CHARS if provider == "kling" else MAX_VEO_PROMPT_CHARS
            expected_clips = len(plan_direct_segments(self.target_duration_seconds))
            if len(self.clip_beats) != expected_clips:
                raise ValueError(f"Direct cinematic video requires exactly {expected_clips} clip beats")
            if max_direct_prompt_chars(self.description, self.visual_anchor, self.avoid, self.clip_beats) > prompt_limit:
                raise ValueError(f"Direct cinematic specification exceeds the {provider} prompt limit")
            if self.narration_text and len(self.narration_text.split()) > self.target_duration_seconds * 2:
                raise ValueError("Narration is too long for the requested duration")
        return self

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        # Veo supports 16:9 and 9:16 only.
        valid = {"16:9", "9:16"}
        if v not in valid:
            raise ValueError(f"Invalid aspect_ratio. Must be one of: {valid}")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        from src.core.enums import ContentType
        valid = {ct.value for ct in ContentType}
        if v not in valid:
            raise ValueError(f"Invalid content_type. Must be one of: {valid}")
        return v

    @field_validator("video_style")
    @classmethod
    def validate_video_style(cls, v: str) -> str:
        from src.core.enums import VideoStyle
        valid = {vs.value for vs in VideoStyle}
        if v not in valid:
            raise ValueError(f"Invalid video_style. Must be one of: {valid}")
        return v


class UpdateProjectRequest(BaseModel):
    """PATCH /projects/{id} request body."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    language: str | None = Field(default=None, max_length=10)
    audience: str | None = Field(default=None, max_length=500)
    content_type: str | None = None
    video_style: str | None = None
    target_duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    aspect_ratio: str | None = Field(default=None, max_length=10)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    """Response DTO for a project."""

    id: UUID
    owner_id: UUID
    title: str
    description: str
    language: str
    audience: str
    content_type: str
    video_style: str
    target_duration_seconds: int | None
    status: str
    current_step: str
    tags: list[str]
    metadata: dict[str, Any]
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Workflow DTOs
# ---------------------------------------------------------------------------
class WorkflowResponse(BaseModel):
    """Response DTO for a workflow."""

    id: UUID
    project_id: UUID
    version: int
    current_step: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    execution_time_seconds: float | None
    failure_reason: str | None
    retry_count: int
    checkpoint_ref: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Research DTOs
# ---------------------------------------------------------------------------
class ResearchResponse(BaseModel):
    """Response DTO for a research version."""

    id: UUID
    project_id: UUID
    workflow_id: UUID | None
    summary: str
    timeline: list[str]
    interesting_facts: list[str]
    sources: list[str]
    keywords: list[str]
    references: list[str]
    statistics: dict[str, Any]
    audience_pain_points: list[str]
    version: int
    status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Script DTOs
# ---------------------------------------------------------------------------
class CreateScriptRequest(BaseModel):
    """POST /projects/{id}/scripts request body."""

    hook: str = Field(default="", max_length=2000)
    body: str = Field(..., min_length=1, max_length=50000)
    cta: str = Field(default="", max_length=2000)
    language: str = Field(default="en", max_length=10)


class ScriptResponse(BaseModel):
    """Response DTO for a script version."""

    id: UUID
    project_id: UUID
    workflow_id: UUID | None
    hook: str
    body: str
    cta: str
    word_count: int
    estimated_duration_seconds: int
    version: int
    language: str
    status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Storyboard DTOs
# ---------------------------------------------------------------------------
class StoryboardResponse(BaseModel):
    """Response DTO for a storyboard version."""

    id: UUID
    project_id: UUID
    workflow_id: UUID | None
    version: int
    scene_count: int
    estimated_duration_seconds: int
    style: str
    status: str
    narrative_structure: str
    pacing_notes: str
    package_json: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Scene DTOs
# ---------------------------------------------------------------------------
class SceneResponse(BaseModel):
    """Response DTO for a scene."""

    id: UUID
    project_id: UUID
    storyboard_id: UUID | None
    workflow_id: UUID | None
    scene_number: int
    title: str
    duration_seconds: float
    narration: str
    importance_score: float
    emotion: str
    visual_type: str
    camera_angle: str | None
    camera_motion: str | None
    lens: str | None
    lighting: str | None
    composition: str | None
    transition: str | None
    subtitle: str | None
    voice_timing: dict[str, Any]
    background_music: str | None
    sound_effects: list[str]
    generation_status: str
    review_status: str
    created_at: datetime
    updated_at: datetime


class SceneListResponse(BaseModel):
    """Paginated list of scenes."""

    items: list[SceneResponse]
    total: int


# ---------------------------------------------------------------------------
# Asset DTOs
# ---------------------------------------------------------------------------
class AssetResponse(BaseModel):
    """Response DTO for an asset."""

    id: UUID
    project_id: UUID
    scene_id: UUID | None
    asset_type: str
    provider: str
    prompt_version: str
    generation_cost_usd: float
    generation_time_seconds: float
    generation_status: str
    storage_type: str
    storage_ref: str
    metadata: dict[str, Any]
    quality_score: float | None
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Paginated list of assets."""

    items: list[AssetResponse]
    total: int


# ---------------------------------------------------------------------------
# Generation Job DTOs
# ---------------------------------------------------------------------------
class GenerationJobResponse(BaseModel):
    """Response DTO for a generation job."""

    id: UUID
    project_id: UUID
    workflow_id: UUID | None
    scene_id: UUID | None
    job_type: str
    status: str
    priority: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: str | None
    retry_count: int
    max_retries: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    execution_time_seconds: float | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Prompt Execution DTOs
# ---------------------------------------------------------------------------
class PromptExecutionResponse(BaseModel):
    """Response DTO for a prompt execution."""

    id: UUID
    project_id: UUID | None
    workflow_id: UUID | None
    scene_id: UUID | None
    agent_type: str
    prompt_template: str
    prompt_variables: dict[str, Any]
    rendered_prompt: str
    provider: str
    model: str
    temperature: float
    response: str
    latency_ms: int
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    status: str
    error_message: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Analytics DTOs
# ---------------------------------------------------------------------------
class CostSummaryResponse(BaseModel):
    """Response DTO for cost summary."""

    total_cost_usd: float
    cost_by_provider: dict[str, float]
    cost_by_category: dict[str, float]


class TokenUsageSummaryResponse(BaseModel):
    """Response DTO for token usage summary."""

    total_tokens: int
    tokens_by_provider: dict[str, int]


# ---------------------------------------------------------------------------
# Mapper helpers (domain entity → response DTO)
# ---------------------------------------------------------------------------
def project_to_response(project: Any) -> ProjectResponse:
    """Convert a Project domain entity to ProjectResponse DTO."""
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        title=project.title,
        description=project.description,
        language=project.language,
        audience=project.audience,
        content_type=project.content_type.value if hasattr(project.content_type, "value") else project.content_type,
        video_style=project.video_style.value if hasattr(project.video_style, "value") else project.video_style,
        target_duration_seconds=project.target_duration_seconds,
        status=project.status.value if hasattr(project.status, "value") else project.status,
        current_step=project.current_step.value if hasattr(project.current_step, "value") else project.current_step,
        tags=project.tags,
        metadata=project.metadata,
        created_by=project.created_by,
        updated_by=project.updated_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        deleted_at=project.deleted_at,
    )


def workflow_to_response(workflow: Any) -> WorkflowResponse:
    """Convert a Workflow domain entity to WorkflowResponse DTO."""
    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        version=workflow.version,
        current_step=workflow.current_step.value if hasattr(workflow.current_step, "value") else workflow.current_step,
        status=workflow.status.value if hasattr(workflow.status, "value") else workflow.status,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        execution_time_seconds=workflow.execution_time_seconds,
        failure_reason=workflow.failure_reason,
        retry_count=workflow.retry_count,
        checkpoint_ref=workflow.checkpoint_ref,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def scene_to_response(scene: Any) -> SceneResponse:
    """Convert a Scene domain entity to SceneResponse DTO."""
    return SceneResponse(
        id=scene.id,
        project_id=scene.project_id,
        storyboard_id=scene.storyboard_id,
        workflow_id=scene.workflow_id,
        scene_number=scene.scene_number,
        title=scene.title,
        duration_seconds=scene.duration_seconds,
        narration=scene.narration,
        importance_score=scene.importance_score,
        emotion=scene.emotion,
        visual_type=scene.visual_type.value if hasattr(scene.visual_type, "value") else scene.visual_type,
        camera_angle=scene.camera_angle.value if scene.camera_angle and hasattr(scene.camera_angle, "value") else scene.camera_angle,
        camera_motion=scene.camera_motion.value if scene.camera_motion and hasattr(scene.camera_motion, "value") else scene.camera_motion,
        lens=scene.lens,
        lighting=scene.lighting,
        composition=scene.composition,
        transition=scene.transition.value if scene.transition and hasattr(scene.transition, "value") else scene.transition,
        subtitle=scene.subtitle,
        voice_timing=scene.voice_timing,
        background_music=scene.background_music,
        sound_effects=scene.sound_effects,
        generation_status=scene.generation_status.value if hasattr(scene.generation_status, "value") else scene.generation_status,
        review_status=scene.review_status.value if hasattr(scene.review_status, "value") else scene.review_status,
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


def asset_to_response(asset: Any) -> AssetResponse:
    """Convert a BaseAsset domain entity to AssetResponse DTO."""
    return AssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        scene_id=asset.scene_id,
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type,
        provider=asset.provider.value if hasattr(asset.provider, "value") else str(asset.provider),
        prompt_version=asset.prompt_version,
        generation_cost_usd=asset.generation_cost_usd,
        generation_time_seconds=asset.generation_time_seconds,
        generation_status=asset.generation_status.value if hasattr(asset.generation_status, "value") else asset.generation_status,
        storage_type=asset.storage_type.value if hasattr(asset.storage_type, "value") else asset.storage_type,
        storage_ref=asset.storage_ref,
        metadata=asset.metadata,
        quality_score=asset.quality_score,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )
