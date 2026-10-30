"""Hook Generator Agent — generates multiple hooks and selects the best.

Third agent in the script workflow.  Generates hooks using various
techniques (question, bold statement, unexpected fact, story,
contradiction, curiosity gap), then selects the best one based on
estimated retention score.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.script.prompts import HOOK_GENERATOR_PROMPT
from src.ai.agents.script.schema import Hook, HookResult, NarrativeStrategy
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class HookGeneratorAgent(BaseAgent):
    """Generates multiple hooks and selects the best one.

    Generates hooks using:
    - Question
    - Bold Statement
    - Unexpected Fact
    - Story
    - Contradiction
    - Curiosity Gap

    Stores rejected hooks for reference.
    """

    def __init__(self) -> None:
        super().__init__(
            name="hook_generator",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SCRIPT_WRITER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["hooks"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        ns_data = context.state.script.metadata.get("narrative_strategy", {})
        strategy = NarrativeStrategy.model_validate(ns_data) if ns_data else NarrativeStrategy()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        audience = rp.audience.primary_persona.persona_name or "general audience"
        content_angle = rp.content_angle.selected_angle.angle_type if rp.content_angle.selected_angle else ""

        return HOOK_GENERATOR_PROMPT, {
            "topic": topic,
            "narrative_style": strategy.style,
            "audience": audience,
            "content_angle": content_angle,
            "research_summary": rp.summary.overview or "No summary available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        hooks = [
            Hook(
                hook_type=h.get("hook_type", ""),
                content=h.get("content", ""),
                rationale=h.get("rationale", ""),
                estimated_retention_score=h.get("estimated_retention_score", 0.0),
            )
            for h in data.get("hooks", [])
            if h.get("content")
        ]

        # Select best hook by retention score
        if hooks:
            selected = max(hooks, key=lambda h: h.estimated_retention_score)
            rejected = [h for h in hooks if h is not selected]
        else:
            selected = None
            rejected = []

        return HookResult(
            hooks=hooks,
            selected_hook=selected,
            rejected_hooks=rejected,
            selection_rationale=f"Selected for highest retention score: {selected.estimated_retention_score:.2f}" if selected else "",
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, HookResult):
            context.state.script.metadata["hook_result"] = result.model_dump()
            if result.selected_hook:
                context.state.script.hook = result.selected_hook.content
