"""Tests for the SCENE_PLANNING -> ASSET_GENERATION flow with mocked gateways."""

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
from src.ai.gateway.image_gateway import ImageGateway
from src.ai.gateway.video_gateway import VideoGateway
from src.ai.gateway.voice_gateway import VoiceGateway
from src.application.dto.responses import GenerationResult
from src.core.enums import SceneGenerationStatus, VisualType
from src.infrastructure.tasks.workflow_tasks import _create_step_output
from src.workflow.state import WorkflowState


def test_gateways_expose_expected_method_names() -> None:
    """The workflow calls generate_image/generate_video/generate_speech.

    This guards against method-name typos in the real gateway classes
    (e.g. the old ``generrate_image``), which mocked gateway tests
    cannot catch.
    """
    assert hasattr(ImageGateway, "generate_image")
    assert hasattr(VideoGateway, "generate_video")
    assert hasattr(VoiceGateway, "generate_speech")


def _make_scene_package(
    scene_number: int,
    title: str,
    narration: str,
    asset_type: str,
    visual_description: str,
) -> ScenePackage:
    return ScenePackage(
        scene_id=f"scene-{scene_number}",
        scene_number=scene_number,
        title=title,
        narration=narration,
        duration_seconds=5,
        visual_prompt_summary=visual_description,
        asset_type=asset_type,
        camera_plan=CameraPlan(
            scene_id=f"scene-{scene_number}",
            camera_angle="wide",
            lens="standard",
            movement="pan_left",
        ),
        visual_plan=VisualPlan(
            scene_id=f"scene-{scene_number}",
            visual_description=visual_description,
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
                "The Crash",
                "The sky didn't just break; it shattered.",
                "stock_image",
                "A fourteen-year-old boy on a silent alien beach, wreckage smouldering behind him.",
            ),
            _make_scene_package(
                2,
                "Primal Ingenuity",
                "Surviving the first week required turning terror into mechanics.",
                "ai_image",
                "A crude solar still and bow-drill fire kit arranged on jungle floor.",
            ),
            _make_scene_package(
                3,
                "The Rescue",
                "A rescue vessel cuts through the mist.",
                "stock_footage",
                "A Coast Guard vessel slicing through open ocean toward camera.",
            ),
        ]
    )


def _image_result() -> GenerationResult:
    return GenerationResult(
        success=True,
        provider="stock_image",
        model="pexels",
        output=b"\x89PNG-fake-bytes",
        cost_usd=0.0,
        latency_ms=120,
    )


def _video_result() -> GenerationResult:
    return GenerationResult(
        success=True,
        provider="stock_video",
        model="pexels-video",
        output=b"\x00\x00\x00\x18ftypmp42-fake-bytes",
        cost_usd=0.0,
        latency_ms=300,
    )


@pytest.mark.asyncio
async def test_scene_planning_then_asset_generation_flow() -> None:
    """SCENE_PLANNING creates Scene rows, then ASSET_GENERATION produces assets."""
    project_id = uuid4()
    workflow_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        title="A Boy Survived Alone on a Mysterious Island",
        description="A survival story",
    )

    package = _make_storyboard_package()
    workflow_state = WorkflowState()
    workflow_state.storyboard.metadata["storyboard_package"] = package.model_dump()

    # --- Service mock -----------------------------------------------------
    service = MagicMock()
    created_scenes: list = []
    created_assets: list = []
    updated_scenes: list = []

    storyboard = SimpleNamespace(id=uuid4())
    service._storyboard_repo.get_latest_version = AsyncMock(return_value=storyboard)

    async def _create_scene(scene):
        created_scenes.append(scene)
        return scene

    async def _get_scenes(pid):
        return list(created_scenes)

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

    # --- Container mock ---------------------------------------------------
    container = MagicMock()
    container.image_gateway = MagicMock()
    container.image_gateway.generate_image = AsyncMock(return_value=_image_result())
    container.video_gateway = MagicMock()
    container.video_gateway.generate_video = AsyncMock(return_value=_video_result())

    async def _upload(data, path, content_type="application/octet-stream"):
        return f"local:///storage/{path}"

    container.storage_gateway.upload = AsyncMock(side_effect=_upload)

    # --- Step 1: SCENE_PLANNING -------------------------------------------
    state_after_planning = await _create_step_output(
        service=service,
        engine=None,
        container=container,
        workflow_state=workflow_state,
        project=project,
        workflow_id=workflow_id,
        step="scene_planning",
    )

    assert state_after_planning is workflow_state
    assert len(created_scenes) == 3
    assert [s.scene_number for s in created_scenes] == [1, 2, 3]
    assert all(s.generation_status == SceneGenerationStatus.PENDING for s in created_scenes)

    # --- Step 2: ASSET_GENERATION ------------------------------------------
    state_after_assets = await _create_step_output(
        service=service,
        engine=None,
        container=container,
        workflow_state=workflow_state,
        project=project,
        workflow_id=workflow_id,
        step="asset_generation",
    )

    assert state_after_assets is workflow_state

    # Image gateway used for scenes 1 and 2, video gateway for scene 3
    assert container.image_gateway.generate_image.await_count == 2
    assert container.video_gateway.generate_video.await_count == 1

    image_prompts = [
        call.args[0] for call in container.image_gateway.generate_image.await_args_list
    ]
    assert any("alien beach" in p for p in image_prompts)
    assert any("solar still" in p for p in image_prompts)

    # Storage uploads: two images + one video
    assert container.storage_gateway.upload.await_count == 3
    upload_paths = [
        call.args[1] if len(call.args) > 1 else call.kwargs.get("path")
        for call in container.storage_gateway.upload.await_args_list
    ]
    assert f"projects/{project_id}/images/scene_1.png" in upload_paths
    assert f"projects/{project_id}/images/scene_2.png" in upload_paths
    assert f"projects/{project_id}/videos/scene_3.mp4" in upload_paths

    # Three assets persisted
    assert len(created_assets) == 3
    assert all(a.generation_status.value == "ready" for a in created_assets)
    assert all(a.storage_ref.startswith("local:///storage/projects/") for a in created_assets)

    # Scenes updated with concrete visual types
    scene_by_number = {s.scene_number: s for s in created_scenes}
    assert scene_by_number[1].visual_type == VisualType.STOCK_IMAGE
    assert scene_by_number[2].visual_type == VisualType.AI_IMAGE
    assert scene_by_number[3].visual_type == VisualType.STOCK_FOOTAGE
    assert all(
        s.generation_status != SceneGenerationStatus.FAILED
        for s in created_scenes
    )

    # Scene repo update called for each visual type assignment
    assert len(updated_scenes) == 3
