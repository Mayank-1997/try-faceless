"""Publishing & Distribution Platform schemas — all Pydantic v2 models.

Defines every data structure used by the publishing platform:
- Publishing metadata (title, description, tags, category, SEO)
- Publishing plan and tasks
- Publisher configuration and authentication
- Publishing report and metrics
- Scheduling configuration
- Queue and progress tracking
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
class PublishingPlatform(str, Enum):
    """Supported publishing platforms."""

    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    MEDIUM = "medium"
    WORDPRESS = "wordpress"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    PODCAST = "podcast"
    CUSTOM = "custom"


class PublishingMode(str, Enum):
    """Publishing execution modes."""

    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    DRAFT = "draft"
    MANUAL_APPROVAL = "manual_approval"
    MULTI_PLATFORM = "multi_platform"


class PublishingJobStatus(str, Enum):
    """Status of a publishing job."""

    QUEUED = "queued"
    AUTHENTICATING = "authenticating"
    VALIDATING = "validating"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    THUMBNAIL_UPLOADING = "thumbnail_uploading"
    METADATA_UPDATING = "metadata_updating"
    PUBLISHING = "publishing"
    SCHEDULED = "scheduled"
    DRAFT_SAVED = "draft_saved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class PublishingPriority(int, Enum):
    """Priority levels for publishing queue."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    BACKGROUND = 20


class AuthMethod(str, Enum):
    """Authentication methods for publishers."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    REFRESH_TOKEN = "refresh_token"
    SERVICE_ACCOUNT = "service_account"
    BASIC = "basic"
    CUSTOM = "custom"


class YouTubeCategory(str, Enum):
    """YouTube video categories."""

    FILM_ANIMATION = "1"
    AUTOS_VEHICLES = "2"
    MUSIC = "10"
    PETS_ANIMALS = "15"
    SPORTS = "17"
    TRAVEL_EVENTS = "19"
    GAMING = "20"
    PEOPLE_BLOGS = "22"
    COMEDY = "23"
    ENTERTAINMENT = "24"
    NEWS_POLITICS = "25"
    HOWTO_STYLE = "26"
    EDUCATION = "27"
    SCIENCE_TECH = "28"
    NONPROFIT_ACTIVISM = "29"


class YouTubeLicense(str, Enum):
    """YouTube video licenses."""

    YOUTUBE = "youtube"
    CREATIVE_COMMON = "creativeCommon"


class ThumbnailFormat(str, Enum):
    """Supported thumbnail formats."""

    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    WEBP = "webp"


class RetryStrategy(str, Enum):
    """Retry strategies for failed publishing."""

    NONE = "none"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


class FailoverStrategy(str, Enum):
    """Failover strategies for multi-platform publishing."""

    NONE = "none"
    SKIP_FAILED = "skip_failed"
    RETRY_ON_ALTERNATIVE = "retry_on_alternative"
    ABORT_ALL = "abort_all"


# ---------------------------------------------------------------------------
# Publishing Metadata
# ---------------------------------------------------------------------------
class PublishingMetadata(BaseModel):
    """Metadata for publishing a video to a platform.

    Contains all the information needed to publish a video,
    including title, description, tags, category, and SEO data.
    """

    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    category: str = ""
    hashtags: list[str] = Field(default_factory=list)
    language: str = "en"
    seo_metadata: dict[str, Any] = Field(default_factory=dict)
    platform_metadata: dict[str, Any] = Field(default_factory=dict)
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    # YouTube-specific
    privacy_status: str = "private"
    license: str = "youtube"
    made_for_kids: bool = False
    self_declared_made_for_kids: bool | None = None
    embeddable: bool = True
    public_stats_viewable: bool = True
    notify_subscribers: bool = True
    playlist_id: str | None = None
    recording_date: datetime | None = None
    recording_location: str | None = None

    @property
    def title_length(self) -> int:
        """Title character count."""
        return len(self.title)

    @property
    def description_length(self) -> int:
        """Description character count."""
        return len(self.description)

    @property
    def tag_count(self) -> int:
        """Number of tags."""
        return len(self.tags)


# ---------------------------------------------------------------------------
# Platform Configuration
# ---------------------------------------------------------------------------
class PlatformConfig(BaseModel):
    """Configuration for a publishing platform."""

    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    enabled: bool = True
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    access_token: str = ""
    token_expiry: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    redirect_uri: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Authentication Credential
# ---------------------------------------------------------------------------
class AuthCredential(BaseModel):
    """Stored authentication credential for a publisher."""

    id: UUID = Field(default_factory=uuid4)
    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    auth_method: AuthMethod = AuthMethod.OAUTH2
    access_token: str = ""
    refresh_token: str = ""
    token_expiry: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the access token has expired."""
        if self.token_expiry is None:
            return False
        return datetime.now(timezone.utc) >= self.token_expiry

    @property
    def is_valid(self) -> bool:
        """Check if the credential has a non-empty access token."""
        return bool(self.access_token) and not self.is_expired


# ---------------------------------------------------------------------------
# Thumbnail Configuration
# ---------------------------------------------------------------------------
class ThumbnailSpec(BaseModel):
    """Thumbnail specification for a platform."""

    format: ThumbnailFormat = ThumbnailFormat.JPG
    width: int = 1280
    height: int = 720
    max_size_bytes: int = 2 * 1024 * 1024  # 2MB YouTube limit
    quality: int = 90

    @property
    def aspect_ratio(self) -> str:
        """Thumbnail aspect ratio."""
        return f"{self.width}:{self.height}"


# ---------------------------------------------------------------------------
# Publishing Task
# ---------------------------------------------------------------------------
class PublishingTask(BaseModel):
    """A single publishing task for one platform."""

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID = Field(default_factory=uuid4)
    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    mode: PublishingMode = PublishingMode.IMMEDIATE
    metadata: PublishingMetadata = Field(default_factory=PublishingMetadata)
    video_path: str = ""
    thumbnail_path: str = ""
    scheduled_at: datetime | None = None
    status: PublishingJobStatus = PublishingJobStatus.QUEUED
    priority: PublishingPriority = PublishingPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    error: str | None = None
    provider_response: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the task is in a terminal state."""
        return self.status in (
            PublishingJobStatus.COMPLETED,
            PublishingJobStatus.FAILED,
            PublishingJobStatus.CANCELLED,
            PublishingJobStatus.DRAFT_SAVED,
        )

    @property
    def execution_time_seconds(self) -> float:
        """Calculate execution time if the task has started."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Publishing Plan
# ---------------------------------------------------------------------------
class PublishingPlan(BaseModel):
    """A plan for publishing a project package to one or more platforms.

    Generated by the PublishingPlanner before publishing begins.
    """

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    project_package_id: UUID = Field(default_factory=uuid4)
    tasks: list[PublishingTask] = Field(default_factory=list)
    mode: PublishingMode = PublishingMode.IMMEDIATE
    failover_strategy: FailoverStrategy = FailoverStrategy.SKIP_FAILED
    estimated_publishing_time: float = 0.0
    platform_count: int = 0
    metadata: PublishingMetadata = Field(default_factory=PublishingMetadata)
    thumbnail_specs: dict[str, ThumbnailSpec] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def task_count(self) -> int:
        """Number of publishing tasks."""
        return len(self.tasks)

    @property
    def platforms(self) -> list[PublishingPlatform]:
        """List of platforms in this plan."""
        return list({t.platform for t in self.tasks})


# ---------------------------------------------------------------------------
# Publishing Report
# ---------------------------------------------------------------------------
class PublishingReport(BaseModel):
    """Report for a completed publishing operation.

    Contains the status, platform, video URL, timing, and any
    warnings or errors for each platform.
    """

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    status: PublishingJobStatus = PublishingJobStatus.COMPLETED
    video_url: str = ""
    video_id: str = ""
    upload_duration_seconds: float = 0.0
    publish_duration_seconds: float = 0.0
    total_duration_seconds: float = 0.0
    provider_response: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    thumbnail_uploaded: bool = False
    metadata_updated: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_successful(self) -> bool:
        """Check if publishing was successful."""
        return self.status == PublishingJobStatus.COMPLETED and not self.errors


# ---------------------------------------------------------------------------
# Publishing Metrics
# ---------------------------------------------------------------------------
class PublishingMetrics(BaseModel):
    """Metrics collected during publishing."""

    upload_speed_mbps: float = 0.0
    upload_bytes: int = 0
    thumbnail_upload_time_seconds: float = 0.0
    metadata_update_time_seconds: float = 0.0
    total_api_calls: int = 0
    failed_api_calls: int = 0
    retry_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Publishing Progress
# ---------------------------------------------------------------------------
class PublishingProgress(BaseModel):
    """Progress tracking for a publishing job."""

    task_id: UUID = Field(default_factory=uuid4)
    status: PublishingJobStatus = PublishingJobStatus.QUEUED
    progress_percentage: float = 0.0
    current_stage: str = ""
    stages_completed: list[str] = Field(default_factory=list)
    upload_progress: float = 0.0  # 0-100 for upload
    estimated_time_remaining: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Publishing Job (Queue entry)
# ---------------------------------------------------------------------------
class PublishingJob(BaseModel):
    """A job in the publishing queue."""

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    status: PublishingJobStatus = PublishingJobStatus.QUEUED
    priority: PublishingPriority = PublishingPriority.NORMAL
    scheduled_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    report: PublishingReport | None = None
    metrics: PublishingMetrics = Field(default_factory=PublishingMetrics)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state."""
        return self.status in (
            PublishingJobStatus.COMPLETED,
            PublishingJobStatus.FAILED,
            PublishingJobStatus.CANCELLED,
            PublishingJobStatus.DRAFT_SAVED,
        )

    @property
    def execution_time_seconds(self) -> float:
        """Calculate execution time."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Schedule Configuration
# ---------------------------------------------------------------------------
class ScheduleConfig(BaseModel):
    """Scheduling configuration for publishing."""

    mode: PublishingMode = PublishingMode.IMMEDIATE
    scheduled_at: datetime | None = None
    timezone: str = "UTC"
    recurring: bool = False
    recurring_cron: str | None = None
    campaign_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_scheduled(self) -> bool:
        """Check if this is a scheduled publish."""
        return self.mode == PublishingMode.SCHEDULED and self.scheduled_at is not None

    @property
    def is_immediate(self) -> bool:
        """Check if this is an immediate publish."""
        return self.mode == PublishingMode.IMMEDIATE


# ---------------------------------------------------------------------------
# Platform Requirements
# ---------------------------------------------------------------------------
class PlatformRequirements(BaseModel):
    """Requirements for a specific platform."""

    platform: PublishingPlatform = PublishingPlatform.YOUTUBE
    max_title_length: int = 100
    max_description_length: int = 5000
    max_tags: int = 500
    max_tag_length: int = 30
    supported_video_formats: list[str] = Field(default_factory=lambda: ["mp4", "mov", "avi", "wmv", "flv"])
    max_video_size_bytes: int = 256 * 1024 * 1024 * 1024  # 256GB YouTube limit
    thumbnail_width: int = 1280
    thumbnail_height: int = 720
    thumbnail_formats: list[str] = Field(default_factory=lambda: ["jpg", "png", "bmp"])
    thumbnail_max_size_bytes: int = 2 * 1024 * 1024  # 2MB
    requires_auth: bool = True
    requires_thumbnail: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Publishing Strategy
# ---------------------------------------------------------------------------
class PublishingStrategy(BaseModel):
    """Publishing strategy configuration."""

    mode: PublishingMode = PublishingMode.IMMEDIATE
    platforms: list[PublishingPlatform] = Field(default_factory=lambda: [PublishingPlatform.YOUTUBE])
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    retry_delay_seconds: float = 60.0
    failover_strategy: FailoverStrategy = FailoverStrategy.SKIP_FAILED
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)
