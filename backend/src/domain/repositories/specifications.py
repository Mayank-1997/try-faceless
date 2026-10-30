"""Specification pattern — reusable, composable query specifications.

Specifications encapsulate business query logic in a reusable way.
Each specification knows how to test an entity in-memory and how to
build a SQLAlchemy filter clause for database queries.

Usage::

    spec = ProjectsByOwner(user_id)
    projects = await repo.list_with_spec(spec)

    # Compose with AND / OR / NOT
    spec = ProjectsByOwner(user_id) & CompletedProjects()
    projects = await repo.list_with_spec(spec)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, and_, or_, not_, select
from sqlalchemy.sql.elements import BinaryExpression

from src.core.enums import (
    AssetGenerationStatus,
    JobStatus,
    ProjectStatus,
    ResearchStatus,
    ScriptStatus,
    SceneGenerationStatus,
)
from src.domain.entities.asset import BaseAsset
from src.domain.entities.generation_job import GenerationJob
from src.domain.entities.project import Project
from src.domain.entities.research import Research
from src.domain.entities.scene import Scene
from src.domain.entities.script import Script
from src.persistence.models.business import (
    AssetModel,
    GenerationJobModel,
    ProjectModel,
    ResearchModel,
    SceneModel,
    ScriptModel,
)

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """Base specification interface.

    Specifications can be composed using ``&`` (AND), ``|`` (OR), and
    ``~`` (NOT) operators.
    """

    @abstractmethod
    def is_satisfied_by(self, entity: T) -> bool:
        """Check if an entity satisfies this specification (in-memory)."""
        ...

    @abstractmethod
    def to_query(self) -> BinaryExpression:
        """Build a SQLAlchemy filter clause for this specification."""
        ...

    def __and__(self, other: Specification[T]) -> AndSpecification[T]:
        return AndSpecification(self, other)

    def __or__(self, other: Specification[T]) -> OrSpecification[T]:
        return OrSpecification(self, other)

    def __invert__(self) -> NotSpecification[T]:
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """Logical AND of two specifications."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self.left = left
        self.right = right

    def is_satisfied_by(self, entity: T) -> bool:
        return self.left.is_satisfied_by(entity) and self.right.is_satisfied_by(entity)

    def to_query(self) -> BinaryExpression:
        return and_(self.left.to_query(), self.right.to_query())


class OrSpecification(Specification[T]):
    """Logical OR of two specifications."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self.left = left
        self.right = right

    def is_satisfied_by(self, entity: T) -> bool:
        return self.left.is_satisfied_by(entity) or self.right.is_satisfied_by(entity)

    def to_query(self) -> BinaryExpression:
        return or_(self.left.to_query(), self.right.to_query())


class NotSpecification(Specification[T]):
    """Logical NOT of a specification."""

    def __init__(self, spec: Specification[T]) -> None:
        self.spec = spec

    def is_satisfied_by(self, entity: T) -> bool:
        return not self.spec.is_satisfied_by(entity)

    def to_query(self) -> BinaryExpression:
        return not_(self.spec.to_query())


# ---------------------------------------------------------------------------
# Project specifications
# ---------------------------------------------------------------------------
class ProjectsByOwner(Specification[Project]):
    """Projects owned by a specific user."""

    def __init__(self, owner_id: Any) -> None:
        self.owner_id = owner_id

    def is_satisfied_by(self, entity: Project) -> bool:
        return entity.owner_id == self.owner_id

    def to_query(self) -> BinaryExpression:
        return ProjectModel.owner_id == self.owner_id


class CompletedProjects(Specification[Project]):
    """Projects with completed status."""

    def is_satisfied_by(self, entity: Project) -> bool:
        return entity.status == ProjectStatus.COMPLETED

    def to_query(self) -> BinaryExpression:
        return ProjectModel.status == ProjectStatus.COMPLETED.value


class ActiveProjects(Specification[Project]):
    """Projects that are not deleted, cancelled, or completed."""

    _active_statuses = {
        ProjectStatus.DRAFT,
        ProjectStatus.RESEARCHING,
        ProjectStatus.SCRIPTING,
        ProjectStatus.PLANNING,
        ProjectStatus.GENERATING,
        ProjectStatus.RENDERING,
        ProjectStatus.PUBLISHING,
    }

    def is_satisfied_by(self, entity: Project) -> bool:
        return entity.status in self._active_statuses

    def to_query(self) -> BinaryExpression:
        return ProjectModel.status.in_([s.value for s in self._active_statuses])


# ---------------------------------------------------------------------------
# Job specifications
# ---------------------------------------------------------------------------
class RunningJobs(Specification[GenerationJob]):
    """Jobs that are currently running."""

    def is_satisfied_by(self, entity: GenerationJob) -> bool:
        return entity.status == JobStatus.RUNNING

    def to_query(self) -> BinaryExpression:
        return GenerationJobModel.status == JobStatus.RUNNING.value


class QueuedJobs(Specification[GenerationJob]):
    """Jobs that are queued."""

    def is_satisfied_by(self, entity: GenerationJob) -> bool:
        return entity.status == JobStatus.QUEUED

    def to_query(self) -> BinaryExpression:
        return GenerationJobModel.status == JobStatus.QUEUED.value


# ---------------------------------------------------------------------------
# Asset specifications
# ---------------------------------------------------------------------------
class AssetsByScene(Specification[BaseAsset]):
    """Assets belonging to a specific scene."""

    def __init__(self, scene_id: Any) -> None:
        self.scene_id = scene_id

    def is_satisfied_by(self, entity: BaseAsset) -> bool:
        return entity.scene_id == self.scene_id

    def to_query(self) -> BinaryExpression:
        return AssetModel.scene_id == self.scene_id


class ReadyAssets(Specification[BaseAsset]):
    """Assets that are ready for use."""

    def is_satisfied_by(self, entity: BaseAsset) -> bool:
        return entity.is_ready

    def to_query(self) -> BinaryExpression:
        return AssetModel.generation_status == AssetGenerationStatus.READY.value


# ---------------------------------------------------------------------------
# Script specifications
# ---------------------------------------------------------------------------
class LatestScriptVersion(Specification[Script]):
    """Latest approved script version for a project."""

    def __init__(self, project_id: Any) -> None:
        self.project_id = project_id

    def is_satisfied_by(self, entity: Script) -> bool:
        return entity.project_id == self.project_id and entity.status == ScriptStatus.APPROVED

    def to_query(self) -> BinaryExpression:
        return and_(
            ScriptModel.project_id == self.project_id,
            ScriptModel.status == ScriptStatus.APPROVED.value,
        )


# ---------------------------------------------------------------------------
# Research specifications
# ---------------------------------------------------------------------------
class LatestResearchVersion(Specification[Research]):
    """Latest completed research version for a project."""

    def __init__(self, project_id: Any) -> None:
        self.project_id = project_id

    def is_satisfied_by(self, entity: Research) -> bool:
        return entity.project_id == self.project_id and entity.status == ResearchStatus.COMPLETED

    def to_query(self) -> BinaryExpression:
        return and_(
            ResearchModel.project_id == self.project_id,
            ResearchModel.status == ResearchStatus.COMPLETED.value,
        )


# ---------------------------------------------------------------------------
# Scene specifications
# ---------------------------------------------------------------------------
class ScenesPendingGeneration(Specification[Scene]):
    """Scenes that are pending asset generation."""

    def is_satisfied_by(self, entity: Scene) -> bool:
        return entity.generation_status == SceneGenerationStatus.PENDING

    def to_query(self) -> BinaryExpression:
        return SceneModel.generation_status == SceneGenerationStatus.PENDING.value
