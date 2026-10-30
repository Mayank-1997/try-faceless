# Plane Crash / Emergency Flyby Test Inputs (Kling v3 Single-Shot)

Reference video: `C:\Users\91858\Downloads\crash_1.mp4`

---

## 1. Precise Reference Video Analysis

| Property | Value |
|---|---|
| Duration | `11.10s` (use `12` or `15` seconds in UI) |
| Resolution | `720x1280` (9:16 vertical portrait) |
| Frame rate | `30 fps` |
| Audio | AAC stereo — roaring jet turbines, wind/fire rumble |
| Source medium | **3D Flight-Sim / GTA V modded replay** (Boeing 747-400 in fictional *"Caipira"* Brazilian livery flying over the Route 68 / Fort Zancudo highway overpass with Mount Josiah in the background) |

### Frame-by-frame timeline of `crash_1.mp4`

| Time | What happens on screen | Why it hooks viewers |
|---|---|---|
| **0–2s** | Elevated hillside view over a two-level concrete highway viaduct in arid hills with cars moving below. A massive white Boeing 747 enters low from the left with nose pitched up; its left-wing engine is on fire and trailing thick black smoke. | **Instant scale contrast + danger**: a giant commercial airliner impossibly low right above normal highway traffic. |
| **2–4s** | As the 747 crosses above the concrete overpass bridge, **both wing-root/inboard engines erupt in long orange flames** and dense black smoke trails. | **Escalation**: the fire doubles in size as the plane approaches the camera. |
| **4–7s** | **Peak close-up side profile**: the 747 fills the center of the vertical frame at eye level with the hillside camera, banking slightly away while panning left-to-right across the dry cliffside. | **Maximum visual clarity**: viewers clearly see the airline fuselage, windows, blue engine cowlings, and roaring flames. |
| **7–9s** | The camera continues panning right as the burning 747 descends below the level of the upper highway deck toward the industrial/airport structures in the valley. | **Suspense**: will it clear the bridge or slam into the highway/buildings? |
| **9–11.1s** | The aircraft skims down into the industrial strip / runway perimeter behind the highway, belly-landing in a massive billowing black smoke plume **just before a full explosion**. | **Cliffhanger cut**: cutting right as it touches down drives replays and comments (and avoids platform graphic-disaster bans). |

### Key takeaways for your new FB/IG channel

1. **The reference is a "near-crash / low emergency flyby + belly touchdown", NOT a mid-air fireball**:
   - Keeping the plane intact and flying dangerously low over everyday landmarks (highways, bridges, rooftops, beaches) for 90% of the clip is what creates tension.
   - Cutting on the ground-skim / smoke plume (instead of mass casualties or carnage) keeps the reel safe for **Facebook/Instagram monetization and AI safety filters** (`enable_safety_checker: true` on fal.ai).
2. **Camera formula**:
   - **Single bystander telephoto pan** from an elevated vantage point (hillside, overpass, balcony) panning smoothly left-to-right as the heavy jet roars past.
3. **Why Kling v3 is upgrade over the reference**:
   - `crash_1.mp4` has visible GTA V terrain/tree textures if you look closely. Prompting Kling v3 for **photorealistic smartphone witness footage** gives you the exact same composition and choreography, but looking like real live-action footage rather than a game mod.

---

## 2. UI Inputs — Kling Single-Shot (12s or 15s)

Go to **New Project** and enter:

| UI field | Value |
|---|---|
| Content Type | **YouTube Video** |
| Title | `A380 Emergency Highway Flyby` |
| Description | Paste **Description** below |
| Production Flow | **Direct cinematic video (follow my description)** |
| Fixed subject and setting | Paste **Fixed subject and setting** below |
| Number of clip beats | **1** |
| Beat 1 — Scene | Paste **Scene** below |
| Beat 1 — Camera | Paste **Camera** below |
| Beat 1 — Action | Paste **Action** below |
| Beat 1 — Ending | **Leave empty** (folded into Action) |
| Beat 1 — Visual style | Paste **Visual style** below |
| Beat 1 — Audio | Paste **Audio** below |
| Beat 1 — Continuity | **Leave empty** |
| Beat 1 — Avoid in this clip | **Leave empty** |
| Avoid | Paste **Avoid** below |
| Narration | **Leave blank** |
| Language | **English** |
| Target Duration (sec) | `12` (matches the 11.1s reference pace) or `15` |
| Video Style | **Cinematic** |
| Aspect Ratio | **9:16 Portrait (1080x1920) — Shorts/Reels** |

---

## Description

```text
Photorealistic 9:16 vertical aviation emergency footage, real-time speed, single continuous shot. A massive double-deck Airbus A380 airliner with a crimson-red tail fin and engines engulfed in bright orange flames and thick black smoke makes an ultra-low emergency descent over a multi-level highway overpass, banking past the camera and skimming down into a smoke plume.
```

## Fixed subject and setting

```text
Same white double-deck Airbus A380 superjumbo jet with crimson-red tail fin and silver stripe, burning wing engines trailing dense black smoke, same sunlit hillside highway overpass with moving traffic and distant mountain ridge.
```

## Beat 1 — Scene

```text
Bright afternoon sun over dry coastal hills and a tall multi-level concrete highway overpass with cars driving across. A massive white double-deck Airbus A380 passenger airliner with a crimson-red tail fin approaches at dangerously low altitude just above the highway bridge, its under-wing engines engulfed in roaring orange flames and trailing thick billowing black smoke plumes.
```

## Beat 1 — Camera

```text
Elevated hillside witness camera beside the highway overpass — steady handheld telephoto tracking shot with subtle natural shake. The camera pans smoothly left-to-right as the giant A380 roars past at eye level, tracking its descent across the bridge toward the valley floor in one continuous unbroken shot.
```

## Beat 1 — Action

```text
The burning Airbus A380 glides in fast and low from the left with nose pitched slightly up in a desperate flare, roaring directly over the elevated highway bridge while cars drive beneath it. Heavy black smoke and long tongues of orange fire stream from the wings as the double-deck fuselage fills the frame in a close side-profile flyby, then banks gently right and descends behind the highway toward the valley strip, skimming the ground in a dramatic emergency touchdown as dense black smoke billows upward.
```

## Beat 1 — Ending

```text
(Leave empty)
```

## Beat 1 — Visual style

```text
Photorealistic live-action smartphone witness footage, crisp daylight, natural heat shimmer and exhaust turbulence, realistic heavy aircraft weight and momentum, real-time 30fps motion.
```

## Beat 1 — Audio

```text
Continuous terrified [passengers and bystanders] screaming in panic throughout the entire clip, layered over deafening [burning jet engines] howling and surging at low altitude, [fire] roaring from the turbines, a violent [wind blast] buffeting the microphone as the plane passes, and a heavy [ground rumble] at touchdown. No music, no narration.
```

## Beat 1 — Continuity

```text
(Leave empty)
```

## Beat 1 — Avoid in this clip

```text
(Leave empty)
```

## Avoid

```text
No camera cuts, no cockpit POV, no cartoon or video-game textures, no slow motion, no mid-air disintegration, no spinning out of control, no text, no watermarks, no music, no narration. Heavy realistic jet inertia and physics.
```

---

## 3. Prompt Budget & Cost Verification

| Field | Chars |
|---|---|
| Description | 377 |
| Fixed subject and setting | 228 |
| Beat 1 (composed sections) | 1756 |
| Avoid (routed to `negative_prompt`) | 226 |
| **Total composed prompt sent to Kling** | **2365 / 3072** (under Kling's 2500 recommended target) |

- **12s generation cost** (Kling v3 Standard, audio on): `12s × $0.126 = $1.51`
- **15s generation cost** (Kling v3 Standard, audio on): `15s × $0.126 = $1.89`

---

# Video 2 — Coastal Low Flyby into Hillside Dive (sky_2.mp4)

Reference video: `C:\Users\91858\Downloads\sky_2.mp4`

## 1. Precise Reference Video Analysis

| Property | Value |
|---|---|
| Duration | `11.33s` (use `12` seconds in UI) |
| Resolution | `720x1280` (9:16 vertical portrait) |
| Frame rate | `30 fps` |
| Audio | AAC — jet roar, wind rumble |
| Source medium | **GTA V / flight-sim replay** (white 747 over a Del Perro-style beach, pier, coastal highway and green hills) |

### Frame-by-frame timeline of `sky_2.mp4`

| Time | What happens on screen | Why it hooks |
|---|---|---|
| **0–2s** | Elevated view over a sunny beach, pier and coastal highway. A white 747 enters low over the water with **three engines on fire** trailing heavy black smoke arcs. | Instant danger + scale — burning jet impossibly low over a populated beach. |
| **2–4s** | The plane **pulls up steeply** past the camera — belly and four flaming engine trails fill the vertical frame against pure blue sky. | **Peak visual moment** — the pull-up + belly view is the clip's signature. |
| **4–7s** | Camera tilts up tracking it; the plane levels over city towers, then banks over green coastal hills, smoke trails arcing behind. | Continuous momentum — no dead air. |
| **7–11.3s** | The 747 **drops into a steep nose-down dive** toward the hillside and the coastal highway below, its shadow racing across the hill — clip ends just before impact. | Cliffhanger cut — imminent crash implied, never shown. |

### Key differences vs `crash_1.mp4`

| Aspect | crash_1 | sky_2 |
|---|---|---|
| Setting | Overcast highway overpass | **Sunny beach + pier + hills** |
| Burning engines | 2 | **3** (thicker smoke arcs) |
| Flight path | Straight descent to touchdown | **Pull-up → level → steep dive** |
| Camera | Bystander pan | **Tilts up tracking** the plane |
| Ending | Belly touchdown in smoke | **Nose-down dive, cut pre-impact** |

---

## 2. UI Inputs — Kling Single-Shot (12s)

Same UI field layout as Video 1 — **1 beat**, Target Duration `12`, 9:16 portrait.

## Description

```text
Photorealistic 9:16 vertical aviation emergency footage, real-time speed, single continuous shot. A large twin-aisle passenger airliner with three engines streaming fire and thick black smoke flies dangerously low over a sunny coastal beach and pier, climbs past the camera in a desperate pull-up, then drops into a steep dive over green coastal hills beside a highway.
```

## Fixed subject and setting

```text
Same white twin-aisle airliner with dark tail fin, three engines burning with orange flames and arcing black smoke trails, same sunny blue-sky coastline with beach, pier, city towers and green hills.
```

## Beat 1 — Scene

```text
Brilliant clear-blue midday sky over a sunny coastline — a wide beach, a long wooden pier, palm-lined coastal highway with moving cars, distant city towers and a suspension bridge. A large white twin-aisle passenger airliner approaches at very low altitude over the water, three of its engines engulfed in bright orange flames trailing thick arcing black smoke.
```

## Beat 1 — Camera

```text
Elevated coastal viewpoint high above the beachfront road — a single continuous handheld tracking shot. The camera tilts up to follow the burning airliner as it roars overhead in a steep pull-up, then tilts down tracking it as it drops over the green hillside toward the highway below.
```

## Beat 1 — Action

```text
The burning airliner glides in low over the beach and pier, flames and black smoke streaming from three engines, its shadow sliding across the sand. It pulls up steeply past the camera in a desperate climbing bank — filling the frame belly-first against the blue sky — then rolls level over the city towers, banks over the green coastal hills, and drops into a steep nose-down descent toward the hillside and highway below, smoke trails arcing behind it, as the clip ends just before impact.
```

## Beat 1 — Ending

```text
(Leave empty)
```

## Beat 1 — Visual style

```text
Photorealistic live-action phone witness footage, harsh clear daylight, natural heat shimmer around the burning engines, realistic heavy aircraft weight and momentum, real-time 30fps motion.
```

## Beat 1 — Audio

```text
Continuous terrified [bystanders] screaming in panic throughout the clip, layered over deafening [burning jet engines] howling and surging, [fire] roaring from the turbines, a violent [wind blast] as the plane thunders overhead, and distant [traffic noise] below. No music, no narration.
```

## Beat 1 — Continuity

```text
(Leave empty)
```

## Beat 1 — Avoid in this clip

```text
(Leave empty)
```

## Avoid

```text
No camera cuts, no cockpit POV, no cartoon or video-game textures, no slow motion, no mid-air disintegration, no spinning barrel roll, no text, no watermarks, no music, no narration. Heavy realistic jet inertia and physics.
```

---

## 3. Prompt Budget & Cost

| Field | Chars |
|---|---|
| Description | 369 |
| Fixed subject and setting | 199 |
| Beat 1 (composed sections) | 1666 |
| Avoid (routed to `negative_prompt`) | 223 |
| **Total composed prompt sent to Kling** | **2238 / 3072** |

- **12s generation cost** (Kling v3 Standard, audio on): `12s × $0.126 = $1.51`
