"""SQLAlchemy ORM models for the business domain (Phase 3).

Maps the domain entities (Project, Workflow, Research, Script,
Storyboard, Scene, Asset, GenerationJob, PromptExecution, CostRecord,
TokenUsageRecord) to database tables.

Uses single-table inheritance for assets::

    AssetModel (base, polymorphic_on="asset_type")
    ├── ImageAssetModel      (polymorphic_identity="image")
    ├── VideoAssetModel      (polymorphic_identity="video")
    ├── VoiceAssetModel      (polymorphic_identity="voice")
    ├── SubtitleAssetModel   (polymorphic_identity="subtitle")
    └── ThumbnailAssetModel  (polymorphic_identity="thumbnail")
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import (
    AuditMixin,
    Base,
    BaseModel,
    UUIDPrimaryKeyMixin,
)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectModel(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """ORM model for the ``projects`` table."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_content_type", "content_type"),
        Index("ix_projects_current_step", "current_step"),
        Index("ix_projects_created_at", "created_at"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    audience: Mapped[str] = mapped_column(Text, default="", server_default="")
    content_type: Mapped[str] = mapped_column(String(50), default="youtube_video", server_default="youtube_video", nullable=False)
    video_style: Mapped[str] = mapped_column(String(50), default="mixed", server_default="mixed")
    target_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False)
    current_step: Mapped[str] = mapped_column(String(50), default="initialization", server_default="initialization", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}", server_default="{}")  # JSON-encoded dict
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    workflows: Mapped[list["WorkflowModel"]] = relationship(
        "WorkflowModel", back_populates="project", lazy="selectin",
    )
    research_versions: Mapped[list["ResearchModel"]] = relationship(
        "ResearchModel", back_populates="project", lazy="selectin",
    )
    scripts: Mapped[list["ScriptModel"]] = relationship(
        "ScriptModel", back_populates="project", lazy="selectin",
    )
    storyboards: Mapped[list["StoryboardModel"]] = relationship(
        "StoryboardModel", back_populates="project", lazy="selectin",
    )
    scenes: Mapped[list["SceneModel"]] = relationship(
        "SceneModel", back_populates="project", lazy="selectin",
    )
    jobs: Mapped[list["GenerationJobModel"]] = relationship(
        "GenerationJobModel", back_populates="project", lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------
class WorkflowModel(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """ORM model for the ``workflows`` table."""

    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_project_id", "project_id"),
        Index("ix_workflows_status", "status"),
        Index("ix_workflows_current_step", "current_step"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    current_step: Mapped[str] = mapped_column(String(50), default="initialization", server_default="initialization", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    checkpoint_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="workflows")


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------
class ResearchModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``research`` table."""

    __tablename__ = "research"
    __table_args__ = (
        Index("ix_research_project_id", "project_id"),
        Index("ix_research_version", "version"),
        Index("ix_research_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    timeline: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    interesting_facts: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    sources: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    keywords: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    references: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    statistics: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON-encoded dict
    audience_pain_points: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="research_versions")


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------
class ScriptModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``scripts`` table."""

    __tablename__ = "scripts"
    __table_args__ = (
        Index("ix_scripts_project_id", "project_id"),
        Index("ix_scripts_version", "version"),
        Index("ix_scripts_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    hook: Mapped[str] = mapped_column(Text, default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    cta: Mapped[str] = mapped_column(Text, default="", server_default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    estimated_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="scripts")


# ---------------------------------------------------------------------------
# Storyboards
# ---------------------------------------------------------------------------
class StoryboardModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``storyboards`` table."""

    __tablename__ = "storyboards"
    __table_args__ = (
        Index("ix_storyboards_project_id", "project_id"),
        Index("ix_storyboards_version", "version"),
        Index("ix_storyboards_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    scene_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    estimated_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    style: Mapped[str] = mapped_column(String(50), default="mixed", server_default="mixed")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False)
    narrative_structure: Mapped[str] = mapped_column(Text, default="", server_default="")
    pacing_notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    package_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="storyboards")
    scenes: Mapped[list["SceneModel"]] = relationship(
        "SceneModel", back_populates="storyboard", lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------
class SceneModel(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """ORM model for the ``scenes`` table."""

    __tablename__ = "scenes"
    __table_args__ = (
        Index("ix_scenes_project_id", "project_id"),
        Index("ix_scenes_storyboard_id", "storyboard_id"),
        Index("ix_scenes_scene_number", "scene_number"),
        Index("ix_scenes_generation_status", "generation_status"),
        Index("ix_scenes_review_status", "review_status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    storyboard_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storyboards.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="", server_default="")
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    narration: Mapped[str] = mapped_column(Text, default="", server_default="")
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    emotion: Mapped[str] = mapped_column(String(50), default="", server_default="")
    visual_type: Mapped[str] = mapped_column(String(30), default="image", server_default="image")
    camera_angle: Mapped[str | None] = mapped_column(String(30), nullable=True)
    camera_motion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    lens: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lighting: Mapped[str | None] = mapped_column(String(200), nullable=True)
    composition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_timing: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON-encoded dict
    background_music: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sound_effects: Mapped[str] = mapped_column(Text, default="", server_default="")  # JSON-encoded list
    generation_status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="scenes")
    storyboard: Mapped["StoryboardModel"] = relationship("StoryboardModel", back_populates="scenes")
    assets: Mapped[list["AssetModel"]] = relationship(
        "AssetModel", back_populates="scene", lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Assets (single-table inheritance)
# ---------------------------------------------------------------------------
class AssetModel(Base, UUIDPrimaryKeyMixin):
    """ORM base model for the ``assets`` table (single-table inheritance).

    The ``asset_type`` column acts as the discriminator for the
    inheritance hierarchy. All asset-specific columns are nullable
    in the base table and populated only by the relevant subclass.
    """

    __tablename__ = "assets"
    __mapper_args__ = {"polymorphic_on": "asset_type"}
    __table_args__ = (
        Index("ix_assets_project_id", "project_id"),
        Index("ix_assets_scene_id", "scene_id"),
        Index("ix_assets_asset_type", "asset_type"),
        Index("ix_assets_generation_status", "generation_status"),
        Index("ix_assets_created_at", "created_at"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="", server_default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="", server_default="")
    generation_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    generation_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    generation_status: Mapped[str] = mapped_column(String(30), default="planned", server_default="planned", nullable=False)
    storage_type: Mapped[str] = mapped_column(String(20), default="local", server_default="local")
    storage_ref: Mapped[str] = mapped_column(Text, default="", server_default="")
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}", server_default="{}")  # JSON-encoded dict
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- Asset-specific columns (nullable, used by subclasses) ---
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    voice_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    speaking_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    scene: Mapped["SceneModel"] = relationship("SceneModel", back_populates="assets")


class ImageAssetModel(AssetModel):
    """ORM model for image assets (single-table inheritance)."""

    __mapper_args__ = {"polymorphic_identity": "image"}


class VideoAssetModel(AssetModel):
    """ORM model for video assets (single-table inheritance)."""

    __mapper_args__ = {"polymorphic_identity": "video"}


class VoiceAssetModel(AssetModel):
    """ORM model for voice assets (single-table inheritance)."""

    __mapper_args__ = {"polymorphic_identity": "voice"}


class SubtitleAssetModel(AssetModel):
    """ORM model for subtitle assets (single-table inheritance)."""

    __mapper_args__ = {"polymorphic_identity": "subtitle"}


class ThumbnailAssetModel(AssetModel):
    """ORM model for thumbnail assets (single-table inheritance)."""

    __mapper_args__ = {"polymorphic_identity": "thumbnail"}


# ---------------------------------------------------------------------------
# Generation Jobs
# ---------------------------------------------------------------------------
class GenerationJobModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``generation_jobs`` table."""

    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index("ix_generation_jobs_project_id", "project_id"),
        Index("ix_generation_jobs_workflow_id", "workflow_id"),
        Index("ix_generation_jobs_scene_id", "scene_id"),
        Index("ix_generation_jobs_job_type", "job_type"),
        Index("ix_generation_jobs_status", "status"),
        Index("ix_generation_jobs_priority", "priority"),
        Index("ix_generation_jobs_queued_at", "queued_at"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal", nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON-encoded dict
    result: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON-encoded dict
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default="3", nullable=False)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="jobs")


# ---------------------------------------------------------------------------
# Prompt Executions
# ---------------------------------------------------------------------------
class PromptExecutionModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``prompt_executions`` table."""

    __tablename__ = "prompt_executions"
    __table_args__ = (
        Index("ix_prompt_executions_project_id", "project_id"),
        Index("ix_prompt_executions_workflow_id", "workflow_id"),
        Index("ix_prompt_executions_scene_id", "scene_id"),
        Index("ix_prompt_executions_provider", "provider"),
        Index("ix_prompt_executions_status", "status"),
        Index("ix_prompt_executions_created_at", "created_at"),
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    agent_type: Mapped[str] = mapped_column(String(50), default="", server_default="")
    prompt_template: Mapped[str] = mapped_column(String(200), default="", server_default="")
    prompt_variables: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON-encoded dict
    rendered_prompt: Mapped[str] = mapped_column(Text, default="", server_default="")
    provider: Mapped[str] = mapped_column(String(50), default="", server_default="")
    model: Mapped[str] = mapped_column(String(100), default="", server_default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.7, server_default="0.7")
    response: Mapped[str] = mapped_column(Text, default="", server_default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------
class CostRecordModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``cost_records`` table."""

    __tablename__ = "cost_records"
    __table_args__ = (
        Index("ix_cost_records_user_id", "user_id"),
        Index("ix_cost_records_project_id", "project_id"),
        Index("ix_cost_records_workflow_id", "workflow_id"),
        Index("ix_cost_records_job_id", "job_id"),
        Index("ix_cost_records_scene_id", "scene_id"),
        Index("ix_cost_records_asset_id", "asset_id"),
        Index("ix_cost_records_provider", "provider"),
        Index("ix_cost_records_cost_category", "cost_category"),
        Index("ix_cost_records_period", "period"),
        Index("ix_cost_records_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="", server_default="")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0", nullable=False)
    cost_category: Mapped[str] = mapped_column(String(30), default="llm", server_default="llm")
    period: Mapped[str] = mapped_column(String(20), default="daily", server_default="daily")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}", server_default="{}")  # JSON-encoded dict
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Token Tracking
# ---------------------------------------------------------------------------
class TokenUsageRecordModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for the ``token_usage_records`` table."""

    __tablename__ = "token_usage_records"
    __table_args__ = (
        Index("ix_token_usage_user_id", "user_id"),
        Index("ix_token_usage_project_id", "project_id"),
        Index("ix_token_usage_workflow_id", "workflow_id"),
        Index("ix_token_usage_provider", "provider"),
        Index("ix_token_usage_agent_type", "agent_type"),
        Index("ix_token_usage_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="", server_default="")
    agent_type: Mapped[str] = mapped_column(String(50), default="", server_default="")
    model: Mapped[str] = mapped_column(String(100), default="", server_default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}", server_default="{}")  # JSON-encoded dict
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
