"""Token Tracker — centralised tracking of LLM token usage.

Tracks token usage at multiple granularities:
- Per agent
- Per project
- Per user
- Per provider/model

Distinguishes between input tokens, output tokens, and cached tokens.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.core.enums import AIProvider, AgentType
from src.core.logging import get_logger


class TokenEntry(BaseModel):
    """A single token usage tracking entry."""

    agent_type: AgentType
    provider: AIProvider
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    project_id: str | None = None
    user_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cached_tokens


class TokenSummary(BaseModel):
    """Aggregated token usage summary."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_tokens: int = 0
    entry_count: int = 0
    by_agent: dict[str, int] = Field(default_factory=dict)
    by_provider: dict[str, int] = Field(default_factory=dict)


class TokenTracker:
    """Centralised token usage tracking service.

    Accumulates token usage in memory.  In production, entries are
    periodically persisted to the ``api_usage`` table.
    """

    def __init__(self, config: Any = None) -> None:
        """Create the token tracker.

        Args:
            config: The application configuration service (optional,
                not currently used but reserved for future features
                like token budgets).
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._entries: list[TokenEntry] = []
        self._project_totals: dict[str, int] = defaultdict(int)
        self._user_totals: dict[str, int] = defaultdict(int)
        self._agent_totals: dict[str, int] = defaultdict(int)
        self._provider_totals: dict[str, int] = defaultdict(int)

    def record(self, entry: TokenEntry) -> None:
        """Record a token usage entry.

        Args:
            entry: The token entry to record.
        """
        self._entries.append(entry)

        total = entry.total_tokens
        if entry.project_id:
            self._project_totals[entry.project_id] += total
        if entry.user_id:
            self._user_totals[entry.user_id] += total
        self._agent_totals[entry.agent_type.value] += total
        self._provider_totals[entry.provider.value] += total

        self._logger.info(
            "tokens_recorded",
            agent=entry.agent_type.value,
            provider=entry.provider.value,
            input_tokens=entry.input_tokens,
            output_tokens=entry.output_tokens,
            cached_tokens=entry.cached_tokens,
            total_tokens=total,
        )

    def get_project_tokens(self, project_id: str) -> int:
        """Get the total token count for a project."""
        return self._project_totals.get(project_id, 0)

    def get_user_tokens(self, user_id: str) -> int:
        """Get the total token count for a user."""
        return self._user_totals.get(user_id, 0)

    def get_agent_tokens(self, agent_type: AgentType) -> int:
        """Get the total tokens used by a specific agent."""
        return self._agent_totals.get(agent_type.value, 0)

    def get_provider_tokens(self, provider: AIProvider) -> int:
        """Get the total tokens used with a specific provider."""
        return self._provider_totals.get(provider.value, 0)

    def get_project_summary(self, project_id: str) -> TokenSummary:
        """Get a detailed token usage summary for a project."""
        summary = TokenSummary()
        project_entries = [e for e in self._entries if e.project_id == project_id]

        for entry in project_entries:
            summary.total_input_tokens += entry.input_tokens
            summary.total_output_tokens += entry.output_tokens
            summary.total_cached_tokens += entry.cached_tokens
            summary.total_tokens += entry.total_tokens
            summary.entry_count += 1
            summary.by_agent[entry.agent_type.value] = (
                summary.by_agent.get(entry.agent_type.value, 0) + entry.total_tokens
            )
            summary.by_provider[entry.provider.value] = (
                summary.by_provider.get(entry.provider.value, 0) + entry.total_tokens
            )

        return summary

    def get_all_entries(self) -> list[TokenEntry]:
        """Return all recorded token entries."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear all tracked tokens (primarily for testing)."""
        self._entries.clear()
        self._project_totals.clear()
        self._user_totals.clear()
        self._agent_totals.clear()
        self._provider_totals.clear()
