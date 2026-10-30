"""Generation Orchestrator.

The orchestrator is the top-level coordinator for the generation platform.

Responsibilities:
- Receive requests
- Validate requests
- Estimate execution
- Estimate cost
- Select provider
- Create generation jobs
- Submit jobs to queue
- Track progress
- Persist outputs
- Emit workflow events
- Return generated assets
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.logging import get_logger
from src.generation.budget import BudgetManager
from src.generation.cache import CacheManager
from src.generation.concurrency import ConcurrencyManager
from src.generation.events import GenerationEventEmitter
from src.generation.executor import GenerationExecutor
from src.generation.health import ProviderHealthMonitor
from src.generation.provider_selection import ProviderSelectionEngine
from src.generation.queue_manager import QueueManager
from src.generation.quality import QualityEngine
from src.generation.schema import (
    AssetCategory,
    GeneratedAsset,
    GenerationJob,
    GenerationProgress,
    GenerationRequest,
    GenerationStrategy,
    JobPriority,
    JobStatus,
    ValidationReport,
)
from src.generation.strategy import GenerationStrategyEngine
from src.generation.validation import ValidationPipeline


class GenerationOrchestrator:
    """Top-level coordinator for the generation platform.

    Receives generation requests, creates jobs, submits them to the
    queue, executes them through the executor, validates results,
    and returns generated assets.

    Never calls providers directly — delegates to the executor.
    """

    def __init__(
        self,
        *,
        strategy_engine: GenerationStrategyEngine | None = None,
        queue: QueueManager | None = None,
        provider_selection: ProviderSelectionEngine | None = None,
        budget: BudgetManager | None = None,
        concurrency: ConcurrencyManager | None = None,
        health: ProviderHealthMonitor | None = None,
        cache: CacheManager | None = None,
        executor: GenerationExecutor | None = None,
        validation: ValidationPipeline | None = None,
        quality: QualityEngine | None = None,
        events: GenerationEventEmitter | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._strategy_engine = strategy_engine or GenerationStrategyEngine()
        self._queue = queue or QueueManager()
        self._health = health or ProviderHealthMonitor()
        self._provider_selection = provider_selection or ProviderSelectionEngine(self._health)
        self._budget = budget or BudgetManager()
        self._concurrency = concurrency or ConcurrencyManager()
        self._cache = cache or CacheManager()
        self._executor = executor or GenerationExecutor(
            cache=self._cache,
            health=self._health,
            concurrency=self._concurrency,
            event_emitter=events,
        )
        self._validation = validation or ValidationPipeline()
        self._quality = quality or QualityEngine()
        self._events = events or GenerationEventEmitter()
        self._jobs: dict[Any, GenerationJob] = {}  # job_id -> job
        self._assets: dict[Any, GeneratedAsset] = {}  # asset_id -> asset
        self._progress = GenerationProgress()

    @property
    def progress(self) -> GenerationProgress:
        """Current generation progress."""
        self._progress.queued = self._queue.queue_size
        self._progress.update_percentage()
        return self._progress

    @property
    def strategy_engine(self) -> GenerationStrategyEngine:
        return self._strategy_engine

    @property
    def provider_selection(self) -> ProviderSelectionEngine:
        return self._provider_selection

    @property
    def budget_manager(self) -> BudgetManager:
        return self._budget

    @property
    def health_monitor(self) -> ProviderHealthMonitor:
        return self._health

    @property
    def cache_manager(self) -> CacheManager:
        return self._cache

    @property
    def queue_manager(self) -> QueueManager:
        return self._queue

    async def submit(
        self,
        request: GenerationRequest,
        *,
        strategy: GenerationStrategy | None = None,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> GenerationJob:
        """Submit a generation request.

        Creates a job, selects a provider, estimates cost, checks
        budget, and enqueues the job.

        Args:
            request: The generation request.
            strategy: Optional strategy override. Uses balanced if not provided.
            priority: Job priority.

        Returns:
            The created ``GenerationJob``.
        """
        if strategy is None:
            strategy = self._strategy_engine.get_strategy("balanced")

        # Select provider
        selection = self._provider_selection.select(request, strategy)
        if selection is None:
            raise ValueError(f"No provider available for category {request.category.value}")

        provider_name, model, estimated_cost = selection

        # Budget check
        estimate = self._budget.estimate(request, provider_name, model, estimated_cost)
        if not estimate.affordable:
            # Try downgrade
            downgrade = self._budget.recommend_downgrade(request)
            if downgrade:
                self._logger.info(
                    "budget_downgrade_recommended",
                    original=request.category.value,
                    downgrade=downgrade.value,
                )
                request.category = downgrade
                selection = self._provider_selection.select(request, strategy)
                if selection:
                    provider_name, model, estimated_cost = selection

        # Create job
        job = GenerationJob(
            request=request,
            priority=priority,
            provider=provider_name,
            model=model,
            estimated_cost=estimated_cost,
            max_retries=strategy.max_retries,
            metadata={
                "enable_caching": strategy.enable_caching,
                "enable_fallback": strategy.enable_fallback,
                "strategy_mode": strategy.mode.value,
            },
        )

        self._jobs[job.id] = job
        self._progress.total_jobs += 1

        # Enqueue
        await self._queue.enqueue(job)
        self._logger.info(
            "job_submitted",
            job_id=str(job.id),
            scene_id=request.scene_id,
            category=request.category.value,
            provider=provider_name,
            estimated_cost=estimated_cost,
        )
        return job

    async def submit_batch(
        self,
        requests: list[GenerationRequest],
        *,
        strategy: GenerationStrategy | None = None,
    ) -> list[GenerationJob]:
        """Submit multiple generation requests.

        Args:
            requests: List of generation requests.
            strategy: Optional strategy override.

        Returns:
            List of created jobs.
        """
        jobs = []
        for req in requests:
            job = await self.submit(req, strategy=strategy)
            jobs.append(job)
        return jobs

    async def process_queue(self) -> list[GeneratedAsset]:
        """Process all jobs in the queue.

        Dequeues jobs, executes them, validates results, and
        records quality scores.

        Returns:
            List of generated assets.
        """
        assets: list[GeneratedAsset] = []

        while True:
            job = await self._queue.dequeue()
            if job is None:
                break

            try:
                asset = await self._executor.execute(job)

                # Validate
                report = await self._validation.validate(asset)
                if not report.overall_valid:
                    self._logger.warning(
                        "asset_validation_failed",
                        asset_id=str(asset.id),
                        reason=report.rejected_reason,
                    )
                    # Retry if possible
                    if job.retry_count < job.max_retries:
                        await self._queue.retry(job, report.rejected_reason or "Validation failed")
                        continue
                    else:
                        self._progress.failed += 1
                        continue

                # Evaluate quality
                quality_result = self._quality.evaluate(asset)
                asset.quality_score = quality_result.overall_score
                asset.quality_result = quality_result

                # Record spend
                self._budget.record_spend(
                    job.request.project_id,
                    job.request.scene_id,
                    job.request.category,
                    asset.cost_usd,
                )

                self._assets[asset.id] = asset
                assets.append(asset)
                self._progress.completed += 1

            except Exception as exc:
                self._logger.error("job_processing_failed", job_id=str(job.id), error=str(exc))
                if job.retry_count < job.max_retries:
                    await self._queue.retry(job, str(exc))
                else:
                    self._progress.failed += 1

        # Process retries
        retries = await self._queue.move_retries_to_queue()
        if retries > 0:
            retry_assets = await self.process_queue()
            assets.extend(retry_assets)

        return assets

    async def cancel_job(self, job_id: Any) -> bool:
        """Cancel a job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            ``True`` if cancelled.
        """
        await self._queue.cancel(job_id)
        if job_id in self._jobs:
            self._jobs[job_id].status = JobStatus.CANCELLED
        self._progress.cancelled += 1
        return True

    def get_job(self, job_id: Any) -> GenerationJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_asset(self, asset_id: Any) -> GeneratedAsset | None:
        """Get an asset by ID."""
        return self._assets.get(asset_id)

    def get_all_assets(self) -> list[GeneratedAsset]:
        """Get all generated assets."""
        return list(self._assets.values())

    def get_assets_for_scene(self, scene_id: str) -> list[GeneratedAsset]:
        """Get all assets for a specific scene."""
        return [a for a in self._assets.values() if a.scene_id == scene_id]

    def get_assets_for_project(self, project_id: str) -> list[GeneratedAsset]:
        """Get all assets for a project."""
        return [a for a in self._assets.values() if a.metadata.get("project_id") == project_id]
