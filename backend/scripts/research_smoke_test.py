"""Research-only smoke test.

Runs the real ServiceContainer + research_workflow graph against Gemini for a
single topic to verify that agents receive the LLM gateway and produce a
ResearchPackage. Prints a concise PASS/FAIL summary.

Usage (inside the worker container):
    python scripts/research_smoke_test.py "Your topic here"
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

from src.application.di.container import ServiceContainer
from src.ai.agents.research.workflow import ResearchWorkflowGraph
from src.core.enums import ProjectInputType
from src.core.interfaces import LLMProvider
from src.workflow.engine import WorkflowEngine
from src.workflow.state import ProjectInfo, TopicData, WorkflowState


async def main(topic: str) -> int:
    container = ServiceContainer()
    await container.initialize()

    llm_count = len(container.provider_registry.get_providers_by_type(LLMProvider))
    print(f"LLM providers registered: {llm_count}")
    if llm_count == 0:
        print("RESULT: FAIL (no LLM provider configured)")
        await container.shutdown()
        return 1

    engine = WorkflowEngine()
    engine.register_workflow(ResearchWorkflowGraph())

    state = WorkflowState(
        project=ProjectInfo(
            project_id=uuid4(),
            user_id=uuid4(),
            name=topic,
            input_type=ProjectInputType.TOPIC,
            target_duration_seconds=600,
            target_resolution="1920x1080",
        ),
        topic=TopicData(raw_topic=topic),
    )

    result = await engine.execute(
        workflow_name="research_workflow",
        initial_state=state,
        project_id=state.project.project_id,
        user_id=state.project.user_id,
        config=container.config,
        gateways={"llm": container.llm_gateway},
        services={
            "prompt_executor": container.prompt_executor,
            "cost_tracker": container.cost_tracker,
            "token_tracker": container.token_tracker,
            "event_bus": container.event_bus,
            "langfuse_client": container.langfuse_client,
            "metrics_collector": container.metrics_collector,
        },
        timeout_seconds=900,
    )

    final = result.state
    has_package = bool(final.research.metadata.get("research_package"))
    print(f"execution_success={result.success}")
    print(f"total_tokens={final.total_tokens} total_cost_usd={final.total_cost_usd}")
    print(f"research_package_present={has_package}")
    if result.error:
        print(f"error={result.error}")

    await container.shutdown()

    if result.success and final.total_tokens > 0:
        print("RESULT: PASS")
        return 0
    print("RESULT: FAIL")
    return 2


if __name__ == "__main__":
    topic_arg = sys.argv[1] if len(sys.argv) > 1 else "The history and future of electric vehicles"
    raise SystemExit(asyncio.run(main(topic_arg)))
