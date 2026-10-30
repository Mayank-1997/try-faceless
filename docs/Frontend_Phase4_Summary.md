# Phase 4: Video Production Experience — Summary

## Overview

Phase 4 implements the Video Production Experience, covering three major subsystems:
1. **Timeline Editor** — Composition management and timeline visualization
2. **Render Queue** — Submit, monitor, and manage render jobs
3. **Publishing** — Create publishing plans, execute, and track publishing to YouTube

---

## Backend Changes

### New Files

#### `backend/src/application/services/production_service.py`
- `ProductionService` class bridging composition, rendering, and publishing subsystems
- Response models: `CompositionResponse`, `RenderJobResponse`, `RenderProgressResponse`, `ProjectPackageResponse`, `PreviewResponse`, `PublishingPlanResponse`, `PublishingJobResponse`, `PublishingReportResponse`, `MessageResponse`
- Composition operations: `build_composition`, `get_composition`, `get_project_composition`, `update_timeline`
- Render operations: `submit_render`, `cancel_render`, `list_renders`, `get_render_progress`, `get_project_package`, `generate_preview`
- Publishing operations: `create_publishing_plan`, `get_publishing_plan`, `list_publishing_plans`, `execute_publishing`, `cancel_publishing`, `list_publishing_jobs`, `get_publishing_reports`
- Uses in-memory stores for compositions, project packages, render progress, publishing plans, and reports
- Leverages existing `CompositionBuilder`, `CompositionValidator`, `RenderingPipeline`, `ExportEngine`, `PreviewEngine`, `RenderQueue`, `PublishingQueue`

#### `backend/src/presentation/routers/production.py`
- REST API router with prefix `/projects` (nested under project resources)
- All endpoints require authentication via `require_authentication`
- **Composition endpoints**:
  - `POST /{project_id}/composition` — Build composition
  - `GET /{project_id}/composition` — Get project composition
  - `GET /{project_id}/composition/{composition_id}` — Get composition by ID
  - `PATCH /{project_id}/composition/{composition_id}/timeline` — Update timeline
- **Render endpoints**:
  - `POST /{project_id}/renders` — Submit render job
  - `GET /{project_id}/renders` — List render jobs
  - `GET /{project_id}/renders/{job_id}` — Get render job
  - `GET /{project_id}/renders/{job_id}/progress` — Get render progress
  - `POST /{project_id}/renders/{job_id}/cancel` — Cancel render job
- **Preview endpoints**:
  - `POST /{project_id}/composition/{composition_id}/preview` — Generate preview
- **Project Package endpoints**:
  - `GET /{project_id}/package` — Get final project package
- **Publishing endpoints**:
  - `POST /{project_id}/publishing/plans` — Create publishing plan
  - `GET /{project_id}/publishing/plans` — List publishing plans
  - `GET /{project_id}/publishing/plans/{plan_id}` — Get publishing plan
  - `POST /{project_id}/publishing/plans/{plan_id}/execute` — Execute publishing plan
  - `GET /{project_id}/publishing/jobs` — List publishing jobs
  - `POST /{project_id}/publishing/jobs/{job_id}/cancel` — Cancel publishing job
  - `GET /{project_id}/publishing/reports` — List publishing reports

### Modified Files

#### `backend/src/presentation/main.py`
- Added import for `production_router`
- Registered `production_router` with API prefix

---

## Frontend Changes

### Shared Types (`frontend/packages/shared-types/src/business-dto.ts`)
Added Phase 4 DTOs:
- **Composition**: `TimelineClipDTO`, `TrackDTO`, `TimelineDTO`, `CompositionSceneDTO`, `ExportProfileDTO`, `CompositionDocumentDTO`, `CreateCompositionRequest`, `UpdateTimelineRequest`
- **Rendering**: `RenderJobDTO`, `RenderProgressDTO`, `RenderMetricsDTO`, `QualityReportDTO`, `ProjectPackageDTO`, `CreateRenderRequest`, `PreviewResultDTO`
- **Publishing**: `PublishingMetadataDTO`, `PublishingTaskDTO`, `PublishingPlanDTO`, `PublishingReportDTO`, `PublishingJobDTO`, `PublishingProgressDTO`, `CreatePublishingRequest`, `SchedulePublishRequest`

### SDK Module (`frontend/packages/platform-sdk/src/modules/production.ts`)
- `ProductionSDK` class with methods for all composition, render, and publishing API calls
- Wired into `PlatformSDK` class as `sdk.production`

### React Query Hooks (`frontend/packages/platform-sdk/src/hooks/production-hooks.ts`)
- `productionKeys` query key factory
- **Composition**: `useComposition`, `useBuildComposition`, `useUpdateTimeline`
- **Rendering**: `useRenders`, `useRenderProgress` (auto-polling every 2s until terminal), `useSubmitRender`, `useCancelRender`
- **Preview**: `useGeneratePreview`
- **Package**: `useProjectPackage`
- **Publishing**: `usePublishingPlans`, `usePublishingJobs`, `usePublishingReports`, `useCreatePublishingPlan`, `useExecutePublishing`, `useCancelPublishingJob`

### Icons (`frontend/packages/icons/src/index.ts`)
- Added: `SplitSquareHorizontal`, `Combine`, `Gauge`, `UploadCloud`, `CalendarClock`

### Frontend Pages

#### Timeline Editor (`frontend/apps/web/src/app/(workspace)/projects/[id]/timeline/page.tsx`)
- Build composition with export preset selection (1080p, 1440p, 4k, square, portrait)
- Display composition metadata: version, track count, duration, resolution
- Validation status indicator
- Scene overview cards with timing and visual descriptions
- Timeline visualization with track types (video, image, voice, music, SFX, subtitles, overlays, animation)
- Track properties: muted, locked, hidden
- Clip visualization with proportional positioning on time ruler
- Export profile display (format, resolution, codec, bitrate)
- Preview generation button
- Navigation to rendering page

#### Render Queue (`frontend/apps/web/src/app/(workspace)/projects/[id]/rendering/page.tsx`)
- Submit render jobs with priority selection (critical, high, normal, low, background)
- Real-time status updates via WebSocket (`realtimeProvider`)
- Active render progress card with stage tracking, frame count, ETA
- Stats cards: queued, running, completed, failed
- Job list with status badges, retry count, execution time, error messages
- Cancel running jobs
- Download completed renders
- Project package display with quality report
- Navigation to timeline and publishing pages

#### Publishing (`frontend/apps/web/src/app/(workspace)/projects/[id]/publishing/page.tsx`)
- Create publishing plan form: title, description, tags, privacy status, mode (immediate/scheduled)
- Character count validation for title (100) and description (5000)
- Scheduled publishing with datetime picker
- Publishing plans list with validation errors and task details
- Execute publishing plans
- Publishing jobs list with real-time status updates via WebSocket
- Cancel active publishing jobs
- Publishing reports with upload duration, video URL, thumbnail/metadata status
- Direct link to published video on YouTube
- Navigation back to rendering and project pages

### Project Detail Page (`frontend/apps/web/src/app/(workspace)/projects/[id]/page.tsx`)
- Added navigation tabs for Timeline, Rendering, and Publishing
- Imported `Layers`, `Film`, `Youtube` icons

---

## Architecture Notes

- The `ProductionService` uses in-memory stores as a placeholder for database persistence
- The service leverages existing backend subsystems: `CompositionBuilder`, `CompositionValidator`, `RenderingPipeline`, `ExportEngine`, `PreviewEngine`, `RenderQueue`, `PublishingQueue`
- The production router is nested under `/projects/{project_id}/` following the existing RESTful pattern
- Real-time updates use the existing `realtimeProvider` from `@ai-video-studio/platform-kernel`
- Render progress polling auto-stops when jobs reach terminal states (completed, failed, cancelled)
- All endpoints require authentication via `require_authentication` dependency
