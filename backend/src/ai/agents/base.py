"""Base agent — abstract foundation for all AI agents.

Every future AI agent (ResearchAgent, ScriptAgent, ScenePlanner, etc.)
must inherit from ``BaseAgent``.  It extends the workflow ``BaseNode``
with AI-specific concerns:

- Prompt execution via ``PromptExecutor``
- Output validation via ``OutputValidator``
- Quality evaluation via ``QualityEvaluator``
- Artifact management via ``ArtifactManager``
- Agent memory via ``AgentMemory``
- Agent lifecycle events via ``AgentEventEmitter``
- Cost and token tracking
- Workflow state updates

Agent Lifecycle::

    Initialize
        ↓
    Validate Input
        ↓
    Prepare Prompt
        ↓
    Execute AI
        ↓
    Validate Output
        ↓
    Evaluate Quality
        ↓
    Persist Result (Artifacts)
        ↓
    Emit Events
        ↓
    Update Workflow State
        ↓
    Return Result

Subclasses implement:
    - ``prepare_prompt``: Build the prompt template and variables.
    - ``process_response``: Extract and structure the AI response.
    - ``update_workflow_state``: Update ``WorkflowState`` with results.

Subclasses may override:
    - ``output_schema``: Pydantic model for output validation.
    - ``quality_threshold``: Minimum quality score (default 0.7).
    - ``retry_policy``: Retry policy for AI calls.
    - ``on_initialize``: Custom initialization.
    - ``on_before_ai_call``: Pre-AI-call hook.
    - ``on_after_ai_call``: Post-AI-call hook.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from src.ai.agents.artifact import ArtifactManager, ArtifactType
from src.ai.agents.context import AgentContext
from src.ai.agents.events import AgentEventEmitter
from src.ai.agents.exceptions import (
    AgentExecutionError,
    OutputValidationError,
    QualityThresholdError,
)
from src.ai.agents.memory import AgentMemory, MemoryScope
from src.ai.agents.output_validator import OutputValidator, ValidationResult
from src.ai.agents.prompt_executor import PromptExecutor, PromptExecutionOptions
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.quality import QualityEvaluator, QualityResult
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.core.logging import get_logger
from src.workflow.base_node import BaseNode
from src.workflow.contexts import NodeContext
from src.workflow.retry_policy import RetryPolicy, RetryPolicies
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------
class AgentResult(BaseModel):
    """Result of an agent execution.

    Attributes:
        success: Whether the agent succeeded.
        agent_name: The agent name.
        response: The AI response.
        quality: The quality evaluation result.
        validation: The output validation result.
        artifacts_created: Number of artifacts created.
        execution_time_ms: Total execution time in milliseconds.
        cost_usd: Total cost in USD.
        tokens_consumed: Total tokens consumed.
        error: Error message if failed.
    """

    success: bool = True
    agent_name: str = ""
    response: AIResponse | None = None
    quality: QualityResult | None = None
    validation: ValidationResult | None = None
    artifacts_created: int = 0
    execution_time_ms: int = 0
    cost_usd: float = 0.0
    tokens_consumed: int = 0
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------
class BaseAgent(BaseNode):
    """Abstract base class for all AI agents.

    Extends ``BaseNode`` with AI-specific lifecycle management.
    Agents are nodes that call AI providers, validate output,
    evaluate quality, and create artifacts.

    Subclasses must implement:
        - ``agent_type``: Return the ``AgentType`` enum value.
        - ``prepare_prompt``: Build the prompt template and variables.
        - ``process_response``: Extract structured data from AI response.
        - ``update_workflow_state``: Update state with agent results.

    Attributes:
        quality_threshold: Minimum quality score to pass (0.0–1.0).
        enable_quality_check: Whether to run quality evaluation.
        enable_output_validation: Whether to validate output.
        enable_artifact_creation: Whether to create artifacts.
    """

    def __init__(
        self,
        name: str | None = None,
        *,
        retry_policy: RetryPolicy | None = None,
        quality_threshold: float = 0.7,
        enable_quality_check: bool = True,
        enable_output_validation: bool = True,
        enable_artifact_creation: bool = True,
    ) -> None:
        """Initialize the base agent.

        Args:
            name: Agent name. If None, uses the class name lowercased.
            retry_policy: Retry policy for AI calls.
            quality_threshold: Minimum quality score to pass.
            enable_quality_check: Whether to run quality evaluation.
            enable_output_validation: Whether to validate output.
            enable_artifact_creation: Whether to create artifacts.
        """
        super().__init__(
            name=name,
            node_type="agent",
            retry_policy=retry_policy or RetryPolicies.PROVIDER,
        )
        self.quality_threshold = quality_threshold
        self.enable_quality_check = enable_quality_check
        self.enable_output_validation = enable_output_validation
        self.enable_artifact_creation = enable_artifact_creation
        self._agent_logger = get_logger(f"agent.{self.name}")

    # -----------------------------------------------------------------------
    # Properties for subclasses to override
    # -----------------------------------------------------------------------
    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the ``AgentType`` enum value for this agent."""
        ...

    @property
    def output_validator_config(self) -> dict[str, Any]:
        """Configuration for the output validator.

        Override in subclasses to customize validation.

        Returns:
            Dictionary with keys: ``schema``, ``required_fields``,
            ``business_rules``, ``max_repair_attempts``.
        """
        return {}

    # -----------------------------------------------------------------------
    # Abstract methods — subclass responsibilities
    # -----------------------------------------------------------------------
    @abstractmethod
    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        """Prepare the prompt template and variables for AI execution.

        Args:
            context: The agent context with state and dependencies.

        Returns:
            A tuple of (PromptTemplate, variables_dict).
        """
        ...

    @abstractmethod
    async def process_response(
        self,
        response: AIResponse,
        context: AgentContext,
    ) -> Any:
        """Process the AI response into structured data.

        Args:
            response: The AI response from the prompt executor.
            context: The agent context.

        Returns:
            The processed result (type depends on the agent).
        """
        ...

    @abstractmethod
    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        """Update the workflow state with agent results.

        Args:
            result: The processed result from ``process_response``.
            response: The original AI response.
            context: The agent context.
        """
        ...

    # -----------------------------------------------------------------------
    # Lifecycle hooks (override in subclasses)
    # -----------------------------------------------------------------------
    async def on_initialize(self, context: AgentContext) -> None:
        """Called before agent execution begins. Override for custom setup."""
        pass

    async def on_before_ai_call(self, context: AgentContext) -> None:
        """Called before the AI call. Override for custom pre-processing."""
        pass

    async def on_after_ai_call(
        self,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        """Called after the AI call succeeds. Override for custom post-processing."""
        pass

    async def on_quality_evaluated(
        self,
        quality: QualityResult,
        context: AgentContext,
    ) -> None:
        """Called after quality evaluation. Override for custom handling."""
        pass

    async def on_artifacts_created(
        self,
        artifacts: list[Any],
        context: AgentContext,
    ) -> None:
        """Called after artifacts are created. Override for custom handling."""
        pass

    # -----------------------------------------------------------------------
    # Main execution method
    # -----------------------------------------------------------------------
    async def execute(self, context: NodeContext) -> WorkflowState:
        """Execute the agent's core logic.

        This method is called by the workflow engine via ``BaseNode.run``.
        It converts the ``NodeContext`` to an ``AgentContext`` and
        delegates to ``run_agent``.

        Args:
            context: The node context from the workflow engine.

        Returns:
            The updated ``WorkflowState``.
        """
        # Convert NodeContext to AgentContext
        agent_context = self._create_agent_context(context)

        result = await self.run_agent(agent_context)

        if not result.success and result.error:
            raise AgentExecutionError(self.name, result.error)

        return context.state

    async def run_agent(self, context: AgentContext) -> AgentResult:
        """Run the complete agent lifecycle.

        This is the main entry point for agent execution.  It handles
        the full lifecycle: initialize → validate → prompt → execute AI →
        validate output → evaluate quality → persist → emit events →
        update state.

        Args:
            context: The agent context with all dependencies.

        Returns:
            An ``AgentResult`` with execution details.
        """
        started_at = datetime.now(timezone.utc)
        logger = context.logger
        corr_id = context.correlation_id

        # Create event emitter
        event_emitter = AgentEventEmitter(context.event_bus)

        # Emit AgentStarted
        await event_emitter.emit_agent_started(
            self.name, self.agent_type.value, context.identity.execution_id,
            correlation_id=corr_id,
        )

        # Initialize
        await self.on_initialize(context)
        logger.info("agent_initialized", agent=self.name)

        # Check cancellation
        if context.is_cancelled:
            logger.info("agent_cancelled", agent=self.name)
            return AgentResult(
                success=False,
                agent_name=self.name,
                error="Cancelled",
            )

        try:
            # Step 1: Prepare prompt
            template, variables = await self.prepare_prompt(context)
            logger.info(
                "prompt_prepared",
                agent=self.name,
                template=template.name,
                variables=list(variables.keys()),
            )

            # Emit PromptGenerated
            await event_emitter.emit_prompt_generated(
                self.name, template.name, len(template.template),
                correlation_id=corr_id,
            )

            # Step 2: Pre-AI hook
            await self.on_before_ai_call(context)

            # Step 3: Execute AI
            prompt_executor = context.prompt_executor or PromptExecutor(
                llm_gateway=context.llm_gateway or context.gateways.get("llm"),
                langfuse_client=context.services.get("langfuse_client") if context.services else None,
            )

            # Attach to the workflow-level Langfuse trace when one exists,
            # so every agent LLM call groups under a single trace per run.
            workflow_trace_id = None
            try:
                workflow_trace_id = context.state.metadata.custom.get("langfuse_trace_id")
            except (AttributeError, KeyError):
                workflow_trace_id = None

            options = PromptExecutionOptions(
                correlation_id=corr_id,
                expect_json=self.enable_output_validation,
                trace_id=workflow_trace_id,
            )

            response = await prompt_executor.execute_template(
                template, variables,
                agent_name=self.name,
                options=options,
            )

            if not response.success:
                error_msg = "; ".join(response.errors) if response.errors else "AI call failed"
                logger.error("agent_ai_failed", agent=self.name, error=error_msg)
                await event_emitter.emit_agent_failed(
                    self.name, error_msg, correlation_id=corr_id,
                )
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    response=response,
                    error=error_msg,
                )

            # Emit PromptExecuted
            await event_emitter.emit_prompt_executed(
                self.name, response.provider, response.model,
                response.cost_usd, response.total_tokens, response.latency_ms,
                correlation_id=corr_id,
            )

            # Step 4: Post-AI hook
            await self.on_after_ai_call(response, context)

            # Track cost and tokens
            context.state.add_cost(response.cost_usd, "llm")
            context.state.add_tokens(
                input_t=response.input_tokens,
                output_t=response.output_tokens,
            )

            # Step 5: Validate output
            validation_result: ValidationResult | None = None
            if self.enable_output_validation:
                validator = context.output_validator or self._create_output_validator()
                validation_result = validator.validate(response.response)

                if not validation_result.is_valid:
                    logger.warning(
                        "agent_output_validation_failed",
                        agent=self.name,
                        errors=validation_result.errors,
                    )
                    await event_emitter.emit_validation_failed(
                        self.name, validation_result.errors,
                        correlation_id=corr_id,
                    )
                    # Don't raise — continue with whatever structured data we
                    # could extract (or an empty dict) so that
                    # ``process_response`` and ``update_workflow_state`` still
                    # run.  This prevents a single JSON parse error from wiping
                    # out all downstream state (e.g. the entire script or
                    # storyboard package).  Agents are expected to handle empty
                    # / partial data gracefully in ``update_workflow_state``.
                    if response.structured_data is None:
                        response.structured_data = (
                            validation_result.structured_data or {}
                        )

            # Step 6: Process response
            processed_result = await self.process_response(response, context)

            # Step 7: Evaluate quality
            quality_result: QualityResult | None = None
            if self.enable_quality_check:
                evaluator = context.quality_evaluator or QualityEvaluator(
                    threshold=self.quality_threshold,
                )
                quality_result = evaluator.evaluate(
                    response.response,
                    context={"prompt": template.template},
                )

                await event_emitter.emit_quality_evaluated(
                    self.name, quality_result.score, quality_result.passed,
                    self.quality_threshold,
                    correlation_id=corr_id,
                )

                await self.on_quality_evaluated(quality_result, context)

                if not quality_result.passed:
                    logger.warning(
                        "agent_quality_below_threshold",
                        agent=self.name,
                        score=quality_result.score,
                        threshold=self.quality_threshold,
                    )

            # Step 8: Create artifacts
            artifacts_created = 0
            artifact_mgr = context.artifact_manager or context.services.get("artifact_manager")
            if self.enable_artifact_creation and artifact_mgr:
                artifact = artifact_mgr.store(
                    agent_name=self.name,
                    artifact_type=ArtifactType.PROMPT_OUTPUT,
                    name=f"{self.name}_output",
                    content=processed_result,
                    metadata={
                        "provider": response.provider,
                        "model": response.model,
                        "quality_score": quality_result.score if quality_result else None,
                    },
                    project_id=context.identity.project_id,
                    execution_id=context.identity.execution_id,
                )
                artifacts_created = 1
                await self.on_artifacts_created([artifact], context)

                await event_emitter.emit_artifacts_created(
                    self.name, artifacts_created, [ArtifactType.PROMPT_OUTPUT],
                    correlation_id=corr_id,
                )

            # Step 9: Update workflow state
            await self.update_workflow_state(processed_result, response, context)

            # Mark agent complete
            context.state.execution.mark_agent_complete(self.agent_type)
            context.state.execution.current_agent = self.agent_type

            # Calculate metrics
            completed_at = datetime.now(timezone.utc)
            exec_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Emit AgentCompleted
            await event_emitter.emit_agent_completed(
                self.name, exec_ms, response.cost_usd, response.total_tokens,
                quality_result.score if quality_result else None,
                correlation_id=corr_id,
            )

            logger.info(
                "agent_completed",
                agent=self.name,
                execution_time_ms=exec_ms,
                cost_usd=response.cost_usd,
                tokens=response.total_tokens,
                quality_score=quality_result.score if quality_result else None,
            )

            return AgentResult(
                success=True,
                agent_name=self.name,
                response=response,
                quality=quality_result,
                validation=validation_result,
                artifacts_created=artifacts_created,
                execution_time_ms=exec_ms,
                cost_usd=response.cost_usd,
                tokens_consumed=response.total_tokens,
            )

        except AgentExecutionError:
            raise
        except OutputValidationError:
            raise
        except Exception as exc:
            logger.error(
                "agent_failed",
                agent=self.name,
                error=str(exc),
            )
            await event_emitter.emit_agent_failed(
                self.name, str(exc), correlation_id=corr_id,
            )
            return AgentResult(
                success=False,
                agent_name=self.name,
                error=str(exc),
            )

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------
    def _create_agent_context(self, node_context: NodeContext) -> AgentContext:
        """Create an ``AgentContext`` from a ``NodeContext``.

        Args:
            node_context: The node context from the workflow engine.

        Returns:
            An ``AgentContext`` with AI-specific dependencies.
        """
        # Extract AI dependencies from node context services/gateways
        return AgentContext.from_node_context(
            node_context,
            agent_name=self.name,
            agent_type=self.agent_type.value,
            llm_gateway=node_context.gateways.get("llm"),
            prompt_executor=node_context.services.get("prompt_executor"),
            output_validator=node_context.services.get("output_validator"),
            quality_evaluator=node_context.services.get("quality_evaluator"),
            artifact_manager=node_context.services.get("artifact_manager"),
            memory=node_context.services.get("agent_memory"),
            event_bus=node_context.services.get("event_bus"),
        )

    def _create_output_validator(self) -> OutputValidator:
        """Create an output validator from configuration.

        Returns:
            An ``OutputValidator`` configured from ``output_validator_config``.
        """
        config = self.output_validator_config
        return OutputValidator(
            schema=config.get("schema"),
            required_fields=config.get("required_fields"),
            business_rules=config.get("business_rules"),
            max_repair_attempts=config.get("max_repair_attempts", 2),
        )

    # -----------------------------------------------------------------------
    # Memory helpers
    # -----------------------------------------------------------------------
    async def remember(
        self,
        context: AgentContext,
        key: str,
        value: Any,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a value in agent memory.

        Args:
            context: The agent context.
            key: The memory key.
            value: The value to store.
            scope: The memory scope.
            ttl_seconds: Optional time-to-live.
        """
        memory = context.memory or context.services.get("agent_memory")
        if memory is not None:
            await memory.store(
                key, value,
                scope=scope,
                agent_name=self.name,
                execution_id=context.identity.execution_id,
                ttl_seconds=ttl_seconds,
            )

    async def recall(
        self,
        context: AgentContext,
        key: str,
        *,
        scope: str = MemoryScope.SHORT_TERM,
    ) -> Any | None:
        """Retrieve a value from agent memory.

        Args:
            context: The agent context.
            key: The memory key.
            scope: The memory scope.

        Returns:
            The stored value, or None if not found.
        """
        memory = context.memory or context.services.get("agent_memory")
        if memory is None:
            return None
        return await memory.retrieve(
            key, scope=scope,
            execution_id=context.identity.execution_id,
        )
