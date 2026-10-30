"""Fluent workflow builder for constructing workflow graphs.

Provides a fluent API for building workflow graphs without
subclassing ``BaseWorkflowGraph``.  Useful for simple workflows
and for testing.

Example::

    graph = (
        WorkflowBuilder("youtube_video_v1")
        .description("YouTube video generation workflow")
        .content_type("youtube_video")
        .add_node(research_node, is_entry=True)
        .add_node(script_node)
        .add_node(scene_node)
        .add_node(render_node, is_exit=True)
        .add_edge("research", "script")
        .add_edge("script", "scene_planner")
        .add_edge("scene_planner", "render")
        .add_conditional(
            "research",
            "script",
            lambda s: s.research.summary != "",
            "research_complete",
        )
        .add_conditional(
            "research",
            "research",  # retry
            lambda s: s.research.summary == "",
            "research_retry",
        )
        .enable_checkpointing()
        .build()
    )
"""

from __future__ import annotations

from typing import Any, Callable

from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.base_node import BaseNode
from src.workflow.checkpoint import CheckpointManager
from src.workflow.contexts import WorkflowContext
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Builder-generated graph
# ---------------------------------------------------------------------------
class BuiltWorkflowGraph(BaseWorkflowGraph):
    """A workflow graph constructed by the ``WorkflowBuilder``.

    This class wraps the builder's configuration into a ``BaseWorkflowGraph``
    implementation without requiring subclassing.
    """

    def __init__(
        self,
        metadata: GraphMetadata,
        nodes: list[BaseNode],
        edges: list[tuple[str, str]],
        conditional_edges: list[tuple[str, str, Callable[[WorkflowState], bool], str]],
        parallel_edges: list[tuple[str, list[str]]],
        checkpoint_enabled: bool = False,
    ) -> None:
        super().__init__()
        self._metadata = metadata
        self._nodes_to_add = nodes
        self._edges_to_add = edges
        self._conditional_to_add = conditional_edges
        self._parallel_to_add = parallel_edges
        self._checkpoint_enabled = checkpoint_enabled

    @property
    def metadata(self) -> GraphMetadata:
        return self._metadata

    def build_graph(self) -> None:
        for node in self._nodes_to_add:
            is_entry = node.name == self._metadata.entry_node
            is_exit = node.name in self._metadata.exit_nodes
            self.add_node(node, is_entry=is_entry, is_exit=is_exit)

        for source, target in self._edges_to_add:
            self.add_edge(source, target)

        for source, target, condition, name in self._conditional_to_add:
            self.add_conditional_edge(source, target, condition, name)

        for source, targets in self._parallel_to_add:
            self.add_parallel_nodes(source, targets)


# ---------------------------------------------------------------------------
# Fluent builder
# ---------------------------------------------------------------------------
class WorkflowBuilder:
    """Fluent builder for constructing workflow graphs.

    Provides a chainable API for defining nodes, edges, conditional
    routing, parallel execution, and checkpointing.
    """

    def __init__(self, name: str, version: str = "1.0.0") -> None:
        """Initialize the builder.

        Args:
            name: The workflow name.
            version: The workflow version.
        """
        self._metadata = GraphMetadata(name=name, version=version)
        self._nodes: list[BaseNode] = []
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: list[
            tuple[str, str, Callable[[WorkflowState], bool], str]
        ] = []
        self._parallel_edges: list[tuple[str, list[str]]] = []
        self._checkpoint_enabled = False
        self._entry_node: str | None = None
        self._exit_nodes: list[str] = []

    # -----------------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------------
    def description(self, description: str) -> WorkflowBuilder:
        """Set the workflow description."""
        self._metadata = self._metadata.model_copy(update={"description": description})
        return self

    def content_type(self, content_type: str) -> WorkflowBuilder:
        """Set the content type."""
        self._metadata = self._metadata.model_copy(update={"content_type": content_type})
        return self

    def tags(self, tags: list[str]) -> WorkflowBuilder:
        """Set workflow tags."""
        self._metadata = self._metadata.model_copy(update={"tags": tags})
        return self

    # -----------------------------------------------------------------------
    # Nodes
    # -----------------------------------------------------------------------
    def add_node(
        self,
        node: BaseNode,
        *,
        is_entry: bool = False,
        is_exit: bool = False,
    ) -> WorkflowBuilder:
        """Add a node to the workflow.

        Args:
            node: The node instance to add.
            is_entry: Whether this is the entry point.
            is_exit: Whether this is a terminal node.
        """
        self._nodes.append(node)
        if is_entry:
            self._entry_node = node.name
            self._metadata = self._metadata.model_copy(
                update={"entry_node": node.name}
            )
        if is_exit:
            self._exit_nodes.append(node.name)
        return self

    # -----------------------------------------------------------------------
    # Edges
    # -----------------------------------------------------------------------
    def add_edge(self, source: str, target: str) -> WorkflowBuilder:
        """Add an unconditional edge between two nodes.

        Args:
            source: The source node name.
            target: The target node name.
        """
        self._edges.append((source, target))
        return self

    def add_conditional(
        self,
        source: str,
        target: str,
        condition: Callable[[WorkflowState], bool],
        condition_name: str = "",
    ) -> WorkflowBuilder:
        """Add a conditional edge.

        The edge is only followed if ``condition`` returns True.

        Args:
            source: The source node name.
            target: The target node name.
            condition: Callable that takes ``WorkflowState`` and returns bool.
            condition_name: Optional name for the condition.
        """
        self._conditional_edges.append((source, target, condition, condition_name))
        return self

    def add_parallel(
        self,
        source: str,
        targets: list[str],
    ) -> WorkflowBuilder:
        """Add fan-out edges for parallel execution.

        Args:
            source: The source node name.
            targets: List of target node names to execute in parallel.
        """
        self._parallel_edges.append((source, targets))
        return self

    # -----------------------------------------------------------------------
    # Checkpointing
    # -----------------------------------------------------------------------
    def enable_checkpointing(self) -> WorkflowBuilder:
        """Enable checkpointing for this workflow."""
        self._checkpoint_enabled = True
        return self

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------
    def build(self) -> BuiltWorkflowGraph:
        """Build and return the workflow graph.

        Returns:
            A ``BuiltWorkflowGraph`` instance ready for execution.

        Raises:
            ValueError: If no nodes are defined or no entry point is set.
        """
        if not self._nodes:
            raise ValueError("Cannot build workflow with no nodes")

        if self._entry_node is None:
            raise ValueError("No entry node specified. Use add_node(..., is_entry=True)")

        # Update exit nodes in metadata
        self._metadata = self._metadata.model_copy(
            update={"exit_nodes": self._exit_nodes}
        )

        return BuiltWorkflowGraph(
            metadata=self._metadata,
            nodes=self._nodes,
            edges=self._edges,
            conditional_edges=self._conditional_edges,
            parallel_edges=self._parallel_edges,
            checkpoint_enabled=self._checkpoint_enabled,
        )
