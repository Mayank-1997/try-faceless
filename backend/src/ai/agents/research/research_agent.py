"""Research Agent — gathers information from web search results.

Third agent in the research workflow.  Uses the research plan to
execute web searches (via the LLM gateway or a search tool) and
extracts structured facts, statistics, examples, historical events,
and definitions from the results.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import RESEARCH_PROMPT
from src.ai.agents.research.schema import (
    ResearchFact,
    ResearchItem,
    ResearchPlan,
    WebResearchResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ResearchAgent(BaseAgent):
    """Gathers information from web search results.

    For each search query in the research plan, this agent:
    1. Executes a web search (via tool or LLM gateway)
    2. Processes the results to extract structured facts
    3. Categorizes facts by type (fact, statistic, example, historical_event, definition)
    4. Collects references

    The agent uses the ``RESEARCH_PROMPT`` template to process
    search results through the LLM for structured extraction.
    """

    def __init__(self, max_queries: int = 5) -> None:
        super().__init__(
            name="research_agent",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.4,
        )
        self._max_queries = max_queries

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCH

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["facts"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        plan_data = context.state.research.metadata.get("research_plan", {})
        plan = ResearchPlan.model_validate(plan_data) if plan_data else ResearchPlan()

        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        # Gather search results from all queries
        all_results: list[str] = []
        queries_executed = 0

        for section in plan.sections:
            for query in section.queries:
                if queries_executed >= self._max_queries:
                    break
                search_results = await self._execute_search(query.query, context)
                if search_results:
                    all_results.append(f"Query: {query.query}\nResults:\n{search_results}")
                queries_executed += 1
            if queries_executed >= self._max_queries:
                break

        # If no plan queries, use the topic as a single query
        if not all_results:
            search_results = await self._execute_search(topic, context)
            if search_results:
                all_results.append(f"Query: {topic}\nResults:\n{search_results}")

        search_text = "\n\n".join(all_results) if all_results else "No search results available. Use your knowledge about the topic."

        return RESEARCH_PROMPT, {
            "topic": topic,
            "query": topic,
            "search_results": search_text,
        }

    async def _execute_search(self, query: str, context: AgentContext) -> str:
        """Execute a web search using available tools or gateway.

        Tries (in order):
        1. Web search tool from context.tools
        2. LLM gateway (as fallback for knowledge-based responses)

        Args:
            query: The search query.
            context: The agent context.

        Returns:
            Search results as a string.
        """
        # Try web search tool first
        if "web_search" in context.tools:
            try:
                tool = context.get_tool("web_search")
                result = await tool.execute(query=query)
                if result.success and result.output:
                    return str(result.output)
            except Exception:
                pass

        # Fallback: use LLM gateway directly for knowledge-based response
        if context.llm_gateway or context.gateways.get("llm"):
            try:
                gateway = context.llm_gateway or context.gateways.get("llm")
                result = await gateway.generate(
                    f"Provide detailed factual information about: {query}",
                    use_flash=True,
                )
                if result and result.success:
                    return result.output if hasattr(result, "output") else str(result)
            except Exception:
                pass

        return ""

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        def parse_facts(raw: list[dict]) -> list[ResearchFact]:
            return [
                ResearchFact(
                    fact=f.get("fact", ""),
                    source_url=f.get("source_url", ""),
                    source_title=f.get("source_title", ""),
                    category=f.get("category", "fact"),
                    confidence=f.get("confidence", 0.5),
                    verified=False,
                    references=f.get("references", []),
                )
                for f in raw if f.get("fact")
            ]

        facts = parse_facts(data.get("facts", []))
        statistics = parse_facts(data.get("statistics", []))
        examples = parse_facts(data.get("examples", []))
        historical_events = parse_facts(data.get("historical_events", []))
        definitions = parse_facts(data.get("definitions", []))
        references = data.get("references", [])

        all_facts = facts + statistics + examples + historical_events + definitions

        return WebResearchResult(
            query=context.state.topic.expanded_topic or context.state.topic.raw_topic,
            items=[],
            total_results=len(all_facts),
            facts=facts,
            statistics=statistics,
            examples=examples,
            historical_events=historical_events,
            definitions=definitions,
            references=references,
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, WebResearchResult):
            context.state.research.metadata["web_research"] = result.model_dump()
            context.state.research.key_facts = [f.fact for f in result.facts if f.fact]
            context.state.research.sources = [
                type("ResearchSource", (), {
                    "url": f.source_url,
                    "title": f.source_title,
                    "snippet": f.fact,
                    "relevance_score": f.confidence,
                })()
                for f in result.facts if f.source_url
            ]
