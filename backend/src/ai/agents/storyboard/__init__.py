"""Storyboard & Scene Planning subsystem — transforms scripts into production-ready storyboards.

Phase 8: Implements the complete storyboard workflow with 9 agents:
- StoryAnalyzerAgent
- StoryBeatAgent
- SceneSegmentationAgent
- StoryboardAgent (visual)
- CameraPlannerAgent
- AnimationPlannerAgent
- AssetDecisionAgent
- ContinuityAgent
- StoryboardReviewAgent

All agents inherit from ``BaseAgent`` and produce a structured
``StoryboardPackage`` consumed by downstream agents (Image, Video,
Voice, Rendering).
"""

from src.ai.agents.storyboard.animation_planner import AnimationPlannerAgent
from src.ai.agents.storyboard.asset_decision import AssetDecisionAgent
from src.ai.agents.storyboard.camera_planner import CameraPlannerAgent
from src.ai.agents.storyboard.continuity import ContinuityAgent
from src.ai.agents.storyboard.events import StoryboardEventEmitter, StoryboardEvents
from src.ai.agents.storyboard.scene_segmentation import SceneSegmentationAgent
from src.ai.agents.storyboard.story_analyzer import StoryAnalyzerAgent
from src.ai.agents.storyboard.story_beat import StoryBeatAgent
from src.ai.agents.storyboard.storyboard_review import StoryboardReviewAgent
from src.ai.agents.storyboard.storyboard_visual import StoryboardAgent
from src.ai.agents.storyboard.workflow import StoryboardWorkflowGraph
from src.ai.agents.storyboard.schema import (
    AnimationPlan,
    AnimationPlanResult,
    AssetDecisionResult,
    AssetSceneDecision,
    CameraPlan,
    CameraPlanResult,
    ContinuityResult,
    PlannedScene,
    ScenePackage,
    SceneSegmentationResult,
    StoryAnalysis,
    StoryBeat,
    StoryBeatResult,
    StoryboardPackage,
    StoryboardQualityEvaluation,
    StoryboardReviewResult,
    VisualPlan,
    VisualStoryboardResult,
)
