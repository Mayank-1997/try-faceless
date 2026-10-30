"""Prompt execution entity — tracks every AI prompt execution.

Each time a prompt is sent to an AI provider, a PromptExecution record
is created to track the template, variables, rendered prompt, provider,
model, parameters, response, latency, cost, and token usage.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import AIProvider, PromptExecutionStatus


class PromptExecution:
    """A single prompt execution record.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project (optional for system prompts).
        workflow_id: UUID of the workflow that triggered this execution.
        scene_id: UUID of the scene this prompt is for (optional).
        agent_type: The agent that executed the prompt.
        prompt_template: Name or ID of the template used.
        prompt_variables: Variables substituted into the template.
        rendered_prompt: The final rendered prompt sent to the provider.
        provider: AI provider used.
        model: Model identifier used.
        temperature: Sampling temperature.
        response: Raw response from the provider.
        latency_ms: Response latency in milliseconds.
        cost_usd: Cost of this execution in USD.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        cached_tokens: Number of tokens served from cache.
        status: Execution status.
        error_message: Error message if failed.
        created_at: Execution timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID | None = None,
        workflow_id: UUID | None = None,
        scene_id: UUID | None = None,
        agent_type: str = "",
        prompt_template: str = "",
        prompt_variables: dict[str, Any] | None = None,
        rendered_prompt: str = "",
        provider: AIProvider | str = "",
        model: str = "",
        temperature: float = 0.7,
        response: str = "",
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        status: PromptExecutionStatus = PromptExecutionStatus.PENDING,
        error_message: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.scene_id = scene_id
        self.agent_type = agent_type
        self.prompt_template = prompt_template
        self.prompt_variables = prompt_variables or {}
        self.rendered_prompt = rendered_prompt
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.response = response
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens
        self.status = status
        self.error_message = error_message
        self.created_at = created_at or datetime.now(dt_timezone.utc)

    def mark_success(
        self,
        *,
        response: str,
        latency_ms: int,
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> None:
        """Mark the execution as successful with response data."""
        self.response = response
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens
        self.status = PromptExecutionStatus.SUCCESS

    def mark_failed(self, error: str) -> None:
        """Mark the execution as failed."""
        self.status = PromptExecutionStatus.FAILED
        self.error_message = error

    def mark_cached(self) -> None:
        """Mark the execution as served from cache."""
        self.status = PromptExecutionStatus.CACHED

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (input + output)."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "scene_id": str(self.scene_id) if self.scene_id else None,
            "agent_type": self.agent_type,
            "prompt_template": self.prompt_template,
            "prompt_variables": self.prompt_variables,
            "rendered_prompt": self.rendered_prompt,
            "provider": self.provider.value if hasattr(self.provider, "value") else str(self.provider),
            "model": self.model,
            "temperature": self.temperature,
            "response": self.response,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
