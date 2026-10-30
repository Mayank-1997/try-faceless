"""Unit of Work pattern — transactional boundary for repository operations.

Coordinates transactional consistency across multiple repositories.
Supports nested transactions via savepoints, rollback, and commit.

Usage::

    async with UnitOfWork(session_factory) as uow:
        project = await uow.projects.create(project)
        workflow = await uow.workflows.create(workflow)
        await uow.commit()

If an exception occurs, the context manager automatically rolls back.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    """Async Unit of Work wrapping an ``AsyncSession``.

    Provides access to all repositories within a single transactional
    boundary. Nested transactions are supported via savepoints.

    Attributes:
        session: The underlying SQLAlchemy async session.
        projects: ProjectRepository instance.
        workflows: WorkflowRepository instance.
        research: ResearchRepository instance.
        scripts: ScriptRepository instance.
        storyboards: StoryboardRepository instance.
        scenes: SceneRepository instance.
        assets: AssetRepository instance.
        jobs: GenerationJobRepository instance.
        prompt_executions: PromptExecutionRepository instance.
        analytics: AnalyticsRepository instance.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        repositories: dict[str, Any] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._repositories: dict[str, Any] = repositories or {}
        self._savepoint_stack: list[Any] = []

    @property
    def session(self) -> AsyncSession:
        """Get the current session, raising if not in a context."""
        if self._session is None:
            raise RuntimeError("UnitOfWork must be used as an async context manager")
        return self._session

    async def __aenter__(self) -> UnitOfWork:
        """Begin a new transactional session."""
        self._session = self._session_factory()
        await self._session.__aenter__()
        self._register_repositories()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Roll back on exception, close session."""
        if exc_type is not None:
            await self.rollback()
        if self._session is not None:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

    def _register_repositories(self) -> None:
        """Instantiate all repositories with the current session.

        Repositories are imported lazily to avoid circular imports.
        """
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

        session = self.session
        self.projects = ProjectRepositoryImpl(session)
        self.workflows = WorkflowRepositoryImpl(session)
        self.research = ResearchRepositoryImpl(session)
        self.scripts = ScriptRepositoryImpl(session)
        self.storyboards = StoryboardRepositoryImpl(session)
        self.scenes = SceneRepositoryImpl(session)
        self.assets = AssetRepositoryImpl(session)
        self.jobs = GenerationJobRepositoryImpl(session)
        self.prompt_executions = PromptExecutionRepositoryImpl(session)
        self.analytics = AnalyticsRepositoryImpl(session)

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._session is not None:
            await self._session.rollback()

    async def begin_nested(self) -> None:
        """Begin a nested transaction (savepoint)."""
        if self._session is not None:
            sp = await self._session.begin_nested()
            self._savepoint_stack.append(sp)

    async def release_nested(self) -> None:
        """Release the current savepoint (commit it)."""
        if self._savepoint_stack:
            sp = self._savepoint_stack.pop()
            await sp.commit()

    async def rollback_nested(self) -> None:
        """Roll back to the current savepoint."""
        if self._savepoint_stack:
            sp = self._savepoint_stack.pop()
            await sp.rollback()

    @property
    def is_active(self) -> bool:
        """Check if the transaction is still active."""
        return self._session is not None and self._session.in_transaction()


def unit_of_work_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> type[UnitOfWork]:
    """Create a UnitOfWork class bound to a specific session factory.

    Useful for dependency injection in FastAPI.
    """

    class BoundUnitOfWork(UnitOfWork):
        def __init__(self) -> None:
            super().__init__(session_factory)

    return BoundUnitOfWork
