"""Research workflow graph — LangGraph integration for the research subsystem.

Defines the sequential workflow that chains all 8 research agents:

    TopicAnalyzer → ResearchPlanner → ResearchAgent → FactVerification →
    KeywordExtraction → AudienceAnalysis → ContentAngle → ResearchSummary

Each agent is a node in the graph.  The workflow produces a
``ResearchPackage`` stored in ``WorkflowState.research.metadata``.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.research.audience_analysis import AudienceAnalysisAgent
from src.ai.agents.research.content_angle import ContentAngleAgent
from src.ai.agents.research.fact_verification import FactVerificationAgent
from src.ai.agents.research.keyword_extraction import KeywordExtractionAgent
from src.ai.agents.research.research_agent import ResearchAgent
from src.ai.agents.research.research_planner import ResearchPlannerAgent
from src.ai.agents.research.research_summary import ResearchSummaryAgent
from src.ai.agents.research.topic_analyzer import TopicAnalyzerAgent
from src.core.logging import get_logger
from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.contexts import NodeContext
from src.workflow.state import WorkflowState


class ResearchWorkflowGraph(BaseWorkflowGraph):
    """Workflow graph for the Topic Discovery & Research subsystem.

    Chains 8 agents sequentially:
    1. TopicAnalyzerAgent — Analyze the user topic
    2. ResearchPlannerAgent — Create research plan
    3. ResearchAgent — Gather information from web search
    4. FactVerificationAgent — Cross-check and verify facts
    5. KeywordExtractionAgent — Extract SEO keywords
    6. AudienceAnalysisAgent — Identify target audience
    7. ContentAngleAgent — Generate and select content angle
    8. ResearchSummaryAgent — Generate summary and assemble package
    """

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(__name__)
        self._metadata: GraphMetadata = GraphMetadata()
        self.build_graph()

    def build_graph(self) -> None:
        """Build the research workflow graph.

        Registers all 8 research agents as nodes and chains them
        sequentially with edges.
        """
        # Create agent instances
        topic_analyzer = TopicAnalyzerAgent()
        research_planner = ResearchPlannerAgent()
        research_agent = ResearchAgent()
        fact_verification = FactVerificationAgent()
        keyword_extraction = KeywordExtractionAgent()
        audience_analysis = AudienceAnalysisAgent()
        content_angle = ContentAngleAgent()
        research_summary = ResearchSummaryAgent()

        # Register nodes
        self.add_node(topic_analyzer)
        self.add_node(research_planner)
        self.add_node(research_agent)
        self.add_node(fact_verification)
        self.add_node(keyword_extraction)
        self.add_node(audience_analysis)
        self.add_node(content_angle)
        self.add_node(research_summary)

        # Define sequential edges
        self.add_edge(topic_analyzer.name, research_planner.name)
        self.add_edge(research_planner.name, research_agent.name)
        self.add_edge(research_agent.name, fact_verification.name)
        self.add_edge(fact_verification.name, keyword_extraction.name)
        self.add_edge(keyword_extraction.name, audience_analysis.name)
        self.add_edge(audience_analysis.name, content_angle.name)
        self.add_edge(content_angle.name, research_summary.name)

        # Set metadata
        self._metadata = GraphMetadata(
            name="research_workflow",
            version="1.0.0",
            description="Topic Discovery & Research workflow with 8 agents",
            content_type="research_package",
            entry_node=topic_analyzer.name,
            exit_nodes=[research_summary.name],
            tags=["research", "topic_discovery", "phase6"],
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
            raise ValueError(f"Node '{node_name}' not found in research workflow graph")

        self._logger.info(
            "research_node_executing",
            node=node_name,
            agent_type=getattr(node, "agent_type", None),
        )

        return await node.run(context)
