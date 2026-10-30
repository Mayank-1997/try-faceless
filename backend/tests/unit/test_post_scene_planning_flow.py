"""End-to-end test for ALL steps after SCENE_PLANNING.

Builds a near-real WorkflowState (project, topic, research, script and
storyboard metadata exactly as the agent graphs would have produced them)
and runs:

    SCENE_PLANNING -> ASSET_GENERATION -> VOICE_GENERATION ->
    SUBTITLE_GENERATION -> RENDERING -> THUMBNAIL -> SEO

All external effects (image/video/voice gateways, storage, LLM,
CompositionBuilder, RenderingPipeline) are mocked; repositories are
in-memory. No Gemini / stock APIs / ffmpeg / database are touched.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.agents.storyboard.schema import (
    CameraPlan,
    ScenePackage,
    StoryboardPackage,
    VisualPlan,
)
from src.application.dto.responses import GenerationResult
from src.core.enums import AssetType, SceneGenerationStatus, VisualType
from src.infrastructure.tasks.workflow_tasks import _create_step_output
from src.workflow.state import ProjectInfo, TopicData, WorkflowState

PROJECT_ID = uuid4()
USER_ID = uuid4()
WORKFLOW_ID = uuid4()

# ---------------------------------------------------------------------------
# Near-real WorkflowState
# ---------------------------------------------------------------------------

NARRATIONS = {
    1: (
        "The sky didn't just break; it shattered in a deafening roar of "
        "tearing metal. Fourteen-year-old Leo surfaced from blackness onto "
        "a silent, alien beach, the wreckage of Flight 472 smouldering "
        "behind him, and not a single living soul in sight."
    ),
    2: (
        "The first week was a brutal education. Leo pried aluminium panels "
        "from the fuselage to roof a lean-to, rigged a solar still from "
        "plastic sheeting, and spent an entire afternoon coaxing sparks "
        "from a bow drill until fire finally crackled to life."
    ),
    3: (
        "On day thirty-four, a distant engine note grew into a thunderous "
        "roar. Leo collapsed his signal fire into a screaming pillar of "
        "smoke just as a Coast Guard cutter broke through the mist, and "
        "rescue became the sweetest word he would ever hear."
    ),
}


def _scene_package(n: int, title: str, asset_type: str, visual: str) -> ScenePackage:
    return ScenePackage(
        scene_id=f"scene-{n}",
        scene_number=n,
        title=title,
        narration=NARRATIONS[n],
        duration_seconds={1: 25, 2: 30, 3: 20}[n],
        visual_prompt_summary=visual[:80],
        asset_type=asset_type,
        camera_plan=CameraPlan(
            scene_id=f"scene-{n}",
            camera_angle={1: "wide", 2: "close_up", 3: "aerial"}[n],
            lens={1: "wide", 2: "macro", 3: "telephoto"}[n],
            movement={1: "pan_left", 2: "zoom_in", 3: "dolly_in"}[n],
        ),
        visual_plan=VisualPlan(
            scene_id=f"scene-{n}",
            visual_description=visual,
            composition="rule of thirds",
            lighting={1: "harsh midday", 2: "golden hour", 3: "overcast mist"}[n],
        ),
        quality_score=0.9,
    )


def _build_storyboard_package() -> StoryboardPackage:
    return StoryboardPackage(
        scene_packages=[
            _scene_package(
                1,
                "The Catalyst and Descent",
                "stock_image",
                "A fourteen-year-old boy standing alone on a silent tropical "
                "beach, airliner wreckage smouldering in the background, harsh "
                "midday light, cinematic wide shot.",
            ),
            _scene_package(
                2,
                "Primal Ingenuity",
                "ai_image",
                "Crude survival tools arranged on a jungle floor: fuselage "
                "aluminium lean-to, solar still made from plastic sheeting, "
                "bow drill with glowing embers, golden hour light.",
            ),
            _scene_package(
                3,
                "The Rescue",
                "stock_footage",
                "A Coast Guard vessel slicing through misty open ocean toward "
                "camera, aerial drone shot, dramatic overcast lighting.",
            ),
        ]
    )


def _build_workflow_state() -> WorkflowState:
    """Mirror the state a real run has at the start of SCENE_PLANNING."""
    state = WorkflowState(
        project=ProjectInfo(
            project_id=PROJECT_ID,
            user_id=USER_ID,
            name="A Boy Survived Alone on a Mysterious Island",
            target_duration_seconds=75,  # 25 + 30 + 20
            target_resolution="1920x1080",
        ),
        topic=TopicData(
            raw_topic="A Boy Survived Alone on a Mysterious Island",
            expanded_topic=(
                "The harrowing yet uplifting survival journey of a young boy "
                "stranded alone on an uncharted, mysterious island following a "
                "devastating plane crash."
            ),
        ),
    )

    # research.metadata — produced by ResearchWorkflowGraph
    state.research.metadata["research_package"] = {
        "topic_analysis": {
            "expanded_topic": state.topic.expanded_topic,
            "target_duration_seconds": 75,
            "target_audience": "Thrill-Seeking Escapists",
        },
        "summary": {
            "overview": "A Robinsonade survival story with anomalous island mystery.",
            "important_facts": [
                "Bow-drill fires can take hours to coax to life.",
                "Solar stills distill seawater using only sunlight and plastic.",
                "Smoke columns are the internationally recognised distress signal.",
            ],
        },
        "fact_verification": {
            "verified_facts": [
                {"category": "survival", "fact": "Signal fires save lives."},
            ],
        },
    }

    # script.metadata — produced by ScriptWorkflowGraph
    state.script.metadata["narrative_strategy"] = {
        "style": "storytelling",
        "rationale": (
            "The storytelling style immerses the viewer in the narrative arc "
            "of the boy's harrowing adventure."
        ),
        "flow": "Crash, survival basics, mystery, rescue.",
        "pacing": "varied",
        "tone": "dramatic",
        "emotional_arc": "Terror to triumph.",
        "key_beats": [
            "The catastrophic plane crash",
            "Mastering water, shelter and fire",
            "The rescue vessel arrival",
        ],
        "audience_alignment": "Thrill-Seeking Escapists.",
    }
    state.script.metadata["script_outline"] = {
        "title": "A Boy Survived Alone on a Mysterious Island",
        "sections": [
            {
                "section_id": f"s{n}",
                "title": t,
                "description": d,
                "key_talking_points": [],
                "estimated_time_seconds": {1: 25, 2: 30, 3: 20}[n],
                "target_word_count": 60,
            }
            for n, t, d in [
                (1, "The Catalyst and Descent", "The crash and first awakening."),
                (2, "Primal Ingenuity", "Mastering survival basics."),
                (3, "The Rescue", "The Coast Guard arrival."),
            ]
        ],
    }
    state.script.metadata["sections"] = [
        {
            "section_id": f"s{n}",
            "title": f"Section {n}",
            "narration": NARRATIONS[n],
            "estimated_duration_seconds": {1: 25, 2: 30, 3: 20}[n],
            "word_count": len(NARRATIONS[n].split()),
        }
        for n in (1, 2, 3)
    ]
    state.script.metadata["hook_result"] = {
        "hooks": [],
        "selected_hook": {
            "hook_type": "curiosity_gap",
            "content": (
                "What would you do if you woke up completely alone on an "
                "island that shouldn't exist?"
            ),
        },
    }
    state.script.metadata["cta_result"] = {
        "primary_cta": {
            "cta_type": "subscribe",
            "content": "Subscribe for more incredible survival stories.",
            "placement": "end",
        },
        "secondary_ctas": [],
    }

    # storyboard.metadata — produced by StoryboardWorkflowGraph
    state.storyboard.metadata["storyboard_package"] = (
        _build_storyboard_package().model_dump()
    )
    return state


# ---------------------------------------------------------------------------
# Mock service / container
# ---------------------------------------------------------------------------


def _build_service():
    service = MagicMock()
    created_scenes: list = []
    created_assets: list = []
    updated_scenes: list = []

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

    async def _get_assets(pid, asset_type=None):
        if asset_type is None:
            return list(created_assets)
        return [a for a in created_assets if a.asset_type == asset_type]

    service._storyboard_repo.get_latest_version = AsyncMock(
        return_value=SimpleNamespace(id=uuid4())
    )
    service._scene_repo.create = AsyncMock(side_effect=_create_scene)
    service._scene_repo.get_by_project = AsyncMock(side_effect=_get_scenes)
    service._scene_repo.update = AsyncMock(side_effect=_update_scene)
    service._asset_repo.create = AsyncMock(side_effect=_create_asset)
    service._asset_repo.get_by_project = AsyncMock(side_effect=_get_assets)

    return service, created_scenes, created_assets, updated_scenes


def _generation_result(provider: str, model: str, output: bytes) -> GenerationResult:
    return GenerationResult(
        success=True,
        provider=provider,
        model=model,
        output=output,
        cost_usd=0.0,
        latency_ms=150,
    )


def _build_container():
    container = MagicMock()

    container.image_gateway = MagicMock()
    container.image_gateway.generate_image = AsyncMock(
        return_value=_generation_result("stock_image", "pexels", b"\xff\xd8\xff\xe0jpg")
    )
    container.video_gateway = MagicMock()
    container.video_gateway.generate_video = AsyncMock(
        return_value=_generation_result(
            "stock_video", "pexels-video", b"\x00\x00\x00\x18ftypmp42"
        )
    )
    container.voice_gateway = MagicMock()
    container.voice_gateway.generate_speech = AsyncMock(
        return_value=_generation_result("google_tts", "en-US-Studio-Q", b"ID3mp3")
    )

    upload_paths: list[str] = []

    async def _upload(data, path, content_type="application/octet-stream"):
        upload_paths.append(path)
        return f"local:///storage/{path}"

    container.storage_gateway.upload = AsyncMock(side_effect=_upload)
    container._upload_paths = upload_paths

    container.config.storage.local_path = "/app/storage"

    container.llm_gateway = MagicMock()
    container.llm_gateway.generate_json = AsyncMock(
        return_value=GenerationResult(
            success=True,
            provider="gemini",
            model="gemini-flash-lite-latest",
            output={
                "title": "Alone on the Mysterious Island: 34 Days of Survival",
                "description": (
                    "A teen survives a plane crash and 34 days alone on an "
                    "uncharted island using raw ingenuity."
                ),
                "tags": ["survival", "island", "true story", "rescue", "adventure"],
            },
            cost_usd=0.0,
            latency_ms=100,
        )
    )
    return container


async def _run_step(service, container, state, step: str) -> None:
    await _create_step_output(
        service=service,
        engine=None,
        container=container,
        workflow_state=state,
        project=SimpleNamespace(
            id=PROJECT_ID,
            title="A Boy Survived Alone on a Mysterious Island",
            description="A teen survival story after a plane crash.",
        ),
        workflow_id=WORKFLOW_ID,
        step=step,
    )


# ---------------------------------------------------------------------------
# The end-to-end test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_steps_after_scene_planning() -> None:
    state = _build_workflow_state()
    service, scenes, assets, updated = _build_service()
    container = _build_container()

    # --- SCENE_PLANNING ---------------------------------------------------
    await _run_step(service, container, state, "scene_planning")
    assert len(scenes) == 3
    assert [s.scene_number for s in scenes] == [1, 2, 3]
    assert all(s.generation_status == SceneGenerationStatus.PENDING for s in scenes)
    # ai_image is normalised to IMAGE during entity conversion
    assert [s.visual_type for s in scenes] == [
        VisualType.STOCK_IMAGE,
        VisualType.IMAGE,
        VisualType.STOCK_FOOTAGE,
    ]

    # --- ASSET_GENERATION --------------------------------------------------
    await _run_step(service, container, state, "asset_generation")
    assert container.image_gateway.generate_image.await_count == 2
    assert container.video_gateway.generate_video.await_count == 1

    image_prompts = [
        c.args[0] for c in container.image_gateway.generate_image.await_args_list
    ]
    assert any("alien beach" in p or "tropical beach" in p for p in image_prompts)
    assert any("solar still" in p for p in image_prompts)

    video_kwargs = container.video_gateway.generate_video.await_args.kwargs
    assert video_kwargs["duration_seconds"] == 20.0  # scene 3 duration

    assert len(assets) == 3  # 2 images + 1 video
    assert {a.asset_type for a in assets} == {AssetType.IMAGE, AssetType.VIDEO}
    assert all(a.generation_status.value == "ready" for a in assets)
    by_number = {s.scene_number: s for s in scenes}
    assert by_number[2].visual_type == VisualType.AI_IMAGE  # upgraded by step
    assert all(
        s.generation_status != SceneGenerationStatus.FAILED for s in scenes
    )

    expected_paths = {
        f"projects/{PROJECT_ID}/images/scene_1.png",
        f"projects/{PROJECT_ID}/images/scene_2.png",
        f"projects/{PROJECT_ID}/videos/scene_3.mp4",
    }
    assert expected_paths <= set(container._upload_paths)

    # --- VOICE_GENERATION --------------------------------------------------
    await _run_step(service, container, state, "voice_generation")
    assert container.voice_gateway.generate_speech.await_count == 3
    spoken = [
        c.args[0] for c in container.voice_gateway.generate_speech.await_args_list
    ]
    assert any("Flight 472" in s for s in spoken)
    assert any("bow drill" in s for s in spoken)
    assert any("Coast Guard cutter" in s for s in spoken)
    assert len(assets) == 6  # +3 voice assets
    voice_paths = {
        f"projects/{PROJECT_ID}/voice/scene_{n}.mp3" for n in (1, 2, 3)
    }
    assert voice_paths <= set(container._upload_paths)

    # --- SUBTITLE_GENERATION -----------------------------------------------
    await _run_step(service, container, state, "subtitle_generation")
    for s in scenes:
        assert s.subtitle and "-->" in s.subtitle
        assert s.scene_number in (1, 2, 3)
    srt_3 = by_number[3].subtitle
    assert "00:00:20,000" in srt_3  # scene 3 duration -> end timestamp
    assert "Coast Guard cutter" in srt_3

    # --- RENDERING -----------------------------------------------------------
    fake_composition = MagicMock()
    fake_package = MagicMock()
    fake_package.final_video_path = f"/app/storage/projects/{PROJECT_ID}/final_video.mp4"
    fake_package.render_report.model_dump.return_value = {"duration": 75.0}

    with (
        patch("src.infrastructure.tasks.workflow_tasks.CompositionBuilder") as mb_cls,
        patch("src.infrastructure.tasks.workflow_tasks.RenderingPipeline") as mp_cls,
    ):
        mb = MagicMock()
        mb.build.return_value = fake_composition
        mb_cls.return_value = mb
        mp = MagicMock()
        mp.execute = AsyncMock(return_value=fake_package)
        mp_cls.return_value = mp

        await _run_step(service, container, state, "rendering")

        manifest = mb.build.call_args.args[0]
        assert manifest.project_id == str(PROJECT_ID)
        assert len(manifest.scene_manifests) == 3
        assert manifest.total_duration_seconds == 75.0
        for sm in manifest.scene_manifests:
            assert sm.image is not None or sm.video is not None
            assert sm.voice is not None
        pipeline_args, pipeline_kwargs = mp.execute.call_args
        assert pipeline_args[0] is fake_composition
        assert str(PROJECT_ID) in pipeline_args[1]
        assert pipeline_kwargs["project_id"] == str(PROJECT_ID)

    assert (
        state.metadata.custom["final_video_path"]
        == fake_package.final_video_path
    )
    assert state.metadata.custom["render_report"] == {"duration": 75.0}

    # --- THUMBNAIL -----------------------------------------------------------
    await _run_step(service, container, state, "thumbnail")
    thumbs = [a for a in assets if a.asset_type == AssetType.THUMBNAIL]
    assert len(thumbs) == 1
    assert thumbs[0].is_default is True
    assert state.metadata.custom["thumbnail_uri"] == thumbs[0].storage_ref

    # --- SEO ------------------------------------------------------------------
    await _run_step(service, container, state, "seo")
    container.llm_gateway.generate_json.assert_awaited_once()
    seo = state.metadata.custom["seo"]
    assert seo["title"] == "Alone on the Mysterious Island: 34 Days of Survival"
    assert len(seo["tags"]) == 5
    assert "survival" in seo["tags"]

    # --- Final tallies ---------------------------------------------------------
    assert len(assets) == 10  # 2 images + 1 video + 3 voice + 3 subtitles + 1 thumbnail
    assert len(container._upload_paths) == 9  # 3 media + 3 voice + 3 subtitles
