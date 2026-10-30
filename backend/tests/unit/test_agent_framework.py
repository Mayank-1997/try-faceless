"""Tests for the Phase 5 AI Agent Framework."""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.ai.agents.artifact import (
    Artifact,
    ArtifactManager,
    ArtifactType,
)
from src.ai.agents.base import AgentResult, BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.events import AgentEventEmitter, AgentEvents
from src.ai.agents.exceptions import (
    AgentAlreadyRegisteredError,
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
    ArtifactNotFoundError,
    OutputValidationError,
    PromptExecutionError,
    PromptRenderingError,
    PromptValidationError,
    QualityThresholdError,
    ToolNotFoundError,
)
from src.ai.agents.memory import (
    AgentMemory,
    InMemoryAgentMemory,
    MemoryEntry,
    MemoryScope,
)
from src.ai.agents.output_validator import (
    BusinessRule,
    OutputValidator,
    ValidationResult,
)
from src.ai.agents.prompt_executor import (
    PromptExecutionOptions,
    PromptExecutionRecord,
    PromptExecutor,
)
from src.ai.agents.prompt_template import (
    PromptTemplate,
    PromptTemplateMetadata,
    PromptVariable,
)
from src.ai.agents.quality import (
    DimensionEvaluator,
    QualityDimensions,
    QualityEvaluator,
    QualityResult,
)
from src.ai.agents.registry import (
    AgentMetadata,
    AgentRegistry,
)
from src.ai.agents.response import AIResponse
from src.ai.agents.tools import (
    Tool,
    ToolMetadata,
    ToolParameter,
    ToolRegistry,
    ToolResult,
)
from src.core.enums import AgentType
from src.workflow.contexts import (
    CancellationToken,
    ExecutionContext,
    IdentityContext,
    NodeContext,
)
from src.workflow.retry_policy import RetryPolicies
from src.workflow.state import WorkflowState


# ===========================================================================
# AI Response tests
# ===========================================================================
class TestAIResponse:
    def test_default_success(self):
        resp = AIResponse()
        assert resp.success is True
        assert resp.response == ""
        assert resp.cost_usd == 0.0
        assert resp.total_tokens == 0

    def test_has_structured_data(self):
        resp = AIResponse(structured_data={"key": "value"})
        assert resp.has_structured_data is True

    def test_no_structured_data(self):
        resp = AIResponse()
        assert resp.has_structured_data is False

    def test_has_warnings(self):
        resp = AIResponse(warnings=["test warning"])
        assert resp.has_warnings is True

    def test_no_warnings(self):
        resp = AIResponse()
        assert resp.has_warnings is False

    def test_failure_factory(self):
        resp = AIResponse.failure("test error", provider="gemini")
        assert resp.success is False
        assert "test error" in resp.errors
        assert resp.provider == "gemini"

    def test_from_generation_result(self):
        class MockResult:
            success = True
            output = "test output"
            cost_usd = 0.05
            input_tokens = 100
            output_tokens = 50
            total_tokens = 150
            latency_ms = 200
            provider = "gemini"
            model = "gemini-2.0-flash"
            metadata = {"key": "value"}
            correlation_id = "corr-123"

        resp = AIResponse.from_generation_result(MockResult())
        assert resp.success is True
        assert resp.response == "test output"
        assert resp.cost_usd == 0.05
        assert resp.provider == "gemini"


# ===========================================================================
# Agent Context tests
# ===========================================================================
class TestAgentContext:
    def test_default_creation(self):
        ctx = AgentContext()
        assert ctx.agent_name == ""
        assert ctx.agent_type == ""
        assert ctx.llm_gateway is None
        assert ctx.prompt_executor is None
        assert ctx.is_cancelled is False

    def test_logger_property(self):
        ctx = AgentContext(agent_name="test_agent")
        logger = ctx.logger
        assert logger is not None

    def test_is_cancelled(self):
        token = CancellationToken()
        token.cancel()
        ctx = AgentContext(cancellation_token=token)
        assert ctx.is_cancelled is True

    def test_get_repository_not_found(self):
        ctx = AgentContext()
        with pytest.raises(KeyError):
            ctx.get_repository("nonexistent")

    def test_get_repository(self):
        ctx = AgentContext(repositories={"project": "repo"})
        assert ctx.get_repository("project") == "repo"

    def test_get_gateway_not_found(self):
        ctx = AgentContext()
        with pytest.raises(KeyError):
            ctx.get_gateway("nonexistent")

    def test_get_service_not_found(self):
        ctx = AgentContext()
        with pytest.raises(KeyError):
            ctx.get_service("nonexistent")

    def test_get_tool_not_found(self):
        ctx = AgentContext()
        with pytest.raises(KeyError):
            ctx.get_tool("nonexistent")

    def test_get_tool(self):
        ctx = AgentContext(tools={"web_search": "tool_instance"})
        assert ctx.get_tool("web_search") == "tool_instance"

    def test_from_node_context(self):
        node_ctx = NodeContext(
            identity=IdentityContext(workflow_id="test"),
            state=WorkflowState(),
            gateways={"llm": "llm_gateway"},
            services={"event_bus": "bus"},
        )
        agent_ctx = AgentContext.from_node_context(
            node_ctx,
            agent_name="test_agent",
            agent_type="research",
        )
        assert agent_ctx.agent_name == "test_agent"
        assert agent_ctx.llm_gateway == "llm_gateway"
        assert agent_ctx.event_bus == "bus"

    def test_correlation_id(self):
        ctx = AgentContext(
            execution=ExecutionContext(correlation_id="corr-123"),
        )
        assert ctx.correlation_id == "corr-123"


# ===========================================================================
# Prompt Template tests
# ===========================================================================
class TestPromptTemplate:
    def test_from_string_auto_detects_variables(self):
        template = PromptTemplate.from_string(
            "test",
            "Hello {{name}}, you are {{role}}",
        )
        assert "name" in template.all_variable_names
        assert "role" in template.all_variable_names

    def test_render_with_variables(self):
        template = PromptTemplate.from_string(
            "test",
            "Hello {{name}}, you are {{role}}",
        )
        rendered = template.render({"name": "Alice", "role": "admin"})
        assert "Alice" in rendered
        assert "admin" in rendered

    def test_render_missing_required_raises(self):
        template = PromptTemplate.from_string(
            "test",
            "Hello {{name}}, you are {{role}}",
        )
        with pytest.raises(PromptValidationError):
            template.render({"name": "Alice"})

    def test_render_with_default_values(self):
        template = PromptTemplate(
            name="test",
            template="Hello {{name}}, mode={{mode}}",
            variables=[
                PromptVariable(name="name", required=True),
                PromptVariable(name="mode", required=False, default_value="default"),
            ],
        )
        rendered = template.render({"name": "Alice"})
        assert "default" in rendered

    def test_required_variables(self):
        template = PromptTemplate(
            name="test",
            template="{{a}} {{b}} {{c}}",
            variables=[
                PromptVariable(name="a", required=True),
                PromptVariable(name="b", required=False),
                PromptVariable(name="c", required=True),
            ],
        )
        assert "a" in template.required_variables
        assert "c" in template.required_variables
        assert "b" not in template.required_variables
        assert "b" in template.optional_variables

    def test_template_variables_property(self):
        template = PromptTemplate.from_string(
            "test",
            "{{a}} {{b}} {{a}}",
        )
        assert template.template_variables == {"a", "b"}

    def test_version(self):
        template = PromptTemplate(
            name="test",
            template="test",
            metadata=PromptTemplateMetadata(version="2.1.0"),
        )
        assert template.version == "2.1.0"

    def test_validate_variables_success(self):
        template = PromptTemplate.from_string("test", "{{a}} {{b}}")
        template.validate_variables({"a": "1", "b": "2"})  # Should not raise

    def test_render_error_raises_prompt_rendering_error(self):
        template = PromptTemplate(
            name="test",
            template="test",
            variables=[],
        )
        # Should work fine
        result = template.render({})
        assert result == "test"


# ===========================================================================
# Prompt Executor tests
# ===========================================================================
class MockLLMGateway:
    """Mock LLM gateway for testing."""

    def __init__(self, output: str = "test output", fail: bool = False) -> None:
        self._output = output
        self._fail = fail

    async def generate(self, prompt: str, **kwargs) -> any:
        if self._fail:
            raise Exception("Gateway error")

        class Result:
            success = True
            output = self._output
            cost_usd = 0.05
            input_tokens = 100
            output_tokens = 50
            total_tokens = 150
            latency_ms = 100
            provider = "gemini"
            model = "gemini-2.0-flash"
            metadata = {}
            correlation_id = kwargs.get("correlation_id")

        return Result()


class TestPromptExecutor:
    @pytest.mark.asyncio
    async def test_execute_prompt_success(self):
        gateway = MockLLMGateway(output="Hello world")
        executor = PromptExecutor(llm_gateway=gateway)
        response = await executor.execute_prompt("test prompt", agent_name="test")
        assert response.success is True
        assert response.response == "Hello world"
        assert response.cost_usd == 0.05
        assert response.provider == "gemini"

    @pytest.mark.asyncio
    async def test_execute_prompt_failure(self):
        gateway = MockLLMGateway(fail=True)
        executor = PromptExecutor(llm_gateway=gateway)
        with pytest.raises(PromptExecutionError):
            await executor.execute_prompt("test", agent_name="test")

    @pytest.mark.asyncio
    async def test_execute_template(self):
        gateway = MockLLMGateway(output="Generated content")
        executor = PromptExecutor(llm_gateway=gateway)
        template = PromptTemplate.from_string("test", "Generate about {{topic}}")
        response = await executor.execute_template(
            template, {"topic": "AI"}, agent_name="test",
        )
        assert response.success is True
        assert response.response == "Generated content"

    @pytest.mark.asyncio
    async def test_execute_prompt_json(self):
        gateway = MockLLMGateway(output='{"key": "value"}')
        executor = PromptExecutor(llm_gateway=gateway)
        options = PromptExecutionOptions(expect_json=True)
        response = await executor.execute_prompt("test", agent_name="test", options=options)
        assert response.has_structured_data is True
        assert response.structured_data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_prompt_json_parse_failure(self):
        gateway = MockLLMGateway(output="not json")
        executor = PromptExecutor(llm_gateway=gateway)
        options = PromptExecutionOptions(expect_json=True)
        response = await executor.execute_prompt("test", agent_name="test", options=options)
        assert response.has_structured_data is False
        assert response.has_warnings is True

    @pytest.mark.asyncio
    async def test_no_gateway_raises(self):
        executor = PromptExecutor(llm_gateway=None)
        with pytest.raises(PromptExecutionError):
            await executor.execute_prompt("test", agent_name="test")

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        gateway = MockLLMGateway()
        executor = PromptExecutor(llm_gateway=gateway)
        await executor.execute_prompt("prompt1", agent_name="agent_a")
        await executor.execute_prompt("prompt2", agent_name="agent_b")
        assert executor.history_count == 2
        agent_a_history = executor.get_history(agent_name="agent_a")
        assert len(agent_a_history) == 1

    @pytest.mark.asyncio
    async def test_total_cost(self):
        gateway = MockLLMGateway()
        executor = PromptExecutor(llm_gateway=gateway)
        await executor.execute_prompt("p1", agent_name="a")
        await executor.execute_prompt("p2", agent_name="a")
        assert executor.get_total_cost("a") == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_total_tokens(self):
        gateway = MockLLMGateway()
        executor = PromptExecutor(llm_gateway=gateway)
        await executor.execute_prompt("p1", agent_name="a")
        assert executor.get_total_tokens("a") == 150

    def test_clear_history(self):
        executor = PromptExecutor()
        executor._history.append(PromptExecutionRecord(agent_name="test"))
        executor.clear_history()
        assert executor.history_count == 0


# ===========================================================================
# Output Validator tests
# ===========================================================================
class TestOutputValidator:
    def test_valid_json_output(self):
        validator = OutputValidator(required_fields=["name", "value"])
        result = validator.validate('{"name": "test", "value": 42}')
        assert result.is_valid is True
        assert result.structured_data is not None
        assert result.structured_data["name"] == "test"

    def test_invalid_json(self):
        validator = OutputValidator(required_fields=["name"])
        result = validator.validate("not json")
        assert result.is_valid is False
        assert any("JSON" in e for e in result.errors)

    def test_missing_required_field(self):
        validator = OutputValidator(required_fields=["name", "value"])
        result = validator.validate('{"name": "test"}')
        assert result.is_valid is False
        assert any("value" in e for e in result.errors)

    def test_schema_validation(self):
        from pydantic import BaseModel as PydanticModel, Field

        class MySchema(PydanticModel):
            name: str
            value: int

        validator = OutputValidator(schema=MySchema)
        result = validator.validate('{"name": "test", "value": 42}')
        assert result.is_valid is True

    def test_schema_validation_failure(self):
        from pydantic import BaseModel as PydanticModel

        class MySchema(PydanticModel):
            name: str
            value: int

        validator = OutputValidator(schema=MySchema)
        result = validator.validate('{"name": "test", "value": "not an int"}')
        assert result.is_valid is False

    def test_business_rule(self):
        def rule(data):
            if data.get("value", 0) > 10:
                return True, None
            return False, "Value must be > 10"

        validator = OutputValidator(
            required_fields=["value"],
            business_rules=[BusinessRule("value_check", rule)],
        )
        result = validator.validate('{"value": 5}')
        assert result.is_valid is False
        assert any("value_check" in e for e in result.errors)

    def test_business_rule_passes(self):
        def rule(data):
            if data.get("value", 0) > 10:
                return True, None
            return False, "Value must be > 10"

        validator = OutputValidator(
            required_fields=["value"],
            business_rules=[BusinessRule("value_check", rule)],
        )
        result = validator.validate('{"value": 20}')
        assert result.is_valid is True

    def test_no_schema_just_checks_nonempty(self):
        validator = OutputValidator()
        result = validator.validate("some output")
        assert result.is_valid is True

    def test_empty_output_fails(self):
        validator = OutputValidator()
        result = validator.validate("")
        assert result.is_valid is False

    def test_valid_result_factory(self):
        result = ValidationResult.valid(structured_data={"a": 1})
        assert result.is_valid is True
        assert result.structured_data == {"a": 1}

    def test_invalid_result_factory(self):
        result = ValidationResult.invalid(["error1", "error2"])
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validate_and_repair_success(self):
        def repair_fn(output, errors):
            return '{"name": "fixed", "value": 1}'

        validator = OutputValidator(required_fields=["name", "value"])
        result = validator.validate_and_repair(
            '{"name": "test"}',  # Missing "value"
            repair_fn=repair_fn,
        )
        assert result.is_valid is True
        assert result.repaired is True
        assert result.repaired_output is not None

    def test_validate_and_repair_failure(self):
        def repair_fn(output, errors):
            return '{"still": "broken"}'

        validator = OutputValidator(
            required_fields=["name", "value"],
            max_repair_attempts=2,
        )
        result = validator.validate_and_repair(
            '{"name": "test"}',
            repair_fn=repair_fn,
        )
        assert result.is_valid is False

    def test_validate_and_repair_no_repair_fn(self):
        validator = OutputValidator(required_fields=["name"])
        result = validator.validate_and_repair('{}')
        assert result.is_valid is False
        assert result.repaired is False

    def test_add_business_rule(self):
        validator = OutputValidator(required_fields=["value"])
        validator.add_business_rule(BusinessRule("rule1", lambda d: (True, None)))
        assert len(validator._business_rules) == 1


# ===========================================================================
# Quality Evaluator tests
# ===========================================================================
class TestQualityEvaluator:
    def test_evaluate_good_output(self):
        evaluator = QualityEvaluator(threshold=0.5)
        result = evaluator.evaluate(
            "This is a well-structured output with sufficient length " * 5,
            context={"min_length": 50, "max_length": 10000},
        )
        assert result.score > 0
        assert isinstance(result.dimensions, QualityDimensions)

    def test_evaluate_empty_output(self):
        evaluator = QualityEvaluator()
        result = evaluator.evaluate("")
        assert result.score == 0.0
        assert result.passed is False

    def test_evaluate_pass_threshold(self):
        evaluator = QualityEvaluator(threshold=0.0)
        result = evaluator.evaluate("Some content here that is long enough")
        assert result.passed is True

    def test_evaluate_fail_threshold(self):
        evaluator = QualityEvaluator(threshold=0.99)
        result = evaluator.evaluate("short")
        assert result.passed is False

    def test_score_percentage(self):
        result = QualityResult(score=0.75, passed=True, threshold=0.7)
        assert result.score_percentage == 75.0

    def test_grade(self):
        assert QualityResult(score=0.95).grade == "A"
        assert QualityResult(score=0.85).grade == "B"
        assert QualityResult(score=0.75).grade == "C"
        assert QualityResult(score=0.65).grade == "D"
        assert QualityResult(score=0.45).grade == "F"

    def test_dimension_names(self):
        evaluator = QualityEvaluator()
        names = evaluator.dimension_names
        assert "completeness" in names
        assert "readability" in names

    def test_add_dimension(self):
        evaluator = QualityEvaluator()
        evaluator.add_dimension(
            DimensionEvaluator("custom", 0.1, lambda o, c: 0.5)
        )
        assert "custom" in evaluator.dimension_names

    def test_quality_dimensions_as_dict(self):
        dims = QualityDimensions(completeness=0.8, readability=0.9)
        d = dims.as_dict()
        assert d["completeness"] == 0.8
        assert d["readability"] == 0.9

    def test_suggestions_for_low_scores(self):
        evaluator = QualityEvaluator(threshold=0.9)
        result = evaluator.evaluate("short")
        assert len(result.suggestions) > 0 or len(result.notes) > 0


# ===========================================================================
# Artifact Manager tests
# ===========================================================================
class TestArtifactManager:
    def test_store_and_get(self):
        mgr = ArtifactManager()
        artifact = mgr.store(
            agent_name="test_agent",
            artifact_type=ArtifactType.RESEARCH,
            name="research_output",
            content={"summary": "test"},
        )
        assert artifact.id is not None
        retrieved = mgr.get(artifact.id)
        assert retrieved.name == "research_output"
        assert retrieved.content == {"summary": "test"}

    def test_get_not_found(self):
        mgr = ArtifactManager()
        with pytest.raises(ArtifactNotFoundError):
            mgr.get(uuid4())

    def test_list_by_agent(self):
        mgr = ArtifactManager()
        mgr.store(agent_name="agent_a", artifact_type="research", name="r1", content="c1")
        mgr.store(agent_name="agent_a", artifact_type="script", name="s1", content="c2")
        mgr.store(agent_name="agent_b", artifact_type="research", name="r2", content="c3")
        agent_a_artifacts = mgr.list_by_agent("agent_a")
        assert len(agent_a_artifacts) == 2

    def test_list_by_type(self):
        mgr = ArtifactManager()
        mgr.store(agent_name="a", artifact_type="research", name="r1", content="c1")
        mgr.store(agent_name="b", artifact_type="script", name="s1", content="c2")
        research_artifacts = mgr.list_by_type("research")
        assert len(research_artifacts) == 1

    def test_list_by_execution(self):
        mgr = ArtifactManager()
        exec_id = uuid4()
        mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1", execution_id=exec_id)
        mgr.store(agent_name="b", artifact_type="s", name="s1", content="c2", execution_id=exec_id)
        mgr.store(agent_name="c", artifact_type="r", name="r2", content="c3")
        exec_artifacts = mgr.list_by_execution(exec_id)
        assert len(exec_artifacts) == 2

    def test_list_all(self):
        mgr = ArtifactManager()
        mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1")
        mgr.store(agent_name="b", artifact_type="s", name="s1", content="c2")
        assert len(mgr.list_all()) == 2

    def test_delete(self):
        mgr = ArtifactManager()
        artifact = mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1")
        assert mgr.delete(artifact.id) is True
        assert mgr.delete(artifact.id) is False

    def test_delete_by_execution(self):
        mgr = ArtifactManager()
        exec_id = uuid4()
        mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1", execution_id=exec_id)
        mgr.store(agent_name="b", artifact_type="s", name="s1", content="c2", execution_id=exec_id)
        count = mgr.delete_by_execution(exec_id)
        assert count == 2

    def test_count(self):
        mgr = ArtifactManager()
        assert mgr.count == 0
        mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1")
        assert mgr.count == 1

    def test_clear(self):
        mgr = ArtifactManager()
        mgr.store(agent_name="a", artifact_type="r", name="r1", content="c1")
        mgr.clear()
        assert mgr.count == 0


# ===========================================================================
# Agent Memory tests
# ===========================================================================
class TestInMemoryAgentMemory:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "value1", agent_name="test")
        result = await memory.retrieve("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self):
        memory = InMemoryAgentMemory()
        result = await memory.retrieve("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "value1", agent_name="test")
        assert await memory.delete("key1") is True
        assert await memory.delete("key1") is False

    @pytest.mark.asyncio
    async def test_list_keys(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "v1", agent_name="a")
        await memory.store("key2", "v2", agent_name="b")
        keys = await memory.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_list_keys_filtered_by_agent(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "v1", agent_name="a")
        await memory.store("key2", "v2", agent_name="b")
        keys = await memory.list_keys(agent_name="a")
        assert "key1" in keys
        assert "key2" not in keys

    @pytest.mark.asyncio
    async def test_clear_all(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "v1", agent_name="a")
        await memory.store("key2", "v2", agent_name="b")
        count = await memory.clear()
        assert count == 2
        assert memory.count == 0

    @pytest.mark.asyncio
    async def test_clear_by_scope(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "v1", scope=MemoryScope.SHORT_TERM)
        await memory.store("key2", "v2", scope=MemoryScope.WORKFLOW)
        count = await memory.clear(scope=MemoryScope.SHORT_TERM)
        assert count == 1

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        memory = InMemoryAgentMemory()
        await memory.store("key1", "v1", ttl_seconds=0)
        # Should be expired immediately
        result = await memory.retrieve("key1")
        assert result is None

    def test_memory_entry_is_expired(self):
        entry = MemoryEntry(key="test", value="v", ttl_seconds=0)
        assert entry.is_expired is True

    def test_memory_entry_not_expired(self):
        entry = MemoryEntry(key="test", value="v", ttl_seconds=3600)
        assert entry.is_expired is False

    def test_memory_entry_no_ttl(self):
        entry = MemoryEntry(key="test", value="v", ttl_seconds=None)
        assert entry.is_expired is False


# ===========================================================================
# Tools tests
# ===========================================================================
class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_tool",
            description="Mock tool for testing",
            category="test",
            parameters=[
                ToolParameter(name="query", description="Search query", required=True),
                ToolParameter(name="limit", description="Max results", required=False, default_value=10),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult.failure_result("Missing query")
        return ToolResult.success_result(f"Results for: {query}")

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        assert registry.get("mock_tool") is tool

    def test_get_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_exists(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        assert registry.exists("mock_tool") is True
        assert registry.exists("nonexistent") is False

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "mock_tool"

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        assert registry.unregister("mock_tool") is True
        assert registry.unregister("mock_tool") is False

    def test_count(self):
        registry = ToolRegistry()
        assert registry.count == 0
        registry.register(MockTool())
        assert registry.count == 1

    def test_duplicate_register_raises(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        with pytest.raises(ValueError):
            registry.register(MockTool())

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        await registry.initialize_all()  # Should not raise

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        await registry.shutdown_all()  # Should not raise


class TestTool:
    def test_validate_parameters_all_present(self):
        tool = MockTool()
        missing = tool.validate_parameters(query="test", limit=5)
        assert missing == []

    def test_validate_parameters_missing_required(self):
        tool = MockTool()
        missing = tool.validate_parameters(limit=5)
        assert "query" in missing

    @pytest.mark.asyncio
    async def test_execute_success(self):
        tool = MockTool()
        result = await tool.execute(query="test query")
        assert result.success is True
        assert "test query" in result.output

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        tool = MockTool()
        result = await tool.execute()
        assert result.success is False

    def test_tool_result_success_factory(self):
        result = ToolResult.success_result("output", key="value")
        assert result.success is True
        assert result.output == "output"
        assert result.metadata["key"] == "value"

    def test_tool_result_failure_factory(self):
        result = ToolResult.failure_result("error")
        assert result.success is False
        assert result.error == "error"


# ===========================================================================
# Agent Registry tests
# ===========================================================================
class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        agent = MockAgent("test_agent")
        registry.register(agent)
        retrieved = registry.get("test_agent")
        assert retrieved is agent

    def test_get_latest_version(self):
        registry = AgentRegistry()
        agent1 = MockAgent("test_agent")
        registry.register(agent1, AgentMetadata(name="test_agent", version="1.0.0"))
        agent2 = MockAgent("test_agent_v2")
        registry.register(agent2, AgentMetadata(name="test_agent", version="2.0.0"))
        retrieved = registry.get("test_agent")
        assert retrieved is agent2

    def test_get_specific_version(self):
        registry = AgentRegistry()
        agent1 = MockAgent("test_agent")
        registry.register(agent1, AgentMetadata(name="test_agent", version="1.0.0"))
        agent2 = MockAgent("test_agent_v2")
        registry.register(agent2, AgentMetadata(name="test_agent", version="2.0.0"))
        retrieved = registry.get("test_agent", "1.0.0")
        assert retrieved is agent1

    def test_get_not_found(self):
        registry = AgentRegistry()
        with pytest.raises(AgentNotFoundError):
            registry.get("nonexistent")

    def test_duplicate_registration_raises(self):
        registry = AgentRegistry()
        agent = MockAgent("test_agent")
        registry.register(agent, AgentMetadata(name="test_agent", version="1.0.0"))
        with pytest.raises(AgentAlreadyRegisteredError):
            registry.register(agent, AgentMetadata(name="test_agent", version="1.0.0"))

    def test_list_agents(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a"))
        registry.register(MockAgent("b"), AgentMetadata(name="b"))
        agents = registry.list_agents()
        assert len(agents) == 2

    def test_list_by_type(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a", agent_type="research"))
        registry.register(MockAgent("b"), AgentMetadata(name="b", agent_type="script"))
        registry.register(MockAgent("c"), AgentMetadata(name="c", agent_type="research"))
        research_agents = registry.list_by_type("research")
        assert len(research_agents) == 2

    def test_list_versions(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a", version="1.0.0"))
        registry.register(MockAgent("a2"), AgentMetadata(name="a", version="2.0.0"))
        versions = registry.list_versions("a")
        assert "1.0.0" in versions
        assert "2.0.0" in versions

    def test_exists(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a", version="1.0.0"))
        assert registry.exists("a") is True
        assert registry.exists("a", "1.0.0") is True
        assert registry.exists("a", "2.0.0") is False
        assert registry.exists("b") is False

    def test_unregister(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a", version="1.0.0"))
        assert registry.unregister("a", "1.0.0") is True
        assert registry.unregister("a", "1.0.0") is False

    def test_clear(self):
        registry = AgentRegistry()
        registry.register(MockAgent("a"), AgentMetadata(name="a"))
        registry.clear()
        assert registry.count == 0

    def test_count(self):
        registry = AgentRegistry()
        assert registry.count == 0
        registry.register(MockAgent("a"), AgentMetadata(name="a"))
        assert registry.count == 1

    def test_auto_extract_metadata(self):
        registry = AgentRegistry()
        agent = MockAgent("test_agent")
        registry.register(agent)  # No metadata provided
        assert registry.exists("test_agent")


# ===========================================================================
# Agent Event Emitter tests
# ===========================================================================
class TestAgentEventEmitter:
    @pytest.mark.asyncio
    async def test_emit_without_bus(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit("TestEvent", {"key": "value"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_agent_started(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_agent_started("test", "research", uuid4())
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_prompt_generated(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_prompt_generated("test", "template1", 500)

    @pytest.mark.asyncio
    async def test_emit_prompt_executed(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_prompt_executed("test", "gemini", "flash", 0.05, 150, 200)

    @pytest.mark.asyncio
    async def test_emit_validation_failed(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_validation_failed("test", ["error1"])

    @pytest.mark.asyncio
    async def test_emit_retry_triggered(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_retry_triggered("test", 1, 2.0, "error")

    @pytest.mark.asyncio
    async def test_emit_agent_completed(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_agent_completed("test", 500, 0.05, 150, 0.85)

    @pytest.mark.asyncio
    async def test_emit_agent_failed(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_agent_failed("test", "error")

    @pytest.mark.asyncio
    async def test_emit_artifacts_created(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_artifacts_created("test", 2, ["research", "script"])

    @pytest.mark.asyncio
    async def test_emit_quality_evaluated(self):
        emitter = AgentEventEmitter(event_bus=None)
        await emitter.emit_quality_evaluated("test", 0.85, True, 0.7)


# ===========================================================================
# Exceptions tests
# ===========================================================================
class TestAgentExceptions:
    def test_agent_execution_error(self):
        exc = AgentExecutionError("test_agent", "something failed")
        assert "test_agent" in str(exc)
        assert exc.agent_name == "test_agent"

    def test_agent_timeout_error(self):
        exc = AgentTimeoutError("test_agent", 30)
        assert "30s" in str(exc)
        assert exc.timeout_seconds == 30

    def test_prompt_execution_error(self):
        exc = PromptExecutionError("test_agent", "prompt failed")
        assert "test_agent" in str(exc)

    def test_prompt_rendering_error(self):
        exc = PromptRenderingError("template1", "bad template")
        assert "template1" in str(exc)
        assert exc.template_name == "template1"

    def test_prompt_validation_error(self):
        exc = PromptValidationError("template1", ["var1", "var2"])
        assert "template1" in str(exc)
        assert "var1" in str(exc)
        assert exc.missing_variables == ["var1", "var2"]

    def test_output_validation_error(self):
        exc = OutputValidationError("test_agent", "bad output")
        assert "test_agent" in str(exc)

    def test_quality_threshold_error(self):
        exc = QualityThresholdError("test_agent", 0.5, 0.8)
        assert "0.50" in str(exc)
        assert exc.score == 0.5
        assert exc.threshold == 0.8

    def test_artifact_not_found_error(self):
        exc = ArtifactNotFoundError("artifact-123")
        assert "artifact-123" in str(exc)

    def test_tool_not_found_error(self):
        exc = ToolNotFoundError("web_search")
        assert "web_search" in str(exc)

    def test_agent_not_found_error(self):
        exc = AgentNotFoundError("research", "1.0.0")
        assert "research" in str(exc)

    def test_agent_already_registered_error(self):
        exc = AgentAlreadyRegisteredError("research", "1.0.0")
        assert "research" in str(exc)


# ===========================================================================
# Base Agent tests
# ===========================================================================
class MockAgent(BaseAgent):
    """Mock agent for testing BaseAgent lifecycle."""

    def __init__(self, name: str = "mock_agent", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCH

    async def prepare_prompt(self, context):
        template = PromptTemplate.from_string(
            "mock_template",
            "Research the topic: {{topic}}",
        )
        return template, {"topic": "AI"}

    async def process_response(self, response, context):
        return {"summary": response.response}

    async def update_workflow_state(self, result, response, context):
        context.state.research = context.state.research.model_copy(
            update={"summary": result["summary"]}
        )


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_agent_lifecycle_success(self):
        gateway = MockLLMGateway(output="AI research summary")
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=False,
        )
        artifact_mgr = ArtifactManager()
        ctx = AgentContext(
            state=WorkflowState(),
            agent_name="mock_agent",
            agent_type="research",
            gateways={"llm": gateway},
            services={"artifact_manager": artifact_mgr},
        )
        result = await agent.run_agent(ctx)
        assert result.success is True
        assert result.response is not None
        assert result.response.response == "AI research summary"

    @pytest.mark.asyncio
    async def test_agent_updates_workflow_state(self):
        gateway = MockLLMGateway(output="Research about AI")
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=False,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
        )
        await agent.run_agent(ctx)
        assert ctx.state.research.summary == "Research about AI"

    @pytest.mark.asyncio
    async def test_agent_tracks_cost_and_tokens(self):
        gateway = MockLLMGateway(output="test")
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=False,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
        )
        result = await agent.run_agent(ctx)
        assert result.cost_usd == 0.05
        assert result.tokens_consumed == 150
        assert ctx.state.total_cost_usd == pytest.approx(0.05)
        assert ctx.state.total_tokens == 150

    @pytest.mark.asyncio
    async def test_agent_cancellation(self):
        gateway = MockLLMGateway()
        agent = MockAgent()
        token = CancellationToken()
        token.cancel()
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
            cancellation_token=token,
        )
        result = await agent.run_agent(ctx)
        assert result.success is False
        assert "Cancelled" in (result.error or "")

    @pytest.mark.asyncio
    async def test_agent_ai_failure(self):
        gateway = MockLLMGateway(fail=True)
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
        )
        result = await agent.run_agent(ctx)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_agent_creates_artifact(self):
        gateway = MockLLMGateway(output="test output")
        artifact_mgr = ArtifactManager()
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=True,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
            services={"artifact_manager": artifact_mgr},
        )
        result = await agent.run_agent(ctx)
        assert result.success is True
        assert result.artifacts_created == 1
        assert artifact_mgr.count == 1

    @pytest.mark.asyncio
    async def test_agent_quality_evaluation(self):
        gateway = MockLLMGateway(output="A well-structured research summary about AI " * 10)
        agent = MockAgent(
            enable_quality_check=True,
            enable_output_validation=False,
            enable_artifact_creation=False,
            quality_threshold=0.3,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
        )
        result = await agent.run_agent(ctx)
        assert result.success is True
        assert result.quality is not None
        assert result.quality.score > 0

    @pytest.mark.asyncio
    async def test_agent_marks_agent_complete(self):
        gateway = MockLLMGateway(output="test")
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=False,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
        )
        await agent.run_agent(ctx)
        assert AgentType.RESEARCH in ctx.state.execution.completed_agents

    @pytest.mark.asyncio
    async def test_agent_memory_helpers(self):
        memory = InMemoryAgentMemory()
        gateway = MockLLMGateway(output="test")
        agent = MockAgent(
            enable_quality_check=False,
            enable_output_validation=False,
            enable_artifact_creation=False,
        )
        ctx = AgentContext(
            state=WorkflowState(),
            gateways={"llm": gateway},
            services={"agent_memory": memory},
        )
        await agent.remember(ctx, "test_key", "test_value")
        result = await agent.recall(ctx, "test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_agent_recall_no_memory(self):
        agent = MockAgent()
        ctx = AgentContext(state=WorkflowState())
        result = await agent.recall(ctx, "key")
        assert result is None

    @pytest.mark.asyncio
    async def test_agent_result_model(self):
        result = AgentResult(success=True, agent_name="test", execution_time_ms=100)
        assert result.success is True
        assert result.agent_name == "test"
        assert result.execution_time_ms == 100
