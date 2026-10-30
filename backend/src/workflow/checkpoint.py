"""Checkpoint management for workflow orchestration.

Provides an abstraction over LangGraph's checkpointing system,
supporting:
- Save checkpoints during execution
- Restore from checkpoints for resume
- List available checkpoints
- Delete old checkpoints (garbage collection)

The checkpoint manager wraps LangGraph's ``BaseCheckpointSaver``
and adds metadata persistence for recovery after crashes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.workflow.exceptions import CheckpointError, CheckpointNotFoundError


# ---------------------------------------------------------------------------
# Checkpoint metadata
# ---------------------------------------------------------------------------
class CheckpointMetadata(BaseModel):
    """Metadata for a saved checkpoint.

    Attributes:
        checkpoint_ref: The checkpoint reference string (LangGraph thread_ts).
        execution_id: The workflow execution ID.
        workflow_id: The workflow definition ID.
        node_name: The node that was executing when the checkpoint was saved.
        step: The step number at which the checkpoint was saved.
        created_at: When the checkpoint was created.
        state_size_bytes: Approximate size of the serialized state.
        tags: Optional tags for categorization.
    """

    checkpoint_ref: str = ""
    execution_id: UUID
    workflow_id: str = ""
    node_name: str = ""
    step: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state_size_bytes: int = 0
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Checkpoint manager
# ---------------------------------------------------------------------------
class CheckpointManager:
    """Manages workflow checkpoints for resume and recovery.

    Wraps a LangGraph checkpoint saver and provides a simplified
    interface for saving, restoring, and managing checkpoints.

    Attributes:
        saver: The underlying LangGraph checkpoint saver.
    """

    def __init__(self, saver: Any = None) -> None:
        """Initialize the checkpoint manager.

        Args:
            saver: A LangGraph ``BaseCheckpointSaver`` instance.
                If None, an in-memory saver is used (for testing).
        """
        self._saver = saver
        self._logger = get_logger(__name__)
        self._checkpoints: dict[str, CheckpointMetadata] = {}

        if saver is None:
            try:
                from langgraph.checkpoint.memory import MemorySaver

                self._saver = MemorySaver()
            except ImportError:
                self._logger.warning(
                    "checkpoint_saver_not_available",
                    message="langgraph MemorySaver not available, checkpoints disabled",
                )
                self._saver = None

    @property
    def saver(self) -> Any:
        """Return the underlying LangGraph checkpoint saver."""
        return self._saver

    @property
    def is_enabled(self) -> bool:
        """Check if checkpointing is enabled."""
        return self._saver is not None

    async def save(
        self,
        execution_id: UUID,
        workflow_id: str,
        node_name: str,
        step: int,
        state: Any,
        checkpoint_ref: str | None = None,
    ) -> CheckpointMetadata | None:
        """Save a checkpoint.

        Args:
            execution_id: The workflow execution ID.
            workflow_id: The workflow definition ID.
            node_name: The node that was executing.
            step: The step number.
            state: The workflow state to checkpoint.
            checkpoint_ref: Optional explicit checkpoint reference.
                If None, a new one is generated.

        Returns:
            The checkpoint metadata, or None if checkpointing is disabled.
        """
        if not self.is_enabled:
            # Still track metadata even without a saver (for testing)
            ref = checkpoint_ref or f"{execution_id}:{step}"
            metadata = CheckpointMetadata(
                checkpoint_ref=ref,
                execution_id=execution_id,
                workflow_id=workflow_id,
                node_name=node_name,
                step=step,
            )
            self._checkpoints[ref] = metadata
            return metadata

        ref = checkpoint_ref or f"{execution_id}:{step}"
        self._logger.info(
            "checkpoint_saving",
            execution_id=str(execution_id),
            checkpoint_ref=ref,
            node=node_name,
            step=step,
        )

        try:
            state_size = len(str(state.model_dump())) if hasattr(state, "model_dump") else 0
        except Exception:
            state_size = 0

        metadata = CheckpointMetadata(
            checkpoint_ref=ref,
            execution_id=execution_id,
            workflow_id=workflow_id,
            node_name=node_name,
            step=step,
            state_size_bytes=state_size,
        )

        self._checkpoints[ref] = metadata
        self._logger.info(
            "checkpoint_saved",
            checkpoint_ref=ref,
            node=node_name,
            step=step,
            state_size_bytes=state_size,
        )
        return metadata

    async def get(self, checkpoint_ref: str) -> CheckpointMetadata:
        """Get checkpoint metadata by reference.

        Args:
            checkpoint_ref: The checkpoint reference string.

        Returns:
            The checkpoint metadata.

        Raises:
            CheckpointNotFoundError: If the checkpoint does not exist.
        """
        if checkpoint_ref not in self._checkpoints:
            raise CheckpointNotFoundError(checkpoint_ref)
        return self._checkpoints[checkpoint_ref]

    async def list_checkpoints(
        self,
        execution_id: UUID | None = None,
        workflow_id: str | None = None,
    ) -> list[CheckpointMetadata]:
        """List checkpoints, optionally filtered.

        Args:
            execution_id: Filter by execution ID.
            workflow_id: Filter by workflow ID.

        Returns:
            List of checkpoint metadata, ordered by creation time.
        """
        results = list(self._checkpoints.values())
        if execution_id is not None:
            results = [c for c in results if c.execution_id == execution_id]
        if workflow_id is not None:
            results = [c for c in results if c.workflow_id == workflow_id]
        results.sort(key=lambda c: c.created_at)
        return results

    async def delete(self, checkpoint_ref: str) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_ref: The checkpoint reference string.

        Returns:
            True if the checkpoint was deleted, False if it didn't exist.
        """
        if checkpoint_ref in self._checkpoints:
            del self._checkpoints[checkpoint_ref]
            self._logger.info("checkpoint_deleted", checkpoint_ref=checkpoint_ref)
            return True
        return False

    async def delete_all(self, execution_id: UUID) -> int:
        """Delete all checkpoints for an execution.

        Args:
            execution_id: The execution ID to clean up.

        Returns:
            Number of checkpoints deleted.
        """
        to_delete = [
            ref for ref, meta in self._checkpoints.items()
            if meta.execution_id == execution_id
        ]
        for ref in to_delete:
            del self._checkpoints[ref]
        self._logger.info(
            "checkpoints_deleted_all",
            execution_id=str(execution_id),
            count=len(to_delete),
        )
        return len(to_delete)

    async def get_latest(self, execution_id: UUID) -> CheckpointMetadata | None:
        """Get the latest checkpoint for an execution.

        Args:
            execution_id: The execution ID.

        Returns:
            The latest checkpoint metadata, or None if no checkpoints exist.
        """
        checkpoints = await self.list_checkpoints(execution_id=execution_id)
        if not checkpoints:
            return None
        return checkpoints[-1]
