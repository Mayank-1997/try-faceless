# Video Composition Platform & Rendering Engine — Architecture

## Overview

The Video Composition Platform (Phase 10) transforms generated assets from the
Generation Platform (Phase 9) into finished videos. It is **renderer-independent**:
the `CompositionRenderer` abstraction allows swapping FFmpeg for MoviePy, Remotion,
Cloud GPU, or any future renderer without architectural changes.

## Pipeline

```
AssetManifest (Phase 9)
    │
    ▼
CompositionBuilder ──────────► CompositionDocument
    │                              │
    │                              ▼
    │                     CompositionValidator (10 stages)
    │                              │
    │                              ▼
    │                     RenderPlanner ──► RenderPlan
    │                              │
    │                              ▼
    │                     CompositionOptimizer
    │                              │
    │                              ▼
    │                     TimelineCompiler ──► Rendering Instructions
    │                              │
    │                              ▼
    │              ┌─── CompositionRenderer (abstract)
    │              │           │
    │              │     FFmpegCompositionRenderer
    │              │           │
    │              │     FFmpeg Command Builder
    │              │           │
    │              │     FFmpeg Subprocess
    │              │           │
    │              └───────────┘
    │                              │
    │                              ▼
    │                     QualityValidator ──► QualityReport
    │                              │
    │                              ▼
    │                     ExportEngine
    │                              │
    │                              ▼
    └──────────────────────► ProjectPackage
```

## Key Design Decisions

### 1. CompositionDocument as Single Source of Truth

The `CompositionDocument` is the **only** data structure the renderer consumes.
It contains:
- Timeline with unlimited tracks
- Scenes with camera motions and animations
- Transitions between scenes
- Video effects
- Text overlays
- Subtitle configuration
- Audio mixing configuration
- Export profile
- Rendering metadata
- Validation metadata

This decouples the rendering engine from the generation platform — the renderer
never needs to know about `AssetManifest`, `GenerationJob`, or any generation-specific
concepts.

### 2. Renderer Independence

A new `CompositionRenderer` abstract base class (`src/composition/renderer.py`)
defines the renderer contract:
- `load()` — Load a composition document
- `validate()` — Validate for this renderer's capabilities
- `prepare()` — Prepare assets and working directory
- `render()` — Render the video
- `monitor()` — Monitor rendering progress
- `cancel()` — Cancel rendering
- `cleanup()` — Clean up temporary files
- `collect_metrics()` — Collect rendering metrics
- `validate_output()` — Validate the rendered output

This is **separate** from the existing `Renderer` interface in `src/core/interfaces.py`,
which handles low-level operations (merge, concatenate, burn_subtitles). The existing
interface remains unchanged.

### 3. Track System

The `TrackSystem` supports unlimited tracks of any type:
- Video, Image, Voice, Music, Sound Effect, Subtitle, Overlay, Animation, Custom

Tracks are layered by their `layer` property (lower = behind, higher = in front).

### 4. Engine Separation

Each media processing domain has its own engine:
- `CameraMotionEngine` — Pan, zoom, tilt, orbit, Ken Burns, parallax, custom paths
- `ImageAnimationEngine` — Scale, translate, rotate, opacity, crop, depth illusion, parallax, presets
- `TransitionEngine` — Fade, crossfade, slide, push, zoom, blur, dissolve, custom
- `VideoEffectsEngine` — Brightness, contrast, color correction, blur, sharpen, glow, noise reduction, vignette, LUT
- `TextEngine` — Titles, lower thirds, captions, credits, watermarks, callouts, animated text
- `SubtitleEngine` — SRT, VTT, ASS with highlighting, speaker labels, multiple languages
- `AudioMixer` — Voice normalization, music ducking, fade in/out, crossfade, volume balancing
- `MediaSynchronizer` — Ensures all media elements are properly aligned

Each engine generates configuration objects AND translates them to FFmpeg filter
strings, making the renderer's job straightforward.

### 5. Rendering Pipeline

The `RenderingPipeline` orchestrates 13 stages:
1. Load Composition
2. Validate Composition
3. Prepare Assets
4. Compile Timeline
5. Optimize
6. Render (delegated to renderer)
7. Validate Output
8. Generate Project Package

Events are emitted at each stage for real-time progress tracking.

### 6. Render Queue & Progress Tracking

The `RenderQueue` supports:
- Priority-based ordering (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Retry with configurable max retries
- Dead letter queue for permanently failed jobs
- Pause/resume
- Cancellation

The `ProgressTracker` provides:
- Real-time progress updates
- Callback-based subscriptions for WebSockets/SSE
- Per-stage progress tracking

### 7. Render Cache

The `RenderCache` uses a deterministic hash of the `CompositionDocument` to cache
rendered outputs. When the same composition is rendered again, the cached output
is reused. Architecture supports future:
- Scene-level rendering
- Segment rendering
- Incremental rendering

### 8. Preview Engine

The `PreviewEngine` generates low-resolution previews for quick review.
Architecture supports future:
- Timeline previews
- Scene previews
- Audio previews
- Storyboard previews

### 9. Project Package

The `ProjectPackage` is the final output and the contract for future Publishing
modules (Phase 12). It contains:
- CompositionDocument
- Final video path/URI
- Thumbnail path/URI
- Subtitle files
- Timeline
- Waveforms
- Metadata
- Render report
- Quality report
- Performance metrics
- Cost summary

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Video Composition Platform                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Composition   │  │ Composition  │  │  RenderPlanner       │  │
│  │ Builder       │─►│ Validator    │─►│                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                                       │               │
│         ▼                                       ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Composition   │  │ Composition  │  │  TimelineCompiler    │  │
│  │ Document      │─►│ Optimizer    │─►│                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                                       │               │
│         │           ┌──────────────────────────┐│               │
│         │           │  RenderingPipeline       ││               │
│         │           │  ┌────────────────────┐  ││               │
│         └──────────►│  │ CompositionRenderer│  ││               │
│                     │  │   (abstract)       │  ││               │
│                     │  └─────────┬──────────┘  ││               │
│                     │            │             ││               │
│                     │  ┌─────────▼──────────┐  ││               │
│                     │  │FFmpegComposition   │  ││               │
│                     │  │Renderer            │  ││               │
│                     │  └────────────────────┘  ││               │
│                     └──────────────────────────┘│               │
│                                  │               │               │
│                                  ▼               │               │
│                     ┌──────────────────────────┐│               │
│                     │  QualityValidator        ││               │
│                     └──────────────────────────┘│               │
│                                  │               │               │
│                                  ▼               │               │
│                     ┌──────────────────────────┐│               │
│                     │  ExportEngine            ││               │
│                     └──────────────────────────┘│               │
│                                  │               │               │
│                                  ▼               │               │
│                     ┌──────────────────────────┐│               │
│                     │  ProjectPackage          ││               │
│                     └──────────────────────────┘│               │
└─────────────────────────────────────────────────────────────────┘
```

## Engine Diagram

```
┌─────────────────────────────────────────────────┐
│                  Engines                         │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│
│  │ CameraMotion│  │ ImageAnim   │  │Transition││
│  │ Engine      │  │ Engine      │  │ Engine   ││
│  └─────────────┘  └─────────────┘  └──────────┘│
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│
│  │ VideoEffects│  │ Text        │  │ Subtitle ││
│  │ Engine      │  │ Engine      │  │ Engine   ││
│  └─────────────┘  └─────────────┘  └──────────┘│
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│
│  │ AudioMixer  │  │ MediaSync   │  │ Track    ││
│  │             │  │             │  │ System   ││
│  └─────────────┘  └─────────────┘  └──────────┘│
└─────────────────────────────────────────────────┘
```

## Events

| Event | Emitted By | Description |
|-------|-----------|-------------|
| CompositionCreated | CompositionBuilder | Composition document built from AssetManifest |
| CompositionValidated | CompositionValidator | Validation completed (valid/invalid) |
| RenderPlanned | RenderPlanner | Render plan generated with estimates |
| RenderingStarted | RenderingPipeline | Rendering has begun |
| EncodingStarted | FFmpegCompositionRenderer | FFmpeg encoding started |
| EncodingCompleted | FFmpegCompositionRenderer | FFmpeg encoding completed |
| RenderingCompleted | RenderingPipeline | Rendering finished successfully |
| RenderingFailed | RenderingPipeline | Rendering failed |
| ProjectPackageGenerated | RenderingPipeline | Project package created |

## File Structure

```
src/composition/
├── __init__.py              # All exports
├── schema.py                # All Pydantic v2 models and enums
├── events.py                # CompositionEventEmitter + event constants
├── tracks.py                # TrackSystem
├── camera.py                # CameraMotionEngine
├── animation.py             # ImageAnimationEngine
├── transitions.py           # TransitionEngine
├── effects.py               # VideoEffectsEngine
├── text.py                  # TextEngine
├── subtitles.py             # SubtitleEngine
├── audio.py                 # AudioMixer
├── synchronizer.py          # MediaSynchronizer
├── builder.py               # CompositionBuilder
├── validator.py             # CompositionValidator
├── planner.py               # RenderPlanner
├── optimizer.py             # CompositionOptimizer
├── timeline_compiler.py     # TimelineCompiler
├── renderer.py              # CompositionRenderer (abstract)
├── ffmpeg_renderer.py       # FFmpegCompositionRenderer
├── pipeline.py              # RenderingPipeline
├── export.py                # ExportEngine
├── quality.py               # QualityValidator
├── render_cache.py          # RenderCache
├── preview.py               # PreviewEngine
├── render_queue.py          # RenderQueue
└── progress.py              # ProgressTracker
```

## Testing

212 tests in `tests/unit/test_composition_platform.py` covering:
- Schema models, enums, defaults, computed properties
- Track system (create, add, remove, get by type, ordering)
- Camera motion engine (all motion types, FFmpeg filter generation)
- Image animation engine (all animation types, presets, FFmpeg filter generation)
- Transition engine (all transition types, xfade filter generation)
- Video effects engine (all effect types, FFmpeg filter generation)
- Text engine (all text types, drawtext filter generation)
- Subtitle engine (SRT/VTT generation, config, FFmpeg filter)
- Audio mixer (voice/music/SFX tracks, normalization, ducking, fading, amix)
- Media synchronizer (voice-visual sync, alignment, audio sync check)
- Composition builder (manifest to document, tracks, scenes, transitions, animations)
- Composition validator (10 validation stages, errors, warnings)
- Render planner (estimates, bottlenecks, suggestions, parallelizable detection)
- Composition optimizer (layer ordering, animation cleanup, audio trim, asset sorting)
- Timeline compiler (overlap resolution, timestamps, instructions, scene data)
- FFmpeg renderer (command building, URI conversion, validation, metrics)
- Rendering pipeline (progress tracking)
- Export engine (presets, custom profiles, preview profiles, metadata)
- Quality validator (resolution, duration, dropped frames, encoding, integrity)
- Render cache (hash, put/get, hit rate, eviction, invalidation)
- Preview engine (profile creation, time/size estimation)
- Render queue (priority, retry, dead letter, pause/resume, cancel)
- Progress tracker (register, update, subscribe, unsubscribe)
- Events (all 9 event types)
- Integration (full pipeline: build → validate → plan → optimize → compile)
