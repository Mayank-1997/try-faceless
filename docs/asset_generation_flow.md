# Asset Generation Flow

How the asset generation step turns storyboard planning into actual
images, videos, and voice files via stock providers (Pexels, Pixabay,
Unsplash) and AI providers (Imagen, Veo).

## 1. Inputs from WorkflowState

The asset generation step (`WorkflowStep.ASSET_GENERATION`) reads from:

```
workflow_state.storyboard.metadata["storyboard_package"].scene_packages[i]
```

Each `ScenePackage` (defined in `src/ai/agents/storyboard/schema.py`)
has these fields, but only a subset is used for the stock API call:

| Field                     | Used as                | Source                          |
|---------------------------|------------------------|---------------------------------|
| `visual_plan.visual_description` | **Primary prompt** | `StoryboardVisualAgent` (LLM)   |
| `visual_prompt_summary`   | Fallback prompt        | `StoryboardReviewAgent` (= copy of `visual_description`) |
| `title`                   | Last-resort prompt     | `SceneSegmentationAgent`        |
| `asset_type`              | Decides image vs video gateway | `AssetDecisionAgent` (LLM) |
| `duration_seconds`        | Video duration         | `SceneSegmentationAgent`        |
| `scene_number`            | Storage path           | —                               |

The prompt selection logic in
`src/infrastructure/tasks/workflow_tasks.py` (line ~1008):

```python
prompt = sp.visual_plan.visual_description or sp.visual_prompt_summary or sp.title
visual = (sp.asset_type or "ai_image").lower()
```

Then the `asset_type` string decides which gateway is called:

| `asset_type` value            | Gateway called               |
|-------------------------------|------------------------------|
| `stock_image`, `ai_image`, `image` | `image_gateway.generate_image()` (Imagen primary, stock fallback) |
| `stock_footage`, `stock_video`, `video` | **Redirected to `ai_image`** — uses Imagen with Ken Burns animation, NOT the video gateway |
| Anything else (diagram, chart, icon, screenshot, animation_only, mixed_assets) | Placeholder PNG generated locally |

## 2. The LLM prompt that generates `visual_description`

The `StoryboardVisualAgent` asks the LLM to produce, per scene:

- `visual_description` — the description that becomes the stock search query
- `composition` — e.g., "Rule of thirds, centered"
- `foreground` — foreground elements
- `background` — background elements

Only `visual_description` reaches the stock API. The others are used by
the rendering pipeline for layout/animation.

## 3. The LLM prompt that decides `asset_type`

The `AssetDecisionAgent` uses `ASSET_DECISION_PROMPT` (in
`src/ai/agents/storyboard/prompts.py`, v2.0.0), which instructs:

> 1. ALWAYS prefer ai_image (Google Imagen / Gemini image generation) for
>    still visuals. AI-generated images produce far more accurate,
>    on-prompt, and visually consistent results than stock photos.
> 2. Use stock_image only as a fallback when ai_image is unavailable or
>    the scene is a generic real-world subject.
> 3. Use stock_footage only when real motion is essential.
> 4. NEVER use ai_video unless the scene absolutely requires custom AI
>    motion and cost is not the priority.
> 5. Set estimated_generation_cost to 0.04 for ai_image.
> 6. Set estimated_generation_cost to 0.00 for stock_image and stock_footage.

The LLM returns a JSON `decisions` array with `asset_type`,
`confidence_score`, `estimated_generation_cost`, and `rationale` per scene.

### Provider selection now respects the Imagen-first policy

The registry registers Imagen BEFORE stock providers, so Imagen is the
primary image provider whenever a Gemini API key is configured. Stock
providers are registered as fallback. See section 5 for details.

## 4. Query cleaning before stock API call

Before the `visual_description` reaches Pexels/Pixabay/Unsplash, it is
cleaned by `_clean_query()` in `src/ai/providers/stock.py`:

```python
def _clean_query(prompt: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", prompt)
    words = [w for w in text.split() if w]
    return " ".join(words[:12]) or "nature"   # first 12 words only
```

Example:

| LLM `visual_description`                          | Stock search query                |
|---------------------------------------------------|-----------------------------------|
| "Close-up of coarse coffee grounds being measured on a dark surface" | `Close up of coarse coffee grounds being measured on` |
| "A scientist in a white lab coat pouring liquid nitrogen into a beaker, slow motion" | `A scientist in a white lab coat pouring liquid nitrogen into` |

Punctuation is stripped, and only the first 12 words are kept.

## 5. Provider selection: Imagen-first (stock as fallback)

### Registration order (defines priority)

In `src/ai/providers/registry.py`:

```python
await self._register_llm_providers()
await self._register_image_providers()   # Imagen registered FIRST (primary)
await self._register_stock_providers()   # Stock registered SECOND (fallback)
await self._register_video_providers()
await self._register_voice_providers()
```

`get_providers_by_type()` returns providers **in registration order**.
The gateway's `_get_primary_provider()` always returns `providers[0]`,
so **Imagen is always the primary image provider** when a Gemini API
key is configured. Stock providers serve as fallback.

### What this means in practice

| Imagen/Gemini key configured? | Primary image provider | Fallback |
|-------------------------------|------------------------|----------|
| Yes (GEMINI_API_KEY or GOOGLE_IMAGEN_API_KEY) | ImagenProvider | StockImageProvider (if stock keys set) |
| No                            | StockImageProvider (if stock keys set) | None |

### ImagenProvider implementation

The `ImagenProvider` (in `src/ai/providers/imagen.py`) uses the
`google.generativeai` SDK with the `gemini-2.5-flash-image` model.
This model is accessible with a standard `GEMINI_API_KEY` — no Vertex
AI / GCP service-account required. The provider accepts
`GOOGLE_IMAGEN_API_KEY` if set, but falls back to `GEMINI_API_KEY`.

The model returns `inline_data` parts containing raw PNG image bytes.

### Langfuse tracing

The `ImageGateway` records each `generate_image` call as a Langfuse
**generation** observation, including:
- The prompt (input)
- Provider and model
- Cost (USD)
- Latency (start/end time)
- Image size (bytes)
- Correlation ID and trace ID

This makes image-generation costs visible alongside LLM costs in the
Langfuse dashboard. The `langfuse_client` is injected via the DI
container (`ServiceContainer._init_gateways`).

## 6. Provider fallback chain: Pexels vs Pixabay vs Unsplash

There is **no confidence scoring** between stock providers. It is a
hardcoded **sequential** fallback chain — providers are tried one at a
time, and the first provider that returns a downloadable result wins.

**We do NOT call all three providers at once and pick the best.** We
call them one at a time. Pexels is tried first. Only if Pexels fails
completely do we try Pixabay. Only if Pixabay also fails do we try
Unsplash.

### Image search order

| Order | Provider  | API endpoint                                      |
|-------|-----------|---------------------------------------------------|
| 1     | Pexels    | `https://api.pexels.com/v1/search?query=...`      |
| 2     | Pixabay   | `https://pixabay.com/api/?key=...&q=...`          |
| 3     | Unsplash  | `https://api.unsplash.com/search/photos?query=...` |

### Video search order

| Order | Provider  | API endpoint                                      |
|-------|-----------|---------------------------------------------------|
| 1     | Pexels    | `https://api.pexels.com/videos/search?query=...`  |
| 2     | Pixabay   | `https://pixabay.com/api/videos/?key=...&q=...`   |

Unsplash does not provide videos.

### How the fallback works (step by step)

For each provider, in order:

1. Search the API with the cleaned query.
2. For each result returned, attempt to download the media file.
3. If the download succeeds, return the bytes immediately (first
   successful download wins — remaining providers are never contacted).
4. If the download fails (network error, broken link), try the next
   result from the same provider.
5. If all results from a provider fail or the provider returns no
   results, move to the next provider.
6. If all providers fail, raise `AIProviderError`.

### Concrete example — happy path (Pexels succeeds, others never called)

LLM `visual_description`:
> "Close-up of coarse coffee grounds being measured on a dark surface"

After `_clean_query()`:
> `"Close up of coarse coffee grounds being measured on"`

```
Step 1: Search Pexels
        GET https://api.pexels.com/v1/search?query=Close+up+of+coarse+coffee...
        ↓
        Pexels returns 5 photos: [photo1, photo2, photo3, photo4, photo5]

Step 2: Try to download photo1
        GET https://images.pexels.com/photos/12345/large2x.jpg
        ↓
        SUCCESS → return the image bytes immediately. DONE.
        (photo2-photo5 are never tried, Pixabay is never called, Unsplash is never called)
```

### Concrete example — Pexels empty, Pixabay succeeds

```
Step 1: Search Pexels
        Pexels returns [] (no photos matched "quantum physics lab equipment")
        ↓
        The for-loop has nothing to iterate → falls through

Step 2: Search Pixabay  ← only now reached
        GET https://pixabay.com/api/?key=...&q=quantum+physics+lab+equipment
        ↓
        Pixabay returns 3 photos: [photoA, photoB, photoC]

Step 3: Try to download photoA
        GET https://pixabay.com/get/largeImageURL...
        ↓
        SUCCESS → return image bytes. DONE.
        (Unsplash is never called)
```

### Concrete example — Pexels and Pixabay both fail, Unsplash succeeds

```
Step 1: Search Pexels → returns [] (nothing matched)
Step 2: Search Pixabay → returns [photoA, photoB]
        Try download photoA → network timeout
        Try download photoB → 404 error
        ↓
        All Pixabay downloads failed → falls through

Step 3: Search Unsplash  ← only now reached
        GET https://api.unsplash.com/search/photos?query=...
        ↓
        Unsplash returns 2 photos: [photoX, photoY]

Step 4: Try to download photoX
        SUCCESS → return image bytes. DONE.
```

### Concrete example — all providers fail

```
Step 1: Pexels → [] empty
Step 2: Pixabay → [] empty
Step 3: Unsplash → [] empty
        ↓
        raise AIProviderError("No free stock image found for the prompt")
```

### Visual flow diagram

```
Pexels search
  ├─ got results? → try downloading each one
  │    ├─ 1st download succeeds → RETURN (done, Pixabay/Unsplash never called)
  │    └─ all downloads fail → fall through
  └─ no results → fall through
        ↓
Pixabay search
  ├─ got results? → try downloading each one
  │    ├─ 1st download succeeds → RETURN (done, Unsplash never called)
  │    └─ all downloads fail → fall through
  └─ no results → fall through
        ↓
Unsplash search (images only, not for videos)
  ├─ got results? → try downloading each one
  │    ├─ 1st download succeeds → RETURN
  │    └─ all downloads fail → fall through
  └─ no results → fall through
        ↓
raise AIProviderError
```

### Key takeaway

If Pexels has a mediocre match but Pixabay has a perfect match, you
still get the Pexels result — because Pexels is tried first. There is
no relevance scoring between providers. The only reason to move to the
next provider is if the current one returns **nothing** or **all
downloads fail**.

### Pexels video quality selection

When downloading from Pexels, video files are sorted by resolution
(highest first), and the highest-resolution file that downloads
successfully is used:

```python
files = sorted(files, key=lambda f: f.get("width", 0), reverse=True)
```

### Pixabay video quality selection

Pixabay videos are tried in order: `large` → `medium` → `small`.

## 7. Cost model

| Provider               | Cost   |
|------------------------|--------|
| StockImageProvider     | $0.00  |
| StockVideoProvider     | $0.00  |
| ImagenProvider (AI)    | ~$0.04 per image |
| VeoProvider (AI video) | ~$0.10 per second |

The `AssetDecisionAgent` estimates costs, but the actual cost is
calculated by the provider's `calculate_cost()` method at generation
time.

## 8. Output storage

Generated assets are stored under:

```
storage/projects/<project_id>/
  images/scene_<N>.png      # stock or AI images
  videos/scene_<N>.mp4      # stock or AI videos
  voice/scene_<N>.mp3       # TTS audio
  subtitles/scene_<N>.srt    # subtitle files
```

Each asset is also recorded in the `assets` database table with:
`asset_type`, `storage_ref` (local URI), `generation_status`,
`provider`, `generation_cost_usd`, `quality_score`.

## 9. Key files

| File | Purpose |
|------|---------|
| `src/infrastructure/tasks/workflow_tasks.py` | Asset generation step (line ~983), reads `scene_packages`, calls gateways |
| `src/ai/agents/storyboard/schema.py` | `ScenePackage`, `VisualPlan`, `StoryboardPackage` definitions |
| `src/ai/agents/storyboard/prompts.py` | `ASSET_DECISION_PROMPT` — LLM prompt for asset type decisions |
| `src/ai/agents/storyboard/asset_decision.py` | `AssetDecisionAgent` — decides `asset_type` per scene |
| `src/ai/agents/storyboard/storyboard_visual.py` | `StoryboardVisualAgent` — writes `visual_description` |
| `src/ai/providers/stock.py` | `_StockClient` — Pexels/Pixabay/Unsplash search + download, `_clean_query()` |
| `src/ai/providers/registry.py` | Provider registration order (stock first, then Imagen, then Veo) |
| `src/ai/gateway/image_gateway.py` | `ImageGateway` — calls primary image provider with retry + fallback |
| `src/ai/gateway/video_gateway.py` | `VideoGateway` — calls primary video provider with retry + fallback |
| `src/application/di/container.py` | DI container — wires gateways into `ServiceContainer` |

## 10. Improvement opportunities

1. **Respect the LLM's `asset_type` decision** — currently `ai_image`
   still goes to stock if stock keys are configured. The gateway should
   select the provider based on the requested type.

2. **Score stock results by relevance** — currently the first result
   from the first provider wins. Could score results by matching query
   terms against result tags/description and pick the best match.

3. **Parallel provider search** — currently providers are tried
   sequentially. Could search all providers in parallel and pick the
   best result, reducing latency.

4. **Cache stock results** — the same query may be used across
   workflow reruns. Caching would avoid redundant API calls.

5. **Better query extraction** — `_clean_query()` naively takes the
   first 12 words. A smarter extraction could identify the key
   subject/action and produce a better search query.
