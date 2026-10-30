# Direct Cinematic Pipeline — Veo 3.1 Lite

> **Purpose**: Architecture document for the *Direct cinematic video*
> production flow — the mode that generates a short cinematic video
> directly from a user-supplied shot specification using Google
> **Veo 3.1 Fast** (`veo-3.1-fast-generate-preview`) with provider-side
> video extension, skipping the
> research/script/storyboard LLM agent graphs entirely.
>
> **Audience**: engineering review. Companion test inputs:
> `CINEMATIC_FLOW_TEST_INPUTS.md`.

---

## 1. Overview

The system supports two production modes per project
(`project.metadata["production_mode"]`):

| Mode | Description |
|---|---|
| `explainer` (default) | Full LangGraph pipeline: research → script → storyboard → per-scene assets → TTS → render → thumbnail → SEO. |
| `direct_cinematic` | **This document.** The user writes the production spec directly; the backend builds a single-scene storyboard deterministically (no LLM) and generates the video as a chain of Veo clips. |

Design intent: Veo 3.1 Fast generates short clips and supports
provider-side **7-second video extension**. Direct cinematic starts with
one Veo clip, extends the original Veo resource as many times as needed to
cover the requested duration, then trims and normalizes the combined result
locally. This avoids concatenating independent generated clips for direct
cinematic continuity.

```text
User form (Next.js)
    │  description, visual_anchor, clip_beats[], avoid, narration_text,
    │  target_duration_seconds, aspect_ratio
    ▼
POST /projects ── CreateProjectRequest.validate_direct_cinematic()
    │  metadata: { production_mode: "direct_cinematic", visual_anchor,
    │             clip_beats, avoid, narration_text, aspect_ratio }
    ▼
Celery: execute_workflow_task  (workflow_tasks.py)
    │
    ├─ RESEARCH             ── skipped
    ├─ SCRIPTING            ── skipped
    ├─ STORYBOARD           ── _build_direct_storyboard()  (deterministic, no LLM)
    ├─ SCENE_PLANNING       ── 1 Scene row created
    ├─ ASSET_GENERATION     ── _generate_scene_video() → initial Veo clip + extensions → scene_1.mp4
    ├─ VOICE_GENERATION     ── only if narration_text set (Edge/Google TTS)
    ├─ SUBTITLE_GENERATION  ── only if narration_text set (SRT from narration)
    ├─ RENDERING            ── _render_composition_multi_pass() → final_video.mp4
    ├─ THUMBNAIL            ── ffmpeg frame grab @1s from final video
    └─ SEO                  ── skipped; PUBLISHING disabled pipeline-wide
```

---

## 2. Inputs and validation

### UI → API field mapping

| UI field (New Project → Production Flow = "Direct cinematic video") | API field (`CreateProjectRequest`) | Stored at |
|---|---|---|
| Description (static scene spec — no action) | `description` | `projects.description` |
| Fixed subject and setting | `visual_anchor` | `project.metadata["visual_anchor"]` |
| Ordered clip beats (one per line) | `clip_beats: list[str]` | `project.metadata["clip_beats"]` |
| Avoid | `avoid` | `project.metadata["avoid"]` |
| Narration (optional) | `narration_text` | `project.metadata["narration_text"]` |
| Target Duration (sec) | `target_duration_seconds` | `projects.target_duration_seconds` |
| Aspect Ratio | `aspect_ratio` (`16:9` / `9:16`) | `project.metadata["aspect_ratio"]` |

### Validation (`business_dtos.py::CreateProjectRequest.validate_direct_cinematic`)

- `content_type` must be `youtube_video`; `description` required.
- `target_duration_seconds` must be **4–120 s**.
- `visual_anchor` and `clip_beats` required; for direct extension the beat
  count is `1` for durations up to 8 s, otherwise
  `1 + ceil((duration - 8) / 7)` (e.g. 15 s → 2 beats, 30 s → 5 beats).
- Prompt budget: `len(description) + len(visual_anchor) + len(avoid)
  + max(beat lengths) + 300 ≤ 3500` chars (Veo ~1024-token prompt limit).
- Narration must fit: `words ≤ duration × 2` (≈120 wpm cap).
- The frontend enforces the same rules before submit
  (`apps/web/.../projects/new/page.tsx`) and shows the required beat
  count derived from the duration.

### Hard guarantees enforced in the backend

- `_build_direct_storyboard` re-validates the whole spec at workflow
  time and fails fast if Veo is disabled (`USE_VEO`).
- At ASSET_GENERATION, the storyboard package is **diffed against
  `project.metadata`** — if anything drifted, the run raises
  `"Direct cinematic storyboard changed the production specification"`.
- Any Veo/provider failure or missing frame-handoff is **fatal** in this
  mode (no silent fallbacks — see §7).

---

## 3. Workflow steps

The pipeline runs inside `execute_workflow_task`
(`src/infrastructure/tasks/workflow_tasks.py`). Step routing lives in
`_create_step_output`; the mode check is
`_is_direct_cinematic(project)` → `metadata["production_mode"] ==
"direct_cinematic"`.

| Step | Direct cinematic behavior |
|---|---|
| `INITIALIZATION` | Unchanged — builds `WorkflowState` with `target_resolution` from aspect ratio (`1080x1920` for 9:16). |
| `RESEARCH` | **Skipped.** The LLM-provider check is also bypassed, so a run needs only a Veo key. |
| `SCRIPTING` | **Skipped.** |
| `STORYBOARD` | `_build_direct_storyboard()` synthesizes a `StoryboardPackage` with **exactly one scene** (`sc1`): `visual_description = description`, `shared_context = visual_anchor`, `metadata = {clip_beats, avoid}`, `asset_type = "ai_video"`. No agents run. |
| `SCENE_PLANNING` | Unchanged — persists 1 `Scene` row from the package. |
| `ASSET_GENERATION` | `_generate_scene_video()` — initial Veo generation followed by provider-side 7-second extensions (§4). Requires a registered `veo` `VideoProvider`, else the run fails. |
| `VOICE_GENERATION` | Runs **only when `narration_text` is set**: single TTS clip for the one scene, with speaking-rate correction (0.8–1.35×) so audio fits `target_duration`; raises if audio exceeds scene duration + 0.25 s. |
| `SUBTITLE_GENERATION` | Runs **only when `narration_text` is set**: generates an SRT from the narration text. |
| `RENDERING` | `_render_composition_multi_pass()` — per-scene render + concat (§6). If there is no voice asset, Veo's **embedded clip audio** is mapped onto the voice track so ambient sound is preserved. |
| `THUMBNAIL` | No image assets exist, so it falls back to extracting a frame at **t=1 s** from `final_video.mp4`. |
| `SEO` | **Skipped** for direct cinematic. |
| `PUBLISHING` | Disabled pipeline-wide (commented out). |

---

## 4. Veo clip planning and prompt construction

### 4.1 Duration → extension plan (`_plan_direct_cinematic_segments`)

Direct cinematic uses one initial Veo generation followed by 7-second
provider-side extensions:

```text
requested <= 8 s: [one initial Veo clip]
requested > 8 s: [8] + [7] * ceil((requested - 8) / 7)
```

Examples:

```text
8 s  → [8]          → 8 generated seconds
15 s → [8, 7]       → 15 generated seconds
20 s → [8, 7, 7]    → 22 generated seconds, trim to 20
30 s → [8, 7, 7, 7, 7] → 36 generated seconds, trim to 30
```

The final combined Veo result is locally normalized to 720p/24 fps and
trimmed to the requested duration. Beat lines map directly to the initial
segment and each extension; no automatic shortest-first reordering occurs.

### 4.2 Per-clip prompt (`_generate_scene_video`)

```text
clip 0:
  "Fixed production specification: <description>.
   Same subject and location throughout: <visual_anchor>.
   Avoid: <avoid | default>.
   This clip is part 1 of N; show ONLY this action beat: <beats[0]>.
   Establish the subject and setting."

clip k>0 (with seed frame):
  "Same subject and location throughout: <visual_anchor>.
   Avoid: <avoid | default>.
   This clip is part k+1 of N; show ONLY this action beat: <beats[k]>.
   The supplied image is this clip's exact first frame; continue its
   motion and camera. Do not restart or repeat earlier action."
```

Rationale baked into the design (learned from earlier failures):

- **Action never appears in `description`** — Veo renders the entire
  action it reads into the first clip (caused a mid-air
  teleport/overshoot). Action lives only in beats.
- **The full spec goes to clip 1 only** — repeating it on continuations
  re-narrates the arc and fights the seeded frame.
- A beat must not reference later-clip events, even negatively.

### 4.3 Provider-side video extension (continuity)

- The initial Veo call explicitly requests `resolution="720p"` (even for
  an 8-second clip) because Gemini API extension accepts only 720p input.
- The downloaded initial video is probed locally; if its dimensions are not
  720p for the selected aspect ratio, the workflow fails before making an
  extension request.
- The initial call retains both downloaded bytes and the original
  provider-side `generated_videos[0].video` resource.
- Each continuation calls `generate_videos(video=<previous Veo resource>,
  prompt=<next beat>)`; local MP4 files are never re-uploaded as extension
  sources.
- Google extension adds 7 seconds and returns a combined video. The latest
  remote resource replaces the previous one for the next extension.
- Losing the remote resource or receiving a non-Veo result is fatal in direct
  cinematic mode.
- The final combined video is normalized locally after the last extension;
  no independent clip concatenation is used for the direct path.

### 4.4 Video normalization (`_concat_video_clips`)

- Direct cinematic always decodes and normalizes the combined result to
  720p (`720x1280` portrait or `1280x720` landscape), 24 fps, yuv420p,
  AAC 48 kHz stereo, and `+faststart`.
- The normalized video and its complete audio stream are trimmed to the
  requested duration only after extension generation has covered it.
- The explainer path retains the stream-copy fast path for uniform clips;
  mixed resolutions are re-encoded before downstream rendering.

The normalized result is uploaded as
`storage/projects/<id>/videos/scene_1.mp4` and recorded as a
`VideoAsset` at the requested duration and 24 fps. The `Scene` row's
`duration_seconds` is the requested output duration, not the over-generated
extension total.

---

## 5. Veo provider (`src/ai/providers/veo.py`)

| Aspect | Detail |
|---|---|
| SDK | `google-genai` (Gemini API) — `client.models.generate_videos` is a long-running operation |
| Default model | `veo-3.1-fast-generate-preview` (`GOOGLE_VEO_MODEL`) |
| API key | `GOOGLE_VEO_API_KEY`, falling back to `GEMINI_API_KEY` (same credential serves Veo) |
| Enablement | `USE_VEO=true`; registration in `providers/registry.py::_register_video_providers` |
| Durations | Initial generation uses the supported Veo duration; extension adds exactly **7 s** per call |
| Extension | Supported by Veo 3.1 Fast, not Lite; requires the original remote Veo video resource |
| Resolution | Direct extension input/output is normalized to **720p** locally; final render may upscale |
| Aspect ratio | `16:9` or `9:16` (derived from target width/height); direct output normalized at **24 fps** |
| Audio | Native Veo audio is retained through extension and local normalization when narration is blank |
| Polling | `client.operations.get(op)` every **10 s** until `done`, bounded by `GOOGLE_VEO_REQUEST_TIMEOUT` (default 600 s) |
| Cost | `COST_VEO_PER_SECOND` defaults to **$0.10**; initial seconds plus 7-second extension seconds are tracked |
| Retry/fallback | `VideoGateway._call_with_retry` — `GOOGLE_VEO_MAX_RETRIES` (default 2) with exponential backoff; direct extension never falls back to another provider |

All calls are traced to Langfuse (`video_generation_scene_N_clip_K`)
and per-clip cost is recorded on the workflow state + cost tracker;
per-clip prompts/durations/handoff status land in
`workflow_state.metadata.custom["video_clips"]`.

---

## 6. Rendering (`_render_composition_multi_pass`)

1. For each scene, a `SceneAssetManifest` is built (image, video,
   voice, subtitles) and rendered **separately** by
   `FFmpegCompositionRenderer` through `RenderingPipeline` — avoids the
   single huge filter graph that used to OOM on long sequences.
   Direct cinematic uses 24 fps at the project's target resolution
   (e.g. `1080x1920`); explainer mode retains 30 fps.
2. **Audio rule for direct cinematic**: when the scene has a video but
   *no* voice asset, `ffprobe` checks whether the Veo clip has an audio
   stream; if so the clip's own audio is appended to the timeline's
   VOICE track — preserving Veo's native ambient/effects audio.
   When narration exists, the TTS voice asset is used normally.
3. Scene parts are concatenated with `ffmpeg -f concat -c copy` — no
   trimming, since the clip plan already covers the target duration.
4. Output: `storage/projects/<id>/final_video.mp4`. Per-scene SRTs are
   merged into a video-level SRT offset by cumulative scene duration
   (`_combine_scene_subtitles`).

---

## 7. Failure semantics

Direct cinematic is deliberately **strict** — a degraded result is
worse than a failed run because the user is paying for exact-spec
footage:

| Condition | Behavior |
|---|---|
| Veo provider unavailable / `USE_VEO` off | Fail at storyboard or asset step |
| Beat count ≠ clip plan | `ValueError` before any API call |
| Clip generated by non-Veo provider | `RuntimeError` (fallback disabled) |
| Frame handoff extraction fails | `RuntimeError` |
| Narration longer than scene duration + 0.25 s | `ValueError` |
| Any clip generation error | Propagates — run fails (no image fallback) |

By contrast, the explainer mode degrades gracefully: per-scene Veo
failure → AI image, missing frame → unchained clip.

---

## 8. Observability & artifacts

| What | Where |
|---|---|
| Per-clip prompt, duration, provider, cost, frame-handoff status | `storage/workflow_state/<project>/<workflow>/workflow_state.json` → `metadata.custom.video_clips` |
| Step I/O (skipped flags, clip counts) | `metadata.custom.step_input` / `step_output` |
| LLM/generation tracing | Langfuse traces + `prompt_executions`-style cost records via `cost_tracker` |
| Scene video | `storage/projects/<id>/videos/scene_1.mp4` |
| Final video | `storage/projects/<id>/final_video.mp4` |
| Thumbnail | `storage/projects/<id>/thumbnails/thumbnail.png` |
| Combined subtitles | `storage/projects/<id>/subtitles/<project-id>.srt` |

---

## 9. Known limitations

- **7 s per extension** — a 30 s video may generate 36 seconds and trim
  locally; every extension depends on the previous remote Veo resource.
- **720p extension** — direct extension is normalized to 720p before the
  final render upscales to the selected project resolution.
- **Extension ≠ guaranteed continuity** — provider-side continuation is
  stronger than a seeded frame but cannot guarantee perfect physics or an
  invisible seam.
- **Remote-resource lifetime** — Gemini extension requires a Veo-generated
  resource retained by Google; a downloaded local MP4 cannot be used as a
  replacement after the resource expires.
- **Single scene** — direct cinematic produces exactly one logical
  scene; multi-shot sequences are expressed as beats, not scenes.
- **No reference-video conditioning** — the current UI still does not upload
  the user's reference video as an extension source.
- **Cost is real** — at the configured $0.10/s, a 15 s extension plan is
  approximately $1.50 and a 30 s plan may bill 36 generated seconds
  (approximately $3.60) before local trimming.

---

## 10. Key files

| Concern | File |
|---|---|
| Workflow orchestration + all cinematic logic | `backend/src/infrastructure/tasks/workflow_tasks.py` (`_is_direct_cinematic`, `_build_direct_storyboard`, `_plan_veo_clip_durations`, `_build_veo_prompt`, `_generate_scene_video`, `_concat_video_clips`, `_extract_last_frame_png`, `_render_composition_multi_pass`) |
| Veo provider | `backend/src/ai/providers/veo.py` |
| Video gateway (retry/fallback/tracing) | `backend/src/ai/gateway/video_gateway.py` |
| Provider registration | `backend/src/ai/providers/registry.py::_register_video_providers` |
| API validation | `backend/src/application/dto/business_dtos.py::CreateProjectRequest` |
| Metadata persistence | `backend/src/application/services/project_service.py::create_project` |
| Settings (`USE_VEO`, keys, timeouts, cost) | `backend/src/core/config.py::VeoSettings`, `CostSettings` |
| Project creation UI | `frontend/apps/web/src/app/(workspace)/projects/new/page.tsx` |
| Composition/rendering | `backend/src/composition/{builder,pipeline,ffmpeg_renderer}.py` |
| Test inputs / prompt guidance | `CINEMATIC_FLOW_TEST_INPUTS.md` |
