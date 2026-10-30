"""Application-wide enumerations — typed constants for domain concepts.

All enums inherit from ``str`` to ensure JSON-serialisable values and
native compatibility with SQLAlchemy's ``Enum`` column type.
"""

from __future__ import annotations

from enum import Enum


class AppEnvironment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class UserRole(str, Enum):
    """User authorization roles."""

    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"


class ProjectStatus(str, Enum):
    """Lifecycle status of a video project."""

    DRAFT = "draft"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    PLANNING = "planning"
    GENERATING = "generating"
    RENDERING = "rendering"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectInputType(str, Enum):
    """How the user initiated the project."""

    TOPIC = "topic"
    SCRIPT = "script"


class JobStatus(str, Enum):
    """Background job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(str, Enum):
    """Job queue priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentType(str, Enum):
    """Identifies each autonomous AI agent in the workflow."""

    DIRECTOR = "director"
    TOPIC = "topic"
    RESEARCH = "research"
    STORY_PLANNER = "story_planner"
    SCRIPT_WRITER = "script_writer"
    SCENE_PLANNER = "scene_planner"
    ASSET_DECISION = "asset_decision"
    IMAGE_PROMPT = "image_prompt"
    VIDEO_PROMPT = "video_prompt"
    VOICE = "voice"
    SUBTITLE = "subtitle"
    RENDERING = "rendering"
    THUMBNAIL = "thumbnail"
    SEO = "seo"
    PUBLISHER = "publisher"


class AgentStatus(str, Enum):
    """Runtime status of an individual agent execution."""

    PENDING = "pending"
    INITIALIZED = "initialized"
    RUNNING = "running"
    VALIDATING_INPUT = "validating_input"
    EXECUTING = "executing"
    VALIDATING_OUTPUT = "validating_output"
    SUCCEEDED = "succeeded"
    RETRYING = "retrying"
    FAILED = "failed"
    SKIPPED = "skipped"


class VisualType(str, Enum):
    """The kind of visual content a scene requires."""

    TALKING = "talking"
    ANIMATION = "animation"
    INFOGRAPHIC = "infographic"
    IMAGE = "image"
    VIDEO = "video"
    MIXED = "mixed"
    DIAGRAM = "diagram"
    TIMELINE = "timeline"
    COMPARISON = "comparison"
    MAP = "map"
    SCREENSHOT = "screenshot"
    CODE = "code"
    PRODUCT_DEMO = "product_demo"
    STOCK_IMAGE = "stock_image"
    STOCK_FOOTAGE = "stock_footage"
    AI_IMAGE = "ai_image"
    AI_VIDEO = "ai_video"


class AssetDecision(str, Enum):
    """The Asset Decision Agent's choice for a scene.

    Ordered roughly from cheapest to most expensive.
    """

    SKIP_SCENE = "skip_scene"
    MERGE_SCENE = "merge_scene"
    EXISTING_ASSET = "existing_asset"
    STOCK_ASSET = "stock_asset"
    ANIMATED_IMAGE = "animated_image"
    CAMERA_MOTION = "camera_motion"
    MOTION_GRAPHICS = "motion_graphics"
    AI_IMAGE = "ai_image"
    AI_VIDEO = "ai_video"
    DIAGRAM = "diagram"
    CHART = "chart"
    ICON = "icon"
    SCREENSHOT = "screenshot"
    ANIMATION_ONLY = "animation_only"
    MIXED_ASSETS = "mixed_assets"


class AssetType(str, Enum):
    """Categorisation of generated or fetched assets."""

    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"


class AssetStatus(str, Enum):
    """Lifecycle of an individual asset."""

    PLANNED = "planned"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    REJECTED = "rejected"


class AIProvider(str, Enum):
    """Supported AI service providers."""

    GEMINI = "gemini"
    VEO = "veo"
    IMAGEN = "imagen"
    GOOGLE_TTS = "google_tts"
    EDGE_TTS = "edge_tts"
    STOCK_IMAGE = "stock_image"
    STOCK_VIDEO = "stock_video"
    # Future providers
    OPENAI = "openai"
    CLAUDE = "claude"
    ELEVENLABS = "elevenlabs"
    RUNWAY = "runway"
    FAL = "fal"
    KLING = "kling"
    MINIMAX = "minimax"


class GeminiModel(str, Enum):
    """Available Gemini model identifiers."""

    GEMINI_25_PRO = "gemini-2.5-pro"
    GEMINI_25_FLASH = "gemini-2.5-flash"


class VoiceGender(str, Enum):
    """Voice character gender selection."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class VoiceTone(str, Enum):
    """Narration tone for voice generation."""

    NEUTRAL = "neutral"
    ENTHUSIASTIC = "enthusiastic"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    DRAMATIC = "dramatic"
    EDUCATIONAL = "educational"


class CameraAngle(str, Enum):
    """Camera angle directives for scene planning."""

    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVERHEAD = "overhead"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH = "dutch"
    POV = "pov"


class CameraMotion(str, Enum):
    """Camera movement directives for scene planning."""

    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    ORBIT = "orbit"


class TransitionType(str, Enum):
    """Scene-to-scene transition styles."""

    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    SLIDE = "slide"
    ZOOM = "zoom"


class PublishStatus(str, Enum):
    """YouTube publishing lifecycle."""

    NOT_PUBLISHED = "not_published"
    SCHEDULING = "scheduling"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class PrivacyStatus(str, Enum):
    """YouTube video privacy levels."""

    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class ActivityType(str, Enum):
    """Categorisation of logged activities."""

    USER_ACTION = "user_action"
    AGENT_EXECUTION = "agent_execution"
    JOB_EVENT = "job_event"
    API_CALL = "api_call"
    ERROR = "error"
    SYSTEM = "system"


class LogLevel(str, Enum):
    """Structured log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StorageType(str, Enum):
    """Asset storage backend selection."""

    LOCAL = "local"
    GCS = "gcs"
    S3 = "s3"


# ---------------------------------------------------------------------------
# IAM / Authentication enums
# ---------------------------------------------------------------------------
class UserStatus(str, Enum):
    """Lifecycle status of a user account."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    LOCKED = "locked"


class AuthProvider(str, Enum):
    """Authentication method used to create / access an account."""

    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    # Future providers
    APPLE = "apple"
    LINKEDIN = "linkedin"


class ApiKeyStatus(str, Enum):
    """Lifecycle status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SessionStatus(str, Enum):
    """Lifecycle status of a user session."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TokenType(str, Enum):
    """JWT token type discriminator."""

    ACCESS = "access"
    REFRESH = "refresh"


class AuditAction(str, Enum):
    """Categorisation of auditable security events."""

    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFIED = "email_verified"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    SESSION_REVOKED = "session_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    PROFILE_UPDATED = "profile_updated"


class ThemePreference(str, Enum):
    """User UI theme preference."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class DefaultRoleName(str, Enum):
    """System-defined role names (custom roles use arbitrary names)."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Business Domain enums (Phase 3)
# ---------------------------------------------------------------------------
class ContentType(str, Enum):
    """Supported content types for projects."""

    YOUTUBE_VIDEO = "youtube_video"
    BLOG = "blog"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PODCAST = "podcast"
    DOCUMENTATION = "documentation"
    COURSE = "course"


class VideoStyle(str, Enum):
    """Visual style for video projects."""

    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    EXPLAINER = "explainer"
    TALKING_HEAD = "talking_head"
    ANIMATED = "animated"
    MIXED = "mixed"
    STOCK_FOOTAGE = "stock_footage"
    WHITEBOARD = "whiteboard"


class WorkflowStatus(str, Enum):
    """Lifecycle status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(str, Enum):
    """Named steps in the workflow pipeline."""

    INITIALIZATION = "initialization"
    RESEARCH = "research"
    SCRIPTING = "scripting"
    STORYBOARD = "storyboard"
    SCENE_PLANNING = "scene_planning"
    ASSET_GENERATION = "asset_generation"
    VOICE_GENERATION = "voice_generation"
    SUBTITLE_GENERATION = "subtitle_generation"
    RENDERING = "rendering"
    THUMBNAIL = "thumbnail"
    SEO = "seo"
    # PUBLISHING is temporarily disabled; SEO is the final step
    # PUBLISHING = "publishing"
    COMPLETED = "completed"


class ResearchStatus(str, Enum):
    """Status of a research version."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


class ScriptStatus(str, Enum):
    """Status of a script version."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class StoryboardStatus(str, Enum):
    """Status of a storyboard version."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SceneGenerationStatus(str, Enum):
    """Generation lifecycle of a scene's assets."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    PARTIALLY_GENERATED = "partially_generated"
    FAILED = "failed"
    SKIPPED = "skipped"


class SceneReviewStatus(str, Enum):
    """Human review status of a scene."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class AssetGenerationStatus(str, Enum):
    """Generation lifecycle of an individual asset."""

    PLANNED = "planned"
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    REJECTED = "rejected"
    REGENERATED = "regenerated"


class JobType(str, Enum):
    """Types of background generation jobs."""

    RESEARCH = "research"
    SCRIPT = "script"
    SCENE = "scene"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    SUBTITLE = "subtitle"
    RENDERING = "rendering"
    THUMBNAIL = "thumbnail"
    SEO = "seo"
    PUBLISHING = "publishing"


class CostPeriod(str, Enum):
    """Time period for cost aggregation."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PromptExecutionStatus(str, Enum):
    """Status of a prompt execution."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CACHED = "cached"
