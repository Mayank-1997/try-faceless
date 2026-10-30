"""Repository interfaces for the business domain — abstract contracts for data access.

Each aggregate root has an interface defining the operations repositories
must implement. Repositories expose domain entities, never ORM models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.core.enums import (
    AssetGenerationStatus,
    AssetType,
    ContentType,
    JobPriority,
    JobStatus,
    JobType,
    ProjectStatus,
    PromptExecutionStatus,
    ResearchStatus,
    SceneGenerationStatus,
    SceneReviewStatus,
    ScriptStatus,
    StoryboardStatus,
    VideoStyle,
    WorkflowStatus,
    WorkflowStep,
)
from src.domain.entities.asset import BaseAsset
from src.domain.entities.cost_tracking import CostRecord
from src.domain.entities.generation_job import GenerationJob
from src.domain.entities.project import Project
from src.domain.entities.prompt_execution import PromptExecution
from src.domain.entities.research import Research
from src.domain.entities.scene import Scene
from src.domain.entities.script import Script
from src.domain.entities.storyboard import Storyboard
from src.domain.entities.token_tracking import TokenUsageRecord
from src.domain.entities.workflow import Workflow


# ---------------------------------------------------------------------------
# Project Repository
# ---------------------------------------------------------------------------
class ProjectRepository(ABC):
    """Abstract repository for the ``Project`` aggregate root."""

    @abstractmethod
    async def create(self, project: Project) -> Project:
        """Create a new project."""
        ...

    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get a project by ID (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_by_owner(
        self, owner_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Project]:
        """List projects owned by a user."""
        ...

    @abstractmethod
    async def update(self, project: Project) -> Project:
        """Update an existing project."""
        ...

    @abstractmethod
    async def soft_delete(self, project_id: UUID, deleted_by: UUID) -> bool:
        """Soft-delete a project."""
        ...

    @abstractmethod
    async def list_projects(
        self,
        *,
        status: ProjectStatus | None = None,
        content_type: ContentType | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        """List projects with optional filters and pagination."""
        ...

    @abstractmethod
    async def count_projects(
        self,
        *,
        status: ProjectStatus | None = None,
        owner_id: UUID | None = None,
    ) -> int:
        """Count projects with optional filters."""
        ...


# ---------------------------------------------------------------------------
# Workflow Repository
# ---------------------------------------------------------------------------
class WorkflowRepository(ABC):
    """Abstract repository for the ``Workflow`` aggregate."""

    @abstractmethod
    async def create(self, workflow: Workflow) -> Workflow:
        """Create a new workflow."""
        ...

    @abstractmethod
    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        """Get a workflow by ID."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Workflow]:
        """List workflows for a project."""
        ...

    @abstractmethod
    async def get_active_workflow(self, project_id: UUID) -> Workflow | None:
        """Get the currently active workflow for a project."""
        ...

    @abstractmethod
    async def get_latest_workflow(self, project_id: UUID) -> Workflow | None:
        """Get the latest workflow for a project regardless of status."""
        ...

    @abstractmethod
    async def update(self, workflow: Workflow) -> Workflow:
        """Update an existing workflow."""
        ...

    @abstractmethod
    async def list_by_status(
        self, status: WorkflowStatus, *, offset: int = 0, limit: int = 50
    ) -> list[Workflow]:
        """List workflows by status."""
        ...


# ---------------------------------------------------------------------------
# Research Repository
# ---------------------------------------------------------------------------
class ResearchRepository(ABC):
    """Abstract repository for the ``Research`` aggregate."""

    @abstractmethod
    async def create(self, research: Research) -> Research:
        """Create a new research version."""
        ...

    @abstractmethod
    async def get_by_id(self, research_id: UUID) -> Research | None:
        """Get a research version by ID."""
        ...

    @abstractmethod
    async def get_latest_version(self, project_id: UUID) -> Research | None:
        """Get the latest research version for a project."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Research]:
        """List all research versions for a project."""
        ...

    @abstractmethod
    async def update(self, research: Research) -> Research:
        """Update a research version."""
        ...

    @abstractmethod
    async def supersede_previous_versions(self, project_id: UUID, keep_version: int) -> int:
        """Mark all older versions as superseded. Returns count of superseded."""
        ...


# ---------------------------------------------------------------------------
# Script Repository
# ---------------------------------------------------------------------------
class ScriptRepository(ABC):
    """Abstract repository for the ``Script`` aggregate."""

    @abstractmethod
    async def create(self, script: Script) -> Script:
        """Create a new script version."""
        ...

    @abstractmethod
    async def get_by_id(self, script_id: UUID) -> Script | None:
        """Get a script version by ID."""
        ...

    @abstractmethod
    async def get_latest_version(self, project_id: UUID) -> Script | None:
        """Get the latest script version for a project."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Script]:
        """List all script versions for a project."""
        ...

    @abstractmethod
    async def update(self, script: Script) -> Script:
        """Update a script version."""
        ...


# ---------------------------------------------------------------------------
# Storyboard Repository
# ---------------------------------------------------------------------------
class StoryboardRepository(ABC):
    """Abstract repository for the ``Storyboard`` aggregate."""

    @abstractmethod
    async def create(self, storyboard: Storyboard) -> Storyboard:
        """Create a new storyboard version."""
        ...

    @abstractmethod
    async def get_by_id(self, storyboard_id: UUID) -> Storyboard | None:
        """Get a storyboard version by ID."""
        ...

    @abstractmethod
    async def get_latest_version(self, project_id: UUID) -> Storyboard | None:
        """Get the latest storyboard version for a project."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Storyboard]:
        """List all storyboard versions for a project."""
        ...

    @abstractmethod
    async def update(self, storyboard: Storyboard) -> Storyboard:
        """Update a storyboard version."""
        ...


# ---------------------------------------------------------------------------
# Scene Repository
# ---------------------------------------------------------------------------
class SceneRepository(ABC):
    """Abstract repository for the ``Scene`` aggregate."""

    @abstractmethod
    async def create(self, scene: Scene) -> Scene:
        """Create a new scene."""
        ...

    @abstractmethod
    async def get_by_id(self, scene_id: UUID) -> Scene | None:
        """Get a scene by ID."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 200
    ) -> list[Scene]:
        """List scenes for a project ordered by scene number."""
        ...

    @abstractmethod
    async def get_by_storyboard(self, storyboard_id: UUID) -> list[Scene]:
        """List scenes for a storyboard ordered by scene number."""
        ...

    @abstractmethod
    async def update(self, scene: Scene) -> Scene:
        """Update a scene."""
        ...

    @abstractmethod
    async def bulk_create(self, scenes: list[Scene]) -> list[Scene]:
        """Create multiple scenes at once."""
        ...

    @abstractmethod
    async def delete_by_project(self, project_id: UUID) -> int:
        """Delete all scenes for a project. Returns count deleted."""
        ...

    @abstractmethod
    async def list_by_generation_status(
        self, project_id: UUID, status: SceneGenerationStatus
    ) -> list[Scene]:
        """List scenes by generation status within a project."""
        ...

    @abstractmethod
    async def list_by_review_status(
        self, project_id: UUID, status: SceneReviewStatus
    ) -> list[Scene]:
        """List scenes by review status within a project."""
        ...


# ---------------------------------------------------------------------------
# Asset Repository
# ---------------------------------------------------------------------------
class AssetRepository(ABC):
    """Abstract repository for the ``BaseAsset`` aggregate."""

    @abstractmethod
    async def create(self, asset: BaseAsset) -> BaseAsset:
        """Create a new asset."""
        ...

    @abstractmethod
    async def get_by_id(self, asset_id: UUID) -> BaseAsset | None:
        """Get an asset by ID."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, asset_type: AssetType | None = None, offset: int = 0, limit: int = 100
    ) -> list[BaseAsset]:
        """List assets for a project with optional type filter."""
        ...

    @abstractmethod
    async def get_by_scene(self, scene_id: UUID) -> list[BaseAsset]:
        """List all assets for a scene."""
        ...

    @abstractmethod
    async def update(self, asset: BaseAsset) -> BaseAsset:
        """Update an asset."""
        ...

    @abstractmethod
    async def list_by_status(
        self, project_id: UUID, status: AssetGenerationStatus
    ) -> list[BaseAsset]:
        """List assets by generation status within a project."""
        ...


# ---------------------------------------------------------------------------
# Generation Job Repository
# ---------------------------------------------------------------------------
class GenerationJobRepository(ABC):
    """Abstract repository for the ``GenerationJob`` aggregate."""

    @abstractmethod
    async def create(self, job: GenerationJob) -> GenerationJob:
        """Create a new job."""
        ...

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> GenerationJob | None:
        """Get a job by ID."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[GenerationJob]:
        """List jobs for a project."""
        ...

    @abstractmethod
    async def update(self, job: GenerationJob) -> GenerationJob:
        """Update a job."""
        ...

    @abstractmethod
    async def list_by_status(
        self, status: JobStatus, *, offset: int = 0, limit: int = 100
    ) -> list[GenerationJob]:
        """List jobs by status (across all projects)."""
        ...

    @abstractmethod
    async def list_by_type(
        self, project_id: UUID, job_type: JobType
    ) -> list[GenerationJob]:
        """List jobs by type within a project."""
        ...

    @abstractmethod
    async def get_next_queued(self) -> GenerationJob | None:
        """Get the next queued job by priority."""
        ...


# ---------------------------------------------------------------------------
# Prompt Execution Repository
# ---------------------------------------------------------------------------
class PromptExecutionRepository(ABC):
    """Abstract repository for the ``PromptExecution`` aggregate."""

    @abstractmethod
    async def create(self, execution: PromptExecution) -> PromptExecution:
        """Create a new prompt execution record."""
        ...

    @abstractmethod
    async def get_by_id(self, execution_id: UUID) -> PromptExecution | None:
        """Get a prompt execution by ID."""
        ...

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[PromptExecution]:
        """List prompt executions for a project."""
        ...

    @abstractmethod
    async def get_by_workflow(
        self, workflow_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[PromptExecution]:
        """List prompt executions for a workflow."""
        ...

    @abstractmethod
    async def update(self, execution: PromptExecution) -> PromptExecution:
        """Update a prompt execution."""
        ...


# ---------------------------------------------------------------------------
# Analytics Repository (cost & token tracking)
# ---------------------------------------------------------------------------
class AnalyticsRepository(ABC):
    """Abstract repository for cost and token analytics."""

    # --- Cost tracking ---

    @abstractmethod
    async def create_cost_record(self, record: CostRecord) -> CostRecord:
        """Create a new cost record."""
        ...

    @abstractmethod
    async def get_project_costs(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[CostRecord]:
        """List cost records for a project."""
        ...

    @abstractmethod
    async def get_total_cost_by_project(self, project_id: UUID) -> float:
        """Get total cost for a project."""
        ...

    @abstractmethod
    async def get_total_cost_by_user(
        self, user_id: UUID, *, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> float:
        """Get total cost for a user within an optional date range."""
        ...

    @abstractmethod
    async def get_cost_breakdown_by_provider(self, project_id: UUID) -> dict[str, float]:
        """Get cost breakdown by provider for a project."""
        ...

    @abstractmethod
    async def get_cost_breakdown_by_category(self, project_id: UUID) -> dict[str, float]:
        """Get cost breakdown by category for a project."""
        ...

    # --- Token tracking ---

    @abstractmethod
    async def create_token_record(self, record: TokenUsageRecord) -> TokenUsageRecord:
        """Create a new token usage record."""
        ...

    @abstractmethod
    async def get_project_tokens(
        self, project_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> list[TokenUsageRecord]:
        """List token usage records for a project."""
        ...

    @abstractmethod
    async def get_total_tokens_by_project(self, project_id: UUID) -> int:
        """Get total tokens consumed for a project."""
        ...

    @abstractmethod
    async def get_total_tokens_by_user(
        self, user_id: UUID, *, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> int:
        """Get total tokens consumed by a user within an optional date range."""
        ...

    @abstractmethod
    async def get_token_breakdown_by_provider(self, project_id: UUID) -> dict[str, int]:
        """Get token usage breakdown by provider for a project."""
        ...
