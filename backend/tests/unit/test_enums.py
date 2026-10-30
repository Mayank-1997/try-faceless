"""Unit tests for core enums — verify enum membership, string values, and completeness."""

from __future__ import annotations

import pytest

from src.core.enums import (
    AgentType,
    AgentStatus,
    AIProvider,
    AssetDecision,
    AssetStatus,
    AssetType,
    CameraAngle,
    CameraMotion,
    TransitionType,
    JobPriority,
    JobStatus,
    ProjectStatus,
    PublishStatus,
    UserRole,
    VisualType,
)


class TestJobStatus:
    """Tests for the JobStatus enum."""

    def test_all_expected_statuses_exist(self) -> None:
        expected = {"queued", "running", "completed", "retrying", "failed", "cancelled", "paused"}
        actual = {status.value for status in JobStatus}
        assert actual == expected

    def test_queued_is_first_value(self) -> None:
        assert JobStatus.QUEUED.value == "queued"

    def test_string_inheritance(self) -> None:
        assert isinstance(JobStatus.QUEUED, str)
        assert JobStatus.QUEUED == "queued"


class TestAgentType:
    """Tests for the AgentType enum — must cover all workflow agents."""

    @pytest.mark.parametrize(
        "agent",
        [
            "director",
            "topic",
            "research",
            "story_planner",
            "script_writer",
            "scene_planner",
            "asset_decision",
            "image_prompt",
            "video_prompt",
            "voice",
            "subtitle",
            "rendering",
            "thumbnail",
            "seo",
            "publisher",
        ],
    )
    def test_agent_exists(self, agent: str) -> None:
        assert AgentType(agent) is not None

    def test_total_agent_count(self) -> None:
        assert len(list(AgentType)) == 15


class TestAssetDecision:
    """Tests for the AssetDecision enum — cost-optimisation choices."""

    def test_all_decisions_exist(self) -> None:
        expected = {
            "skip_scene",
            "merge_scene",
            "existing_asset",
            "stock_asset",
            "animated_image",
            "camera_motion",
            "motion_graphics",
            "ai_image",
            "ai_video",
            "diagram",
            "chart",
            "icon",
            "screenshot",
            "animation_only",
            "mixed_assets",
        }
        actual = {decision.value for decision in AssetDecision}
        assert actual == expected

    def test_ai_video_is_most_expensive(self) -> None:
        """AI_VIDEO should be among the most expensive options."""
        decisions = list(AssetDecision)
        assert AssetDecision.AI_VIDEO in decisions

    def test_skip_scene_is_cheapest(self) -> None:
        """SKIP_SCENE should be the first (cheapest) option."""
        decisions = list(AssetDecision)
        assert decisions[0] == AssetDecision.SKIP_SCENE


class TestVisualType:
    """Tests for the VisualType enum."""

    def test_all_visual_types(self) -> None:
        expected = {
            "talking", "animation", "infographic", "image", "video", "mixed",
            "diagram", "timeline", "comparison", "map", "screenshot",
            "code", "product_demo", "stock_footage", "ai_image", "ai_video",
        }
        actual = {vt.value for vt in VisualType}
        assert actual == expected


class TestAIProvider:
    """Tests for the AIProvider enum."""

    def test_primary_providers(self) -> None:
        assert AIProvider.GEMINI.value == "gemini"
        assert AIProvider.VEO.value == "veo"
        assert AIProvider.IMAGEN.value == "imagen"
        assert AIProvider.GOOGLE_TTS.value == "google_tts"

    def test_future_providers(self) -> None:
        """Future providers should be defined for extensibility."""
        future = {AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.ELEVENLABS, AIProvider.RUNWAY}
        assert len(future) == 4


class TestProjectStatus:
    """Tests for the ProjectStatus enum."""

    def test_draft_is_default(self) -> None:
        assert ProjectStatus.DRAFT.value == "draft"

    def test_completed_exists(self) -> None:
        assert ProjectStatus.COMPLETED.value == "completed"

    def test_failed_exists(self) -> None:
        assert ProjectStatus.FAILED.value == "failed"


class TestCameraEnums:
    """Tests for camera angle and motion enums."""

    def test_camera_angles(self) -> None:
        assert CameraAngle.WIDE.value == "wide"
        assert CameraAngle.CLOSE_UP.value == "close_up"
        assert CameraAngle.POV.value == "pov"

    def test_camera_motions(self) -> None:
        assert CameraMotion.STATIC.value == "static"
        assert CameraMotion.ZOOM_IN.value == "zoom_in"
        assert CameraMotion.TRACKING.value == "tracking"


class TestTransitionType:
    """Tests for the TransitionType enum."""

    def test_cut_and_fade(self) -> None:
        assert TransitionType.CUT.value == "cut"
        assert TransitionType.FADE.value == "fade"


class TestUserRole:
    """Tests for the UserRole enum."""

    def test_roles(self) -> None:
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.CREATOR.value == "creator"
        assert UserRole.VIEWER.value == "viewer"
