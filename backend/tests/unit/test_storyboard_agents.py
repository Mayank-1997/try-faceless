"""Tests for the Phase 8 Storyboard & Scene Planning subsystem."""

from __future__ import annotations

import json
import pytest
from uuid import uuid4

from src.ai.agents.context import AgentContext
from src.ai.agents.script.schema import (
    HookResult,
    Hook,
    NarrativeStrategy,
    ScriptPackage,
    ScriptSection,
)
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
from src.ai.agents.storyboard.workflow import StoryboardWorkflowGraph
from src.core.enums import AgentType
from src.workflow.contexts import IdentityContext
from src.workflow.state import WorkflowState


# ===========================================================================
# Mock LLM Gateway
# ===========================================================================
class MockLLMGateway:
    """Mock LLM gateway that returns pre-configured JSON responses."""

    def __init__(self, response_data: dict | None = None) -> None:
        self._response_data = response_data or {}

    async def generate(self, prompt: str, **kwargs):
        class Result:
            success = True
            output = json.dumps(self._response_data)
            cost_usd = 0.05
            input_tokens = 100
            output_tokens = 50
            total_tokens = 150
            latency_ms = 100
            provider = "gemini"
            model = "gemini-2.0-flash"
            metadata = {}
            correlation_id = kwargs.get("correlation_id")
        return Result()


# ===========================================================================
# Helper to create agent context with script package
# ===========================================================================
def make_context(
    *,
    gateway: MockLLMGateway | None = None,
    script_package: ScriptPackage | None = None,
    storyboard_metadata: dict | None = None,
) -> AgentContext:
    state = WorkflowState()
    state.topic.raw_topic = "AI"
    state.topic.expanded_topic = "Artificial Intelligence"

    if script_package is None:
        script_package = ScriptPackage(
            title="Understanding AI",
            full_script="Welcome to this video about AI. AI is a fascinating field. Let's explore it together.",
            word_count=100,
            estimated_duration_seconds=300,
            narrative_strategy=NarrativeStrategy(style="educational", tone="informative"),
            sections=[
                ScriptSection(section_id="s1", title="Intro", narration="Welcome to AI.", word_count=50),
            ],
            hook_result=HookResult(selected_hook=Hook(content="What is AI?")),
        )

    state.script.metadata["script_package"] = script_package.model_dump()
    state.script.title = script_package.title
    state.script.content = script_package.full_script

    if storyboard_metadata:
        state.storyboard.metadata = dict(storyboard_metadata)

    return AgentContext(
        state=state,
        agent_name="test",
        agent_type="story_planner",
        gateways={"llm": gateway or MockLLMGateway()},
        identity=IdentityContext(workflow_id="test", execution_id=uuid4()),
    )


# ===========================================================================
# Schema tests
# ===========================================================================
class TestStoryboardSchemas:
    def test_story_analysis_defaults(self):
        sa = StoryAnalysis()
        assert sa.pacing == "moderate"
        assert sa.emotional_peaks == []

    def test_story_beat_defaults(self):
        sb = StoryBeat()
        assert sb.importance == "medium"
        assert sb.duration_seconds == 0

    def test_story_beat_result(self):
        sbr = StoryBeatResult(
            beats=[StoryBeat(beat_type="introduction", purpose="Hook viewer")],
            total_beats=1,
        )
        assert sbr.total_beats == 1
        assert sbr.beats[0].beat_type == "introduction"

    def test_planned_scene_defaults(self):
        ps = PlannedScene()
        assert ps.scene_number == 0
        assert ps.scene_type == ""

    def test_planned_scene_with_data(self):
        ps = PlannedScene(
            scene_number=1,
            scene_id="sc1",
            title="Intro",
            start_timestamp=0.0,
            end_timestamp=30.0,
            narration="Welcome",
            estimated_duration_seconds=30,
            scene_goal="Introduce topic",
            scene_type="talking",
        )
        assert ps.scene_id == "sc1"
        assert ps.estimated_duration_seconds == 30

    def test_scene_segmentation_result(self):
        ssr = SceneSegmentationResult(
            scenes=[PlannedScene(scene_id="sc1"), PlannedScene(scene_id="sc2")],
            total_scenes=2,
            total_duration_seconds=60,
        )
        assert ssr.total_scenes == 2

    def test_visual_plan_defaults(self):
        vp = VisualPlan()
        assert vp.color_palette == []
        assert vp.objects == []

    def test_visual_plan_with_data(self):
        vp = VisualPlan(
            scene_id="sc1",
            visual_description="AI brain visualization",
            composition="Rule of thirds",
            mood="curious",
            color_palette=["#FF0000", "#00FF00"],
            depth="deep",
        )
        assert vp.composition == "Rule of thirds"
        assert len(vp.color_palette) == 2

    def test_visual_storyboard_result(self):
        vsr = VisualStoryboardResult(
            visual_plans=[VisualPlan(scene_id="sc1")],
        )
        assert len(vsr.visual_plans) == 1

    def test_camera_plan_defaults(self):
        cp = CameraPlan()
        assert cp.motion_speed == "normal"

    def test_camera_plan_with_data(self):
        cp = CameraPlan(
            scene_id="sc1",
            camera_angle="medium",
            movement="pan_right",
            lens="standard",
        )
        assert cp.camera_angle == "medium"
        assert cp.movement == "pan_right"

    def test_camera_plan_result(self):
        cpr = CameraPlanResult(
            camera_plans=[CameraPlan(scene_id="sc1"), CameraPlan(scene_id="sc2")],
        )
        assert len(cpr.camera_plans) == 2

    def test_animation_plan_defaults(self):
        ap = AnimationPlan()
        assert ap.scene_effects == []

    def test_animation_plan_with_data(self):
        ap = AnimationPlan(
            scene_id="sc1",
            element_animation="Fade in elements",
            entrance_transition="Fade in",
            exit_transition="Fade out",
            scene_effects=["particle", "glow"],
        )
        assert ap.entrance_transition == "Fade in"
        assert len(ap.scene_effects) == 2

    def test_animation_plan_result(self):
        apr = AnimationPlanResult(
            animation_plans=[AnimationPlan(scene_id="sc1")],
        )
        assert len(apr.animation_plans) == 1

    def test_asset_scene_decision(self):
        asd = AssetSceneDecision(
            scene_id="sc1",
            asset_type="ai_image",
            confidence_score=0.85,
            estimated_generation_cost=0.05,
            estimated_rendering_complexity="low",
        )
        assert asd.confidence_score == 0.85
        assert asd.estimated_rendering_complexity == "low"

    def test_asset_decision_result(self):
        adr = AssetDecisionResult(
            decisions=[AssetSceneDecision(scene_id="sc1")],
            total_estimated_cost=0.05,
        )
        assert adr.total_estimated_cost == 0.05

    def test_continuity_result_defaults(self):
        cr = ContinuityResult()
        assert cr.aspect_ratio == "16:9"
        assert cr.consistency_score == 0.0

    def test_continuity_result_with_data(self):
        cr = ContinuityResult(
            consistency_score=0.85,
            issues=["Color mismatch in scene 3"],
        )
        assert cr.consistency_score == 0.85
        assert len(cr.issues) == 1

    def test_storyboard_review_result(self):
        rr = StoryboardReviewResult(
            overall_score=0.85,
            passed=True,
            issues=[],
            strengths=["Good visual variety"],
        )
        assert rr.passed is True
        assert rr.overall_score == 0.85

    def test_storyboard_quality_evaluation(self):
        qe = StoryboardQualityEvaluation(
            visual_diversity=0.85,
            overall_production_score=0.82,
        )
        assert qe.visual_diversity == 0.85

    def test_scene_package_defaults(self):
        sp = ScenePackage()
        assert sp.priority == "medium"
        assert sp.estimated_cost == 0.0

    def test_scene_package_with_data(self):
        sp = ScenePackage(
            scene_id="sc1",
            scene_number=1,
            title="Intro",
            narration="Welcome",
            duration_seconds=30,
            asset_type="ai_image",
            estimated_cost=0.05,
        )
        assert sp.scene_id == "sc1"
        assert sp.estimated_cost == 0.05

    def test_storyboard_package_defaults(self):
        sp = StoryboardPackage()
        assert sp.version == 1
        assert sp.is_ready is False

    def test_storyboard_package_ready(self):
        sp = StoryboardPackage(
            scenes=SceneSegmentationResult(total_scenes=3),
            scene_packages=[ScenePackage(scene_id="sc1"), ScenePackage(scene_id="sc2"), ScenePackage(scene_id="sc3")],
        )
        assert sp.is_ready is True
        assert sp.scene_count == 3

    def test_storyboard_package_total_cost(self):
        sp = StoryboardPackage(
            scene_packages=[
                ScenePackage(estimated_cost=0.05),
                ScenePackage(estimated_cost=0.10),
                ScenePackage(estimated_cost=0.15),
            ],
        )
        assert sp.total_estimated_cost == 0.30


# ===========================================================================
# Story Analyzer Agent tests
# ===========================================================================
class TestStoryAnalyzerAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        gateway = MockLLMGateway(response_data={
            "narrative_flow": "Introduction to conclusion",
            "emotional_peaks": ["Curiosity peak at 30s"],
            "pacing": "varied",
            "scene_boundaries": ["Boundary at 30s"],
            "emphasis_points": ["AI definition"],
            "dramatic_moments": ["AI revelation"],
            "visual_opportunities": ["Show AI brain"],
        })
        agent = StoryAnalyzerAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway)
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("story_analysis")
        assert data is not None
        assert data["pacing"] == "varied"
        assert ctx.state.storyboard.pacing_notes == "varied"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = StoryAnalyzerAgent()
        assert agent.agent_type == AgentType.STORY_PLANNER


# ===========================================================================
# Story Beat Agent tests
# ===========================================================================
class TestStoryBeatAgent:
    @pytest.mark.asyncio
    async def test_successful_beats(self):
        gateway = MockLLMGateway(response_data={
            "beats": [
                {"beat_type": "introduction", "purpose": "Hook viewer", "emotion": "curious", "duration_seconds": 30, "importance": "high", "description": "Opening hook"},
                {"beat_type": "explanation", "purpose": "Explain AI", "emotion": "neutral", "duration_seconds": 120, "importance": "critical", "description": "Core content"},
                {"beat_type": "conclusion", "purpose": "Wrap up", "emotion": "satisfied", "duration_seconds": 30, "importance": "medium", "description": "Closing"},
            ],
        })
        agent = StoryBeatAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "story_analysis": StoryAnalysis(narrative_flow="Test flow").model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("story_beats")
        assert data is not None
        assert data["total_beats"] == 3
        assert ctx.state.storyboard.act_count == 3

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = StoryBeatAgent()
        assert agent.agent_type == AgentType.STORY_PLANNER


# ===========================================================================
# Scene Segmentation Agent tests
# ===========================================================================
class TestSceneSegmentationAgent:
    @pytest.mark.asyncio
    async def test_successful_segmentation(self):
        gateway = MockLLMGateway(response_data={
            "scenes": [
                {"scene_number": 1, "scene_id": "sc1", "title": "Intro", "start_timestamp": 0.0, "end_timestamp": 30.0, "narration": "Welcome to AI", "estimated_duration_seconds": 30, "scene_goal": "Introduce", "scene_type": "talking"},
                {"scene_number": 2, "scene_id": "sc2", "title": "Explanation", "start_timestamp": 30.0, "end_timestamp": 180.0, "narration": "AI is...", "estimated_duration_seconds": 150, "scene_goal": "Explain", "scene_type": "diagram"},
            ],
        })
        agent = SceneSegmentationAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "story_beats": StoryBeatResult(beats=[StoryBeat(description="Beat 1")]).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("scenes")
        assert data is not None
        assert data["total_scenes"] == 2
        assert data["total_duration_seconds"] == 180

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = SceneSegmentationAgent()
        assert agent.agent_type == AgentType.SCENE_PLANNER


# ===========================================================================
# Visual Storyboard Agent tests
# ===========================================================================
class TestStoryboardVisualAgent:
    @pytest.mark.asyncio
    async def test_successful_visual_plans(self):
        gateway = MockLLMGateway(response_data={
            "visual_plans": [
                {"scene_id": "sc1", "visual_description": "AI brain", "composition": "Centered", "mood": "curious", "color_palette": ["#FF0000"], "depth": "deep", "visual_style": "modern"},
                {"scene_id": "sc2", "visual_description": "Diagram", "composition": "Rule of thirds", "mood": "informative", "color_palette": ["#00FF00"], "depth": "flat", "visual_style": "clean"},
            ],
        })
        agent = StoryboardAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(
                scenes=[PlannedScene(scene_id="sc1", title="Intro"), PlannedScene(scene_id="sc2", title="Body")],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("visual_plans")
        assert data is not None
        assert len(data["visual_plans"]) == 2

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = StoryboardAgent()
        assert agent.agent_type == AgentType.SCENE_PLANNER


# ===========================================================================
# Camera Planner Agent tests
# ===========================================================================
class TestCameraPlannerAgent:
    @pytest.mark.asyncio
    async def test_successful_camera_plans(self):
        gateway = MockLLMGateway(response_data={
            "camera_plans": [
                {"scene_id": "sc1", "camera_angle": "medium", "camera_distance": "medium", "lens": "standard", "movement": "static", "motion_speed": "normal", "focus_point": "Center"},
                {"scene_id": "sc2", "camera_angle": "close_up", "camera_distance": "close", "lens": "telephoto", "movement": "zoom_in", "motion_speed": "slow", "focus_point": "Top left"},
            ],
        })
        agent = CameraPlannerAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(scenes=[PlannedScene(scene_id="sc1")]).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1")]).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("camera_plans")
        assert data is not None
        assert len(data["camera_plans"]) == 2

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = CameraPlannerAgent()
        assert agent.agent_type == AgentType.SCENE_PLANNER


# ===========================================================================
# Animation Planner Agent tests
# ===========================================================================
class TestAnimationPlannerAgent:
    @pytest.mark.asyncio
    async def test_successful_animation_plans(self):
        gateway = MockLLMGateway(response_data={
            "animation_plans": [
                {"scene_id": "sc1", "element_animation": "Fade in", "text_animation": "Typewriter", "camera_motion": "Slow pan", "object_motion": "Float", "background_motion": "Subtle gradient", "timing": "2s delay", "entrance_transition": "Fade in", "exit_transition": "Fade out", "scene_effects": ["particle"]},
            ],
        })
        agent = AnimationPlannerAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(scenes=[PlannedScene(scene_id="sc1")]).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1")]).model_dump(),
            "camera_plans": CameraPlanResult(camera_plans=[CameraPlan(scene_id="sc1")]).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("animation_plans")
        assert data is not None
        assert len(data["animation_plans"]) == 1

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = AnimationPlannerAgent()
        assert agent.agent_type == AgentType.SCENE_PLANNER


# ===========================================================================
# Asset Decision Agent tests
# ===========================================================================
class TestAssetDecisionAgent:
    @pytest.mark.asyncio
    async def test_successful_decisions(self):
        gateway = MockLLMGateway(response_data={
            "decisions": [
                {"scene_id": "sc1", "asset_type": "ai_image", "confidence_score": 0.85, "estimated_generation_cost": 0.05, "estimated_rendering_complexity": "low", "rationale": "Good for static visual"},
                {"scene_id": "sc2", "asset_type": "animation_only", "confidence_score": 0.75, "estimated_generation_cost": 0.10, "estimated_rendering_complexity": "medium", "rationale": "Needs motion"},
            ],
        })
        agent = AssetDecisionAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(scenes=[PlannedScene(scene_id="sc1"), PlannedScene(scene_id="sc2")]).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1"), VisualPlan(scene_id="sc2")]).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("asset_decisions")
        assert data is not None
        assert len(data["decisions"]) == 2
        assert abs(data["total_estimated_cost"] - 0.15) < 1e-9

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = AssetDecisionAgent()
        assert agent.agent_type == AgentType.ASSET_DECISION


# ===========================================================================
# Continuity Agent tests
# ===========================================================================
class TestContinuityAgent:
    @pytest.mark.asyncio
    async def test_successful_continuity(self):
        gateway = MockLLMGateway(response_data={
            "character_consistency": "Consistent",
            "color_consistency": "Blue theme maintained",
            "object_consistency": "Consistent",
            "visual_style_consistency": "Modern style throughout",
            "camera_style_consistency": "Varied but coherent",
            "aspect_ratio": "16:9",
            "lighting_consistency": "Consistent",
            "transition_consistency": "Fade transitions throughout",
            "brand_style": "Educational tone maintained",
            "issues": ["Color shift in scene 3"],
            "consistency_score": 0.85,
        })
        agent = ContinuityAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(scenes=[PlannedScene(scene_id="sc1")]).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1")]).model_dump(),
            "camera_plans": CameraPlanResult(camera_plans=[CameraPlan(scene_id="sc1")]).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        data = ctx.state.storyboard.metadata.get("continuity")
        assert data is not None
        assert data["consistency_score"] == 0.85

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ContinuityAgent()
        assert agent.agent_type == AgentType.SCENE_PLANNER


# ===========================================================================
# Storyboard Review Agent tests
# ===========================================================================
class TestStoryboardReviewAgent:
    @pytest.mark.asyncio
    async def test_successful_review(self):
        gateway = MockLLMGateway(response_data={
            "scene_flow_score": 0.85,
            "visual_variety_score": 0.8,
            "scene_balance_score": 0.9,
            "narrative_consistency_score": 0.85,
            "camera_variety_score": 0.75,
            "animation_quality_score": 0.8,
            "budget_efficiency_score": 0.85,
            "rendering_feasibility_score": 0.9,
            "overall_score": 0.84,
            "issues": [],
            "strengths": ["Good visual variety"],
            "recommendations": ["Add more camera angles"],
            "passed": True,
        })
        agent = StoryboardReviewAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "scenes": SceneSegmentationResult(
                scenes=[PlannedScene(scene_id="sc1", scene_number=1, title="Intro", narration="Welcome", estimated_duration_seconds=30)],
                total_scenes=1,
                total_duration_seconds=30,
            ).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1")]).model_dump(),
            "camera_plans": CameraPlanResult(camera_plans=[CameraPlan(scene_id="sc1")]).model_dump(),
            "animation_plans": AnimationPlanResult(animation_plans=[AnimationPlan(scene_id="sc1")]).model_dump(),
            "asset_decisions": AssetDecisionResult(decisions=[AssetSceneDecision(scene_id="sc1", estimated_generation_cost=0.05)], total_estimated_cost=0.05).model_dump(),
            "continuity": ContinuityResult(consistency_score=0.85).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        review_data = ctx.state.storyboard.metadata.get("review")
        assert review_data is not None
        assert review_data["overall_score"] == 0.84
        assert review_data["passed"] is True

    @pytest.mark.asyncio
    async def test_assembles_storyboard_package(self):
        gateway = MockLLMGateway(response_data={
            "overall_score": 0.85,
            "passed": True,
            "scene_flow_score": 0.85,
            "visual_variety_score": 0.8,
            "scene_balance_score": 0.9,
            "narrative_consistency_score": 0.85,
            "camera_variety_score": 0.75,
            "animation_quality_score": 0.8,
            "budget_efficiency_score": 0.85,
            "rendering_feasibility_score": 0.9,
            "issues": [],
            "strengths": ["Good"],
            "recommendations": [],
        })
        agent = StoryboardReviewAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, storyboard_metadata={
            "story_analysis": StoryAnalysis(narrative_flow="Test flow").model_dump(),
            "story_beats": StoryBeatResult(beats=[StoryBeat(description="Beat 1")], total_beats=1).model_dump(),
            "scenes": SceneSegmentationResult(
                scenes=[PlannedScene(scene_id="sc1", scene_number=1, title="Intro", narration="Welcome", estimated_duration_seconds=30)],
                total_scenes=1,
                total_duration_seconds=30,
            ).model_dump(),
            "visual_plans": VisualStoryboardResult(visual_plans=[VisualPlan(scene_id="sc1", visual_description="AI brain")]).model_dump(),
            "camera_plans": CameraPlanResult(camera_plans=[CameraPlan(scene_id="sc1", camera_angle="medium")]).model_dump(),
            "animation_plans": AnimationPlanResult(animation_plans=[AnimationPlan(scene_id="sc1", entrance_transition="Fade in")]).model_dump(),
            "asset_decisions": AssetDecisionResult(decisions=[AssetSceneDecision(scene_id="sc1", asset_type="ai_image", estimated_generation_cost=0.05)], total_estimated_cost=0.05).model_dump(),
            "continuity": ContinuityResult(consistency_score=0.85).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        pkg_data = ctx.state.storyboard.metadata.get("storyboard_package")
        assert pkg_data is not None
        assert pkg_data["quality"]["overall_production_score"] == 0.85
        assert len(pkg_data["scene_packages"]) == 1
        assert pkg_data["scene_packages"][0]["scene_id"] == "sc1"
        assert pkg_data["scene_packages"][0]["asset_type"] == "ai_image"
        assert ctx.state.storyboard.narrative_structure == "Test flow"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = StoryboardReviewAgent()
        assert agent.agent_type == AgentType.STORY_PLANNER


# ===========================================================================
# Storyboard Workflow Graph tests
# ===========================================================================
class TestStoryboardWorkflowGraph:
    def test_build_graph(self):
        graph = StoryboardWorkflowGraph()
        graph.build_graph()
        assert len(graph.nodes) == 9

    def test_graph_metadata(self):
        graph = StoryboardWorkflowGraph()
        graph.build_graph()
        meta = graph.metadata
        assert meta.name == "storyboard_workflow"
        assert meta.entry_node == "story_analyzer"
        assert "storyboard_review" in meta.exit_nodes

    def test_graph_has_all_agents(self):
        graph = StoryboardWorkflowGraph()
        graph.build_graph()
        expected = {
            "story_analyzer", "story_beat", "scene_segmentation",
            "visual_storyboard", "camera_planner", "animation_planner",
            "asset_decision", "continuity", "storyboard_review",
        }
        assert set(graph.nodes.keys()) == expected

    def test_graph_edges_count(self):
        graph = StoryboardWorkflowGraph()
        graph.build_graph()
        assert len(graph.edges) == 8  # 9 nodes, 8 edges

    def test_graph_edge_chain(self):
        graph = StoryboardWorkflowGraph()
        graph.build_graph()
        edges = graph.edges
        chain = [(e.source, e.target) for e in edges]
        assert ("story_analyzer", "story_beat") in chain
        assert ("story_beat", "scene_segmentation") in chain
        assert ("scene_segmentation", "visual_storyboard") in chain
        assert ("visual_storyboard", "camera_planner") in chain
        assert ("camera_planner", "animation_planner") in chain
        assert ("animation_planner", "asset_decision") in chain
        assert ("asset_decision", "continuity") in chain
        assert ("continuity", "storyboard_review") in chain


# ===========================================================================
# Storyboard Events tests
# ===========================================================================
class TestStoryboardEvents:
    @pytest.mark.asyncio
    async def test_emit_storyboard_started(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_storyboard_started("AI Video", uuid4())

    @pytest.mark.asyncio
    async def test_emit_story_analyzed(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_story_analyzed(3, 5)

    @pytest.mark.asyncio
    async def test_emit_beats_generated(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_beats_generated(5)

    @pytest.mark.asyncio
    async def test_emit_scenes_planned(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_scenes_planned(10, 600)

    @pytest.mark.asyncio
    async def test_emit_visual_storyboard_generated(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_visual_storyboard_generated(10)

    @pytest.mark.asyncio
    async def test_emit_camera_planned(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_camera_planned(10)

    @pytest.mark.asyncio
    async def test_emit_animation_planned(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_animation_planned(10)

    @pytest.mark.asyncio
    async def test_emit_asset_decision_completed(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_asset_decision_completed(10, 0.50)

    @pytest.mark.asyncio
    async def test_emit_continuity_validated(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_continuity_validated(0.85, 2)

    @pytest.mark.asyncio
    async def test_emit_storyboard_reviewed(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_storyboard_reviewed(0.85, True, 1)

    @pytest.mark.asyncio
    async def test_emit_storyboard_completed(self):
        emitter = StoryboardEventEmitter(event_bus=None)
        await emitter.emit_storyboard_completed(uuid4(), 10, 0.50, 0.85)

    def test_event_constants(self):
        assert StoryboardEvents.STORYBOARD_STARTED == "StoryboardStarted"
        assert StoryboardEvents.STORY_ANALYZED == "StoryAnalyzed"
        assert StoryboardEvents.BEATS_GENERATED == "BeatsGenerated"
        assert StoryboardEvents.SCENES_PLANNED == "ScenesPlanned"
        assert StoryboardEvents.VISUAL_STORYBOARD_GENERATED == "VisualStoryboardGenerated"
        assert StoryboardEvents.CAMERA_PLANNED == "CameraPlanned"
        assert StoryboardEvents.ANIMATION_PLANNED == "AnimationPlanned"
        assert StoryboardEvents.ASSET_DECISION_COMPLETED == "AssetDecisionCompleted"
        assert StoryboardEvents.CONTINUITY_VALIDATED == "ContinuityValidated"
        assert StoryboardEvents.STORYBOARD_REVIEWED == "StoryboardReviewed"
        assert StoryboardEvents.STORYBOARD_COMPLETED == "StoryboardCompleted"


# ===========================================================================
# Prompt Template tests
# ===========================================================================
class TestStoryboardPrompts:
    def test_story_analyzer_prompt(self):
        from src.ai.agents.storyboard.prompts import STORY_ANALYZER_PROMPT
        assert STORY_ANALYZER_PROMPT.name == "story_analyzer"
        assert "{{full_script}}" in STORY_ANALYZER_PROMPT.template

    def test_story_beat_prompt(self):
        from src.ai.agents.storyboard.prompts import STORY_BEAT_PROMPT
        assert STORY_BEAT_PROMPT.name == "story_beat"
        assert "{{story_analysis}}" in STORY_BEAT_PROMPT.template

    def test_scene_segmentation_prompt(self):
        from src.ai.agents.storyboard.prompts import SCENE_SEGMENTATION_PROMPT
        assert SCENE_SEGMENTATION_PROMPT.name == "scene_segmentation"
        assert "{{story_beats}}" in SCENE_SEGMENTATION_PROMPT.template

    def test_visual_storyboard_prompt(self):
        from src.ai.agents.storyboard.prompts import VISUAL_STORYBOARD_PROMPT
        assert VISUAL_STORYBOARD_PROMPT.name == "visual_storyboard"
        assert "{{scenes}}" in VISUAL_STORYBOARD_PROMPT.template

    def test_camera_planner_prompt(self):
        from src.ai.agents.storyboard.prompts import CAMERA_PLANNER_PROMPT
        assert CAMERA_PLANNER_PROMPT.name == "camera_planner"
        assert "{{visual_plans}}" in CAMERA_PLANNER_PROMPT.template

    def test_animation_planner_prompt(self):
        from src.ai.agents.storyboard.prompts import ANIMATION_PLANNER_PROMPT
        assert ANIMATION_PLANNER_PROMPT.name == "animation_planner"
        assert "{{camera_plans}}" in ANIMATION_PLANNER_PROMPT.template

    def test_asset_decision_prompt(self):
        from src.ai.agents.storyboard.prompts import ASSET_DECISION_PROMPT
        assert ASSET_DECISION_PROMPT.name == "asset_decision"
        assert "{{scenes}}" in ASSET_DECISION_PROMPT.template

    def test_continuity_prompt(self):
        from src.ai.agents.storyboard.prompts import CONTINUITY_PROMPT
        assert CONTINUITY_PROMPT.name == "continuity"
        assert "{{brand_style}}" in CONTINUITY_PROMPT.template

    def test_storyboard_review_prompt(self):
        from src.ai.agents.storyboard.prompts import STORYBOARD_REVIEW_PROMPT
        assert STORYBOARD_REVIEW_PROMPT.name == "storyboard_review"
        assert "{{scene_count}}" in STORYBOARD_REVIEW_PROMPT.template

    def test_all_prompts_registered(self):
        from src.ai.agents.storyboard.prompts import STORYBOARD_PROMPTS
        assert len(STORYBOARD_PROMPTS) == 9
        for name in ["story_analyzer", "story_beat", "scene_segmentation",
                      "visual_storyboard", "camera_planner", "animation_planner",
                      "asset_decision", "continuity", "storyboard_review"]:
            assert name in STORYBOARD_PROMPTS

    def test_all_prompts_have_versions(self):
        from src.ai.agents.storyboard.prompts import STORYBOARD_PROMPTS
        for name, template in STORYBOARD_PROMPTS.items():
            assert template.version != "", f"Prompt {name} has no version"


# ===========================================================================
# Integration test — full storyboard pipeline
# ===========================================================================
class TestStoryboardPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the full storyboard pipeline with all 9 agents."""
        responses = iter([
            # Story Analyzer
            {"narrative_flow": "Intro to conclusion", "emotional_peaks": ["Peak 1"], "pacing": "moderate", "scene_boundaries": ["30s"], "emphasis_points": ["AI def"], "dramatic_moments": ["Reveal"], "visual_opportunities": ["Brain visual"]},
            # Story Beat
            {"beats": [{"beat_type": "introduction", "purpose": "Hook", "emotion": "curious", "duration_seconds": 30, "importance": "high", "description": "Opening"}, {"beat_type": "conclusion", "purpose": "Wrap", "emotion": "satisfied", "duration_seconds": 30, "importance": "medium", "description": "Closing"}]},
            # Scene Segmentation
            {"scenes": [{"scene_number": 1, "scene_id": "sc1", "title": "Intro", "start_timestamp": 0.0, "end_timestamp": 30.0, "narration": "Welcome to AI", "estimated_duration_seconds": 30, "scene_goal": "Introduce", "scene_type": "talking"}, {"scene_number": 2, "scene_id": "sc2", "title": "Body", "start_timestamp": 30.0, "end_timestamp": 180.0, "narration": "AI is...", "estimated_duration_seconds": 150, "scene_goal": "Explain", "scene_type": "diagram"}]},
            # Visual Storyboard
            {"visual_plans": [{"scene_id": "sc1", "visual_description": "AI brain", "composition": "Centered", "mood": "curious", "color_palette": ["#FF0000"], "depth": "deep", "visual_style": "modern"}, {"scene_id": "sc2", "visual_description": "Diagram", "composition": "Rule of thirds", "mood": "informative", "color_palette": ["#00FF00"], "depth": "flat", "visual_style": "clean"}]},
            # Camera Planner
            {"camera_plans": [{"scene_id": "sc1", "camera_angle": "medium", "camera_distance": "medium", "lens": "standard", "movement": "static", "motion_speed": "normal", "focus_point": "Center"}, {"scene_id": "sc2", "camera_angle": "close_up", "camera_distance": "close", "lens": "telephoto", "movement": "zoom_in", "motion_speed": "slow", "focus_point": "Top"}]},
            # Animation Planner
            {"animation_plans": [{"scene_id": "sc1", "element_animation": "Fade in", "text_animation": "Typewriter", "camera_motion": "Static", "object_motion": "None", "background_motion": "Gradient", "timing": "2s", "entrance_transition": "Fade in", "exit_transition": "Fade out", "scene_effects": ["particle"]}, {"scene_id": "sc2", "element_animation": "Slide", "text_animation": "Reveal", "camera_motion": "Zoom", "object_motion": "Pulse", "background_motion": "None", "timing": "1s", "entrance_transition": "Slide in", "exit_transition": "Slide out", "scene_effects": []}]},
            # Asset Decision
            {"decisions": [{"scene_id": "sc1", "asset_type": "ai_image", "confidence_score": 0.85, "estimated_generation_cost": 0.05, "estimated_rendering_complexity": "low", "rationale": "Static visual"}, {"scene_id": "sc2", "asset_type": "animation_only", "confidence_score": 0.75, "estimated_generation_cost": 0.10, "estimated_rendering_complexity": "medium", "rationale": "Needs motion"}]},
            # Continuity
            {"character_consistency": "Consistent", "color_consistency": "Consistent", "object_consistency": "Consistent", "visual_style_consistency": "Modern", "camera_style_consistency": "Coherent", "aspect_ratio": "16:9", "lighting_consistency": "Consistent", "transition_consistency": "Consistent", "brand_style": "Educational", "issues": [], "consistency_score": 0.9},
            # Storyboard Review
            {"scene_flow_score": 0.85, "visual_variety_score": 0.8, "scene_balance_score": 0.9, "narrative_consistency_score": 0.85, "camera_variety_score": 0.75, "animation_quality_score": 0.8, "budget_efficiency_score": 0.85, "rendering_feasibility_score": 0.9, "overall_score": 0.84, "issues": [], "strengths": ["Good variety"], "recommendations": [], "passed": True},
        ])

        class PipelineGateway:
            async def generate(self, prompt, **kwargs):
                class Result:
                    success = True
                    output = json.dumps(next(responses))
                    cost_usd = 0.05
                    input_tokens = 100
                    output_tokens = 50
                    total_tokens = 150
                    latency_ms = 100
                    provider = "gemini"
                    model = "gemini-2.0-flash"
                    metadata = {}
                    correlation_id = kwargs.get("correlation_id")
                return Result()

        gateway = PipelineGateway()
        ctx = make_context(gateway=gateway)

        agents = [
            StoryAnalyzerAgent(),
            StoryBeatAgent(),
            SceneSegmentationAgent(),
            StoryboardAgent(),
            CameraPlannerAgent(),
            AnimationPlannerAgent(),
            AssetDecisionAgent(),
            ContinuityAgent(),
            StoryboardReviewAgent(),
        ]

        for agent in agents:
            agent.enable_quality_check = False
            agent.enable_artifact_creation = False

        for agent in agents:
            result = await agent.run_agent(ctx)
            assert result.success is True, f"Agent {agent.name} failed: {result.error}"

        # Verify final storyboard package
        pkg_data = ctx.state.storyboard.metadata.get("storyboard_package")
        assert pkg_data is not None
        assert pkg_data["quality"]["overall_production_score"] == 0.84
        assert len(pkg_data["scene_packages"]) == 2
        assert pkg_data["scene_packages"][0]["scene_id"] == "sc1"
        assert pkg_data["scene_packages"][1]["scene_id"] == "sc2"
        assert abs(pkg_data["estimated_budget"] - 0.15) < 1e-9
