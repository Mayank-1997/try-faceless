# Phase 5 — AI Agent Framework Architecture

## Overview

The AI Agent Framework provides a reusable, strongly-typed foundation that every future AI agent in the platform will inherit from. It eliminates duplicated code across agents (Research, Script, ScenePlanner, ImageGenerator, etc.) and is generic enough to support Video, Blog, LinkedIn, Twitter, Podcast, and future AI workflows.

The framework belongs to the **Application Layer** in the Clean Architecture.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BaseAgent                                    │
│  (initialize → validate → prompt → AI → validate → quality →        │
│   artifacts → events → update state)                                │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Prompt   │ │ Output   │ │ Quality  │ │ Artifact │ │ Agent    │
│ Executor │ │ Validator│ │ Evaluator│ │ Manager  │ │ Memory   │
└────┬─────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
     │
     ▼
┌──────────┐     ┌──────────┐     ┌──────────┐
│ LLM      │────▶│ Provider │────▶│ Gemini / │
│ Gateway  │     │ Registry │     │ OpenAI / │
└──────────┘     └──────────┘     │ Claude   │
                                  └──────────┘
```

## Agent Lifecycle

```
┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Initialize │───▶│ Validate     │───▶│ Prepare      │───▶│ Execute AI   │
│            │    │ Input        │    │ Prompt       │    │ (via Gateway)│
└────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                   ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐
                   │ Update       │◀───│ Emit         │◀───│ Validate     │
                   │ Workflow     │    │ Events       │    │ Output       │
                   │ State        │    │              │    │              │
                   └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                   ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐
                   │ Return       │◀───│ Create       │◀───│ Evaluate     │
                   │ Result       │    │ Artifacts    │    │ Quality      │
                   └──────────────┘    └──────────────┘    └──────────────┘
```

## Prompt Flow Diagram

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ PromptTemplate│──▶│ Validate     │───▶│ Render       │───▶│ PromptExecutor│
│ (name,       │    │ Variables    │    │ (substitute  │    │ (execute)    │
│  template,   │    │              │    │  {{vars}})   │    │              │
│  variables,  │    └──────────────┘    └──────────────┘    └──────┬───────┘
│  metadata)   │                                              │
└─────────────┘                                              ▼
                   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                   │ AIResponse   │◀───│ Parse JSON   │◀───│ LLM Gateway  │
                   │ (success,    │    │ (if expected)│    │ (provider    │
                   │  response,   │    │              │    │  selection,  │
                   │  cost,       │    └──────────────┘    │  fallback,   │
                   │  tokens,     │                        │  retry)      │
                   │  latency)    │                        └──────────────┘
                   └──────────────┘
```

## Execution Sequence Diagram

```
WorkflowEngine          BaseAgent           PromptExecutor       LLMGateway      Provider
     │                      │                    │                  │               │
     │── execute(node) ────▶│                    │                  │               │
     │                      │── run_agent() ────▶│                  │               │
     │                      │  (lifecycle)       │                  │               │
     │                      │                    │                  │               │
     │                      │── on_initialize()  │                  │               │
     │                      │                    │                  │               │
     │                      │── prepare_prompt() │                  │               │
     │                      │  (subclass)        │                  │               │
     │                      │                    │                  │               │
     │                      │── execute_template│                  │               │
     │                      │                    │── render() ──────▶│               │
     │                      │                    │── generate() ────▶│── generate()─▶│
     │                      │                    │                  │◀── result ────│
     │                      │                    │◀── AIResponse ───│               │
     │                      │◀── response ───────│                  │               │
     │                      │                    │                  │               │
     │                      │── validate_output()│                  │               │
     │                      │── evaluate_quality│                  │               │
     │                      │── create_artifact()│                  │               │
     │                      │── emit_events()    │                  │               │
     │                      │── update_state()   │                  │               │
     │                      │                    │                  │               │
     │◀── AgentResult ──────│                    │                  │               │
```

## Key Components

### BaseAgent (`src/ai/agents/base.py`)

Abstract class extending `BaseNode` with AI-specific lifecycle:

- **Input validation** — Schema-based via `BaseNode`
- **Prompt execution** — Via `PromptExecutor` (never calls providers directly)
- **Output validation** — Via `OutputValidator` with JSON/schema/required-fields
- **Quality evaluation** — Via `QualityEvaluator` with multi-dimension scoring
- **Artifact creation** — Via `ArtifactManager`
- **Cost & token tracking** — Updates `WorkflowState` automatically
- **Event emission** — 9 agent lifecycle events via `AgentEventEmitter`
- **Memory** — Short-term, workflow, and execution memory via `AgentMemory`
- **Retry** — Inherits `RetryPolicy` from `BaseNode`

Subclasses implement:
- `agent_type` — Return `AgentType` enum value
- `prepare_prompt(context)` — Build `PromptTemplate` and variables
- `process_response(response, context)` — Extract structured data
- `update_workflow_state(result, response, context)` — Update state

### AgentContext (`src/ai/agents/context.py`)

Dependency injection container for agents:

- `identity` — `IdentityContext` (project, user, workflow, execution IDs)
- `state` — `WorkflowState` (mutable)
- `execution` — `ExecutionContext` (current node, timing, correlation)
- `llm_gateway` — LLM gateway for AI calls
- `prompt_executor` — Prompt execution pipeline
- `output_validator` — Output validation
- `quality_evaluator` — Quality scoring
- `artifact_manager` — Artifact storage
- `memory` — Agent memory interface
- `tools` — Dictionary of tool instances
- `event_bus` — Event bus for lifecycle events
- `cancellation_token` — Cooperative cancellation

### PromptExecutor (`src/ai/agents/prompt_executor.py`)

Single entry point for all AI calls:

- `execute_template(template, variables)` — Execute a `PromptTemplate`
- `execute_prompt(prompt)` — Execute a raw prompt string
- `execute_file_prompt(agent_type, name, variables)` — Execute file-based prompt via `PromptManager`
- JSON response parsing
- Execution history tracking (`PromptExecutionRecord`)
- Cost and token aggregation
- Correlation ID propagation

### PromptTemplate (`src/ai/agents/prompt_template.py`)

Versioned prompt templates:

- `name`, `template`, `variables`, `metadata`
- `PromptVariable` with name, description, default value, required flag
- `PromptTemplateMetadata` with version, author, tags, model compatibility, temperature
- `from_string()` — Auto-detect variables from template
- `render(variables)` — Substitute `{{variable}}` placeholders
- `validate_variables(provided)` — Check required variables

### OutputValidator (`src/ai/agents/output_validator.py`)

Multi-strategy output validation:

- JSON parsing validation
- Pydantic schema validation
- Required fields checking
- Custom `BusinessRule` validators
- `validate_and_repair()` — Attempt repair with custom repair function
- `ValidationResult` with errors, warnings, structured data

### QualityEvaluator (`src/ai/agents/quality.py`)

Multi-dimension quality scoring (0.0–1.0):

- **Completeness** — Length and keyword coverage
- **Length** — Within expected bounds
- **Consistency** — Internal consistency (deduplication heuristic)
- **Readability** — Structure, paragraphs, sentence length
- **Relevance** — Keyword overlap with prompt
- **Accuracy** — Placeholder for future LLM-as-a-Judge
- `QualityResult` with score, dimensions, pass/fail, grade (A–F), suggestions
- Configurable threshold and custom `DimensionEvaluator`

### ArtifactManager (`src/ai/agents/artifact.py`)

Artifact storage and retrieval:

- `store()` — Store with agent name, type, content, metadata
- `get()` — Retrieve by ID
- `list_by_agent()`, `list_by_type()`, `list_by_execution()`
- `delete()`, `delete_by_execution()`, `clear()`
- `Artifact` model with ID, content, metadata, tags, timestamps
- Artifact types: research, script, scene_plan, image, video, voice, subtitle, thumbnail, metadata, prompt_output

### AgentMemory (`src/ai/agents/memory.py`)

Memory abstraction (interfaces only, no vector DB):

- `AgentMemory` — Abstract interface with store, retrieve, delete, list_keys, clear
- `InMemoryAgentMemory` — In-memory implementation for testing
- `MemoryEntry` — Entry with key, value, agent name, execution ID, TTL, tags
- `MemoryScope` — Constants: SHORT_TERM, WORKFLOW, EXECUTION, CONVERSATION, SHARED

### Tools (`src/ai/agents/tools.py`)

Tool abstraction (interfaces only, no implementations):

- `Tool` — Abstract interface with execute, initialize, shutdown, validate_parameters
- `ToolRegistry` — Register, get, list, unregister tools
- `ToolMetadata` — Name, description, category, version, parameters
- `ToolParameter` — Name, description, type, required, default value
- `ToolResult` — Success/failure with output, error, metadata

### AgentRegistry (`src/ai/agents/registry.py`)

Versioned agent registration:

- `register(agent, metadata)` — Register with auto-extracted or explicit metadata
- `get(name, version)` — Lookup by name (latest version) or name + version
- `list_agents()`, `list_by_type()`, `list_versions()`
- `exists()`, `unregister()`, `clear()`
- `AgentMetadata` — Name, agent type, version, description, content types, tags

### AgentEventEmitter (`src/ai/agents/events.py`)

Agent lifecycle events on the existing `EventBus`:

| Event | When |
|-------|------|
| `AgentStarted` | Agent begins execution |
| `PromptGenerated` | Prompt template rendered |
| `PromptExecuted` | AI call completed |
| `ValidationFailed` | Output validation failed |
| `RetryTriggered` | Retry attempt initiated |
| `AgentCompleted` | Agent finished successfully |
| `AgentFailed` | Agent failed |
| `ArtifactsCreated` | Artifacts stored |
| `QualityEvaluated` | Quality score computed |

### AIResponse (`src/ai/agents/response.py`)

Standard response model for all AI calls:

- `success`, `response`, `structured_data`
- `cost_usd`, `input_tokens`, `output_tokens`, `total_tokens`
- `latency_ms`, `provider`, `model`
- `warnings`, `errors`, `metadata`
- `correlation_id`, `timestamp`
- `from_generation_result()` — Convert from gateway `GenerationResult`
- `failure()` — Create failure response

## Error Handling

### Exception Hierarchy

```
AppError
├── DomainError
│   ├── AgentExecutionError
│   ├── AgentInitializationError
│   ├── AgentTimeoutError
│   ├── PromptExecutionError
│   ├── PromptRenderingError
│   ├── PromptValidationError
│   ├── OutputValidationError
│   ├── OutputRepairError
│   ├── QualityEvaluationError
│   ├── QualityThresholdError
│   ├── ToolExecutionError
│   ├── ToolNotFoundError
│   ├── AgentNotFoundError
│   └── AgentAlreadyRegisteredError
└── InfrastructureError
    ├── ArtifactError
    ├── ArtifactNotFoundError
    └── MemoryError
```

## Dependency Injection

All agents receive dependencies via `AgentContext`. No direct instantiation:

```python
class ResearchAgent(BaseAgent):
    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCH

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        template = PromptTemplate.from_string("research", "Research: {{topic}}")
        return template, {"topic": context.state.topic.primary_topic}

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        return {"summary": response.response}

    async def update_workflow_state(self, result, response, context) -> None:
        context.state.research = context.state.research.model_copy(
            update={"summary": result["summary"]}
        )
```

## Testing

143 unit tests in `tests/unit/test_agent_framework.py` covering:

- `AIResponse` — creation, factories, conversion
- `AgentContext` — DI, cancellation, repository/gateway/service/tool lookups
- `PromptTemplate` — variable detection, rendering, validation, defaults
- `PromptExecutor` — template/raw/file execution, JSON parsing, history, cost tracking
- `OutputValidator` — JSON/schema/required-fields, business rules, repair
- `QualityEvaluator` — dimensions, scoring, thresholds, grades, suggestions
- `ArtifactManager` — store/get/list/delete by agent/type/execution
- `InMemoryAgentMemory` — store/retrieve/delete/list/clear, TTL expiry
- `ToolRegistry` — register/get/list/unregister, parameter validation
- `AgentRegistry` — versioned registration, lookup, listing
- `AgentEventEmitter` — all 9 event types
- `BaseAgent` — full lifecycle, cost/tokens, cancellation, AI failure, artifacts, quality, state updates, memory
- All exception classes
