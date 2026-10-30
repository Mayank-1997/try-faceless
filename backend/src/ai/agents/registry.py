"""Agent registry for the AI Agent Framework.

Provides a central registry for AI agents with:
- Registration with versioning
- Lookup by name and version
- Metadata inspection
- Future plugin support

The registry is the single source of truth for available agents.
The workflow engine and DI container use it to find and inject agents.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.ai.agents.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
)
from src.core.enums import AgentType
from src.core.logging import get_logger


# ---------------------------------------------------------------------------
# Agent metadata
# ---------------------------------------------------------------------------
class AgentMetadata(BaseModel):
    """Metadata describing a registered agent.

    Attributes:
        name: The agent name (unique identifier).
        agent_type: The ``AgentType`` enum value.
        version: Semantic version string.
        description: Human-readable description.
        content_types: Content types this agent supports.
        tags: Optional tags for categorization.
    """

    name: str = ""
    agent_type: str = ""
    version: str = "1.0.0"
    description: str = ""
    content_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------
class AgentRegistryEntry:
    """An entry in the agent registry.

    Attributes:
        agent: The agent instance (or factory callable).
        metadata: The agent metadata.
        name: The agent name.
        version: The agent version.
    """

    def __init__(
        self,
        agent: Any,
        metadata: AgentMetadata,
    ) -> None:
        self.agent = agent
        self.metadata = metadata
        self.name = metadata.name
        self.version = metadata.version

    @property
    def key(self) -> str:
        """Return the registry key (name:version)."""
        return f"{self.name}:{self.version}"


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------
class AgentRegistry:
    """Central registry for AI agents.

    Supports registering agents with versioning, looking up agents
    by name and version, and listing all registered agents.

    Usage::

        registry = AgentRegistry()
        registry.register(ResearchAgent(), AgentMetadata(
            name="research",
            agent_type=AgentType.RESEARCH.value,
            version="1.0.0",
        ))
        agent = registry.get("research", "1.0.0")
    """

    def __init__(self) -> None:
        self._entries: dict[str, AgentRegistryEntry] = {}
        self._by_name: dict[str, list[str]] = {}
        self._by_type: dict[str, list[str]] = {}
        self._logger = get_logger(__name__)

    def register(
        self,
        agent: Any,
        metadata: AgentMetadata | None = None,
    ) -> None:
        """Register an agent.

        Args:
            agent: The agent instance to register.
            metadata: Optional metadata. If None, auto-extracted from agent.

        Raises:
            AgentAlreadyRegisteredError: If an agent with the same
                name and version is already registered.
        """
        if metadata is None:
            # Auto-extract metadata from agent
            name = getattr(agent, "name", agent.__class__.__name__.lower())
            agent_type_val = (
                agent.agent_type.value
                if hasattr(agent, "agent_type") and hasattr(agent.agent_type, "value")
                else str(getattr(agent, "agent_type", "unknown"))
            )
            metadata = AgentMetadata(
                name=name,
                agent_type=agent_type_val,
            )

        entry = AgentRegistryEntry(agent, metadata)
        key = entry.key

        if key in self._entries:
            raise AgentAlreadyRegisteredError(entry.name, entry.version)

        self._entries[key] = entry

        # Index by name
        if entry.name not in self._by_name:
            self._by_name[entry.name] = []
        self._by_name[entry.name].append(entry.version)
        self._by_name[entry.name].sort()

        # Index by type
        if entry.metadata.agent_type not in self._by_type:
            self._by_type[entry.metadata.agent_type] = []
        self._by_type[entry.metadata.agent_type].append(entry.name)

        self._logger.info(
            "agent_registered",
            name=entry.name,
            version=entry.version,
            agent_type=entry.metadata.agent_type,
        )

    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> Any:
        """Get a registered agent by name and optional version.

        Args:
            name: The agent name.
            version: The agent version. If None, returns the latest version.

        Returns:
            The agent instance.

        Raises:
            AgentNotFoundError: If the agent is not registered.
        """
        if version is not None:
            key = f"{name}:{version}"
            if key not in self._entries:
                raise AgentNotFoundError(name, version)
            return self._entries[key].agent

        # Find latest version
        if name not in self._by_name or not self._by_name[name]:
            raise AgentNotFoundError(name)
        latest_version = self._by_name[name][-1]
        key = f"{name}:{latest_version}"
        return self._entries[key].agent

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents with metadata.

        Returns:
            List of dictionaries with agent metadata.
        """
        return [
            {
                "name": entry.name,
                "version": entry.version,
                "agent_type": entry.metadata.agent_type,
                "description": entry.metadata.description,
                "content_types": entry.metadata.content_types,
                "tags": entry.metadata.tags,
            }
            for entry in self._entries.values()
        ]

    def list_by_type(self, agent_type: str) -> list[dict[str, Any]]:
        """List agents by agent type.

        Args:
            agent_type: The agent type string.

        Returns:
            List of agent metadata dictionaries.
        """
        names = self._by_type.get(agent_type, [])
        results: list[dict[str, Any]] = []
        for name in names:
            versions = self._by_name.get(name, [])
            for version in versions:
                entry = self._entries.get(f"{name}:{version}")
                if entry:
                    results.append({
                        "name": entry.name,
                        "version": entry.version,
                        "agent_type": entry.metadata.agent_type,
                        "description": entry.metadata.description,
                    })
        return results

    def list_versions(self, name: str) -> list[str]:
        """List all registered versions of an agent.

        Args:
            name: The agent name.

        Returns:
            List of version strings, sorted from oldest to newest.

        Raises:
            AgentNotFoundError: If the agent name is not registered.
        """
        if name not in self._by_name or not self._by_name[name]:
            raise AgentNotFoundError(name)
        return list(self._by_name[name])

    def exists(self, name: str, version: str | None = None) -> bool:
        """Check if an agent is registered.

        Args:
            name: The agent name.
            version: Optional version. If None, checks if any version exists.

        Returns:
            True if the agent is registered.
        """
        if version is not None:
            return f"{name}:{version}" in self._entries
        return name in self._by_name and len(self._by_name[name]) > 0

    def unregister(self, name: str, version: str) -> bool:
        """Unregister an agent.

        Args:
            name: The agent name.
            version: The agent version.

        Returns:
            True if the agent was unregistered, False if it didn't exist.
        """
        key = f"{name}:{version}"
        if key not in self._entries:
            return False

        entry = self._entries[key]
        del self._entries[key]

        # Update name index
        if name in self._by_name:
            self._by_name[name] = [
                v for v in self._by_name[name] if v != version
            ]
            if not self._by_name[name]:
                del self._by_name[name]

        # Update type index
        agent_type = entry.metadata.agent_type
        if agent_type in self._by_type:
            self._by_type[agent_type] = [
                n for n in self._by_type[agent_type] if n != name
            ]
            if not self._by_type[agent_type]:
                del self._by_type[agent_type]

        self._logger.info("agent_unregistered", name=name, version=version)
        return True

    def clear(self) -> None:
        """Clear all registered agents."""
        self._entries.clear()
        self._by_name.clear()
        self._by_type.clear()
        self._logger.info("agent_registry_cleared")

    @property
    def count(self) -> int:
        """Return the number of registered agents."""
        return len(self._entries)
