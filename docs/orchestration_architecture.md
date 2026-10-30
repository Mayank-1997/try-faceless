# Phase 4 — Orchestration Framework Architecture

## Overview

The orchestration framework provides a reusable, strongly-typed workflow engine built on LangGraph. It supports workflow registration, execution, lifecycle management, state transitions, checkpointing, execution history, error handling, retry policies, conditional routing, parallel execution, and event emission.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Workflow Engine                              │
│  (execute, cancel, resume, timeout, metrics, history)               │
└──────────┬──────────────────────┬──────────────────┬───────────────┘
           │                      │                  │
           ▼                      ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Graph Registry   │  │  Checkpoint Mgr  │  │  Event Emitter   │
│  (register, get,  │  │  (save, restore, │  │  (workflow &     │
│   version, list)  │  │   list, delete)  │  │   node events)   │
└────────┬─────────┘  └──────────────────┘  └────────┬─────────┘
         │                                           │
         ▼                                           ▼
┌──────────────────────────────┐           ┌──────────────────┐
│  BaseWorkflowGraph           │           │  Event Bus       │
│  (nodes, edges, conditional, │           │  (existing)      │
│   parallel, LangGraph)       │           └──────────────────┘
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  BaseNode                    │
│  (execute, validate, retry,  │
│   hooks, cost/tokens)        │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  NodeContext                 │
│  (state, identity, deps,     │
│   cancellation, logger)      │
└──────────────────────────────┘
```

## Workflow Lifecycle

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌───────────┐
│ PENDING │───▶│ RUNNING  │───▶│ PAUSED   │───▶│ RESUMING  │───▶│ COMPLETED │
└─────────┘    └──────────┘    └──────────┘    └───────────┘    └───────────┘
                   │                                  │
                   ├─────▶ CANCELLED ◀────────────────┘
                   │
                   └─────▶ FAILED
                   │
                   └─────▶ TIMEOUT
```

## Key Components

### WorkflowState (`src/workflow/state.py`)

The central Pydantic state object passed between LangGraph nodes. Extended in Phase 4 with:

- `execution_id: UUID` — Unique execution identifier
- `workflow_id: str` — Workflow definition identifier
- `metadata: WorkflowMetadata` — Name, version, content type, tags
- `correlation_id: str | None` — Distributed tracing correlation ID
- `trace_id: str | None` — OpenTelemetry trace ID
- `NodeExecutionRecord` — Per-node execution record (status, timing, cost, tokens, retries)
- `ExecutionStatus` extended with `current_node`, `completed_at`, `checkpoint_ref`, `retry_count`, `timeout_seconds`, `node_history`

### Contexts (`src/workflow/contexts.py`)

- **IdentityContext** — Frozen Pydantic model with `project_id`, `user_id`, `workflow_id`, `execution_id`
- **ExecutionContext** — Mutable execution tracking with `current_node`, `timeout_seconds`, `correlation_id`
- **CancellationToken** — Cooperative cancellation with `cancel()`, `is_cancelled`, `reason`
- **NodeContext** — Complete context passed to nodes: state, identity, execution, repositories, gateways, services, config, cancellation token
- **WorkflowContext** — Higher-level context for graph execution, creates `NodeContext` per node

### RetryPolicy (`src/workflow/retry_policy.py`)

Frozen dataclass with exponential backoff and jitter:

- `max_retries`, `initial_delay_seconds`, `max_delay_seconds`, `backoff_multiplier`
- `jitter` — Random jitter to avoid thundering herd
- `retryable_errors` — Set of error severity levels to retry
- `should_retry(error, attempt)` — Classifies error and checks retry limits
- `get_delay(attempt)` — Calculates delay with exponential backoff

Presets: `NO_RETRY`, `STANDARD`, `AGGRESSIVE`, `CONSERVATIVE`, `PROVIDER`, `VALIDATION`

`RetryExecutor` wraps an async callable and applies the policy with automatic retry and delay.

### BaseNode (`src/workflow/base_node.py`)

Abstract base class for all workflow nodes:

- **Input/Output Validation** — Optional Pydantic schema validation
- **Retry** — Configurable `RetryPolicy` per node
- **Lifecycle Hooks** — `on_before_execute`, `on_after_execute`, `on_error`
- **Metrics** — Records `NodeExecutionRecord` with timing, cost, tokens, retries
- **Cost/Token Tracking** — `record_cost()`, `record_tokens()` helpers
- **Cancellation** — Checks `CancellationToken` before execution

### BaseWorkflowGraph (`src/workflow/base_graph.py`)

Abstract base class for all workflow graphs:

- **Node Registration** — `add_node(node, is_entry, is_exit)`
- **Edges** — `add_edge(source, target)` for unconditional routing
- **Conditional Routing** — `add_conditional_edge(source, target, condition)` for dynamic routing
- **Parallel Execution** — `add_parallel_nodes(source, targets)` for fan-out
- **LangGraph Integration** — Constructs `StateGraph` with compiled nodes and edges
- **Fallback Execution** — Sequential execution when LangGraph is not installed
- **Lifecycle Hooks** — `on_before_build`, `on_after_build`, `on_before_execute`, `on_after_execute`

### CheckpointManager (`src/workflow/checkpoint.py`)

- Save checkpoints with metadata (execution ID, node name, step, state size)
- Restore from checkpoints for resume
- List and filter checkpoints by execution ID or workflow ID
- Delete individual checkpoints or all for an execution
- Get latest checkpoint for an execution
- Wraps LangGraph's `MemorySaver` (or custom `BaseCheckpointSaver`)

### WorkflowEventEmitter (`src/workflow/events.py`)

Emits structured events on the existing `EventBus`:

- **Workflow Events** — Started, Completed, Failed, Paused, Cancelled
- **Node Events** — Started, Completed, Failed
- **Other Events** — CheckpointSaved, RetryTriggered, CancellationRequested

All events include correlation IDs for distributed tracing.

### GraphRegistry (`src/workflow/registry.py`)

- Register workflows with name and version
- Lookup by name (latest version) or name + version
- List all workflows with metadata
- List versions for a workflow
- Check existence, unregister, clear
- Versioned keys: `name:version`

### WorkflowEngine (`src/workflow/engine.py`)

Central orchestrator:

- `execute(workflow_name, initial_state, ...)` — Execute a registered workflow
- `cancel(execution_id, reason)` — Cancel a running execution
- `resume(execution_id, checkpoint_ref)` — Resume from checkpoint
- Timeout enforcement via `asyncio.wait_for`
- Active execution tracking
- Execution history from node records
- Returns `ExecutionResult` with success, state, metrics, checkpoint ref

### WorkflowBuilder (`src/workflow/builder.py`)

Fluent API for constructing workflow graphs:

```python
graph = (
    WorkflowBuilder("youtube_video_v1")
    .description("YouTube video generation")
    .content_type("youtube_video")
    .add_node(research_node, is_entry=True)
    .add_node(script_node)
    .add_node(render_node, is_exit=True)
    .add_edge("research", "script")
    .add_edge("script", "render")
    .add_conditional("research", "script", lambda s: s.research.summary != "")
    .add_parallel("render", ["thumbnail", "seo"])
    .enable_checkpointing()
    .build()
)
```

## Error Handling

### Error Classification (`src/workflow/exceptions.py`)

Errors are classified into severity levels for retry logic:

- **VALIDATION** — `ValidationError`, `AgentValidationError`, `NodeValidationError` (not retried)
- **PROVIDER** — `AIProviderError`, `AIProviderTimeoutError`, `ProviderException` (retried)
- **RETRYABLE** — `InfrastructureError`, `NodeExecutionError`, `ConnectionError`, `TimeoutError`, `OSError` (retried)
- **FATAL** — `WorkflowCancelledError`, `WorkflowTimeoutError`, generic exceptions (not retried)

### Exception Hierarchy

```
AppError
├── DomainError
│   ├── WorkflowExecutionError
│   ├── WorkflowCancelledError
│   ├── WorkflowTimeoutError
│   ├── WorkflowPausedError
│   ├── NodeExecutionError
│   ├── NodeValidationError
│   ├── NodeRetryExhaustedError
│   ├── WorkflowNotFoundError
│   └── WorkflowAlreadyRegisteredError
└── InfrastructureError
    ├── CheckpointError
    └── CheckpointNotFoundError
```

## Dependency Injection

Nodes receive all dependencies via `NodeContext`:

```python
class MyNode(BaseNode):
    async def execute(self, context: NodeContext) -> WorkflowState:
        # Access repositories
        project_repo = context.get_repository("project")

        # Access gateways
        llm = context.get_gateway("llm")

        # Access services
        cost_tracker = context.get_service("cost_tracker")

        # Record cost and tokens
        self.record_cost(context, 0.05, "llm")
        self.record_tokens(context, input_tokens=500, output_tokens=200)

        return context.state
```

The `WorkflowEngine` injects repositories, gateways, and services from the `ServiceContainer` into the `WorkflowContext`, which creates `NodeContext` per node.

## Testing

97 unit tests in `tests/unit/test_workflow_orchestration.py` covering:

- Context creation and DI
- Retry policy logic and executor
- BaseNode execution, validation, retry, cancellation, hooks
- BaseWorkflowGraph build, sequential execution, conditional routing
- GraphRegistry registration, lookup, versioning
- CheckpointManager save, get, list, delete
- WorkflowEventEmitter all event types
- WorkflowEngine execute, cancel, history
- WorkflowBuilder fluent construction
- Error classification
- State extensions
