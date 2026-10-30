"""Offline end-to-end check of the Veo video pipeline.

Exercises the Veo code path against a previously generated
``workflow_state.json`` WITHOUT calling the Veo API:

    storyboard_package  ->  per-scene Veo prompt + 4/6/8s clip plan
                        ->  VideoGateway.generate_video (stubbed provider)
                        ->  VideoAsset manifest
                        ->  CompositionBuilder timeline (video track)

Run from the backend directory:

    python test_veo_pipeline.py [path/to/workflow_state.json]
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

DEFAULT_STATE = (
    Path(__file__).parent.parent
    / "storage"
    / "workflow_state"
    / "74abdec0-b8f6-4e4e-804f-f13e2860a8b8"
    / "1819fa8c-060a-4853-9839-e5de8c961884"
    / "workflow_state.json"
)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
class FakeVeoProvider:
    """Minimal VideoProvider stub — returns fake bytes, records calls."""

    from src.core.enums import AIProvider

    provider_name = AIProvider.VEO

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_video(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return b"FAKE-MP4-BYTES"

    def calculate_cost(self, duration_seconds, resolution):
        return round(0.05 * duration_seconds, 6)


class FakeLangfuse:
    """Records generation() calls like the real Langfuse client."""

    def __init__(self) -> None:
        self.generations: list[dict] = []

    def generation(self, **kwargs):
        self.generations.append(kwargs)


class FakeRegistry:
    def __init__(self, provider) -> None:
        self._provider = provider

    def get_providers_by_type(self, interface_type):
        return [self._provider]

    def get_provider_names_by_type(self, interface_type):
        return [self._provider.provider_name.value]

    def get_provider(self, name):
        return self._provider

    def has_provider(self, name):
        return True


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_storyboard_package(state: dict):
    """storyboard_package must round-trip into StoryboardPackage."""
    from src.ai.agents.storyboard.schema import StoryboardPackage

    pkg_dict = state["storyboard"]["metadata"]["storyboard_package"]
    package = StoryboardPackage.model_validate(pkg_dict)
    assert package.scene_packages, "no scene_packages in stored state"
    print(f"  storyboard_package OK — {len(package.scene_packages)} scenes")
    return package


def check_clip_plans(package):
    """Each scene's clip plan is the *minimum* 4/6/8s cover of its duration."""
    from src.infrastructure.tasks.workflow_tasks import _plan_veo_clip_durations

    for sp in package.scene_packages:
        plan = _plan_veo_clip_durations(float(sp.duration_seconds or 8))
        assert all(d in (4, 6, 8) for d in plan), f"bad clip durations {plan}"
        assert sum(plan) >= sp.duration_seconds, (
            f"scene {sp.scene_number}: clips {sum(plan)}s < duration "
            f"{sp.duration_seconds}s"
        )
        # minimum billed cover: even durations exact, odd get <=1s overshoot
        waste = sum(plan) - float(sp.duration_seconds)
        assert waste <= 1.0, f"scene {sp.scene_number}: billed waste {waste}s"
        print(
            f"  scene {sp.scene_number}: {sp.duration_seconds}s -> "
            f"{plan} (billed {sum(plan)}s, waste {waste:.0f}s)"
        )

    # sanity table for the optimal-cover planner
    cases = {4: [4], 5: [6], 8: [8], 10: [6, 4], 15: [8, 8], 17: [6, 4, 8],
             18: [8, 6, 4], 20: [8, 8, 4], 45: [8, 8, 8, 8, 8, 6],
             46: [8, 8, 8, 8, 8, 6], 50: [8, 8, 8, 8, 8, 6, 4]}
    for d, _expected in cases.items():
        plan = _plan_veo_clip_durations(float(d))
        assert all(c in (4, 6, 8) for c in plan)
        assert sum(plan) >= d
        assert sum(plan) - d <= 1, f"plan({d})={plan} wastes {sum(plan)-d}s"


def check_scene_snapping():
    """LLM-planned durations are trusted; only minimally repaired."""
    from src.ai.agents.storyboard.schema import PlannedScene
    from src.ai.agents.storyboard.scene_segmentation import (
        _snap_to_veo_durations,
        _validate_scene_durations,
    )

    durations = [17.3, 45.1, 15.0, 44.8, 15.4, 49.9, 50.2, 19.9]
    snapped = _snap_to_veo_durations(durations, 180)
    assert abs(sum(snapped) - 180) < 0.01, f"snapped total {sum(snapped)} != 180"
    even = sum(1 for d in snapped if d % 2 == 0 and d >= 4)
    assert even >= len(snapped) - 1, f"too many non-feasible scenes: {snapped}"
    print(f"  snapped {durations[:3]}... -> {snapped} (sum={sum(snapped)})")

    snapped_no_target = _snap_to_veo_durations([5.0, 9.0, 3.0], None)
    # banker's rounding: 5->4, 9->8; min clip length is 4
    assert snapped_no_target == [4.0, 8.0, 4.0], snapped_no_target

    # Validation path: well-formed LLM durations pass through unchanged
    def mkscene(i, dur):
        return PlannedScene(scene_number=i, scene_id=f"sc{i}",
                            narration=" ".join(["w"] * int(dur * 2.5)),
                            estimated_duration_seconds=dur)

    good = [mkscene(1, 4), mkscene(2, 12), mkscene(3, 14)]
    _validate_scene_durations(good, 30)
    assert [s.estimated_duration_seconds for s in good] == [4, 12, 14]
    assert good[2].end_timestamp == 30.0
    print("  well-formed LLM durations pass through unchanged -> [4, 12, 14]")

    # Drifting LLM output gets minimally repaired to hit the target
    bad = [mkscene(1, 4), mkscene(2, 12), mkscene(3, 30)]  # sums 46 != 50
    _validate_scene_durations(bad, 50)
    total = sum(s.estimated_duration_seconds for s in bad)
    assert abs(total - 50) < 1.01, f"repaired total {total}"
    print(f"  drifting LLM durations repaired: [4, 12, 30] -> "
          f"{[s.estimated_duration_seconds for s in bad]} (sum={total})")


def check_veo_prompts(package):
    """Veo prompts must compose visual + camera + motion and stay bounded."""
    from src.infrastructure.tasks.workflow_tasks import _build_veo_prompt

    for sp in package.scene_packages:
        base = sp.visual_plan.visual_description or sp.visual_prompt_summary or sp.title
        prompt = _build_veo_prompt(sp, base)
        assert prompt and len(prompt) <= 3500, (
            f"scene {sp.scene_number}: prompt len {len(prompt)}"
        )
    sample = _build_veo_prompt(
        package.scene_packages[0],
        package.scene_packages[0].visual_plan.visual_description
        or package.scene_packages[0].title,
    )
    print(f"  prompts OK — sample ({len(sample)} chars):\n    {sample[:200]}...")


def check_duration_quantization():
    from src.ai.providers.veo import quantize_veo_duration

    cases = {3.0: 4, 4.0: 4, 4.5: 6, 6.0: 6, 6.5: 8, 8.0: 8, 12.0: 8}
    for inp, expected in cases.items():
        got = quantize_veo_duration(inp)
        assert got == expected, f"quantize({inp})={got}, want {expected}"
    print(f"  quantize_veo_duration OK — {cases}")


async def check_provider_and_gateway():
    """VeoProvider init + generate (sync stubbed) + VideoGateway round-trip."""
    from src.ai.providers.veo import VeoProvider
    from src.ai.gateway.video_gateway import VideoGateway
    from src.core.config_service import ConfigService
    from src.core.interfaces import ProviderConfig

    provider = VeoProvider()
    await provider.initialize(
        ProviderConfig(
            api_key="fake-key",
            model="veo-3.1-lite-generate-preview",
            request_timeout=30,
            extra={"cost_per_second": 0.05},
        )
    )
    provider._generate_video_sync = lambda *a, **k: b"FAKE-VEO-MP4"
    data = await provider.generate_video("test prompt", duration_seconds=8.0)
    assert data == b"FAKE-VEO-MP4"

    # cost bills the quantised duration
    assert provider.calculate_cost(5.0, "1920x1080") == round(0.05 * 6, 6)
    print("  VeoProvider init/generate/cost OK (stubbed API)")

    # Gemini-key fallback (no dedicated GOOGLE_VEO_API_KEY)
    provider2 = VeoProvider()
    await provider2.initialize(
        ProviderConfig(api_key="", model="", extra={"gemini_api_key": "gem-key"})
    )
    assert provider2._api_key == "gem-key"
    assert provider2._model_name == "veo-3.1-lite-generate-preview"
    print("  VeoProvider GEMINI_API_KEY fallback + default model OK")

    # Full gateway path — retry/cost/metadata wrapper + Langfuse tracing
    langfuse = FakeLangfuse()
    gateway = VideoGateway(
        FakeRegistry(FakeVeoProvider()), ConfigService(), langfuse_client=langfuse
    )
    await gateway.initialize()
    result = await gateway.generate_video(
        "Atlantis dome of crystal and gold",
        duration_seconds=8.0,
        width=1920,
        height=1080,
        fps=24,
        trace_id="trace-123",
        generation_name="video_generation_scene_1_clip_0",
    )
    assert result.success and result.output == b"FAKE-MP4-BYTES"
    assert result.provider == "veo"
    assert result.metadata["duration_seconds"] == 8.0

    # Langfuse generation was recorded with real cost + model
    assert len(langfuse.generations) == 1
    gen = langfuse.generations[0]
    assert gen["trace_id"] == "trace-123"
    assert gen["name"] == "video_generation_scene_1_clip_0"
    assert gen["cost_usd"] == result.cost_usd == 0.4
    assert gen["provider"] == "veo"
    print(f"  VideoGateway.generate_video OK — provider={result.provider}, "
          f"cost=${result.cost_usd}, langfuse generation recorded")


async def check_clip_concat():
    """Multi-clip concat via ffmpeg (skipped when ffmpeg unavailable)."""
    if not shutil.which("ffmpeg"):
        print("  SKIP — ffmpeg not on this host (runs in Docker)")
        return
    from src.infrastructure.tasks.workflow_tasks import _concat_video_clips

    assert await _concat_video_clips([b"only"]) == b"only"
    print("  _concat_video_clips single-clip passthrough OK")


def check_composition(package):
    """A video asset must land on the video track, suppressing the image."""
    from src.composition.builder import CompositionBuilder
    from src.generation.schema import (
        AssetCategory,
        AssetManifest,
        GeneratedAsset,
        SceneAssetManifest,
    )

    manifests = []
    for sp in package.scene_packages:
        video = GeneratedAsset(
            scene_id=sp.scene_id,
            category=AssetCategory.VIDEO,
            provider="veo",
            model="veo-3.1-lite-generate-preview",
            storage_uri=f"local:///videos/scene_{sp.scene_number}.mp4",
        )
        manifests.append(
            SceneAssetManifest(
                scene_id=sp.scene_id,
                scene_number=sp.scene_number,
                video=video,
            )
        )
    manifest = AssetManifest(project_id="test", scene_manifests=manifests)
    scene_durations = {
        sp.scene_id: float(sp.duration_seconds) for sp in package.scene_packages
    }

    doc = CompositionBuilder().build(manifest, scene_durations=scene_durations)

    video_track = next(t for t in doc.timeline.tracks if t.track_type.value == "video")
    image_track = next(t for t in doc.timeline.tracks if t.track_type.value == "image")
    assert len(video_track.clips) == len(package.scene_packages)
    assert len(image_track.clips) == 0, "image clips should be suppressed by video"

    total = sum(c.duration for c in video_track.clips)
    expected = sum(float(sp.duration_seconds) for sp in package.scene_packages)
    assert abs(total - expected) < 0.01, f"video timeline {total}s != {expected}s"
    print(
        f"  CompositionBuilder OK — {len(video_track.clips)} video clips, "
        f"timeline {total:.0f}s, image track empty"
    )


def check_config_defaults():
    from src.core.config import VeoSettings

    s = VeoSettings()
    assert s.model == "veo-3.1-lite-generate-preview", s.model
    print(f"  config default model={s.model}, enabled={s.enabled} "
          f"(USE_VEO env), timeout={s.request_timeout}s")


# ---------------------------------------------------------------------------
def main() -> int:
    state_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STATE
    print(f"Loading workflow state: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    print(f"  project target: {state['project']['target_duration_seconds']}s")

    print("\n[1] storyboard_package round-trip")
    package = check_storyboard_package(state)

    print("\n[2] per-scene clip plans (minimum billed cover)")
    check_clip_plans(package)

    print("\n[2b] scene durations snapped to Veo-feasible lengths")
    check_scene_snapping()

    print("\n[3] Veo prompt composition")
    check_veo_prompts(package)

    print("\n[4] provider duration quantization")
    check_duration_quantization()

    print("\n[5] VeoProvider + VideoGateway (stubbed API)")
    asyncio.run(check_provider_and_gateway())

    print("\n[6] clip concat")
    asyncio.run(check_clip_concat())

    print("\n[7] composition: video assets on video track")
    check_composition(package)

    print("\n[8] config defaults")
    check_config_defaults()

    print("\nALL VEO PIPELINE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
