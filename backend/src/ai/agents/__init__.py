"""AI Agent Framework — reusable foundation for all AI agents.

Phase 5: AI Agent Framework providing:
- ``BaseAgent``: Abstract agent with full lifecycle (prompt → AI → validate → quality → artifacts).
- ``AgentContext``: DI container with LLM gateway, prompt executor, validators, memory, tools.
- ``PromptExecutor``: Prompt rendering, AI execution via LLM gateway, history, metrics.
- ``PromptTemplate``: Versioned templates with variables, defaults, and validation.
- ``OutputValidator``: JSON/schema/required-fields validation with repair support.
- ``QualityEvaluator``: Multi-dimension quality scoring (completeness, length, readability, etc.).
- ``ArtifactManager``: Artifact storage and retrieval by agent, type, and execution.
- ``AgentMemory``: Memory abstraction (short-term, workflow, execution, shared) — interfaces only.
- ``Tool`` / ``ToolRegistry``: Tool abstraction for future tools (web search, calculator, etc.).
- ``AgentRegistry``: Versioned agent registration, lookup, and metadata.
- ``AgentEventEmitter``: Agent lifecycle events on the existing EventBus.
- ``AIResponse``: Standard response model with cost, tokens, latency, and metadata.
"""
