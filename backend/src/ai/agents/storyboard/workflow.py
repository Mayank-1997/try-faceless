"""Storyboard workflow graph — LangGraph integration for the storyboard & scene planning subsystem.

Defines the sequential workflow that chains all 9 storyboard agents:

    StoryAnalyzer → StoryBeat → SceneSegmentation → VisualStoryboard →
    CameraPlanner → AnimationPlanner → AssetDecision → Continuity →
    StoryboardReview

Each agent is a node in the graph.  The workflow produces a
``StoryboardPackage`` stored in ``WorkflowState.storyboard.metadata``.
"""

from __future__ import annotations

from src.ai.agents.storyboard.animation_planner import AnimationPlannerAgent
from src.ai.agents.storyboard.asset_decision import AssetDecisionAgent
from src.ai.agents.storyboard.camera_planner import CameraPlannerAgent
from src.ai.agents.storyboard.continuity import ContinuityAgent
from src.ai.agents.storyboard.scene_segmentation import SceneSegmentationAgent
from src.ai.agents.storyboard.story_analyzer import StoryAnalyzerAgent
from src.ai.agents.storyboard.story_beat import StoryBeatAgent
from src.ai.agents.storyboard.storyboard_review import StoryboardReviewAgent
from src.ai.agents.storyboard.storyboard_visual import StoryboardAgent
from src.core.logging import get_logger
from src.workflow.base_graph import BaseWorkflowGraph, GraphMetadata
from src.workflow.contexts import NodeContext
from src.workflow.state import WorkflowState


class StoryboardWorkflowGraph(BaseWorkflowGraph):
    """Workflow graph for the Storyboard & Scene Planning subsystem.

    Chains 9 agents sequentially:
    1. StoryAnalyzerAgent — Analyze narrative flow, emotional peaks, visual opportunities
    2. StoryBeatAgent — Convert script into story beats
    3. SceneSegmentationAgent — Split script into production scenes
    4. StoryboardAgent — Generate visual descriptions for each scene
    5. CameraPlannerAgent — Plan camera angles and movements
    6. AnimationPlannerAgent — Plan animations for each scene
    7. AssetDecisionAgent — Decide asset types for each scene
    8. ContinuityAgent — Ensure visual consistency across scenes
    9. StoryboardReviewAgent — Review and assemble final StoryboardPackage
    """

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(__name__)
        self._metadata: GraphMetadata = GraphMetadata()
        self.build_graph()

    def build_graph(self) -> None:
        """Build the storyboard workflow graph."""
        story_analyzer = StoryAnalyzerAgent()
        story_beat = StoryBeatAgent()
        scene_segmentation = SceneSegmentationAgent()
        visual_storyboard = StoryboardAgent()
        camera_planner = CameraPlannerAgent()
        animation_planner = AnimationPlannerAgent()
        asset_decision = AssetDecisionAgent()
        continuity = ContinuityAgent()
        storyboard_review = StoryboardReviewAgent()

        self.add_node(story_analyzer)
        self.add_node(story_beat)
        self.add_node(scene_segmentation)
        self.add_node(visual_storyboard)
        self.add_node(camera_planner)
        self.add_node(animation_planner)
        self.add_node(asset_decision)
        self.add_node(continuity)
        self.add_node(storyboard_review)

        self.add_edge(story_analyzer.name, story_beat.name)
        self.add_edge(story_beat.name, scene_segmentation.name)
        self.add_edge(scene_segmentation.name, visual_storyboard.name)
        self.add_edge(visual_storyboard.name, camera_planner.name)
        self.add_edge(camera_planner.name, animation_planner.name)
        self.add_edge(animation_planner.name, asset_decision.name)
        self.add_edge(asset_decision.name, continuity.name)
        self.add_edge(continuity.name, storyboard_review.name)

        self._metadata = GraphMetadata(
            name="storyboard_workflow",
            version="1.0.0",
            description="Storyboard & Scene Planning workflow with 9 agents",
            content_type="storyboard_package",
            entry_node=story_analyzer.name,
            exit_nodes=[storyboard_review.name],
            tags=["storyboard", "scene_planning", "phase8"],
        )

    @property
    def metadata(self) -> GraphMetadata:
        return self._metadata

    async def execute_node(
        self,
        node_name: str,
        context: NodeContext,
    ) -> WorkflowState:
        node = self._nodes.get(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found in storyboard workflow graph")

        self._logger.info(
            "storyboard_node_executing",
            node=node_name,
            agent_type=getattr(node, "agent_type", None),
        )

        return await node.run(context)
