"""Call to Action Agent — generates CTAs matching channel style.

Sixth agent in the script workflow.  Generates multiple CTAs
(subscribe, like, comment, visit website, download, newsletter),
selects a primary and secondary CTAs, and ensures they match
the channel style.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.script.prompts import CTA_PROMPT
from src.ai.agents.script.schema import CallToAction, CTAResult, NarrativeStrategy
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class CallToActionAgent(BaseAgent):
    """Generates call-to-action content for the script.

    Generates CTAs using types:
    - Subscribe
    - Like
    - Comment
    - Visit Website
    - Download
    - Newsletter

    Selects primary and secondary CTAs that match channel style.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cta",
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
            "required_fields": ["ctas"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        ns_data = context.state.script.metadata.get("narrative_strategy", {})
        strategy = NarrativeStrategy.model_validate(ns_data) if ns_data else NarrativeStrategy()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        audience = rp.audience.primary_persona.persona_name or "general audience"
        channel_style = context.state.script.metadata.get("channel_style", "educational")

        return CTA_PROMPT, {
            "topic": topic,
            "audience": audience,
            "narrative_style": strategy.style,
            "channel_style": channel_style,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        def parse_cta(c: dict) -> CallToAction:
            return CallToAction(
                cta_type=c.get("cta_type", ""),
                content=c.get("content", ""),
                placement=c.get("placement", "end"),
                rationale=c.get("rationale", ""),
            )

        ctas = [parse_cta(c) for c in data.get("ctas", []) if c.get("content")]
        primary_data = data.get("primary_cta", {})
        primary = parse_cta(primary_data) if primary_data and primary_data.get("content") else (ctas[0] if ctas else None)
        secondary = [parse_cta(c) for c in data.get("secondary_ctas", []) if c.get("content")]

        return CTAResult(
            ctas=ctas,
            primary_cta=primary,
            secondary_ctas=secondary,
            channel_style_match=data.get("channel_style_match", ""),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, CTAResult):
            context.state.script.metadata["cta_result"] = result.model_dump()
            if result.primary_cta:
                context.state.script.outro = result.primary_cta.content
