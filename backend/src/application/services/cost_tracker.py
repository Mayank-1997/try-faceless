"""Cost Tracker — centralised tracking of all AI operation costs.

Tracks costs at multiple granularities:
- Per agent (which agent incurred the cost)
- Per project (total project cost)
- Per user (aggregate user spending)
- Per scene (individual scene cost)
- Per provider (cost breakdown by provider)

Costs are accumulated in memory and periodically persisted to the
database via the ``api_usage`` table (implemented in Phase 3).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.core.config_service import ConfigService
from src.core.enums import AIProvider, AgentType
from src.core.interfaces import CostCalculator
from src.core.logging import get_logger


class CostEntry(BaseModel):
    """A single cost tracking entry."""

    agent_type: AgentType
    provider: AIProvider
    model: str
    cost_usd: float
    project_id: str | None = None
    scene_id: str | None = None
    user_id: str | None = None
    operation: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CostSummary(BaseModel):
    """Aggregated cost summary for a project or user."""

    total_cost_usd: float = 0.0
    llm_cost_usd: float = 0.0
    image_cost_usd: float = 0.0
    video_cost_usd: float = 0.0
    voice_cost_usd: float = 0.0
    render_cost_usd: float = 0.0
    entry_count: int = 0
    by_agent: dict[str, float] = Field(default_factory=dict)
    by_provider: dict[str, float] = Field(default_factory=dict)


class CostTracker(CostCalculator):
    """Centralised cost tracking service.

    Implements the ``CostCalculator`` interface for cost calculation
    and adds accumulation and summarisation capabilities.
    """

    def __init__(self, config: ConfigService) -> None:
        """Create the cost tracker.

        Args:
            config: The application configuration service.
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._entries: list[CostEntry] = []
        self._project_totals: dict[str, float] = defaultdict(float)
        self._user_totals: dict[str, float] = defaultdict(float)
        self._agent_totals: dict[str, float] = defaultdict(float)
        self._provider_totals: dict[str, float] = defaultdict(float)

    def record(self, entry: CostEntry) -> None:
        """Record a cost entry.

        Args:
            entry: The cost entry to record.
        """
        self._entries.append(entry)

        if entry.project_id:
            self._project_totals[entry.project_id] += entry.cost_usd
        if entry.user_id:
            self._user_totals[entry.user_id] += entry.cost_usd
        self._agent_totals[entry.agent_type.value] += entry.cost_usd
        self._provider_totals[entry.provider.value] += entry.cost_usd

        self._logger.info(
            "cost_recorded",
            agent=entry.agent_type.value,
            provider=entry.provider.value,
            cost_usd=entry.cost_usd,
            project_id=entry.project_id,
        )

    def get_project_cost(self, project_id: str) -> float:
        """Get the total cost for a project.

        Args:
            project_id: The project UUID string.

        Returns:
            Total cost in USD.
        """
        return self._project_totals.get(project_id, 0.0)

    def get_user_cost(self, user_id: str) -> float:
        """Get the total cost for a user.

        Args:
            user_id: The user UUID string.

        Returns:
            Total cost in USD.
        """
        return self._user_totals.get(user_id, 0.0)

    def get_agent_cost(self, agent_type: AgentType) -> float:
        """Get the total cost incurred by a specific agent.

        Args:
            agent_type: The agent type.

        Returns:
            Total cost in USD.
        """
        return self._agent_totals.get(agent_type.value, 0.0)

    def get_provider_cost(self, provider: AIProvider) -> float:
        """Get the total cost incurred with a specific provider.

        Args:
            provider: The AI provider.

        Returns:
            Total cost in USD.
        """
        return self._provider_totals.get(provider.value, 0.0)

    def get_project_summary(self, project_id: str) -> CostSummary:
        """Get a detailed cost summary for a project.

        Args:
            project_id: The project UUID string.

        Returns:
            ``CostSummary`` with breakdowns by category, agent, and provider.
        """
        summary = CostSummary()
        project_entries = [e for e in self._entries if e.project_id == project_id]

        for entry in project_entries:
            summary.total_cost_usd += entry.cost_usd
            summary.entry_count += 1
            summary.by_agent[entry.agent_type.value] = (
                summary.by_agent.get(entry.agent_type.value, 0.0) + entry.cost_usd
            )
            summary.by_provider[entry.provider.value] = (
                summary.by_provider.get(entry.provider.value, 0.0) + entry.cost_usd
            )

            # Categorise by provider type
            if entry.provider in (AIProvider.GEMINI, AIProvider.OPENAI, AIProvider.CLAUDE):
                summary.llm_cost_usd += entry.cost_usd
            elif entry.provider in (AIProvider.IMAGEN,):
                summary.image_cost_usd += entry.cost_usd
            elif entry.provider in (AIProvider.VEO, AIProvider.RUNWAY, AIProvider.FAL, AIProvider.KLING):
                summary.video_cost_usd += entry.cost_usd
            elif entry.provider in (AIProvider.GOOGLE_TTS, AIProvider.ELEVENLABS):
                summary.voice_cost_usd += entry.cost_usd

        return summary

    def get_all_entries(self) -> list[CostEntry]:
        """Return all recorded cost entries."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear all tracked costs (primarily for testing)."""
        self._entries.clear()
        self._project_totals.clear()
        self._user_totals.clear()
        self._agent_totals.clear()
        self._provider_totals.clear()

    # -----------------------------------------------------------------------
    # CostCalculator interface implementation
    # -----------------------------------------------------------------------
    def calculate_llm_cost(
        self, provider: AIProvider, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate the cost of an LLM request."""
        if provider == AIProvider.GEMINI:
            if "flash" in model.lower():
                input_cost = (input_tokens / 1000) * self._config.cost.gemini_flash_input_per_1k
                output_cost = (output_tokens / 1000) * self._config.cost.gemini_flash_output_per_1k
            else:
                input_cost = (input_tokens / 1000) * self._config.cost.gemini_pro_input_per_1k
                output_cost = (output_tokens / 1000) * self._config.cost.gemini_pro_output_per_1k
            return round(input_cost + output_cost, 6)
        return 0.0

    def calculate_image_cost(self, provider: AIProvider, width: int, height: int) -> float:
        """Calculate the cost of an image generation request."""
        if provider == AIProvider.IMAGEN:
            return self._config.cost.imagen_per_image
        return 0.0

    def calculate_video_cost(self, provider: AIProvider, duration_seconds: float, resolution: str) -> float:
        """Calculate the cost of a video generation request."""
        if provider == AIProvider.VEO:
            return round(self._config.cost.veo_per_second * duration_seconds, 6)
        if provider == AIProvider.KLING:
            return round(self._config.cost.kling_per_second * duration_seconds, 6)
        return 0.0

    def calculate_voice_cost(self, provider: AIProvider, character_count: int) -> float:
        """Calculate the cost of a voice generation request."""
        if provider == AIProvider.GOOGLE_TTS:
            return round((character_count / 1000) * self._config.cost.tts_per_1k_chars, 6)
        return 0.0

    def calculate_render_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate the cost of a rendering operation.

        FFmpeg rendering is currently free (self-hosted).  Cloud
        rendering costs will be added when cloud renderers are implemented.
        """
        return 0.0
