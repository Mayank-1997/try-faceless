# Test inputs for a video inspired by `storage/she_flies.mp4`

The reference is approximately 10 seconds, portrait 9:16: a blonde woman dressed in white dives from a limestone sinkhole rim toward a **small circular trampoline on the grassy floor**, bounces back up, and ends on the same ledge. There is **no water or pool**. These inputs aim to reproduce the sequence, not the exact pixels or an identical person.

## Important: direct cinematic now uses Veo extension

- The pipeline uses `veo-3.1-fast-generate-preview`.
- For a 10-second request, it generates an initial **8-second** Veo video and extends it by **7 seconds**, then trims the combined result to exactly 10 seconds.
- The second beat is sent as a Veo **video-extension prompt**, not as a new independent text-to-video clip.
- The initial Veo generation is explicitly requested at **720p**, as Gemini API extension rejects 1080p input. The downloaded first clip is checked for 720p dimensions before any extension request is made.
- The original Veo-generated remote video resource is retained in memory for the extension. A local MP4 is not uploaded back to Veo.
- The combined result is normalized to 720p/24 fps with AAC audio before the final render.
- For 15 seconds, use 2 beats: 8s initial + 7s extension.
- For 30 seconds, use 5 beats: 8s initial + four 7s extensions; the 36-second generated result is trimmed to 30 seconds.

Go to **New Project** and enter the following:

| UI field | Value |
| --- | --- |
| Content Type (step 1) | **YouTube Video** |
| Title | `Jungle Sinkhole Trampoline Bounce` |
| Description | Paste the Description block below (static scene specification only) |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Fixed subject and setting block below |
| Ordered clip beats | Paste the two lines below together, one per line |
| Avoid | Paste the Avoid block below |
| Narration | **Leave blank**; no TTS narration/subtitles |
| Language | **English** (default; unused without narration) |
| Target Duration (sec) | `10` |
| Target Audience | `Viewers of short cinematic stunts and adventure videos` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080×1920) — Shorts/Reels** |
| Tags (comma-separated) | `jungle, sinkhole, trampoline, cliff dive, cinematic stunt` |

## Description

Keep the action sequence out of this field. Action belongs in the ordered beats.

```text
A single continuous photorealistic vertical shot in soft natural daylight with the feel of a helmet-mounted handheld action camera. From behind and slightly above, the camera looks down past steep pale limestone walls and dense green jungle toward the grassy floor of a deep open-air sinkhole, where a tiny circular trampoline with a dark jumping surface and gray rim sits on the grass far below. An athletic adult woman with a long blonde ponytail, white racerback sports bra, white leggings and white athletic shoes stands on the rocky rim at the edge. Natural wind, falling-air and springy trampoline impact sounds; no spoken narration.
```

## Fixed subject and setting

```text
The same athletic adult blonde woman throughout: long blonde ponytail, white racerback sports bra, white leggings, white athletic shoes. One deep open-air limestone jungle sinkhole in soft natural daylight, with pale vertical rock walls, dense green foliage, a grassy floor and the same rocky starting ledge. A single small round trampoline with dark jumping fabric and a gray rim stands on the grass far below the ledge. Keep the character, clothing, location and trampoline fixed throughout the initial video and every extension.
```

## Ordered clip beats

Paste **exactly two lines** into the Ordered clip beats box. The first line controls the initial Veo video. The second line controls the 7-second Veo extension.

```text
The same woman launches headfirst from the rocky ledge and descends rapidly through the sinkhole toward the tiny round trampoline on the grassy floor; the camera follows continuously from above with the pale walls rushing past. End this initial segment while she is still descending immediately above the trampoline, before the rebound sequence.
Continue the supplied Veo video without restarting or replaying the dive: she impacts the center of the tiny floor-level trampoline, the mat flexes deeply, then launches her impossibly high upward; the camera tilts up and follows her rising until she lands standing on the exact same rocky ledge where she started, in the same white outfit.
```

## Avoid

```text
No water, pool, splash, cliff-mounted trampoline, harness, ropes, cables, industrial rig, outfit change, second woman, second trampoline, sunset, snow, studio, title card, captions, voiceover or hard cut. Keep the trampoline small and on the grassy ground below, not attached to the cliff. Maintain the same camera direction and continuous action across the Veo extension.
```

On the Review step confirm **Direct cinematic video**, **10s**, and **9:16 Portrait**. Click **Create Project**, then click **Start Workflow** on the project page. Creating the project alone does not generate video.

## After running

Check **Storyboard → Generation scene packages**, then:

```text
storage/workflow_state/<project-id>/<workflow-id>/workflow_state.json
```

Inspect these keys:

```text
storyboard.metadata.storyboard_package.scene_packages[0].metadata.clip_beats
metadata.custom.video_clips
```

For the new extension flow, `metadata.custom.video_clips` should show:

- Segment 0: `generation_mode: initial`, approximately 8 seconds.
- Segment 1: `generation_mode: extension`, approximately 7 seconds.
- Segment 1: `input_video_supplied: true`.
- Both segments: `remote_video_retained: true` during the workflow.

Inspect:

```text
storage/projects/<project-id>/videos/scene_1.mp4
storage/projects/<project-id>/final_video.mp4
```

The final output should be approximately 10 seconds, 24 fps, portrait, and should contain the combined Veo audio. If narration is blank, there will be no spoken voiceover; natural Veo wind, impact and environment audio should remain.

**Cost and limits:** With `COST_VEO_PER_SECOND=0.10`, this 10-second request bills approximately 15 generated seconds, or **$1.50**, because the extension produces 8s + 7s before local trimming. A 30-second request uses 8s + four 7s extensions, approximately 36 billed seconds or **$3.60**. Starting the workflow makes real Veo calls and consumes credits. The UI provides text direction, not reference-video conditioning; extension improves continuity but cannot guarantee exact physics or an invisible seam.

---

# Test inputs: 15-second video inspired by `C:\Users\91858\Downloads\cycling.mp4`

The reference is approximately 30 seconds, portrait 9:16 and 24 fps. It is a first-person bicycle ride: the camera starts on a broad high rooftop, enters a narrow steep track wrapping down around a glass skyscraper, and exits onto a broad flat rooftop endpoint. The rider's gloved hands, handlebars and front tire remain visible, with the city far below and warm hazy daylight. For this shorter version, the cyclist must complete the route and arrive safely at the endpoint **by the end of the 15-second video**; do not end mid-descent.

These inputs follow the direct-cinematic Veo extension plan:

- 15-second target = one **8-second initial video** + one **7-second extension**.
- Exactly **two ordered beats** are required.
- Beat 1 establishes the POV ride and begins the descent; beat 2 completes the descent, reaches the endpoint, decelerates and stops before the video ends.
- The workflow trims the combined extension output to 15 seconds. Avoid putting the endpoint only in a final action that is unlikely to finish in time; specify that the cyclist is fully stopped on the endpoint before the final frame.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `POV Rooftop Descent — 15 Second Ride` |
| Description | Paste the Cycling Description block below (scene/camera/style only; action goes in beats) |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Cycling Fixed subject and setting block below |
| Ordered clip beats | Paste the two Cycling Ordered clip beats, one per line |
| Avoid | Paste the Cycling Avoid block below |
| Narration | **Leave blank**; preserve Veo's generated wind/rolling/bicycle audio |
| Language | **English** (unused with blank narration) |
| Target Duration (sec) | `15` |
| Target Audience | `Viewers of immersive POV action and cinematic cycling videos` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080×1920) — Shorts/Reels** |
| Tags | `cycling, POV, rooftop descent, skyscraper, action camera, cinematic` |

## Cycling Description

```text
A photorealistic, thrilling first-person helmet-camera bicycle video in portrait 9:16, 24 fps, filmed as one continuous forward-facing POV with natural action-camera shake, realistic wheel vibration, directional motion blur and warm hazy late-afternoon light. The viewer sees the same rider's black-gloved hands gripping the same black handlebars and the same front tire at the bottom center of frame. The setting is a very tall modern glass skyscraper above a hazy city, with a broad flat rooftop start, a narrow pale concrete track that curves steeply down and wraps around the outside of the glass tower, and a broad, level rooftop landing platform at the route's end. Keep the track visibly connected to the endpoint and the endpoint large, flat and safe to stop on. Natural wind rush, tire roll and subtle bicycle rattling; no speech or music.
```

## Cycling Fixed subject and setting

```text
One continuous first-person helmet-mounted bicycle POV. Keep the same black bicycle, same front tire centered at the bottom, same handlebars and the same black-gloved hands visible throughout; never switch to an external camera or show the rider from behind. One modern glass skyscraper above a distant hazy city at warm late-afternoon light. The route is a single continuous narrow pale concrete track that begins on a broad flat rooftop, descends steeply while curving around the outside of the same tower, and terminates at one broad, level rooftop landing platform. Preserve the tower facade, route direction, bicycle geometry, camera height and lighting across the initial Veo video and its extension. The landing platform is a clear final destination, not another drop.
```

## Cycling Ordered clip beats

Paste exactly these two lines. The initial 8-second segment covers the start and most of the descent. The 7-second extension must finish the ride and show the successful arrival and stop.

```text
From the same first-person helmet camera, accelerate straight across the broad rooftop start and onto the narrow concrete track visibly attached to the glass tower. The front wheel and gloved hands stay in view as the track tips into a steep descent and begins its sweeping curve around the building; wind and tire vibration build. Continue forward down the connected track, but end this initial segment still partway through the descent with the route ahead clearly visible; do not reach the endpoint yet.
Continue the exact same POV ride from the supplied Veo video and follow the same connected track through the remainder of its steep curve around the glass tower. The camera and front wheel stay aligned with the path. The track visibly levels out into the broad rooftop landing platform; ride fully onto it, brake smoothly, and come to a complete controlled stop near the center, with both hands still on the handlebars and the bicycle stable. Hold the stopped POV on the safe flat endpoint for the final second. The cyclist must finish the route and be completely stopped before this extension ends; do not cut away or end mid-descent.
```

## Cycling Avoid

```text
No third-person shot, no drone view, no camera cuts, no camera teleport, no alternate bicycle, no disappearing or duplicated wheel/handlebars/hands, no change in glove or bicycle color, no broken or disconnected track, no sudden jump or flight, no falling off the building, no crash, no collision, no injury, no pedestrians or other cyclists, no extra ramps, no tunnel, no change to night or storm conditions, no text, subtitles, watermark, logo, narration or music. Keep the track connected all the way to the broad, flat rooftop endpoint and show the cyclist fully stopped there before the last frame.
```

### 15-second cycling check and cost

On the Review step check **Direct cinematic video**, **15 seconds** and **9:16 Portrait**. Create the project, then start its workflow. The expected generation plan is `8s initial + 7s extension`, normalized to **720×1280 at 24 fps**, with the final render at the selected project resolution and trimmed to 15 seconds. At the configured `$0.10` per generated second, the estimated Veo cost is **$1.50**, before retries. Do not start the workflow if you do not want a paid Veo generation.

The endpoint instructions make completion within 15 seconds explicit, but Veo can still miss route geometry, braking or the final stop. This text-only workflow does not condition on the reference MP4 itself, so it cannot guarantee an exact recreation or identical shot timing.

---

# Test inputs: 15-second video inspired by `C:\Users\91858\Downloads\cliff_jumping.mp4`

The reference is an adrenaline-charged ~14-second, 9:16 vertical POV video of a high cliff jump:
- **Perspective**: Ultra-wide first-person POV (chest/chin-mounted action camera) looking down past the jumper's torso, thighs, and shoes directly into a sheer, dizzying canyon void.
- **Progression**: Standing on the edge of the precipice looking down at a distant narrow river gorge far below, taking in the terrifying height, leaping forward into open space, freefalling with rushing wind and blurring rock walls, and slamming feet-first into deep water with an explosive splash and underwater immersion.

### Attribute changes applied (while matching or exceeding the thrill):
1. **Setting**: Changed from an old stone bridge/road structure to a breathtaking **natural 80-foot sheer granite canyon cliff** overlooking a pristine **crystal-clear turquoise mountain gorge pool** in crisp natural sunlight.
2. **Attire**: Changed from turquoise boardshorts with geometric waistband to **athletic crimson-red boardshorts and sleek black minimalist water shoes** for strong visual contrast against pale granite rock and turquoise water.
3. **Clean Scene**: Removed spectators on the cliff and swimmers in the water below so the jump feels raw, solitary, and intensely focused on the jumper's vertigo and courage.
4. **Duration & Pacing**: Tuned for the **15-second direct cinematic extension workflow** (`8s initial + 7s extension = 2 beats`):
   - **Beat 1 (8s initial)**: Teetering on the dizzying stone edge, looking straight down past the toes into the terrifying 80ft drop, then a late leap — the moment the feet leave the rock, time dilates into **dramatic slow motion** (matching the reference's 1–2s slow-mo hang-time). The clip ends suspended in slow-motion hang-time at the very top of the fall, the pool still a small turquoise patch far below. Ending high also prevents Veo overshooting into the water before the extension starts.
   - **Beat 2 (7s extension)**: The slow motion snaps back to real-time speed, the plummet accelerates to terminal velocity with canyon walls streaking past, pencil-dive alignment, and the feet **piercing the surface with zero deceleration** — the body punches straight through in one motion and the camera is instantly swallowed underwater into a roaring bubble column.
5. **Slow motion (v2 fix)**: The first generated version had no slow-motion beat and spent ~2–3 seconds skimming/floating on the water surface before submerging, because the initial clip ended with the feet already at the water. The revised beats below fix both: slow-mo hang-time caps the initial clip's descent, and the extension is instructed to pierce the surface with no skim or float.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `POV Cliff Jump — 80ft Canyon Gorge Dive` |
| Description | Paste the Cliff Jump Description block below (scene/camera/style only; action goes in beats) |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Cliff Jump Fixed subject and setting block below |
| Ordered clip beats | Paste the two Cliff Jump Ordered clip beats, one per line |
| Avoid | Paste the Cliff Jump Avoid block below |
| Narration | **Leave blank**; preserve Veo's generated wind rushing and explosive water splash audio |
| Language | **English** (unused with blank narration) |
| Target Duration (sec) | `15` |
| Target Audience | `Viewers of extreme stunts, cliff diving, and adrenaline POV action` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080×1920) — Shorts/Reels** |
| Tags | `cliff jumping, POV, 80ft dive, canyon, extreme sports, adrenaline, action camera, cinematic` |

## Cliff Jump Description

```text
A photorealistic, adrenaline-inducing first-person POV cliff diving video in portrait 9:16, 24 fps, shot on an ultra-wide action camera. The viewer sees the athletic diver's bare chest, athletic crimson-red boardshorts, and black water shoes at the bottom of the frame, looking straight down into a dizzying 80-foot vertical drop between sheer rugged canyon walls into a deep crystal-clear turquoise river pool below. Natural bright sunny daylight, realistic wide-angle perspective distortion, intense rushing wind and explosive water impact acoustics; no speech or music.
```

## Cliff Jump Fixed subject and setting

```text
One continuous first-person chest/chin action-camera POV of a cliff dive. The diver's athletic torso, bright crimson-red boardshorts, and black water shoes remain anchored at the bottom of the frame pointing downwards throughout. The location is a towering natural 80-foot sheer granite cliff precipice towering over a deep, narrow turquoise mountain river canyon in crisp natural daylight. Keep the diver's clothing, body frame, canyon walls, turquoise pool below, and camera orientation consistent across the initial video and its extension.
```

## Cliff Jump Ordered clip beats

Paste **exactly two lines** into the Ordered clip beats box. The first line controls the initial 8-second Veo video. The second line controls the 7-second Veo extension completing the dive and water entry.

```text
From the first-person camera looking down over the diver's toes on the dizzying rock precipice, hold on the terrifying 80-foot drop into the tiny turquoise pool far below, then take a powerful forward leap off the rock lip. The instant the feet leave the rock, time dilates into dramatic slow motion: the launch hangs in the air, shorts and shoes drifting slowly, the canyon rim creeping past. End this segment still suspended in slow-motion hang-time at the very top of the fall, the water a small patch far below.
Continue from the supplied Veo video in the same slow-motion hang-time for a brief beat, then speed snaps back to real time and the diver plummets at full falling speed toward the turquoise pool, canyon walls streaking past and wind roaring. The diver locks into a vertical pencil dive and the feet pierce the surface with zero deceleration — no skimming, no floating — the whole body punches straight through in one continuous motion and the camera is instantly engulfed underwater in a roaring column of white bubbles looking up at the fading circle of daylight.
```

## Cliff Jump Avoid

```text
No third-person view, no drone footage, no camera cuts, no camera teleport, no clothing change, no change of shorts color from crimson, no missing or distorted legs/feet, no shoes disappearing, no safety harness, no ropes, no bridge, no guardrails, no second jumper, no hitting rocks or canyon walls, no crash or injury, no floating or skimming across the water surface, no soft splashdown, no decelerating or hovering at the water surface, no sunset or night, no on-screen text, subtitles, watermark, logo, narration or music. The camera must pierce the surface and be fully underwater in bubbles before the video ends.
```

### 15-second cliff jump check and cost

On the Review step check **Direct cinematic video**, **15 seconds** and **9:16 Portrait**. Create the project, then click **Start Workflow**. The expected generation plan is `8s initial + 7s extension = 15 generated seconds`, normalized to **720×1280 at 24 fps** with native splash and wind audio, and upscaled to `1080×1920` for final output. At the configured `$0.10` per generated second, the estimated Veo cost is **$1.50**, before retries. Starting the workflow makes real Veo calls and consumes credits.

---

# Test inputs: faithful 14-second reproduction of `C:\Users\91858\Downloads\cliff_jumping.mp4`

Unlike the modified variant above (which changed the shorts to crimson, the cliff to granite and removed the bystanders), this input aims to **reproduce the reference as-is**: same POV camera, same turquoise board shorts, same limestone gorge, same companion at the edge, same swimmer below.

**Frame-level analysis of the reference** (~13.87 s, 720×1280, 30 fps, h264 + aac):

- **Camera**: first-person POV from a wide-angle action camera mounted just above the jumper's head and angled steeply downward — his bare tanned torso, turquoise board shorts with a patterned waistband, bare legs and bare feet stay in the lower frame throughout, with the gorge floor far below.
- **Setting**: a deep, narrow limestone gorge with vertical grey stratified rock walls, green shrubs clinging to ledges, a flat stone jump platform at the top, a companion's bare legs standing at the frame's right edge, a thin dark blue-green water channel at the gorge floor with a lone swimmer floating mid-channel, and a soft sun flare at the far end of the canyon.
- **Pacing** (verified at 8 fps sampling): ~0–12.5 s real-time anticipation standing at the rim with small balance shifts; sudden leap at ~12.6 s; the fall is a **fast speed-ramp** — take-off to splash is roughly **half a second** on screen — violent white splash ~13.0 s; murky green underwater frames to 13.87 s. **The reference contains no slow-motion segment** — the fall is accelerated, not dilated (the slow-mo hang-time in the variant above was an artistic change, not part of the reference).

### Clip plan for this input

- Target **14 s** → extension plan `8s initial + 7s extension` = 15 generated seconds, trimmed to 14 → exactly **two beats**.
- Beat 1 (8 s initial): anticipation only — he stays planted on the rim. Do not mention the leap in beat 1 at all.
- Beat 2 (7 s extension): the whole leap → fast plummet → splash → underwater, written with speed language to bias Veo toward the reference's accelerated fall. Includes "pierce the surface with zero deceleration" (the skim/float fix learned from the earlier variant).

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `POV Gorge Cliff Jump — Reference Reproduction` |
| Description | Paste the Faithful Cliff Jump Description block below (scene/camera/style only; action goes in beats) |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Faithful Cliff Jump Fixed subject and setting block below |
| Ordered clip beats | Paste the two Faithful Cliff Jump Ordered clip beats, one per line |
| Avoid | Paste the Faithful Cliff Jump Avoid block below |
| Narration | **Leave blank**; preserve Veo's generated wind/splash/underwater audio |
| Language | **English** (unused with blank narration) |
| Target Duration (sec) | `14` |
| Target Audience | `Viewers of first-person cliff jumping and extreme sports reels` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080×1920) — Shorts/Reels** |
| Tags | `cliff jump, POV, gorge, limestone canyon, cliff diving, action camera` |

## Faithful Cliff Jump Description

```text
A single continuous photorealistic vertical first-person POV shot from a wide-angle action camera mounted just above the jumper's head and angled steeply downward, so his own bare tanned torso, turquoise board shorts with a patterned waistband, legs and bare feet remain visible in the lower frame throughout. Beneath his feet yawns a deep, narrow limestone gorge: vertical grey stratified rock walls, green shrubs clinging to ledges, and a thin channel of dark blue-green water running along the gorge floor far below, with a soft sun flare at the far end of the canyon. Bright midday daylight, realistic wide-angle distortion. Buffeting wind, echoing gorge acoustics, a violent splash then muffled underwater rumble; no spoken narration.
```

## Faithful Cliff Jump Fixed subject and setting

```text
One continuous downward-facing first-person POV from a camera above the jumper's head. The same athletic adult man throughout: shirtless, turquoise board shorts with a patterned waistband, barefoot, his torso and legs anchored in the lower frame. One deep narrow limestone gorge in bright midday daylight with vertical grey stratified rock walls and green shrubs on ledges; a flat stone jump platform at the top; a companion's bare legs standing at the frame's right edge on the same platform; a thin dark blue-green water channel at the gorge floor far below with a lone swimmer floating mid-channel. Keep the camera orientation, the man, his turquoise shorts, the gorge, the platform and the water channel identical across the initial video and its extension.
```

## Faithful Cliff Jump Ordered clip beats

Paste **exactly two lines**. Line 1 controls the initial 8-second Veo video; line 2 controls the 7-second extension that continues the same video.

```text
He stands at the very edge of the stone jump platform looking straight down into the gorge, the downward camera swaying gently with small shifts of his balance; his turquoise shorts and bare feet stay planted at the rim, the companion's bare legs beside him at frame right, the thin dark water channel far below, a swimmer floating mid-channel; he is still standing on the ledge when the clip ends.
He suddenly springs forward off the rim and plummets feet-first, the stratified gorge walls streaking upward past the lens at high speed as the thin water channel rushes up fast; his feet pierce the surface with zero deceleration — no skimming, no floating — in a violent white splash that engulfs the frame, and the camera is instantly swallowed into dark murky green underwater looking up at a fading circle of daylight.
```

## Faithful Cliff Jump Avoid

```text
No third-person view, no drone or follow-cam angle, no camera that leaves his head, no camera cuts or teleport, no helmet straps or selfie stick visible, no pool or open lake beside the platform, no waterfall, no boat, no rope or harness, no outfit change, no shoes appearing on his bare feet, no second jumper diving, no hitting the rock walls, no crash or injury, no skimming or floating on the water surface, no soft splashdown, no slow-motion replay, no sunset or night, no on-screen text, captions, subtitles, watermark, logo, narration or music. The water must stay a narrow channel at the gorge floor far below the ledge, and the man must stay barefoot in turquoise board shorts.
```

### 14-second faithful cliff jump check and cost

On the Review step check **Direct cinematic video**, **14 seconds** and **9:16 Portrait**. Create the project, then click **Start Workflow**. The expected generation plan is `8s initial + 7s extension` = 15 generated seconds trimmed to 14, normalized to **720×1280 at 24 fps**, with the initial segment at **second 8** handing off to the extension as a remote video (`input_video_supplied: true`, `remote_video_retained: true` in `metadata.custom.video_clips`). At the configured `$0.10` per generated second, the estimated Veo cost is **$1.50**, before retries.

**Realism risks specific to this reel:** Veo may drift the fixed downward POV (torso/shorts may vanish), widen the water channel into a pool, pace the fall slower than the reference's sub-second speed-ramp, or skim on the surface before submerging — if the fall floats or the entry lingers, strengthen beat 2's speed language ("hurtles", "slams straight through"). The companion's legs and the distant swimmer are secondary depth cues — drop them from the anchor if they confuse the model.

---

# Test inputs: 15-second POV headland sprint + ocean cliff dive (v2 — optimized prompts)

This is the **optimized rewrite** of project `e6d9ebff-6801-4b5f-8bf5-cb366f683571`, which suffered from:

1. **No continuity** between the 8s initial clip and the 7s extension — Veo re-interpreted the scene.
2. **No real fall** — the athlete landed in the water almost instantly because beat 1 tried to cram sprint + dialogue + jump + freefall into 8 seconds, and beat 2 had no room for a dramatic descent.
3. **Beats were too long** (774 and 816 chars) — Veo ignores portions of prompts over ~500 chars.
4. **Visual anchor was misused** — it contained pacing and audio direction ("build excitement through rapid footsteps...") instead of static character/setting description. The visual anchor is sent verbatim in every clip prompt, so it must describe *what stays the same*, not *what happens*.
5. **Sub-second timestamps** (e.g. "0.0–1.5s:") do not work with Veo — it does not understand frame-precise choreography.

### Changes from v1

| Problem | v1 | v2 fix |
|---|---|---|
| Beat length | 774 / 816 chars | ~320 / ~290 chars |
| Visual anchor | Pacing + audio direction (533 chars) | Static character/setting description (~350 chars) |
| Description | Included "no external camera angles" redundantly with avoid | Clean scene/style spec, ~350 chars |
| Avoid | Long list with redundant entries (493 chars) | Deduplicated, ~350 chars |
| Beat 1 scope | Sprint + dialogue + jump + freefall | Sprint + jump only; end at cliff edge in the air |
| Beat 2 scope | Freefall + voice + splash + underwater | Freefall + splash + underwater only |
| Dialogue in beats | "Here we go!" and "Woo-hoo!" cries | Moved to description (audio direction); beats focus on motion |
| Sub-second timestamps | Present in original user input | Removed entirely |

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `POV Headland Sprint & Ocean Dive — v2` |
| Description | Paste the Headland v2 Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Headland v2 Fixed subject and setting block below |
| Number of clip beats | **2** |
| Beat 1 | Paste Headland v2 Beat 1 below |
| Beat 2 | Paste Headland v2 Beat 2 below |
| Avoid | Paste the Headland v2 Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080×1920) — Shorts/Reels** |

## Headland v2 Description

Scene, camera and audio specification only — action belongs in the beats.

```text
Photorealistic 9:16 vertical extreme-adventure video, 24 FPS, head-mounted action-camera POV on an athletic young woman sprinting along a narrow rugged rocky headland above a vast deep-blue ocean. The camera follows natural head movement; hands and forearms may briefly enter the bottom of frame. Bright natural daylight, realistic motion blur. She shouts excited reactions at takeoff and during the fall. Synchronized natural audio: footsteps on rock, rushing wind, ocean roar, heavy splash, muffled underwater. No music, no narration, no text.
```

## Headland v2 Fixed subject and setting

```text
Same athletic young woman throughout: running gear, ponytail, visible hands and forearms only. Same narrow rocky headland jutting over a vast deep-blue ocean with steep coastal cliffs, bright daylight and scattered clouds. Same head-mounted first-person POV camera — never switch to a third-person, drone or external angle. Keep the character, headland, ocean, coastline, lighting and camera perspective identical across the initial clip and its extension.
```

## Headland v2 Beat 1

Paste into the **Beat 1** textarea (initial 8-second clip).

```text
First-person head-camera: sprint hard along the narrow rocky headland toward the cliff tip, camera bouncing with each stride, footsteps crunching on rock. Reach the exposed edge, plant one final powerful step and leap forward off the cliff into open air above the deep-blue ocean. End in the first moment of freefall with the ocean still far below. Do not enter the water.
```

## Headland v2 Beat 2

Paste into the **Beat 2** textarea (7-second extension).

```text
Continue from the same freefall. Plummet toward the deep-blue ocean — water expands rapidly in view, cliff walls rush past, wind roars. Plunge feet-first into the sea with a heavy forceful splash. Camera passes underwater into turbulent white bubbles with shimmering blue light above. Finish fully submerged with bubbles gradually clearing and muffled underwater sounds.
```

## Headland v2 Avoid

```text
No third-person view, no drone shot, no external camera, no visible face or full body, no camera cut or teleport, no backward movement, no hovering or floating in mid-air, no premature water entry, no missed water entry, no ending mid-air, no skimming on the surface, no slow-motion, no second person, no outfit change, no music, no text, no logo, no subtitles. Keep coastline and ocean consistent across both clips.
```

### Prompt budget check

| Field | v1 chars | v2 chars |
|---|---|---|
| Description | 440 | ~480 |
| Visual anchor | 533 | ~350 |
| Avoid | 493 | ~350 |
| Longest beat | 816 (beat 2) | ~320 (beat 1) |
| **Max clip prompt** | **2459** | **~1500** |

The v2 prompts are roughly **40% shorter**, well within Veo's effective comprehension range.

### 15-second headland v2 check and cost

On the Review step check **Direct cinematic video**, **15 seconds** and **9:16 Portrait**. Create the project, then click **Start Workflow**. Generation plan: `8s initial + 7s extension`, normalized to **720×1280 at 24 fps**, trimmed to 15 seconds. Estimated Veo cost: **$1.50** at `$0.10/s`. Do not start the workflow without intending a paid Veo generation.

**Key prompt principles applied:**
- Beats under 350 chars — Veo follows short, direct action instructions far more reliably than long multi-paragraph descriptions.
- Visual anchor describes only *static* identity (character, location, camera style) — never pacing or action.
- No sub-second timestamps — describe progression, not timecodes.
- Each beat directs exactly one phase of action (sprint+jump OR fall+splash), not the entire sequence.
- Audio cues stay in the description, not repeated in every beat.

---

# Extension prompt restructure (applied to all video durations)

## Problem diagnosed from projects `e6d9ebff` (v1) and `84a92505` (v2)

Both projects showed a **continuity break at the 8-second boundary**: the athlete was high above the ocean at second 8, then suddenly near the water at second 9. The video followed instructions correctly within each clip, but the extension did not continue smoothly from where the initial clip left off.

### Root cause: extension prompts drowned the action beat

Veo extension works by extracting the **last 1 second (24 frames)** of the input video as visual context. The model already *sees* the character, setting, camera, lighting, and current motion state from those frames.

Our extension prompt was **1517 chars** — 27× longer than Google's own example extension prompt (56 chars: *"Extend this video with the paraglider slowly descending"*). The breakdown:

| Section | Chars | % of prompt | Needed? |
|---|---|---|---|
| Visual anchor (repeated) | 347 | 23% | No — Veo sees this in the video |
| Avoid list (repeated) | 381 | 25% | No — Veo maintains the video's style |
| Wrapper/framing text | 499 | 33% | Mostly no |
| **Action beat** (the point) | **290** | **19%** | **Yes** |

The actual action instruction was only 19% of the prompt. The repeated context **competed** with the visual signal from the last 24 frames, causing Veo to re-interpret the scene state and jump the action forward.

### Fix applied in `backend/src/application/services/direct_cinematic.py`

The `direct_clip_prompt()` function now generates two very different prompt structures:

**Initial clip (clip 0)** — unchanged, full specification:
```
Fixed production specification: {description}.
Same subject and location throughout: {visual_anchor}.
Avoid: {avoid}.
This is the initial segment; show ONLY this action beat: {beat}.
Establish the subject and camera position.
```

**Extension clips (clip 1+)** — short and action-focused:
```
Continue smoothly from the last frame of this video.
Same subject, camera and world — do not restart or cut.
{beat}
```

### Result

| Metric | Before | After |
|---|---|---|
| Extension prompt (15s, 2 beats) | 1517 chars | 478 chars |
| Extension prompt (30s, 5 beats) | ~1500 chars each | ~160 chars each |
| Action beat % of extension prompt | 19% | 61–80% |
| Beat 1 (initial, unchanged) | 1915 chars | 1915 chars |

### Applies to all durations

Every extension for any duration (15s, 30s, 45s, up to 148s) goes through the same `direct_clip_prompt()`. The fix improves continuity across all of them — and is especially important for longer videos with 4+ extensions, where prompt drift previously accumulated with every hop.

### Beat writing tips for best continuity

1. **End beat 1 on a clean handoff** — describe where the action should be at the END of the 8-second initial clip, not just what happens during it. "End in the first moment of freefall with the ocean still far below" is good.
2. **Start extension beats with what the viewer sees** — "Continue from the same freefall" or "Plummet toward the ocean" tells Veo what the current state is.
3. **Don't repeat the visual anchor in beats** — the anchor is in the initial prompt and in the video itself.
4. **Keep beats under 400 chars** — shorter beats get followed more reliably by Veo extension.

---

# Test inputs: 15-second sinkhole swan dive (reference reproduction)

Reference video: `C:\Users\91858\Downloads\AQOmOcIWzLoWVNmH0aF0d2BbpskToqRKeYSF0EbJG8TBoBHSEkz3y5iMNgUdGGwOneV1NZvk9O9yTBQvKEByD1IgP-KgSwRjqire-66xiHHO5Q.mp4`

### Reference video analysis

| Property | Value |
|---|---|
| Duration | 15 seconds |
| Resolution | 720x1280 (9:16 portrait) |
| Frame rate | 24 fps |
| Audio | AAC stereo, ambient crowd/wind/splash sounds |

### Scene breakdown (from frame-by-frame analysis)

| Time | What's on screen |
|---|---|
| 0–3s | **Hook/anticipation**: Close-up from behind a muscular shirtless man in red swim shorts standing at the rim of a massive natural limestone sinkhole. A crowd of ~15 shirtless spectators in mixed-color swim trunks stands on the far rim watching. The sinkhole is a deep vertical cylinder carved into layered/stratified grey rock, with a small dark blue-green water pool glinting far below. Bright midday sun, arid coastal plateau, clear sky. The man looks down, shifts his weight, builds tension. |
| 3–4s | **Launch**: He takes a final step and launches into a dramatic swan dive — arms spread wide, body arched, falling forward into the shaft. Camera begins pulling back to reveal the full circular opening. |
| 4–8s | **Freefall**: Camera tracks from a third-person drone angle looking straight down into the cylindrical rock shaft. The diver falls with arms spread, getting progressively smaller against the layered walls. Spectators visible at the rim above. The dark water pool sparkles below but is still far away. The scale of the sinkhole is dramatic — he shrinks to a small figure. |
| 8–10s | **Impact**: He hits the water with a massive white splash that erupts upward. Camera holds the overhead angle looking straight down through the shaft. The splash dominates the pool surface. |
| 10–13s | **Aftermath**: Big concentric ripples and white foam spread outward across the dark pool. The splash energy slowly dissipates. Viewed from directly above through the rock cylinder. |
| 13–15s | **Resolution**: Water settles into gentle concentric ripple patterns and foam. A small swimmer visible in the pool. Overhead view holds steady — the deep circular geological formation frames the entire shot. |

### Why this video hooks viewers

1. **Instant visual hook** — the sinkhole is an alien-looking geological formation; the viewer has never seen anything like it
2. **Anticipation** — 3 full seconds of the man standing at the edge, tension building
3. **Scale reveal** — when the camera pulls to the overhead angle, the terrifying depth becomes apparent
4. **Satisfying payoff** — the splash and settling ripples provide closure
5. **One continuous shot** — no cuts, just smooth drone-tracking motion

### Camera behavior (important — NOT first-person)

Unlike the previous headland tests which were POV, this video uses a **third-person drone-tracking shot**:
- Starts behind/above the diver at the rim
- Smoothly transitions to a direct overhead angle during the fall
- Holds the overhead looking-straight-down angle for the splash and aftermath
- Never cuts or changes perspective

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Sinkhole Swan Dive` |
| Description | Paste the Sinkhole Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Sinkhole Fixed subject and setting block below |
| Number of clip beats | **2** |
| Beat 1 | Paste Sinkhole Beat 1 below |
| Beat 2 | Paste Sinkhole Beat 2 below |
| Avoid | Paste the Sinkhole Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Sinkhole Description

```text
Photorealistic 9:16 vertical extreme-sport video, 24 fps. Third-person drone-tracking shot above and behind a muscular shirtless man in red swim shorts standing at the rim of a massive natural limestone sinkhole on a sun-baked coastal plateau. The sinkhole is a deep vertical cylinder with layered stratified rock walls dropping 25 meters to a small dark blue-green water pool far below. About fifteen shirtless male spectators in colorful swim trunks stand around the far rim watching. Bright midday sunlight, clear sky, scattered white clouds. Camera smoothly tracks the diver then tilts to an overhead looking-straight-down angle during the fall. Natural ambient audio only: crowd murmurs, wind gusts, rushing air during the fall, heavy water impact, and settling ripples. No music, no narration, no text overlays.
```

## Sinkhole Fixed subject and setting

```text
Same muscular shirtless man in red swim shorts throughout. Same deep cylindrical limestone sinkhole with layered grey rock walls, dark blue-green water pool at the bottom, boulders around the pool edge. Same crowd of shirtless spectators on the far rim. Same bright midday lighting and clear sky. Keep the sinkhole geometry, the man, the crowd, and the overhead camera perspective consistent across the initial clip and its extension.
```

## Sinkhole Beat 1

Paste into the **Beat 1** textarea (initial 8-second clip).

```text
The man stands at the sinkhole rim looking down, body tense with anticipation. Spectators watch from the opposite rim. He takes a breath, then launches into a dramatic swan dive with arms spread wide. Camera tracks him as he falls through the cylindrical rock shaft, getting smaller against the layered walls. The water pool is still far below. End with him mid-fall, arms spread, about halfway down the shaft.
```

**Why this beat works for continuity**: Beat 1 ends with the diver clearly mid-fall, still high above the water. This gives the extension a clean visual state to continue from — the last 24 frames show a falling figure with plenty of distance to the water, so the extension naturally continues the descent rather than jumping to the splash.

## Sinkhole Beat 2

Paste into the **Beat 2** textarea (7-second extension).

```text
He plummets the remaining distance and slams into the dark water pool with a massive white splash that erupts upward. Camera holds the overhead angle looking straight down through the sinkhole. Concentric ripples and foam spread across the pool surface. The splash settles into gentle waves. Hold on the aftermath from above.
```

## Sinkhole Avoid

```text
No first-person POV, no camera cuts, no teleportation, no slow-motion, no hovering, no outfit change, no disappearing crowd, no changing sinkhole shape, no extra divers, no music, no text, no logos. Do not show the diver entering the water in the first clip.
```

### Prompt budget

| Field | Chars |
|---|---|
| Description | 790 |
| Visual anchor | 413 |
| Avoid | 264 |
| Beat 1 | 399 |
| Beat 2 | 322 |
| **Initial clip prompt** | **2103** |
| **Extension prompt** | **434** |
| Max / limit | **2103 / 3500** |

### 15-second sinkhole check and cost

Generation plan: `8s initial + 7s extension`, normalized to **720x1280 at 24 fps**, trimmed to 15 seconds. Estimated Veo cost: **$1.50** at `$0.10/s`. Do not start the workflow without intending a paid Veo generation.

**Rate limit reminder**: Tier 1 allows 2 RPM for Veo. A 15-second project makes exactly 2 Veo calls (1 initial + 1 extension). Space runs at least 60 seconds apart to avoid 429 errors. Do not run multiple projects back-to-back.

---

# Test inputs: 15-second volcanic cliff backflip into monster wave (v3)

Reference video: `C:\Users\91858\Downloads\sea_jump.mp4` (10 seconds — generation is 15s because Veo's minimum for 2 beats is 8+7s; the extra 5s is calm aftermath)

### Reference video analysis

| Property | Value |
|---|---|
| Duration | 10 seconds |
| Resolution | 720x1280 (9:16 portrait) |
| Frame rate | 24 fps |
| Audio | AAC stereo, ambient ocean/wind/splash sounds |

### Scene breakdown (from frame-by-frame analysis)

| Time | What's on screen |
|---|---|
| 0–2s | **Hook/anticipation**: Athletic shirtless man in black swim shorts standing barefoot on a dark volcanic lava rock cliff edge. Massive turquoise-blue ocean waves crashing below. Bright midday sun, vivid blue sky, Hawaiian-style coastline. He watches the waves, tension building. |
| 2–3s | He crouches low, timing an incoming wave, body coiled and ready to launch. A huge turquoise wave begins to build and crest in front of him. |
| 3–4s | He spreads his arms wide and launches off the cliff edge toward the face of the enormous cresting wave. |
| 4–5s | Mid-air backflip — body inverted, tucked into a rotation, falling toward the curling turquoise barrel wave. |
| 5–6s | Still rotating, descending into the base of the massive wave. The turquoise barrel curls behind him — a transparent wall of water with white spray. Volcanic rocks visible at the bottom of frame. |
| 6–7s | The massive wave crashes around him — turquoise barrel collapses into an explosion of white water. He disappears into the foam. |
| 7–8s | Total whiteout — wave explodes with spray and mist engulfing the frame. Volcanic rocks barely visible through the chaos. |
| 8–9s | Wave recedes. He surfaces in the churning turquoise water with **both arms raised in triumph**. White foam surrounds him. |
| 9–10s | Floating in the turquoise ocean, celebrating, wave pulling back. |

### Why this video hooks viewers

1. **Instant danger** — man standing on volcanic rocks above monster waves = immediate "is he insane?!" reaction
2. **Wave timing** — he jumps precisely as a huge wave crests, maximizing the visual drama
3. **Backflip** — acrobatic stakes on top of an already dangerous cliff jump
4. **The engulfing crash** — terrifying moment where he disappears inside the wave
5. **Triumphant surface** — arms raised = satisfying "he survived!" payoff
6. **Stunning color contrast** — turquoise ocean, black volcanic rock, blue sky

### Camera behavior

Close third-person handheld camera right behind the jumper at the cliff edge — at the same height, looking over his shoulder and down. The viewer feels the height and the drop. NOT a drone, NOT a distant landscape shot, NOT first-person. The cameraman is standing right behind him on the cliff top.

### v1 issues (project `fc2dc45f`, 15s)

The first generation had three problems:
1. **Camera too far away** — Veo placed the camera low among the rocks at the waterline, making the man tiny and removing all sense of height
2. **Backflip too slow/floaty** — looked like slow-motion, unrealistic hang time
3. **Cliff too low** — no visible drop, no vertigo, no thrill

### v2 → v3 restructure (action timed to beat boundary)

v2 split the action at the extension boundary mid-fall — the same risky handoff that caused continuity breaks before. v3 keeps 15s total (Veo's minimum for 2 beats is 8+7 anyway — the 10s option wasted paid footage) but **moves the entire thrilling action into beat 1**: anticipation → jump → backflip → fall → water entry → wave crash, all inside the 8-second initial clip. The diver is already underwater at the 8s boundary — the last frame is a wall of white foam. Beat 2 is only aftermath: surface, triumph, floating. The extension boundary falls on a static foam frame, eliminating mid-air continuity risk.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Backflip Into a Monster Wave` |
| Description | Paste the Wave Backflip v3 Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Wave Backflip v3 Fixed subject and setting block below |
| Number of clip beats | **2** |
| Beat 1 | Paste Wave Backflip v3 Beat 1 below |
| Beat 2 | Paste Wave Backflip v3 Beat 2 below |
| Avoid | Paste the Wave Backflip v3 Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Wave Backflip v3 Description

```text
Photorealistic 9:16 vertical extreme-sport video, 24 fps, real-time speed — NOT slow motion. Close third-person handheld camera right behind a muscular shirtless man in black swim shorts standing barefoot at the edge of a TALL volcanic lava rock cliff, at least 10 meters above the ocean. Camera is at the same height as the jumper, looking over his shoulder and down at the turquoise water far below — the viewer feels the terrifying drop. Massive powerful waves crash against the cliff base. Bright midday sun, blue sky, Hawaiian volcanic coastline. Everything moves at normal real-world speed with realistic gravity. Natural audio: ocean roar, wind, splash. No music, no narration, no text.
```

## Wave Backflip v3 Fixed subject and setting

```text
Same muscular shirtless man in black swim shorts throughout. Same tall dark volcanic lava rock cliff high above the turquoise ocean. Same massive cresting waves hitting the cliff base far below. Same close handheld camera behind the jumper at cliff-edge height. Same bright midday tropical light. Keep the cliff height, wave scale, man, and camera perspective identical across both clips.
```

## Wave Backflip v3 Beat 1

Paste into the **Beat 1** textarea (initial 8-second clip).

```text
The man stands at the tall cliff edge, camera close behind him, ocean far below with huge turquoise waves. He crouches, explodes off the edge into a fast backflip — rapid rotation, real gravity, no floating. He drops fast and slams into the churning water. The enormous wave crashes over him in a wall of white spray and foam filling the frame.
```

**Why this beat works**: The entire action — anticipation, jump, backflip, fall, water entry, wave crash — happens in the initial 8-second clip with no extension boundary splitting the action. By the end of beat 1, the wave has already crashed and the screen is white water/foam, which is a perfect static handoff frame for the extension (no mid-air continuity needed). The backflip uses "fast", "rapid rotation", "no floating" and the avoid list reinforces "no slow motion" to keep real-time speed.

## Wave Backflip v3 Beat 2

Paste into the **Beat 2** textarea (7-second extension — all kept).

```text
The white water clears and he surfaces, wiping water from his face. He raises both arms high in triumph, shouting in celebration. He floats on his back in the turquoise ocean, catching his breath, as waves roll past and the foam settles around him.
```

**Why this fills 7 seconds**: Beat 2 is pure aftermath — foam clearing, surfacing, arms raised, then a calm settle into floating. All low-motion content that Veo can sustain for the full extension without inventing new action.

## Wave Backflip v3 Avoid

```text
No slow motion, no floaty movement, no hovering, no low cliff, no calm ocean, no distant camera, no drone shot, no first-person POV, no camera cuts, no outfit change, no music, no text, no logos. The backflip must obey real gravity — fast rotation, fast fall, no floating in mid-air.
```

### Prompt budget

| Field | Chars |
|---|---|
| Description | 693 |
| Visual anchor | 387 |
| Avoid | 282 |
| Beat 1 | 344 |
| Beat 2 | 248 |
| **Initial clip prompt** | **1892** |
| **Extension prompt** | **357** |
| Max / limit | **1892 / 3500** |

### What changed across versions

| Issue | v1 | v2 | v3 (current) |
|---|---|---|---|
| Duration | 15s | 15s | 15s (all kept — no wasted footage) |
| Camera | Distant, low | Close, cliff-height | Close, cliff-height |
| Cliff height | Not specified | 10+ meters | 10+ meters |
| Speed | Not addressed | Real-time, no slow-mo | Real-time, no slow-mo |
| Backflip | "dramatic" | "fast, rapid rotation" | "fast, rapid rotation" |
| Beat 1 scope | Anticipation + jump only | Anticipation + jump + mid-fall | **Full action: anticipation + jump + fall + splash + wave crash** |
| Beat 2 scope | Fall + splash + surface | Splash + surface | **Surface + triumph + floating aftermath** |
| Extension boundary | Mid-fall (risky) | Mid-fall (risky) | **After wave crash (safe — static foam)** |

### 15-second wave backflip v3 check and cost

Generation plan: `8s initial + 7s extension`, full 15 seconds kept. Output: **720x1280 at 24 fps**. Estimated Veo cost: **$1.50** at `$0.10/s`.

**Pacing note**: All the action happens in the first ~9 seconds (jump ~4s, splash ~7s, wave crash ~8s). Seconds 9–15 are calm aftermath — surfacing, triumph, floating. The reference was 10s; the extra 5s here is gentle wind-down, which gives viewers a moment to absorb the shot before looping.

**Rate limit reminder**: Tier 1 allows 2 RPM for Veo. A 15-second project makes 2 Veo calls (1 initial + 1 extension). Space runs at least 60 seconds apart to avoid 429 errors.


---

# Test inputs: 15-second storm fjord death dive (100m+, rain, underwater payoff)

Reference video: `C:\Users\91858\Downloads\sky_to_jump.mp4` (real footage: Norwegian fjord death-dive, 500K+ views / 10K+ likes on Facebook)

### Reference video analysis

| Property | Value |
|---|---|
| Duration | 15 seconds |
| Resolution | 720x1280 (9:16 portrait) |
| Frame rate | 24 fps |
| Audio | AAC stereo, ambient wind/water sounds |

### Scene breakdown (from frame-by-frame analysis)

| Time | What's on screen |
|---|---|
| 0–2s | **Hook**: Shirtless man on a rocky alpine ledge, snowy mountains behind. A blonde woman in the foreground covers her mouth nervously — a human reaction face as instant emotional hook. |
| 2–4s | He **sprints** toward the cliff edge; camera runs right behind him at his speed. |
| 4–5s | Launches into a swan dive over a vast dark-blue fjord. |
| 5–9s | **Camera leans over the edge and tilts straight down, tracking him** — he shrinks to a tiny figure against the enormous fjord and 600m snowy mountain wall across the water. The fall is sustained ~4+ seconds. |
| 9s | A **tiny** white splash in the vast dark water — the smallness of the splash sells the extreme height. |
| 10–13s | Underwater view: a massive bubble column descends through the deep blue. |
| 13–15s | He rises through the bubbles toward the light — survival reveal = second payoff. |

### Lessons applied from the 150K-view sinkhole and 500-view backflip comparison

1. **Payoff lands at ~65–90% of runtime** — splash at ~10s, underwater reveal 10–15s. Nothing resolves early.
2. **Scale dwarfs the human** — the tiny splash is more terrifying than a frame-filling one.
3. **Every frame shows progress** — the diver visibly shrinks each second; no dead frames, no whiteout.
4. **Reaction faces in frame 0** — the nervous woman pre-sells danger before the action starts.
5. **Camera motion at real speed** — follows him at running pace, tilts over the edge tracking the fall. Movement sells "you are there."
6. **Harsh environment = extra stakes** — heavy rain + storm clouds + icy water instead of sunny tropical coast.

### Extension boundary safety

The 8s boundary lands with the diver **mid-fall as a tiny distant speck** — normally risky, but proven safe by the sinkhole video: small distant figures hide continuity errors that would be glaring on a close-up body.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Storm Fjord Death Dive` |
| Description | Paste the Fjord Dive Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Fjord Dive Fixed subject and setting block below |
| Number of clip beats | **2** |
| Beat 1 | Paste Fjord Dive Beat 1 below |
| Beat 2 | Paste Fjord Dive Beat 2 below |
| Avoid | Paste the Fjord Dive Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Fjord Dive Description

```text
Photorealistic 9:16 vertical extreme-sport video, 24 fps, real-time speed — NOT slow motion. Third-person camera on a remote rocky ledge at least 100 meters above a vast dark deep-blue fjord, surrounded by towering snow-covered mountain walls. Heavy rainfall and dramatic dark storm clouds, grey moody overcast light, rain streaks visible in frame. A muscular shirtless man in dark swim shorts stands barefoot at the ledge; a few spectators including a woman covering her mouth with both hands watch nervously behind him. Camera follows him at running speed as he sprints to the edge, then leans out over the cliff and tilts straight down, tracking his fall — he shrinks to a tiny figure against the enormous dark water far below. Real-world gravity and speed throughout. Audio: cold wind, heavy rain, distant thunder rumble, faint distant splash, muffled underwater rumble. No music, no narration, no text.
```

## Fjord Dive Fixed subject and setting

```text
Same muscular shirtless man in dark swim shorts throughout. Same sheer rocky ledge at least 100 meters above the vast dark deep-blue fjord, snow-covered mountain walls towering across the water. Same heavy rainfall, dark storm clouds, and grey overcast light. Same group of nervous spectators at the ledge. Keep the extreme height, the tiny scale of the diver against the fjord, the stormy weather, and the tracking camera consistent across both clips.
```

## Fjord Dive Beat 1

Paste into the **Beat 1** textarea (initial 8-second clip).

```text
Heavy rain falls as the man stands at the ledge, the woman behind him covering her mouth. He sprints toward the edge and launches into a long swan dive, arms spread. The camera leans over the edge and tilts straight down tracking his fall — he quickly shrinks to a small figure far above the dark fjord, rain streaking through the frame. End with him still falling, a distant speck high above the water.
```

## Fjord Dive Beat 2

Paste into the **Beat 2** textarea (7-second extension).

```text
He keeps falling, now a tiny speck against the huge dark fjord, until he strikes the surface — a small white splash in the vast water. Underwater: a huge column of bubbles churns down through the deep blue. He rises slowly through the bubbles toward the grey daylight above.
```

## Fjord Dive Avoid

```text
No slow motion, no floating, no sunny sky, no clear weather, no calm daylight, no low cliff, no camera cuts, no drone shot, no first-person POV, no outfit change, no disappearing spectators, no music, no text, no logos. The fall must obey real gravity — accelerating fast downward, no hovering.
```

### Prompt budget

| Field | Chars |
|---|---|
| Description | 952 |
| Visual anchor | 448 |
| Avoid | 276 |
| Beat 1 | 403 |
| Beat 2 | 274 |
| **Initial clip prompt** | **2240** |
| **Extension prompt** | **383** |
| Max / limit | **2240 / 3500** |

### Resulting timeline

| Time | Content |
|---|---|
| 0–3s | Rain, ledge, nervous woman, sprint + launch |
| 3–8s | Camera tilts down tracking him — he shrinks fast, still high |
| 8–10s | Falling as a distant speck → tiny splash (~10s) |
| 10–15s | Underwater bubble column → he rises toward the light |

### 15-second fjord dive check and cost

Generation plan: `8s initial + 7s extension`, full 15 seconds kept. Output: **720x1280 at 24 fps**. Estimated Veo cost: **$1.50** at `$0.10/s`.

**Rate limit reminder**: Tier 1 allows 2 RPM for Veo. Space runs at least 60 seconds apart to avoid 429 errors.

---

# Test inputs: 15-second storm fjord death dive — KLING single-shot version

Same reference (`sky_to_jump.mp4`), adapted for **Kling v3 via fal.ai**: one 15-second `text-to-video` call, one beat covering the entire arc — no extension boundary at all. Key Kling adaptations vs the Veo version: camera trimmed to ONE move (Kling docs warn multi-instruction cameras get unstable), audio written as `[source] + action`, no "across both clips" continuity language.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Storm Fjord Death Dive` |
| Description | Paste the Kling Fjord Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Kling Fjord Fixed subject and setting block below |
| Number of clip beats | **1** |
| Beat 1 — Scene | Paste Kling Beat 1 **Scene** below |
| Beat 1 — Camera | Paste Kling Beat 1 **Camera** below |
| Beat 1 — Action | Paste Kling Beat 1 **Action** below |
| Beat 1 — Ending | Paste Kling Beat 1 **Ending** below |
| Beat 1 — Visual style | Paste Kling Beat 1 **Visual style** below |
| Beat 1 — Audio | Paste Kling Beat 1 **Audio** below |
| Beat 1 — Continuity | Paste Kling Beat 1 **Continuity** below |
| Beat 1 — Avoid in this clip | Paste Kling Beat 1 **Avoid in this clip** below |
| Avoid | Paste the Kling Fjord Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Kling Fjord Description

```text
Photorealistic 9:16 vertical extreme-sport video, real-time speed — NOT slow motion. Single continuous shot. A shirtless man cliff-dives into a vast dark fjord in heavy rain; a close chase camera dives with him and tracks his fall all the way underwater. No music, no narration, no text.
```

## Kling Fjord Fixed subject and setting

```text
Same muscular shirtless man in dark swim shorts for the whole shot. Same rocky ledge 150–200 metres above the vast dark deep-blue fjord, snow-covered mountain walls towering across the water. Same heavy rainfall, dark storm clouds and grey overcast light. Same nervous spectators at the ledge. Keep the extreme height, the tiny scale of the diver against the fjord, the stormy weather and the downward tracking camera identical throughout.
```

## Kling Beat 1 — Scene

```text
A remote rocky ledge roughly 150–200 metres above a vast, dark deep-blue fjord, surrounded by towering snow-covered mountain walls. Heavy rainfall, dark storm clouds, grey overcast light. A muscular shirtless man in dark swim shorts stands at the ledge edge; three nervous spectators in raincoats behind him, one woman covering her mouth.
```

## Kling Beat 1 — Camera

```text
Close third-person chase camera about 1.5–2 metres behind the diver and slightly above his shoulders — the camera sprints with him to the edge, then tilts down and tracks his fall in one continuous downward move, keeping his back and body centred in frame.
```

## Kling Beat 1 — Action

```text
He stands at the ledge for a beat as rain pelts down and the spectators urge him on. He takes two quick running steps and launches into a powerful forward dive — arms extended, torso aligned with his motion, legs trailing behind. The camera dives after him and both plummet toward the fjord, mountains and dark water rushing upward through the background with a strong sense of speed and vertigo. Around the 8–9 second mark he strikes the surface in a violent white splash and the camera follows underwater into a churning column of bubbles. Real-world gravity throughout — the fall is fast, never floaty.
```

## Kling Beat 1 — Ending

```text
Underwater looking up: the diver rises slowly through the bubble column toward the shimmering grey surface and daylight above. End on him ascending through the last metres of deep-blue water.
```

## Kling Beat 1 — Visual style

```text
Photorealistic live-action extreme-sports footage. Natural motion blur, realistic perspective and environmental scale, real-time speed — no slow motion. Immersive chase-camera cinematography.
```

## Kling Beat 1 — Audio

```text
[Wind] roaring past the camera and [rain] heavy impact sounds with a distant thunder rumble during the fall — then a violent [splash] and muffled [underwater] rumble for the final seconds. No music, no narration, no text.
```

## Kling Beat 1 — Continuity

```text
The same diver, outfit, body proportions, cliff, fjord, mountains, spectators and stormy weather for the entire shot.
```

## Kling Beat 1 — Avoid in this clip

```text
Camera cuts, camera teleportation, drone shots, front-facing or side views of the diver, distant shots where he disappears, uncontrolled somersaults, backward rotation, floating, hovering, slow motion, sudden zooms, changes in clothing.
```

## Kling Fjord Avoid

```text
No slow motion, no floating, no sunny sky, no clear weather, no low cliff, no camera cuts, no drone shot, no first-person POV, no outfit change, no disappearing spectators, no music, no text, no logos. The fall must obey real gravity — accelerating downward, no hovering.
```

### Prompt budget (Kling single-shot)

| Field | Chars |
|---|---|
| Description | 287 |
| Visual anchor | 439 |
| Avoid | 271 |
| Beat 1 (composed, 8 sections) | 2240 |
| **Initial clip prompt (composed)** | **3421 / 3500** |

> Description is deliberately a short production spec — the Scene section carries the environment detail. A longer description pushed the composed prompt over 3500.

### Resulting timeline (single 15s clip)

| Time | Content |
|---|---|
| 0–2s | Hook: rain, ledge, spectators, the woman covering her mouth |
| 2–3s | Two running steps → forward dive |
| 3–8s | Camera tracks the fall — diver shrinks against the vast fjord |
| ~8–9s | Splash — camera follows underwater |
| 9–15s | Bubble column → he rises toward the grey daylight |

### Cost

Kling v3 standard, audio on: `15s × $0.126 = $1.89` per generation. Pro tier: `15s × $0.168 = $2.52`.

**Note**: our pipeline still injects the Avoid text inside the composed prompt. Optionally also mirror it into Kling's native `negative_prompt` field once the provider wires that through.

---

# Test inputs: 15-second narrow-shaft death dive (structured Beat 1 fields)

Reference video: `C:\Users\91858\Downloads\small_hole_jump.mp4` (15.9s, 720x1280, 30fps — man in red shorts sprints through a narrow sandstone canyon gap, dives headfirst into a tight circular shaft, falls ~7s to a glowing blue pool, splash at ~10s)

### User-requested modifications vs reference

1. **Half the sinkhole diameter** — shaft described as "barely 3 metres across, tighter than a man standing with arms spread" — claustrophobic, walls rush past close.
2. **Splash moved from ~10s to ~12–13s** — deeper shaft (hundreds of metres), pool stays a tiny dot for most of the fall. Splash lands at ~80% of runtime — maximum retention to the end.
3. **No sprint — diver starts poised at the rim** — he stands ready to dive from second 1 with ~a dozen cheering spectators around the rim (replaces the run-up; crowd = social proof hook).

### Why the structure works

- Extension boundary at 8s lands **mid-fall on a small figure** inside the shaft — the most forgiving handoff (tiny distant subject hides continuity errors, same as the sinkhole video).
- Splash timing is controlled by describing the pool as "still a small dot" at the end of beat 1 — Veo keeps falling through beat 2 before impact.
- Camera = "spectator standing right behind him" who leans over the rim — no running needed since he starts at the edge.
- Red shorts = distinctive color pop against pale sandstone; the crowd + rim ring silhouetted from below is the money shot.

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Narrow Well Death Dive` |
| Description | Paste the Narrow Well Description block below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Narrow Well Fixed subject and setting block below |
| Number of clip beats | **2** |
| Beat 1 → Scene | Paste Scene below |
| Beat 1 → Camera | Paste Camera below |
| Beat 1 → Action | Paste Action below |
| Beat 1 → Ending | Paste Ending below |
| Beat 1 → Visual style | Paste Visual style below |
| Beat 1 → Audio | Paste Audio below |
| Beat 1 → Continuity | Paste Continuity below |
| Beat 1 → Avoid in this clip | Paste per-clip Avoid below |
| Beat 2 | Paste Narrow Well Beat 2 below |
| Avoid | Paste the Narrow Well Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Narrow Well Description

```text
Photorealistic 9:16 vertical extreme-sport video, 30 fps, real-time speed — NOT slow motion. Third-person chase camera behind a muscular shirtless man in red swim shorts at a narrow desert canyon sinkhole in harsh midday sun. Natural audio: crowd cheers, wind, shaft echo, underwater rumble. No music, no narration, no text.
```

## Narrow Well Fixed subject and setting

```text
Same muscular shirtless man in bright red swim shorts throughout. Same tight ~3 metre sandstone shaft with glowing blue-green pool at the bottom. Same crowd of about a dozen spectators at the rim. Same midday desert light and chase camera behind him.
```

## Narrow Well Beat 1 — structured sections

### Scene

```text
A narrow desert sandstone canyon under harsh midday sun. A tight circular vertical shaft — barely 3 metres across — is cut into the canyon floor and plunges hundreds of metres into darkness, ending in a tiny glowing blue-green water pool impossibly far below. A muscular shirtless man in bright red swim shorts stands barefoot at the very rim, ready to dive. About a dozen cheering spectators crowd around the rim behind him.
```

### Camera

```text
Close third-person camera about 1.5-2 metres behind the man and slightly above shoulder level — positioned like a spectator standing right behind him. As he dives into the shaft the camera leans over the rim and tilts straight down, tracking his fall — he stays centered in frame. Never in front of him, never a side view, never a drone shot, never lose sight of him.
```

### Action

```text
The crowd cheers and shouts as the man stands poised at the rim, looking down into the dark shaft. He takes a breath, spreads his arms and dives headfirst into the tight hole. The camera tilts straight down over the rim and follows him — his red shorts a bright speck against the pale rock walls rushing upward. The glowing blue pool far below is still a tiny dot.
```

### Ending

```text
He is still falling deep inside the narrow shaft — the bright ring of the rim with silhouetted spectators far above, the blue pool still a small dot below. Fall in progress.
```

### Visual style

```text
Photorealistic live-action extreme-sports footage. Natural motion blur, real-time speed, no slow motion.
```

### Audio

```text
Crowd cheers at the rim, then wind rushing past and air roaring inside the tight shaft as he falls. No music, no narration, no text.
```

### Continuity

```text
Same man, same red shorts, same narrow shaft, same cheering crowd at the rim, same glowing blue pool throughout.
```

### Avoid in this clip

```text
Camera cuts, camera teleportation, drone views, the shaft appearing wider, floating or hovering, slow motion, front-facing views of the man, crowd members jumping in.
```

## Narrow Well Beat 2

```text
He keeps falling down the tight shaft — the glowing blue pool grows steadily larger below him until he strikes the surface and the camera plunges into churning bubbles. Ripples spread across the dark pool inside the shaft as he rises toward the distant ring of daylight above.
```

## Narrow Well Avoid

```text
No slow motion, no floaty falling, no hovering, no camera cuts, no drone shot, no first-person POV, no enlarging the hole, no extra divers, no music, no text, no logos. Real gravity — fast and accelerating fall.
```

### Prompt budget

| Field | Chars |
|---|---|
| Description | 311 |
| Visual anchor | 290 |
| Avoid | 196 |
| Beat 1 (composed sections) | 1928 |
| Beat 2 | 276 |
| **Initial clip prompt** | **2897** |
| **Extension prompt** | **385** |
| Max / limit | **2897 / 3500** |

### Resulting timeline

| Time | Content |
|---|---|
| 0–1s | Crowd of ~12 cheering around the rim, diver poised at the edge |
| 1–3s | He spreads his arms and dives headfirst into the tight hole |
| 3–8s | Camera tilts down over the rim, diver shrinks into the shaft, pool still tiny |
| 8–12s | Continued fall — pool grows steadily larger |
| ~12–13s | Splash — camera plunges underwater into bubbles |
| 13–15s | Ripples in the confined shaft, rising toward rim of daylight |

### 15-second narrow well dive check and cost

Generation plan: `8s initial + 7s extension`, full 15 seconds kept. Output: **720x1280 at 24 fps** (Veo output; reference was 30fps). Estimated Veo cost: **$1.50** at `$0.10/s`.

**Rate limit reminder**: Tier 1 allows 2 RPM for Veo. Space runs at least 60 seconds apart to avoid 429 errors.

---

# Test inputs: 15-second narrow-shaft death dive — KLING single-shot version

Same reference (`small_hole_jump.mp4`), adapted for **Kling v3 via fal.ai**: one 15-second `text-to-video` call, **1 beat** covering the whole arc — no extension boundary. Kling adaptations: camera reduced to ONE tracking move, audio written as `[source] + action`, splash held at ~14s via "still a tiny dot" depth language — payoff lands in the final second (~93% of runtime).

Go to **New Project** and enter:

| UI field | Value |
| --- | --- |
| Content Type | **YouTube Video** |
| Title | `Narrow Well Death Dive` |
| Description | Paste the Kling Narrow Well Description below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste the Kling Narrow Well Fixed subject and setting below |
| Number of clip beats | **1** |
| Beat 1 — Scene | Paste Kling Scene below |
| Beat 1 — Camera | Paste Kling Camera below |
| Beat 1 — Action | Paste Kling Action below |
| Beat 1 — Ending | Paste Kling Ending below |
| Beat 1 — Visual style | Paste Kling Visual style below |
| Beat 1 — Audio | Paste Kling Audio below |
| Beat 1 — Continuity | Paste Kling Continuity below |
| Beat 1 — Avoid in this clip | Paste Kling per-clip Avoid below |
| Avoid | Paste the Kling Narrow Well Avoid block below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

## Kling Narrow Well Description

```text
Photorealistic 9:16 vertical extreme-sport video, real-time speed, single continuous shot. A shirtless man in red swim shorts dives headfirst into an extremely narrow vertical sandstone shaft in a desert canyon; the camera tracks his fall to a glowing pool far below and plunges underwater.
```

## Kling Narrow Well Fixed subject and setting

```text
Same man, same ~3 metre shaft, same crowd and harsh midday light for the whole shot.
```

## Kling Beat 1 — Scene

```text
Narrow desert sandstone canyon, harsh midday sun. A tight circular shaft — barely 3 metres across — cut into the canyon floor plunges hundreds of metres into darkness, ending in a tiny glowing blue-green pool far below. A muscular shirtless man in bright red swim shorts stands at the rim; about a dozen cheering spectators crowd behind him.
```

## Kling Beat 1 — Camera

```text
Close third-person camera ~1.5–2 metres behind the man, slightly above shoulder level. As he dives in it tilts straight down over the rim and tracks his fall in one continuous downward move, keeping him centred in frame.
```

## Kling Beat 1 — Action

```text
The crowd cheers as he stands poised at the rim. He spreads his arms and dives headfirst into the tight hole. The camera follows him down — his red shorts a bright speck against pale walls rushing upward. The fall feels endless, the pool stays a tiny dot almost the whole way — only at the very end of the clip does he splash into the tiny pool; the camera plunges in and a violent burst of churning bubbles fills the frame as his red shorts vanish into the dark water. Real gravity — fast accelerating fall.
```

## Kling Beat 1 — Ending

```text
Leave empty — the impact/bubble ending is folded into Action (single shot has no separate ending state to protect).
```

## Kling Beat 1 — Visual style

```text
Photorealistic live-action extreme-sports footage. Natural motion blur, realistic scale, real-time speed. Claustrophobic narrow-shaft cinematography.
```

## Kling Beat 1 — Audio

```text
[Crowd] cheering, then [wind] roaring and echoing inside the tight shaft, then a violent [splash] and muffled [underwater] rumble at the very end.
```

## Kling Beat 1 — Continuity

```text
Leave empty — a single continuous clip can't lose continuity; the anchor above covers it.
```

## Kling Beat 1 — Avoid in this clip

```text
Leave empty — merged into the global Avoid block below (Kling routes it to negative_prompt).
```

## Kling Narrow Well Avoid

```text
No slow motion, no floaty falling, no hovering, no camera cuts, no drone shot, no first-person POV, no enlarging the hole, no extra divers, no music, no text, no logos, no front-facing views of the man, no crowd members jumping in. Real gravity — fast and accelerating fall.
```

### Prompt budget (Kling single-shot)

| Field | Chars |
|---|---|
| Description | 299 |
| Visual anchor | 87 |
| Avoid (→ `negative_prompt`, not counted) | 310 |
| Beat 1 (composed, 4 filled sections) | 1067 |
| **Initial clip prompt (composed)** | **1775 / 3072** |

### Resulting timeline (single 15s clip)

| Time | Content |
|---|---|
| 0–2s | Hook: ~12 spectators cheering around the rim, diver poised at the edge |
| 2–4s | Arms spread → headfirst dive into the tight hole |
| 4–13s | Camera tracks the fall — red shorts shrink against pale walls, pool stays a tiny dot |
| ~14s | Pool swells fast → splash, camera plunges underwater |
| 14–15s | Violent burst of bubbles — the payoff lands in the final second |

### Cost

Kling v3 standard, audio on: `15s × $0.126 = $1.89` per generation. Pro tier: `15s × $0.168 = $2.52`.

**Note**: Action already uses the strongest depth language ("the pool stays a tiny dot until the last second"). If Kling still splashes early, reinforce Ending instead — e.g. "the entire clip is one continuous fall; impact happens only in the final frame".
