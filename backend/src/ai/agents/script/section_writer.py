"""Section Writer Agent — writes individual script sections.

Fourth agent in the script workflow.  Takes the outline and writes
each section independently with narration, facts, examples,
emotional pacing, and references.  Supports parallel execution
of multiple sections.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.response import AIResponse
from src.ai.agents.script.prompts import SECTION_WRITER_PROMPT
from src.ai.agents.script.schema import (
    NarrativeStrategy,
    ScriptOutline,
    ScriptSection,
)
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class SectionWriterAgent(BaseAgent):
    """Writes individual script sections from the outline.

    Each section includes:
    - Full narration text
    - Facts used
    - Examples
    - Emotional pacing
    - Estimated duration and word count
    - References
    - Future scene count estimate

    Supports parallel execution — each section is written independently.
    The agent iterates over all outline sections and writes each one.
    """

    def __init__(self) -> None:
        super().__init__(
            name="section_writer",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.4,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SCRIPT_WRITER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["sections"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        ns_data = context.state.script.metadata.get("narrative_strategy", {})
        strategy = NarrativeStrategy.model_validate(ns_data) if ns_data else NarrativeStrategy()

        outline_data = context.state.script.metadata.get("script_outline", {})
        outline = ScriptOutline.model_validate(outline_data) if outline_data else ScriptOutline()

        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        # Light research context — keep only the first 7 verified facts
        rp_data = context.state.research.metadata.get("research_package", {})
        if rp_data:
            verified = rp_data.get("fact_verification", {}).get("verified_facts", [])[:7]
            facts = "\n".join(
                f"- [{vf.get('category', '')}] {vf.get('fact', '')}" for vf in verified
            )
        else:
            facts = "No specific facts available. Use general knowledge."

        if not facts:
            facts = "No specific facts available. Use general knowledge."

        # List all outline sections for the model
        sections_text = "\n\n".join(
            f"[{s.section_id}] {s.title}\n"
            f"- Description: {s.description}\n"
            f"- Key talking points: {', '.join(s.key_talking_points)}\n"
            f"- Target word count: {s.target_word_count}\n"
            f"- Estimated duration: {s.estimated_time_seconds} seconds"
            for s in outline.sections
        )
        if not sections_text:
            sections_text = "No sections available."

        return SECTION_WRITER_PROMPT, {
            "topic": topic,
            "narrative_style": strategy.style,
            "tone": strategy.tone,
            "sections": sections_text,
            "research_facts": facts,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        raw_sections = data.get("sections", [])
        return [
            ScriptSection(
                section_id=s.get("section_id", ""),
                title=s.get("title", ""),
                narration=s.get("narration", ""),
                estimated_duration_seconds=s.get("estimated_duration_seconds", 0),
                word_count=s.get(
                    "word_count",
                    len(s.get("narration", "").split()) if s.get("narration") else 0,
                ),
                emotion=s.get("emotion", "neutral"),
                importance=s.get("importance", "medium"),
                purpose=s.get("purpose", "inform"),
                references=s.get("references", []),
                facts_used=s.get("facts_used", []),
                examples=s.get("examples", []),
                future_scene_count=s.get("future_scene_count", 0),
            )
            for s in raw_sections
            if s.get("narration")
        ]

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if not isinstance(result, list):
            return

        # Append to existing sections list, replacing by section_id
        existing = context.state.script.metadata.get("sections", [])
        sections = [ScriptSection.model_validate(s) for s in existing] if existing else []
        existing_ids = {s.section_id for s in sections}

        for new_section in result:
            if new_section.section_id in existing_ids:
                for i, s in enumerate(sections):
                    if s.section_id == new_section.section_id:
                        sections[i] = new_section
                        break
            else:
                sections.append(new_section)
            existing_ids.add(new_section.section_id)

        context.state.script.metadata["sections"] = [s.model_dump() for s in sections]
