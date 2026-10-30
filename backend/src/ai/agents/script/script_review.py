"""Script Review Agent — validates script quality and effectiveness.

Seventh agent in the script workflow.  Reviews the complete script
for logic, flow, completeness, consistency, fact usage, audience
alignment, length, and reading level.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.response import AIResponse
from src.ai.agents.script.prompts import SCRIPT_REVIEW_PROMPT
from src.ai.agents.script.schema import (
    HookResult,
    ScriptReviewResult,
    ScriptSection,
)
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ScriptReviewAgent(BaseAgent):
    """Reviews the complete script for quality.

    Validates:
    - Logic and argument flow
    - Narrative flow between sections
    - Completeness of content
    - Consistency of tone and style
    - Fact usage and accuracy
    - Audience alignment
    - Length appropriateness
    - Reading level suitability
    """

    def __init__(self) -> None:
        super().__init__(
            name="script_review",
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
            "required_fields": ["overall_score", "passed"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        audience = rp.audience.primary_persona.persona_name or "general audience"
        target_duration = (
            context.state.project.target_duration_seconds
            or rp.topic_analysis.target_duration_seconds
        )

        # Assemble full script text
        sections_data = context.state.script.metadata.get("sections", [])
        sections = [ScriptSection.model_validate(s) for s in sections_data] if sections_data else []

        hook_data = context.state.script.metadata.get("hook_result", {})
        hook_result = HookResult.model_validate(hook_data) if hook_data else HookResult()

        parts = []
        if hook_result.selected_hook:
            parts.append(f"[HOOK] {hook_result.selected_hook.content}")
        for s in sections:
            parts.append(f"[{s.section_id}] {s.title}\n{s.narration}")
        full_script = "\n\n".join(parts) if parts else "No script content available."

        return SCRIPT_REVIEW_PROMPT, {
            "topic": topic,
            "audience": audience,
            "target_duration": target_duration,
            "full_script": full_script,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return ScriptReviewResult(
            logic_score=data.get("logic_score", 0.0),
            flow_score=data.get("flow_score", 0.0),
            completeness_score=data.get("completeness_score", 0.0),
            consistency_score=data.get("consistency_score", 0.0),
            fact_usage_score=data.get("fact_usage_score", 0.0),
            audience_alignment_score=data.get("audience_alignment_score", 0.0),
            length_score=data.get("length_score", 0.0),
            reading_level_score=data.get("reading_level_score", 0.0),
            overall_score=data.get("overall_score", 0.0),
            issues=data.get("issues", []),
            strengths=data.get("strengths", []),
            recommendations=data.get("recommendations", []),
            passed=data.get("passed", False),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, ScriptReviewResult):
            context.state.script.metadata["review"] = result.model_dump()
            context.state.script.quality_score = result.overall_score
