# AI Video Studio — End-to-End Workflow Architecture

Complete flow of what happens when a user creates a project and clicks "Start Workflow".

---

## 1. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Browser)                            │
│               Next.js Frontend (port 3000)                   │
│  Create Project → Start Workflow → Poll Status               │
└──────┬───────────────┬──────────────────┬────────────────────┘
       │               │                  │
       ▼               ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)                      │
│  POST /projects  →  ProjectService.create_project()           │
│  POST /projects/{id}/workflow/start                            │
│    → ProjectService.start_workflow()                          │
│    → execute_workflow_task.delay()  ──→ Redis broker          │
│  GET /projects/{id}/workflow  (polling)                       │
└──────────┬───────────────────────────────┬───────────────────┘
           │                               │
           ▼                               ▼
┌────────────────────┐    ┌────────────────────────────────────┐
│ PostgreSQL (5432)  │    │  Celery Worker (aivideo_celery_worker)│
│                    │    │                                    │
│ Tables:            │    │  execute_workflow_task()            │
│ - users            │    │    → _run_workflow()                │
│ - projects         │    │      → ServiceContainer.initialize()│
│ - workflows        │    │      → WorkflowEngine.execute()     │
│ - research         │    │        → ResearchWorkflowGraph (8)  │
│ - scripts          │    │        → ScriptWorkflowGraph (8)    │
│ - storyboards      │    │        → StoryboardWorkflowGraph (9)│
│ - scenes           │    │      → Persist to DB                │
│ - assets           │    │                                    │
│ - cost_records     │    │  Each agent → Gemini LLM API call   │
│ - token_usage      │    │  Model: gemini-flash-latest         │
└────────────────────┘    └────────────────────────────────────┘
```

---

## 2. Infrastructure Components

| Container | Purpose | Port |
|-----------|---------|------|
| `aivideo_api` | FastAPI backend (uvicorn) | 8000 |
| `aivideo_celery_worker` | Celery worker — runs workflow tasks | — |
| `aivideo_celery_beat` | Celery beat — scheduled tasks | — |
| `aivideo_postgres` | PostgreSQL database | 5432 |
| `aivideo_redis` | Redis — Celery broker + result backend | 6379 |
| `aivideo_web` | Next.js frontend | 3000 |

### Key Config (`.env`)

| Variable | Value | Purpose |
|----------|-------|---------|
| `GEMINI_API_KEY` | (secret) | Google AI Studio API key |
| `GEMINI_FLASH_MODEL` | `gemini-flash-latest` | Model used for all agents |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `3600` (60 min) | Soft timeout |
| `CELERY_TASK_TIME_LIMIT` | `3900` (65 min) | Hard kill timeout |

---

## Step 1: User Registration & Login

### API Calls

1. **`POST /api/v1/auth/register`** — Body: `{ email, password, username, name }`
   - Class: `AuthRouter` → `AuthenticationService.register()`
   - DB: INSERT into `users` table

2. **`POST /api/v1/auth/login`** — Body: `{ email, password }`
   - Class: `AuthRouter` → `AuthenticationService.login()`
   - Returns: `{ access_token, token_type, user }`
   - DB: Reads `users`, inserts `user_sessions`

### Files
- `backend/src/presentation/routers/auth.py`
- `backend/src/application/services/authentication_service.py`
- `backend/src/persistence/models/auth.py`

---

## Step 2: Create Project

### API Call

**`POST /api/v1/projects`**
- Headers: `Authorization: Bearer <JWT>`
- Body: `{ title, description, content_type, video_style, target_duration_seconds, language, audience, tags, metadata }`

### Code Path

```
Frontend: createProject form
  → SDK: getSDK().projects.create(data)
    → HTTP POST /api/v1/projects

Backend:
  projects.py: create_project()              [router, line 68]
    → ProjectService.create_project()         [service, line 80]
      → Project(domain entity)
      → SqlAlchemyProjectRepository.create()  [persist]
        → ProjectModel → SQL INSERT
      → project_to_response()                 [entity → DTO]
    → session.commit()
    → returns ProjectResponse
```

### DB Table: `projects`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Project ID |
| owner_id | UUID (FK→users) | Owner |
| title | VARCHAR(300) | Title |
| description | TEXT | Description |
| language | VARCHAR(10) | e.g., "en" |
| content_type | VARCHAR(50) | e.g., "youtube_video" |
| video_style | VARCHAR(50) | e.g., "mixed" |
| target_duration_seconds | INTEGER | e.g., 600 |
| status | VARCHAR(20) | "draft" initially |
| current_step | VARCHAR(50) | "initialization" initially |
| tags | TEXT (JSON) | JSON list |
| metadata | TEXT (JSON) | JSON dict |

### Files
- Router: `backend/src/presentation/routers/projects.py:68-78`
- Service: `backend/src/application/services/project_service.py:80-98`
- ORM: `backend/src/persistence/models/business.py:48-107` (`ProjectModel`)

---

## Step 3: Start Workflow (UI → API → Celery)

### UI Flow

On the project detail page, the user clicks **"Start Workflow"**:

```
frontend/apps/web/src/app/(workspace)/projects/[id]/page.tsx:554
  <Button onClick={() => startWorkflow.mutate(projectId)}>
    Start Workflow
  </Button>
```

The `useStartWorkflow` hook sends the HTTP request:
```
frontend/packages/platform-sdk/src/hooks/project-hooks.ts:116
  mutationFn: (id) => getSDK().projects.startWorkflow(id)
```

### API Call

**`POST /api/v1/projects/{project_id}/workflow/start`**
- Returns: `WorkflowResponse` → `{ id, project_id, current_step, status }`

### Code Path

```
Backend:
  projects.py: start_workflow()              [router, line 153]
    → ProjectService.start_workflow()         [service, line 188]
      1. Load project from DB
      2. If active workflow exists, mark it FAILED
      3. Create new Workflow entity:
         - version=1, step="initialization", status="running"
      4. INSERT into "workflows" table
      5. Update project: status="researching"
      6. UPDATE "projects" table
    → session.commit()
    → execute_workflow_task.delay(project_id, workflow_id)
      → Pushes task to Redis queue (non-blocking)
    → returns WorkflowResponse
```

### DB Changes

**`workflows` table** (new row): `id, project_id, version=1, current_step="initialization", status="running"`

**`projects` table** (updated): `status` → `"researching"`

### Files
- Router: `backend/src/presentation/routers/projects.py:153-167`
- Service: `backend/src/application/services/project_service.py:188-231`
- ORM: `backend/src/persistence/models/business.py:113-149` (`WorkflowModel`)
- Celery task: `backend/src/infrastructure/tasks/workflow_tasks.py:64-67`

---

## Step 4: Celery Worker Executes the Full Pipeline

### How It Works

1. `aivideo_celery_worker` runs `celery -A src.infrastructure.tasks.celery_app worker`
2. Celery connects to Redis broker at `redis://aivideo_redis:6379/1`
3. When `execute_workflow_task.delay()` is called, task is pushed to Redis
4. Worker picks up task and executes it

### Celery Config (`backend/src/infrastructure/tasks/celery_app.py`)

| Setting | Value |
|---------|-------|
| broker_url | `redis://aivideo_redis:6379/1` |
| result_backend | `redis://aivideo_redis:6379/2` |
| task_soft_time_limit | 3600s |
| task_time_limit | 3900s |
| worker_concurrency | 4 |

### Task Entry Point

```python
# workflow_tasks.py:64-67
@celery_app.task(name="src.infrastructure.tasks.workflow_tasks.execute_workflow_task")
def execute_workflow_task(project_id: str, workflow_id: str) -> None:
    return asyncio.run(_run_workflow(UUID(project_id), UUID(workflow_id)))
```

### `_run_workflow()` — Main Loop (`workflow_tasks.py:70-171`)

```
_run_workflow(project_id, workflow_id):
  1. Create dedicated async DB engine (bound to this task's event loop)
  2. Create ServiceContainer and initialize():
     → Loads Gemini provider (from GEMINI_API_KEY)
     → Creates LLMGateway, PromptExecutor, CostTracker, TokenTracker,
       EventBus, LangfuseClient, MetricsCollector
  3. Create WorkflowEngine, register 3 graphs:
     → ResearchWorkflowGraph (8 agents)
     → ScriptWorkflowGraph (8 agents)
     → StoryboardWorkflowGraph (9 agents)
  4. Build initial WorkflowState from project
  5. STEP LOOP:
     while current_step != "completed":
       a. advance_workflow() → moves to next step, updates DB
       b. _create_step_output(step):
          → "research"       → run ResearchWorkflowGraph, save to research table
          → "scripting"      → run ScriptWorkflowGraph, save to scripts table
          → "storyboard"     → run StoryboardWorkflowGraph, save to storyboards table
          → "scene_planning" → create Scene rows from storyboard data
          → other steps      → skipped (placeholder)
       c. Commit to DB
       d. Sleep 3s (let UI polling observe transition)
```

### Workflow Step Order

Defined in `ProjectService._STEP_ORDER` (line 256-269):

| # | Step | Project Status | Has LLM? | Description |
|---|------|---------------|----------|-------------|
| 1 | initialization | researching | No | Setup (done by start_workflow) |
| 2 | research | researching | Yes (8 agents) | Topic analysis, web research, keywords |
| 3 | scripting | scripting | Yes (8 agents) | Narrative, outline, hook, sections, CTA |
| 4 | storyboard | planning | Yes (9 agents) | Story analysis, scenes, visuals, camera |
| 5 | scene_planning | planning | No | Creates Scene DB rows from storyboard |
| 6 | asset_generation | generating | No | Placeholder |
| 7 | voice_generation | generating | No | Placeholder |
| 8 | subtitle_generation | generating | No | Placeholder |
| 9 | rendering | rendering | No | Placeholder |
| 10 | thumbnail | rendering | No | Placeholder |
| 11 | seo | publishing | No | Placeholder |
| 12 | completed | completed | No | Done |

### How Each Workflow Graph Executes

```
WorkflowEngine.execute(workflow_name, state, ...):    [engine.py:146]
  1. Look up graph from registry
  2. Create WorkflowContext with gateways & services:
     - gateways: {"llm": LLMGateway}
     - services: {"prompt_executor", "cost_tracker", "token_tracker",
                  "event_bus", "langfuse_client", "metrics_collector"}
  3. Build LangGraph StateGraph (nodes + edges)
  4. Execute: graph.ainvoke(initial_state)
     → LangGraph runs each node sequentially
     → Each node is a BaseAgent wrapped for LangGraph
  5. Return ExecutionResult (state, cost, tokens)
```

### How Each Agent Executes

```
BaseAgent.run_agent(context):                          [base.py:299]
  1. Emit AgentStarted event
  2. prepare_prompt(context) → (PromptTemplate, variables)
  3. PromptExecutor.execute_template(template, variables):
     a. Render prompt with variables
     b. LLMGateway.generate(rendered_prompt):
        → GeminiLLMProvider.generate(prompt)
          → Google Gemini API: model.generate_content(prompt)
          → Returns response.text
     c. Parse JSON from response (strip markdown fences via _clean_json_output)
     d. Return AIResponse
  4. OutputValidator.validate(response):
     → Check required JSON fields, attempt repair if invalid
  5. QualityEvaluator.evaluate(response):
     → Score 0.0-1.0, must exceed quality_threshold
  6. process_response() → extract structured data
  7. update_workflow_state() → store results in WorkflowState
  8. Track cost & tokens in state
  9. Emit AgentCompleted event
```

---

## Phase A: Research Workflow

**File**: `backend/src/ai/agents/research/workflow.py`
**Graph**: `ResearchWorkflowGraph` — 8 agents sequential

### Agent Chain

```
TopicAnalyzer → ResearchPlanner → ResearchAgent → FactVerification →
KeywordExtraction → AudienceAnalysis → ContentAngle → ResearchSummary
```

### Agent Details

| # | Agent Name | Class | LLM Calls | What It Does |
|---|-----------|-------|-----------|--------------|
| 1 | topic_analyzer | `TopicAnalyzerAgent` | 1 | Analyzes topic, expands it, identifies category & audience |
| 2 | research_planner | `ResearchPlannerAgent` | 1 | Creates structured research plan with search queries |
| 3 | research_agent | `ResearchAgent` | 1 + up to 5 | Calls Gemini per search query (max 5), then 1 call to extract facts |
| 4 | fact_verification | `FactVerificationAgent` | 1 | Cross-checks facts, assigns confidence scores |
| 5 | keyword_extraction | `KeywordExtractionAgent` | 1 | Extracts SEO keywords from research |
| 6 | audience_analysis | `AudienceAnalysisAgent` | 1 | Identifies audience personas, pain points |
| 7 | content_angle | `ContentAngleAgent` | 1 | Generates & selects best content angle |
| 8 | research_summary | `ResearchSummaryAgent` | 1 | Assembles final ResearchPackage |

### LLM Calls: Research Phase

- **Minimum**: 8 (if 0 search queries)
- **Typical**: 12-13 (4-5 search queries + 1 extraction + 7 other agents)
- **Maximum**: 13 (5 queries + 1 extraction + 7 others)

### Output

`ResearchPackage` stored in `WorkflowState.research.metadata["research_package"]`:
- summary (overview, timeline, facts, statistics)
- web_research (facts, statistics, examples, definitions, references)
- keywords, audience, content_angle

### DB: `research` table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Record ID |
| project_id | UUID (FK) | Related project |
| workflow_id | UUID (FK) | Related workflow |
| summary | TEXT | Overview |
| timeline | TEXT (JSON) | Timeline events |
| interesting_facts | TEXT (JSON) | Facts list |
| sources | TEXT (JSON) | Source URLs |
| keywords | TEXT (JSON) | Keywords |
| references | TEXT (JSON) | References |
| statistics | TEXT (JSON) | Statistics dict |
| audience_pain_points | TEXT (JSON) | Pain points |
| version | INTEGER | Version number |
| status | VARCHAR(20) | "completed" |

### Prompt Files
- `backend/src/ai/agents/research/prompts.py` (inline Python templates)

---

## Phase B: Script Workflow

**File**: `backend/src/ai/agents/script/workflow.py`
**Graph**: `ScriptWorkflowGraph` — 8 agents sequential

### Agent Chain

```
NarrativeStrategy → ScriptOutline → HookGenerator → SectionWriter →
Transition → CallToAction → ScriptReview → ScriptOptimization
```

### Agent Details

| # | Agent Name | Class | LLM Calls | What It Does |
|---|-----------|-------|-----------|--------------|
| 1 | narrative_strategy | `NarrativeStrategyAgent` | 1 | Chooses storytelling approach |
| 2 | script_outline | `ScriptOutlineAgent` | 1 | Generates complete outline |
| 3 | hook_generator | `HookGeneratorAgent` | 1 | Generates & selects best hook |
| 4 | section_writer | `SectionWriterAgent` | 1 | Writes all sections |
| 5 | transition | `TransitionAgent` | 1 | Generates smooth transitions |
| 6 | call_to_action | `CallToActionAgent` | 1 | Generates CTAs |
| 7 | script_review | `ScriptReviewAgent` | 1 | Reviews quality |
| 8 | script_optimization | `ScriptOptimizationAgent` | 1 | Assembles final ScriptPackage |

### LLM Calls: Script Phase

- **Total**: 8 (exactly 1 per agent)

### Output

`ScriptPackage` stored in `WorkflowState.script.metadata["script_package"]`:
- narrative_style, outline, hook_result, sections, transitions
- cta_result, full_script, word_count, estimated_duration_seconds

### DB: `scripts` table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Record ID |
| project_id | UUID (FK) | Related project |
| workflow_id | UUID (FK) | Related workflow |
| hook | TEXT | Hook text |
| body | TEXT | Full script body |
| cta | TEXT | Call to action |
| word_count | INTEGER | Word count |
| estimated_duration_seconds | INTEGER | Duration |
| version | INTEGER | Version |
| language | VARCHAR(10) | Language |
| status | VARCHAR(20) | "approved" |

### Prompt Files
- `backend/src/ai/agents/script/prompts.py`

---

## Phase C: Storyboard Workflow

**File**: `backend/src/ai/agents/storyboard/workflow.py`
**Graph**: `StoryboardWorkflowGraph` — 9 agents sequential

### Agent Chain

```
StoryAnalyzer → StoryBeat → SceneSegmentation → VisualStoryboard →
CameraPlanner → AnimationPlanner → AssetDecision → Continuity →
StoryboardReview
```

### Agent Details

| # | Agent Name | Class | LLM Calls | What It Does |
|---|-----------|-------|-----------|--------------|
| 1 | story_analyzer | `StoryAnalyzerAgent` | 1 | Analyzes narrative flow, emotional peaks |
| 2 | story_beat | `StoryBeatAgent` | 1 | Converts script into story beats |
| 3 | scene_segmentation | `SceneSegmentationAgent` | 1 | Splits script into production scenes |
| 4 | visual_storyboard | `StoryboardAgent` | 1 | Visual descriptions per scene |
| 5 | camera_planner | `CameraPlannerAgent` | 1 | Camera angles & movements |
| 6 | animation_planner | `AnimationPlannerAgent` | 1 | Animation plans per scene |
| 7 | asset_decision | `AssetDecisionAgent` | 1 | Asset types (image/video/stock) |
| 8 | continuity | `ContinuityAgent` | 1 | Visual consistency across scenes |
| 9 | storyboard_review | `StoryboardReviewAgent` | 1 | Assembles final StoryboardPackage |

### LLM Calls: Storyboard Phase

- **Total**: 9 (exactly 1 per agent)

### Output

`StoryboardPackage` stored in `WorkflowState.storyboard.metadata["storyboard_package"]`:
- story_analysis, story_beats
- scene_packages (per scene: number, title, duration, narration, visual_plan, camera_plan, asset_type)
- continuity, scene_count, estimated_timeline_minutes

### DB: `storyboards` table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Record ID |
| project_id | UUID (FK) | Related project |
| workflow_id | UUID (FK) | Related workflow |
| version | INTEGER | Version |
| scene_count | INTEGER | Number of scenes |
| estimated_duration_seconds | INTEGER | Total duration |
| style | VARCHAR(50) | Visual style |
| status | VARCHAR(20) | "approved" |
| narrative_structure | TEXT | Narrative flow |
| pacing_notes | TEXT | Pacing notes |

### Prompt Files
- `backend/src/ai/agents/storyboard/prompts.py`

---

## Phase D: Scene Planning

**No LLM calls** — converts `StoryboardPackage` into `Scene` DB rows.

### Code Path

```
_create_step_output(step="scene_planning"):     [workflow_tasks.py:219-225]
  1. Get StoryboardPackage from workflow state
  2. Get latest storyboard from DB (for FK)
  3. For each scene_package:
     → Create Scene entity (scene_number, title, duration, narration,
       visual_type, camera_angle, camera_motion, lens, lighting, etc.)
     → INSERT into "scenes" table
```

### DB: `scenes` table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Scene ID |
| project_id | UUID (FK) | Project |
| storyboard_id | UUID (FK) | Storyboard |
| workflow_id | UUID (FK) | Workflow |
| scene_number | INTEGER | Order |
| title | VARCHAR(300) | Scene title |
| duration_seconds | FLOAT | Duration |
| narration | TEXT | Voiceover text |
| visual_type | VARCHAR(30) | "image"/"video"/"stock_footage" |
| camera_angle | VARCHAR(30) | Camera angle |
| camera_motion | VARCHAR(30) | Camera movement |
| generation_status | VARCHAR(30) | "pending" |
| review_status | VARCHAR(30) | "pending" |

---

## Phases E-K: Placeholder Steps

These steps are defined but have **no real implementation**. They are skipped:

| Step | Project Status | Future Purpose |
|------|---------------|----------------|
| asset_generation | generating | Generate images/videos per scene |
| voice_generation | generating | TTS voiceover per scene |
| subtitle_generation | generating | Subtitles from narration |
| rendering | rendering | Render final video |
| thumbnail | rendering | Generate thumbnail |
| seo | publishing | SEO title/description/tags |

When workflow reaches "completed", total cost and tokens are logged.

---

## Database Tables Overview

### PostgreSQL: `aivideo_studio`

Connection: `postgresql+asyncpg://aivideo:aivideo_secret@aivideo_postgres:5432/aivideo_studio`

### All Tables

| Table | ORM Model | Purpose |
|-------|-----------|---------|
| `users` | `UserModel` | User accounts |
| `roles` | `RoleModel` | RBAC roles |
| `permissions` | `PermissionModel` | RBAC permissions |
| `user_roles` | association | User↔Role |
| `role_permissions` | association | Role↔Permission |
| `refresh_tokens` | `RefreshTokenModel` | JWT refresh tokens |
| `api_keys` | `ApiKeyModel` | API keys |
| `user_sessions` | `UserSessionModel` | Login sessions |
| `password_reset_tokens` | — | Password resets |
| `email_verification_tokens` | — | Email verification |
| `user_preferences` | — | User settings |
| `audit_logs` | `AuditLogModel` | Audit trail |
| `projects` | `ProjectModel` | Video projects |
| `workflows` | `WorkflowModel` | Workflow executions |
| `research` | `ResearchModel` | Research outputs |
| `scripts` | `ScriptModel` | Script outputs |
| `storyboards` | `StoryboardModel` | Storyboard outputs |
| `scenes` | `SceneModel` | Individual scenes |
| `assets` | `AssetModel` | Generated assets (STI) |
| `generation_jobs` | `GenerationJobModel` | Background jobs |
| `prompt_executions` | `PromptExecutionModel` | LLM call audit |
| `cost_records` | `CostRecordModel` | Cost per API call |
| `token_usage_records` | `TokenUsageRecordModel` | Token usage |

### Key Relationships

```
users (1) ──< projects (1) ──< workflows (1)
                      ├──< research (N)
                      ├──< scripts (N)
                      ├──< storyboards (N) ──< scenes (N) ──< assets (N)
                      └──< generation_jobs (N)
```

---

## Total LLM Call Summary

| Phase | Agents | Min Calls | Typical Calls | Max Calls |
|-------|--------|-----------|---------------|-----------|
| Research | 8 | 8 | 12-13 | 13 |
| Script | 8 | 8 | 8 | 8 |
| Storyboard | 9 | 9 | 9 | 9 |
| Scene Planning | 0 | 0 | 0 | 0 |
| **Total** | **25** | **25** | **29-30** | **30** |

### Why Research Has Variable Calls

The `ResearchAgent` (agent #3) makes **1 LLM call per search query** (up to 5 queries from the research plan), plus **1 final call** to extract structured facts. The `ResearchPlannerAgent` (agent #2) determines how many queries to generate — typically 4-5.

### Estimated Cost (Gemini Flash)

- Input: ~$0.0003 per 1K tokens
- Output: ~$0015 per 1K tokens
- Average per call: ~1500 input + ~1700 output tokens
- **Per call cost**: ~$0.003
- **Total workflow cost (30 calls)**: ~**$0.09**

---

## Class & Method Reference

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `ProjectService` | `application/services/project_service.py` | Project CRUD + workflow control |
| `WorkflowEngine` | `workflow/engine.py` | Orchestrates graph execution |
| `ServiceContainer` | `application/di/container.py` | Dependency injection |
| `LLMGateway` | `ai/gateway/llm_gateway.py` | Unified LLM interface |
| `PromptExecutor` | `ai/agents/prompt_executor.py` | Renders prompts, calls LLM |
| `OutputValidator` | `ai/agents/output_validator.py` | Validates JSON output |
| `QualityEvaluator` | `ai/agents/quality.py` | Scores agent output |
| `BaseAgent` | `ai/agents/base.py` | Agent lifecycle |
| `BaseWorkflowGraph` | `workflow/base_graph.py` | Graph construction & execution |
| `ResearchWorkflowGraph` | `ai/agents/research/workflow.py` | 8-agent research pipeline |
| `ScriptWorkflowGraph` | `ai/agents/script/workflow.py` | 8-agent script pipeline |
| `StoryboardWorkflowGraph` | `ai/agents/storyboard/workflow.py` | 9-agent storyboard pipeline |
| `GeminiLLMProvider` | `ai/providers/gemini.py` | Google Gemini API client |
| `LangfuseClient` | `infrastructure/observability/langfuse_client.py` | LLM tracing |

### Key Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `create_project()` | `ProjectService` | Create project in DB |
| `start_workflow()` | `ProjectService` | Create workflow, dispatch Celery task |
| `advance_workflow()` | `ProjectService` | Move to next step, update DB |
| `execute_workflow_task()` | celery task | Entry point for Celery worker |
| `_run_workflow()` | `workflow_tasks.py` | Main step loop |
| `_create_step_output()` | `workflow_tasks.py` | Execute graph for each step |
| `execute()` | `WorkflowEngine` | Run a workflow graph |
| `run_agent()` | `BaseAgent` | Full agent lifecycle |
| `generate()` | `LLMGateway` | Call Gemini API |
| `execute_template()` | `PromptExecutor` | Render prompt + call LLM |
| `validate()` | `OutputValidator` | Check JSON output |
| `_clean_json_output()` | `output_validator.py` | Strip markdown fences from LLM output |
