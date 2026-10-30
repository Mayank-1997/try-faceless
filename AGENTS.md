# AGENTS.md

> **Purpose**: This file is auto-loaded by AI assistants (Devin, Claude, etc.)
> at the start of every session. It contains the essential architectural
> knowledge needed to work on this codebase without reading dozens of files.
> Detailed docs are in `docs/` — this file is the quick-reference index.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async + asyncpg), Celery,
  Redis, LangGraph, Pydantic v2
- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind,
  pnpm monorepo (`frontend/apps/web`, `frontend/packages/*`)
- **Infra**: Docker Compose (postgres, redis, api, celery_worker, celery_beat,
  web), Alembic migrations, FFmpeg for video rendering
- **AI Providers**: Google Gemini (LLM), Google TTS / Edge TTS (voice),
  stock + AI image/video generation
- **Storage**: Local filesystem (`storage/` dir), accessed as
  `local:///app/storage/...` inside containers

## Project Structure (Key Directories)

```
backend/
  src/
    ai/
      agents/          # LangGraph agent graphs (research/, script/, storyboard/)
      gateway/         # LLM gateway, voice gateway, image/video gateways
      providers/       # Provider implementations (google_tts, edge_tts, stock, etc.)
    application/
      di/              # ServiceContainer, dependency injection
      services/        # ProjectService (main orchestrator), platform_service, etc.
    composition/       # FFmpeg video composition pipeline
      builder.py       # CompositionBuilder — builds timeline from manifest
      pipeline.py      # RenderingPipeline — orchestrates FFmpeg rendering
      ffmpeg_renderer.py  # FFmpegCompositionRenderer — actual FFmpeg commands
    core/
      config.py        # Settings (Pydantic, loads from .env)
      enums.py         # All enums (JobStatus, AssetType, WorkflowStep, etc.)
      interfaces.py    # Abstract interfaces for gateways/providers
    domain/
      entities/        # Domain entities (Scene, Asset, Storyboard, Script, etc.)
    generation/
      schema.py        # AssetManifest, SceneAssetManifest, GeneratedAsset
      executor.py      # Asset generation executor
    infrastructure/
      tasks/
        workflow_tasks.py  # THE main workflow file — all Celery task logic
        celery_app.py      # Celery app definition
      storage/
        gateway.py     # StorageGateway (local/S3 abstraction)
        local.py       # LocalStorageProvider
    persistence/
      models/          # SQLAlchemy ORM models (business.py, auth.py)
      repositories/    # Repository classes (business_repositories.py)
    presentation/
      routers/         # FastAPI routes (projects.py, platform.py, etc.)
    workflow/
      state.py         # WorkflowState — the root state object (see below)
      engine.py        # WorkflowEngine — runs LangGraph sub-workflows
      builder.py       # Builds LangGraph graphs from node definitions
  prompts/              # LLM prompt templates
  alembic/              # Database migrations
frontend/
  apps/web/            # Next.js web app
  packages/
    platform-sdk/      # TypeScript SDK for backend API
    platform-kernel/   # Shared UI components
    icons/             # Icon re-exports
docs/                   # Detailed architecture docs (one per subsystem)
storage/                # Local file storage (projects, workflow_state, etc.)
```

## Workflow Pipeline (Step Order)

The pipeline runs as a Celery task (`execute_workflow_task`) in
`workflow_tasks.py`. Steps execute in this order:

1. **RESEARCH** — runs `research_workflow` (LangGraph, 10+ agents)
2. **SCRIPTING** — runs `script_workflow` (LangGraph, 8+ agents)
3. **STORYBOARD** — runs `storyboard_workflow` (LangGraph, 9 agents)
4. **SCENE_PLANNING** — creates Scene entities from storyboard package
5. **ASSET_GENERATION** — generates images/videos per scene
6. **VOICE_GENERATION** — TTS from scene narration (see gotcha below)
7. **SUBTITLE_GENERATION** — SRT files from scene narration
8. **RENDERING** — multi-pass FFmpeg render → `final_video.mp4`
9. **THUMBNAIL** — picks a scene image as thumbnail
10. **SEO** — generates title/description/tags
11. **PUBLISHING** — (optional) publishes to YouTube

Each step: runs → persists to DB → `_hydrate_workflow_state` →
`_save_workflow_state` → saves checkpoint to `workflows` table.

## WorkflowState (the central state object)

Defined in `src/workflow/state.py`. Every LangGraph node receives and
returns this. Key fields:

| Field | Type | Purpose |
|-------|------|---------|
| `project` | `ProjectInfo` | Project metadata (id, name, status) |
| `research` | `ResearchData` | Research results (sources, facts, summary) |
| `script` | `ScriptData` | Script content (hook, body, outro, word_count) |
| `storyboard` | `StoryboardData` | Narrative structure + `metadata["storyboard_package"]` |
| `scenes` | `list[SceneData]` | Per-scene definitions (narration, camera, visual_type) |
| `assets` | `list[AssetData]` | Generated assets (images, videos, voice, subtitles) |
| `voice` | `VoiceData` | Voice settings (language, voice_name, duration) |
| `rendering` | `RenderingData` | Render status (output_path, file_size, duration) |
| `seo` | `SEOData` | SEO metadata (title, description, tags) |
| `cost` | `CostData` | Running cost totals per category |

**Important**: The storyboard package (with scene narrations) is stored in
`state.storyboard.metadata["storyboard_package"]`, NOT in `state.scenes`.
The voice/subtitle/asset generation steps read from this metadata key via
`_get_storyboard_package(state)`. See "Known Gotchas" below.

## Database (Key Tables)

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `projects` | Project metadata | id, title, status, language, content_type |
| `workflows` | Workflow runs | id, project_id, version, status, checkpoint_ref |
| `scenes` | Scene definitions | id, project_id, workflow_id, scene_number, narration, duration_seconds |
| `assets` | Generated assets | id, project_id, scene_id, asset_type, storage_ref, generation_status |
| `storyboards` | Storyboard packages | id, project_id, scene_count, package_json |
| `scripts` | Script versions | id, project_id, hook, body, cta, word_count |
| `research` | Research results | id, project_id, summary, sources, keywords |
| `prompt_executions` | LLM call logs | rendered_prompt, response, provider, model, tokens, cost |

DB connection: `postgresql+asyncpg://aivideo:aivideo_secret@postgres:5432/aivideo_studio`
(Docker) or `@localhost:5433` (local debug).

## Common Commands

```powershell
# Full Docker stack
docker compose up -d

# Local debug mode (postgres + redis in Docker, app on host)
docker compose up -d postgres redis
docker compose stop api celery_worker celery_beat

# Run Celery worker locally (Windows)
& "backend/.venv/Scripts/python.exe" -m celery -A src.infrastructure.tasks.celery_app worker --pool=solo --loglevel=INFO

# Run a script inside the API container (e.g. render script)
docker cp backend/_script.py aivideo_api:/app/_script.py
docker exec aivideo_api python /app/_script.py

# Apply DB migrations
docker compose exec api alembic upgrade head

# Query DB directly
& "backend/.venv/Scripts/python.exe" -c "import asyncio, asyncpg; ..."

# Restart API after code changes (code is volume-mounted)
docker compose restart api
```

## Known Gotchas

### 1. storyboard_package wiped by hydration (FIXED)

`_hydrate_workflow_state` rebuilds `state.storyboard` from the DB
`storyboards` table. Originally it created a new `StoryboardData` with
empty `metadata={}`, wiping the `storyboard_package` that
`storyboard_review.py` had set. This caused voice/subtitle/asset
generation to find no scene packages → empty output → render failure.

**Fix**: hydration now restores `storyboard_package` from
`storyboard.package_json` into `metadata`. See
`workflow_tasks.py` `_hydrate_workflow_state`.

### 2. Multiple workflow runs create duplicate scenes/assets

Each workflow run creates new Scene and Asset rows without deleting old
ones. A project can have 30+ scenes from 4+ workflow runs. Always filter
by `workflow_id` when querying scenes/assets for a specific run.

### 3. build_outputs_zip included ALL workflows' assets (FIXED)

`build_outputs_zip` in `project_service.py` originally fetched all assets
for a project (across all workflow runs), producing a 1 GB+ zip that
caused OOM/timeout. Now filters to only the latest workflow's scenes.

### 4. FFmpeg not on Windows host

FFmpeg is only inside the Docker containers. Rendering scripts must run
inside `aivideo_api` container: `docker exec aivideo_api python /app/script.py`

### 5. Celery prefork pool crashes on Windows

Use `--pool=solo` when running Celery on Windows.

### 6. Python 3.14 incompatible

`google.protobuf` C extension breaks on 3.14. Use Python 3.12.

## Key Files Quick Reference

| Need to... | Look at |
|------------|---------|
| Understand workflow steps | `src/infrastructure/tasks/workflow_tasks.py` `_create_step_output()` |
| Debug an LLM call | `src/ai/gateway/llm_gateway.py` `generate()` |
| Change workflow state fields | `src/workflow/state.py` |
| Add/modify an agent | `src/ai/agents/<phase>/` (research, script, storyboard) |
| Change video rendering | `src/composition/ffmpeg_renderer.py`, `src/composition/pipeline.py` |
| Add a new API endpoint | `src/presentation/routers/projects.py` |
| Change DB schema | `src/persistence/models/business.py` + Alembic migration |
| Modify download/export | `src/application/services/project_service.py` `build_outputs_zip()` |
| Frontend API calls | `frontend/packages/platform-sdk/src/modules/projects.ts` |

## Detailed Documentation

For deep dives, see `docs/`:
- `docs/architecture.md` — overall system architecture
- `docs/DATABASE_SCHEMA.md` — full DB schema
- `docs/composition_architecture.md` — video composition pipeline
- `docs/generation_architecture.md` — asset generation
- `docs/storyboard_architecture.md` — storyboard agents
- `docs/orchestration_architecture.md` — workflow orchestration
- `WORKFLOW_ARCHITECTURE.md` — workflow pipeline details

---

## Local Debugging (VS Code Hybrid Mode)

The project supports hybrid debugging: **postgres + redis run in Docker**,
while **FastAPI + Celery run on the host** under the VS Code debugger.

### Prerequisites

- Python 3.12+ venv at `backend/.venv` with `fastapi`, `uvicorn`, `celery`,
  `debugpy`, `sqlalchemy`, and other deps installed.
- Docker Desktop running for postgres + redis.

### One-time setup

```powershell
# Install debug-only deps in the local venv if not already present
& "backend/.venv/Scripts/python.exe" -m pip install "celery[redis]>=5.4.0,<5.5" "debugpy>=1.8.0"
```

### Python version

The local `.venv` must use **Python 3.12** (matching `backend/Dockerfile`).
Python 3.14 is not supported because `google.protobuf`'s C/UPB extension is
incompatible with 3.14's metaclass handling, which breaks `google.generativeai`.

To recreate the venv with 3.12:

```powershell
Move-Item -Path "backend/.venv" -Destination "backend/.venv_old" -Force
py -3.12 -m venv "backend/.venv"
& "backend/.venv/Scripts/python.exe" -m pip install -e "backend/.[dev]"
& "backend/.venv/Scripts/python.exe" -m pip install "debugpy>=1.8.0"
```

### How the launch env overrides work

The `.env` file contains Docker-internal hostnames (`postgres`, `redis`).
The `env` block in the launch config:

- Clears `DATABASE_URL` so the connection string is rebuilt from the
  `POSTGRES_*` components loaded from `.env`.
- Overrides `POSTGRES_HOST` to `localhost` and `POSTGRES_PORT` to `5433`
  (the port docker-compose publishes on the host).
- Overrides `REDIS_HOST` to `localhost`.
- Overrides `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to the
  `localhost` equivalents.
- Sets `STORAGE_LOCAL_PATH` to a writable Windows path under the repo.

This preserves your real `POSTGRES_PASSWORD` and `GEMINI_API_KEY` from
`.env` while redirecting the services that must reach Docker.

### Windows-specific notes

- **Use `--pool=solo` for Celery** (already in `launch.json`). The default
  `prefork` pool crashes on Windows under the debugger.
- **Set `justMyCode` to `false`** in `launch.json` if you want to step into
  third-party packages (e.g., `google.generativeai`, `langchain-core`).
- **FFmpeg** is only needed for rendering/publishing stages. If you see
  `FFMPEG_PATH` errors, either install FFmpeg or stop debugging after the
  research/script/storyboard steps.

### Switching to local debug mode

1. Start only the infrastructure containers and stop the app containers:

   ```powershell
   docker compose up -d postgres redis
   docker compose stop api celery_worker celery_beat
   ```

   Or run the VS Code task **"Switch to local debug mode"**
   (`Ctrl+Shift+P` → `Tasks: Run Task`).

2. In VS Code, go to the Run & Debug panel (`Ctrl+Shift+D`) and select:
   - **FastAPI (debug, no reload)** — breakpoints in API/route code.
   - **Celery worker (debug)** — breakpoints in workflow/agent code.
   - **FastAPI + Celery worker (debug)** — starts both (compound config).
   - **Full stack (debug)** — starts FastAPI + Celery worker + Celery beat.

3. Set breakpoints in any `.py` file (e.g., `src/ai/gateway/llm_gateway.py`,
   `src/infrastructure/tasks/workflow_tasks.py`) and press `F5`.

### How the env override works

The `.env` file uses Docker-internal hostnames (`postgres`, `redis`).
The `env` block in `.vscode/launch.json` overrides them to `localhost`
with the ports docker-compose publishes:

| Variable             | .env (Docker)                          | launch.json override (local)            |
|----------------------|----------------------------------------|-----------------------------------------|
| `DATABASE_URL`       | `...@postgres:5432/aivideo_studio`     | `...@localhost:5433/aivideo_studio`     |
| `CELERY_BROKER_URL`  | `redis://redis:6379/1`                 | `redis://localhost:6379/1`              |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2`              | `redis://localhost:6379/2`              |
| `REDIS_HOST`         | `redis`                                | `localhost`                             |

`GEMINI_API_KEY` and other secrets still load from `.env` via `envFile`.

### Switching back to full Docker mode

```powershell
docker compose up -d
```

### Good places for breakpoints when debugging LLM calls

- `src/ai/gateway/llm_gateway.py` — `generate()` / `generate_json()` (every LLM call)
- `src/ai/agents/prompt_executor.py` — `_execute()` (prompt rendering + gateway call)
- `src/infrastructure/tasks/workflow_tasks.py` — `_run_workflow()` / `_create_step_output()`
- `src/ai/agents/base.py` — agent execution lifecycle
- `src/workflow/engine.py` — `WorkflowEngine.run()` (step transitions)

### Celery worker on Windows

Celery's default `prefork` pool does not work reliably on Windows
(especially under the debugger). The debug launch config uses
`--pool=solo`, which runs all tasks in the same process. This means
breakpoints inside `execute_workflow_task`, `_run_workflow`,
`llm_gateway.generate`, and `prompt_executor._execute` will hit.

If you run Celery from the command line on Windows for non-debug use,
use:

```powershell
& "backend/.venv/Scripts/python.exe" -m celery -A src.infrastructure.tasks.celery_app worker --pool=solo --loglevel=INFO
```

### Inspecting LLM outputs in the database

LLM call outputs are stored in the `prompt_executions` table
(see `PromptExecutionModel` in `src/persistence/models/business.py`).
Key columns: `rendered_prompt`, `response`, `provider`, `model`,
`input_tokens`, `output_tokens`, `cost_usd`, `latency_ms`, `status`.

Cost and token aggregates are in `cost_records` and `token_usage_records`.

Note: the in-memory `PromptExecutor._history` list tracks executions per
process but is not automatically persisted to `prompt_executions` —
persistence happens through the repository layer when wired up.

### Database migrations

The API container does not run migrations automatically on startup. After
pulling code that adds new columns, apply Alembic migrations from inside the
API container:

```powershell
docker compose exec api alembic upgrade head
```

If `alembic` fails with `ModuleNotFoundError: No module named 'psycopg2'`,
install the sync PostgreSQL driver first (the image uses `asyncpg` for the
app and needs `psycopg2-binary` for Alembic):

```powershell
docker compose exec api pip install psycopg2-binary
docker compose exec api alembic upgrade head
```

For a permanent fix, `psycopg2-binary` is listed in `backend/pyproject.toml`
so rebuilding the image (`docker compose up -d --build api celery_worker
celery_beat`) installs it automatically.
