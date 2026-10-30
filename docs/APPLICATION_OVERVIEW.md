# AI Video Studio — Application Overview

> Autonomous AI-powered YouTube Content Studio — full-stack application for end-to-end automated video content generation, rendering, and publishing.

---

## Table of Contents

- [Architecture Summary](#architecture-summary)
- [Backend Functionalities](#backend-functionalities)
  - [Authentication & Authorization](#authentication--authorization)
  - [User Management](#user-management)
  - [API Key Management](#api-key-management)
  - [Session Management](#session-management)
  - [Project Management](#project-management)
  - [Workflow Engine](#workflow-engine)
  - [AI Agents — Research, Script, Storyboard](#ai-agents--research-script-storyboard)
  - [Content Generation Pipeline](#content-generation-pipeline)
  - [Video Composition & Timeline](#video-composition--timeline)
  - [Rendering](#rendering)
  - [Publishing to YouTube](#publishing-to-youtube)
  - [Platform Analytics & Cost Tracking](#platform-analytics--cost-tracking)
  - [Billing & Subscriptions](#billing--subscriptions)
  - [Organizations & Teams](#organizations--teams)
  - [Feature Flags](#feature-flags)
  - [Admin & Monitoring](#admin--monitoring)
- [Frontend UI Pages](#frontend-ui-pages)
  - [Public / Auth Pages](#public--auth-pages)
  - [Workspace Pages](#workspace-pages)
  - [Project Sub-Pages](#project-sub-pages)
- [Tech Stack](#tech-stack)

---

## Architecture Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy (async), Alembic, Redis |
| Frontend | Next.js (App Router), React, TypeScript, TailwindCSS |
| Monorepo | Frontend uses Turborepo with shared packages (design-system, platform-sdk, platform-kernel, icons, shared-types, shared-utils, theme) |
| AI Providers | Gemini (LLM), VEO (Video), Imagen (Images), Google TTS / ElevenLabs (Voice) |
| Rendering | FFmpeg-based composition and rendering pipeline |
| Publishing | YouTube Data API |
| Infrastructure | Docker, Docker Compose |

---

## Backend Functionalities

### Authentication & Authorization

**Router:** `@/backend/src/presentation/routers/auth.py`

- **Register** — `POST /auth/register` — Create a new user account with email verification
- **Login** — `POST /auth/login` — Authenticate with email/password, returns access + refresh tokens
- **Token Refresh** — `POST /auth/refresh` — Refresh expired access tokens
- **Logout** — `POST /auth/logout` — Revoke current session and refresh token
- **Logout All** — `POST /auth/logout-all` — Revoke all sessions for the user
- **Forgot Password** — `POST /auth/forgot-password` — Generate password reset token
- **Reset Password** — `POST /auth/reset-password` — Reset password using reset token
- **Verify Email** — `POST /auth/verify-email` — Verify email with verification token
- **Resend Verification** — `POST /auth/resend-verification` — Resend email verification

**Supporting services:**
- `AuthenticationService` — orchestrates login, registration, token lifecycle
- `PasswordService` — password hashing and verification (bcrypt)
- `TokenService` — JWT access/refresh token generation and validation
- `AuthorizationService` — role-based access control (RBAC), `require_authentication` dependency
- `RoleService` — role and permission management with default seeder

### User Management

**Router:** `@/backend/src/presentation/routers/users.py`

- **Get Current User** — `GET /users/me` — Get authenticated user's profile
- **Update Profile** — `PATCH /users/me` — Update name, username, avatar
- **Change Password** — `PATCH /users/password` — Change current password
- **Get Preferences** — `GET /users/me/preferences` — Get user preferences
- **Update Preferences** — `PATCH /users/me/preferences` — Update notification, theme, and other preferences
- **Get User by ID** — `GET /users/{id}` — Admin operation to fetch any user
- **List Users** — `GET /users` — List users with status filter and pagination

### API Key Management

**Router:** `@/backend/src/presentation/routers/api_keys.py`

- **List API Keys** — `GET /api-keys` — List all API keys for the current user
- **Create API Key** — `POST /api-keys` — Create a new API key (secret shown only once)
- **Revoke API Key** — `DELETE /api-keys/{id}` — Revoke an API key
- **Update API Key** — `PATCH /api-keys/{id}` — Update key name or scopes

### Session Management

**Router:** `@/backend/src/presentation/routers/sessions.py`

- **List Sessions** — `GET /sessions` — List all active sessions for the current user
- **Revoke Session** — `DELETE /sessions/{id}` — Revoke a specific session
- **Revoke All Sessions** — `DELETE /sessions` — Revoke all sessions

### Project Management

**Router:** `@/backend/src/presentation/routers/projects.py`

- **Create Project** — `POST /projects` — Create a new video/content project
- **List Projects** — `GET /projects` — List projects with filters (status, content_type, pagination)
- **Get Project** — `GET /projects/{id}` — Get project details
- **Update Project** — `PATCH /projects/{id}` — Update project metadata
- **Delete Project** — `DELETE /projects/{id}` — Soft-delete a project
- **Get Workflow** — `GET /projects/{id}/workflow` — Get active workflow status
- **Start Workflow** — `POST /projects/{id}/workflow/start` — Start the automated content generation workflow
- **Cancel Workflow** — `POST /projects/{id}/workflow/cancel` — Cancel the running workflow
- **Get Research** — `GET /projects/{id}/research` — Get latest research output
- **List Research Versions** — `GET /projects/{id}/research/versions` — Paginated research history
- **Get Script** — `GET /projects/{id}/script` — Get latest script
- **List Script Versions** — `GET /projects/{id}/script/versions` — Paginated script history
- **Create Script Version** — `POST /projects/{id}/script` — Create a new script version (manual edit)
- **Get Storyboard** — `GET /projects/{id}/storyboard` — Get latest storyboard
- **List Storyboard Versions** — `GET /projects/{id}/storyboard/versions` — Paginated storyboard history
- **List Scenes** — `GET /projects/{id}/scenes` — List all scenes in the storyboard
- **Get Scene** — `GET /projects/{id}/scenes/{scene_id}` — Get a single scene
- **Update Scene** — `PATCH /projects/{id}/scenes/{scene_id}` — Update scene narration, camera, etc.
- **List Assets** — `GET /projects/{id}/assets` — List generated assets (images, videos, voice, music, subtitles, thumbnails) with type filter
- **Get Asset** — `GET /projects/{id}/assets/{asset_id}` — Get a single asset
- **List Generation Jobs** — `GET /projects/{id}/jobs` — List generation jobs for the project

**Supported content types:** YouTube Video, Blog Post, LinkedIn Article, Twitter Thread, Instagram Post, Podcast, Documentation, Course

**Supported video styles:** Cinematic, Documentary, Explainer, Talking Head, Animated, Mixed, Stock Footage, Whiteboard

### Workflow Engine

**Module:** `@/backend/src/workflow/`

A graph-based workflow engine that orchestrates the entire content generation pipeline:

- **13 Workflow Steps:** Initialization → Research → Scripting → Storyboard → Scene Planning → Asset Generation → Voice Generation → Subtitle Generation → Rendering → Thumbnail → SEO → Publishing → Completed
- **Features:** State management, checkpointing, retry policies, event-driven architecture, node-based graph builder, context propagation

### AI Agents — Research, Script, Storyboard

**Module:** `@/backend/src/ai/agents/`

#### Research Agent (`research/`)
- **Topic Analysis** — Analyzes the project topic for content angles
- **Keyword Extraction** — Extracts SEO keywords and search terms
- **Audience Analysis** — Identifies target audience pain points
- **Content Angle** — Determines unique content perspective
- **Fact Verification** — Verifies facts in the research
- **Research Summary** — Generates a comprehensive research summary
- **Research Planner** — Plans the research workflow steps

#### Script Agent (`script/`)
- **Script Outline** — Creates a structured script outline
- **Hook Generator** — Generates attention-grabbing opening hooks
- **Section Writer** — Writes individual script sections
- **Narrative Strategy** — Determines the narrative flow and structure
- **Call to Action** — Generates closing CTAs
- **Transitions** — Creates smooth transitions between sections
- **Script Optimization** — Optimizes script for engagement and clarity
- **Script Review** — Reviews and scores script quality

#### Storyboard Agent (`storyboard/`)
- **Scene Segmentation** — Breaks script into visual scenes
- **Story Analyzer** — Analyzes story structure and beats
- **Story Beat** — Defines key story moments
- **Camera Planner** — Plans camera angles and movements
- **Animation Planner** — Plans animation sequences
- **Asset Decision** — Decides what assets are needed per scene
- **Continuity Checker** — Ensures visual continuity across scenes
- **Storyboard Visual** — Generates visual descriptions for scenes
- **Storyboard Review** — Reviews and validates the storyboard

**Shared agent infrastructure:** Base agent class, prompt executor, prompt templates, memory management, output validation, quality scoring, artifact management, tool registry, event system

### Content Generation Pipeline

**Module:** `@/backend/src/generation/`

- **Orchestrator** — Coordinates generation jobs across providers
- **Executor** — Executes individual generation tasks
- **Provider Selection** — Selects optimal AI provider based on task, cost, and quality
- **Queue Manager** — Manages job queues with priority
- **Concurrency Control** — Limits concurrent generation jobs
- **Budget Management** — Tracks and enforces generation budget limits
- **Caching** — Caches generation results to avoid redundant API calls
- **Quality Assessment** — Scores generated content quality
- **Validation** — Validates generated outputs against schemas
- **Strategy** — Selects generation strategies (e.g., text-to-image, text-to-video)
- **Subtitle Generation** — Generates subtitles from scripts
- **Thumbnail Generation** — Generates video thumbnails
- **Health Monitoring** — Monitors generation pipeline health
- **Manifest** — Tracks all generated assets in a manifest

### Video Composition & Timeline

**Module:** `@/backend/src/composition/`

- **Composition Builder** — Builds a composition document from project assets
- **Timeline Compiler** — Compiles timeline into renderable format
- **Track Management** — Manages video, image, voice, music, SFX, subtitle, overlay, animation tracks
- **Audio Synchronizer** — Syncs audio tracks with video
- **Text/Subtitles** — Renders text overlays and subtitles
- **Transitions** — Applies transitions between clips
- **Effects** — Applies visual effects
- **Animations** — Manages animation sequences
- **Camera Movements** — Simulates camera movements (pan, zoom, etc.)
- **Preview Generator** — Generates low-resolution previews
- **Render Queue** — Manages render job queue
- **Render Cache** — Caches rendered segments
- **Quality Validator** — Validates composition before rendering
- **FFmpeg Renderer** — FFmpeg-based rendering backend
- **Export** — Export presets (1080p, 1440p, 4K, square, portrait)

**Production API endpoints** (`@/backend/src/presentation/routers/production.py`):
- `POST /projects/{id}/composition` — Build composition from assets
- `GET /projects/{id}/composition` — Get latest composition
- `PATCH /projects/{id}/composition/{cid}/timeline` — Update timeline
- `POST /projects/{id}/composition/{cid}/preview` — Generate low-res preview
- `GET /projects/{id}/package` — Get final project package (video + assets)

### Rendering

**Module:** `@/backend/src/rendering/` and `@/backend/src/composition/ffmpeg_renderer.py`

- FFmpeg-based video rendering pipeline
- Render job submission with priority levels (critical, high, normal, low, background)
- Real-time progress tracking (frames processed, ETA, stage completion)
- Render stages: loading → validating → preparing → compiling → composing → rendering → encoding → validating output
- Cancel in-progress renders
- Quality reporting on completed renders

**API endpoints:**
- `POST /projects/{id}/renders` — Submit render job
- `GET /projects/{id}/renders` — List render jobs
- `GET /projects/{id}/renders/{job_id}` — Get render job
- `GET /projects/{id}/renders/{job_id}/progress` — Get real-time progress
- `POST /projects/{id}/renders/{job_id}/cancel` — Cancel render job

### Publishing to YouTube

**Module:** `@/backend/src/publishing/`

- **YouTube Publisher** — Uploads videos to YouTube via YouTube Data API
- **OAuth Authentication** — Manages YouTube OAuth tokens
- **Metadata Management** — Sets video title, description, tags, category, privacy status
- **Thumbnail Upload** — Uploads custom thumbnails
- **Scheduling** — Schedule video publication for a future date/time
- **Publishing Modes** — Immediate or scheduled publishing
- **Publishing Queue** — Queues and manages publishing jobs
- **Validation** — Validates video and metadata before upload
- **Progress Tracking** — Tracks upload progress
- **Publishing Reports** — Generates reports with upload duration, video URL, warnings, errors
- **Strategy** — Supports multi-platform publishing strategy
- **Draft Saving** — Save as draft instead of publishing

**API endpoints:**
- `POST /projects/{id}/publishing/plans` — Create publishing plan
- `GET /projects/{id}/publishing/plans` — List publishing plans
- `POST /projects/{id}/publishing/plans/{plan_id}/execute` — Execute publishing plan
- `GET /projects/{id}/publishing/jobs` — List publishing jobs
- `POST /projects/{id}/publishing/jobs/{job_id}/cancel` — Cancel publishing job
- `GET /projects/{id}/publishing/reports` — List publishing reports

### Platform Analytics & Cost Tracking

**Module:** `@/backend/src/platform/`

- **Analytics Summary** — Total projects, success rate, failure rate, avg generation/rendering/publishing times
- **Cost Breakdown** — Total cost, revenue, profit margin, cost per provider, daily costs
- **Usage Tracking** — Images generated, videos generated, voice minutes, rendering minutes, publishing count, token usage
- **Provider Usage** — API calls per provider
- **Cost Analytics** — Detailed cost analysis across dimensions
- **Token Tracking** — Tracks LLM token consumption
- **Metrics** — Platform-wide metrics collection
- **Monitoring** — System monitoring and alerting

**API endpoints:**
- `GET /platform/analytics/summary` — Analytics summary
- `GET /platform/analytics/costs` — Cost breakdown
- `GET /platform/usage/{user_id}` — Usage summary per user

### Billing & Subscriptions

**Module:** `@/backend/src/platform/billing.py`

- **Plans** — Multiple subscription tiers with features (max projects, images, videos, voice minutes, rendering minutes, storage, custom branding, priority support, API access, advanced analytics)
- **Subscriptions** — Create, cancel, change plan, with trial support
- **Credits** — Add/track credits by type (image, video, voice, render, publish)
- **Invoices** — Generate, list, and pay invoices

**API endpoints:**
- `GET /platform/billing/plans` — List available plans
- `GET /platform/billing/plans/{id}` — Get plan details
- `GET /platform/billing/subscriptions/{user_id}` — Get user subscription
- `POST /platform/billing/subscriptions` — Create subscription
- `POST /platform/billing/subscriptions/{user_id}/cancel` — Cancel subscription
- `PATCH /platform/billing/subscriptions/{user_id}` — Change plan
- `GET /platform/billing/credits/{user_id}` — Get credit balance
- `POST /platform/billing/credits/{user_id}/add` — Add credits
- `GET /platform/billing/invoices` — List invoices
- `POST /platform/billing/invoices/{id}/pay` — Pay invoice

### Organizations & Teams

**Module:** `@/backend/src/platform/organization.py`

- **Create Organization** — Create an org with owner, slug, max members
- **List Organizations** — List orgs for a user
- **Get Organization** — Get org details
- **List Members** — List team members in an org
- **Add Member** — Add a member with a role

**API endpoints:**
- `GET /platform/organizations` — List organizations
- `POST /platform/organizations` — Create organization
- `GET /platform/organizations/{id}` — Get organization
- `GET /platform/organizations/{id}/members` — List members
- `POST /platform/organizations/{id}/members` — Add member

### Feature Flags

**Module:** `@/backend/src/platform/feature_flags.py`

- **Create Flag** — Create feature flags with type (boolean, percentage), scope (global, user, organization, plan)
- **List Flags** — List all feature flags, optionally filtered by scope
- **Get Flag** — Get a specific flag by key
- **Update Flag** — Toggle or update flag configuration
- **Delete Flag** — Remove a feature flag

**API endpoints:**
- `GET /platform/feature-flags` — List feature flags
- `POST /platform/feature-flags` — Create feature flag
- `PATCH /platform/feature-flags/{key}` — Update feature flag
- `DELETE /platform/feature-flags/{key}` — Delete feature flag

### Admin & Monitoring

**Module:** `@/backend/src/platform/admin.py`, `@/backend/src/platform/monitoring.py`, `@/backend/src/platform/audit.py`

- **Platform Overview** — Aggregate stats (total projects, invoices, organizations)
- **System Health** — Component health checks with status (healthy, degraded, unhealthy) and latency
- **Provider Health** — AI provider availability and health
- **Audit Logs** — Recent platform activity logs (action, user, resource)
- **Billing Overview** — Platform-wide billing dashboard
- **Usage Dashboard** — Platform-wide usage stats
- **User Management** — Suspend/activate users

**API endpoints:**
- `GET /platform/admin/overview` — Platform overview
- `GET /platform/admin/health` — System health
- `GET /platform/admin/providers` — Provider health
- `GET /platform/admin/audit-logs` — Audit logs
- `GET /platform/admin/billing` — Billing overview
- `GET /platform/admin/usage` — Usage dashboard
- `POST /platform/admin/users/{id}/suspend` — Suspend user
- `POST /platform/admin/users/{id}/activate` — Activate user

---

## Frontend UI Pages

### Public / Auth Pages

| Page | Route | Description |
|------|-------|-------------|
| **Home / Redirect** | `/` | Redirects to `/dashboard` if authenticated, otherwise `/login` |
| **Login** | `/login` | Email/password login form |
| **Register** | `/register` | New user registration form |

### Workspace Pages

All workspace pages are wrapped in the `WorkspaceShell` layout with a collapsible sidebar, top navigation, status bar, and inspector panel. Authentication is required.

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/dashboard` | Overview with project stats (total, in-progress, completed, failed), quick links to Analytics/Billing/Settings/Admin, and recent projects grid |
| **Projects List** | `/projects` | Searchable, filterable grid of all projects with status badges, tags, edit/delete actions, and delete confirmation dialog |
| **New Project** | `/projects/new` | 3-step wizard: (1) Choose content type, (2) Enter details (title, description, language, audience, video style, duration, tags), (3) Review & create |
| **Project Detail** | `/projects/{id}` | Project overview with metadata cards (language, content type, audience, created date), tags, content navigation tabs, workflow start/cancel buttons, and a 13-step workflow progress visualization |
| **Analytics** | `/analytics` | Stats grid (total projects, success rate, avg gen time, total cost), project analytics (successful/failed/failure rate), resource usage (images, videos, voice, rendering, publishing, tokens), provider usage, cost breakdown (total, revenue, profit margin, cost per provider, daily costs), most used providers |
| **Billing** | `/billing` | Current subscription card, available plans grid with feature comparison, credits balance by type with add-credits form, invoices list with pay action |
| **Settings** | `/settings` | Profile info, appearance (light/dark/system theme), brand kit (primary color, font family, watermark URL), AI provider config (Gemini, VEO, Imagen, TTS model selection), voice settings (provider, voice ID, speed), storage usage bar, notification preferences (email/in-app toggles), security (2FA status, change password) |
| **Admin** | `/admin` | Platform overview stats, system health checks with status/latency, feature flags management (create/toggle/delete), organizations list, audit logs feed |

### Project Sub-Pages

These pages are accessed from the Project Detail page's content navigation tabs and follow the workflow pipeline order:

| Page | Route | Description |
|------|-------|-------------|
| **Research** | `/projects/{id}/research` | AI-generated research summary, keywords, audience pain points, timeline, interesting facts, sources (with links), version history, regenerate button |
| **Script** | `/projects/{id}/script` | Script display with hook/body/CTA sections, word count & estimated duration stats, version history, edit mode (create new version), export to .txt, regenerate |
| **Storyboard** | `/projects/{id}/storyboard` | Storyboard metadata (scene count, duration, style, narrative structure), scene cards grid with narration/camera info/duration/emotion/generation status/review status, edit scene narration dialog, version history |
| **Assets** | `/projects/{id}/assets` | Asset studio with filter tabs (images, videos, voice, music, subtitles, thumbnails), asset cards with preview area, provider/cost/quality metadata, preview & download buttons, generate assets action |
| **Generation Dashboard** | `/projects/{id}/generation` | Real-time generation job dashboard with overall progress bar, stats (queued/running/completed/failed), job queue list with status icons, priority badges, retry info, realtime WebSocket updates |
| **Timeline Editor** | `/projects/{id}/timeline` | Composition builder with export preset selection, validation status, scene overview, multi-track timeline visualization (video, image, voice, music, SFX, subtitles, overlays, animation) with clip positioning, track mute/lock/visibility, export profile display, preview generation |
| **Render Queue** | `/projects/{id}/rendering` | Render job submission with priority selection, active render progress (stage, percentage, frames, ETA, completed stages), stats grid, job list with realtime status, cancel/download actions, final project package display (video path, thumbnail, subtitles, quality report) |
| **Publishing** | `/projects/{id}/publishing` | Publishing plan creation form (title, description, tags, privacy status, immediate/scheduled mode, schedule date), publishing plans list with execute buttons, publishing jobs with realtime status, publishing reports with video URL, upload duration, thumbnail/metadata status, warnings/errors |

---

## Tech Stack

### Backend
- **Framework:** FastAPI (async ASGI)
- **Database:** SQLAlchemy async ORM with Alembic migrations (SQLite dev / PostgreSQL prod)
- **Cache:** Redis
- **Auth:** JWT (access + refresh tokens), bcrypt password hashing, RBAC with roles & permissions
- **AI:** Gemini (LLM), VEO (video generation), Imagen (image generation), Google TTS / ElevenLabs (voice)
- **Rendering:** FFmpeg
- **Publishing:** YouTube Data API v3
- **Architecture:** Clean Architecture / Domain-Driven Design (domain entities, application services, infrastructure, presentation)
- **Background Tasks:** Celery with Celery Beat scheduler

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** TailwindCSS with CSS custom properties (light/dark themes)
- **State Management:** Zustand (auth store), React Query (data fetching via platform-sdk)
- **Realtime:** WebSocket-based realtime provider for job/render/publishing status updates
- **Monorepo:** Turborepo with shared packages:
  - `@ai-video-studio/design-system` — UI components (Card, Button, Badge, Input, Select, Dialog, Skeleton, EmptyState, Progress, etc.)
  - `@ai-video-studio/platform-sdk` — API hooks and SDK client
  - `@ai-video-studio/platform-kernel` — Auth store, platform provider, realtime provider, theme hook
  - `@ai-video-studio/icons` — Lucide icon set
  - `@ai-video-studio/shared-types` — TypeScript types and enums
  - `@ai-video-studio/shared-utils` — Utility functions (formatRelativeTime, etc.)
  - `@ai-video-studio/theme` — Theme variables (light/dark)

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Services:** Backend API, Frontend web app, PostgreSQL, Redis, Celery worker, Celery Beat
