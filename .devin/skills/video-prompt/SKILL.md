---
name: video-prompt
description: Analyze a reference video (or text description) and generate optimized direct-cinematic prompts for the New Project UI
argument-hint: "<path to reference video or description of what the video should show>"
triggers:
  - user
---

# Generate direct-cinematic video prompts

The user provides either a **reference video file** or a **text description** of the video they want. Analyze the input, then produce a complete set of copy-paste fields for the **New Project** page using the **direct cinematic** production flow.

## Step 1 — Analyze the input

### If the user provides a reference video

1. Copy the video into `storage/` so the API container can access it.
2. Run `ffprobe` inside the `aivideo_api` container to get duration, resolution, fps, audio codec.
3. Extract key frames at every 1-second interval:
   ```bash
   docker exec aivideo_api bash -c "
     mkdir -p /app/storage/ref_frames
     for t in 0 1 2 3 ... N; do
       ffmpeg -y -ss \$t -i /app/storage/ref_video.mp4 -frames:v 1 -q:v 2 /app/storage/ref_frames/frame_\${t}s.jpg 2>/dev/null
     done
   "
   ```
4. Copy frames back to the host and **read every frame** to understand the visual content.
5. Document a shot-by-shot breakdown:
   - What's on screen at each second
   - Subject appearance (clothing, body type, distinguishing features)
   - Setting/environment (location type, lighting, weather, geological features)
   - Camera angle **and motion** (POV, chase cam, drone, tracking, static, tilts/pans)
   - Other people/elements in the scene
   - Audio characteristics (ambient sounds, speech, music)
   - The **hook** — what makes this video grab attention in the first 2 seconds
   - **Where the payoff lands** (% of runtime) — the strongest videos keep it late
6. Clean up temp files when done.

### If the user provides a text description

Ask clarifying questions if needed about:
- Camera perspective (first-person POV vs third-person vs drone vs chase)
- Subject appearance
- Setting details
- Duration preference
- What the "hook" moment is

## Step 2 — Design the prompts

### Understanding the direct cinematic pipeline

The direct cinematic flow bypasses the research/script/storyboard agents entirely. The user's description, visual anchor, beats, and avoid text are sent **directly to Google Veo** for video generation.

**How Veo generation works:**
- Initial clip: 8 seconds (for durations > 8s)
- Each extension: adds 7 seconds via Veo's server-side video extension API
- Extension uses the **last 1 second (24 frames)** of the previous clip as visual context
- Extension returns a **single combined video** (original + new footage)
- Final output is trimmed to the requested duration

**Duration → beat count mapping:**
| Duration | Beats | Segments |
|---|---|---|
| 4s | 1 | `[4]` |
| 6s | 1 | `[6]` |
| 8s | 1 | `[8]` |
| 9–15s | 2 | `[8, 7]` |
| 16–22s | 3 | `[8, 7, 7]` |
| 23–29s | 4 | `[8, 7, 7, 7]` |
| 30–36s | 5 | `[8, 7, 7, 7, 7]` |

The number of beats MUST match the segment count or the backend will reject the request.

### Beat 1 uses STRUCTURED sections (current UI)

Beat 1 is **not** a single textarea in the current UI — it has separate labeled fields. When generating a prompt set, output **each field separately** so the user can paste them one-by-one:

| Section field | Required | Content |
|---|---|---|
| **Scene** | Required | Location, environment, weather, subject, spectators — one dense paragraph |
| **Camera** | Required | Camera type + position + movement + explicit negatives ("never in front, never side view, never drone") |
| **Action** | Required | What the subject does, in order — the actual motion sequence |
| **Ending** | Optional | Where the clip should end — the handoff frame. Leave blank to let Veo decide |
| **Visual style** | Optional | Photorealistic, motion blur, real-time speed |
| **Audio** | Optional | Ambient sound design, no music/narration |
| **Continuity** | Optional | What must stay identical (subject, outfit, environment, weather) |
| **Avoid in this clip** | Optional | Per-clip negatives (cuts, teleportation, drone shots, floating) |

The UI composes these into `clip_beats[0]` as a labeled block (`SCENE:\n...\n\nCAMERA:\n...`). Empty optional sections are omitted.

**Beats 2+** stay as plain textareas — extension prompts (`Continue smoothly from the last frame...` + action text).

### Proven techniques (from real generated videos — 500K+ views)

These come from debugging real runs, including a fjord chase-dive that produced excellent output:

1. **"Camera = second person jumping behind him"** — the single most effective camera technique discovered. Instead of abstract camera directions, tell Veo the camera represents another person following the subject. Produces genuine chase-cam footage: subject stays centered in foreground, real speed, strong vertigo.

2. **Structured sections beat long prose.** The winning fjord prompt was 3100+ chars organized into SCENE/CAMERA/ACTION/ENDING/STYLE/AUDIO/CONTINUITY/AVOID — each section one clear job. Veo handled the length fine BECAUSE it was organized. Long unstructured paragraphs fail; long labeled sections work.

3. **Match fall/drop distance to remaining clip time** — `height ≈ ½·g·t²` where t = seconds left in the clip after setup:
   - ~5.5s of fall available → 150–200m cliff (impact lands right at the boundary)
   - ~3s of fall available → 50m
   - 1000m cliff forced Veo to teleport the diver — the failure mode you get when distance >> time

4. **END the initial clip "a split second before impact/landing."** The safest handoff frame is impact-imminent: foam, near-surface, or contact-in-progress. Splash/impact frames extend perfectly because there's no body-position detail to mismatch. Mid-air close-ups are the riskiest boundary.

5. **Extension beats start with what the viewer sees.** "He keeps falling, now a tiny speck" or "The white water clears" grounds the extension in the current visual state before requesting new action.

6. **Extension prompts are already kept short by the code** — just prefix + beat text. Anchor/avoid/description are NOT repeated; Veo gets continuity from the video itself. Keep extension beats ~150–400 chars, one action phase.

7. **Real-time, not slow-mo — say it twice.** Put "real-time speed — NOT slow motion" in the description AND "no slow motion, no floaty movement" in avoid. Veo defaults to cinematic drift otherwise.

8. **Visual anchor = static identity ONLY.** Character appearance, location, camera style. Never pacing or action. Sent verbatim in the initial prompt.

9. **No sub-second timestamps.** Describe action progression, not "0.0–1.5s:" choreography.

10. **One distinctive visual pop helps** — bright/pink shorts, colorful raincoats on spectators. Makes the subject instantly trackable and memorable.

### Retention rules (from view analytics: 150K-view vs 500-view comparison)

- **Delay the payoff to ~65–75% of runtime.** Splash/payoff at ~10s of 15s keeps retention; payoff at ~5s caused 52% drop-off by 5s.
- **Scale dwarfs the human.** A tiny splash in a vast fjord is more terrifying than a frame-filling wave. Environment should dominate.
- **Every frame must show progress.** Falling/getting smaller, water approaching — never 2+ seconds of static noise (whiteout = retention cliff).
- **Reaction faces in frame 0** (someone covering their mouth) pre-sell danger better than 15 passive spectators.
- **Harsh environments add stakes** — rain/storm/ice > sunny tropical.
- **Match the reference's duration.** Don't stretch a 10s reference to 15s — either match it or put the extra seconds in calm aftermath.

### Prompt budget

Max prompt per Veo API call: **3500 chars**. Initial prompt = description + anchor + avoid + composed beat 1 + ~200 chars overhead. Extension = ~112 char prefix + beat.

| Field | Target |
|---|---|
| Description | 150–800 chars |
| Visual anchor | 300–450 chars |
| Avoid | 200–350 chars |
| Beat 1 (composed) | 1200–2500 chars for structured, ~300–400 for simple |
| Beat 2+ | 150–400 chars |
| **Initial total** | **< 3500** |
| **Extension total** | typically 300–500 |

### Hook design

First 2 seconds decide retention. Open with:
- **Instant visual intrigue** — unusual location, dramatic scale
- **Human reaction face** — spectator's fear/anticipation
- **Implied danger** — edge, height, drop visible in frame

## Step 3 — Validate the prompts

Run validation inside the API container (no Veo call):

```python
docker exec aivideo_api python -c "
from src.application.services.direct_cinematic import direct_clip_prompt, plan_direct_segments, max_direct_prompt_chars

# verify:
# 1. beat count == plan_direct_segments(duration)
# 2. max_direct_prompt_chars(...) < 3500
# 3. print actual clip-0 and extension prompts with char counts
"
```

Also validate the DTO:

```python
docker exec aivideo_api python -c "
from src.application.dto.business_dtos import CreateProjectRequest
req = CreateProjectRequest(
    title=..., description=..., content_type='youtube_video',
    production_mode='direct_cinematic', target_duration_seconds=...,
    aspect_ratio='9:16', video_style='cinematic', language='en',
    visual_anchor=..., clip_beats=[composed_beat1, beat2, ...],
    avoid=..., narration_text='', audience='', tags=[],
)
print('ACCEPTED')
"
```

When simulating the composed beat 1, build it exactly like the UI does:

```python
sections = {'scene': '...', 'camera': '...', 'action': '...',
            'ending': '', 'visual_style': '...', 'audio': '...',
            'continuity': '...', 'avoid': '...'}
composed = '\n\n'.join(
    f'{k.upper()}:\n{v.strip()}' for k, v in sections.items() if v.strip()
)
# visual_style label renders as "VISUAL STYLE:" — adjust accordingly
```

## Step 4 — Present the output

Give the user a complete copy-paste set:

### Settings table

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `{title}` |
| Description | Paste Description below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste Fixed subject and setting below |
| Number of clip beats | **{N}** |
| Beat 1 → Scene / Camera / Action / Ending / Visual style / Audio / Continuity / Avoid | Paste each section below |
| Beat 2+ | Paste each below |
| Avoid | Paste Avoid below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `{duration}` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

### Each Beat 1 section as a labeled code block

```text
{SCENE text}
```

```text
{CAMERA text}
```

```text
{ACTION text}
```

```text
{ENDING text — or "leave blank"}
```

etc.

### Beats 2+ as labeled code blocks

```text
{beat 2 text}
```

### Prompt budget table

Field char counts, composed initial/extension prompt sizes, confirm < 3500.

### Cost warning

`{duration}s × $0.10/s = ${cost}`. Tier 1 = 2 RPM — space runs 60+ seconds apart.

## Optional: direct API test scripts

For testing prompts outside the UI workflow, `_veo_fjord_test.py` (initial gen) and `_veo_fjord_extend.py` (extension via Files API URI) exist at the repo root and can be copied/adapted. They run inside `aivideo_api` — **they make real billed Veo calls; ask the user before running.**

Technical note: extensions can reuse a remote video via `client.files.get()` → `types.Video(uri=f.uri)` — pass **uri only, NO mime_type** (it serializes as `encoding`, which the model rejects with 400).

## Valid enum values

- **content_type**: `youtube_video`, `blog`, `linkedin`, `twitter`, `instagram`, `podcast`, `documentation`, `course`
- **video_style**: `cinematic`, `documentary`, `explainer`, `talking_head`, `animated`, `mixed`, `stock_footage`, `whiteboard`
- **aspect_ratio**: `16:9`, `9:16`
- **production_mode**: `direct_cinematic` (always for this skill)

## Existing test inputs for reference

See `CINEMATIC_FLOW_TEST_INPUTS.md` for proven prompt sets:
- POV headland sprint + ocean cliff dive
- Sinkhole swan dive (100K+ views)
- Storm fjord chase-dive (best continuity yet — structured sections + chase camera + 150–200m cliff + pre-impact ending)

## If the user asks about a previous run that went wrong

Use the `debug-video-project` skill instead.
