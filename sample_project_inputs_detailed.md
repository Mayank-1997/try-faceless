# Sample Project Inputs — Detailed Scene Descriptions

Use these inputs on the **Create New Project** page to test the
end-to-end flow with the new **Imagen (AI image) generation** pipeline.

## How to use this file

1. Choose a project.
2. On the **Create New Project** page, fill in the form fields.
3. Click **Create Project** and start the workflow.
4. After the **ASSET_GENERATION** step completes, check the generated
   images under:
   ```
   storage/projects/<project_id>/images/scene_N.png
   ```
5. Compare the generated images against the **Expected Scenes** section
   for each project below to verify Imagen produced the right visuals.

## What to look for (Imagen vs Stock)

With the new Imagen-first pipeline:

- **All visual scenes** should generate via `ai_image` (Imagen), not stock.
- **Stock footage scenes** are automatically redirected to `ai_image`.
- Images should closely match the scene descriptions below — Imagen
  produces on-prompt visuals, unlike stock which often returns
  irrelevant matches.
- Check **Langfuse** for traces: each image generation should appear as
  a `generation` observation with cost `$0.04`.

## Field reference

| Field | Notes |
|---|---|
| `title` | 1–300 chars, required. |
| `description` | 0–5000 chars. More detail = better scripts and scenes. |
| `language` | `en`, `es`, `fr`, `de`, `hi`, `zh`, `ja`. |
| `audience` | e.g. "beginners, tech enthusiasts". |
| `content_type` | Choose `youtube_video` for full video pipeline. |
| `video_style` | e.g. `documentary`, `explainer`, `cinematic`. |
| `target_duration_seconds` | 60–300 recommended for testing. |
| `tags` | Comma-separated. Max 20. |

---

## Project 1: The Lost City of Atlantis

- **Title:** The Lost City of Atlantis
- **Description:** A documentary-style exploration of the Atlantis myth. Cover Plato's original account, the possible real-world locations (Santorini, the Richat Structure, Antarctica), and why the legend endures. Tone: mysterious, educational, cinematic.
- **Language:** en
- **Audience:** History buffs, mythology fans, documentary lovers
- **Content type:** youtube_video
- **Video style:** documentary
- **Target duration:** 180
- **Tags:** Atlantis, mythology, history, documentary, ancient civilizations

### Expected Scenes (6–8 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | Aerial view of a sunken ancient city beneath crystal-clear blue ocean water, golden ruins glowing faintly, rays of sunlight piercing through the water surface | Slow aerial dolly-in |
| 2 — Plato's Account | An ancient Greek scroll on a wooden table, quill beside it, warm candlelight, a marble bust of Plato in the blurred background | Close-up, shallow depth of field |
| 3 — Santorini Theory | A volcanic island caldera filled with blue water, white-washed Greek buildings on the cliff edge, dramatic sunset light | Wide establishing shot |
| 4 — The Richat Structure | Satellite-style top-down view of the Richat Structure in the Sahara desert — concentric circular rock formations, golden sand, blue center | Overhead, slow zoom-out |
| 5 — Antarctica Theory | A vast icy Antarctic landscape with snow-covered mountains, a crack in the ice revealing ancient stone structures below, cold blue tones | Wide pan |
| 6 — The Enduring Legend | A modern museum display case with ancient artifacts, soft spotlight, visitors in silhouette admiring the exhibit, warm museum lighting | Medium shot, slow dolly-in |
| 7 — Conclusion | A lone diver's flashlight beam sweeping across underwater ruins, bubbles rising, mysterious and haunting atmosphere, deep blue darkness | POV, handheld feel |

---

## Project 2: How the Pyramids Were Really Built

- **Title:** How the Pyramids Were Really Built
- **Description:** An educational explainer covering the leading theories of pyramid construction: the internal ramp theory, water shafts, and the latest 2024 discoveries. Tone: factual, awe-inspiring, accessible.
- **Language:** en
- **Audience:** History enthusiasts, students, curious minds
- **Content type:** youtube_video
- **Video style:** documentary
- **Target duration:** 240
- **Tags:** pyramids, Egypt, ancient engineering, archaeology, history

### Expected Scenes (7–9 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | Wide shot of the Great Pyramid of Giza at golden hour, a lone figure in silhouette standing at the base for scale, warm desert light, dramatic sky | Wide establishing, slow zoom-in |
| 2 — The Scale | Close-up of massive limestone blocks, a worker's hand tracing the edge of a block, dust particles in sunlight, showing the precision of the cuts | Extreme close-up |
| 3 — The External Ramp Theory | A long earthen ramp spiraling up the outside of a half-built pyramid, workers pulling blocks with ropes, dusty atmosphere, ancient Egyptian setting | Wide, high angle |
| 4 — The Internal Ramp Theory | A cutaway cross-section diagram of the pyramid showing internal spiral tunnels, workers inside moving blocks, torch-lit interior, architectural blueprint style | Cutaway / cross-section |
| 5 — The Water Shaft Theory | A flooded channel beside the pyramid with wooden boats carrying stone blocks, workers guiding the boats, ancient Nile-side setting, misty morning | Medium wide shot |
| 6 — The 2024 Discovery | A modern archaeological dig site near the pyramids, researchers with laptops and drones, a tent with equipment, desert backdrop, documentary feel | Medium shot |
| 7 — The Workforce | A bustling ancient Egyptian workers' village, people baking bread, mixing mortar, and hauling stones, lively atmosphere, warm earthy tones | Wide, slow pan |
| 8 — Conclusion | Time-lapse style: the pyramid rising block by block from bare desert to completed structure, dramatic sky transitioning from day to night | Time-lapse, static |

---

## Project 3: The Science of Sleep and Dreams

- **Title:** The Science of Sleep and Dreams
- **Description:** A calm, science-based explainer on what happens in the brain during sleep: REM vs non-REM, why we dream, the role of the hippocampus, and tips for better sleep. Tone: soothing, informative, visually soft.
- **Language:** en
- **Audience:** Students, wellness audience, curious adults
- **Content type:** youtube_video
- **Video style:** explainer
- **Target duration:** 180
- **Tags:** sleep, dreams, brain science, REM, neuroscience

### Expected Scenes (6–8 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | A person sleeping peacefully in a softly lit bedroom, moonlight through curtains, a faint glowing outline of a brain hovering above their head, dreamy ethereal atmosphere | Medium shot, slow dolly-in |
| 2 — Sleep Stages | A glowing cross-section of a human brain showing different colored regions lighting up in sequence (blue, purple, gold), representing NREM and REM stages, dark background, bioluminescent style | Close-up, slow orbit |
| 3 — REM Sleep | A close-up of a sleeping eye with rapid eye movement visible beneath the closed eyelid, subtle twitching, soft blue lighting, EEG wave overlay faintly visible | Extreme close-up |
| 4 — Why We Dream | A surreal dreamscape: floating islands, a clock melting like Dali's painting, soft pastel colors, a person walking through a door that leads to the sky, dreamlike and abstract | Wide, slow tracking |
| 5 — The Hippocampus | A glowing 3D model of the hippocampus inside a translucent human head, golden light, memory fragments (small images) flowing into it like a stream, dark background | Medium close-up, slow rotation |
| 6 — Sleep Tips | A cozy bedroom scene with a warm bedside lamp, a book on the nightstand, a phone face-down, soft amber lighting, plants on the windowsill, inviting and calm | Medium shot, static |
| 7 — Conclusion | A sunrise through a bedroom window, a person waking up refreshed and stretching, warm golden light, birds visible outside, optimistic and energizing | Medium shot, slow zoom-out |

---

## Project 4: The Viking Discovery of America

- **Title:** The Viking Discovery of America
- **Description:** A historical narrative about how Norse explorers reached North America 500 years before Columbus. Cover Erik the Red, Leif Erikson, the settlement at L'Anse aux Meadows, and why the colony failed. Tone: epic, cold, atmospheric.
- **Language:** en
- **Audience:** History fans, Viking enthusiasts, documentary lovers
- **Content type:** youtube_video
- **Video style:** cinematic
- **Target duration:** 240
- **Tags:** Vikings, Leif Erikson, Norse, America, pre-Columbian

### Expected Scenes (8–10 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | A Viking longship emerging from thick Arctic fog, dragon-headed prow cutting through icy waves, a crew of Vikings in furs and helmets rowing in unison, cold blue and grey tones, dramatic | Wide, low angle |
| 2 — Greenland | A harsh green and white Icelandic/Greenland landscape, a small Norse settlement with turf-roofed longhouses, smoke rising from chimneys, mountains in the distance, overcast sky | Wide establishing shot |
| 3 — Erik the Red | A weathered Viking chieftain with a red beard, fur cloak, standing at the prow of a ship looking at new land, wind blowing his hair, determination on his face, dramatic lighting | Medium close-up |
| 4 — Leif Erikson's Voyage | A map-style illustration showing a route from Greenland southwest across the North Atlantic to a coastline labeled "Vinland", aged parchment texture, hand-drawn cartography style | Top-down, static |
| 5 — Landfall | Vikings stepping off a longship onto a rocky, forested coastline (Newfoundland-like), dense green trees, a Viking placing a hand on the soil, misty morning, sense of discovery | Medium shot, low angle |
| 6 — L'Anse aux Meadows | A reconstructed Norse settlement with turf-walled buildings, a smoky blacksmith forge, Viking tools and weapons laid out, forest backdrop, late afternoon light | Wide shot |
| 7 — Conflict with Skraelings | A tense standoff between armored Vikings and indigenous people in a forest clearing, no violence shown, both sides cautious and wary, dramatic tension, dappled forest light | Medium wide |
| 8 — Abandonment | An empty, decaying Norse longhouse being reclaimed by nature, vines growing through the door, a discarded axe on the ground, melancholy atmosphere, autumn light | Medium shot, slow dolly-in |
| 9 — The Legacy | A modern museum display of Viking artifacts (a helmet, a coin, a runestone) under glass, soft spotlights, visitors in the background, warm museum lighting | Medium close-up |
| 10 — Conclusion | A Viking longship sailing back toward the horizon at sunset, silhouette against an orange and purple sky, the ship getting smaller, epic and wistful | Wide, slow zoom-out |

---

## Project 5: What Happens Inside a Black Hole?

- **Title:** What Happens Inside a Black Hole?
- **Description:** A mind-bending explainer of what theoretically happens if you fall into a black hole: spaghettification, time dilation, the event horizon, and the singularity. Tone: awe-inspiring, slightly unsettling, visually spectacular.
- **Language:** en
- **Audience:** Science fans, space enthusiasts, curious teenagers
- **Content type:** youtube_video
- **Video style:** cinematic
- **Target duration:** 180
- **Tags:** black hole, space, physics, spaghettification, event horizon

### Expected Scenes (6–8 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | A massive black hole with a glowing orange accretion disk, stars being stretched and pulled into it, a tiny spaceship for scale, deep space background, awe-inspiring and terrifying | Wide, slow zoom-in |
| 2 — The Event Horizon | A boundary in space where light bends and distorts, stars behind it appear warped and stretched, a faint ring of light, dark center, gravitational lensing effect | Close-up, slow orbit |
| 3 — Spaghettification | A stylized illustration of a human figure being stretched vertically into a thin line as it approaches the black hole, atoms separating, blue and purple energy, abstract and slightly disturbing | Medium, slow zoom-in |
| 4 — Time Dilation | A clock floating in space near a black hole, its hands slowing down and stopping, while a second clock far away ticks normally, split-screen effect, Einstein's face faintly in the background | Medium shot |
| 5 — The Singularity | A point of infinite density, all matter compressed to a single point, a blinding white light surrounded by absolute darkness, mathematical equations faintly visible, abstract and unknowable | Abstract, slow zoom-in |
| 6 — Hawking Radiation | Faint particles escaping from the edge of the black hole, glowing blue, the black hole slowly shrinking, energy radiating outward, Stephen Hawking's silhouette faintly visible | Medium wide |
| 7 — Conclusion | A person floating in space looking at a black hole, tiny against the vastness, stars reflected in their helmet visor, a sense of wonder and insignificance, deep blue and orange palette | Wide, slow pull-back |

---

## Project 6: The Rise and Fall of the Roman Empire

- **Title:** The Rise and Fall of the Roman Empire
- **Description:** A sweeping historical narrative from the founding of Rome to the fall of the Western Empire. Cover the Republic, Caesar's rise, the Pax Romana, and the slow collapse. Tone: epic, grand, tragic.
- **Language:** en
- **Audience:** History students, documentary fans, classics enthusiasts
- **Content type:** youtube_video
- **Video style:** documentary
- **Target duration:** 300
- **Tags:** Rome, Roman Empire, Julius Caesar, history, ancient

### Expected Scenes (10–12 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | The Roman Forum in its full glory, marble columns, senators in togas walking, the Colosseum in the far background, golden hour light, bustling ancient city | Wide establishing, slow pan |
| 2 — The Founding | A stylized image of Romulus and Remus as infants being nursed by a she-wolf under a fig tree, ancient Italian countryside, mythological and iconic | Medium shot, classical painting style |
| 3 — The Republic | The Roman Senate in session, senators in white togas debating in a marble hall, raised speaking platform, serious expressions, torch-lit interior | Wide shot |
| 4 — Caesar's Rise | Julius Caesar crossing the Rubicon river on horseback, army behind him, dramatic sky, determination on his face, "alea iacta est" mood, cinematic | Medium shot, low angle |
| 5 — The Empire | A map of the Roman Empire at its greatest extent, from Britain to Egypt, glowing borders, major cities marked, aged parchment style with modern glow | Top-down, slow zoom-out |
| 6 — Pax Romana | A peaceful Roman provincial city, aqueducts, markets, a Roman road with travelers, children playing, warm Mediterranean light, prosperity and order | Wide, slow pan |
| 7 — The Colosseum | The Colosseum packed with spectators, gladiators in the arena, the emperor's thumb, dust and sunlight, dramatic and visceral | Wide, high angle |
| 8 — The Crisis | A Roman city under siege, barbarians at the gates, smoke and fire, a Roman standard falling, chaos and despair, dark and dramatic tones | Wide, handheld feel |
| 9 — The Fall | The last emperor Romulus Augustulus handing over his crown, a small boy on a throne, a barbarian king standing before him, somber and quiet, end of an era | Medium shot |
| 10 — The Legacy | Roman ruins in modern Rome, the Colosseum half-collapsed, tourists walking through, sunset light, a sense of time and endurance | Wide, slow zoom-out |
| 11 — Conclusion | A single Roman column standing alone in a field of wildflowers, golden sunset behind it, birds flying past, poetic and melancholic | Medium wide, static |

---

## Project 7: How Your Immune System Fights a Virus

- **Title:** How Your Immune System Fights a Virus
- **Description:** A biology explainer showing how the immune system responds to a viral infection: the innate response, T-cells, antibodies, and memory cells. Tone: educational, dynamic, visually colorful.
- **Language:** en
- **Audience:** Students, science enthusiasts, health-conscious adults
- **Content type:** youtube_video
- **Video style:** explainer
- **Target duration:** 150
- **Tags:** immune system, virus, biology, T-cells, antibodies

### Expected Scenes (6–8 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | A virus (spiky red sphere) approaching a healthy human cell (blue membrane), dramatic microscopic view, dark background with glowing particles, biological and dramatic | Close-up, slow zoom-in |
| 2 — The Invasion | A virus injecting its genetic material into a cell, the cell membrane being breached, viral RNA spreading inside, red and green fluorescent tags, microscope-style imagery | Extreme close-up |
| 3 — The Innate Response | Macrophages (large blobby white cells) engulfing viruses, a battlefield-style scene at the cellular level, glowing particles, dynamic and active, warm and cool tones | Medium, dynamic |
| 4 — The Alarm | A dendritic cell presenting a viral antigen on its surface, a T-helper cell approaching to "read" it, molecular handshake, glowing communication lines between cells | Close-up |
| 5 — T-Cells Attack | Killer T-cells (sleek, predatory cells) destroying virus-infected cells, infected cells bursting, green and red fluorescence, action and precision | Medium, fast movement |
| 6 — Antibodies | Y-shaped antibodies swarming and neutralizing viruses, locking onto the spikes, viruses being clumped together and disabled, golden and blue glow, satisfying and precise | Close-up, slow orbit |
| 7 — Memory Cells | Memory T and B cells resting quietly, storing a "blueprint" of the virus for future defense, a vault-like cellular structure, calm and reassuring, warm golden light | Medium shot |
| 8 — Conclusion | A healthy person breathing calmly, a faint glowing shield around them representing immunity, soft natural light, a park setting, optimistic and peaceful | Medium wide, slow zoom-out |

---

## Project 8: The Mystery of the Bermuda Triangle

- **Title:** The Mystery of the Bermuda Triangle
- **Description:** A documentary exploring the Bermuda Triangle phenomenon: famous disappearances (Flight 19, USS Cyclops), scientific explanations (methane gas, rogue waves, magnetic anomalies), and why the legend persists. Tone: mysterious, balanced, investigative.
- **Language:** en
- **Audience:** Mystery fans, documentary lovers, curious minds
- **Content type:** youtube_video
- **Video style:** documentary
- **Target duration:** 180
- **Tags:** Bermuda Triangle, mystery, disappearances, ocean, paranormal

### Expected Scenes (7–9 scenes)

| Scene | Visual Description (what Imagen should generate) | Camera |
|---|---|---|
| 1 — The Hook | A map of the Atlantic Ocean with a glowing triangle drawn between Miami, Bermuda, and Puerto Rico, storm clouds swirling inside it, a ship silhouette in distress, dark and ominous | Top-down, slow zoom-in |
| 2 — Flight 19 | Five WWII Navy bombers flying in formation over the ocean, blue sky turning grey, the planes appearing confused and disoriented, radio waves visualized as fading lines, 1940s era | Wide, tracking shot |
| 3 — The Disappearance | An empty ocean where Flight 19 should be, scattered clouds, an oil slick on the water, eerie calm after chaos, a search plane circling above, somber and unsettling | Wide, high angle |
| 4 — USS Cyclops | A massive early 1900s naval cargo ship listing in a storm, massive waves crashing over the deck, the ship disappearing into the trough, dramatic and terrifying, dark green ocean | Wide, low angle |
| 5 — Methane Gas Theory | An underwater methane gas eruption, bubbles rising rapidly from the seafloor, a ship losing buoyancy and sinking, water density dropping, scientific cross-section view | Cross-section, slow zoom-in |
| 6 — Rogue Waves | A massive 100-foot rogue wave looming over a small ship, the wave about to crash, dramatic lighting, the ship tiny against the wall of water, terrifying and awe-inspiring | Wide, low angle |
| 7 — Magnetic Anomalies | A ship's compass spinning wildly, the needle unable to find north, the bridge of an old ship, instruments malfunctioning, red warning lights, claustrophobic and tense | Close-up, handheld |
| 8 — The Legend | A bookstore shelf with books about the Bermuda Triangle, a documentary playing on an old TV, a person reading with wide eyes, pop culture and mythmaking, warm nostalgic light | Medium shot |
| 9 — Conclusion | A calm, sunny ocean in the Bermuda Triangle region, a cruise ship passing peacefully, no storms, no mystery, just beautiful blue water — the reality vs the myth, bright and clear | Wide, slow pan |

---

## Verification Checklist

After running each project through the workflow, verify:

- [ ] **All scene images exist** in `storage/projects/<project_id>/images/`
- [ ] **No stock video files** in `storage/projects/<project_id>/videos/` (stock_footage should be redirected to ai_image)
- [ ] **Images match the scene descriptions** above (Imagen should produce on-prompt visuals)
- [ ] **Langfuse traces** show `image_generation` observations with cost `$0.04` each
- [ ] **Final video** uses Ken Burns pan/zoom on the AI images (no stock clips)
- [ ] **Total image cost** = number of visual scenes × $0.04

## Cost Estimates per Project

| Project | Visual Scenes | Est. Image Cost | Est. LLM Cost | Total Est. |
|---|---|---|---|---|
| 1. Atlantis | 7 | $0.28 | ~$0.15 | ~$0.43 |
| 2. Pyramids | 8 | $0.32 | ~$0.20 | ~$0.52 |
| 3. Sleep Science | 7 | $0.28 | ~$0.15 | ~$0.43 |
| 4. Vikings | 10 | $0.40 | ~$0.25 | ~$0.65 |
| 5. Black Hole | 7 | $0.28 | ~$0.15 | ~$0.43 |
| 6. Roman Empire | 11 | $0.44 | ~$0.30 | ~$0.74 |
| 7. Immune System | 8 | $0.32 | ~$0.18 | ~$0.50 |
| 8. Bermuda Triangle | 9 | $0.36 | ~$0.20 | ~$0.56 |

> **Note:** LLM costs are estimates based on Gemini Flash pricing. Actual
> costs depend on prompt length and number of agents invoked. Check
> Langfuse for exact per-call costs.
