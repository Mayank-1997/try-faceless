# Publishing & Distribution Platform — Architecture

## Overview

The Publishing & Distribution Platform (Phase 11) distributes generated content
to multiple destinations. It is **provider-independent**: the `Publisher`
abstraction allows adding YouTube, LinkedIn, Medium, WordPress, Twitter/X,
Facebook, Instagram, TikTok, Podcast, and future publishers without
architectural changes.

## Pipeline

```
ProjectPackage (Phase 10)
    │
    ▼
PublishingPlanner ──────────► PublishingPlan
    │                              │
    │                              ▼
    │                     PublishingStrategyEngine
    │                              │
    │                              ▼
    │                     PublishingQueue
    │                              │
    │                              ▼
    │              ┌─── Publisher (abstract)
    │              │           │
    │              │     YouTubePublisher
    │              │     LinkedInPublisher (future)
    │              │     MediumPublisher (future)
    │              │     WordPressPublisher (future)
    │              │     TwitterPublisher (future)
    │              │     FacebookPublisher (future)
    │              │     InstagramPublisher (future)
    │              │     TikTokPublisher (future)
    │              │     PodcastPublisher (future)
    │              │           │
    │              └───────────┘
    │                              │
    │                              ▼
    │                     PublishingValidator
    │                              │
    │                              ▼
    │                     PublishingReport
    │                              │
    │                              ▼
    └──────────────────────► ProjectPackage + Report
```

## Key Design Decisions

### 1. Publisher Interface

A new `Publisher` abstract base class (`src/publishing/publisher.py`) defines
the publisher contract:
- `authenticate()` — Authenticate with the platform
- `validate()` — Validate assets and metadata for this platform
- `prepare()` — Prepare assets for upload
- `publish()` — Publish the video
- `schedule()` — Schedule publishing for a future time
- `cancel()` — Cancel a scheduled or in-progress publish
- `monitor()` — Monitor publishing progress
- `collect_metrics()` — Collect publishing metrics

New platforms are added by implementing this interface. No other code changes
are needed.

### 2. PublishingPlanner as Entry Point

The `PublishingPlanner` consumes a `ProjectPackage` (from Phase 10) and
produces a `PublishingPlan` with:
- One `PublishingTask` per target platform
- Platform-optimized metadata (title, description, tags, hashtags, SEO)
- Thumbnail specifications per platform
- Estimated publishing time
- Validation errors and warnings

### 3. PublishingStrategyEngine

Provides 8 preset strategies and custom strategy creation:
- **immediate** — Publish now to YouTube
- **scheduled** — Schedule for a future time
- **draft** — Save as draft for review
- **manual_approval** — Require manual approval before publishing
- **multi_platform** — Publish to multiple platforms simultaneously
- **youtube_only** — YouTube with aggressive retries
- **conservative** — Draft mode with minimal retries
- **aggressive** — Multi-platform with many retries

Retry strategies: exponential backoff, linear backoff, fixed delay, none.
Failover strategies: skip failed, retry on alternative, abort all.

### 4. AuthenticationManager

Manages authentication credentials for all platforms:
- OAuth2 token exchange
- API key authentication
- Refresh token management
- Credential storage and retrieval
- Multi-user support
- Automatic token refresh

### 5. MetadataEngine

Generates platform-optimized metadata:
- Title truncation to platform limits
- Description optimization
- Tag generation from keywords
- Hashtag generation (platform-specific: Instagram 30, others 10)
- SEO metadata (OpenGraph, Twitter Cards)
- Platform-specific metadata (YouTube category, LinkedIn visibility, etc.)

Platform limits are hardcoded for YouTube, LinkedIn, Medium, WordPress,
Twitter/X, Facebook, Instagram, TikTok, and Podcast.

### 6. ThumbnailManager

Validates and manages thumbnails per platform:
- Platform-specific specs (dimensions, format, max size)
- Validation (file exists, size, format)
- Variant path generation
- Metadata generation
- Supports YouTube (1280×720), Instagram (1080×1080), TikTok (1080×1920),
  Podcast (3000×3000), and more

### 7. PublishingValidator

8 validation stages:
1. Video format (file exists, size, extension)
2. Thumbnail (exists, size, format, required vs optional)
3. Metadata (title, description, tags)
4. Title length (platform-specific limits)
5. Description limits (platform-specific)
6. Platform requirements (tag count, tag length)
7. Authentication (warnings for missing credentials)
8. Scheduling (future time validation)

### 8. PublishingQueue

Priority-based async queue with:
- Priority ordering (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Retry with configurable max retries and strategies
- Dead letter queue for permanently failed jobs
- Pause/resume
- Cancellation (active or queued)

Architecture supports future distributed workers.

### 9. SchedulingEngine

Supports:
- Immediate publish
- Specific date/time with timezone awareness
- Due task detection
- Schedule cancellation
- Architecture for future recurring publishing and campaign scheduling

### 10. ProgressTracker

Tracks 8 stages:
- Queued, Uploading, Thumbnail upload, Metadata update,
  Publishing, Completed, Failed, Cancelled

Callback-based subscriptions for real-time updates via WebSockets/SSE.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                Publishing & Distribution Platform                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Publishing    │  │ Strategy     │  │  Authentication      │  │
│  │ Planner       │─►│ Engine       │  │  Manager             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                │                       │              │
│         ▼                ▼                       │              │
│  ┌──────────────┐  ┌──────────────┐             │              │
│  │ Publishing    │  │ Publishing   │             │              │
│  │ Plan          │─►│ Queue        │             │              │
│  └──────────────┘  └──────────────┘             │              │
│         │                │                       │              │
│         │           ┌────▼──────────┐            │              │
│         │           │  Publisher    │────────────┘              │
│         │           │  (abstract)   │                           │
│         │           └────┬──────────┘                           │
│         │                │                                      │
│         │     ┌──────────▼──────────┐                          │
│         │     │  YouTubePublisher   │                          │
│         │     │  LinkedInPublisher  │ (future)                 │
│         │     │  MediumPublisher    │ (future)                 │
│         │     │  ...                │                          │
│         │     └─────────────────────┘                          │
│         │                │                                      │
│         │           ┌────▼──────────┐                           │
│         │           │  Validator    │                           │
│         │           └────┬──────────┘                           │
│         │                │                                      │
│         │           ┌────▼──────────┐                           │
│         │           │  Publishing   │                           │
│         │           │  Report       │                           │
│         │           └───────────────┘                           │
│         │                                                      │
│  ┌──────▼──────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Metadata     │  │ Thumbnail    │  │  Scheduling Engine   │  │
│  │ Engine       │  │ Manager      │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────┐                                               │
│  │ Progress     │                                               │
│  │ Tracker      │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## YouTube Publishing Flow

```
1. PublishingPlanner.plan()
   ├── Validate ProjectPackage
   ├── Generate metadata (MetadataEngine)
   ├── Get thumbnail spec (ThumbnailManager)
   └── Create PublishingTask

2. PublishingQueue.submit()
   └── Task queued with priority

3. PublishingQueue.dequeue()
   └── Task becomes active

4. YouTubePublisher.authenticate()
   └── OAuth2 token exchange

5. YouTubePublisher.validate()
   └── Validate video, thumbnail, metadata

6. YouTubePublisher.prepare()
   ├── Set default category (Education)
   ├── Set default license (youtube)
   └── Set default privacy (private)

7. YouTubePublisher.publish()
   ├── Upload video (with progress tracking)
   ├── Upload thumbnail (if provided)
   ├── Update metadata
   └── Set privacy status

8. PublishingReport generated
   ├── Video URL
   ├── Upload duration
   ├── Provider response
   └── Warnings/errors
```

## Events

| Event | Emitted By | Description |
|-------|-----------|-------------|
| PublishingPlanned | PublishingPlanner | Publishing plan generated |
| PublishingStarted | Publisher | Publishing has begun |
| UploadProgress | Publisher | Upload progress update |
| PublishingCompleted | Publisher | Publishing finished successfully |
| PublishingFailed | Publisher | Publishing failed |
| RetryTriggered | PublishingQueue | Job retried after failure |
| ScheduleCreated | SchedulingEngine | Schedule created for future publish |
| DraftSaved | Publisher | Draft saved for review |

## File Structure

```
src/publishing/
├── __init__.py          # All exports
├── schema.py            # All Pydantic v2 models and enums
├── events.py            # PublishingEventEmitter + event constants
├── publisher.py         # Publisher (abstract base class)
├── auth.py              # AuthenticationManager
├── metadata.py          # MetadataEngine
├── thumbnail.py         # ThumbnailManager
├── validator.py         # PublishingValidator
├── youtube.py           # YouTubePublisher
├── planner.py           # PublishingPlanner
├── strategy.py          # PublishingStrategyEngine
├── queue.py             # PublishingQueue
├── scheduler.py         # SchedulingEngine
└── progress.py          # ProgressTracker
```

## Future Publishers

Adding a new publisher requires only:
1. Implement the `Publisher` ABC
2. Add platform-specific requirements to `PublishingValidator`
3. Add thumbnail spec to `ThumbnailManager`
4. Add metadata limits to `MetadataEngine`

No changes to planner, queue, scheduler, or strategy engine.

### Planned Future Publishers

| Platform | Auth Method | Key Features |
|----------|------------|--------------|
| LinkedIn | OAuth2 | Video posts, article publishing |
| Medium | API Key | Article publishing with embedded video |
| WordPress | OAuth2/Basic | Blog post with embedded video |
| Twitter/X | OAuth2 | Short video posts, threads |
| Facebook | OAuth2 | Video posts, page publishing |
| Instagram | OAuth2 | Reels, stories, grid posts |
| TikTok | OAuth2 | Video uploads with effects |
| Podcast | API Key | Audio extraction and RSS feed |

## Testing

167 tests in `tests/unit/test_publishing_platform.py` covering:
- Schema models, enums, defaults, computed properties
- Authentication manager (OAuth2, API key, refresh, store, delete, validate)
- Metadata engine (generation, truncation, hashtags, SEO, validation)
- Thumbnail manager (specs, validation, variants, metadata)
- Publishing validator (video, thumbnail, metadata, title, description, platform, auth, scheduling)
- YouTube publisher (authenticate, validate, prepare, publish, schedule, cancel, monitor, metrics)
- Publishing planner (plan generation, multi-platform, metadata, thumbnail specs, scheduling)
- Strategy engine (presets, custom strategies, validation, retry delays)
- Publishing queue (priority, retry, dead letter, pause/resume, cancel)
- Scheduling engine (immediate, scheduled, draft, due tasks, cancellation)
- Progress tracker (register, update, subscribe, unsubscribe)
- Events (all 8 event types)
- Publisher interface (abstract class, isinstance check)
- Integration (full planning pipeline, full publishing pipeline, multi-platform, scheduled, queue+progress)
