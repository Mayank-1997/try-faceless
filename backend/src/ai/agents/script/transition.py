"""Transition Agent — generates smooth transitions between sections.

Fifth agent in the script workflow.  Takes all written sections
and generates smooth transitions ensuring natural flow between
them, avoiding abrupt topic changes.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.response import AIResponse
from src.ai.agents.script.prompts import TRANSITION_PROMPT
from src.ai.agents.script.schema import NarrativeStrategy, ScriptSection, TransitionResult
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class TransitionAgent(BaseAgent):
    """Generates smooth transitions between script sections.

    - Ensures sections connect naturally
    - Avoids abrupt topic changes
    - Provides flow analysis
    - Assigns smoothness score
    """

    def __init__(self) -> None:
        super().__init__(
            name="transition",
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
            "required_fields": ["transitions"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        ns_data = context.state.script.metadata.get("narrative_strategy", {})
        strategy = NarrativeStrategy.model_validate(ns_data) if ns_data else NarrativeStrategy()

        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        sections_data = context.state.script.metadata.get("sections", [])
        sections = [ScriptSection.model_validate(s) for s in sections_data] if sections_data else []

        sections_text = "\n\n".join(
            f"[{s.section_id}] {s.title}\n{s.narration}"
            for s in sections
        )
        if not sections_text:
            sections_text = "No sections available."

        return TRANSITION_PROMPT, {
            "topic": topic,
            "narrative_style": strategy.style,
            "sections": sections_text,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return TransitionResult(
            transitions=data.get("transitions", {}),
            flow_analysis=data.get("flow_analysis", ""),
            smoothness_score=data.get("smoothness_score", 0.0),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, TransitionResult):
            context.state.script.metadata["transitions"] = result.model_dump()

            # Update section transitions
            sections_data = context.state.script.metadata.get("sections", [])
            sections = (
                [ScriptSection.model_validate(s) for s in sections_data]
                if sections_data
                else []
            )
            for section in sections:
                if section.section_id in result.transitions:
                    section.transition = result.transitions[section.section_id]
            context.state.script.metadata["sections"] = [s.model_dump() for s in sections]
