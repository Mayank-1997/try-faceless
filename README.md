# AI Video Studio

Autonomous AI-powered YouTube Content Studio — generates complete long-form YouTube videos from a topic or existing script with minimal human interaction.

## Architecture

The system follows **Clean Architecture** with clear layer separation:

| Layer | Responsibility |
|-------|---------------|
| **Presentation** | FastAPI routers, middleware, exception handlers |
| **Application** | DI container, DTOs, cost/token trackers, event bus |
| **Domain** | Entities, value objects, repository interfaces, domain exceptions |
| **Infrastructure** | Database engine, Redis, Celery, storage gateway, observability |
| **Persistence** | SQLAlchemy models, repository implementations, Alembic |
| **AI** | LLM/Image/Video/Voice gateways, provider registry, prompt manager, providers |
| **Workflow** | LangGraph orchestration, strongly-typed WorkflowState |
| **Rendering** | Rendering gateway, FFmpeg renderer |
| **Publishing** | YouTube API, SEO optimization, analytics |
| **Core** | ConfigService, interfaces, logging, correlation IDs, constants, enums, exceptions |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, LangGraph, SQLAlchemy 2, Celery, Pydantic V2
- **Database**: PostgreSQL 16, Redis 7
- **AI**: Gemini 2.5 Pro/Flash, Google Veo, Imagen 3, Google TTS
- **Video**: FFmpeg
- **Frontend**: NextJS, TypeScript, TailwindCSS, Shadcn UI
- **Infra**: Docker, Docker Compose

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env
# Fill in API keys (Gemini, YouTube, etc.)

# 2. Start infrastructure
docker-compose up -d postgres redis

# 3. Install backend dependencies
cd backend
pip install -e ".[dev]"

# 4. Run database migrations
alembic upgrade head

# 5. Start the API server
uvicorn src.presentation.main:app --reload

# 6. Start Celery workers (in separate terminals)
celery -A src.infrastructure.tasks.celery_app worker --loglevel=INFO
celery -A src.infrastructure.tasks.celery_app beat --loglevel=INFO
```

## Project Structure

```
ai-video-studio/
├── backend/
│   ├── src/
│   │   ├── core/           # Config, constants, enums, exceptions, logging
│   │   ├── domain/         # Entities, value objects, repository interfaces
│   │   ├── application/    # Services, DTOs
│   │   ├── presentation/   # FastAPI routers, middleware
│   │   ├── infrastructure/ # DB engine, Redis, Celery
│   │   ├── persistence/    # SQLAlchemy models, repositories
│   │   ├── ai/             # Agents, providers, prompts
│   │   ├── workflow/       # LangGraph workflow
│   │   ├── rendering/      # FFmpeg
│   │   └── publishing/     # YouTube, SEO
│   ├── prompts/            # Versioned prompt templates
│   ├── alembic/            # Database migrations
│   ├── tests/              # Unit, integration, mock AI, API tests
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/               # NextJS application (Phase 9)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Development Phases

1. **Phase 1** — Foundation Architecture ✅ (ConfigService, DI, Gateways, Registry, Prompts, Storage, Rendering, Cost/Token Tracking, Event Bus, Observability, WorkflowState, Testing)
2. **Phase 2** — Authentication & User Management ✅ (IAM module: JWT auth, RBAC, users, roles, permissions, sessions, API keys, audit logging)
3. **Phase 3** — Persistence Layer ✅ (Business domain entities, ORM models, repositories, UoW, specifications, migrations)
4. **Phase 4** — Orchestration Framework ✅ (LangGraph workflow engine, BaseNode, BaseWorkflowGraph, GraphRegistry, WorkflowBuilder, checkpointing, retry policies, event emission, contexts)
5. **Phase 5** — AI Agent Framework ✅ (BaseAgent, AgentContext, PromptExecutor, OutputValidator, QualityEvaluator, ArtifactManager, AgentMemory, ToolRegistry, AgentRegistry, events)
6. **Phase 6** — Topic Discovery & Research System ✅ (8 research agents, ResearchPackage schema, ResearchWorkflowGraph, research events, prompt templates, 63 tests)
7. **Phase 7** — Script Generation System ✅ (8 script agents, ScriptPackage schema, ScriptWorkflowGraph, script events, prompt templates, 64 tests)
8. **Phase 8** — Storyboard & Scene Planning System ✅ (9 storyboard agents, StoryboardPackage schema, StoryboardWorkflowGraph, storyboard events, prompt templates, 74 tests)
9. **Phase 9** — Generation Platform & Intelligent Asset Generation ✅ (GenerationStrategyEngine, GenerationOrchestrator, QueueManager, ProviderSelectionEngine, BudgetManager, ConcurrencyManager, ProviderHealthMonitor, CacheManager, GenerationExecutor, ValidationPipeline, QualityEngine, AssetManifestBuilder, SubtitleGenerator, ThumbnailGenerator, generation events, 142 tests)
10. **Phase 10** — Video Composition Platform & Rendering Engine ✅ (CompositionDocument, CompositionBuilder, CompositionValidator, RenderPlanner, CompositionOptimizer, TimelineCompiler, CompositionRenderer abstraction, FFmpegCompositionRenderer, RenderingPipeline, ExportEngine, ProjectPackage, RenderCache, PreviewEngine, QualityValidator, RenderQueue, ProgressTracker, TrackSystem, CameraMotionEngine, ImageAnimationEngine, TransitionEngine, VideoEffectsEngine, TextEngine, SubtitleEngine, AudioMixer, MediaSynchronizer, composition events, 212 tests)
11. **Phase 11** — Publishing & Distribution Platform ✅ (Publisher interface, YouTubePublisher, PublishingPlanner, PublishingStrategyEngine, PublishingQueue, SchedulingEngine, MetadataEngine, ThumbnailManager, PublishingValidator, AuthenticationManager, ProgressTracker, PublishingReport, publishing events, 167 tests)
12. **Phase 12** — Platform Services, Analytics & SaaS Foundation ✅ (AnalyticsService, UsageTracker, BillingService, CostAnalyticsService, OrganizationService, NotificationService, FeatureFlagService, PlatformAuditService, MonitoringService, HealthService, MetricsService, ApiManagementService, AdminService, 192 tests)
13. **Phase 13** — API Layer (FastAPI, JWT auth, CRUD)
14. **Phase 14** — Frontend (NextJS dashboard)
15. **Phase 15** — Testing & Observability

## Phase 1 Modules

| Module | File | Description |
|--------|------|-------------|
| **ConfigService** | `src/core/config_service.py` | Centralized config with feature flags, runtime overrides |
| **DI Container** | `src/application/di/container.py` | ServiceContainer with lifecycle management |
| **DI Providers** | `src/application/di/dependencies.py` | FastAPI `Depends()` providers |
| **Base Interfaces** | `src/core/interfaces.py` | LLMProvider, ImageProvider, VideoProvider, VoiceProvider, Renderer, StorageProvider, PromptLoader, CostCalculator |
| **Extended Exceptions** | `src/core/exceptions.py` | GatewayError, ProviderException, PromptException, RegistryError, EventBusError, etc. |
| **Response Models** | `src/application/dto/responses.py` | Success, Failure, Progress, Streaming, GenerationResult, RetryResult |
| **LLM Gateway** | `src/ai/gateway/llm_gateway.py` | Unified LLM interface with fallback, retries, caching |
| **Image Gateway** | `src/ai/gateway/image_gateway.py` | Unified image generation |
| **Video Gateway** | `src/ai/gateway/video_gateway.py` | Unified video generation |
| **Voice Gateway** | `src/ai/gateway/voice_gateway.py` | Unified voice generation |
| **Provider Registry** | `src/ai/providers/registry.py` | Configuration-driven provider switching |
| **Gemini Provider** | `src/ai/providers/gemini.py` | Google Gemini LLM implementation |
| **Imagen Provider** | `src/ai/providers/imagen.py` | Google Imagen image generation |
| **Veo Provider** | `src/ai/providers/veo.py` | Google Veo video generation |
| **Google TTS Provider** | `src/ai/providers/google_tts.py` | Google Cloud TTS implementation |
| **Prompt Manager** | `src/ai/prompts/prompt_manager.py` | Prompt loading, versioning, rendering, caching |
| **Storage Gateway** | `src/infrastructure/storage/gateway.py` | Abstract file storage |
| **Local Storage** | `src/infrastructure/storage/local.py` | Local filesystem storage |
| **Rendering Gateway** | `src/rendering/gateway.py` | Abstract rendering interface |
| **FFmpeg Renderer** | `src/rendering/ffmpeg.py` | FFmpeg implementation (merge, concatenate, subtitles, thumbnail) |
| **Cost Tracker** | `src/application/services/cost_tracker.py` | Per-project/agent/user/provider cost tracking |
| **Token Tracker** | `src/application/services/token_tracker.py` | Input/output/cached token tracking |
| **Event Bus** | `src/application/services/event_bus.py` | Async pub/sub for loose coupling |
| **Metrics Collector** | `src/infrastructure/observability/metrics.py` | Execution time, retries, failures, success rate |
| **WorkflowState** | `src/workflow/state.py` | Strongly-typed Pydantic state for LangGraph |
| **Correlation IDs** | `src/core/correlation.py` | Request-scoped tracing context |
| **Correlation Middleware** | `src/presentation/middleware/correlation.py` | Auto-injects X-Correlation-ID |

## Phase 2 Modules — IAM

| Module | File | Description |
|--------|------|-------------|
| **IAM Enums** | `src/core/enums.py` | UserStatus, AuthProvider, ApiKeyStatus, SessionStatus, TokenType, AuditAction, ThemePreference, DefaultRoleName |
| **User Entity** | `src/domain/entities/user.py` | User aggregate root with status management, profile, roles |
| **Role Entity** | `src/domain/entities/role.py` | RBAC role with permission grouping |
| **Permission Entity** | `src/domain/entities/permission.py` | Granular authorization action |
| **Session Entity** | `src/domain/entities/session.py` | User session with device/browser/IP tracking |
| **API Key Entity** | `src/domain/entities/api_key.py` | Hashed API key with scopes and expiration |
| **Refresh Token Entity** | `src/domain/entities/refresh_token.py` | JWT refresh token with rotation support |
| **Preferences Entity** | `src/domain/entities/preferences.py` | Per-user application settings |
| **Audit Log Entity** | `src/domain/entities/audit_log.py` | Immutable security event record |
| **Token Entities** | `src/domain/entities/tokens.py` | Password reset and email verification tokens |
| **Auth Exceptions** | `src/domain/exceptions/auth_exceptions.py` | 25+ IAM-specific exception classes |
| **Repository Interfaces** | `src/domain/repositories/auth_repositories.py` | 9 abstract repository contracts |
| **ORM Models** | `src/persistence/models/auth.py` | 12 SQLAlchemy models (users, roles, permissions, sessions, etc.) |
| **Repository Implementations** | `src/persistence/repositories/auth_repositories.py` | 9 SQLAlchemy repository implementations |
| **Auth DTOs** | `src/application/dto/auth_dtos.py` | Pydantic V2 request/response DTOs |
| **Password Service** | `src/application/services/password_service.py` | bcrypt hashing, verification, strength validation |
| **Token Service** | `src/application/services/token_service.py` | JWT creation, validation, rotation |
| **Authentication Service** | `src/application/services/authentication_service.py` | Login, register, refresh, logout, password reset |
| **Authorization Service** | `src/application/services/authorization_service.py` | RBAC checking, FastAPI dependencies |
| **User Service** | `src/application/services/user_service.py` | Profile management, preferences |
| **API Key Service** | `src/application/services/api_key_service.py` | API key CRUD and validation |
| **Session Service** | `src/application/services/session_service.py` | Session listing and revocation |
| **Audit Service** | `src/application/services/audit_service.py` | Audit log recording and querying |
| **Role Service** | `src/application/services/role_service.py` | Role/Permission CRUD, default seeding |
| **Auth Middleware** | `src/presentation/middleware/auth.py` | JWT/API key validation, request context |
| **Auth Router** | `src/presentation/routers/auth.py` | /auth/* endpoints |
| **Users Router** | `src/presentation/routers/users.py` | /users/* endpoints |
| **API Keys Router** | `src/presentation/routers/api_keys.py` | /api-keys/* endpoints |
| **Sessions Router** | `src/presentation/routers/sessions.py` | /sessions/* endpoints |
| **Exception Handler** | `src/presentation/handlers/auth_handlers.py` | Maps AppError to structured JSON |

## Phase 3 Modules — Business Domain & Persistence

| Module | File | Description |
|--------|------|-------------|
| **Business Enums** | `src/core/enums.py` | ProjectStatus, WorkflowStatus, WorkflowStep, ResearchStatus, ScriptStatus, StoryboardStatus, SceneGenerationStatus, SceneReviewStatus, AssetType, AssetGenerationStatus, StorageType, JobType, JobStatus, JobPriority, PromptExecutionStatus, AIProvider, ContentType, VideoStyle |
| **Project Entity** | `src/domain/entities/project.py` | Project aggregate root with status, tags, metadata, soft-delete |
| **Workflow Entity** | `src/domain/entities/workflow.py` | Workflow with step tracking, retry, checkpoint, execution time |
| **Research Entity** | `src/domain/entities/research.py` | Research version with sources, keywords, statistics, pain points |
| **Script Entity** | `src/domain/entities/script.py` | Script version with hook, body, CTA, word count, duration estimate |
| **Storyboard Entity** | `src/domain/entities/storyboard.py` | Storyboard version with scene count, narrative structure, pacing |
| **Scene Entity** | `src/domain/entities/scene.py` | Scene with narration, camera, lighting, composition, transitions, review |
| **Asset Entities** | `src/domain/entities/asset.py` | BaseAsset + ImageAsset, VideoAsset, VoiceAsset, SubtitleAsset, ThumbnailAsset |
| **Generation Job Entity** | `src/domain/entities/generation_job.py` | Job with type, status, priority, payload, result, retry tracking |
| **Prompt Execution Entity** | `src/domain/entities/prompt_execution.py` | LLM call tracking with tokens, cost, latency, status |
| **Cost Tracking Entity** | `src/domain/entities/cost_tracking.py` | CostRecord with provider, category, period, metadata |
| **Token Tracking Entity** | `src/domain/entities/token_tracking.py` | TokenUsageRecord with input/output/cached tokens |
| **Business Exceptions** | `src/domain/exceptions/business_exceptions.py` | Domain exceptions for all business entities |
| **Repository Interfaces** | `src/domain/repositories/business_repositories.py` | Abstract repository contracts for all aggregates |
| **Specification Pattern** | `src/domain/repositories/specifications.py` | Composable query predicates (AND, OR, NOT) for reusable queries |
| **ORM Models** | `src/persistence/models/business.py` | SQLAlchemy models with single-table inheritance for assets |
| **Repository Implementations** | `src/persistence/repositories/business_repositories.py` | Async CRUD + query repositories with ORM-to-domain mappers |
| **Unit of Work** | `src/persistence/unit_of_work.py` | Async context manager for transactional consistency |
| **Business DTOs** | `src/application/dto/business_dtos.py` | Pydantic V2 request/response DTOs with entity-to-DTO mappers |
| **Alembic Migration** | `alembic/versions/0002_business_domain.py` | Creates 11 business domain tables with indexes and FKs |
| **Unit Tests** | `tests/unit/test_business_repositories.py` | 61 tests covering CRUD, inheritance, specifications, entity behavior |

## Phase 4 Modules — Orchestration Framework

| Module | File | Description |
|--------|------|-------------|
| **Workflow Exceptions** | `src/workflow/exceptions.py` | WorkflowExecutionError, NodeExecutionError, CheckpointError, WorkflowNotFoundError, error classification |
| **Extended WorkflowState** | `src/workflow/state.py` | NodeExecutionRecord, WorkflowMetadata, extended ExecutionStatus with node history, checkpoint ref, retry count |
| **Contexts** | `src/workflow/contexts.py` | IdentityContext, ExecutionContext, CancellationToken, NodeContext, WorkflowContext with DI |
| **Retry Policy** | `src/workflow/retry_policy.py` | RetryPolicy with exponential backoff + jitter, RetryExecutor, preset policies (STANDARD, AGGRESSIVE, CONSERVATIVE) |
| **BaseNode** | `src/workflow/base_node.py` | Abstract node with validation, retry, lifecycle hooks, cost/token tracking, metrics recording |
| **BaseWorkflowGraph** | `src/workflow/base_graph.py` | Abstract graph with nodes, edges, conditional routing, parallel execution, LangGraph integration |
| **Checkpoint Manager** | `src/workflow/checkpoint.py` | CheckpointMetadata, save/restore/list/delete, LangGraph MemorySaver integration |
| **Event Emitter** | `src/workflow/events.py` | WorkflowEventEmitter for workflow/node lifecycle events on EventBus |
| **Graph Registry** | `src/workflow/registry.py` | Versioned workflow registration, lookup, listing, unregister |
| **Workflow Engine** | `src/workflow/engine.py` | Central orchestrator: execute, cancel, resume, timeout, metrics, execution history |
| **Workflow Builder** | `src/workflow/builder.py` | Fluent builder API for constructing workflow graphs without subclassing |
| **Unit Tests** | `tests/unit/test_workflow_orchestration.py` | 97 tests covering contexts, retry, nodes, graphs, registry, checkpoints, events, engine, builder |

## Phase 5 Modules — AI Agent Framework

| Module | File | Description |
|--------|------|-------------|
| **Agent Exceptions** | `src/ai/agents/exceptions.py` | AgentExecutionError, PromptExecutionError, OutputValidationError, QualityThresholdError, ArtifactError, ToolExecutionError, AgentNotFoundError |
| **AI Response** | `src/ai/agents/response.py` | Standard AIResponse model with success, response, structured data, cost, tokens, latency, provider, model, warnings, errors |
| **Agent Context** | `src/ai/agents/context.py` | AgentContext with identity, state, execution, LLM gateway, prompt executor, validators, memory, tools, event bus, cancellation |
| **Prompt Template** | `src/ai/agents/prompt_template.py` | PromptTemplate with versioning, variables, defaults, metadata, validation, rendering; PromptVariable and PromptTemplateMetadata |
| **Prompt Executor** | `src/ai/agents/prompt_executor.py` | PromptExecutor with template execution, raw prompt, file-based prompts, JSON parsing, history tracking, cost/token metrics |
| **Output Validator** | `src/ai/agents/output_validator.py` | OutputValidator with JSON/schema/required-fields validation, business rules, repair support; ValidationResult and BusinessRule |
| **Quality Evaluator** | `src/ai/agents/quality.py` | QualityEvaluator with completeness, length, consistency, readability, relevance, accuracy dimensions; QualityResult with pass/fail and grade |
| **Artifact Manager** | `src/ai/agents/artifact.py` | ArtifactManager with store/get/list/delete by agent, type, execution; Artifact model with content, metadata, tags |
| **Agent Memory** | `src/ai/agents/memory.py` | AgentMemory abstract interface + InMemoryAgentMemory; MemoryEntry with TTL; MemoryScope constants (short-term, workflow, execution, shared) |
| **Tools** | `src/ai/agents/tools.py` | Tool abstract interface, ToolRegistry, ToolMetadata, ToolParameter, ToolResult; for future web search, calculator, browser tools |
| **Agent Events** | `src/ai/agents/events.py` | AgentEventEmitter with 9 event types: AgentStarted, PromptGenerated, PromptExecuted, ValidationFailed, RetryTriggered, AgentCompleted, AgentFailed, ArtifactsCreated, QualityEvaluated |
| **Base Agent** | `src/ai/agents/base.py` | BaseAgent abstract class extending BaseNode with full lifecycle: initialize → validate → prompt → AI → validate output → quality → artifacts → events → update state |
| **Agent Registry** | `src/ai/agents/registry.py` | AgentRegistry with versioned registration, lookup by name/version, list by type, metadata inspection |
| **Unit Tests** | `tests/unit/test_agent_framework.py` | 143 tests covering AIResponse, AgentContext, PromptTemplate, PromptExecutor, OutputValidator, QualityEvaluator, ArtifactManager, AgentMemory, Tools, AgentRegistry, AgentEventEmitter, exceptions, BaseAgent |

## Phase 6 Modules — Topic Discovery & Research System

| Module | File | Description |
|--------|------|-------------|
| **Research Schema** | `src/ai/agents/research/schema.py` | ResearchPackage, TopicAnalysis, ResearchPlan, WebResearchResult, FactVerificationResult, KeywordSet, AudienceAnalysisResult, ContentAngleResult, ResearchSummary — all Pydantic v2 models |
| **Research Prompts** | `src/ai/agents/research/prompts.py` | 8 versioned prompt templates for all research agents with JSON output expectations |
| **Topic Analyzer** | `src/ai/agents/research/topic_analyzer.py` | Analyzes user topic: category, difficulty, content type, longevity, research depth, missing info |
| **Research Planner** | `src/ai/agents/research/research_planner.py` | Creates research plan with sections, search queries, source diversity, fact requirements |
| **Research Agent** | `src/ai/agents/research/research_agent.py` | Gathers facts, statistics, examples, historical events, definitions from web search or LLM |
| **Fact Verification** | `src/ai/agents/research/fact_verification.py` | Cross-checks facts, removes conflicts, flags uncertain claims, assigns confidence scores |
| **Keyword Extraction** | `src/ai/agents/research/keyword_extraction.py` | Extracts primary, secondary, semantic, long-tail keywords, entities, concepts, SEO tags |
| **Audience Analysis** | `src/ai/agents/research/audience_analysis.py` | Identifies audience personas, knowledge level, pain points, questions, reading level |
| **Content Angle** | `src/ai/agents/research/content_angle.py` | Generates 5+ content angles (educational, storytelling, comparison, etc.) and selects best |
| **Research Summary** | `src/ai/agents/research/research_summary.py` | Generates structured summary and assembles final ResearchPackage |
| **Research Workflow** | `src/ai/agents/research/workflow.py` | ResearchWorkflowGraph chaining 8 agents sequentially via BaseWorkflowGraph |
| **Research Events** | `src/ai/agents/research/events.py` | 9 research-specific events: ResearchStarted, TopicAnalyzed, ResearchPlanned, etc. |
| **Unit Tests** | `tests/unit/test_research_agents.py` | 63 tests covering all schemas, 8 agents, workflow graph, events, prompts, full pipeline integration |

## Phase 7 Modules — Script Generation System

| Module | File | Description |
|--------|------|-------------|
| **Script Schema** | `src/ai/agents/script/schema.py` | ScriptPackage, NarrativeStrategy, ScriptOutline, OutlineSection, Hook, HookResult, ScriptSection, TransitionResult, CallToAction, CTAResult, ScriptReviewResult, ScriptOptimizationResult, ScriptQualityEvaluation — all Pydantic v2 models |
| **Script Prompts** | `src/ai/agents/script/prompts.py` | 8 versioned prompt templates for all script agents with JSON output expectations |
| **Narrative Strategy** | `src/ai/agents/script/narrative_strategy.py` | Chooses storytelling style, flow, pacing, tone based on audience, topic, duration |
| **Script Outline** | `src/ai/agents/script/script_outline.py` | Generates complete outline with sections, subsections, talking points, timing, word counts |
| **Hook Generator** | `src/ai/agents/script/hook_generator.py` | Generates 6+ hooks (question, bold statement, unexpected fact, story, contradiction, curiosity gap), selects best |
| **Section Writer** | `src/ai/agents/script/section_writer.py` | Writes individual sections with narration, facts, examples, emotional pacing, references; supports parallel execution |
| **Transition** | `src/ai/agents/script/transition.py` | Generates smooth transitions between sections, ensures natural flow, assigns smoothness score |
| **Call to Action** | `src/ai/agents/script/call_to_action.py` | Generates CTAs (subscribe, like, comment, visit website, download, newsletter), matches channel style |
| **Script Review** | `src/ai/agents/script/script_review.py` | Validates logic, flow, completeness, consistency, fact usage, audience alignment, length, reading level |
| **Script Optimization** | `src/ai/agents/script/script_optimization.py` | Improves retention, clarity, redundancy, sentence variety, natural speech, engagement; assembles final ScriptPackage |
| **Script Workflow** | `src/ai/agents/script/workflow.py` | ScriptWorkflowGraph chaining 8 agents sequentially via BaseWorkflowGraph |
| **Script Events** | `src/ai/agents/script/events.py` | 10 script-specific events: ScriptStarted, NarrativeStrategySelected, OutlineGenerated, HookSelected, etc. |
| **Unit Tests** | `tests/unit/test_script_agents.py` | 64 tests covering all schemas, 8 agents, workflow graph, events, prompts, full pipeline integration |

## Phase 8 Modules — Storyboard & Scene Planning System

| Module | File | Description |
|--------|------|-------------|
| **Storyboard Schema** | `src/ai/agents/storyboard/schema.py` | StoryboardPackage, StoryAnalysis, StoryBeat, StoryBeatResult, PlannedScene, SceneSegmentationResult, VisualPlan, VisualStoryboardResult, CameraPlan, CameraPlanResult, AnimationPlan, AnimationPlanResult, AssetSceneDecision, AssetDecisionResult, ContinuityResult, StoryboardReviewResult, StoryboardQualityEvaluation, ScenePackage — all Pydantic v2 models |
| **Storyboard Prompts** | `src/ai/agents/storyboard/prompts.py` | 9 versioned prompt templates for all storyboard agents with JSON output expectations |
| **Story Analyzer** | `src/ai/agents/storyboard/story_analyzer.py` | Analyzes narrative flow, emotional peaks, pacing, scene boundaries, visual opportunities |
| **Story Beat** | `src/ai/agents/storyboard/story_beat.py` | Converts script into story beats (introduction, conflict, explanation, reveal, transition, conclusion) |
| **Scene Segmentation** | `src/ai/agents/storyboard/scene_segmentation.py` | Splits script into production scenes with scene numbers, timestamps, narration, goals, types |
| **Visual Storyboard** | `src/ai/agents/storyboard/storyboard_visual.py` | Generates visual descriptions: composition, foreground, background, objects, mood, lighting, color palette |
| **Camera Planner** | `src/ai/agents/storyboard/camera_planner.py` | Plans camera angles, distances, lenses, movements, motion speed, focus points |
| **Animation Planner** | `src/ai/agents/storyboard/animation_planner.py` | Plans element, text, camera, object, background animations with timing and transitions |
| **Asset Decision** | `src/ai/agents/storyboard/asset_decision.py` | Decides asset types (AI image, AI video, stock, diagram, etc.) with confidence scores and cost estimates |
| **Continuity** | `src/ai/agents/storyboard/continuity.py` | Ensures visual consistency: characters, colors, objects, style, camera, aspect ratio, lighting, brand |
| **Storyboard Review** | `src/ai/agents/storyboard/storyboard_review.py` | Reviews storyboard quality and assembles final StoryboardPackage with per-scene ScenePackage objects |
| **Storyboard Workflow** | `src/ai/agents/storyboard/workflow.py` | StoryboardWorkflowGraph chaining 9 agents sequentially via BaseWorkflowGraph |
| **Storyboard Events** | `src/ai/agents/storyboard/events.py` | 11 storyboard-specific events: StoryboardStarted, StoryAnalyzed, BeatsGenerated, ScenesPlanned, etc. |
| **Unit Tests** | `tests/unit/test_storyboard_agents.py` | 74 tests covering all schemas, 9 agents, workflow graph, events, prompts, full pipeline integration |

## Phase 9 Modules — Generation Platform & Intelligent Asset Generation

| Module | File | Description |
|--------|------|-------------|
| **Generation Schema** | `src/generation/schema.py` | GenerationMode, AssetCategory, JobStatus, JobPriority, ValidationStage enums; GenerationStrategy, GenerationRequest, GenerationJob, ProviderHealthMetrics, BudgetEstimate, BudgetStatus, ValidationResult, ValidationReport, QualityResult, GeneratedAsset, SceneAssetManifest, AssetManifest, GenerationProgress, CacheKey, CacheEntry — all Pydantic v2 models |
| **Generation Events** | `src/generation/events.py` | 9 generation lifecycle events: GenerationStarted, GenerationCompleted, GenerationFailed, RetryTriggered, ProviderChanged, BudgetExceeded, AssetStored, ValidationFailed, ManifestCompleted |
| **Strategy Engine** | `src/generation/strategy.py` | GenerationStrategyEngine with economy, balanced, premium, fast, custom modes; controls image/video ratio, provider/model selection, resolution, retry, concurrency, cost, quality, priority |
| **Queue Manager** | `src/generation/queue_manager.py` | Priority-based async job queue with retry queue, dead letter queue, cancellation, pause/resume |
| **Provider Selection** | `src/generation/provider_selection.py` | ProviderSelectionEngine scoring cost, latency, availability, quality, preference; automatic fallback chain |
| **Health Monitor** | `src/generation/health.py` | ProviderHealthMonitor tracking latency, timeouts, failures, availability, cost, quality, quota; auto-disable unhealthy providers |
| **Budget Manager** | `src/generation/budget.py` | BudgetManager with project/scene/category cost tracking, budget enforcement, video→image downgrade recommendations |
| **Concurrency Manager** | `src/generation/concurrency.py` | ConcurrencyManager with global/provider/project semaphores, daily/monthly quotas, adaptive throttling |
| **Cache Manager** | `src/generation/cache.py` | CacheManager with deterministic cache keys (prompt, provider, model, aspect ratio, resolution, duration, seed, style, prompt version), TTL, eviction |
| **Generation Executor** | `src/generation/executor.py` | The ONLY component that calls AI providers; wraps image/video/voice gateways; handles caching, retry, health, concurrency, storage upload, event emission |
| **Validation Pipeline** | `src/generation/validation.py` | 10-stage validation: file, metadata, resolution, duration, prompt alignment, quality, duplicate detection, storage, content safety |
| **Quality Engine** | `src/generation/quality.py` | QualityEngine evaluating visual quality, prompt alignment, voice quality, subtitle accuracy, consistency, brand compliance; category-specific weighted scoring |
| **Orchestrator** | `src/generation/orchestrator.py` | GenerationOrchestrator: submit requests, select providers, estimate costs, check budgets, create jobs, enqueue, process queue, validate, evaluate quality, track progress |
| **Asset Manifest** | `src/generation/manifest.py` | AssetManifestBuilder: groups assets by scene, computes per-scene and project-level totals (duration, cost, assets, render time), produces final AssetManifest for Rendering Engine |
| **Subtitle Generator** | `src/generation/subtitle.py` | SubtitleGenerator producing SRT and VTT formats with sentence-level timestamps, word-level timing, line wrapping |
| **Thumbnail Generator** | `src/generation/thumbnail.py` | ThumbnailGenerator producing thumbnail prompts, variations, clickability scores; no text inside thumbnails |
| **Unit Tests** | `tests/unit/test_generation_platform.py` | 142 tests covering all schemas, strategy engine, queue manager, provider selection, health monitor, budget manager, concurrency, cache, executor, validation pipeline, quality engine, orchestrator, manifest builder, subtitle generator, thumbnail generator, events, full pipeline integration |

## Phase 10 Modules — Video Composition Platform & Rendering Engine

| Module | File | Description |
|--------|------|-------------|
| **Composition Schema** | `src/composition/schema.py` | TrackType, LayerType, TransitionType, EasingType, CameraMotionType, ImageAnimationType, VideoEffectType, TextType, SubtitleFormat, ExportFormat, ExportResolution, RenderStatus, RenderPriority enums; TimelineClip, Track, Timeline, CompositionScene, CameraMotion, ImageAnimation, Transition, VideoEffect, TextOverlay, SubtitleConfig, AudioTrack, AudioMixConfig, ExportProfile, EncodingProfile, RenderingMetadata, ValidationMetadata, CompositionDocument, RenderPlan, RenderMetrics, QualityReport, RenderJob, RenderProgress, RenderCacheEntry, ProjectPackage, PreviewResult — all Pydantic v2 models |
| **Composition Events** | `src/composition/events.py` | 9 composition lifecycle events: CompositionCreated, CompositionValidated, RenderPlanned, RenderingStarted, EncodingStarted, EncodingCompleted, RenderingCompleted, RenderingFailed, ProjectPackageGenerated |
| **Track System** | `src/composition/tracks.py` | TrackSystem managing unlimited tracks (video, image, voice, music, SFX, subtitle, overlay, animation, custom) with layer ordering |
| **Camera Motion Engine** | `src/composition/camera.py` | CameraMotionEngine supporting pan, zoom, tilt, orbit, Ken Burns, parallax, custom paths with easing; FFmpeg zoompan/crop filter generation |
| **Image Animation Engine** | `src/composition/animation.py` | ImageAnimationEngine supporting scale, translate, rotate, opacity, crop, depth illusion, parallax, motion presets; FFmpeg filter generation |
| **Transition Engine** | `src/composition/transitions.py` | TransitionEngine supporting fade, crossfade, slide, push, zoom, blur, dissolve, custom; FFmpeg xfade filter generation |
| **Video Effects Engine** | `src/composition/effects.py` | VideoEffectsEngine supporting brightness, contrast, color correction, blur, sharpen, glow, noise reduction, vignette, LUT; FFmpeg filter generation |
| **Text Engine** | `src/composition/text.py` | TextEngine supporting titles, lower thirds, captions, credits, watermarks, callouts, animated text; FFmpeg drawtext filter generation |
| **Subtitle Engine** | `src/composition/subtitles.py` | SubtitleEngine supporting SRT, VTT, ASS formats with word/sentence highlighting, speaker labels, multiple languages, animated subtitles; SRT/VTT generation |
| **Audio Mixer** | `src/composition/audio.py` | AudioMixer supporting voice normalization, music ducking, fade in/out, crossfade, volume balancing; FFmpeg audio filter generation |
| **Media Synchronizer** | `src/composition/synchronizer.py` | MediaSynchronizer ensuring voice, video, images, music, effects, subtitles, and animations are properly aligned; detects and reports sync issues |
| **Composition Builder** | `src/composition/builder.py` | CompositionBuilder transforming AssetManifest into CompositionDocument with timeline, tracks, scenes, camera motions, image animations, transitions, audio config, subtitle config, export profile |
| **Composition Validator** | `src/composition/validator.py` | CompositionValidator with 10 validation stages: timeline integrity, missing assets, broken references, track overlaps, subtitle timing, audio sync, transition conflicts, animation conflicts, scene ordering, export settings |
| **Render Planner** | `src/composition/planner.py` | RenderPlanner estimating execution time, CPU, memory, disk, GPU usage, rendering complexity, output size, bottlenecks, optimization suggestions; identifies parallelizable segments |
| **Composition Optimizer** | `src/composition/optimizer.py` | CompositionOptimizer optimizing layer ordering, animation scheduling, subtitle placement, audio synchronization, asset loading order, rendering order, memory usage |
| **Timeline Compiler** | `src/composition/timeline_compiler.py` | TimelineCompiler resolving overlaps, generating frame-accurate timestamps, compiling scene data, generating per-clip rendering instructions with camera, animation, and effect metadata |
| **Renderer Abstraction** | `src/composition/renderer.py` | CompositionRenderer abstract base class: load, validate, prepare, render, monitor, cancel, cleanup, collect_metrics, validate_output — renderer-independent interface |
| **FFmpeg Renderer** | `src/composition/ffmpeg_renderer.py` | FFmpegCompositionRenderer implementing CompositionRenderer with FFmpeg command builder, progress monitoring, retry support, failure recovery, metrics collection, hardware acceleration hooks (NVENC/QSV) |
| **Rendering Pipeline** | `src/composition/pipeline.py` | RenderingPipeline orchestrating 13 stages: load, validate, prepare, compile, optimize, render, validate output, generate project package; emits events at each stage |
| **Export Engine** | `src/composition/export.py` | ExportEngine with encoding presets (1080p, 1440p, 4K, square, portrait), custom profile creation, preview profile generation, metadata generation |
| **Quality Validator** | `src/composition/quality.py` | QualityValidator checking resolution, duration, subtitle sync, audio sync, dropped frames, missing assets, encoding success, output integrity |
| **Render Cache** | `src/composition/render_cache.py` | RenderCache with composition hash-based caching, hit/miss tracking, eviction, cache invalidation; architecture supports future scene-level and incremental rendering |
| **Preview Engine** | `src/composition/preview.py` | PreviewEngine generating low-resolution previews; architecture supports future timeline, scene, audio, and storyboard previews |
| **Render Queue** | `src/composition/render_queue.py` | RenderQueue with priority-based ordering, retry support, dead letter queue, pause/resume, cancellation; architecture supports future distributed workers |
| **Progress Tracker** | `src/composition/progress.py` | ProgressTracker exposing real-time progress for compilation, rendering, encoding, optimization, validation, completion; callback-based subscriptions for WebSockets/SSE |
| **Unit Tests** | `tests/unit/test_composition_platform.py` | 212 tests covering all schemas, enums, track system, camera motion, image animation, transitions, video effects, text, subtitles, audio mixer, media synchronizer, composition builder, validator, render planner, optimizer, timeline compiler, FFmpeg renderer, rendering pipeline, export engine, quality validator, render cache, preview engine, render queue, progress tracker, events, full pipeline integration |

## Phase 11 Modules — Publishing & Distribution Platform

| Module | File | Description |
|--------|------|-------------|
| **Publishing Schema** | `src/publishing/schema.py` | PublishingPlatform, PublishingMode, PublishingJobStatus, PublishingPriority, AuthMethod, YouTubeCategory, YouTubeLicense, ThumbnailFormat, RetryStrategy, FailoverStrategy enums; PublishingMetadata, PlatformConfig, AuthCredential, ThumbnailSpec, PublishingTask, PublishingPlan, PublishingReport, PublishingMetrics, PublishingProgress, PublishingJob, ScheduleConfig, PlatformRequirements, PublishingStrategy — all Pydantic v2 models |
| **Publishing Events** | `src/publishing/events.py` | 8 publishing lifecycle events: PublishingPlanned, PublishingStarted, UploadProgress, PublishingCompleted, PublishingFailed, RetryTriggered, ScheduleCreated, DraftSaved |
| **Publisher Interface** | `src/publishing/publisher.py` | Publisher abstract base class: authenticate, validate, prepare, publish, schedule, cancel, monitor, collect_metrics — provider-independent interface |
| **Authentication Manager** | `src/publishing/auth.py` | AuthenticationManager supporting OAuth2, API keys, refresh tokens, credential storage, token refresh, multi-user support |
| **Metadata Engine** | `src/publishing/metadata.py` | MetadataEngine generating platform-optimized titles, descriptions, tags, keywords, hashtags, SEO metadata, platform-specific metadata; platform-specific length limits |
| **Thumbnail Manager** | `src/publishing/thumbnail.py` | ThumbnailManager validating, resizing, optimizing thumbnails; platform-specific variants and specs for YouTube, LinkedIn, Medium, WordPress, Twitter, Facebook, Instagram, TikTok, Podcast |
| **Publishing Validator** | `src/publishing/validator.py` | PublishingValidator with 8 validation stages: video format, thumbnail, metadata, title length, description limits, platform requirements, authentication, scheduling; platform-specific requirements |
| **YouTube Publisher** | `src/publishing/youtube.py` | YouTubePublisher implementing Publisher interface: video upload, thumbnail upload, metadata management, privacy/playlist/audience/license settings, immediate/scheduled/draft publishing, progress monitoring, metrics collection |
| **Publishing Planner** | `src/publishing/planner.py` | PublishingPlanner validating ProjectPackage, generating platform-specific metadata, creating publishing tasks, estimating publishing time, generating PublishingPlan |
| **Strategy Engine** | `src/publishing/strategy.py` | PublishingStrategyEngine with 8 preset strategies (immediate, scheduled, draft, manual_approval, multi_platform, youtube_only, conservative, aggressive); custom strategy creation; retry delay calculation (exponential, linear, fixed) |
| **Publishing Queue** | `src/publishing/queue.py` | PublishingQueue with priority-based ordering, retry support, dead letter queue, pause/resume, cancellation; architecture supports future distributed workers |
| **Scheduling Engine** | `src/publishing/scheduler.py` | SchedulingEngine supporting immediate publish, specific date/time, timezone awareness, due task detection, schedule cancellation; architecture supports future recurring and campaign scheduling |
| **Progress Tracker** | `src/publishing/progress.py` | ProgressTracker tracking queued, uploading, thumbnail upload, metadata update, publishing, completed, failed, cancelled stages; callback-based subscriptions for WebSockets/SSE |
| **Unit Tests** | `tests/unit/test_publishing_platform.py` | 167 tests covering all schemas, enums, authentication manager, metadata engine, thumbnail manager, publishing validator, YouTube publisher, publishing planner, strategy engine, publishing queue, scheduling engine, progress tracker, events, publisher interface, full pipeline integration |

## Phase 12 Modules — Platform Services, Analytics & SaaS Foundation

| Module | File | Description |
|--------|------|-------------|
| **Platform Schema** | `src/platform/schema.py` | 30+ Pydantic v2 models and 15 enums: PlanType, SubscriptionStatus, InvoiceStatus, CreditType, OrgRole, InvitationStatus, NotificationChannel, NotificationPriority, NotificationStatus, FeatureFlagScope, FeatureFlagType, PlatformAuditAction, HealthStatus, MetricCategory, MetricType, UsageResourceType, ApiKeyScope; Plan, Subscription, CreditBalance, Invoice, Organization, TeamMember, Invitation, Notification, FeatureFlag, HealthCheck, HealthReport, Metric, Quota, ApiKeyInfo, and more |
| **Analytics Service** | `src/platform/analytics.py` | AnalyticsService tracking projects, generation/publishing/rendering time, success/failure rates, most used providers, top models, project growth, user activity |
| **Usage Tracker** | `src/platform/usage.py` | UsageTracker tracking images, videos, voice minutes, rendering minutes, storage, bandwidth, projects, publishing, tokens, provider usage; per-user and per-org summaries |
| **Billing Service** | `src/platform/billing.py` | BillingService with Free/Pro/Enterprise plans, subscriptions, credits, invoices, plan limits; future Stripe integration via extensible interface |
| **Cost Analytics** | `src/platform/cost_analytics.py` | CostAnalyticsService tracking cost per project, user, provider, asset, workflow; daily/monthly costs; profit margin calculation |
| **Organization Service** | `src/platform/organization.py` | OrganizationService managing orgs, teams, members, roles, invitations, ownership transfer; team collaboration with project sharing, comments, approvals, activity feed |
| **Notification Service** | `src/platform/notification.py` | NotificationService supporting email, in-app, webhook channels; batch sending, read/dismiss status, webhook registration; future Slack/Discord/Teams |
| **Feature Flag Service** | `src/platform/feature_flags.py` | FeatureFlagService with boolean, percentage, variant flags; global, user, org, plan scopes; A/B testing support |
| **Platform Audit Service** | `src/platform/audit.py` | PlatformAuditService for publishing, generation, deletion, billing, admin changes, role changes, settings changes; append-only audit log |
| **Monitoring Service** | `src/platform/monitoring.py` | MonitoringService tracking latency, queue size, failures, retries, provider availability, memory/CPU/disk usage; HealthService with component health checks |
| **Metrics Service** | `src/platform/metrics.py` | MetricsService collecting business, technical, performance, financial, operational metrics with aggregated summaries |
| **API Management** | `src/platform/api_management.py` | ApiManagementService for API keys, rate limits, quotas, usage reports; future developer portal |
| **Admin Service** | `src/platform/admin.py` | AdminService providing platform overview, user overview, provider health, system health, billing overview, usage dashboard, support tools |
| **Unit Tests** | `tests/unit/test_platform_services.py` | 192 tests covering all schemas, enums, analytics, usage tracking, billing, cost analytics, organization management, notifications, feature flags, audit, monitoring, health, metrics, API management, admin, full platform integration |

## Architecture Documentation

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation including module dependency diagrams, class diagrams, and sequence diagrams.

See [docs/iam_architecture.md](docs/iam_architecture.md) for IAM module documentation including authentication flow, RBAC, JWT lifecycle, ERD, and sequence diagrams.

See [docs/orchestration_architecture.md](docs/orchestration_architecture.md) for orchestration framework documentation including workflow lifecycle, component diagrams, and error handling.

See [docs/agent_framework_architecture.md](docs/agent_framework_architecture.md) for AI Agent Framework documentation including agent lifecycle, prompt flow, execution sequence, and component diagrams.

See [docs/research_architecture.md](docs/research_architecture.md) for Topic Discovery & Research System documentation including research workflow diagram, agent interaction diagram, and research package schema.

See [docs/script_architecture.md](docs/script_architecture.md) for Script Generation System documentation including script workflow diagram, agent interaction diagram, and script package schema.

See [docs/storyboard_architecture.md](docs/storyboard_architecture.md) for Storyboard & Scene Planning System documentation including storyboard workflow diagram, scene planning diagram, camera planning diagram, and animation planning diagram.

See [docs/generation_architecture.md](docs/generation_architecture.md) for Generation Platform documentation including platform architecture, provider selection flow, queue flow, execution flow, validation pipeline, and asset manifest schema.

See [docs/composition_architecture.md](docs/composition_architecture.md) for Video Composition Platform documentation including composition pipeline, renderer abstraction, timeline compilation, and project package schema.

See [docs/publishing_architecture.md](docs/publishing_architecture.md) for Publishing & Distribution Platform documentation including publishing pipeline, publisher interface, YouTube flow, queue architecture, and scheduling architecture.

See [docs/platform_services_architecture.md](docs/platform_services_architecture.md) for Platform Services documentation including service architecture, analytics pipeline, billing flow, organization management, and monitoring/health architecture.
