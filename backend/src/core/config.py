"""Application configuration — strongly-typed settings via Pydantic Settings V2.

All configuration is loaded from environment variables (or ``.env`` file).
Settings are grouped by domain concern into nested models for clarity and
type safety.  The single ``get_settings()`` function provides a cached
singleton, ensuring the environment is parsed only once per process.

Usage::

    from src.core.config import get_settings

    settings = get_settings()
    print(settings.database.url)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Sub-configurations
# ---------------------------------------------------------------------------
class DatabaseSettings(BaseSettings):
    """PostgreSQL connection and connection-pool tuning."""

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    user: str = Field(default="aivideo", alias="POSTGRES_USER")
    password: str = Field(default="aivideo_secret", alias="POSTGRES_PASSWORD")
    name: str = Field(default="aivideo_studio", alias="POSTGRES_DB")
    pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")
    url_override: str = Field(default="", alias="DATABASE_URL")

    @staticmethod
    def _normalize_override(url: str, *, sync: bool) -> str:
        """Normalise a cloud-injected ``DATABASE_URL``.

        Providers like Railway/Heroku inject ``postgres://`` or
        ``postgresql://`` without a driver suffix.  The async engine needs
        ``+asyncpg``; Alembic's sync engine needs ``+psycopg2``.
        """
        url = url.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if sync:
            if url.startswith("postgresql://"):
                return "postgresql+psycopg2://" + url[len("postgresql://"):]
            return url.replace("asyncpg", "psycopg2").replace("aiosqlite", "psycopg2")
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> str:
        if self.url_override:
            return self._normalize_override(self.url_override, sync=False)
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sync_url(self) -> str:
        """Synchronous URL used by Alembic migrations."""
        if self.url_override:
            return self._normalize_override(self.url_override, sync=True)
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis connection for caching and Celery broker."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    use_tls: bool = Field(default=False, alias="REDIS_USE_TLS")

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> str:
        scheme = "rediss" if self.use_tls else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseSettings):
    """Celery worker and beat configuration."""

    broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )
    task_soft_time_limit: int = Field(default=3600, alias="CELERY_TASK_SOFT_TIME_LIMIT")
    task_time_limit: int = Field(default=3900, alias="CELERY_TASK_TIME_LIMIT")
    worker_concurrency: int = Field(default=4, alias="CELERY_WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(
        default=1, alias="CELERY_WORKER_PREFETCH_MULTIPLIER"
    )


class JWTSettings(BaseSettings):
    """JWT authentication parameters."""

    secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )


class GeminiSettings(BaseSettings):
    """Google Gemini LLM provider configuration."""

    api_key: str = Field(default="", alias="GEMINI_API_KEY")
    pro_model: str = Field(default="gemini-2.5-pro", alias="GEMINI_PRO_MODEL")
    flash_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_FLASH_MODEL")
    max_retries: int = Field(default=3, alias="GEMINI_MAX_RETRIES")
    request_timeout: int = Field(default=120, alias="GEMINI_REQUEST_TIMEOUT")


class VeoSettings(BaseSettings):
    """Google Veo video generation provider configuration."""

    enabled: bool = Field(default=False, alias="USE_VEO")
    api_key: str = Field(default="", alias="GOOGLE_VEO_API_KEY")
    model: str = Field(default="veo-3.1-fast-generate-preview", alias="GOOGLE_VEO_MODEL")
    max_retries: int = Field(default=2, alias="GOOGLE_VEO_MAX_RETRIES")
    request_timeout: int = Field(default=600, alias="GOOGLE_VEO_REQUEST_TIMEOUT")


class KlingSettings(BaseSettings):
    """Kling video generation provider configuration (served via fal.ai)."""

    enabled: bool = Field(default=False, alias="USE_KLING")
    api_key: str = Field(default="", alias="FAL_KEY")
    endpoint: str = Field(
        default="fal-ai/kling-video/v3/standard", alias="KLING_ENDPOINT"
    )
    model: str = Field(default="kling-v3-standard", alias="KLING_MODEL")
    max_retries: int = Field(default=2, alias="KLING_MAX_RETRIES")
    request_timeout: int = Field(default=600, alias="KLING_REQUEST_TIMEOUT")
    generate_audio: bool = Field(default=True, alias="KLING_GENERATE_AUDIO")


class ImagenSettings(BaseSettings):
    """Google Imagen image generation provider configuration."""

    api_key: str = Field(default="", alias="GOOGLE_IMAGEN_API_KEY")
    model: str = Field(default="gemini-2.5-flash-image", alias="GOOGLE_IMAGEN_MODEL")
    max_retries: int = Field(default=3, alias="GOOGLE_IMAGEN_MAX_RETRIES")
    request_timeout: int = Field(default=120, alias="GOOGLE_IMAGEN_REQUEST_TIMEOUT")


class StockSettings(BaseSettings):
    """Free stock image / video provider API keys (Pexels, Pixabay, Unsplash)."""

    pexels_api_key: str = Field(default="", alias="STOCK_PEXELS_API_KEY")
    pixabay_api_key: str = Field(default="", alias="STOCK_PIXABAY_API_KEY")
    unsplash_api_key: str = Field(default="", alias="STOCK_UNSPLASH_API_KEY")
    max_results: int = Field(default=5, alias="STOCK_MAX_RESULTS")
    request_timeout: int = Field(default=20, alias="STOCK_REQUEST_TIMEOUT")


class TTSSettings(BaseSettings):
    """Google Text-to-Speech provider configuration."""

    api_key: str = Field(default="", alias="GOOGLE_TTS_API_KEY")
    language: str = Field(default="en-US", alias="GOOGLE_TTS_LANGUAGE")
    voice: str = Field(default="en-US-Studio-Q", alias="GOOGLE_TTS_VOICE")
    max_retries: int = Field(default=3, alias="GOOGLE_TTS_MAX_RETRIES")
    request_timeout: int = Field(default=60, alias="GOOGLE_TTS_REQUEST_TIMEOUT")


class YouTubeSettings(BaseSettings):
    """YouTube Data API configuration for publishing."""

    client_id: str = Field(default="", alias="YOUTUBE_CLIENT_ID")
    client_secret: str = Field(default="", alias="YOUTUBE_CLIENT_SECRET")
    redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/publish/oauth/callback",
        alias="YOUTUBE_REDIRECT_URI",
    )
    api_key: str = Field(default="", alias="YOUTUBE_API_KEY")


class StorageSettings(BaseSettings):
    """Asset storage backend configuration."""

    type: Literal["local", "gcs", "s3"] = Field(default="local", alias="STORAGE_TYPE")
    local_path: str = Field(default="/app/storage", alias="STORAGE_LOCAL_PATH")
    gcs_bucket: str = Field(default="", alias="STORAGE_GCS_BUCKET")
    gcs_project_id: str = Field(default="", alias="STORAGE_GCS_PROJECT_ID")
    gcs_credentials_path: str = Field(default="", alias="STORAGE_GCS_CREDENTIALS_PATH")
    s3_bucket: str = Field(default="", alias="STORAGE_S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="STORAGE_S3_REGION")
    s3_access_key: str = Field(default="", alias="STORAGE_S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="STORAGE_S3_SECRET_KEY")


class FFmpegSettings(BaseSettings):
    """FFmpeg rendering configuration."""

    path: str = Field(default="ffmpeg", alias="FFMPEG_PATH")
    ffprobe_path: str = Field(default="ffprobe", alias="FFPROBE_PATH")
    threads: int = Field(default=4, alias="FFMPEG_THREADS")
    preset: str = Field(default="medium", alias="FFMPEG_PRESET")
    crf: int = Field(default=23, alias="FFMPEG_CRF")


class CostSettings(BaseSettings):
    """Per-unit cost estimates (USD) for budget tracking."""

    gemini_pro_input_per_1k: float = Field(
        default=0.00125, alias="COST_GEMINI_PRO_INPUT_PER_1K"
    )
    gemini_pro_output_per_1k: float = Field(
        default=0.005, alias="COST_GEMINI_PRO_OUTPUT_PER_1K"
    )
    gemini_flash_input_per_1k: float = Field(
        default=0.0003, alias="COST_GEMINI_FLASH_INPUT_PER_1K"
    )
    gemini_flash_output_per_1k: float = Field(
        default=0.0015, alias="COST_GEMINI_FLASH_OUTPUT_PER_1K"
    )
    veo_per_second: float = Field(default=0.10, alias="COST_VEO_PER_SECOND")
    kling_per_second: float = Field(default=0.126, alias="COST_KLING_PER_SECOND")
    imagen_per_image: float = Field(default=0.04, alias="COST_IMAGEN_PER_IMAGE")
    tts_per_1k_chars: float = Field(default=0.016, alias="COST_TTS_PER_1K_CHARS")


class LangfuseSettings(BaseSettings):
    """Langfuse LLM tracing configuration."""

    enabled: bool = Field(default=False, alias="LANGFUSE_ENABLED")
    host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")
    public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    release: str = Field(default="", alias="LANGFUSE_RELEASE")


class CORSSettings(BaseSettings):
    """Cross-origin resource sharing configuration."""

    origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.origins_raw.split(",") if o.strip()]


class RateLimitSettings(BaseSettings):
    """API rate limiting configuration."""

    enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    ai_endpoints: str = Field(default="10/minute", alias="RATE_LIMIT_AI_ENDPOINTS")


class LokiSettings(BaseSettings):
    """Grafana Cloud Loki log shipping configuration.

    When ``LOKI_ENABLED`` is true and URL/user/token are set, every log
    line is buffered and pushed to Grafana Cloud Loki's HTTP API.
    """

    enabled: bool = Field(default=False, alias="LOKI_ENABLED")
    url: str = Field(default="", alias="LOKI_URL")
    user: str = Field(default="", alias="LOKI_USER")
    api_key: str = Field(default="", alias="LOKI_API_KEY")
    push_interval_seconds: float = Field(
        default=5.0, alias="LOKI_PUSH_INTERVAL_SECONDS"
    )
    batch_size: int = Field(default=500, alias="LOKI_BATCH_SIZE")


# ---------------------------------------------------------------------------
# Root settings
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Root application settings — aggregates all sub-configurations.

    Environment variables are read from a ``.env`` file (if present) and
    from the process environment.  Nested settings are populated via
    their respective aliases.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="AI Video Studio", alias="APP_NAME")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=True, alias="APP_DEBUG")
    host: str = Field(default="0.0.0.0", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", alias="APP_API_PREFIX")

    # Aggregated sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    veo: VeoSettings = Field(default_factory=VeoSettings)
    kling: KlingSettings = Field(default_factory=KlingSettings)
    imagen: ImagenSettings = Field(default_factory=ImagenSettings)
    stock: StockSettings = Field(default_factory=StockSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    ffmpeg: FFmpegSettings = Field(default_factory=FFmpegSettings)
    cost: CostSettings = Field(default_factory=CostSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    loki: LokiSettings = Field(default_factory=LokiSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` singleton.

    The cache ensures the environment is parsed only once per process.
    Call ``get_settings.cache_clear()`` in tests that need to override
    environment variables.
    """
    return Settings()
