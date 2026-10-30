import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.application.dto.business_dtos import CreateProjectRequest
from src.infrastructure.tasks import workflow_tasks as tasks


def _project():
    request = CreateProjectRequest(
        title="Jungle dive", description="Blonde athlete in white dives toward a tiny trampoline on the jungle floor and returns to her ledge.",
        target_duration_seconds=10, aspect_ratio="9:16", production_mode="direct_cinematic",
        visual_anchor="Blonde athlete in white, limestone sinkhole, daylight; tiny trampoline on jungle floor.",
        clip_beats=["She dives and falls toward the trampoline below.", "She impacts the trampoline and rebounds to the ledge."],
        avoid="No cables or harnesses", narration_text="",
    )
    return SimpleNamespace(id=uuid4(), owner_id=uuid4(), title=request.title, description=request.description,
                           target_duration_seconds=request.target_duration_seconds, video_style="cinematic",
                           metadata=request.model_dump(exclude={"title", "description", "target_duration_seconds", "video_style", "content_type"}))


def test_direct_request_requires_production_details():
    with pytest.raises(ValidationError):
        CreateProjectRequest(title="Video", description="A dive", target_duration_seconds=10,
                             production_mode="direct_cinematic", visual_anchor="Same woman", clip_beats=[])
    assert CreateProjectRequest(title="Explainer").production_mode == "explainer"


def test_direct_flow_uses_user_spec_and_mocked_video_only(monkeypatch):
    project = _project()
    settings = SimpleNamespace(veo=SimpleNamespace(enabled=True), cost=SimpleNamespace(veo_per_second=0.05))
    monkeypatch.setattr(tasks, "get_settings", lambda: settings)
    from src.ai.agents.storyboard import asset_decision
    monkeypatch.setattr(asset_decision, "get_settings", lambda: settings, raising=False)
    state = tasks._build_initial_state(project)
    assert state.project.target_resolution == "1080x1920"
    package = tasks._build_direct_storyboard(project, state)
    assert package.scene_packages[0].visual_plan.visual_description == project.description
    assert package.visual_plans.shared_context == project.metadata["visual_anchor"]
    assert package.asset_decisions.total_estimated_cost == 0.75
    assert not package.scene_packages[0].narration

    service = MagicMock()
    service._storyboard_repo.create = AsyncMock()
    container = MagicMock()
    engine = MagicMock()

    async def run():
        for step in ("research", "scripting", "storyboard", "voice_generation", "subtitle_generation", "seo"):
            await tasks._create_step_output(service, engine, container, state, project, uuid4(), step)
        assert engine.mock_calls == []
        assert service._storyboard_repo.create.await_count == 1
        assert tasks._get_storyboard_package(state).scene_packages[0].metadata["clip_beats"] == project.metadata["clip_beats"]

        initial_calls = []
        extension_calls = []

        async def generate_initial(prompt, **kwargs):
            initial_calls.append((prompt, kwargs))
            return SimpleNamespace(
                output=b"initial-video",
                provider="veo",
                model="mock-fast-veo",
                cost_usd=0.4,
                latency_ms=1,
                metadata={"remote_video": "remote-initial"},
            )

        async def extend(remote_video, prompt, **kwargs):
            extension_calls.append((remote_video, prompt, kwargs))
            return SimpleNamespace(
                output=b"extended-video",
                provider="veo",
                model="mock-fast-veo",
                cost_usd=0.35,
                latency_ms=1,
                metadata={"remote_video": "remote-extended"},
            )

        container.video_gateway.generate_video_with_resource = AsyncMock(side_effect=generate_initial)
        container.video_gateway.extend_video = AsyncMock(side_effect=extend)
        container.storage_gateway.upload = AsyncMock(return_value="local:///mock/video.mp4")
        service._asset_repo.create = AsyncMock()
        service._scene_repo.update = AsyncMock()
        scene = SimpleNamespace(id=uuid4(), duration_seconds=10, visual_type=None)
        with patch.object(tasks, "_extract_last_frame_png", new_callable=AsyncMock, return_value=b"last-frame"), \
             patch.object(tasks, "_probe_video_bytes_dimensions", new_callable=AsyncMock, return_value=(720, 1280)), \
             patch.object(tasks, "_concat_video_clips", new_callable=AsyncMock, return_value=b"joined-video"), \
             patch.object(tasks, "_validate_video_bytes", new_callable=AsyncMock), \
             patch.object(tasks, "_record_asset_cost"):
            result, frame = await tasks._generate_scene_video(container, project, service, state, scene,
                package.scene_packages[0], project.description, shared_context=package.visual_plans.shared_context)
        assert result["clips"] == 2 and result["video_extension"] and frame == b"last-frame"
        assert initial_calls[0][1]["duration_seconds"] == 8
        assert initial_calls[0][1]["resolution"] == "720p"
        assert initial_calls[0][1]["image"] is None
        assert extension_calls[0][0] == "remote-initial"
        assert extension_calls[0][2]["width"] == 720 and extension_calls[0][2]["height"] == 1280
        assert project.metadata["clip_beats"][0] in initial_calls[0][0]
        assert project.metadata["clip_beats"][1] in extension_calls[0][1]
        assert project.metadata["avoid"] in extension_calls[0][1]
        assert project.description in initial_calls[0][0]
        assert project.description not in extension_calls[0][1]
        assert "exactly this next action beat" in extension_calls[0][1]
        assert state.metadata.custom["video_clips"][1]["input_video_supplied"]
        assert state.metadata.custom["video_clips"][1]["remote_video_retained"]
        assert service._asset_repo.create.await_count == 1

    asyncio.run(run())


def test_direct_storyboard_rejects_wrong_clip_count(monkeypatch):
    project = _project()
    project.metadata["clip_beats"] = ["One action only"]
    state = tasks._build_initial_state(project)
    with pytest.raises(ValueError, match="exactly 2 clip beats"):
        tasks._build_direct_storyboard(project, state)


def test_direct_extension_plans_cover_target_duration():
    assert tasks._plan_direct_cinematic_segments(8) == [8]
    assert tasks._plan_direct_cinematic_segments(15) == [8, 7]
    assert tasks._plan_direct_cinematic_segments(30) == [8, 7, 7, 7, 7]

    request = CreateProjectRequest(
        title="Long POV ride",
        description="A continuous first-person ride.",
        target_duration_seconds=30,
        production_mode="direct_cinematic",
        visual_anchor="Same bicycle and helmet camera.",
        clip_beats=[f"Beat {i}" for i in range(5)],
    )
    assert len(request.clip_beats) == 5


def test_direct_gateway_disables_stock_fallback():
    from src.ai.gateway.video_gateway import VideoGateway
    from src.core.exceptions import VideoGatewayError

    gateway = VideoGateway(MagicMock(), MagicMock())
    gateway._initialized = True
    gateway._get_primary_provider = MagicMock(return_value=SimpleNamespace(generate_video=AsyncMock(side_effect=RuntimeError("provider unavailable"))))
    gateway._try_fallback = AsyncMock()
    with pytest.raises(VideoGatewayError):
        asyncio.run(gateway.generate_video("test", allow_fallback=False))
    gateway._try_fallback.assert_not_awaited()


def test_gateway_preserves_remote_veo_resource_for_extension():
    from src.ai.gateway.video_gateway import VideoGateway
    from src.core.interfaces import VideoGenerationPayload

    provider = MagicMock()
    provider.provider_name = SimpleNamespace(value="veo")
    provider.calculate_cost.return_value = 0.8
    provider.calculate_extension_cost.return_value = 0.7
    provider.generate_video_with_resource = AsyncMock(
        return_value=VideoGenerationPayload(video_bytes=b"initial", remote_video="veo-resource-1")
    )
    provider.extend_video = AsyncMock(
        return_value=VideoGenerationPayload(video_bytes=b"extended", remote_video="veo-resource-2")
    )
    registry = MagicMock()
    registry.get_providers_by_type.return_value = [provider]
    config = SimpleNamespace(veo=SimpleNamespace(model="veo-3.1-fast-generate-preview", max_retries=1))
    gateway = VideoGateway(registry, config)
    gateway._initialized = True

    initial = asyncio.run(
        gateway.generate_video_with_resource(
            "initial", duration_seconds=8, resolution="720p"
        )
    )
    extended = asyncio.run(gateway.extend_video("veo-resource-1", "continue"))
    assert initial.output == b"initial"
    assert initial.metadata["remote_video"] == "veo-resource-1"
    assert extended.output == b"extended"
    assert extended.metadata["remote_video"] == "veo-resource-2"
    assert provider.generate_video_with_resource.await_args.kwargs["resolution"] == "720p"
    provider.extend_video.assert_awaited_once_with(
        "veo-resource-1", "continue", width=720, height=1280, fps=24
    )


def test_veo_gemini_requests_omit_unsupported_generate_audio(monkeypatch):
    from google import genai
    from src.ai.providers.veo import VeoProvider

    remote_video = SimpleNamespace(video_bytes=b"mock-video")
    operation = SimpleNamespace(
        done=True,
        error=None,
        response=SimpleNamespace(
            generated_videos=[SimpleNamespace(video=remote_video)]
        ),
    )
    generate_videos = MagicMock(return_value=operation)
    client = SimpleNamespace(
        models=SimpleNamespace(generate_videos=generate_videos),
        files=SimpleNamespace(download=MagicMock()),
        operations=SimpleNamespace(get=MagicMock()),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=client))
    provider = VeoProvider()
    provider._initialized = True
    provider._api_key = "mock-key"
    provider._model_name = "veo-3.1-fast-generate-preview"
    provider._config = SimpleNamespace(request_timeout=10)

    initial = provider._generate_video_sync(
        "initial prompt", 8, 720, 1280, 24, None, None, None, "720p"
    )
    extension = provider._extend_video_sync(
        remote_video, "continue prompt", 720, 1280, 24
    )

    assert initial.video_bytes == b"mock-video"
    assert initial.remote_video is remote_video
    assert extension.video_bytes == b"mock-video"
    assert extension.remote_video is remote_video
    assert generate_videos.call_count == 2
    assert generate_videos.call_args_list[0].kwargs["config"].resolution == "720p"
    for call in generate_videos.call_args_list:
        config = call.kwargs["config"].model_dump(exclude_unset=True, by_alias=True)
        assert "generateAudio" not in config
        assert "generate_audio" not in config


def test_direct_render_preserves_clip_audio_without_narration(tmp_path):
    import json
    import shutil
    import subprocess
    from src.core.enums import AIProvider, AssetType

    if not shutil.which("ffmpeg"):
        pytest.skip("Local FFmpeg is unavailable")
    project = _project()
    clip = tmp_path / "mock-veo.mp4"
    final = tmp_path / "final.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=360x640:r=24:d=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-shortest",
        "-c:v", "libx264", "-c:a", "aac", str(clip),
    ], check=True)
    scene = SimpleNamespace(id=uuid4(), scene_number=1, duration_seconds=4, camera_motion=None)
    asset = SimpleNamespace(scene_id=scene.id, asset_type=AssetType.VIDEO, provider=AIProvider.VEO,
        storage_ref=f"local://{clip}", generation_cost_usd=0, quality_score=0.8,
        generation_time_seconds=0)
    container = SimpleNamespace(config=SimpleNamespace(storage=SimpleNamespace(local_path=str(tmp_path))))
    result = asyncio.run(tasks._render_composition_multi_pass(
        container, project, uuid4(), [scene], {str(scene.id): [asset]}, str(final),
        width=360, height=640,
    ))
    assert result.render_report.output_resolution == "360x640"
    streams = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
        "-of", "json", str(final),
    ]))["streams"]
    assert {stream["codec_type"] for stream in streams} == {"video", "audio"}
    assert next(stream for stream in streams if stream["codec_type"] == "video")["height"] == 640


def test_concat_normalizes_mixed_resolution_clips(tmp_path):
    """Veo emits 720p for short clips and 1080p for 8s clips.  A stream-copy
    concat of those leaves a mid-stream resolution change on which the
    render filtergraph silently drops frames (12s source -> ~8s output).
    The concat must re-encode mixed clips to a uniform size and keep
    every clip's audio."""
    import json
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("Local FFmpeg is unavailable")

    clips = []
    for i, size in enumerate(("360x640", "720x1280")):
        clip = tmp_path / f"clip_{i}.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc=size={size}:rate=24:duration=2",
            "-f", "lavfi", "-i", f"sine=frequency={440 + i * 220}:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", str(clip),
        ], check=True)
        clips.append(clip.read_bytes())

    joined = tmp_path / "joined.mp4"
    joined.write_bytes(asyncio.run(
        tasks._concat_video_clips(clips, width=1080, height=1920)
    ))
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,width,height:format=duration",
        "-of", "json", str(joined),
    ]))
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (720, 1280)
    assert float(info["format"]["duration"]) == pytest.approx(4.0, abs=0.2)
    assert any(s["codec_type"] == "audio" for s in info["streams"])

    # The render-stage filter chain must no longer drop frames.
    rendered = tmp_path / "rendered.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(joined),
        "-filter_complex",
        "[0:v]scale=720:1280:flags=lanczos,setsar=1,fps=30[v];"
        "[v]trim=duration=4.0,setpts=PTS-STARTPTS[vout];"
        "[0:a]volume=1.0,atrim=duration=4.0,asetpts=PTS-STARTPTS[aout]",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p", str(rendered),
    ], check=True)
    rendered_info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type:format=duration", "-of", "json", str(rendered),
    ]))
    assert float(rendered_info["format"]["duration"]) == pytest.approx(4.0, abs=0.2)
    assert any(s["codec_type"] == "audio" for s in rendered_info["streams"])
