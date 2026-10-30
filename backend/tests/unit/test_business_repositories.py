"""Unit tests for business domain repositories and entities.

Tests cover:
- Project CRUD operations (create, get, update, soft-delete, list, count)
- Workflow lifecycle (create, get, active workflow, update, list by status)
- Research versioning (create, latest version, supersede)
- Script CRUD and versioning
- Storyboard CRUD and versioning
- Scene CRUD, bulk create, filtering by status
- Asset creation with inheritance (Image, Video, Voice, Subtitle, Thumbnail)
- Generation job lifecycle and queue priority
- Prompt execution tracking
- Cost and token analytics
- Specification pattern in-memory and query building
- Unit of Work transactional behavior
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import (
    AIProvider,
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
    StorageType,
    VideoStyle,
    WorkflowStatus,
    WorkflowStep,
)
from src.domain.entities.asset import (
    ImageAsset,
    SubtitleAsset,
    ThumbnailAsset,
    VideoAsset,
    VoiceAsset,
)
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
from src.domain.repositories.specifications import (
    ActiveProjects,
    CompletedProjects,
    ProjectsByOwner,
    QueuedJobs,
    ReadyAssets,
    RunningJobs,
)
from src.persistence.repositories.business_repositories import (
    AnalyticsRepositoryImpl,
    AssetRepositoryImpl,
    GenerationJobRepositoryImpl,
    ProjectRepositoryImpl,
    PromptExecutionRepositoryImpl,
    ResearchRepositoryImpl,
    SceneRepositoryImpl,
    ScriptRepositoryImpl,
    StoryboardRepositoryImpl,
    WorkflowRepositoryImpl,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def owner_id() -> "uuid4":
    return uuid4()


@pytest.fixture
def project_repo(test_db: AsyncSession) -> ProjectRepositoryImpl:
    return ProjectRepositoryImpl(test_db)


@pytest.fixture
def workflow_repo(test_db: AsyncSession) -> WorkflowRepositoryImpl:
    return WorkflowRepositoryImpl(test_db)


@pytest.fixture
def research_repo(test_db: AsyncSession) -> ResearchRepositoryImpl:
    return ResearchRepositoryImpl(test_db)


@pytest.fixture
def script_repo(test_db: AsyncSession) -> ScriptRepositoryImpl:
    return ScriptRepositoryImpl(test_db)


@pytest.fixture
def storyboard_repo(test_db: AsyncSession) -> StoryboardRepositoryImpl:
    return StoryboardRepositoryImpl(test_db)


@pytest.fixture
def scene_repo(test_db: AsyncSession) -> SceneRepositoryImpl:
    return SceneRepositoryImpl(test_db)


@pytest.fixture
def asset_repo(test_db: AsyncSession) -> AssetRepositoryImpl:
    return AssetRepositoryImpl(test_db)


@pytest.fixture
def job_repo(test_db: AsyncSession) -> GenerationJobRepositoryImpl:
    return GenerationJobRepositoryImpl(test_db)


@pytest.fixture
def prompt_repo(test_db: AsyncSession) -> PromptExecutionRepositoryImpl:
    return PromptExecutionRepositoryImpl(test_db)


@pytest.fixture
def analytics_repo(test_db: AsyncSession) -> AnalyticsRepositoryImpl:
    return AnalyticsRepositoryImpl(test_db)


async def _create_user(test_db: AsyncSession) -> "uuid4":
    """Create a minimal user row so FK constraints are satisfied."""
    from datetime import datetime, timezone
    from src.persistence.models.auth import UserModel
    user_id = uuid4()
    orm = UserModel(
        id=user_id,
        email=f"test-{user_id}@example.com",
        username=f"testuser-{user_id.hex[:8]}",
        first_name="Test",
        last_name="User",
        status="active",
        auth_provider="local",
        email_verified=True,
        two_factor_enabled=False,
        hashed_password="dummy_hash",
    )
    test_db.add(orm)
    await test_db.flush()
    return user_id


async def _create_project(project_repo: ProjectRepositoryImpl, owner_id: "uuid4") -> Project:
    """Helper to create a project."""
    return await project_repo.create(
        Project(
            owner_id=owner_id,
            title="Test Video Project",
            description="A test project for unit testing",
            tags=["tech", "ai"],
            metadata={"key": "value"},
        )
    )


# ---------------------------------------------------------------------------
# Project Repository Tests
# ---------------------------------------------------------------------------
class TestProjectRepository:
    """Tests for ProjectRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_project(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        assert project.id is not None
        assert project.title == "Test Video Project"
        assert project.status == ProjectStatus.DRAFT
        assert project.current_step == WorkflowStep.INITIALIZATION
        assert project.tags == ["tech", "ai"]
        assert project.metadata == {"key": "value"}
        assert project.deleted_at is None

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        created = await _create_project(project_repo, owner_id)
        fetched = await project_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test Video Project"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_nonexistent(
        self, project_repo: ProjectRepositoryImpl
    ) -> None:
        fetched = await project_repo.get_by_id(uuid4())
        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_by_owner(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        await _create_project(project_repo, owner_id)
        await project_repo.create(
            Project(owner_id=owner_id, title="Second Project")
        )
        projects = await project_repo.get_by_owner(owner_id)
        assert len(projects) == 2

    @pytest.mark.asyncio
    async def test_update_project(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        project.title = "Updated Title"
        project.description = "Updated description"
        project.update_status(ProjectStatus.RESEARCHING)
        updated = await project_repo.update(project)
        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"
        assert updated.status == ProjectStatus.RESEARCHING

    @pytest.mark.asyncio
    async def test_soft_delete(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        result = await project_repo.soft_delete(project.id, owner_id)
        assert result is True
        fetched = await project_repo.get_by_id(project.id)
        assert fetched is None  # soft-deleted projects are excluded

    @pytest.mark.asyncio
    async def test_list_projects_with_filter(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        p1 = await _create_project(project_repo, owner_id)
        p2 = await project_repo.create(
            Project(owner_id=owner_id, title="Completed Project", status=ProjectStatus.COMPLETED)
        )
        all_projects = await project_repo.list_projects()
        assert len(all_projects) == 2
        completed = await project_repo.list_projects(status=ProjectStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].title == "Completed Project"

    @pytest.mark.asyncio
    async def test_count_projects(
        self, project_repo: ProjectRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession
    ) -> None:
        await _create_user(test_db)
        await _create_project(project_repo, owner_id)
        await project_repo.create(Project(owner_id=owner_id, title="Second"))
        count = await project_repo.count_projects()
        assert count == 2
        count_by_owner = await project_repo.count_projects(owner_id=owner_id)
        assert count_by_owner == 2


# ---------------------------------------------------------------------------
# Workflow Repository Tests
# ---------------------------------------------------------------------------
class TestWorkflowRepository:
    """Tests for WorkflowRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_workflow(
        self, workflow_repo: WorkflowRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        workflow = await workflow_repo.create(
            Workflow(project_id=project.id, version=1)
        )
        assert workflow.id is not None
        assert workflow.project_id == project.id
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.version == 1

    @pytest.mark.asyncio
    async def test_get_active_workflow(
        self, workflow_repo: WorkflowRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await workflow_repo.create(Workflow(project_id=project.id, version=1, status=WorkflowStatus.RUNNING))
        active = await workflow_repo.get_active_workflow(project.id)
        assert active is not None
        assert active.status == WorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_workflow(
        self, workflow_repo: WorkflowRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        workflow = await workflow_repo.create(Workflow(project_id=project.id))
        workflow.start()
        workflow.advance_to(WorkflowStep.RESEARCH)
        updated = await workflow_repo.update(workflow)
        assert updated.status == WorkflowStatus.RUNNING
        assert updated.current_step == WorkflowStep.RESEARCH
        assert updated.started_at is not None

    @pytest.mark.asyncio
    async def test_list_by_status(
        self, workflow_repo: WorkflowRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await workflow_repo.create(Workflow(project_id=project.id, status=WorkflowStatus.RUNNING))
        await workflow_repo.create(Workflow(project_id=project.id, version=2, status=WorkflowStatus.COMPLETED))
        running = await workflow_repo.list_by_status(WorkflowStatus.RUNNING)
        assert len(running) == 1
        completed = await workflow_repo.list_by_status(WorkflowStatus.COMPLETED)
        assert len(completed) == 1


# ---------------------------------------------------------------------------
# Research Repository Tests
# ---------------------------------------------------------------------------
class TestResearchRepository:
    """Tests for ResearchRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_research(
        self, research_repo: ResearchRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        research = await research_repo.create(
            Research(
                project_id=project.id,
                summary="AI is transforming content creation.",
                sources=["https://example.com/ai"],
                keywords=["AI", "content", "automation"],
            )
        )
        assert research.id is not None
        assert research.summary == "AI is transforming content creation."
        assert research.sources == ["https://example.com/ai"]
        assert research.keywords == ["AI", "content", "automation"]
        assert research.version == 1

    @pytest.mark.asyncio
    async def test_get_latest_version(
        self, research_repo: ResearchRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await research_repo.create(Research(project_id=project.id, version=1, summary="v1"))
        await research_repo.create(Research(project_id=project.id, version=2, summary="v2"))
        latest = await research_repo.get_latest_version(project.id)
        assert latest is not None
        assert latest.version == 2
        assert latest.summary == "v2"

    @pytest.mark.asyncio
    async def test_supersede_previous_versions(
        self, research_repo: ResearchRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await research_repo.create(Research(project_id=project.id, version=1, summary="v1"))
        await research_repo.create(Research(project_id=project.id, version=2, summary="v2"))
        count = await research_repo.supersede_previous_versions(project.id, keep_version=2)
        assert count == 1
        all_versions = await research_repo.get_by_project(project.id)
        v1 = [r for r in all_versions if r.version == 1][0]
        assert v1.status == ResearchStatus.SUPERSEDED


# ---------------------------------------------------------------------------
# Script Repository Tests
# ---------------------------------------------------------------------------
class TestScriptRepository:
    """Tests for ScriptRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_script(
        self, script_repo: ScriptRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        script = await script_repo.create(
            Script(
                project_id=project.id,
                hook="Did you know AI can write scripts?",
                body="Full script body here...",
                cta="Subscribe for more!",
                word_count=500,
            )
        )
        assert script.id is not None
        assert script.hook == "Did you know AI can write scripts?"
        assert script.word_count == 500
        assert script.version == 1

    @pytest.mark.asyncio
    async def test_get_latest_version(
        self, script_repo: ScriptRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await script_repo.create(Script(project_id=project.id, version=1, body="v1"))
        await script_repo.create(Script(project_id=project.id, version=2, body="v2"))
        latest = await script_repo.get_latest_version(project.id)
        assert latest is not None
        assert latest.version == 2

    @pytest.mark.asyncio
    async def test_update_script_status(
        self, script_repo: ScriptRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        script = await script_repo.create(Script(project_id=project.id, body="Test"))
        script.approve()
        updated = await script_repo.update(script)
        assert updated.status == ScriptStatus.APPROVED


# ---------------------------------------------------------------------------
# Scene Repository Tests
# ---------------------------------------------------------------------------
class TestSceneRepository:
    """Tests for SceneRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_scene(
        self, scene_repo: SceneRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        scene = await scene_repo.create(
            Scene(
                project_id=project.id,
                scene_number=1,
                title="Opening Scene",
                narration="Welcome to the future of AI.",
                duration_seconds=15.0,
            )
        )
        assert scene.id is not None
        assert scene.scene_number == 1
        assert scene.title == "Opening Scene"
        assert scene.generation_status == SceneGenerationStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_by_project_ordered(
        self, scene_repo: SceneRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await scene_repo.create(Scene(project_id=project.id, scene_number=3, title="Third"))
        await scene_repo.create(Scene(project_id=project.id, scene_number=1, title="First"))
        await scene_repo.create(Scene(project_id=project.id, scene_number=2, title="Second"))
        scenes = await scene_repo.get_by_project(project.id)
        assert len(scenes) == 3
        assert scenes[0].scene_number == 1
        assert scenes[1].scene_number == 2
        assert scenes[2].scene_number == 3

    @pytest.mark.asyncio
    async def test_bulk_create(
        self, scene_repo: SceneRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        scenes = [
            Scene(project_id=project.id, scene_number=i, title=f"Scene {i}")
            for i in range(1, 6)
        ]
        created = await scene_repo.bulk_create(scenes)
        assert len(created) == 5
        all_scenes = await scene_repo.get_by_project(project.id)
        assert len(all_scenes) == 5

    @pytest.mark.asyncio
    async def test_list_by_generation_status(
        self, scene_repo: SceneRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        s1 = await scene_repo.create(Scene(project_id=project.id, scene_number=1))
        s2 = await scene_repo.create(Scene(project_id=project.id, scene_number=2))
        s2.mark_generated()
        await scene_repo.update(s2)
        pending = await scene_repo.list_by_generation_status(project.id, SceneGenerationStatus.PENDING)
        generated = await scene_repo.list_by_generation_status(project.id, SceneGenerationStatus.GENERATED)
        assert len(pending) == 1
        assert len(generated) == 1


# ---------------------------------------------------------------------------
# Asset Repository Tests
# ---------------------------------------------------------------------------
class TestAssetRepository:
    """Tests for AssetRepositoryImpl with inheritance."""

    @pytest.mark.asyncio
    async def test_create_image_asset(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        scene_repo: SceneRepositoryImpl, owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        scene = await scene_repo.create(Scene(project_id=project.id, scene_number=1))
        asset = await asset_repo.create(
            ImageAsset(
                project_id=project.id,
                scene_id=scene.id,
                width=1920,
                height=1080,
                format="png",
                prompt="A futuristic city skyline at sunset",
                negative_prompt="blurry, low quality",
                provider=AIProvider.IMAGEN,
            )
        )
        assert asset.id is not None
        assert isinstance(asset, ImageAsset)
        assert asset.width == 1920
        assert asset.height == 1080
        assert asset.prompt == "A futuristic city skyline at sunset"

    @pytest.mark.asyncio
    async def test_create_video_asset(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        asset = await asset_repo.create(
            VideoAsset(
                project_id=project.id,
                width=1920,
                height=1080,
                duration_seconds=10.0,
                fps=30,
                prompt="Camera panning across a futuristic city",
                provider=AIProvider.VEO,
            )
        )
        assert asset.id is not None
        assert isinstance(asset, VideoAsset)
        assert asset.duration_seconds == 10.0
        assert asset.fps == 30

    @pytest.mark.asyncio
    async def test_create_voice_asset(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        asset = await asset_repo.create(
            VoiceAsset(
                project_id=project.id,
                duration_seconds=30.0,
                language="en-US",
                voice_name="en-US-Standard-A",
                speaking_rate=1.0,
                provider=AIProvider.GOOGLE_TTS,
            )
        )
        assert asset.id is not None
        assert isinstance(asset, VoiceAsset)
        assert asset.voice_name == "en-US-Standard-A"

    @pytest.mark.asyncio
    async def test_create_subtitle_asset(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        asset = await asset_repo.create(
            SubtitleAsset(
                project_id=project.id,
                language="en",
                word_count=500,
            )
        )
        assert asset.id is not None
        assert isinstance(asset, SubtitleAsset)
        assert asset.word_count == 500

    @pytest.mark.asyncio
    async def test_create_thumbnail_asset(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        asset = await asset_repo.create(
            ThumbnailAsset(
                project_id=project.id,
                width=1280,
                height=720,
                is_default=True,
            )
        )
        assert asset.id is not None
        assert isinstance(asset, ThumbnailAsset)
        assert asset.is_default is True

    @pytest.mark.asyncio
    async def test_get_by_project_with_type_filter(
        self, asset_repo: AssetRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await asset_repo.create(ImageAsset(project_id=project.id, width=100, height=100))
        await asset_repo.create(VideoAsset(project_id=project.id, width=100, height=100, duration_seconds=5.0))
        all_assets = await asset_repo.get_by_project(project.id)
        assert len(all_assets) == 2
        images = await asset_repo.get_by_project(project.id, asset_type=AssetType.IMAGE)
        assert len(images) == 1
        assert isinstance(images[0], ImageAsset)


# ---------------------------------------------------------------------------
# Generation Job Repository Tests
# ---------------------------------------------------------------------------
class TestGenerationJobRepository:
    """Tests for GenerationJobRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_job(
        self, job_repo: GenerationJobRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        job = await job_repo.create(
            GenerationJob(
                project_id=project.id,
                job_type=JobType.RESEARCH,
                priority=JobPriority.HIGH,
            )
        )
        assert job.id is not None
        assert job.status == JobStatus.QUEUED
        assert job.priority == JobPriority.HIGH

    @pytest.mark.asyncio
    async def test_job_lifecycle(
        self, job_repo: GenerationJobRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        job = await job_repo.create(GenerationJob(project_id=project.id, job_type=JobType.IMAGE))
        job.start()
        await job_repo.update(job)
        assert job.status == JobStatus.RUNNING
        job.complete(result={"output": "generated.png"})
        await job_repo.update(job)
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"output": "generated.png"}
        assert job.execution_time_seconds is not None

    @pytest.mark.asyncio
    async def test_list_by_status(
        self, job_repo: GenerationJobRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await job_repo.create(GenerationJob(project_id=project.id, job_type=JobType.RESEARCH))
        await job_repo.create(GenerationJob(project_id=project.id, job_type=JobType.SCRIPT))
        queued = await job_repo.list_by_status(JobStatus.QUEUED)
        assert len(queued) == 2

    @pytest.mark.asyncio
    async def test_can_retry_property(
        self, job_repo: GenerationJobRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        job = await job_repo.create(
            GenerationJob(project_id=project.id, job_type=JobType.IMAGE, max_retries=2)
        )
        assert job.can_retry is False  # not failed yet
        job.fail("Generation error")
        await job_repo.update(job)
        assert job.can_retry is True
        job.retry()
        await job_repo.update(job)
        assert job.retry_count == 1
        job.fail("Another error")
        await job_repo.update(job)
        job.retry()
        await job_repo.update(job)
        assert job.retry_count == 2
        assert job.can_retry is False  # max retries reached


# ---------------------------------------------------------------------------
# Prompt Execution Repository Tests
# ---------------------------------------------------------------------------
class TestPromptExecutionRepository:
    """Tests for PromptExecutionRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_and_get(
        self, prompt_repo: PromptExecutionRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        execution = await prompt_repo.create(
            PromptExecution(
                project_id=project.id,
                agent_type="research_agent",
                prompt_template="research_template_v1",
                rendered_prompt="Research the topic of AI video generation",
                provider=AIProvider.GEMINI,
                model="gemini-2.0-flash",
                temperature=0.7,
            )
        )
        assert execution.id is not None
        assert execution.status == PromptExecutionStatus.PENDING
        fetched = await prompt_repo.get_by_id(execution.id)
        assert fetched is not None
        assert fetched.agent_type == "research_agent"

    @pytest.mark.asyncio
    async def test_mark_success(
        self, prompt_repo: PromptExecutionRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        execution = await prompt_repo.create(
            PromptExecution(project_id=project.id, provider=AIProvider.GEMINI, model="gemini-2.0-flash")
        )
        execution.mark_success(
            response="AI video generation is...",
            latency_ms=1500,
            cost_usd=0.002,
            input_tokens=500,
            output_tokens=200,
        )
        updated = await prompt_repo.update(execution)
        assert updated.status == PromptExecutionStatus.SUCCESS
        assert updated.response == "AI video generation is..."
        assert updated.latency_ms == 1500
        assert updated.total_tokens == 700


# ---------------------------------------------------------------------------
# Analytics Repository Tests
# ---------------------------------------------------------------------------
class TestAnalyticsRepository:
    """Tests for AnalyticsRepositoryImpl."""

    @pytest.mark.asyncio
    async def test_create_cost_record(
        self, analytics_repo: AnalyticsRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        record = await analytics_repo.create_cost_record(
            CostRecord(
                project_id=project.id,
                user_id=owner_id,
                provider=AIProvider.GEMINI,
                cost_usd=0.005,
                cost_category="llm",
            )
        )
        assert record.id is not None
        assert record.cost_usd == 0.005

    @pytest.mark.asyncio
    async def test_total_cost_by_project(
        self, analytics_repo: AnalyticsRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await analytics_repo.create_cost_record(
            CostRecord(project_id=project.id, cost_usd=0.01, cost_category="llm")
        )
        await analytics_repo.create_cost_record(
            CostRecord(project_id=project.id, cost_usd=0.02, cost_category="image")
        )
        total = await analytics_repo.get_total_cost_by_project(project.id)
        assert total == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_category(
        self, analytics_repo: AnalyticsRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await analytics_repo.create_cost_record(
            CostRecord(project_id=project.id, cost_usd=0.01, cost_category="llm")
        )
        await analytics_repo.create_cost_record(
            CostRecord(project_id=project.id, cost_usd=0.02, cost_category="image")
        )
        await analytics_repo.create_cost_record(
            CostRecord(project_id=project.id, cost_usd=0.03, cost_category="llm")
        )
        breakdown = await analytics_repo.get_cost_breakdown_by_category(project.id)
        assert breakdown["llm"] == pytest.approx(0.04)
        assert breakdown["image"] == pytest.approx(0.02)

    @pytest.mark.asyncio
    async def test_create_token_record(
        self, analytics_repo: AnalyticsRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        record = await analytics_repo.create_token_record(
            TokenUsageRecord(
                project_id=project.id,
                user_id=owner_id,
                provider=AIProvider.GEMINI,
                agent_type="research_agent",
                model="gemini-2.0-flash",
                input_tokens=500,
                output_tokens=200,
            )
        )
        assert record.id is not None
        assert record.total_tokens == 700

    @pytest.mark.asyncio
    async def test_total_tokens_by_project(
        self, analytics_repo: AnalyticsRepositoryImpl, project_repo: ProjectRepositoryImpl,
        owner_id: "uuid4", test_db: AsyncSession,
    ) -> None:
        await _create_user(test_db)
        project = await _create_project(project_repo, owner_id)
        await analytics_repo.create_token_record(
            TokenUsageRecord(project_id=project.id, input_tokens=500, output_tokens=200)
        )
        await analytics_repo.create_token_record(
            TokenUsageRecord(project_id=project.id, input_tokens=300, output_tokens=100)
        )
        total = await analytics_repo.get_total_tokens_by_project(project.id)
        assert total == 1100


# ---------------------------------------------------------------------------
# Specification Pattern Tests
# ---------------------------------------------------------------------------
class TestSpecifications:
    """Tests for the specification pattern."""

    def test_projects_by_owner_in_memory(self, owner_id: "uuid4") -> None:
        from uuid import uuid4
        spec = ProjectsByOwner(owner_id)
        matching = Project(owner_id=owner_id, title="Match")
        non_matching = Project(owner_id=uuid4(), title="No Match")
        assert spec.is_satisfied_by(matching) is True
        assert spec.is_satisfied_by(non_matching) is False

    def test_completed_projects_in_memory(self) -> None:
        spec = CompletedProjects()
        completed = Project(owner_id=uuid4(), title="Done", status=ProjectStatus.COMPLETED)
        draft = Project(owner_id=uuid4(), title="Draft", status=ProjectStatus.DRAFT)
        assert spec.is_satisfied_by(completed) is True
        assert spec.is_satisfied_by(draft) is False

    def test_active_projects_in_memory(self) -> None:
        spec = ActiveProjects()
        active = Project(owner_id=uuid4(), title="Active", status=ProjectStatus.GENERATING)
        cancelled = Project(owner_id=uuid4(), title="Cancelled", status=ProjectStatus.CANCELLED)
        assert spec.is_satisfied_by(active) is True
        assert spec.is_satisfied_by(cancelled) is False

    def test_and_composition(self, owner_id: "uuid4") -> None:
        spec = ProjectsByOwner(owner_id) & CompletedProjects()
        matching = Project(owner_id=owner_id, title="Done", status=ProjectStatus.COMPLETED)
        non_matching = Project(owner_id=owner_id, title="Draft", status=ProjectStatus.DRAFT)
        assert spec.is_satisfied_by(matching) is True
        assert spec.is_satisfied_by(non_matching) is False

    def test_or_composition(self, owner_id: "uuid4") -> None:
        from uuid import uuid4
        spec = ProjectsByOwner(owner_id) | CompletedProjects()
        matching1 = Project(owner_id=owner_id, title="Mine")
        matching2 = Project(owner_id=uuid4(), title="Completed", status=ProjectStatus.COMPLETED)
        non_matching = Project(owner_id=uuid4(), title="Other Draft")
        assert spec.is_satisfied_by(matching1) is True
        assert spec.is_satisfied_by(matching2) is True
        assert spec.is_satisfied_by(non_matching) is False

    def test_not_composition(self) -> None:
        spec = ~CompletedProjects()
        draft = Project(owner_id=uuid4(), title="Draft", status=ProjectStatus.DRAFT)
        completed = Project(owner_id=uuid4(), title="Done", status=ProjectStatus.COMPLETED)
        assert spec.is_satisfied_by(draft) is True
        assert spec.is_satisfied_by(completed) is False

    def test_queued_jobs_in_memory(self) -> None:
        spec = QueuedJobs()
        queued = GenerationJob(project_id=uuid4(), job_type=JobType.RESEARCH, status=JobStatus.QUEUED)
        running = GenerationJob(project_id=uuid4(), job_type=JobType.RESEARCH, status=JobStatus.RUNNING)
        assert spec.is_satisfied_by(queued) is True
        assert spec.is_satisfied_by(running) is False

    def test_ready_assets_in_memory(self) -> None:
        spec = ReadyAssets()
        ready = ImageAsset(project_id=uuid4(), generation_status=AssetGenerationStatus.READY)
        planned = ImageAsset(project_id=uuid4(), generation_status=AssetGenerationStatus.PLANNED)
        assert spec.is_satisfied_by(ready) is True
        assert spec.is_satisfied_by(planned) is False


# ---------------------------------------------------------------------------
# Domain Entity Behavior Tests
# ---------------------------------------------------------------------------
class TestDomainEntityBehavior:
    """Tests for domain entity business logic."""

    def test_project_update_status(self) -> None:
        project = Project(owner_id=uuid4(), title="Test")
        project.update_status(ProjectStatus.GENERATING)
        assert project.status == ProjectStatus.GENERATING

    def test_project_add_remove_tag(self) -> None:
        project = Project(owner_id=uuid4(), title="Test")
        project.add_tag("ai")
        assert "ai" in project.tags
        project.add_tag("ai")  # duplicate should not add
        assert len(project.tags) == 1
        project.remove_tag("ai")
        assert "ai" not in project.tags

    def test_project_soft_delete(self) -> None:
        owner = uuid4()
        project = Project(owner_id=owner, title="Test")
        project.soft_delete(owner)
        assert project.is_deleted is True
        assert project.deleted_by == owner
        assert project.status == ProjectStatus.CANCELLED
        project.restore()
        assert project.is_deleted is False

    def test_workflow_complete_calculates_execution_time(self) -> None:
        workflow = Workflow(project_id=uuid4())
        workflow.start()
        workflow.complete()
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.execution_time_seconds is not None
        assert workflow.execution_time_seconds >= 0

    def test_workflow_fail_sets_reason(self) -> None:
        workflow = Workflow(project_id=uuid4())
        workflow.start()
        workflow.fail("API timeout")
        assert workflow.status == WorkflowStatus.FAILED
        assert workflow.failure_reason == "API timeout"

    def test_workflow_retry_increments_count(self) -> None:
        workflow = Workflow(project_id=uuid4())
        assert workflow.retry_count == 0
        workflow.retry()
        assert workflow.retry_count == 1
        assert workflow.status == WorkflowStatus.RUNNING

    def test_scene_mark_generated(self) -> None:
        scene = Scene(project_id=uuid4(), scene_number=1)
        assert scene.generation_status == SceneGenerationStatus.PENDING
        scene.mark_generated()
        assert scene.generation_status == SceneGenerationStatus.GENERATED
        assert scene.is_ready_for_review is True

    def test_scene_approve(self) -> None:
        scene = Scene(project_id=uuid4(), scene_number=1)
        scene.approve()
        assert scene.review_status == SceneReviewStatus.APPROVED

    def test_asset_mark_ready(self) -> None:
        asset = ImageAsset(project_id=uuid4())
        assert asset.is_ready is False
        asset.mark_ready()
        assert asset.is_ready is True

    def test_prompt_execution_total_tokens(self) -> None:
        execution = PromptExecution(
            project_id=uuid4(),
            input_tokens=500,
            output_tokens=200,
        )
        assert execution.total_tokens == 700

    def test_job_can_retry(self) -> None:
        job = GenerationJob(project_id=uuid4(), job_type=JobType.IMAGE, max_retries=3)
        assert job.can_retry is False
        job.fail("error")
        assert job.can_retry is True
        assert job.is_terminal is True

    def test_job_is_terminal(self) -> None:
        job = GenerationJob(project_id=uuid4(), job_type=JobType.RESEARCH)
        assert job.is_terminal is False
        job.complete()
        assert job.is_terminal is True

    def test_cost_record_to_dict(self) -> None:
        record = CostRecord(project_id=uuid4(), cost_usd=0.05, cost_category="llm")
        d = record.to_dict()
        assert d["cost_usd"] == 0.05
        assert d["cost_category"] == "llm"

    def test_token_usage_record_total_tokens(self) -> None:
        record = TokenUsageRecord(project_id=uuid4(), input_tokens=100, output_tokens=50)
        assert record.total_tokens == 150
