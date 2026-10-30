"""Scene Segmentation Agent — splits script into production scenes.

Third agent in the storyboard workflow.  Takes the script and story
beats to produce production scenes with scene numbers, timestamps,
narration, duration, goals, and scene types.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import SCENE_SEGMENTATION_PROMPT
from src.ai.agents.storyboard.schema import (
    PlannedScene,
    SceneSegmentationResult,
    StoryBeatResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class SceneSegmentationAgent(BaseAgent):
    """Splits the script into production scenes.

    Each scene contains:
    - Scene number and ID
    - Start/end timestamps
    - Narration text
    - Estimated duration
    - Scene goal
    - Scene type (talking, diagram, animation, etc.)
    """

    def __init__(self) -> None:
        super().__init__(
            name="scene_segmentation",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SCENE_PLANNER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {"required_fields": ["scenes"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        beats_data = context.state.storyboard.metadata.get("story_beats", {})
        beats = StoryBeatResult.model_validate(beats_data) if beats_data else StoryBeatResult()

        beats_text = "\n".join(f"- [{b.beat_type}] {b.description} ({b.duration_seconds}s)" for b in beats.beats)

        return SCENE_SEGMENTATION_PROMPT, {
            "script_title": sp.title,
            # The user-requested duration is authoritative; the script's own
            # estimate is only a fallback when no target was provided.
            "target_duration": (
                context.state.project.target_duration_seconds
                or sp.estimated_duration_seconds
            ),
            "full_script": sp.full_script or "No script available.",
            "story_beats": beats_text or "No beats available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        scenes = [
            PlannedScene(
                scene_number=s.get("scene_number", i + 1),
                scene_id=s.get("scene_id", f"sc{i+1}"),
                title=s.get("title", ""),
                start_timestamp=s.get("start_timestamp", 0.0),
                end_timestamp=s.get("end_timestamp", 0.0),
                narration=s.get("narration", ""),
                estimated_duration_seconds=s.get("estimated_duration_seconds", 0),
                scene_goal=s.get("scene_goal", ""),
                scene_type=s.get("scene_type", "talking"),
            )
            for i, s in enumerate(data.get("scenes", []))
        ]

        # Fallback: if the LLM output could not be parsed (e.g. JSON
        # validation failed), create basic scenes from the script package
        # sections so downstream agents have something to work with.
        if not scenes:
            scenes = self._create_fallback_scenes(context)

        # The LLM plans scene lengths so they sum to the requested
        # duration; validate + minimally repair them rather than
        # re-deriving durations from narration word counts.
        _validate_scene_durations(
            scenes, context.state.project.target_duration_seconds
        )
        total_duration = sum(s.estimated_duration_seconds for s in scenes)
        return SceneSegmentationResult(
            scenes=scenes,
            total_scenes=len(scenes),
            total_duration_seconds=total_duration,
        )

    def _create_fallback_scenes(self, context: AgentContext) -> list[PlannedScene]:
        """Create basic scenes from the script package when LLM parsing fails.

        Uses the script's hook, sections, and CTA to produce one scene per
        segment with reasonable defaults.  This ensures downstream agents
        (visual, camera, voice, rendering) always have scenes to work with.
        """
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        scenes: list[PlannedScene] = []
        start_ts = 0.0

        # Hook scene
        if sp.hook_result and sp.hook_result.selected_hook:
            duration = 10
            scenes.append(PlannedScene(
                scene_number=0,
                scene_id="sc_hook",
                title="Hook",
                start_timestamp=start_ts,
                end_timestamp=start_ts + duration,
                narration=sp.hook_result.selected_hook.content,
                estimated_duration_seconds=duration,
                scene_goal="hook",
                scene_type="talking",
            ))
            start_ts += duration

        # One scene per script section
        for i, section in enumerate(sp.sections):
            duration = section.estimated_duration_seconds or 30
            scenes.append(PlannedScene(
                scene_number=i + 1,
                scene_id=f"sc{i+1}",
                title=section.title or f"Scene {i + 1}",
                start_timestamp=start_ts,
                end_timestamp=start_ts + duration,
                narration=section.narration,
                estimated_duration_seconds=duration,
                scene_goal=section.purpose or "inform",
                scene_type="talking",
            ))
            start_ts += duration

        # CTA scene
        if sp.cta_result and sp.cta_result.primary_cta:
            duration = 10
            scenes.append(PlannedScene(
                scene_number=len(scenes) + 1,
                scene_id=f"sc_cta",
                title="Call to Action",
                start_timestamp=start_ts,
                end_timestamp=start_ts + duration,
                narration=sp.cta_result.primary_cta.content,
                estimated_duration_seconds=duration,
                scene_goal="cta",
                scene_type="talking",
            ))
            start_ts += duration

        # Renumber scenes sequentially
        for i, scene in enumerate(scenes):
            scene.scene_number = i + 1

        return scenes

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, SceneSegmentationResult):
            context.state.storyboard.metadata["scenes"] = result.model_dump()


_WORDS_PER_SECOND = 2.5  # ~150 wpm narration rate


def _validate_scene_durations(
    scenes: list[PlannedScene],
    target_seconds: int | None,
) -> None:
    """Validate the LLM-planned scene durations against the target.

    The prompt instructs the model to choose the scene count and assign
    each scene a Veo-feasible length (even seconds >= 4) that sums exactly
    to the requested duration.  This pass is a minimal repair only:

    - missing/zero durations fall back to a narration-length estimate,
    - Veo mode snaps each duration to the nearest even >= 4 so billed
      clip time equals the scene length exactly,
    - any residual drift from ``target_seconds`` is redistributed so the
      timeline still totals the requested duration,
    - ``start_timestamp``/``end_timestamp`` are rewritten from the final
      values.
    """
    if not scenes:
        return

    durations: list[float] = []
    for s in scenes:
        d = float(s.estimated_duration_seconds or 0)
        if d <= 0:
            d = max(len(s.narration.split()) / _WORDS_PER_SECOND, 3.0)
        durations.append(max(d, 1.0))

    if _veo_clip_alignment_enabled():
        durations = _snap_to_veo_durations(durations, target_seconds)
    elif target_seconds:
        # LLM durations are trusted; rescale only if the total drifted.
        total = sum(durations)
        if total > 0 and abs(total - target_seconds) > 1.0:
            scale = target_seconds / total
            durations = [d * scale for d in durations]

    cursor = 0.0
    for scene, duration in zip(scenes, durations):
        scene.estimated_duration_seconds = max(1, round(duration))
        scene.start_timestamp = round(cursor, 2)
        cursor += duration
        scene.end_timestamp = round(cursor, 2)


def _veo_clip_alignment_enabled() -> bool:
    """True when Veo video generation is enabled (``USE_VEO``)."""
    try:
        from src.core.config import get_settings

        return bool(getattr(get_settings().veo, "enabled", False))
    except Exception:
        return False


def _snap_to_veo_durations(
    durations: list[float],
    target_seconds: int | None,
) -> list[float]:
    """Snap durations to even values >= 4 — exactly coverable by 4/6/8s clips.

    The rounding residual is redistributed in ±2s steps (largest scenes
    first, never below 4s) so the total still equals ``target_seconds``.
    Any leftover odd second is assigned to the longest scene — that single
    scene may keep a non-even duration, which the clip plan still covers
    with <3s of overshoot.
    """
    snapped = [max(4.0, float(round(d / 2.0) * 2)) for d in durations]
    if not target_seconds:
        return snapped

    diff = float(target_seconds) - sum(snapped)
    order = sorted(range(len(snapped)), key=lambda i: snapped[i], reverse=True)
    step = 2.0 if diff > 0 else -2.0
    while abs(diff) >= 2.0:
        progressed = False
        for i in order:
            if abs(diff) < 2.0:
                break
            if snapped[i] + step >= 4.0:
                snapped[i] += step
                diff -= step
                progressed = True
        if not progressed:
            break
    if diff:
        snapped[order[0]] = max(4.0, snapped[order[0]] + diff)
    return snapped
