"""Direct cinematic planning shared between the API DTO and the workflow.

Keeping the segment plan and per-clip prompt composition in one module
guarantees that request-time validation always mirrors the prompts that
are actually sent to Veo at generation time.

Prompt design philosophy
------------------------
Veo video extension already *sees* the input video — it extracts the
last 1 second (24 frames) as visual context for style, character,
camera, lighting and motion direction.  Repeating all of that in the
text prompt competes with the visual signal and drowns the actual action
instruction.  Google's own example extension prompts are one sentence
(~50 chars); ours were 27× longer.

Therefore:
  * **Initial clip (clip 0)** gets the full specification: description,
    visual anchor, avoid, beat, and an "Establish…" instruction.
  * **Extension clips (clip 1+)** get only a short continuation prefix
    and the user's action beat.  The visual anchor and avoid are omitted
    because the model already has that context from the video.
"""

import math

# Veo generates one initial clip (4/6/8s) and extends it in 7s increments.
INITIAL_SEGMENT_SECONDS = 8
EXTENSION_SEGMENT_SECONDS = 7

# Veo accepts ~1024 tokens per prompt; _build_veo_prompt truncates at this
# length, so requests are validated against the same bound.
MAX_VEO_PROMPT_CHARS = 3500

# Kling's documented prompt limit is 3072 characters (2500 recommended).
MAX_KLING_PROMPT_CHARS = 3072

# Short prefix for extension prompts — tells Veo to continue, not restart.
_EXTENSION_PREFIX = (
    "Continue smoothly from the last frame of this video. "
    "Same subject, camera and world — do not restart or cut. "
)

# Kling (fal.ai) generates up to 15 seconds in a single call; longer
# videos are chained in 15-second segments via last-frame image-to-video.
_KLING_MAX_SEGMENT_SECONDS = 15
_KLING_MIN_SEGMENT_SECONDS = 3


def _active_video_provider() -> str:
    """Return the configured primary video provider name.

    Matches the flag the UI uses (``USE_KLING`` / ``NEXT_PUBLIC_VIDEO_PROVIDER``)
    so request-time beat validation stays consistent with the beat count the
    form presents — even before ``FAL_KEY`` is populated.
    """
    try:
        from src.core.config import get_settings

        if get_settings().kling.enabled:
            return "kling"
    except Exception:
        pass
    return "veo"


def plan_direct_segments(
    duration_seconds: float, provider: str | None = None
) -> list[int]:
    """Plan clip segments for the active video provider.

    Veo generates one initial clip (4/6/8s) and extends it in 7-second
    increments; the extension API returns a combined video, so the plan
    covers the target and the result is trimmed locally.

    Kling generates up to 15 seconds per call; longer targets are split
    into ≤15s segments chained via last-frame image-to-video, then the
    accumulated result is trimmed locally to the requested duration.
    """
    provider = provider or _active_video_provider()
    target = max(float(duration_seconds or 0), 4.0)

    if provider == "kling":
        if target <= _KLING_MAX_SEGMENT_SECONDS:
            return [max(_KLING_MIN_SEGMENT_SECONDS, round(target))]
        remaining = target
        segments: list[int] = []
        while remaining > _KLING_MAX_SEGMENT_SECONDS:
            segments.append(_KLING_MAX_SEGMENT_SECONDS)
            remaining -= _KLING_MAX_SEGMENT_SECONDS
        segments.append(max(_KLING_MIN_SEGMENT_SECONDS, math.ceil(remaining)))
        return segments

    if target <= INITIAL_SEGMENT_SECONDS:
        return [4 if target <= 4 else 6 if target <= 6 else 8]
    extension_count = math.ceil((target - INITIAL_SEGMENT_SECONDS) / EXTENSION_SEGMENT_SECONDS)
    return [INITIAL_SEGMENT_SECONDS] + [EXTENSION_SEGMENT_SECONDS] * extension_count


def direct_clip_prompt(
    base_prompt: str,
    shared_context: str,
    avoid: str,
    beats: list[str],
    clip_index: int,
    provider: str | None = None,
) -> str:
    """Compose the exact prompt sent to the video provider for one segment.

    Initial clip (index 0): full context — description, visual anchor,
    avoid list, beat instruction, and an "Establish…" cue.

    Extension clips (index > 0): short and action-focused — a brief
    continuation prefix + the user's beat text.  Veo extension already
    has the visual context from the last 24 frames of the input video,
    so repeating the anchor/avoid/description would only dilute the
    action instruction and cause the model to rush through or skip
    portions of the requested beat.
    """
    provider = provider or _active_video_provider()

    if provider == "kling":
        if clip_index == 0:
            # Kling prompts should stay under ~2500 chars of focused prose
            # and the avoid list goes to the native negative_prompt param.
            return (
                f"{base_prompt}. {shared_context}. "
                f"{beats[0]}"
            )
        return f"{_EXTENSION_PREFIX}{beats[clip_index]}"

    if clip_index == 0:
        # --- initial clip: full specification ---
        return (
            f"Fixed production specification: {base_prompt}. "
            f"Same subject and location throughout: {shared_context}. "
            f"Avoid: {avoid or 'unrequested changes to subject, location and props'}. "
            f"This is the initial segment; show ONLY this action beat: {beats[0]}. "
            f"Establish the subject and camera position."
        )
    else:
        # --- extension clip: short action-only prompt ---
        return f"{_EXTENSION_PREFIX}{beats[clip_index]}"


def max_direct_prompt_chars(
    description: str, visual_anchor: str, avoid: str, beats: list[str]
) -> int:
    """Largest prompt any clip in the plan would send to Veo."""
    return max(
        len(direct_clip_prompt(description, visual_anchor, avoid, beats, i))
        for i in range(len(beats))
    )
