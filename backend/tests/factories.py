"""Test factories — factory functions for creating test objects.

These factories produce valid domain objects, workflow states, and
configurations with sensible defaults.  Tests can override individual
fields as needed.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.core.config_service import ConfigService
from src.core.enums import (
    AgentType,
    AIProvider,
    AssetType,
    ProjectInputType,
    ProjectStatus,
)
from src.core.interfaces import ProviderConfig
from src.workflow.state import (
    AssetData,
    CostData,
    ExecutionStatus,
    ProjectInfo,
    SceneData,
    ScriptData,
    WorkflowState,
)


def make_provider_config(
    *,
    api_key: str = "test-key",
    model: str = "test-model",
    max_retries: int = 3,
    request_timeout: int = 10,
    extra: dict[str, Any] | None = None,
) -> ProviderConfig:
    """Create a ``ProviderConfig`` for testing."""
    return ProviderConfig(
        api_key=api_key,
        model=model,
        max_retries=max_retries,
        request_timeout=request_timeout,
        extra=extra or {},
    )


def make_workflow_state(
    *,
    project_name: str = "Test Project",
    scene_count: int = 3,
) -> WorkflowState:
    """Create a ``WorkflowState`` with sensible test defaults.

    Args:
        project_name: Name for the test project.
        scene_count: Number of scenes to generate.

    Returns:
        A fully populated ``WorkflowState`` for testing.
    """
    state = WorkflowState(
        project=ProjectInfo(
            project_id=uuid4(),
            name=project_name,
            input_type=ProjectInputType.TOPIC,
            status=ProjectStatus.DRAFT,
        ),
        execution=ExecutionStatus(
            current_agent=AgentType.DIRECTOR,
            total_steps=10,
        ),
    )

    for i in range(1, scene_count + 1):
        state.scenes.append(
            SceneData(
                scene_number=i,
                title=f"Scene {i}",
                narration=f"Narration for scene {i}",
                estimated_duration=10.0,
            )
        )
        state.assets.append(
            AssetData(
                scene_number=i,
                asset_type=AssetType.IMAGE,
            )
        )

    state.script = ScriptData(
        title=f"Script for {project_name}",
        content="Test script content",
        word_count=100,
    )

    state.cost = CostData(total_cost_usd=0.05)

    return state


def make_test_config_service(
    *,
    gemini_api_key: str = "test-gemini-key",
    testing: bool = True,
) -> ConfigService:
    """Create a ``ConfigService`` configured for testing.

    Sets environment variables before creating the config, ensuring
    tests don't depend on real environment configuration.
    """
    os.environ.setdefault("GEMINI_API_KEY", gemini_api_key)
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("DEBUG", "true")

    from src.core.config import get_settings

    # Clear the lru_cache to pick up new env vars
    get_settings.cache_clear()
    config = ConfigService()
    if testing:
        config.set_testing_mode(True)
    return config


def make_temp_dir() -> Path:
    """Create a temporary directory and return its path.

    The caller is responsible for cleaning up the directory.
    """
    return Path(tempfile.mkdtemp(prefix="ai_studio_test_"))
