"""Workflow layer — LangGraph workflow orchestration, state management, and execution engine.

Phase 4: Orchestration framework providing:
- ``WorkflowState``: Strongly-typed state for all workflow data.
- ``BaseNode``: Abstract node with retry, validation, metrics, and lifecycle hooks.
- ``BaseWorkflowGraph``: Abstract graph with nodes, edges, conditional routing, and parallel execution.
- ``WorkflowEngine``: Central orchestrator for execution, cancellation, and resume.
- ``GraphRegistry``: Versioned workflow registration and lookup.
- ``WorkflowBuilder``: Fluent builder for constructing workflow graphs.
- ``CheckpointManager``: Checkpoint save/restore for resume and recovery.
- ``WorkflowEventEmitter``: Event emission on the existing ``EventBus``.
- ``RetryPolicy`` / ``RetryExecutor``: Composable retry with exponential backoff.
- ``NodeContext`` / ``WorkflowContext``: Dependency injection for nodes and graphs.
"""
