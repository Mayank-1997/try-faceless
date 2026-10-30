"""Tests for workflow-level Langfuse tracing.

Verifies:
- One trace per workflow trigger, grouped by session_id = workflow_id
- Agents attach generations to the parent workflow trace (no new trace per prompt)
- Per-step spans carry start/end timestamps
- Standalone prompt executions still get their own trace (backwards compatible)
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai.agents.prompt_executor import PromptExecutionOptions, PromptExecutor
from src.ai.agents.script.script_review import ScriptReviewAgent
from src.core.logging import get_logger
from src.infrastructure.observability.langfuse_client import LangfuseClient
from src.workflow.contexts import NodeContext
from src.workflow.state import ResearchData, ScriptData, TopicData, WorkflowState


def _make_gateway_result(output: str = '{"overall_score": 0.9, "passed": true}'):
    """Minimal GenerationResult-like object for the mocked gateway."""
    return SimpleNamespace(
        success=True,
        provider="gemini",
        model="gemini-2.0-flash",
        output=output,
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        cost_usd=0.001,
        latency_ms=50,
        response=output,
        warnings=[],
        errors=[],
        metadata={},
    )


def _bare_langfuse_client() -> LangfuseClient:
    """Build a LangfuseClient with a mocked SDK client (no network, no config)."""
    client = LangfuseClient.__new__(LangfuseClient)
    client._config = None
    client._logger = get_logger("test_langfuse")
    client.enabled = True
    client._client = MagicMock()
    return client


class TestPromptExecutorParentTrace:
    async def test_attaches_to_parent_trace_without_starting_new_one(self):
        langfuse = MagicMock()
        langfuse.start_trace = MagicMock(return_value="should-not-be-used")
        langfuse.update_trace = MagicMock()
        gateway = MagicMock()
        gateway.generate = AsyncMock(return_value=_make_gateway_result())

        executor = PromptExecutor(llm_gateway=gateway, langfuse_client=langfuse)
        options = PromptExecutionOptions(
            correlation_id="corr-1",
            expect_json=True,
            trace_id="wf-trace-123",  # parent workflow trace
        )

        response = await executor.execute_prompt(
            "Write a hook", agent_name="hook_generator", options=options
        )

        assert response.success is True
        # Must NOT start its own trace when a parent trace is provided
        langfuse.start_trace.assert_not_called()
        # Must NOT update the workflow-level trace output (not the owner)
        langfuse.update_trace.assert_not_called()
        # Gateway must receive the parent trace id + agent-named generation
        gateway.generate.assert_awaited_once()
        kwargs = gateway.generate.await_args.kwargs
        assert kwargs["trace_id"] == "wf-trace-123"
        assert kwargs["generation_name"] == "agent: hook_generator"

    async def test_standalone_execution_still_starts_own_trace(self):
        langfuse = MagicMock()
        langfuse.start_trace = MagicMock(return_value="own-trace-1")
        langfuse.update_trace = MagicMock()
        gateway = MagicMock()
        gateway.generate = AsyncMock(return_value=_make_gateway_result())

        executor = PromptExecutor(llm_gateway=gateway, langfuse_client=langfuse)
        options = PromptExecutionOptions(correlation_id="corr-2", expect_json=True)

        response = await executor.execute_prompt(
            "Write a hook", agent_name="hook_generator", options=options
        )

        assert response.success is True
        langfuse.start_trace.assert_called_once()
        langfuse.update_trace.assert_called_once()
        kwargs = gateway.generate.await_args.kwargs
        assert kwargs["trace_id"] == "own-trace-1"

    async def test_failed_parent_trace_call_does_not_update_workflow_trace(self):
        langfuse = MagicMock()
        langfuse.start_trace = MagicMock(return_value="own-trace-9")
        langfuse.update_trace = MagicMock()
        gateway = MagicMock()
        gateway.generate = AsyncMock(side_effect=RuntimeError("boom"))

        executor = PromptExecutor(llm_gateway=gateway, langfuse_client=langfuse)
        options = PromptExecutionOptions(trace_id="wf-trace-xyz")

        from src.ai.agents.exceptions import PromptExecutionError

        with pytest.raises(PromptExecutionError, match="boom"):
            await executor.execute_prompt(
                "Write a hook", agent_name="hook_generator", options=options
            )

        langfuse.start_trace.assert_not_called()
        langfuse.update_trace.assert_not_called()


class TestLangfuseClientSpan:
    def test_span_creates_timestamped_span_inside_trace(self):
        lf = _bare_langfuse_client()
        trace_handle = MagicMock()
        lf._client.trace = MagicMock(return_value=trace_handle)

        start = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
        end = datetime(2026, 9, 6, 12, 0, 3, tzinfo=UTC)
        span_id = lf.span(
            trace_id="wf-trace-1",
            name="step: asset_generation",
            start_time=start,
            end_time=end,
            metadata={"project_id": "p-1"},
        )

        assert span_id is not None
        lf._client.trace.assert_called_once_with(id="wf-trace-1")
        trace_handle.span.assert_called_once()
        kwargs = trace_handle.span.call_args.kwargs
        assert kwargs["name"] == "step: asset_generation"
        assert kwargs["start_time"] == start
        assert kwargs["end_time"] == end
        assert kwargs["metadata"] == {"project_id": "p-1"}

    def test_span_disabled_client_is_noop(self):
        lf = _bare_langfuse_client()
        lf.enabled = False
        assert lf.span(trace_id="t", name="n") is None
        lf._client.trace.assert_not_called()

    def test_start_trace_passes_session_and_user(self):
        lf = _bare_langfuse_client()
        lf.start_trace(
            name="workflow: Island Survival",
            user_id="user-1",
            session_id="wf-42",
            metadata={"trigger": "ui"},
        )
        lf._client.trace.assert_called_once()
        kwargs = lf._client.trace.call_args.kwargs
        assert kwargs["name"] == "workflow: Island Survival"
        assert kwargs["user_id"] == "user-1"
        assert kwargs["session_id"] == "wf-42"


class TestAgentPropagation:
    async def test_agent_passes_workflow_trace_id_to_prompt_options(self):
        """BaseAgent must forward state.metadata.custom['langfuse_trace_id']."""
        state = WorkflowState(
            topic=TopicData(expanded_topic="A Boy Survived Alone on a Mysterious Island"),
            research=ResearchData(),
            script=ScriptData(
                metadata={
                    "narrative_strategy": {"style": "storytelling"},
                    "sections": [
                        {
                            "section_id": "s1",
                            "title": "The Crash",
                            "narration": "The sky shattered.",
                            "estimated_duration_seconds": 45,
                            "word_count": 50,
                        }
                    ],
                }
            ),
        )
        state.metadata.custom["langfuse_trace_id"] = "wf-trace-abc"
        captured: dict = {}

        class CapturingExecutor:
            async def execute_template(self, template, variables, *, agent_name="", options=None):
                captured["trace_id"] = getattr(options, "trace_id", "MISSING")
                captured["agent_name"] = agent_name
                import json

                from src.ai.agents.response import AIResponse

                return AIResponse(
                    success=True,
                    response=json.dumps(
                        {"overall_score": 0.9, "passed": True, "issues": [],
                         "strengths": [], "recommendations": []}
                    ),
                    structured_data={
                        "overall_score": 0.9, "passed": True, "issues": [],
                        "strengths": [], "recommendations": [],
                    },
                )

        ctx = NodeContext(
            state=state,
            services={"prompt_executor": CapturingExecutor()},
        )

        agent = ScriptReviewAgent()
        await agent.execute(ctx)

        assert captured["trace_id"] == "wf-trace-abc"
        assert captured["agent_name"] == "script_review"
        # The trace id must also survive in the persisted state
        assert state.metadata.custom["langfuse_trace_id"] == "wf-trace-abc"
