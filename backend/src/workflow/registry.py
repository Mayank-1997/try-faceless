"""Graph registry for workflow management.

Provides a central registry for workflow graphs with:
- Registration with versioning
- Lookup by name and version
- Metadata inspection
- Future plugin support

The registry is the single source of truth for available workflows.
The ``WorkflowEngine`` uses it to find and execute graphs.
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.exceptions import (
    WorkflowAlreadyRegisteredError,
    WorkflowNotFoundError,
)


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------
class RegistryEntry:
    """An entry in the graph registry.

    Attributes:
        graph: The workflow graph instance.
        name: The workflow name.
        version: The workflow version.
        metadata: The graph metadata.
    """

    def __init__(self, graph: BaseWorkflowGraph) -> None:
        self.graph = graph
        self.metadata: GraphMetadata = graph.metadata
        self.name: str = self.metadata.name
        self.version: str = self.metadata.version

    @property
    def key(self) -> str:
        """Return the registry key (name:version)."""
        return f"{self.name}:{self.version}"


# ---------------------------------------------------------------------------
# Graph registry
# ---------------------------------------------------------------------------
class GraphRegistry:
    """Central registry for workflow graphs.

    Supports registering graphs with versioning, looking up graphs
    by name and version, and listing all registered workflows.

    Usage::

        registry = GraphRegistry()
        registry.register(MyWorkflowGraph())
        graph = registry.get("youtube_video_generation", "1.0.0")
    """

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._by_name: dict[str, list[str]] = {}  # name -> list of versions
        self._logger = get_logger(__name__)

    def register(self, graph: BaseWorkflowGraph) -> None:
        """Register a workflow graph.

        Args:
            graph: The workflow graph to register.

        Raises:
            WorkflowAlreadyRegisteredError: If a graph with the same
                name and version is already registered.
        """
        entry = RegistryEntry(graph)
        key = entry.key

        if key in self._entries:
            raise WorkflowAlreadyRegisteredError(entry.name, entry.version)

        self._entries[key] = entry

        if entry.name not in self._by_name:
            self._by_name[entry.name] = []
        self._by_name[entry.name].append(entry.version)

        # Sort versions for deterministic ordering
        self._by_name[entry.name].sort()

        self._logger.info(
            "workflow_registered",
            name=entry.name,
            version=entry.version,
            content_type=entry.metadata.content_type,
        )

    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> BaseWorkflowGraph:
        """Get a registered workflow graph by name and optional version.

        Args:
            name: The workflow name.
            version: The workflow version. If None, returns the latest version.

        Returns:
            The workflow graph instance.

        Raises:
            WorkflowNotFoundError: If the workflow is not registered.
        """
        if version is not None:
            key = f"{name}:{version}"
            if key not in self._entries:
                raise WorkflowNotFoundError(name, version)
            return self._entries[key].graph

        # Find latest version
        if name not in self._by_name or not self._by_name[name]:
            raise WorkflowNotFoundError(name)

        latest_version = self._by_name[name][-1]
        key = f"{name}:{latest_version}"
        return self._entries[key].graph

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all registered workflows with metadata.

        Returns:
            List of dictionaries with name, version, description,
            content_type, and tags.
        """
        return [
            {
                "name": entry.name,
                "version": entry.version,
                "description": entry.metadata.description,
                "content_type": entry.metadata.content_type,
                "tags": entry.metadata.tags,
                "entry_node": entry.metadata.entry_node,
                "exit_nodes": entry.metadata.exit_nodes,
            }
            for entry in self._entries.values()
        ]

    def list_versions(self, name: str) -> list[str]:
        """List all registered versions of a workflow.

        Args:
            name: The workflow name.

        Returns:
            List of version strings, sorted from oldest to newest.

        Raises:
            WorkflowNotFoundError: If the workflow name is not registered.
        """
        if name not in self._by_name or not self._by_name[name]:
            raise WorkflowNotFoundError(name)
        return list(self._by_name[name])

    def exists(self, name: str, version: str | None = None) -> bool:
        """Check if a workflow is registered.

        Args:
            name: The workflow name.
            version: Optional version. If None, checks if any version exists.

        Returns:
            True if the workflow is registered.
        """
        if version is not None:
            return f"{name}:{version}" in self._entries
        return name in self._by_name and len(self._by_name[name]) > 0

    def unregister(self, name: str, version: str) -> bool:
        """Unregister a workflow.

        Args:
            name: The workflow name.
            version: The workflow version.

        Returns:
            True if the workflow was unregistered, False if it didn't exist.
        """
        key = f"{name}:{version}"
        if key not in self._entries:
            return False

        del self._entries[key]
        if name in self._by_name:
            self._by_name[name] = [v for v in self._by_name[name] if v != version]
            if not self._by_name[name]:
                del self._by_name[name]

        self._logger.info("workflow_unregistered", name=name, version=version)
        return True

    def clear(self) -> None:
        """Clear all registered workflows."""
        self._entries.clear()
        self._by_name.clear()
        self._logger.info("registry_cleared")

    @property
    def count(self) -> int:
        """Return the number of registered workflows."""
        return len(self._entries)
