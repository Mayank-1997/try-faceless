"""Generic response models for AI operations, API endpoints, and job results.

These Pydantic V2 models provide a consistent envelope for all
operations across the platform.  Every service, gateway, and agent
returns one of these models — never raw dictionaries or untyped
objects.

Design principles:
- **Success/Failure separation**: explicit types prevent silent errors.
- **Progress reporting**: long-running operations report progress.
- **Streaming support**: async iterators yield ``StreamingChunk`` models.
- **Cost & token tracking**: every result includes usage metadata.
- **Correlation**: every result carries a correlation ID for tracing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


T = TypeVar("T")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_correlation_id() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Base response envelope
# ---------------------------------------------------------------------------
class BaseResponse(BaseModel):
    """Base model for all responses — carries correlation metadata."""

    correlation_id: str = Field(default_factory=_new_correlation_id)
    timestamp: datetime = Field(default_factory=_utc_now)

    model_config = {"frozen": False}


# ---------------------------------------------------------------------------
# Success / Failure
# ---------------------------------------------------------------------------
class SuccessResponse(BaseResponse, Generic[T]):
    """Standard success response carrying a typed payload."""

    success: bool = True
    data: T
    message: str | None = None


class FailureResponse(BaseResponse):
    """Standard failure response carrying error details."""

    success: bool = False
    error_code: str
    error_message: str
    error_details: dict[str, Any] | None = None
    retryable: bool = False


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
class ProgressResponse(BaseResponse):
    """Progress update for a long-running operation.

    Emitted by job runners, gateways, and agents during execution.
    """

    job_id: str | None = None
    agent_type: str | None = None
    step: str
    current: int
    total: int
    percentage: float = Field(ge=0.0, le=100.0)
    message: str | None = None
    estimated_remaining_seconds: float | None = None

    @property
    def is_complete(self) -> bool:
        return self.current >= self.total


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------
class StreamingChunk(BaseResponse):
    """A single chunk in a streaming response.

    Used by the LLM Gateway's ``stream()`` method and any other
    streaming operation.
    """

    chunk: str
    chunk_index: int = 0
    is_final: bool = False
    input_tokens_so_far: int = 0
    output_tokens_so_far: int = 0


# ---------------------------------------------------------------------------
# Generation Result
# ---------------------------------------------------------------------------
class GenerationResult(BaseResponse, Generic[T]):
    """Result of any AI generation operation (text, image, video, voice).

    Includes cost and token usage for tracking and observability.
    """

    success: bool = True
    provider: str
    model: str
    output: T
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    quality_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_quality_score(self) -> bool:
        return self.quality_score is not None


# ---------------------------------------------------------------------------
# Retry Result
# ---------------------------------------------------------------------------
class RetryResult(BaseResponse):
    """Result of a retry attempt for a failed operation.

    Tracks the attempt number, whether the retry succeeded, and the
    error that caused the previous attempt to fail.
    """

    attempt: int
    max_attempts: int
    succeeded: bool
    error_code: str | None = None
    error_message: str | None = None
    backoff_seconds: float = 0.0
    next_attempt_at: datetime | None = None

    @property
    def has_attempts_remaining(self) -> bool:
        return self.attempt < self.max_attempts

    @property
    def is_final_attempt(self) -> bool:
        return self.attempt >= self.max_attempts


# ---------------------------------------------------------------------------
# Health Check Result
# ---------------------------------------------------------------------------
class HealthCheckResult(BaseResponse):
    """Result of a provider or service health check."""

    service: str
    healthy: bool
    latency_ms: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Paginated Response
# ---------------------------------------------------------------------------
class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated list response with metadata."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 0

    model_config = {"arbitrary_types_allowed": True}

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1
