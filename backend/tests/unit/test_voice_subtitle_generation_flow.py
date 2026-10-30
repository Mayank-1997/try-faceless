"""Tests for VOICE_GENERATION and SUBTITLE_GENERATION steps with mocked gateways."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.agents.storyboard.schema import (
    CameraPlan,
    ScenePackage,
    StoryboardPackage,
    VisualPlan,
)
from src.ai.providers.edge_tts_provider import EdgeTTSProvider
from src.application.dto.responses import GenerationResult
from src.core.enums import AIProvider, AssetGenerationStatus, StorageType
from src.core.exceptions import AIProviderError, VoiceGatewayError
from src.infrastructure.tasks.workflow_tasks import _create_step_output, _narration_to_srt
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_scene_package(
    scene_number: int,
    title: str,
    narration: str,
) -> ScenePackage:
    return ScenePackage(
        scene_id=f"scene-{scene_number}",
        scene_number=scene_number,
        title=title,
        narration=narration,
        duration_seconds=6,
        visual_prompt_summary="A dramatic visual",
        asset_type="stock_image",
        camera_plan=CameraPlan(
            scene_id=f"scene-{scene_number}",
            camera_angle="wide",
            lens="standard",
            movement="pan_left",
        ),
        visual_plan=VisualPlan(
            scene_id=f"scene-{scene_number}",
            visual_description="A dramatic visual",
            lighting="golden hour",
            composition="rule of thirds",
        ),
        quality_score=0.9,
    )


def _make_storyboard_package() -> StoryboardPackage:
    return StoryboardPackage(
        scene_packages=[
            _make_scene_package(
                1,
                "Opening Hook",
                "The solar system is a vast and mysterious place.",
            ),
            _make_scene_package(
                2,
                "The Sun",
                "At the center sits our Sun, a giant ball of burning plasma.",
            ),
            _make_scene_package(
                3,
                "The Planets",
                "Eight planets orbit the Sun, each with its own story.",
            ),
        ]
    )


def _voice_result(provider: str = "edge_tts") -> GenerationResult:
    return GenerationResult(
        success=True,
        provider=provider,
        model="en-US-ChristopherNeural",
        output=b"ID3-fake-mp3-bytes",
        cost_usd=0.0,
        latency_ms=200,
    )


def _make_service_with_scenes(package: StoryboardPackage):
    """Create a mocked ProjectService with scenes already created."""
    service = MagicMock()
    created_assets: list = []
    updated_scenes: list = []

    scenes = []
    for sp in package.scene_packages:
        scene = SimpleNamespace(
            id=uuid4(),
            scene_number=sp.scene_number,
            title=sp.title,
            narration=sp.narration,
            duration_seconds=sp.duration_seconds,
            subtitle=None,
            generation_status="pending",
        )
        scenes.append(scene)

    storyboard = SimpleNamespace(id=uuid4())
    service._storyboard_repo.get_latest_version = AsyncMock(return_value=storyboard)

    async def _create_scene(scene):
        return scene

    async def _get_scenes(pid):
        return list(scenes)

    async def _update_scene(scene):
        updated_scenes.append(scene)
        return scene

    async def _create_asset(asset):
        created_assets.append(asset)
        return asset

    service._scene_repo.create = AsyncMock(side_effect=_create_scene)
    service._scene_repo.get_by_project = AsyncMock(side_effect=_get_scenes)
    service._scene_repo.update = AsyncMock(side_effect=_update_scene)
    service._asset_repo.create = AsyncMock(side_effect=_create_asset)

    return service, scenes, created_assets, updated_scenes


def _make_container(voice_result: GenerationResult | None = None):
    container = MagicMock()
    container.voice_gateway = MagicMock()
    if voice_result is not None:
        container.voice_gateway.generate_speech = AsyncMock(return_value=voice_result)
    else:
        container.voice_gateway.generate_speech = AsyncMock(
            side_effect=VoiceGatewayError("No voice providers registered")
        )

    async def _upload(data, path, content_type="application/octet-stream"):
        return f"local:///storage/{path}"

    container.storage_gateway = MagicMock()
    container.storage_gateway.upload = AsyncMock(side_effect=_upload)
    return container


# ---------------------------------------------------------------------------
# SRT generation tests
# ---------------------------------------------------------------------------
class TestNarrationToSrt:
    def test_basic_srt_structure(self) -> None:
        narration = "The solar system is vast and full of wonders."
        srt = _narration_to_srt(narration, scene_number=1, duration_seconds=6)
        lines = srt.strip().split("\n")
        # SRT: index, timestamp, text, blank, ...
        assert lines[0] == "1"
        assert " --> " in lines[1]
        assert lines[1].startswith("00:00:00,")
        # 9 words gets chunked into 8+1, so first line has 8 words
        assert lines[2] == "The solar system is vast and full of"
        assert srt.endswith("\n")

    def test_short_narration_single_chunk(self) -> None:
        narration = "Hello world."
        srt = _narration_to_srt(narration, scene_number=1, duration_seconds=3)
        lines = srt.strip().split("\n")
        assert lines[0] == "1"
        assert " --> " in lines[1]
        assert lines[2] == "Hello world."

    def test_long_narration_is_chunked(self) -> None:
        narration = (
            "The solar system consists of the Sun and everything that orbits it "
            "including eight planets dozens of moons millions of asteroids and "
            "countless comets all held together by gravity."
        )
        srt = _narration_to_srt(narration, scene_number=1, duration_seconds=12)
        blocks = [b for b in srt.strip().split("\n\n") if b.strip()]
        # ~44 words / 8 per chunk = ~6 chunks
        assert len(blocks) >= 4
        # Each block has: index, timestamp, text
        for block in blocks:
            parts = block.strip().split("\n")
            assert len(parts) == 3
            int(parts[0])  # index is numeric
            assert " --> " in parts[1]
            assert len(parts[2].split()) <= 10  # chunk has at most 10 words

    def test_empty_narration_returns_empty(self) -> None:
        assert _narration_to_srt("", scene_number=1, duration_seconds=5) == ""
        assert _narration_to_srt("   ", scene_number=1, duration_seconds=5) == ""

    def test_single_word(self) -> None:
        srt = _narration_to_srt("Hello", scene_number=1, duration_seconds=2)
        assert "Hello" in srt
        assert "00:00:00,000 --> 00:00:02,000" in srt


# ---------------------------------------------------------------------------
# Voice generation step tests
# ---------------------------------------------------------------------------
class TestVoiceGenerationStep:
    @pytest.mark.asyncio
    async def test_voice_generation_with_mocked_gateway(self) -> None:
        """VOICE_GENERATION creates VoiceAsset records and uploads MP3s."""
        project_id = uuid4()
        workflow_id = uuid4()
        project = SimpleNamespace(
            id=project_id,
            title="The Solar System in 60 Seconds",
            description="A space documentary",
        )

        package = _make_storyboard_package()
        workflow_state = WorkflowState()
        workflow_state.storyboard.metadata["storyboard_package"] = package.model_dump()

        service, scenes, created_assets, updated_scenes = _make_service_with_scenes(package)
        container = _make_container(_voice_result())

        state = await _create_step_output(
            service=service,
            engine=None,
            container=container,
            workflow_state=workflow_state,
            project=project,
            workflow_id=workflow_id,
            step="voice_generation",
        )

        # Every scene with narration should produce a voice asset
        assert len(created_assets) == 3
        for asset in created_assets:
            assert asset.asset_type.value == "voice"
            assert asset.storage_type == StorageType.LOCAL
            assert asset.storage_ref.startswith("local:///storage/projects/")
            assert asset.storage_ref.endswith(".mp3")
            assert asset.generation_status == AssetGenerationStatus.READY

        # Langfuse step IO should be recorded
        step_input = state.metadata.custom.get("step_input", {})
        step_output = state.metadata.custom.get("step_output", {})
        assert step_input.get("step") == "voice_generation"
        assert len(step_input.get("scene_numbers", [])) == 3
        assert len(step_output.get("voice_assets", [])) == 3
        assert step_output.get("errors") == []

    @pytest.mark.asyncio
    async def test_voice_generation_failure_is_recorded(self) -> None:
        """When the gateway raises, errors are captured and the workflow continues."""
        project_id = uuid4()
        workflow_id = uuid4()
        project = SimpleNamespace(
            id=project_id,
            title="Test Project",
            description="Test",
        )

        package = _make_storyboard_package()
        workflow_state = WorkflowState()
        workflow_state.storyboard.metadata["storyboard_package"] = package.model_dump()

        service, scenes, created_assets, _ = _make_service_with_scenes(package)
        container = _make_container(voice_result=None)  # gateway raises

        state = await _create_step_output(
            service=service,
            engine=None,
            container=container,
            workflow_state=workflow_state,
            project=project,
            workflow_id=workflow_id,
            step="voice_generation",
        )

        # No assets created, but errors are recorded in step_output
        assert len(created_assets) == 0
        step_output = state.metadata.custom.get("step_output", {})
        assert step_output.get("step") == "voice_generation"
        assert len(step_output.get("voice_assets", [])) == 0
        assert len(step_output.get("errors", [])) == 3
        for err in step_output["errors"]:
            assert "scene_number" in err
            assert "error" in err


# ---------------------------------------------------------------------------
# Subtitle generation step tests
# ---------------------------------------------------------------------------
class TestSubtitleGenerationStep:
    @pytest.mark.asyncio
    async def test_subtitle_generation_creates_srt_assets(self) -> None:
        """SUBTITLE_GENERATION creates SubtitleAsset records and uploads SRTs."""
        project_id = uuid4()
        workflow_id = uuid4()
        project = SimpleNamespace(
            id=project_id,
            title="The Solar System in 60 Seconds",
            description="A space documentary",
        )

        package = _make_storyboard_package()
        workflow_state = WorkflowState()
        workflow_state.storyboard.metadata["storyboard_package"] = package.model_dump()

        service, scenes, created_assets, updated_scenes = _make_service_with_scenes(package)
        container = _make_container()

        state = await _create_step_output(
            service=service,
            engine=None,
            container=container,
            workflow_state=workflow_state,
            project=project,
            workflow_id=workflow_id,
            step="subtitle_generation",
        )

        # Every scene with narration should produce a subtitle asset
        assert len(created_assets) == 3
        for asset in created_assets:
            assert asset.asset_type.value == "subtitle"
            assert asset.storage_type == StorageType.LOCAL
            assert asset.storage_ref.startswith("local:///storage/projects/")
            assert asset.storage_ref.endswith(".srt")
            assert asset.generation_status == AssetGenerationStatus.READY
            assert asset.language == "en"
            assert asset.format == "srt"
            assert asset.word_count > 0

        # Each scene should have its subtitle field set
        for scene in updated_scenes:
            assert scene.subtitle is not None
            assert "-->" in scene.subtitle  # valid SRT

        # Langfuse step IO
        step_output = state.metadata.custom.get("step_output", {})
        assert step_output.get("step") == "subtitle_generation"
        assert len(step_output.get("subtitles_generated", [])) == 3
        assert step_output.get("errors") == []


# ---------------------------------------------------------------------------
# EdgeTTS provider unit tests (mocked, no network)
# ---------------------------------------------------------------------------
class TestEdgeTTSProvider:
    def test_provider_name(self) -> None:
        provider = EdgeTTSProvider()
        assert provider.provider_name == AIProvider.EDGE_TTS

    def test_cost_is_zero(self) -> None:
        provider = EdgeTTSProvider()
        assert provider.calculate_cost(10000) == 0.0

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self) -> None:
        provider = EdgeTTSProvider()
        health = await provider.health_check()
        assert health.healthy is False

    def test_not_initialized_raises(self) -> None:
        provider = EdgeTTSProvider()
        with pytest.raises(AIProviderError):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                provider.generate_speech("hello")
            )
