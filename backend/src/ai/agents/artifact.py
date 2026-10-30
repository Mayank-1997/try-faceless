"""Artifact manager for the AI Agent Framework.

Responsible for storing and retrieving artifacts produced by agents:

- Research results
- Scripts
- Scene plans
- Images
- Videos
- Voice recordings
- Metadata
- Prompt outputs

Artifacts are stored in-memory by default (for testing) and can
be backed by the existing ``StorageGateway`` for persistent storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.ai.agents.exceptions import ArtifactError, ArtifactNotFoundError
from src.core.logging import get_logger


# ---------------------------------------------------------------------------
# Artifact types
# ---------------------------------------------------------------------------
class ArtifactType:
    """Constants for artifact types."""

    RESEARCH = "research"
    SCRIPT = "script"
    SCENE_PLAN = "scene_plan"
    STORYBOARD = "storyboard"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    METADATA = "metadata"
    PROMPT_OUTPUT = "prompt_output"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Artifact model
# ---------------------------------------------------------------------------
class Artifact(BaseModel):
    """An artifact produced by an agent.

    Attributes:
        id: Unique artifact identifier.
        agent_name: The agent that produced the artifact.
        artifact_type: The type of artifact (research, script, etc.).
        name: Human-readable name.
        content: The artifact content (text, JSON, etc.).
        metadata: Additional metadata (file path, URL, format, etc.).
        created_at: When the artifact was created.
        project_id: Optional project ID.
        execution_id: Optional execution ID.
        tags: Optional tags for categorization.
    """

    id: UUID = Field(default_factory=uuid4)
    agent_name: str = ""
    artifact_type: str = ""
    name: str = ""
    content: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: UUID | None = None
    execution_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Artifact manager
# ---------------------------------------------------------------------------
class ArtifactManager:
    """Manages artifact storage and retrieval.

    Stores artifacts in-memory by default.  Can be extended to use
    the existing ``StorageGateway`` for persistent storage.

    Attributes:
        storage_gateway: Optional storage gateway for persistence.
    """

    def __init__(self, storage_gateway: Any = None) -> None:
        """Initialize the artifact manager.

        Args:
            storage_gateway: Optional storage gateway for file-based persistence.
        """
        self._storage_gateway = storage_gateway
        self._logger = get_logger(__name__)
        self._artifacts: dict[UUID, Artifact] = {}
        self._by_agent: dict[str, list[UUID]] = {}
        self._by_type: dict[str, list[UUID]] = {}
        self._by_execution: dict[UUID, list[UUID]] = {}

    def store(
        self,
        *,
        agent_name: str,
        artifact_type: str,
        name: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
        project_id: UUID | None = None,
        execution_id: UUID | None = None,
        tags: list[str] | None = None,
    ) -> Artifact:
        """Store an artifact.

        Args:
            agent_name: The agent that produced the artifact.
            artifact_type: The type of artifact.
            name: Human-readable name.
            content: The artifact content.
            metadata: Additional metadata.
            project_id: Optional project ID.
            execution_id: Optional execution ID.
            tags: Optional tags.

        Returns:
            The stored ``Artifact`` with a generated ID.
        """
        artifact = Artifact(
            agent_name=agent_name,
            artifact_type=artifact_type,
            name=name,
            content=content,
            metadata=metadata or {},
            project_id=project_id,
            execution_id=execution_id,
            tags=tags or [],
        )

        self._artifacts[artifact.id] = artifact

        # Index by agent
        if agent_name not in self._by_agent:
            self._by_agent[agent_name] = []
        self._by_agent[agent_name].append(artifact.id)

        # Index by type
        if artifact_type not in self._by_type:
            self._by_type[artifact_type] = []
        self._by_type[artifact_type].append(artifact.id)

        # Index by execution
        if execution_id is not None:
            if execution_id not in self._by_execution:
                self._by_execution[execution_id] = []
            self._by_execution[execution_id].append(artifact.id)

        self._logger.info(
            "artifact_stored",
            artifact_id=str(artifact.id),
            agent=agent_name,
            artifact_type=artifact_type,
            name=name,
        )

        return artifact

    def get(self, artifact_id: UUID) -> Artifact:
        """Get an artifact by ID.

        Args:
            artifact_id: The artifact ID.

        Returns:
            The ``Artifact``.

        Raises:
            ArtifactNotFoundError: If the artifact doesn't exist.
        """
        if artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(str(artifact_id))
        return self._artifacts[artifact_id]

    def list_by_agent(self, agent_name: str) -> list[Artifact]:
        """List artifacts produced by a specific agent.

        Args:
            agent_name: The agent name.

        Returns:
            List of artifacts.
        """
        ids = self._by_agent.get(agent_name, [])
        return [self._artifacts[aid] for aid in ids if aid in self._artifacts]

    def list_by_type(self, artifact_type: str) -> list[Artifact]:
        """List artifacts of a specific type.

        Args:
            artifact_type: The artifact type.

        Returns:
            List of artifacts.
        """
        ids = self._by_type.get(artifact_type, [])
        return [self._artifacts[aid] for aid in ids if aid in self._artifacts]

    def list_by_execution(self, execution_id: UUID) -> list[Artifact]:
        """List artifacts for a specific execution.

        Args:
            execution_id: The execution ID.

        Returns:
            List of artifacts.
        """
        ids = self._by_execution.get(execution_id, [])
        return [self._artifacts[aid] for aid in ids if aid in self._artifacts]

    def list_all(self) -> list[Artifact]:
        """List all stored artifacts.

        Returns:
            List of all artifacts.
        """
        return list(self._artifacts.values())

    def delete(self, artifact_id: UUID) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: The artifact ID.

        Returns:
            True if deleted, False if not found.
        """
        if artifact_id not in self._artifacts:
            return False

        artifact = self._artifacts[artifact_id]

        # Remove from indexes
        if artifact.agent_name in self._by_agent:
            self._by_agent[artifact.agent_name] = [
                aid for aid in self._by_agent[artifact.agent_name] if aid != artifact_id
            ]

        if artifact.artifact_type in self._by_type:
            self._by_type[artifact.artifact_type] = [
                aid for aid in self._by_type[artifact.artifact_type] if aid != artifact_id
            ]

        if artifact.execution_id is not None and artifact.execution_id in self._by_execution:
            self._by_execution[artifact.execution_id] = [
                aid for aid in self._by_execution[artifact.execution_id] if aid != artifact_id
            ]

        del self._artifacts[artifact_id]
        self._logger.info("artifact_deleted", artifact_id=str(artifact_id))
        return True

    def delete_by_execution(self, execution_id: UUID) -> int:
        """Delete all artifacts for an execution.

        Args:
            execution_id: The execution ID.

        Returns:
            Number of artifacts deleted.
        """
        ids = self._by_execution.get(execution_id, [])
        count = 0
        for aid in list(ids):
            if self.delete(aid):
                count += 1
        return count

    @property
    def count(self) -> int:
        """Return the total number of stored artifacts."""
        return len(self._artifacts)

    def clear(self) -> None:
        """Clear all artifacts."""
        self._artifacts.clear()
        self._by_agent.clear()
        self._by_type.clear()
        self._by_execution.clear()
