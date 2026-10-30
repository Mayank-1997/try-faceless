# AI Video Studio — Architecture Documentation

## Overview

AI Video Studio is a production-grade, reusable AI Platform built on Clean Architecture
and Domain-Driven Design principles. The system is designed to autonomously generate
long-form YouTube videos with minimal human interaction.

This document describes the architecture established in **Phase 1: Foundation Architecture**.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│  (FastAPI, Middleware, Routers, Exception Handlers)      │
├─────────────────────────────────────────────────────────┤
│                    Application Layer                      │
│  (DI Container, DTOs, Cost Tracker, Token Tracker,       │
│   Event Bus)                                              │
├─────────────────────────────────────────────────────────┤
│                        AI Layer                           │
│  (LLM Gateway, Image/Video/Voice Gateways,               │
│   Provider Registry, Prompt Manager, Providers)           │
├─────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                   │
│  (Database, Redis, Celery, Storage Gateway,              │
│   Observability/Metrics)                                  │
├─────────────────────────────────────────────────────────┤
│                      Rendering Layer                      │
│  (Rendering Gateway, FFmpeg Renderer)                     │
├─────────────────────────────────────────────────────────┤
│                      Workflow Layer                       │
│  (WorkflowState — strongly typed LangGraph state)         │
├─────────────────────────────────────────────────────────┤
│                       Domain Layer                        │
│  (Entities, Value Objects, Enums, Exceptions)             │
├─────────────────────────────────────────────────────────┤
│                     Persistence Layer                     │
│  (SQLAlchemy Models, Alembic Migrations, Repositories)    │
├─────────────────────────────────────────────────────────┤
│                        Core Layer                         │
│  (ConfigService, Interfaces, Logging, Correlation,        │
│   Constants, Enums, Exceptions)                            │
└─────────────────────────────────────────────────────────┘
```

---

## Module Dependency Diagram

```
                    ┌──────────────┐
                    │  main.py     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  ConfigService │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   ServiceContainer (DI)  │
              └────────────┬────────────┘
                           │
        ┌──────────┬───────┼───────┬──────────┐
        │          │       │       │          │
   ┌────▼───┐ ┌───▼────┐ ┌▼─────┐ ┌▼──────┐ ┌─▼────────┐
   │ Storage │ │ Metrics│ │Event │ │ Cost  │ │  Token   │
   │ Gateway │ │Collect.│ │ Bus  │ │Tracker│ │  Tracker │
   └────┬───┘ └────────┘ └──────┘ └───────┘ └──────────┘
        │
   ┌────▼───┐
   │Provider│
   │Registry│
   └────┬───┘
        │
   ┌────▼──────────────────────────────────┐
   │           Gateways                     │
   │  ┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
   │  │ LLM │ │Image │ │Video │ │Voice │  │
   │  └──┬──┘ └──┬───┘ └──┬───┘ └──┬───┘  │
   └─────┼───────┼────────┼────────┼──────┘
         │       │        │        │
   ┌─────▼───────▼────────▼────────▼──────┐
   │           Providers                   │
   │  Gemini │ Imagen │ Veo │ Google TTS  │
   └───────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. Dependency Injection via ServiceContainer

All services are constructed in a single `ServiceContainer` and injected via
FastAPI's `Depends()` system. No module-level globals or singletons.

**Benefits**: Testable, swappable, explicit dependency graph.

### 2. Gateway Pattern for AI Providers

Agents never call providers directly. All AI calls go through gateways:

```
Agent → LLMGateway → ProviderRegistry → GeminiProvider
```

**Benefits**: Provider switching via config only, automatic fallback, retries,
cost tracking, and structured logging without agent awareness.

### 3. Strongly-Typed WorkflowState

LangGraph nodes receive and return `WorkflowState` (Pydantic model), not
dictionaries. All fields are explicit, validated, and documented.

**Benefits**: Type safety, IDE autocompletion, validation, self-documenting.

### 4. Event Bus for Loose Coupling

Components communicate via async pub/sub. Publishers emit events; subscribers
react independently. Errors in one subscriber don't block others.

**Benefits**: Extensible, decoupled, testable.

### 5. Abstract Storage & Rendering

No direct disk I/O or FFmpeg calls. All file operations go through
`StorageGateway`; all rendering through `RenderingGateway`.

**Benefits**: Cloud-ready (S3/GCS/MinIO), testable with mocks.

---

## Class Diagram (Key Interfaces)

```
<<abstract>> LLMProvider
  + provider_name: AIProvider
  + initialize(config: ProviderConfig): void
  + generate(prompt: str, **kwargs): str
  + generate_json(prompt: str, **kwargs): dict
  + stream(prompt: str, **kwargs): AsyncIterator[str]
  + count_tokens(text: str): int
  + calculate_cost(input: int, output: int): float
  + health_check(): HealthStatus
  + shutdown(): void

<<abstract>> ImageProvider
  + generate_image(prompt, width, height, ...): bytes
  + calculate_cost(width, height): float

<<abstract>> VideoProvider
  + generate_video(prompt, duration, width, ...): bytes
  + calculate_cost(duration, resolution): float

<<abstract>> VoiceProvider
  + generate_speech(text, language, voice, ...): bytes
  + calculate_cost(char_count): float

<<abstract>> Renderer
  + render(scenes, output_path, ...): str
  + merge(video, audio, output): str
  + concatenate(videos, output): str
  + burn_subtitles(video, subtitles, output): str
  + generate_thumbnail(video, output, ...): str

<<abstract>> StorageProvider
  + upload(data, key, content_type): str
  + download(key): bytes
  + delete(key): bool
  + exists(key): bool
  + get_url(key, expires_in): str
  + list_files(prefix, limit): list[str]

<<abstract>> PromptLoader
  + load(agent_type, name, version): str
  + render(template, variables): str
  + get_metadata(agent_type, name): dict

<<abstract>> CostCalculator
  + calculate_llm_cost(provider, model, in, out): float
  + calculate_image_cost(provider, w, h): float
  + calculate_video_cost(provider, dur, res): float
  + calculate_voice_cost(provider, chars): float
  + calculate_render_cost(dur, res): float
```

---

## Sequence Diagram: LLM Generation Flow

```
Agent          LLMGateway       ProviderRegistry    GeminiProvider
  │                │                   │                  │
  │  generate()    │                   │                  │
  ├───────────────►│                   │                  │
  │                │  get_providers()  │                  │
  │                ├──────────────────►│                  │
  │                │  [LLMProvider]    │                  │
  │                │◄──────────────────┤                  │
  │                │                   │                  │
  │                │  generate(prompt) │                  │
  │                ├──────────────────────────────────────►│
  │                │                   │                  │
  │                │                   │  (retry on fail) │
  │                │                   │                  │
  │                │  response text    │                  │
  │                │◄──────────────────────────────────────┤
  │                │                   │                  │
  │                │  count_tokens()   │                  │
  │                ├──────────────────────────────────────►│
  │                │  token count      │                  │
  │                │◄──────────────────────────────────────┤
  │                │                   │                  │
  │                │  calculate_cost() │                  │
  │                ├──────────────────────────────────────►│
  │                │  cost_usd         │                  │
  │                │◄──────────────────────────────────────┤
  │                │                   │                  │
  │  GenerationResult                   │                  │
  │◄───────────────┤                   │                  │
  │                │                   │                  │
```

---

## File Structure (Phase 1)

```
backend/
├── src/
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (unchanged)
│   │   ├── config_service.py      # NEW — ConfigService with feature flags
│   │   ├── constants.py           # Application constants (unchanged)
│   │   ├── correlation.py         # NEW — Correlation ID context vars
│   │   ├── enums.py               # Enum definitions (unchanged)
│   │   ├── exceptions.py          # EXTENDED — gateway/provider/prompt errors
│   │   ├── interfaces.py          # NEW — abstract base interfaces
│   │   └── logging.py             # Structured logging (unchanged)
│   ├── application/
│   │   ├── di/
│   │   │   ├── container.py       # NEW — ServiceContainer
│   │   │   └── dependencies.py    # NEW — FastAPI Depends providers
│   │   ├── dto/
│   │   │   └── responses.py       # NEW — Success/Failure/Progress/Streaming
│   │   └── services/
│   │       ├── cost_tracker.py    # NEW — centralized cost tracking
│   │       ├── event_bus.py       # NEW — async pub/sub event bus
│   │       └── token_tracker.py   # NEW — centralized token tracking
│   ├── ai/
│   │   ├── gateway/
│   │   │   ├── llm_gateway.py     # NEW — unified LLM interface
│   │   │   ├── image_gateway.py   # NEW — unified image generation
│   │   │   ├── video_gateway.py   # NEW — unified video generation
│   │   │   └── voice_gateway.py   # NEW — unified voice generation
│   │   ├── providers/
│   │   │   ├── registry.py        # NEW — provider registry
│   │   │   ├── gemini.py          # NEW — Gemini LLM provider
│   │   │   ├── imagen.py          # NEW — Imagen image provider
│   │   │   ├── veo.py             # NEW — Veo video provider
│   │   │   └── google_tts.py      # NEW — Google TTS voice provider
│   │   └── prompts/
│   │       └── prompt_manager.py  # NEW — prompt loading/versioning/rendering
│   ├── infrastructure/
│   │   ├── database/
│   │   │   └── engine.py          # SQLAlchemy engine (unchanged)
│   │   ├── cache/
│   │   │   └── redis_client.py    # Redis client (unchanged)
│   │   ├── storage/
│   │   │   ├── gateway.py         # NEW — storage gateway
│   │   │   └── local.py           # NEW — local filesystem storage
│   │   ├── observability/
│   │   │   └── metrics.py         # NEW — metrics collector
│   │   └── tasks/
│   │       └── celery_app.py      # Celery app (unchanged)
│   ├── rendering/
│   │   ├── gateway.py             # NEW — rendering gateway
│   │   └── ffmpeg.py              # NEW — FFmpeg renderer
│   ├── workflow/
│   │   └── state.py               # NEW — strongly typed WorkflowState
│   ├── presentation/
│   │   ├── main.py                # REFACTORED — DI container integration
│   │   └── middleware/
│   │       └── correlation.py     # NEW — correlation ID middleware
│   ├── domain/                    # Domain layer (Phase 2)
│   ├── persistence/               # Persistence layer (Phase 3)
│   └── publishing/                # Publishing layer (Phase 8)
├── tests/
│   ├── conftest.py                # Pytest configuration (unchanged)
│   ├── factories.py               # NEW — test object factories
│   ├── mocks/
│   │   └── providers.py           # NEW — mock providers for testing
│   └── unit/
│       ├── test_interfaces.py     # NEW
│       ├── test_exceptions_extended.py  # NEW
│       ├── test_config_service.py # NEW
│       ├── test_responses.py      # NEW
│       ├── test_event_bus.py      # NEW
│       ├── test_cost_tracker.py   # NEW
│       ├── test_token_tracker.py  # NEW
│       ├── test_metrics.py        # NEW
│       ├── test_workflow_state.py # NEW
│       ├── test_prompt_manager.py # NEW
│       ├── test_storage.py        # NEW
│       ├── test_correlation.py    # NEW
│       ├── test_llm_gateway.py    # NEW
│       ├── test_base_model.py     # (existing)
│       ├── test_config.py         # (existing)
│       ├── test_constants.py      # (existing)
│       ├── test_enums.py          # (existing)
│       └── test_exceptions.py     # (existing)
└── pyproject.toml                 # Updated — added pyyaml dependency
```

---

## Adding a New Provider

To add a new LLM provider (e.g., OpenAI):

1. **Implement the interface** in `src/ai/providers/openai.py`:
   ```python
   class OpenAILLMProvider(LLMProvider):
       async def generate(self, prompt: str, **kwargs) -> str:
           ...
   ```

2. **Register it** in `ProviderRegistry._register_llm_providers()`:
   ```python
   if openai_config.api_key:
       provider = OpenAILLMProvider()
       await provider.initialize(...)
       self.register(AIProvider.OPENAI, provider)
   ```

3. **Add config** in `src/core/config.py` (OpenAI sub-settings).

4. **No gateway or agent code changes needed.**

---

## Running Tests

```bash
cd backend
pytest tests/unit/ -v
```

## Quality Standards

- Python 3.12 with strict typing
- Pydantic V2 for validation
- Async-first design
- SOLID principles
- No hardcoded values
- No duplicated code
- Extensive docstrings
- Production-grade logging
- High testability
