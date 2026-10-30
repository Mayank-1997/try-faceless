"""Tests for the WorkflowState module."""

from __future__ import annotations

import pytest
from uuid import uuid4

from src.core.enums import (
    AgentType,
    AssetType,
    JobStatus,
    ProjectInputType,
    ProjectStatus,
    VisualType,
)
from src.workflow.state import (
    AssetData,
    CostData,
    ExecutionStatus,
    ProjectInfo,
    SceneData,
    ScriptData,
    TokenUsageData,
    WorkflowState,
)


class TestWorkflowState:
    def test_default_creation(self):
        state = WorkflowState()
        assert state.project is not None
        assert state.scenes == []
        assert state.assets == []
        assert state.cost.total_cost_usd == 0.0
        assert state.token_usage.total_tokens == 0

    def test_add_cost(self):
        state = WorkflowState()
        state.add_cost(0.05, "llm")
        assert state.cost.total_cost_usd == 0.05
        assert state.cost.llm_cost_usd == 0.05

        state.add_cost(0.10, "image")
        assert state.cost.total_cost_usd == pytest.approx(0.15)
        assert state.cost.image_cost_usd == 0.10

    def test_add_tokens(self):
        state = WorkflowState()
        state.add_tokens(input_t=500, output_t=200)
        assert state.token_usage.input_tokens == 500
        assert state.token_usage.output_tokens == 200
        assert state.token_usage.total_tokens == 700

    def test_get_scene_by_number(self):
        state = WorkflowState()
        state.scenes = [
            SceneData(scene_number=1, title="Scene 1"),
            SceneData(scene_number=2, title="Scene 2"),
            SceneData(scene_number=3, title="Scene 3"),
        ]
        scene = state.get_scene(2)
        assert scene is not None
        assert scene.title == "Scene 2"

    def test_get_scene_not_found(self):
        state = WorkflowState()
        state.scenes = [SceneData(scene_number=1, title="Scene 1")]
        assert state.get_scene(99) is None

    def test_get_assets_for_scene(self):
        state = WorkflowState()
        state.assets = [
            AssetData(scene_number=1, asset_type=AssetType.IMAGE),
            AssetData(scene_number=1, asset_type=AssetType.VIDEO),
            AssetData(scene_number=2, asset_type=AssetType.IMAGE),
        ]
        scene1_assets = state.get_assets_for_scene(1)
        assert len(scene1_assets) == 2
        scene2_assets = state.get_assets_for_scene(2)
        assert len(scene2_assets) == 1

    def test_is_complete(self):
        state = WorkflowState()
        assert state.is_complete is False

        state.execution.completed_agents = [AgentType.DIRECTOR]
        state.rendering.status = JobStatus.COMPLETED
        assert state.is_complete is True

    def test_is_complete_with_failures(self):
        state = WorkflowState()
        state.execution.completed_agents = [AgentType.DIRECTOR]
        state.execution.failed_agents = [AgentType.SCENE_PLANNER]
        state.rendering.status = JobStatus.COMPLETED
        assert state.is_complete is False
        assert state.has_failures is True

    def test_has_failures(self):
        state = WorkflowState()
        assert state.has_failures is False
        state.execution.failed_agents = [AgentType.DIRECTOR]
        assert state.has_failures is True


class TestExecutionStatus:
    def test_mark_agent_complete(self):
        status = ExecutionStatus()
        status.mark_agent_complete(AgentType.DIRECTOR)
        assert AgentType.DIRECTOR in status.completed_agents

    def test_mark_agent_failed(self):
        status = ExecutionStatus()
        status.mark_agent_failed(AgentType.DIRECTOR, "API timeout")
        assert AgentType.DIRECTOR in status.failed_agents
        assert "API timeout" in status.errors[0]

    def test_mark_agent_skipped(self):
        status = ExecutionStatus()
        status.mark_agent_skipped(AgentType.SCENE_PLANNER)
        assert AgentType.SCENE_PLANNER in status.skipped_agents

    def test_progress_percentage(self):
        status = ExecutionStatus(total_steps=10, completed_steps=5)
        assert status.progress_percentage == 50.0

    def test_progress_percentage_zero(self):
        status = ExecutionStatus(total_steps=0)
        assert status.progress_percentage == 0.0


class TestCostData:
    def test_add_llm(self):
        cost = CostData()
        cost.add(0.05, "llm")
        assert cost.total_cost_usd == 0.05
        assert cost.llm_cost_usd == 0.05

    def test_add_multiple_categories(self):
        cost = CostData()
        cost.add(0.05, "llm")
        cost.add(0.10, "image")
        cost.add(0.20, "video")
        cost.add(0.02, "voice")
        cost.add(0.01, "render")
        assert cost.total_cost_usd == pytest.approx(0.38)
        assert cost.llm_cost_usd == 0.05
        assert cost.image_cost_usd == 0.10
        assert cost.video_cost_usd == 0.20
        assert cost.voice_cost_usd == 0.02
        assert cost.render_cost_usd == 0.01


class TestTokenUsageData:
    def test_add(self):
        usage = TokenUsageData()
        usage.add(input_t=100, output_t=50, cached_t=25)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cached_tokens == 25
        assert usage.total_tokens == 175

    def test_add_default(self):
        usage = TokenUsageData()
        usage.add()
        assert usage.total_tokens == 0
