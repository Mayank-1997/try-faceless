"""Tool abstraction for the AI Agent Framework.

Provides interfaces for tools that agents can use:

- **Web Search**: Search the web for information
- **Calculator**: Perform calculations
- **Image Search**: Search for images
- **YouTube Search**: Search YouTube for videos
- **Code Execution**: Execute code snippets
- **Browser**: Browse web pages

Only interfaces are defined — no tool implementations.
Concrete tools will be added in future phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tool parameter definition
# ---------------------------------------------------------------------------
class ToolParameter(BaseModel):
    """Definition of a tool parameter.

    Attributes:
        name: The parameter name.
        description: Human-readable description.
        param_type: The parameter type (string, number, boolean, etc.).
        required: Whether the parameter is required.
        default_value: Optional default value.
    """

    name: str
    description: str = ""
    param_type: str = "string"
    required: bool = True
    default_value: Any = None


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------
class ToolResult(BaseModel):
    """Result of a tool execution.

    Attributes:
        success: Whether the tool execution succeeded.
        output: The tool output (text, data, etc.).
        error: Error message if failed.
        execution_time_ms: Execution time in milliseconds.
        metadata: Additional metadata.
        timestamp: When the result was produced.
    """

    success: bool = True
    output: Any = None
    error: str | None = None
    execution_time_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def success_result(cls, output: Any, **metadata: Any) -> ToolResult:
        """Create a successful result."""
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def failure_result(cls, error: str, **metadata: Any) -> ToolResult:
        """Create a failure result."""
        return cls(success=False, error=error, metadata=metadata)


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------
class ToolMetadata(BaseModel):
    """Metadata describing a tool.

    Attributes:
        name: The tool name (unique identifier).
        description: Human-readable description.
        category: Tool category (search, calculation, execution, etc.).
        version: Tool version.
        parameters: List of parameter definitions.
        tags: Optional tags.
    """

    name: str
    description: str = ""
    category: str = ""
    version: str = "1.0.0"
    parameters: list[ToolParameter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract tool interface
# ---------------------------------------------------------------------------
class Tool(ABC):
    """Abstract interface for agent tools.

    Tools are capabilities that agents can invoke during execution.
    Each tool defines its parameters and executes asynchronously.

    Attributes:
        metadata: Tool metadata (name, description, parameters).
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return the tool metadata."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given parameters.

        Args:
            **kwargs: Tool parameters as keyword arguments.

        Returns:
            A ``ToolResult`` with the execution outcome.
        """
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the tool (e.g. establish connections)."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources."""
        ...

    def validate_parameters(self, **kwargs: Any) -> list[str]:
        """Validate that all required parameters are provided.

        Args:
            **kwargs: Provided parameters.

        Returns:
            List of missing required parameter names. Empty if all valid.
        """
        missing: list[str] = []
        for param in self.metadata.parameters:
            if param.required and param.name not in kwargs:
                missing.append(param.name)
        return missing


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
class ToolRegistry:
    """Registry for available tools.

    Tools are registered with a unique name and can be looked up
    by agents during execution.

    Usage::

        registry = ToolRegistry()
        registry.register(WebSearchTool())
        tool = registry.get("web_search")
        result = await tool.execute(query="AI news")
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: The tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        name = tool.metadata.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            The tool instance.

        Raises:
            KeyError: If the tool is not found.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def exists(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: The tool name.

        Returns:
            True if the tool is registered.
        """
        return name in self._tools

    def list_tools(self) -> list[ToolMetadata]:
        """List all registered tools.

        Returns:
            List of tool metadata.
        """
        return [tool.metadata for tool in self._tools.values()]

    def unregister(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: The tool name.

        Returns:
            True if unregistered, False if not found.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    @property
    def count(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    async def initialize_all(self) -> None:
        """Initialize all registered tools."""
        for tool in self._tools.values():
            await tool.initialize()

    async def shutdown_all(self) -> None:
        """Shut down all registered tools."""
        for tool in self._tools.values():
            await tool.shutdown()
