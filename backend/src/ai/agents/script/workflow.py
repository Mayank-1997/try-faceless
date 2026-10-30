"""Script workflow graph — LangGraph integration for the script generation subsystem.

Defines the sequential workflow that chains all 8 script agents:

    NarrativeStrategy → ScriptOutline → HookGenerator → SectionWriter →
    Transition → CTA → ScriptReview → ScriptOptimization

Each agent is a node in the graph.  The workflow produces a
``ScriptPackage`` stored in ``WorkflowState.script.metadata``.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.script.call_to_action import CallToActionAgent
from src.ai.agents.script.hook_generator import HookGeneratorAgent
from src.ai.agents.script.narrative_strategy import NarrativeStrategyAgent
from src.ai.agents.script.script_optimization import ScriptOptimizationAgent
from src.ai.agents.script.script_outline import ScriptOutlineAgent
from src.ai.agents.script.script_review import ScriptReviewAgent
from src.ai.agents.script.section_writer import SectionWriterAgent
from src.ai.agents.script.transition import TransitionAgent
from src.core.logging import get_logger
from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.contexts import NodeContext
from src.workflow.state import WorkflowState


class ScriptWorkflowGraph(BaseWorkflowGraph):
    """Workflow graph for the Script Generation subsystem.

    Chains 8 agents sequentially:
    1. NarrativeStrategyAgent — Choose storytelling approach
    2. ScriptOutlineAgent — Generate complete outline
    3. HookGeneratorAgent — Generate and select best hook
    4. SectionWriterAgent — Write all sections
    5. TransitionAgent — Generate smooth transitions
    6. CallToActionAgent — Generate CTAs
    7. ScriptReviewAgent — Review script quality
    8. ScriptOptimizationAgent — Optimize and assemble package
    """

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(__name__)
        self._metadata: GraphMetadata = GraphMetadata()
        self.build_graph()

    def build_graph(self) -> None:
        """Build the script workflow graph.

        Registers all 8 script agents as nodes and chains them
        sequentially with edges.
        """
        # Create agent instances
        narrative_strategy = NarrativeStrategyAgent()
        script_outline = ScriptOutlineAgent()
        hook_generator = HookGeneratorAgent()
        section_writer = SectionWriterAgent()
        transition = TransitionAgent()
        cta = CallToActionAgent()
        script_review = ScriptReviewAgent()
        script_optimization = ScriptOptimizationAgent()

        # Register nodes
        self.add_node(narrative_strategy)
        self.add_node(script_outline)
        self.add_node(hook_generator)
        self.add_node(section_writer)
        self.add_node(transition)
        self.add_node(cta)
        self.add_node(script_review)
        self.add_node(script_optimization)

        # Define sequential edges
        self.add_edge(narrative_strategy.name, script_outline.name)
        self.add_edge(script_outline.name, hook_generator.name)
        self.add_edge(hook_generator.name, section_writer.name)
        self.add_edge(section_writer.name, transition.name)
        self.add_edge(transition.name, cta.name)
        self.add_edge(cta.name, script_review.name)
        self.add_edge(script_review.name, script_optimization.name)

        # Set metadata
        self._metadata = GraphMetadata(
            name="script_workflow",
            version="1.0.0",
            description="Script Generation workflow with 8 agents",
            content_type="script_package",
            entry_node=narrative_strategy.name,
            exit_nodes=[script_optimization.name],
            tags=["script", "generation", "phase7"],
        )

    @property
    def metadata(self) -> GraphMetadata:
        """Return the graph metadata."""
        return self._metadata

    async def execute_node(
        self,
        node_name: str,
        context: NodeContext,
    ) -> WorkflowState:
        """Execute a single node by name.

        Args:
            node_name: The name of the node to execute.
            context: The node context.

        Returns:
            The updated workflow state.
        """
        node = self._nodes.get(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found in script workflow graph")

        self._logger.info(
            "script_node_executing",
            node=node_name,
            agent_type=getattr(node, "agent_type", None),
        )

        return await node.run(context)
