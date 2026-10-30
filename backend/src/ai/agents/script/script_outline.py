"""Script Outline Agent — generates the complete script outline.

Second agent in the script workflow.  Takes the narrative strategy
and research package to produce a detailed outline with sections,
subsections, key talking points, estimated timing, and word counts.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.script.prompts import SCRIPT_OUTLINE_PROMPT
from src.ai.agents.script.schema import NarrativeStrategy, OutlineSection, ScriptOutline
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ScriptOutlineAgent(BaseAgent):
    """Generates a complete script outline.

    Produces:
    - Script title
    - Opening description
    - Sections with IDs, titles, descriptions
    - Key talking points per section
    - Estimated time and word count per section
    - References
    - Closing description
    """

    def __init__(self) -> None:
        super().__init__(
            name="script_outline",
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
            "required_fields": ["title", "sections"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        ns_data = context.state.script.metadata.get("narrative_strategy", {})
        strategy = NarrativeStrategy.model_validate(ns_data) if ns_data else NarrativeStrategy()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        # The user's requested duration is authoritative over the
        # topic-analyser's suggestion.
        target_duration = (
            context.state.project.target_duration_seconds
            or rp.topic_analysis.target_duration_seconds
            or 600
        )
        target_word_count = int(target_duration * 2.5)  # ~150 wpm

        key_facts = "\n".join(f"- {f}" for f in rp.summary.important_facts[:15])
        if not key_facts:
            key_facts = "No key facts available."

        return SCRIPT_OUTLINE_PROMPT, {
            "topic": topic,
            "narrative_style": strategy.style,
            "target_duration": target_duration,
            "target_word_count": target_word_count,
            "research_summary": rp.summary.overview or "No summary available.",
            "key_facts": key_facts,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        sections = [
            OutlineSection(
                section_id=s.get("section_id", f"s{i+1}"),
                title=s.get("title", ""),
                description=s.get("description", ""),
                key_talking_points=s.get("key_talking_points", []),
                estimated_time_seconds=s.get("estimated_time_seconds", 0),
                target_word_count=s.get("target_word_count", 0),
                references=s.get("references", []),
                subsections=s.get("subsections", []),
                importance=s.get("importance", "medium"),
            )
            for i, s in enumerate(data.get("sections", []))
        ]
        return ScriptOutline(
            title=data.get("title", ""),
            opening=data.get("opening", ""),
            sections=sections,
            closing=data.get("closing", ""),
            total_estimated_time_seconds=data.get("total_estimated_time_seconds", sum(s.estimated_time_seconds for s in sections)),
            total_target_word_count=data.get("total_target_word_count", sum(s.target_word_count for s in sections)),
            references=data.get("references", []),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, ScriptOutline):
            context.state.script.metadata["script_outline"] = result.model_dump()
            context.state.script.title = result.title
