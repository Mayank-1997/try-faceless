"""Agent context — dependency injection container for AI agents.

``AgentContext`` extends the workflow ``NodeContext`` with AI-specific
dependencies that every agent needs:

- **LLM Gateway**: For calling AI providers (never call providers directly)
- **Prompt Executor**: For rendering and executing prompts
- **Output Validator**: For validating AI output
- **Quality Evaluator**: For scoring output quality
- **Artifact Manager**: For storing and retrieving artifacts
- **Agent Memory**: For short-term and workflow memory
- **Tools**: For tool execution (web search, calculator, etc.)
- **Event Bus**: For emitting agent lifecycle events

Agents receive all dependencies via ``AgentContext`` — they never
instantiate anything directly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.workflow.contexts import (
    CancellationToken,
    ExecutionContext,
    IdentityContext,
    NodeContext,
)
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Agent context
# ---------------------------------------------------------------------------
class AgentContext(BaseModel):
    """Complete context passed to every AI agent.

    Encapsulates all dependencies, state, and metadata that an agent
    needs to execute.  Agents receive this object and should never
    access global state or instantiate dependencies directly.

    Attributes:
        identity: Who and what is being executed.
        state: The current workflow state (mutable).
        execution: Runtime execution tracking.
        agent_name: The name of the agent.
        agent_type: The type of the agent (e.g. "research", "script").
        repositories: Dictionary of repository instances by name.
        gateways: Dictionary of gateway instances by name.
        services: Dictionary of service instances by name.
        config: Application configuration service.
        cancellation_token: Cooperative cancellation token.
        llm_gateway: The LLM gateway for AI calls.
        prompt_executor: The prompt executor for prompt rendering and execution.
        output_validator: The output validator for AI output validation.
        quality_evaluator: The quality evaluator for output scoring.
        artifact_manager: The artifact manager for storing artifacts.
        memory: The agent memory interface.
        tools: Dictionary of tool instances by name.
        event_bus: The event bus for emitting events.
    """

    identity: IdentityContext = Field(default_factory=IdentityContext)
    state: WorkflowState = Field(default_factory=WorkflowState)
    execution: ExecutionContext = Field(default_factory=ExecutionContext)
    agent_name: str = ""
    agent_type: str = ""
    repositories: dict[str, Any] = Field(default_factory=dict)
    gateways: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)
    config: Any = None
    cancellation_token: CancellationToken = Field(default_factory=CancellationToken)
    llm_gateway: Any = None
    prompt_executor: Any = None
    output_validator: Any = None
    quality_evaluator: Any = None
    artifact_manager: Any = None
    memory: Any = None
    tools: dict[str, Any] = Field(default_factory=dict)
    event_bus: Any = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def logger(self) -> Any:
        """Return a logger bound to the current agent context."""
        return get_logger(f"agent.{self.agent_name or 'unknown'}")

    @property
    def is_cancelled(self) -> bool:
        """Check if the workflow has been cancelled."""
        return self.cancellation_token.is_cancelled

    @property
    def correlation_id(self) -> str | None:
        """Return the correlation ID for tracing."""
        return self.execution.correlation_id

    def get_repository(self, name: str) -> Any:
        """Get a repository by name.

        Args:
            name: The repository name (e.g. "project", "workflow").

        Returns:
            The repository instance.

        Raises:
            KeyError: If the repository is not found.
        """
        if name not in self.repositories:
            raise KeyError(f"Repository '{name}' not available in agent context")
        return self.repositories[name]

    def get_gateway(self, name: str) -> Any:
        """Get a gateway by name.

        Args:
            name: The gateway name (e.g. "llm", "image", "video").

        Returns:
            The gateway instance.

        Raises:
            KeyError: If the gateway is not found.
        """
        if name not in self.gateways:
            raise KeyError(f"Gateway '{name}' not available in agent context")
        return self.gateways[name]

    def get_service(self, name: str) -> Any:
        """Get a service by name.

        Args:
            name: The service name (e.g. "cost_tracker", "token_tracker").

        Returns:
            The service instance.

        Raises:
            KeyError: If the service is not found.
        """
        if name not in self.services:
            raise KeyError(f"Service '{name}' not available in agent context")
        return self.services[name]

    def get_tool(self, name: str) -> Any:
        """Get a tool by name.

        Args:
            name: The tool name (e.g. "web_search", "calculator").

        Returns:
            The tool instance.

        Raises:
            KeyError: If the tool is not found.
        """
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not available in agent context")
        return self.tools[name]

    @classmethod
    def from_node_context(
        cls,
        node_context: NodeContext,
        *,
        agent_name: str = "",
        agent_type: str = "",
        llm_gateway: Any = None,
        prompt_executor: Any = None,
        output_validator: Any = None,
        quality_evaluator: Any = None,
        artifact_manager: Any = None,
        memory: Any = None,
        tools: dict[str, Any] | None = None,
        event_bus: Any = None,
    ) -> AgentContext:
        """Create an ``AgentContext`` from a ``NodeContext``.

        This is used when an agent is executed as a workflow node.

        Args:
            node_context: The node context from the workflow engine.
            agent_name: The agent name.
            agent_type: The agent type.
            llm_gateway: The LLM gateway instance.
            prompt_executor: The prompt executor instance.
            output_validator: The output validator instance.
            quality_evaluator: The quality evaluator instance.
            artifact_manager: The artifact manager instance.
            memory: The agent memory instance.
            tools: Dictionary of tool instances.
            event_bus: The event bus instance.

        Returns:
            An ``AgentContext`` with all dependencies.
        """
        return cls(
            identity=node_context.identity,
            state=node_context.state,
            execution=node_context.execution,
            agent_name=agent_name,
            agent_type=agent_type,
            repositories=node_context.repositories,
            gateways=node_context.gateways,
            services=node_context.services,
            config=node_context.config,
            cancellation_token=node_context.cancellation_token,
            llm_gateway=llm_gateway or node_context.gateways.get("llm"),
            prompt_executor=prompt_executor,
            output_validator=output_validator,
            quality_evaluator=quality_evaluator,
            artifact_manager=artifact_manager,
            memory=memory,
            tools=tools or {},
            event_bus=event_bus or node_context.services.get("event_bus"),
        )
