"""Tests for the Phase 4 workflow orchestration framework."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.base_node import BaseNode
from src.workflow.builder import WorkflowBuilder
from src.workflow.checkpoint import CheckpointManager, CheckpointMetadata
from src.workflow.contexts import (
    CancellationToken,
    ExecutionContext,
    IdentityContext,
    NodeContext,
    WorkflowContext,
)
from src.workflow.engine import ExecutionResult, WorkflowEngine
from src.workflow.events import WorkflowEventEmitter, WorkflowEvents
from src.workflow.exceptions import (
    NodeExecutionError,
    NodeValidationError,
    WorkflowAlreadyRegisteredError,
    WorkflowCancelledError,
    WorkflowNotFoundError,
    classify_error,
    ErrorSeverity,
)
from src.workflow.registry import GraphRegistry
from src.workflow.retry_policy import RetryExecutor, RetryPolicies, RetryPolicy
from src.workflow.state import (
    ExecutionStatus,
    NodeExecutionRecord,
    WorkflowMetadata,
    WorkflowState,
)


# ---------------------------------------------------------------------------
# Test nodes
# ---------------------------------------------------------------------------
class EchoNode(BaseNode):
    """Simple node that sets a message in state."""
    def __init__(self, name: str = "echo", message: str = "hello") -> None:
        super().__init__(name=name, node_type="test")
        self.message = message

    async def execute(self, context: NodeContext) -> WorkflowState:
        context.state.execution.current_node = self.name
        context.state.execution.current_step = self.name
        return context.state


class FailingNode(BaseNode):
    """Node that always fails."""
    def __init__(self, name: str = "failing") -> None:
        super().__init__(name=name, node_type="test", retry_policy=RetryPolicies.NO_RETRY)

    async def execute(self, context: NodeContext) -> WorkflowState:
        raise ValueError("Intentional failure")


class RetryableFailingNode(BaseNode):
    """Node that fails N times then succeeds."""
    def __init__(self, name: str = "retryable", fail_count: int = 2) -> None:
        super().__init__(name=name, node_type="test",
                         retry_policy=RetryPolicy(max_retries=5, initial_delay_seconds=0.01))
        self.fail_count = fail_count
        self.attempts = 0

    async def execute(self, context: NodeContext) -> WorkflowState:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ConnectionError("Transient failure")
        context.state.execution.current_node = self.name
        return context.state


class CostTrackingNode(BaseNode):
    """Node that records cost and tokens."""
    def __init__(self, name: str = "cost_tracker") -> None:
        super().__init__(name=name, node_type="test")

    async def execute(self, context: NodeContext) -> WorkflowState:
        self.record_cost(context, 0.05, "llm")
        self.record_tokens(context, input_tokens=100, output_tokens=50)
        return context.state


# ---------------------------------------------------------------------------
# Test graph
# ---------------------------------------------------------------------------
class SimpleTestGraph(BaseWorkflowGraph):
    """A simple 3-node test graph."""
    @property
    def metadata(self) -> GraphMetadata:
        return GraphMetadata(
            name="test_workflow",
            version="1.0.0",
            description="Test workflow",
            content_type="test",
            entry_node="node_a",
            exit_nodes=["node_c"],
        )

    def build_graph(self) -> None:
        self.add_node(EchoNode("node_a"), is_entry=True)
        self.add_node(EchoNode("node_b"))
        self.add_node(EchoNode("node_c"), is_exit=True)
        self.add_edge("node_a", "node_b")
        self.add_edge("node_b", "node_c")


class ConditionalTestGraph(BaseWorkflowGraph):
    """Graph with conditional routing."""
    @property
    def metadata(self) -> GraphMetadata:
        return GraphMetadata(
            name="conditional_workflow",
            version="1.0.0",
            entry_node="start",
            exit_nodes=["done", "retry"],
        )

    def build_graph(self) -> None:
        self.add_node(EchoNode("start"), is_entry=True)
        self.add_node(EchoNode("done"), is_exit=True)
        self.add_node(EchoNode("retry"), is_exit=True)
        self.add_conditional_edge(
            "start", "done",
            lambda s: s.research.summary != "",
            "has_research",
        )
        self.add_conditional_edge(
            "start", "retry",
            lambda s: s.research.summary == "",
            "no_research",
        )


# ---------------------------------------------------------------------------
# Context tests
# ---------------------------------------------------------------------------
class TestIdentityContext:
    def test_default_creation(self):
        ctx = IdentityContext()
        assert ctx.project_id is None
        assert ctx.user_id is None
        assert ctx.workflow_id == ""
        assert ctx.execution_id is not None

    def test_frozen(self):
        ctx = IdentityContext(workflow_id="test")
        with pytest.raises(Exception):
            ctx.workflow_id = "changed"


class TestExecutionContext:
    def test_default_creation(self):
        ctx = ExecutionContext()
        assert ctx.current_node == ""
        assert ctx.retry_count == 0
        assert ctx.timeout_seconds is None
        assert not ctx.is_timed_out

    def test_timed_out(self):
        ctx = ExecutionContext(timeout_seconds=0, started_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        assert ctx.is_timed_out

    def test_elapsed_seconds(self):
        ctx = ExecutionContext(started_at=datetime.now(timezone.utc))
        assert ctx.elapsed_seconds >= 0


class TestCancellationToken:
    def test_not_cancelled_by_default(self):
        token = CancellationToken()
        assert not token.is_cancelled
        assert token.reason is None

    def test_cancel(self):
        token = CancellationToken()
        token.cancel("test reason")
        assert token.is_cancelled
        assert token.reason == "test reason"

    def test_reset(self):
        token = CancellationToken()
        token.cancel()
        token.reset()
        assert not token.is_cancelled


class TestNodeContext:
    def test_get_repository_not_found(self):
        ctx = NodeContext()
        with pytest.raises(KeyError):
            ctx.get_repository("nonexistent")

    def test_get_gateway_not_found(self):
        ctx = NodeContext()
        with pytest.raises(KeyError):
            ctx.get_gateway("nonexistent")

    def test_get_service_not_found(self):
        ctx = NodeContext()
        with pytest.raises(KeyError):
            ctx.get_service("nonexistent")

    def test_get_repository(self):
        ctx = NodeContext(repositories={"project": "repo_instance"})
        assert ctx.get_repository("project") == "repo_instance"

    def test_is_cancelled(self):
        token = CancellationToken()
        ctx = NodeContext(cancellation_token=token)
        assert not ctx.is_cancelled
        token.cancel()
        assert ctx.is_cancelled


class TestWorkflowContext:
    def test_create_node_context(self):
        wf_ctx = WorkflowContext(
            identity=IdentityContext(workflow_id="test"),
            repositories={"repo": "instance"},
        )
        state = WorkflowState()
        node_ctx = wf_ctx.create_node_context(state, "my_node")
        assert node_ctx.execution.current_node == "my_node"
        assert node_ctx.repositories == {"repo": "instance"}
        assert node_ctx.state is state


# ---------------------------------------------------------------------------
# Retry policy tests
# ---------------------------------------------------------------------------
class TestRetryPolicy:
    def test_should_retry_within_limits(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(ConnectionError("test"), 0)
        assert policy.should_retry(ConnectionError("test"), 2)
        assert not policy.should_retry(ConnectionError("test"), 3)

    def test_should_not_retry_validation_error(self):
        policy = RetryPolicy(max_retries=3)
        from src.core.exceptions import ValidationError
        error = ValidationError("field", "bad value")
        severity = classify_error(error)
        assert severity == ErrorSeverity.VALIDATION
        assert not policy.should_retry(error, 0)

    def test_should_retry_provider_error(self):
        from src.core.exceptions import AIProviderError
        policy = RetryPolicy(max_retries=3)
        error = AIProviderError("gemini", "timeout")
        assert policy.should_retry(error, 0)

    def test_get_delay_exponential(self):
        policy = RetryPolicy(
            max_retries=5, initial_delay_seconds=1.0,
            max_delay_seconds=100.0, backoff_multiplier=2.0, jitter=False,
        )
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_get_delay_capped(self):
        policy = RetryPolicy(
            max_retries=10, initial_delay_seconds=1.0,
            max_delay_seconds=10.0, backoff_multiplier=2.0, jitter=False,
        )
        assert policy.get_delay(10) == 10.0

    def test_jitter_adds_randomness(self):
        policy = RetryPolicy(jitter=True, initial_delay_seconds=1.0, backoff_multiplier=1.0)
        delays = {policy.get_delay(0) for _ in range(10)}
        assert len(delays) > 1


class TestRetryPolicies:
    def test_no_retry(self):
        assert RetryPolicies.NO_RETRY.max_retries == 0

    def test_standard(self):
        assert RetryPolicies.STANDARD.max_retries == 3

    def test_aggressive(self):
        assert RetryPolicies.AGGRESSIVE.max_retries == 5

    def test_conservative(self):
        assert RetryPolicies.CONSERVATIVE.max_retries == 2

    def test_provider(self):
        assert RetryPolicies.PROVIDER.max_retries == 4


class TestRetryExecutor:
    @pytest.mark.asyncio
    async def test_success_first_try(self):
        executor = RetryExecutor(RetryPolicies.NO_RETRY)
        calls = []

        async def func():
            calls.append(1)

        result = await executor.execute(func)
        assert result.success
        assert result.attempts == 1
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_fails_no_retry(self):
        executor = RetryExecutor(RetryPolicies.NO_RETRY)

        async def func():
            raise ValueError("fail")

        result = await executor.execute(func)
        assert not result.success
        assert result.attempts == 1
        assert isinstance(result.last_error, ValueError)

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        policy = RetryPolicy(max_retries=3, initial_delay_seconds=0.001, jitter=False)
        executor = RetryExecutor(policy)
        attempts = []

        async def func():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("transient")

        result = await executor.execute(func)
        assert result.success
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_retries_exhausted(self):
        policy = RetryPolicy(max_retries=2, initial_delay_seconds=0.001, jitter=False)
        executor = RetryExecutor(policy)

        async def func():
            raise ConnectionError("always fails")

        result = await executor.execute(func)
        assert not result.success
        assert result.attempts == 3  # 1 initial + 2 retries


# ---------------------------------------------------------------------------
# BaseNode tests
# ---------------------------------------------------------------------------
class TestBaseNode:
    @pytest.mark.asyncio
    async def test_echo_node_executes(self):
        node = EchoNode("test_echo", "hello")
        ctx = NodeContext(state=WorkflowState())
        result = await node.run(ctx)
        assert result.execution.current_node == "test_echo"

    @pytest.mark.asyncio
    async def test_failing_node_raises(self):
        node = FailingNode("test_fail")
        ctx = NodeContext(state=WorkflowState())
        with pytest.raises(NodeExecutionError):
            await node.run(ctx)

    @pytest.mark.asyncio
    async def test_node_records_history(self):
        node = EchoNode("test_history")
        ctx = NodeContext(state=WorkflowState())
        await node.run(ctx)
        assert len(ctx.state.execution.node_history) == 1
        record = ctx.state.execution.node_history[0]
        assert record.node_name == "test_history"
        assert record.status == "succeeded"

    @pytest.mark.asyncio
    async def test_failed_node_records_history(self):
        node = FailingNode("test_fail_history")
        ctx = NodeContext(state=WorkflowState())
        with pytest.raises(NodeExecutionError):
            await node.run(ctx)
        assert len(ctx.state.execution.node_history) == 1
        record = ctx.state.execution.node_history[0]
        assert record.status == "failed"
        assert record.error_message is not None

    @pytest.mark.asyncio
    async def test_retryable_node_succeeds_after_retries(self):
        node = RetryableFailingNode("test_retry", fail_count=2)
        ctx = NodeContext(state=WorkflowState())
        result = await node.run(ctx)
        assert result.execution.current_node == "test_retry"
        assert node.attempts == 3
        record = result.execution.node_history[0]
        assert record.retry_count == 2

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        node = CostTrackingNode("test_cost")
        ctx = NodeContext(state=WorkflowState())
        result = await node.run(ctx)
        assert result.cost.total_cost_usd == 0.05
        assert result.cost.llm_cost_usd == 0.05
        assert result.token_usage.input_tokens == 100
        assert result.token_usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_cancellation(self):
        node = EchoNode("test_cancel")
        token = CancellationToken()
        token.cancel()
        ctx = NodeContext(state=WorkflowState(), cancellation_token=token)
        result = await node.run(ctx)
        # Should return state unchanged
        assert result.execution.current_node == ""

    @pytest.mark.asyncio
    async def test_on_before_after_hooks(self):
        calls = []

        class HookedNode(BaseNode):
            def __init__(self):
                super().__init__(name="hooked", node_type="test")

            async def execute(self, context):
                calls.append("execute")
                return context.state

            async def on_before_execute(self, context):
                calls.append("before")

            async def on_after_execute(self, context, state):
                calls.append("after")

        node = HookedNode()
        ctx = NodeContext(state=WorkflowState())
        await node.run(ctx)
        assert calls == ["before", "execute", "after"]


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------
class TestBaseWorkflowGraph:
    @pytest.mark.asyncio
    async def test_build_and_execute(self):
        graph = SimpleTestGraph()
        await graph.build()
        assert graph.is_built
        assert len(graph.nodes) == 3

    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        graph = SimpleTestGraph()
        ctx = WorkflowContext()
        state = WorkflowState()
        result = await graph.execute(ctx, state)
        assert result.execution.completed_steps >= 1

    @pytest.mark.asyncio
    async def test_conditional_routing_done(self):
        graph = ConditionalTestGraph()
        ctx = WorkflowContext()
        state = WorkflowState()
        state.research = state.research.model_copy(update={"summary": "Some research"})
        result = await graph.execute(ctx, state)
        # Should route to "done"
        assert result.execution.completed_steps >= 1

    @pytest.mark.asyncio
    async def test_conditional_routing_retry(self):
        graph = ConditionalTestGraph()
        ctx = WorkflowContext()
        state = WorkflowState()
        # summary is "" by default
        result = await graph.execute(ctx, state)
        # Should route to "retry"
        assert result.execution.completed_steps >= 1

    def test_add_node_duplicate_raises(self):
        graph = SimpleTestGraph()
        graph.add_node(EchoNode("dup"))
        with pytest.raises(ValueError, match="already registered"):
            graph.add_node(EchoNode("dup"))

    def test_add_edge_unregistered_source(self):
        graph = SimpleTestGraph()
        with pytest.raises(ValueError, match="not registered"):
            graph.add_edge("nonexistent", "node_a")

    def test_add_edge_unregistered_target(self):
        graph = SimpleTestGraph()
        graph.add_node(EchoNode("src"))
        with pytest.raises(ValueError, match="not registered"):
            graph.add_edge("src", "nonexistent")


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------
class TestGraphRegistry:
    def test_register_and_get(self):
        registry = GraphRegistry()
        graph = SimpleTestGraph()
        registry.register(graph)
        retrieved = registry.get("test_workflow", "1.0.0")
        assert retrieved is graph

    def test_get_latest_version(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        retrieved = registry.get("test_workflow")
        assert retrieved is not None

    def test_get_not_found(self):
        registry = GraphRegistry()
        with pytest.raises(WorkflowNotFoundError):
            registry.get("nonexistent")

    def test_duplicate_registration_raises(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        with pytest.raises(WorkflowAlreadyRegisteredError):
            registry.register(SimpleTestGraph())

    def test_list_workflows(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        workflows = registry.list_workflows()
        assert len(workflows) == 1
        assert workflows[0]["name"] == "test_workflow"

    def test_list_versions(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        versions = registry.list_versions("test_workflow")
        assert "1.0.0" in versions

    def test_exists(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        assert registry.exists("test_workflow", "1.0.0")
        assert registry.exists("test_workflow")
        assert not registry.exists("nonexistent")

    def test_unregister(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        assert registry.unregister("test_workflow", "1.0.0")
        assert not registry.exists("test_workflow", "1.0.0")

    def test_clear(self):
        registry = GraphRegistry()
        registry.register(SimpleTestGraph())
        registry.clear()
        assert registry.count == 0

    def test_count(self):
        registry = GraphRegistry()
        assert registry.count == 0
        registry.register(SimpleTestGraph())
        assert registry.count == 1


# ---------------------------------------------------------------------------
# Checkpoint tests
# ---------------------------------------------------------------------------
class TestCheckpointManager:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        mgr = CheckpointManager(saver=None)
        state = WorkflowState()
        meta = await mgr.save(uuid4(), "test_wf", "node_a", 1, state)
        assert meta is not None
        retrieved = await mgr.get(meta.checkpoint_ref)
        assert retrieved.checkpoint_ref == meta.checkpoint_ref

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        mgr = CheckpointManager(saver=None)
        from src.workflow.exceptions import CheckpointNotFoundError
        with pytest.raises(CheckpointNotFoundError):
            await mgr.get("nonexistent")

    @pytest.mark.asyncio
    async def test_list_checkpoints(self):
        mgr = CheckpointManager(saver=None)
        exec_id = uuid4()
        state = WorkflowState()
        await mgr.save(exec_id, "wf", "node_a", 1, state)
        await mgr.save(exec_id, "wf", "node_b", 2, state)
        checkpoints = await mgr.list_checkpoints()
        assert len(checkpoints) == 2

    @pytest.mark.asyncio
    async def test_list_checkpoints_filtered(self):
        mgr = CheckpointManager(saver=None)
        exec1, exec2 = uuid4(), uuid4()
        state = WorkflowState()
        await mgr.save(exec1, "wf", "node_a", 1, state)
        await mgr.save(exec2, "wf", "node_b", 2, state)
        result = await mgr.list_checkpoints(execution_id=exec1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete(self):
        mgr = CheckpointManager(saver=None)
        state = WorkflowState()
        meta = await mgr.save(uuid4(), "wf", "node", 1, state)
        assert await mgr.delete(meta.checkpoint_ref)
        assert not await mgr.delete(meta.checkpoint_ref)

    @pytest.mark.asyncio
    async def test_delete_all(self):
        mgr = CheckpointManager(saver=None)
        exec_id = uuid4()
        state = WorkflowState()
        await mgr.save(exec_id, "wf", "node_a", 1, state)
        await mgr.save(exec_id, "wf", "node_b", 2, state)
        count = await mgr.delete_all(exec_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_latest(self):
        mgr = CheckpointManager(saver=None)
        exec_id = uuid4()
        state = WorkflowState()
        await mgr.save(exec_id, "wf", "node_a", 1, state)
        await mgr.save(exec_id, "wf", "node_b", 2, state)
        latest = await mgr.get_latest(exec_id)
        assert latest is not None
        assert latest.step == 2

    @pytest.mark.asyncio
    async def test_get_latest_none(self):
        mgr = CheckpointManager(saver=None)
        assert await mgr.get_latest(uuid4()) is None


# ---------------------------------------------------------------------------
# Event emitter tests
# ---------------------------------------------------------------------------
class TestWorkflowEventEmitter:
    @pytest.mark.asyncio
    async def test_emit_without_bus(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit("TestEvent", {"key": "value"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_workflow_started(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_workflow_started(uuid4(), "test_wf")
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_workflow_completed(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_workflow_completed(uuid4(), "test_wf", 10.0, 0.05, 500)
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_workflow_failed(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_workflow_failed(uuid4(), "test_wf", "error", "node_a")
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_node_events(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_node_started(uuid4(), "node_a", "test")
        await emitter.emit_node_completed(uuid4(), "node_a", 100, 0.01, 50)
        await emitter.emit_node_failed(uuid4(), "node_a", "error", 2)
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_checkpoint_saved(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_checkpoint_saved(uuid4(), "ref1", "node_a", 1)
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_retry_triggered(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_retry_triggered(uuid4(), "node_a", 1, 2.0, "error")
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_cancellation_requested(self):
        emitter = WorkflowEventEmitter(event_bus=None)
        await emitter.emit_cancellation_requested(uuid4(), "user request")
        # Should not raise


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------
class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        engine = WorkflowEngine()
        engine.register_workflow(SimpleTestGraph())
        state = WorkflowState()
        result = await engine.execute("test_workflow", state)
        assert result.success
        assert result.workflow_id == "test_workflow:1.0.0"
        assert result.execution_id is not None

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        engine = WorkflowEngine()
        state = WorkflowState()
        with pytest.raises(WorkflowNotFoundError):
            await engine.execute("nonexistent", state)

    @pytest.mark.asyncio
    async def test_cancel(self):
        engine = WorkflowEngine()
        engine.register_workflow(SimpleTestGraph())
        state = WorkflowState()
        exec_id = uuid4()
        # Can't easily test async cancellation, but test the API
        result = await engine.cancel(exec_id)
        assert result is False  # not active

    @pytest.mark.asyncio
    async def test_active_execution_count(self):
        engine = WorkflowEngine()
        assert engine.active_execution_count == 0
        engine.register_workflow(SimpleTestGraph())
        state = WorkflowState()
        await engine.execute("test_workflow", state)
        assert engine.active_execution_count == 0  # completed

    @pytest.mark.asyncio
    async def test_execution_with_repositories(self):
        engine = WorkflowEngine()
        engine.register_workflow(SimpleTestGraph())
        state = WorkflowState()
        result = await engine.execute(
            "test_workflow", state,
            repositories={"project": "repo"},
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_get_execution_history(self):
        engine = WorkflowEngine()
        engine.register_workflow(SimpleTestGraph())
        state = WorkflowState()
        result = await engine.execute("test_workflow", state)
        history = engine.get_execution_history(result.state)
        assert len(history) >= 1


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------
class TestWorkflowBuilder:
    def test_build_simple(self):
        node_a = EchoNode("a")
        node_b = EchoNode("b")
        graph = (
            WorkflowBuilder("builder_test")
            .description("Test builder")
            .content_type("test")
            .add_node(node_a, is_entry=True)
            .add_node(node_b, is_exit=True)
            .add_edge("a", "b")
            .build()
        )
        assert graph.metadata.name == "builder_test"
        assert graph.metadata.entry_node == "a"
        assert "b" in graph.metadata.exit_nodes

    def test_build_with_conditional(self):
        node_a = EchoNode("a")
        node_b = EchoNode("b")
        node_c = EchoNode("c")
        graph = (
            WorkflowBuilder("conditional_test")
            .add_node(node_a, is_entry=True)
            .add_node(node_b, is_exit=True)
            .add_node(node_c, is_exit=True)
            .add_conditional("a", "b", lambda s: True, "cond1")
            .add_conditional("a", "c", lambda s: False, "cond2")
            .build()
        )
        assert graph.metadata.name == "conditional_test"

    def test_build_with_parallel(self):
        node_a = EchoNode("a")
        node_b = EchoNode("b")
        node_c = EchoNode("c")
        graph = (
            WorkflowBuilder("parallel_test")
            .add_node(node_a, is_entry=True)
            .add_node(node_b)
            .add_node(node_c, is_exit=True)
            .add_parallel("a", ["b", "c"])
            .build()
        )
        assert graph.metadata.name == "parallel_test"

    def test_build_with_tags(self):
        graph = (
            WorkflowBuilder("tagged")
            .tags(["test", "unit"])
            .add_node(EchoNode("a"), is_entry=True, is_exit=True)
            .build()
        )
        assert "test" in graph.metadata.tags

    def test_build_empty_raises(self):
        with pytest.raises(ValueError, match="no nodes"):
            WorkflowBuilder("empty").build()

    def test_build_no_entry_raises(self):
        with pytest.raises(ValueError, match="No entry node"):
            WorkflowBuilder("no_entry").add_node(EchoNode("a")).build()

    @pytest.mark.asyncio
    async def test_built_graph_executes(self):
        graph = (
            WorkflowBuilder("exec_test")
            .add_node(EchoNode("a"), is_entry=True)
            .add_node(EchoNode("b"), is_exit=True)
            .add_edge("a", "b")
            .build()
        )
        ctx = WorkflowContext()
        state = WorkflowState()
        result = await graph.execute(ctx, state)
        assert result.execution.completed_steps >= 1


# ---------------------------------------------------------------------------
# Exception classification tests
# ---------------------------------------------------------------------------
class TestErrorClassification:
    def test_validation_error(self):
        from src.core.exceptions import ValidationError
        assert classify_error(ValidationError("f", "v")) == ErrorSeverity.VALIDATION

    def test_provider_error(self):
        from src.core.exceptions import AIProviderError
        assert classify_error(AIProviderError("gemini", "err")) == ErrorSeverity.PROVIDER

    def test_infrastructure_error(self):
        from src.core.exceptions import InfrastructureError
        assert classify_error(InfrastructureError("err")) == ErrorSeverity.RETRYABLE

    def test_node_execution_error(self):
        assert classify_error(NodeExecutionError("node", "err")) == ErrorSeverity.RETRYABLE

    def test_generic_error_is_fatal(self):
        assert classify_error(ValueError("err")) == ErrorSeverity.FATAL


# ---------------------------------------------------------------------------
# State extension tests
# ---------------------------------------------------------------------------
class TestStateExtensions:
    def test_node_execution_record(self):
        record = NodeExecutionRecord(
            node_name="test",
            status="succeeded",
            execution_time_ms=100,
        )
        assert record.node_name == "test"
        assert record.duration_seconds == 0.0  # no timestamps

    def test_workflow_metadata(self):
        meta = WorkflowMetadata(workflow_name="test", workflow_version="2.0.0")
        assert meta.workflow_name == "test"
        assert meta.workflow_version == "2.0.0"

    def test_execution_status_node_history(self):
        status = ExecutionStatus()
        record = NodeExecutionRecord(node_name="test", status="succeeded")
        status.record_node(record)
        assert len(status.node_history) == 1
        assert status.get_node_history("test")[0].node_name == "test"

    def test_execution_status_mark_completed(self):
        status = ExecutionStatus()
        status.mark_completed()
        assert status.completed_at is not None

    def test_execution_status_is_running(self):
        status = ExecutionStatus()
        assert not status.is_running
        status.current_node = "node_a"
        assert status.is_running

    def test_workflow_state_execution_id(self):
        state = WorkflowState()
        assert state.execution_id is not None
        assert state.workflow_id == ""
        assert state.correlation_id is None

    def test_workflow_state_total_cost(self):
        state = WorkflowState()
        state.add_cost(0.05, "llm")
        assert state.total_cost_usd == 0.05

    def test_workflow_state_total_tokens(self):
        state = WorkflowState()
        state.add_tokens(input_t=100, output_t=50)
        assert state.total_tokens == 150

    def test_workflow_state_execution_time(self):
        state = WorkflowState()
        assert state.execution_time_seconds >= 0
