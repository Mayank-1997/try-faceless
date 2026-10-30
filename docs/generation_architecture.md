# Generation Platform Architecture

## Phase 9 — Generation Platform & Intelligent Asset Generation

## Overview

The Generation Platform is the centralized execution engine for all media generation. It transforms storyboard decisions into production-ready media assets through a pipeline of strategy selection, queueing, provider selection, execution, validation, and manifest building.

**Key Principle:** AI agents never call providers directly. All media generation flows through this platform.

## High-Level Architecture

```
Storyboard
    ↓
GenerationStrategyEngine
    ↓
GenerationOrchestrator
    ↓
QueueManager
    ↓
ProviderSelectionEngine ←→ ProviderHealthMonitor
    ↓
BudgetManager (check/enforce)
    ↓
ConcurrencyManager (acquire slots)
    ↓
CacheManager (dedup check)
    ↓
GenerationExecutor (ONLY component calling providers)
    ↓
ValidationPipeline (10 stages)
    ↓
QualityEngine (multi-dimension scoring)
    ↓
AssetManifestBuilder
    ↓
AssetManifest → Phase 10 Rendering Engine
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GenerationOrchestrator                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ Strategy  │  │  Queue    │  │ Provider  │  │  Budget   │    │
│  │  Engine   │  │ Manager   │  │ Selection │  │  Manager  │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ Concurrency│  │  Health   │  │  Cache    │  │ Executor  │    │
│  │  Manager  │  │  Monitor  │  │  Manager  │  │           │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                    │
│  │ Validation│  │  Quality  │  │  Manifest │                    │
│  │  Pipeline │  │  Engine   │  │  Builder  │                    │
│  └───────────┘  └───────────┘  └───────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
                    ┌─────────────────┐
                    │   Event Bus     │
                    │ (9 event types) │
                    └─────────────────┘
```

## Generation Strategy Engine

### Strategy Modes

| Mode | Resolution | Image/Video Ratio | Max Cost | Concurrency | Quality Threshold |
|------|-----------|-------------------|----------|-------------|-------------------|
| Economy | 1280x720 | 0.9 | $2.00 | 2 | 0.5 |
| Balanced | 1920x1080 | 0.7 | $10.00 | 4 | 0.7 |
| Premium | 3840x2160 | 0.4 | $50.00 | 6 | 0.9 |
| Fast | 1280x720 | 0.95 | $5.00 | 8 | 0.5 |
| Custom | User-defined | User-defined | User-defined | User-defined | User-defined |

### Strategy Parameters

Each strategy controls:
- **Image vs Video ratio** — Higher ratio = more images (cheaper, faster)
- **Provider selection** — Preferred providers per asset category
- **Model selection** — Preferred models per asset category
- **Resolution** — Output resolution (720p, 1080p, 4K)
- **Retry policy** — Maximum retry attempts
- **Concurrency** — Maximum parallel jobs
- **Maximum cost** — Budget ceiling per project
- **Quality threshold** — Minimum acceptable quality score
- **Execution priority** — Queue priority level
- **Caching** — Enable/disable deduplication
- **Fallback** — Enable/disable provider fallback

## Queue Flow

```
                    ┌──────────┐
                    │  Submit  │
                    └────┬─────┘
                         ↓
                    ┌──────────┐
                    │ Priority │
                    │  Queue   │
                    └────┬─────┘
                         ↓
                    ┌──────────┐
               ┌───→│ Dequeue  │───→ Cancelled?
               │    └──────────┘        ↓ Yes
               │         │         [Cancelled]
               │         ↓ No
               │    ┌──────────┐
               │    │ Execute  │
               │    └────┬─────┘
               │         │
               │    ┌────↓─────┐
               │    │ Success? │
               │    └────┬─────┘
               │    Yes  │  No
               │    ┌────┘  └────┐
               │    ↓            ↓
               │ [Completed]  ┌────────┐
               │              │ Retry? │
               │              └───┬────┘
               │             Yes  │  No
               │             ┌────┘  └────┐
               └─────────────┘           ↓
                                   [Dead Letter]
```

### Queue Types

- **Priority Queue** — Jobs ordered by priority (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
- **Retry Queue** — Failed jobs awaiting retry with backoff
- **Dead Letter Queue** — Permanently failed jobs (exceeded max retries)
- **Cancellation Queue** — Jobs marked for cancellation before execution

## Provider Selection Flow

```
                    ┌──────────────┐
                    │   Request    │
                    │ (category)   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  Get all     │
                    │  providers   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Filter out   │
                    │ unhealthy    │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Score each   │
                    │ provider     │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Select best  │
                    │ score        │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Return       │
                    │ (name, model,│
                    │  cost)       │
                    └──────────────┘
```

### Scoring Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| Cost | 0.25 | Lower cost = higher score |
| Latency | 0.15 | Lower latency = higher score |
| Availability | 0.30 | Higher availability = higher score |
| Quality | 0.20 | Higher quality = higher score |
| Preference | 0.10 | Strategy-preferred provider bonus |

### Fallback Chain

When the primary provider fails, the next healthy provider in the chain is tried automatically. The chain is ordered by composite score.

## Execution Flow

```
┌──────────────────────────────────────────────────────────┐
│                   GenerationExecutor                      │
│                                                          │
│  1. Check Cache                                          │
│     ├─ Hit → Return cached asset                         │
│     └─ Miss → Continue                                   │
│                                                          │
│  2. Acquire Concurrency Slots                            │
│     ├─ Global semaphore                                  │
│     ├─ Provider semaphore                                │
│     └─ Project semaphore                                 │
│                                                          │
│  3. Call Provider (via existing gateways)                │
│     ├─ Image → ImageGateway.generate_image()             │
│     ├─ Video → VideoGateway.generate_video()             │
│     ├─ Voice → VoiceGateway.generate_speech()            │
│     ├─ Music/SFX → Framework only                        │
│     └─ Subtitle/Thumbnail → Internal generator           │
│                                                          │
│  4. Record Health Metrics                                │
│     ├─ Success → record_success(latency, cost, quality)  │
│     └─ Failure → record_failure(timeout?)                │
│                                                          │
│  5. Upload to Storage                                    │
│     └─ StorageGateway.upload(bytes, key)                 │
│                                                          │
│  6. Cache Result                                         │
│     └─ CacheManager.put(key, asset)                      │
│                                                          │
│  7. Emit Events                                          │
│     ├─ GenerationStarted                                 │
│     ├─ GenerationCompleted                               │
│     ├─ GenerationFailed                                  │
│     └─ AssetStored                                       │
│                                                          │
│  8. Release Concurrency Slots                            │
└──────────────────────────────────────────────────────────┘
```

## Validation Pipeline

Every generated asset must pass through 10 validation stages:

```
Asset → ┌────────────────────────────────────────────┐
        │ 1. File Validation (size > 0, < max)       │
        │ 2. Metadata Validation (provider, model)   │
        │ 3. Resolution Validation (≥ minimum)       │
        │ 4. Duration Validation (within bounds)     │
        │ 5. Prompt Alignment (non-empty prompt)     │
        │ 6. Quality Evaluation (≥ threshold)        │
        │ 7. Duplicate Detection (content hash)      │
        │ 8. Storage Validation (URI present)        │
        │ 9. Content Safety (moderation check)       │
        │ 10. Overall Validation (all stages pass)   │
        └────────────────────────────────────────────┘
                    ↓
              ┌──────────┐
              │  Valid?  │
              └────┬─────┘
           Yes     │     No
           ↓       └────↓
        [Accept]   [Reject + Emit ValidationFailed]
```

## Quality Evaluation

### Dimensions

| Dimension | Description |
|-----------|-------------|
| Visual Quality | Image/video visual fidelity |
| Prompt Alignment | How well output matches prompt |
| Voice Quality | Audio clarity and naturalness |
| Subtitle Accuracy | Timestamp and text correctness |
| Consistency | Cross-scene visual consistency |
| Brand Compliance | Adherence to brand guidelines |
| **Overall Score** | Weighted composite (category-specific) |

### Category-Specific Weights

| Category | Visual | Prompt | Voice | Subtitle | Consistency | Brand |
|----------|--------|--------|-------|----------|-------------|-------|
| Image | 0.40 | 0.30 | — | — | 0.20 | 0.10 |
| Video | 0.35 | 0.25 | 0.10 | — | 0.20 | 0.10 |
| Voice | — | 0.20 | 0.50 | — | 0.15 | 0.15 |
| Subtitle | — | 0.20 | — | 0.50 | 0.15 | 0.15 |
| Thumbnail | 0.40 | 0.30 | — | — | — | 0.30 |

## Asset Manifest Schema

### SceneAssetManifest

```json
{
  "scene_id": "sc1",
  "scene_number": 1,
  "image": { "id": "...", "storage_uri": "local:///...", "cost_usd": 0.04 },
  "video": null,
  "voice": { "id": "...", "storage_uri": "local:///...", "cost_usd": 0.01 },
  "music": null,
  "subtitles": { "id": "...", "storage_uri": "local:///...", "cost_usd": 0.0 },
  "effects": [],
  "estimated_render_time_seconds": 15.0,
  "estimated_scene_cost": 0.05,
  "dependencies": [],
  "generation_status": "completed"
}
```

### AssetManifest (Project-Level)

```json
{
  "id": "uuid",
  "project_id": "proj1",
  "scene_manifests": [ ... ],
  "total_duration_seconds": 300.0,
  "total_cost": 2.50,
  "total_assets": 15,
  "estimated_rendering_time_seconds": 150.0,
  "version": 1,
  "is_complete": true
}
```

The Rendering Engine (Phase 10) consumes **only** the `AssetManifest`.

## Budget Management

### Budget Enforcement Flow

```
Request → Estimate Cost → Check Budget
                            ├─ Affordable → Proceed
                            └─ Not Affordable
                                 ├─ Recommend Downgrade (Video → Image)
                                 │   └─ Downgrade accepted → Re-estimate
                                 └─ Reject + Emit BudgetExceeded
```

### Budget Tracking Levels

- **Project level** — Total spend vs total budget
- **Scene level** — Per-scene cost accumulation
- **Category level** — Per-category spend (image, video, voice, etc.)

## Concurrency Management

### Limits

| Level | Default | Description |
|-------|---------|-------------|
| Global | 4 workers | Maximum concurrent jobs across all providers |
| Provider | 2 per provider | Respect provider rate limits |
| Project | 3 per project | Fairness across projects |
| Daily quota | 1000 jobs | Maximum jobs per day |
| Monthly quota | 20000 jobs | Maximum jobs per month |

### Adaptive Throttling

When provider failure rate exceeds 30%, concurrency is halved to avoid overwhelming providers.

## Cache Management

### Cache Key Composition

```
SHA-256(prompt | provider | model | aspect_ratio | resolution |
        duration_seconds | seed | style | prompt_version)
```

### Cache Behavior

- **Hit** — Return cached asset, skip provider call, cost = $0
- **Miss** — Call provider, cache result for future requests
- **TTL** — 24 hours (configurable)
- **Eviction** — LRU when cache is full (default 1000 entries)

## Events

| Event | Source | Description |
|-------|--------|-------------|
| GenerationStarted | Executor | Job execution started |
| GenerationCompleted | Executor | Asset successfully generated |
| GenerationFailed | Executor | Job failed after all retries |
| RetryTriggered | Executor | Job queued for retry |
| ProviderChanged | ProviderSelection | Fallback to alternate provider |
| BudgetExceeded | BudgetManager | Budget limit reached |
| AssetStored | Executor | Asset uploaded to storage |
| ValidationFailed | ValidationPipeline | Asset rejected by validation |
| ManifestCompleted | ManifestBuilder | Final manifest assembled |

## State Management

### WorkflowState Extensions

- `AssetData` — Extended with `storage_uri`, `content_hash`, `checksum`, `version`, `generation_metadata`
- `RenderingData` — Extended with `metadata` for manifest storage

## Testing

### Test Coverage (142 tests)

| Test Suite | Tests | Coverage |
|-----------|-------|----------|
| Schemas | 22 | All enums, models, defaults, computed properties |
| Strategy Engine | 10 | All modes, custom strategies, overrides |
| Queue Manager | 9 | Priority, cancel, retry, dead letter, pause/resume |
| Health Monitor | 9 | Success/failure recording, auto-disable, quotas |
| Provider Selection | 7 | Scoring, unhealthy skip, preference, fallback |
| Budget Manager | 9 | Set/check/estimate, downgrade, per-scene tracking |
| Concurrency | 8 | Acquire/release, quotas, limits |
| Cache Manager | 7 | Put/get, hit rate, eviction, invalidation |
| Validation Pipeline | 6 | Valid/invalid assets, all rejection stages |
| Quality Engine | 7 | All categories, batch, project quality |
| Executor | 5 | Image/video/voice/subtitle, cache hit |
| Orchestrator | 5 | Submit, batch, cancel, progress, scene assets |
| Manifest Builder | 5 | Empty, with assets, durations, completeness |
| Subtitle Generator | 7 | SRT/VTT, time format, wrapping, sentences |
| Thumbnail Generator | 6 | Prompt, variations, clickability, no-text |
| Events | 10 | All 9 event types + constants |
| Integration | 3 | Full pipeline, budget downgrade, caching |

## File Structure

```
src/generation/
├── __init__.py              # All exports
├── schema.py                # All Pydantic v2 models and enums
├── events.py                # GenerationEventEmitter + 9 event types
├── strategy.py              # GenerationStrategyEngine
├── queue_manager.py         # QueueManager
├── provider_selection.py    # ProviderSelectionEngine
├── health.py                # ProviderHealthMonitor
├── budget.py                # BudgetManager
├── concurrency.py           # ConcurrencyManager
├── cache.py                 # CacheManager
├── executor.py              # GenerationExecutor
├── validation.py            # ValidationPipeline
├── quality.py               # QualityEngine
├── orchestrator.py          # GenerationOrchestrator
├── manifest.py              # AssetManifestBuilder
├── subtitle.py              # SubtitleGenerator
└── thumbnail.py             # ThumbnailGenerator
```
