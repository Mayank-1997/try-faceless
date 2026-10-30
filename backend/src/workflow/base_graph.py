"""Base workflow graph for the orchestration framework.

Every future workflow (YouTube Video Generation, Blog Generation,
LinkedIn Post Generation, etc.) must inherit from ``BaseWorkflowGraph``.

The base class provides:
- Graph construction (nodes, edges, conditional routing)
- Node registration
- Edge registration
- Conditional routing
- Parallel execution support (fan-out / fan-in)
- Lifecycle hooks (before/after build, before/after execute)
- Checkpoint integration
- Event emission

Subclasses implement ``build_graph`` to define the graph structure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.workflow.base_node import BaseNode
from src.workflow.contexts import NodeContext, WorkflowContext
from src.workflow.events import WorkflowEventEmitter
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Graph metadata
# ---------------------------------------------------------------------------
class GraphMetadata(BaseModel):
    """Metadata describing a workflow graph.

    Attributes:
        name: The workflow name (e.g. "youtube_video_generation").
        version: Semantic version string.
        description: Human-readable description.
        content_type: The content type this workflow produces.
        entry_node: The name of the first node to execute.
        exit_nodes: Names of terminal nodes.
        tags: Optional tags for categorization.
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    content_type: str = ""
    entry_node: str = ""
    exit_nodes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Edge definition
# ---------------------------------------------------------------------------
class EdgeDefinition(BaseModel):
    """Defines an edge between two nodes.

    Attributes:
        source: The source node name.
        target: The target node name.
        condition: Optional callable that returns True if this edge
            should be followed. If None, the edge is unconditional.
        condition_name: Optional name for the condition (for logging).
    """

    source: str
    target: str
    condition: Callable[[WorkflowState], bool] | None = None
    condition_name: str = ""

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------
class NodeRegistration(BaseModel):
    """Registration info for a node in the graph.

    Attributes:
        name: The unique node name within the graph.
        node: The node instance.
        is_entry: Whether this is the entry point.
        is_exit: Whether this is a terminal node.
    """

    name: str
    node: Any = None  # BaseNode instance
    is_entry: bool = False
    is_exit: bool = False

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Base workflow graph
# ---------------------------------------------------------------------------
class BaseWorkflowGraph(ABC):
    """Abstract base class for all workflow graphs.

    Subclasses must implement:
        - ``build_graph``: Define nodes, edges, and conditional routing.

    Subclasses may override:
        - ``metadata``: Return graph metadata.
        - ``on_before_build``: Pre-build hook.  
        - ``on_after_build``: Post-build hook.
        - ``on_before_execute``: Pre-execution hook.
        - ``on_after_execute``: Post-execution hook.

    Attributes:
        metadata: Graph metadata (name, version, description).
    """

    def __init__(self) -> None:
        self._nodes: dict[str, NodeRegistration] = {}
        self._edges: list[EdgeDefinition] = []
        self._conditional_edges: dict[str, list[EdgeDefinition]] = {}
        self._logger = get_logger(f"workflow.graph.{self.__class__.__name__}")
        self._built = False
        self._graph: Any = None  # LangGraph StateGraph instance
        self._active_context: WorkflowContext | None = None

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------
    @property
    @abstractmethod
    def metadata(self) -> GraphMetadata:
        """Return graph metadata. Must be implemented by subclasses."""
        ...

    @property
    def is_built(self) -> bool:
        """Check if the graph has been built."""
        return self._built

    @property
    def nodes(self) -> dict[str, NodeRegistration]:
        """Return all registered nodes."""
        return dict(self._nodes)

    @property
    def edges(self) -> list[EdgeDefinition]:
        """Return all registered edges."""
        return list(self._edges)

    # -----------------------------------------------------------------------
    # Abstract methods
    # -----------------------------------------------------------------------
    @abstractmethod
    def build_graph(self) -> None:
        """Define the graph structure (nodes, edges, routing).

        Subclasses must call ``add_node``, ``add_edge``, and
        ``add_conditional_edge`` within this method.
        """
        ...

    # -----------------------------------------------------------------------
    # Lifecycle hooks (override in subclasses)
    # -----------------------------------------------------------------------
    async def on_before_build(self) -> None:
        """Called before the graph is built."""
        pass

    async def on_after_build(self) -> None:
        """Called after the graph is built."""
        pass

    async def on_before_execute(self, context: WorkflowContext) -> None:
        """Called before workflow execution starts."""
        pass

    async def on_after_execute(self, context: WorkflowContext, state: WorkflowState) -> None:
        """Called after workflow execution completes."""
        pass

    # -----------------------------------------------------------------------
    # Node registration
    # -----------------------------------------------------------------------
    def add_node(
        self,
        node: BaseNode,
        *,
        is_entry: bool = False,
        is_exit: bool = False,
    ) -> None:
        """Register a node in the graph.

        Args:
            node: The node instance to register.
            is_entry: Whether this is the entry point node.
            is_exit: Whether this is a terminal node.

        Raises:
            ValueError: If a node with the same name already exists.
        """
        if node.name in self._nodes:
            raise ValueError(f"Node '{node.name}' already registered in graph")

        self._nodes[node.name] = NodeRegistration(
            name=node.name,
            node=node,
            is_entry=is_entry,
            is_exit=is_exit,
        )
        self._logger.info("node_registered", node=node.name, is_entry=is_entry, is_exit=is_exit)

    # -----------------------------------------------------------------------
    # Edge registration
    # -----------------------------------------------------------------------
    def add_edge(self, source: str, target: str) -> None:
        """Add an unconditional edge between two nodes.

        Args:
            source: The source node name.
            target: The target node name.

        Raises:
            ValueError: If either node is not registered.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not registered")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not registered")

        self._edges.append(EdgeDefinition(source=source, target=target))
        self._logger.info("edge_added", source=source, target=target)

    def add_conditional_edge(
        self,
        source: str,
        target: str,
        condition: Callable[[WorkflowState], bool],
        condition_name: str = "",
    ) -> None:
        """Add a conditional edge between two nodes.

        The edge is only followed if the condition returns True.

        Args:
            source: The source node name.
            target: The target node name.
            condition: A callable that takes ``WorkflowState`` and returns bool.
            condition_name: Optional name for the condition (for logging).

        Raises:
            ValueError: If either node is not registered.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not registered")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not registered")

        edge = EdgeDefinition(
            source=source,
            target=target,
            condition=condition,
            condition_name=condition_name or f"{source}_to_{target}",
        )

        if source not in self._conditional_edges:
            self._conditional_edges[source] = []
        self._conditional_edges[source].append(edge)
        self._logger.info(
            "conditional_edge_added",
            source=source,
            target=target,
            condition_name=edge.condition_name,
        )

    # -----------------------------------------------------------------------
    # Parallel execution support
    # -----------------------------------------------------------------------
    def add_parallel_nodes(
        self,
        source: str,
        targets: list[str],
    ) -> None:
        """Add fan-out edges from a source to multiple target nodes.

        All targets execute in parallel after the source completes.

        Args:
            source: The source node name.
            targets: List of target node names to execute in parallel.

        Raises:
            ValueError: If the source or any target is not registered.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not registered")
        for target in targets:
            if target not in self._nodes:
                raise ValueError(f"Target node '{target}' not registered")
            self._edges.append(EdgeDefinition(source=source, target=target))
        self._logger.info(
            "parallel_edges_added",
            source=source,
            targets=targets,
        )

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------
    async def build(self) -> None:
        """Build the graph by calling ``build_graph`` and constructing
        the LangGraph ``StateGraph``.

        This method:
        1. Calls ``on_before_build`` hook
        2. Calls ``build_graph`` (subclass implementation)
        3. Constructs the LangGraph ``StateGraph``
        4. Calls ``on_after_build`` hook
        """
        if self._built:
            self._logger.warning("graph_already_built")
            return

        await self.on_before_build()
        if not self._nodes:
            self.build_graph()
        self._construct_langgraph()
        self._built = True
        await self.on_after_build()
        self._logger.info(
            "graph_built",
            nodes=len(self._nodes),
            edges=len(self._edges),
            conditional_edges=sum(len(v) for v in self._conditional_edges.values()),
        )

    def _construct_langgraph(self) -> None:
        """Construct the LangGraph StateGraph from registered nodes and edges."""
        try:
            from langgraph.graph import StateGraph as LGSStateGraph
        except ImportError:
            self._logger.warning(
                "langgraph_not_available",
                message="langgraph not installed, graph construction skipped",
            )
            return

        graph = LGSStateGraph(WorkflowState)

        # Add nodes
        for name, reg in self._nodes.items():
            node = reg.node
            if node is not None:
                graph.add_node(name, self._wrap_node(node))

        # Set entry point
        entry = self.metadata.entry_node
        if entry and entry in self._nodes:
            graph.set_entry_point(entry)

        # Add unconditional edges
        for edge in self._edges:
            graph.add_edge(edge.source, edge.target)

        # Add conditional edges
        for source, edges in self._conditional_edges.items():
            conditions: dict[str, Callable[[WorkflowState], str]] = {}
            for edge in edges:
                conditions[edge.target] = self._wrap_condition(edge)
            if conditions:
                graph.add_conditional_edges(source, self._make_router(source, edges))

        # Set exit points
        for exit_node in self.metadata.exit_nodes:
            if exit_node in self._nodes:
                graph.add_edge(exit_node, "__end__")

        try:
            self._graph = graph.compile()
        except Exception as exc:
            self._logger.error("graph_compile_failed", error=str(exc))
            raise

    def _wrap_node(self, node: BaseNode) -> Callable[[WorkflowState], WorkflowState]:
        """Wrap a BaseNode for LangGraph compatibility.

        LangGraph expects sync or async functions that take state and
        return state.  We create a wrapper that extracts the NodeContext
        from the state and calls ``node.run``.

        Since LangGraph manages the state, we store the WorkflowContext
        in a thread-local or pass it through the state.
        """
        async def wrapper(state: WorkflowState) -> WorkflowState:
            # LangGraph reconstructs the state from its channels between
            # nodes, dropping any private attributes we set on it. Prefer the
            # context stored on the graph instance for this execution; fall
            # back to a private state attribute, then to a minimal context.
            context = self._active_context
            if context is None and hasattr(state, "_workflow_context"):
                context = state._workflow_context
            if context is None:
                # Fallback: create a minimal context
                from src.workflow.contexts import NodeContext, ExecutionContext
                context = NodeContext(
                    state=state,
                    execution=ExecutionContext(current_node=node.name),
                )
            else:
                context = context.create_node_context(state, node.name)

            return await node.run(context)

        return wrapper

    def _wrap_condition(self, edge: EdgeDefinition) -> Callable[[WorkflowState], bool]:
        """Wrap a condition function for LangGraph."""
        return edge.condition

    def _make_router(
        self,
        source: str,
        edges: list[EdgeDefinition],
    ) -> Callable[[WorkflowState], str]:
        """Create a router function for conditional edges.

        The router evaluates all conditions and returns the first
        matching target node name.
        """

        def router(state: WorkflowState) -> str:
            for edge in edges:
                if edge.condition is None or edge.condition(state):
                    return edge.target
            # If no condition matches, return the first edge's target
            return edges[0].target if edges else "__end__"

        return router

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------
    async def execute(
        self,
        context: WorkflowContext,
        initial_state: WorkflowState,
    ) -> WorkflowState:
        """Execute the workflow graph.

        Args:
            context: The workflow context with dependencies.
            initial_state: The initial workflow state.

        Returns:
            The final workflow state after execution.
        """
        if not self._built:
            await self.build()

        await self.on_before_execute(context)

        # Store the workflow context on the graph instance so node wrappers
        # can access dependencies (services/gateways). LangGraph reconstructs
        # the state between nodes and drops private attributes, so we cannot
        # rely solely on stashing the context on the state object.
        self._active_context = context
        try:
            # Set the workflow context on state for node wrappers to access
            initial_state._workflow_context = context  # type: ignore[attr-defined]

            if self._graph is not None:
                # Use LangGraph execution
                result = await self._graph.ainvoke(initial_state)
                if isinstance(result, WorkflowState):
                    final_state = result
                else:
                    final_state = WorkflowState.model_validate(result)
            else:
                # Fallback: sequential execution without LangGraph
                final_state = await self._execute_sequential(context, initial_state)
        finally:
            self._active_context = None

        await self.on_after_execute(context, final_state)
        return final_state

    async def _execute_sequential(
        self,
        context: WorkflowContext,
        state: WorkflowState,
    ) -> WorkflowState:
        """Fallback sequential execution when LangGraph is not available.

        Executes nodes in registration order, following edges.
        """
        entry = self.metadata.entry_node
        if not entry or entry not in self._nodes:
            return state

        current = entry
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            reg = self._nodes.get(current)
            if reg is None or reg.node is None:
                break

            node_context = context.create_node_context(state, current)
            state = await reg.node.run(node_context)

            # Find next node via edges
            next_node = None

            # Check conditional edges first
            cond_edges = self._conditional_edges.get(current, [])
            for edge in cond_edges:
                if edge.condition is None or edge.condition(state):
                    next_node = edge.target
                    break

            # Fall back to unconditional edges
            if next_node is None:
                for edge in self._edges:
                    if edge.source == current:
                        next_node = edge.target
                        break

            if next_node is None or next_node in self.metadata.exit_nodes:
                break

            current = next_node

        return state
