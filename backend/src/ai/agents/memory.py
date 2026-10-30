"""Agent memory abstraction for the AI Agent Framework.

Provides interfaces for different memory types:

- **Short-term memory**: Data within a single agent execution
- **Workflow memory**: Data shared across agents in a workflow
- **Execution memory**: Data from previous executions
- **Conversation memory**: Multi-turn conversation history (future)
- **Shared workflow memory**: Cross-agent shared state

Only interfaces are defined — no vector database implementation.
Concrete implementations will be added in future phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Memory entry
# ---------------------------------------------------------------------------
class MemoryEntry(BaseModel):
    """A single entry in agent memory.

    Attributes:
        key: The memory key.
        value: The stored value.
        agent_name: The agent that stored the entry.
        execution_id: Optional execution ID.
        timestamp: When the entry was stored.
        ttl_seconds: Optional time-to-live in seconds.
        tags: Optional tags for categorization.
    """

    key: str
    value: Any = None
    agent_name: str = ""
    execution_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_expired(self) -> bool:
        """Check if this memory entry has expired."""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds


# ---------------------------------------------------------------------------
# Memory scope
# ---------------------------------------------------------------------------
class MemoryScope:
    """Constants for memory scopes."""

    SHORT_TERM = "short_term"
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    CONVERSATION = "conversation"
    SHARED = "shared"


# ---------------------------------------------------------------------------
# Abstract memory interface
# ---------------------------------------------------------------------------
class AgentMemory(ABC):
    """Abstract interface for agent memory.

    Defines the contract for storing and retrieving data across
    agent executions.  Concrete implementations may use in-memory
    dicts, Redis, or vector databases.

    All methods are async to support remote backends.
    """

    @abstractmethod
    async def store(
        self,
        key: str,
        value: Any,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        agent_name: str = "",
        execution_id: UUID | None = None,
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Store a value in memory.

        Args:
            key: The memory key.
            value: The value to store.
            scope: The memory scope.
            agent_name: The agent storing the value.
            execution_id: Optional execution ID.
            ttl_seconds: Optional time-to-live.
            tags: Optional tags.
        """
        ...

    @abstractmethod
    async def retrieve(
        self,
        key: str,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        execution_id: UUID | None = None,
    ) -> Any | None:
        """Retrieve a value from memory.

        Args:
            key: The memory key.
            scope: The memory scope.
            execution_id: Optional execution ID.

        Returns:
            The stored value, or None if not found or expired.
        """
        ...

    @abstractmethod
    async def delete(
        self,
        key: str,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        execution_id: UUID | None = None,
    ) -> bool:
        """Delete a value from memory.

        Args:
            key: The memory key.
            scope: The memory scope.
            execution_id: Optional execution ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def list_keys(
        self,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        agent_name: str | None = None,
        execution_id: UUID | None = None,
    ) -> list[str]:
        """List memory keys, optionally filtered.

        Args:
            scope: The memory scope.
            agent_name: Optional agent name filter.
            execution_id: Optional execution ID filter.

        Returns:
            List of memory keys.
        """
        ...

    @abstractmethod
    async def clear(
        self,
        *,
        scope: str | None = None,
        execution_id: UUID | None = None,
    ) -> int:
        """Clear memory entries.

        Args:
            scope: Optional scope to clear. If None, clears all scopes.
            execution_id: Optional execution ID to clear.

        Returns:
            Number of entries cleared.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation (for testing and development)
# ---------------------------------------------------------------------------
class InMemoryAgentMemory(AgentMemory):
    """In-memory implementation of ``AgentMemory``.

    Stores all entries in a dictionary.  Suitable for testing and
    single-process development.  Not suitable for production
    multi-process deployments.
    """

    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._scope_prefix: dict[str, str] = {
            MemoryScope.SHORT_TERM: "st",
            MemoryScope.WORKFLOW: "wf",
            MemoryScope.EXECUTION: "ex",
            MemoryScope.CONVERSATION: "cv",
            MemoryScope.SHARED: "sh",
        }

    def _make_key(
        self,
        key: str,
        scope: str,
        execution_id: UUID | None,
    ) -> str:
        """Create a composite key for storage."""
        prefix = self._scope_prefix.get(scope, "uk")
        exec_part = str(execution_id) if execution_id else "global"
        return f"{prefix}:{exec_part}:{key}"

    async def store(
        self,
        key: str,
        value: Any,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        agent_name: str = "",
        execution_id: UUID | None = None,
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        composite = self._make_key(key, scope, execution_id)
        entry = MemoryEntry(
            key=key,
            value=value,
            agent_name=agent_name,
            execution_id=execution_id,
            ttl_seconds=ttl_seconds,
            tags=tags or [],
        )
        self._entries[composite] = entry

    async def retrieve(
        self,
        key: str,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        execution_id: UUID | None = None,
    ) -> Any | None:
        composite = self._make_key(key, scope, execution_id)
        entry = self._entries.get(composite)
        if entry is None or entry.is_expired:
            if entry is not None and entry.is_expired:
                del self._entries[composite]
            return None
        return entry.value

    async def delete(
        self,
        key: str,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        execution_id: UUID | None = None,
    ) -> bool:
        composite = self._make_key(key, scope, execution_id)
        if composite in self._entries:
            del self._entries[composite]
            return True
        return False

    async def list_keys(
        self,
        *,
        scope: str = MemoryScope.SHORT_TERM,
        agent_name: str | None = None,
        execution_id: UUID | None = None,
    ) -> list[str]:
        prefix = self._scope_prefix.get(scope, "uk")
        results: list[str] = []
        for composite, entry in self._entries.items():
            if not composite.startswith(f"{prefix}:"):
                continue
            if agent_name is not None and entry.agent_name != agent_name:
                continue
            if execution_id is not None and entry.execution_id != execution_id:
                continue
            if not entry.is_expired:
                results.append(entry.key)
        return results

    async def clear(
        self,
        *,
        scope: str | None = None,
        execution_id: UUID | None = None,
    ) -> int:
        if scope is None and execution_id is None:
            count = len(self._entries)
            self._entries.clear()
            return count

        to_delete: list[str] = []
        for composite, entry in self._entries.items():
            if scope is not None:
                prefix = self._scope_prefix.get(scope, "uk")
                if not composite.startswith(f"{prefix}:"):
                    continue
            if execution_id is not None and entry.execution_id != execution_id:
                continue
            to_delete.append(composite)

        for key in to_delete:
            del self._entries[key]
        return len(to_delete)

    @property
    def count(self) -> int:
        """Return the number of stored entries."""
        return len(self._entries)
