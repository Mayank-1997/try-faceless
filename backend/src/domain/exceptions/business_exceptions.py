"""Business domain exceptions — errors for the project/workflow/scene/asset domain.

These exceptions extend the core ``DomainError`` hierarchy and are
specific to the AI Video Studio business domain. They are distinct
from the IAM exceptions in ``auth_exceptions.py``.
"""

from __future__ import annotations

from src.core.exceptions import DomainError, EntityNotFoundError


# ---------------------------------------------------------------------------
# Project errors
# ---------------------------------------------------------------------------
class ProjectError(DomainError):
    """Base exception for project-related errors."""

    code = "PROJECT_ERROR"
    status_code = 400


class ProjectNotFoundError(ProjectError, EntityNotFoundError):
    """Raised when a project cannot be found."""

    code = "PROJECT_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Project '{identifier}' not found")


class ProjectAccessDeniedError(ProjectError):
    """Raised when a user tries to access a project they don't own."""

    code = "PROJECT_ACCESS_DENIED"
    status_code = 403

    def __init__(self, project_id: str, user_id: str) -> None:
        super().__init__(f"User '{user_id}' does not have access to project '{project_id}'")


class ProjectAlreadyExistsError(ProjectError):
    """Raised when attempting to create a duplicate project."""

    code = "PROJECT_ALREADY_EXISTS"
    status_code = 409

    def __init__(self, title: str) -> None:
        super().__init__(f"Project with title '{title}' already exists")


# ---------------------------------------------------------------------------
# Workflow errors
# ---------------------------------------------------------------------------
class WorkflowError(DomainError):
    """Base exception for workflow-related errors."""

    code = "WORKFLOW_ERROR"
    status_code = 400


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow cannot be found."""

    code = "WORKFLOW_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Workflow '{identifier}' not found")


class WorkflowAlreadyRunningError(WorkflowError):
    """Raised when attempting to start a workflow that is already running."""

    code = "WORKFLOW_ALREADY_RUNNING"
    status_code = 409

    def __init__(self, project_id: str) -> None:
        super().__init__(f"Project '{project_id}' already has a running workflow")


class WorkflowStepError(WorkflowError):
    """Raised when an invalid workflow step transition is attempted."""

    code = "WORKFLOW_STEP_ERROR"
    status_code = 400

    def __init__(self, current_step: str, attempted_step: str) -> None:
        super().__init__(
            f"Cannot transition from '{current_step}' to '{attempted_step}'"
        )


# ---------------------------------------------------------------------------
# Research errors
# ---------------------------------------------------------------------------
class ResearchError(DomainError):
    """Base exception for research-related errors."""

    code = "RESEARCH_ERROR"
    status_code = 400


class ResearchNotFoundError(ResearchError):
    """Raised when a research version cannot be found."""

    code = "RESEARCH_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Research '{identifier}' not found")


# ---------------------------------------------------------------------------
# Script errors
# ---------------------------------------------------------------------------
class ScriptError(DomainError):
    """Base exception for script-related errors."""

    code = "SCRIPT_ERROR"
    status_code = 400


class ScriptNotFoundError(ScriptError):
    """Raised when a script version cannot be found."""

    code = "SCRIPT_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Script '{identifier}' not found")


# ---------------------------------------------------------------------------
# Storyboard errors
# ---------------------------------------------------------------------------
class StoryboardError(DomainError):
    """Base exception for storyboard-related errors."""

    code = "STORYBOARD_ERROR"
    status_code = 400


class StoryboardNotFoundError(StoryboardError):
    """Raised when a storyboard version cannot be found."""

    code = "STORYBOARD_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Storyboard '{identifier}' not found")


# ---------------------------------------------------------------------------
# Scene errors
# ---------------------------------------------------------------------------
class SceneError(DomainError):
    """Base exception for scene-related errors."""

    code = "SCENE_ERROR"
    status_code = 400


class SceneNotFoundError(SceneError):
    """Raised when a scene cannot be found."""

    code = "SCENE_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Scene '{identifier}' not found")


class SceneGenerationError(SceneError):
    """Raised when scene asset generation fails."""

    code = "SCENE_GENERATION_ERROR"
    status_code = 500

    def __init__(self, scene_id: str, detail: str = "Generation failed") -> None:
        super().__init__(f"Scene '{scene_id}': {detail}")


# ---------------------------------------------------------------------------
# Asset errors
# ---------------------------------------------------------------------------
class AssetError(DomainError):
    """Base exception for asset-related errors."""

    code = "ASSET_ERROR"
    status_code = 400


class AssetNotFoundError(AssetError):
    """Raised when an asset cannot be found."""

    code = "ASSET_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str = "Asset not found") -> None:
        super().__init__(identifier)


class AssetGenerationError(AssetError):
    """Raised when asset generation fails."""

    code = "ASSET_GENERATION_ERROR"
    status_code = 500

    def __init__(self, detail: str = "Asset generation failed") -> None:
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Generation job errors
# ---------------------------------------------------------------------------
class GenerationJobError(DomainError):
    """Base exception for generation job errors."""

    code = "GENERATION_JOB_ERROR"
    status_code = 400


class GenerationJobNotFoundError(GenerationJobError):
    """Raised when a generation job cannot be found."""

    code = "GENERATION_JOB_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str = "Job not found") -> None:
        super().__init__(identifier)


class GenerationJobAlreadyExistsError(GenerationJobError):
    """Raised when attempting to create a duplicate job."""

    code = "GENERATION_JOB_ALREADY_EXISTS"
    status_code = 409

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Job '{identifier}' already exists")


# ---------------------------------------------------------------------------
# Prompt execution errors
# ---------------------------------------------------------------------------
class PromptExecutionError(DomainError):
    """Base exception for prompt execution errors."""

    code = "PROMPT_EXECUTION_ERROR"
    status_code = 400


class PromptExecutionNotFoundError(PromptExecutionError):
    """Raised when a prompt execution record cannot be found."""

    code = "PROMPT_EXECUTION_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str = "Prompt execution not found") -> None:
        super().__init__(identifier)
