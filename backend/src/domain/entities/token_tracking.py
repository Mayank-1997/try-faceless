"""Token tracking entity — granular token usage records.

Token usage is tracked per user, project, provider, and agent.
Each record captures input, output, and cached token counts.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import AIProvider


class TokenUsageRecord:
    """A single token usage tracking record.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the user who consumed the tokens.
        project_id: UUID of the project.
        workflow_id: UUID of the workflow (optional).
        provider: AI provider that processed the tokens.
        agent_type: The agent that triggered the usage.
        model: Model identifier used.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        cached_tokens: Number of tokens served from cache.
        metadata: Additional usage metadata.
        created_at: Record creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        provider: AIProvider | str = "",
        agent_type: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.provider = provider
        self.agent_type = agent_type
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(dt_timezone.utc)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (input + output)."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "provider": self.provider.value if hasattr(self.provider, "value") else str(self.provider),
            "agent_type": self.agent_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
