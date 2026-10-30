"""Tests for the media/rendering phase of the workflow pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.core.enums import AssetGenerationStatus, AssetType, StorageType
from src.domain.entities.asset import ImageAsset, VoiceAsset
from src.domain.entities.scene import Scene
from src.infrastructure.tasks.workflow_tasks import _create_step_output
from src.workflow.state import WorkflowState


@pytest.mark.asyncio
async def test_rendering_step_builds_composition_and_runs_pipeline() -> None:
    """The RENDERING step should build an AssetManifest, call CompositionBuilder,
    and invoke RenderingPipeline with the right output path.
    """
    project_id = uuid4()
    scene_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        title="Test Video",
        description="A test description",
    )

    scene = Scene(
        id=scene_id,
        project_id=project_id,
        storyboard_id=None,
        workflow_id=uuid4(),
        scene_number=1,
        title="Scene 1",
        duration_seconds=5.0,
        narration="Hello world",
        importance_score=0.8,
        emotion="curious",
        visual_type=None,
        camera_angle=None,
        camera_motion=None,
        lens="standard",
        lighting=None,
        composition=None,
        transition=None,
        subtitle=None,
        voice_timing={},
        background_music=None,
        sound_effects=[],
        generation_status=None,
        review_status=None,
        created_by=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    image_asset = ImageAsset(
        id=uuid4(),
        project_id=project_id,
        scene_id=scene_id,
        prompt="test image",
        width=1920,
        height=1080,
        format="png",
        provider="stock_image",
        generation_cost_usd=0.0,
        generation_time_seconds=0.5,
        generation_status=AssetGenerationStatus.READY,
        storage_type=StorageType.LOCAL,
        storage_ref=f"local:///app/storage/projects/{project_id}/images/scene_1.png",
        quality_score=0.85,
    )

    voice_asset = VoiceAsset(
        id=uuid4(),
        project_id=project_id,
        scene_id=scene_id,
        duration_seconds=5.0,
        language="en-US",
        voice_name="en-US-Studio-Q",
        format="mp3",
        provider="google_tts",
        generation_cost_usd=0.01,
        generation_time_seconds=0.2,
        generation_status=AssetGenerationStatus.READY,
        storage_type=StorageType.LOCAL,
        storage_ref=f"local:///app/storage/projects/{project_id}/voice/scene_1.mp3",
        quality_score=0.9,
    )

    service = MagicMock()
    service._scene_repo.get_by_project = AsyncMock(return_value=[scene])
    service._asset_repo.get_by_project = AsyncMock(return_value=[image_asset, voice_asset])

    container = MagicMock()
    container.config.storage.local_path = "/app/storage"
    container.llm_gateway = None

    workflow_state = WorkflowState()
    workflow_id = uuid4()

    fake_composition = MagicMock()
    fake_project_package = MagicMock()
    fake_project_package.final_video_path = (
        f"/app/storage/projects/{project_id}/final_video.mp4"
    )
    fake_project_package.render_report.model_dump.return_value = {"duration": 5.0}

    with (
        patch(
            "src.infrastructure.tasks.workflow_tasks.CompositionBuilder"
        ) as mock_builder_cls,
        patch(
            "src.infrastructure.tasks.workflow_tasks.RenderingPipeline"
        ) as mock_pipeline_cls,
    ):
        mock_builder = MagicMock()
        mock_builder.build.return_value = fake_composition
        mock_builder_cls.return_value = mock_builder

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=fake_project_package)
        mock_pipeline_cls.return_value = mock_pipeline

        result = await _create_step_output(
            service=service,
            engine=None,
            container=container,
            workflow_state=workflow_state,
            project=project,
            workflow_id=workflow_id,
            step="rendering",
        )

    assert result is workflow_state
    assert (
        result.metadata.custom["final_video_path"]
        == fake_project_package.final_video_path
    )
    assert result.metadata.custom["render_report"] == {"duration": 5.0}

    service._scene_repo.get_by_project.assert_awaited_once_with(project_id)
    service._asset_repo.get_by_project.assert_awaited_once_with(project_id)

    mock_builder.build.assert_called_once()
    build_args, build_kwargs = mock_builder.build.call_args
    manifest = build_args[0]
    assert manifest.project_id == str(project_id)
    assert len(manifest.scene_manifests) == 1
    assert manifest.scene_manifests[0].image is not None
    assert manifest.scene_manifests[0].voice is not None

    mock_pipeline.execute.assert_awaited_once()
    pipeline_args, pipeline_kwargs = mock_pipeline.execute.call_args
    assert pipeline_args[0] is fake_composition
    assert str(project_id) in pipeline_args[1]
    assert pipeline_kwargs["project_id"] == str(project_id)
