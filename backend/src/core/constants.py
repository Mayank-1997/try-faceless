"""Application-wide constants — magic numbers, string literals, and fixed values."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
APP_NAME: str = "AI Video Studio"
APP_VERSION: str = "0.1.0"
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
DEFAULT_OFFSET: int = 0

# ---------------------------------------------------------------------------
# UUID & Timestamps
# ---------------------------------------------------------------------------
UUID_STR_LENGTH: int = 36

# ---------------------------------------------------------------------------
# Job System
# ---------------------------------------------------------------------------
MAX_JOB_RETRIES: int = 3
JOB_RETRY_BACKOFF_BASE: int = 2  # exponential backoff: 2^attempt seconds
JOB_RETRY_BACKOFF_MAX: int = 300  # 5 minutes max backoff
JOB_VISIBILITY_TIMEOUT: int = 3600  # 1 hour

# ---------------------------------------------------------------------------
# AI / LLM
# ---------------------------------------------------------------------------
DEFAULT_TEMPERATURE: float = 0.7
MAX_TOKENS_DEFAULT: int = 8192
TOKEN_USAGE_PRECISION: int = 4
COST_PRECISION: int = 6

# ---------------------------------------------------------------------------
# Video / Rendering
# ---------------------------------------------------------------------------
DEFAULT_FPS: int = 30
DEFAULT_RESOLUTION_WIDTH: int = 1920
DEFAULT_RESOLUTION_HEIGHT: int = 1080
DEFAULT_VIDEO_BITRATE: str = "5M"
DEFAULT_AUDIO_BITRATE: str = "192k"
DEFAULT_AUDIO_SAMPLE_RATE: int = 48000
SUBTITLE_FONT_SIZE: int = 24
SUBTITLE_FONT_COLOR: str = "white"
SUBTITLE_OUTLINE_COLOR: str = "black"
SUBTITLE_OUTLINE_WIDTH: int = 2

# ---------------------------------------------------------------------------
# Voice / TTS
# ---------------------------------------------------------------------------
TTS_CHARS_PER_SECOND: float = 15.0  # average speaking rate for cost estimation

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
ALLOWED_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")
ALLOWED_VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".webm", ".mov")
ALLOWED_AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".aac", ".ogg")
MAX_UPLOAD_SIZE_MB: int = 500

# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
WORKFLOW_TIMEOUT_SECONDS: int = 7200  # 2 hours max for full pipeline
WORKFLOW_CHECKPOINT_INTERVAL: int = 5  # checkpoint state every N steps
PARALLEL_BRANCH_TIMEOUT: int = 1800  # 30 min for parallel generation

# ---------------------------------------------------------------------------
# Quality Scoring
# ---------------------------------------------------------------------------
MIN_QUALITY_SCORE: float = 0.0
MAX_QUALITY_SCORE: float = 1.0
MIN_ACCEPTABLE_QUALITY: float = 0.7
