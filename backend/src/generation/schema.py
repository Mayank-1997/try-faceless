"""Generation Platform schemas — all Pydantic v2 models for the generation subsystem.

This module defines every data structure used by the Generation Platform:
- Generation strategies (economy, balanced, premium, fast, custom)
- Generation jobs and job status
- Provider health metrics
- Budget estimates and enforcement
- Asset manifest (per-scene and project-level)
- Validation results
- Quality evaluation
- Cache keys
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class GenerationMode(str, Enum):
    """Generation strategy modes."""

    ECONOMY = "economy"
    BALANCED = "balanced"
    PREMIUM = "premium"
    FAST = "fast"
    CUSTOM = "custom"


class AssetCategory(str, Enum):
    """Category of media asset to generate."""

    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"


class JobStatus(str, Enum):
    """Status of a generation job."""

    QUEUED = "queued"
    WAITING = "waiting"
    GENERATING = "generating"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(int, Enum):
    """Priority levels for queue ordering (lower = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    BACKGROUND = 20


class ValidationStage(str, Enum):
    """Stages of the validation pipeline."""

    FILE_VALIDATION = "file_validation"
    METADATA_VALIDATION = "metadata_validation"
    RESOLUTION_VALIDATION = "resolution_validation"
    DURATION_VALIDATION = "duration_validation"
    PROMPT_ALIGNMENT = "prompt_alignment"
    QUALITY_EVALUATION = "quality_evaluation"
    DUPLICATE_DETECTION = "duplicate_detection"
    STORAGE_VALIDATION = "storage_validation"
    CONTENT_SAFETY = "content_safety"


# ---------------------------------------------------------------------------
# Generation Strategy
# ---------------------------------------------------------------------------
class GenerationStrategy(BaseModel):
    """A generation strategy that determines how assets are produced.

    Controls image vs video ratio, provider selection, model selection,
    resolution, retry policy, concurrency, max cost, quality threshold,
    and execution priority.
    """

    mode: GenerationMode = GenerationMode.BALANCED
    image_video_ratio: float = 0.7  # 0.0 = all images, 1.0 = all video
    preferred_providers: dict[str, str] = Field(default_factory=dict)  # category -> provider name
    preferred_models: dict[str, str] = Field(default_factory=dict)  # category -> model name
    resolution: str = "1920x1080"
    max_retries: int = 3
    concurrency: int = 4
    max_cost_usd: float = 10.0
    quality_threshold: float = 0.7
    execution_priority: JobPriority = JobPriority.NORMAL
    enable_caching: bool = True
    enable_fallback: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Generation Request & Job
# ---------------------------------------------------------------------------
class GenerationRequest(BaseModel):
    """A request to generate a single media asset."""

    id: UUID = Field(default_factory=uuid4)
    scene_id: str = ""
    project_id: str = ""
    category: AssetCategory = AssetCategory.IMAGE
    prompt: str = ""
    negative_prompt: str | None = None
    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    duration_seconds: float | None = None
    fps: int | None = None
    seed: int | None = None
    style: str | None = None
    prompt_version: str = "1.0.0"
    voice: str | None = None
    language: str | None = None
    pitch: float | None = None
    speed: float | None = None
    emotion: str | None = None
    ssml: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationJob(BaseModel):
    """A single generation job in the queue."""

    id: UUID = Field(default_factory=uuid4)
    request: GenerationRequest = Field(default_factory=GenerationRequest)
    status: JobStatus = JobStatus.QUEUED
    priority: JobPriority = JobPriority.NORMAL
    provider: str = ""
    model: str = ""
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    dependencies: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def execution_time_seconds(self) -> float:
        """Calculate execution time if the job has started."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Provider Health
# ---------------------------------------------------------------------------
class ProviderHealthMetrics(BaseModel):
    """Health metrics for a single provider."""

    provider: str = ""
    healthy: bool = True
    latency_ms: float = 0.0
    timeout_count: int = 0
    failure_count: int = 0
    success_count: int = 0
    availability: float = 1.0  # 0.0 to 1.0
    average_cost: float = 0.0
    average_quality: float = 0.0
    quota_remaining: int | None = None
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_failure: datetime | None = None
    disabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (0.0 to 1.0)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
class BudgetEstimate(BaseModel):
    """Cost estimate for a generation request."""

    request_id: UUID = Field(default_factory=uuid4)
    provider: str = ""
    model: str = ""
    estimated_cost: float = 0.0
    category: AssetCategory = AssetCategory.IMAGE
    affordable: bool = True
    alternative_provider: str | None = None
    alternative_cost: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BudgetStatus(BaseModel):
    """Current budget status for a project."""

    project_id: str = ""
    total_budget: float = 0.0
    spent: float = 0.0
    remaining: float = 0.0
    per_scene_budget: dict[str, float] = Field(default_factory=dict)
    per_category_spent: dict[str, float] = Field(default_factory=dict)
    exceeded: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class ValidationResult(BaseModel):
    """Result of validating a generated asset."""

    valid: bool = True
    stage: ValidationStage = ValidationStage.FILE_VALIDATION
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Complete validation report for an asset."""

    asset_id: UUID = Field(default_factory=uuid4)
    overall_valid: bool = True
    results: list[ValidationResult] = Field(default_factory=list)
    rejected_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Quality Evaluation
# ---------------------------------------------------------------------------
class QualityResult(BaseModel):
    """Quality evaluation result for a generated asset."""

    asset_id: UUID = Field(default_factory=uuid4)
    visual_quality: float = 0.0
    prompt_alignment: float = 0.0
    voice_quality: float = 0.0
    subtitle_accuracy: float = 0.0
    consistency: float = 0.0
    brand_compliance: float = 0.0
    overall_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Generated Asset
# ---------------------------------------------------------------------------
class GeneratedAsset(BaseModel):
    """A fully generated, validated, and stored asset."""

    id: UUID = Field(default_factory=uuid4)
    job_id: UUID = Field(default_factory=uuid4)
    scene_id: str = ""
    category: AssetCategory = AssetCategory.IMAGE
    provider: str = ""
    model: str = ""
    storage_uri: str = ""
    file_size_bytes: int = 0
    content_hash: str = ""
    checksum: str = ""
    cost_usd: float = 0.0
    quality_score: float = 0.0
    generation_time_seconds: float = 0.0
    validation_report: ValidationReport = Field(default_factory=ValidationReport)
    quality_result: QualityResult = Field(default_factory=QualityResult)
    cached: bool = False
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Asset Manifest
# ---------------------------------------------------------------------------
class SceneAssetManifest(BaseModel):
    """Asset manifest for a single scene.

    Lists all assets needed/generated for one scene.
    """

    scene_id: str = ""
    scene_number: int = 0
    image: GeneratedAsset | None = None
    video: GeneratedAsset | None = None
    voice: GeneratedAsset | None = None
    music: GeneratedAsset | None = None
    subtitles: GeneratedAsset | None = None
    effects: list[GeneratedAsset] = Field(default_factory=list)
    estimated_render_time_seconds: float = 0.0
    estimated_scene_cost: float = 0.0
    dependencies: list[str] = Field(default_factory=list)
    generation_status: JobStatus = JobStatus.QUEUED
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetManifest(BaseModel):
    """Complete asset manifest for an entire project.

    This is the single object that the Rendering Engine (Phase 10)
    consumes.  It contains per-scene manifests and project-level totals.
    """

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    scene_manifests: list[SceneAssetManifest] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_cost: float = 0.0
    total_assets: int = 0
    estimated_rendering_time_seconds: float = 0.0
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if all scene manifests have completed generation."""
        return all(
            sm.generation_status == JobStatus.COMPLETED
            for sm in self.scene_manifests
        )

    @property
    def scene_count(self) -> int:
        """Return the number of scenes."""
        return len(self.scene_manifests)


# ---------------------------------------------------------------------------
# Progress Tracking
# ---------------------------------------------------------------------------
class GenerationProgress(BaseModel):
    """Progress tracking for generation jobs."""

    total_jobs: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    generating: int = 0
    queued: int = 0
    validating: int = 0
    uploading: int = 0
    progress_percentage: float = 0.0
    estimated_time_remaining_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if all jobs are in terminal states."""
        return (self.completed + self.failed + self.cancelled) == self.total_jobs

    def update_percentage(self) -> None:
        """Recalculate progress percentage."""
        if self.total_jobs == 0:
            self.progress_percentage = 0.0
            return
        terminal = self.completed + self.failed + self.cancelled
        self.progress_percentage = (terminal / self.total_jobs) * 100.0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class CacheKey(BaseModel):
    """Cache key for generation deduplication."""

    prompt: str = ""
    provider: str = ""
    model: str = ""
    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    duration_seconds: float | None = None
    seed: int | None = None
    style: str | None = None
    prompt_version: str = "1.0.0"

    def to_hash(self) -> str:
        """Generate a deterministic hash string for this cache key."""
        import hashlib
        key_str = (
            f"{self.prompt}|{self.provider}|{self.model}|"
            f"{self.aspect_ratio}|{self.resolution}|"
            f"{self.duration_seconds}|{self.seed}|"
            f"{self.style}|{self.prompt_version}"
        )
        return hashlib.sha256(key_str.encode()).hexdigest()


class CacheEntry(BaseModel):
    """A cached generation result."""

    key_hash: str = ""
    asset: GeneratedAsset = Field(default_factory=GeneratedAsset)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0
