"""Standard AI response model for all agent AI calls.

Every agent that calls an LLM or other AI provider receives an
``AIResponse`` — a strongly-typed envelope containing the raw
response, structured data, cost, tokens, latency, and metadata.

This model wraps the existing ``GenerationResult`` from the gateway
layer and adds agent-specific fields like warnings, errors, and
structured data extraction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    """Standard response from any AI call made by an agent.

    Attributes:
        success: Whether the AI call succeeded.
        response: The raw text response from the provider.
        structured_data: Parsed structured data (JSON), if applicable.
        cost_usd: Cost of this AI call in USD.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        total_tokens: Total tokens (input + output).
        latency_ms: Response latency in milliseconds.
        provider: The AI provider used (e.g. "gemini", "openai").
        model: The specific model used (e.g. "gemini-2.0-flash").
        warnings: Non-fatal warnings encountered during execution.
        errors: Non-fatal errors encountered during execution.
        metadata: Additional provider-specific metadata.
        correlation_id: Correlation ID for tracing.
        timestamp: When the response was received.
    """

    success: bool = True
    response: str = ""
    structured_data: dict[str, Any] | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    provider: str = ""
    model: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True}

    @property
    def has_structured_data(self) -> bool:
        """Check if structured data was extracted."""
        return self.structured_data is not None

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any non-fatal errors."""
        return len(self.errors) > 0

    @classmethod
    def from_generation_result(
        cls,
        result: Any,
        *,
        structured_data: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> AIResponse:
        """Create an ``AIResponse`` from a ``GenerationResult``.

        Args:
            result: The ``GenerationResult`` from the LLM gateway.
            structured_data: Optional parsed structured data.
            warnings: Optional list of warnings.

        Returns:
            An ``AIResponse`` populated from the generation result.
        """
        return cls(
            success=result.success,
            response=result.output if hasattr(result, "output") else str(result),
            structured_data=structured_data,
            cost_usd=getattr(result, "cost_usd", 0.0),
            input_tokens=getattr(result, "input_tokens", 0),
            output_tokens=getattr(result, "output_tokens", 0),
            total_tokens=getattr(result, "total_tokens", 0),
            latency_ms=getattr(result, "latency_ms", 0),
            provider=getattr(result, "provider", ""),
            model=getattr(result, "model", ""),
            warnings=warnings or [],
            metadata=getattr(result, "metadata", {}),
            correlation_id=getattr(result, "correlation_id", None),
        )

    @classmethod
    def failure(
        cls,
        error: str,
        *,
        provider: str = "",
        model: str = "",
        correlation_id: str | None = None,
    ) -> AIResponse:
        """Create a failure ``AIResponse``.

        Args:
            error: The error message.
            provider: The provider that was attempted.
            model: The model that was attempted.
            correlation_id: Optional correlation ID.

        Returns:
            An ``AIResponse`` with ``success=False``.
        """
        return cls(
            success=False,
            errors=[error],
            provider=provider,
            model=model,
            correlation_id=correlation_id,
        )
