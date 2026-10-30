"""Tests for the Phase 9 Generation Platform."""

from __future__ import annotations

import asyncio
import pytest
from uuid import uuid4

from src.generation.budget import BudgetManager
from src.generation.cache import CacheManager
from src.generation.concurrency import ConcurrencyManager
from src.generation.events import GenerationEventEmitter, GenerationEvents
from src.generation.executor import GenerationExecutor
from src.generation.health import ProviderHealthMonitor
from src.generation.manifest import AssetManifestBuilder
from src.generation.orchestrator import GenerationOrchestrator
from src.generation.provider_selection import ProviderSelectionEngine
from src.generation.quality import QualityEngine
from src.generation.queue_manager import QueueManager
from src.generation.schema import (
    AssetCategory,
    AssetManifest,
    BudgetEstimate,
    BudgetStatus,
    CacheEntry,
    CacheKey,
    GeneratedAsset,
    GenerationJob,
    GenerationMode,
    GenerationProgress,
    GenerationRequest,
    GenerationStrategy,
    JobPriority,
    JobStatus,
    ProviderHealthMetrics,
    QualityResult,
    SceneAssetManifest,
    ValidationReport,
    ValidationResult,
    ValidationStage,
)
from src.generation.strategy import GenerationStrategyEngine
from src.generation.subtitle import SubtitleGenerator
from src.generation.thumbnail import ThumbnailGenerator
from src.generation.validation import ValidationPipeline


# ===========================================================================
# Schema tests
# ===========================================================================
class TestSchemas:
    def test_generation_mode_values(self):
        assert GenerationMode.ECONOMY.value == "economy"
        assert GenerationMode.BALANCED.value == "balanced"
        assert GenerationMode.PREMIUM.value == "premium"
        assert GenerationMode.FAST.value == "fast"
        assert GenerationMode.CUSTOM.value == "custom"

    def test_asset_category_values(self):
        assert AssetCategory.IMAGE.value == "image"
        assert AssetCategory.VIDEO.value == "video"
        assert AssetCategory.VOICE.value == "voice"
        assert AssetCategory.MUSIC.value == "music"
        assert AssetCategory.SOUND_EFFECT.value == "sound_effect"
        assert AssetCategory.SUBTITLE.value == "subtitle"
        assert AssetCategory.THUMBNAIL.value == "thumbnail"

    def test_job_status_values(self):
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.GENERATING.value == "generating"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_priority_ordering(self):
        assert JobPriority.CRITICAL < JobPriority.HIGH
        assert JobPriority.HIGH < JobPriority.NORMAL
        assert JobPriority.NORMAL < JobPriority.LOW
        assert JobPriority.LOW < JobPriority.BACKGROUND

    def test_validation_stage_values(self):
        assert ValidationStage.FILE_VALIDATION.value == "file_validation"
        assert ValidationStage.CONTENT_SAFETY.value == "content_safety"

    def test_generation_strategy_defaults(self):
        s = GenerationStrategy()
        assert s.mode == GenerationMode.BALANCED
        assert s.resolution == "1920x1080"
        assert s.max_retries == 3
        assert s.concurrency == 4
        assert s.enable_caching is True

    def test_generation_request_defaults(self):
        r = GenerationRequest()
        assert r.category == AssetCategory.IMAGE
        assert r.aspect_ratio == "16:9"
        assert r.resolution == "1920x1080"
        assert r.prompt_version == "1.0.0"

    def test_generation_job_is_terminal(self):
        job = GenerationJob(status=JobStatus.COMPLETED)
        assert job.is_terminal is True
        job2 = GenerationJob(status=JobStatus.QUEUED)
        assert job2.is_terminal is False

    def test_generation_job_execution_time(self):
        from datetime import datetime, timezone, timedelta
        job = GenerationJob()
        assert job.execution_time_seconds == 0.0
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = job.started_at + timedelta(seconds=5)
        assert abs(job.execution_time_seconds - 5.0) < 0.1

    def test_provider_health_metrics_defaults(self):
        m = ProviderHealthMetrics()
        assert m.healthy is True
        assert m.availability == 1.0
        assert m.failure_rate == 0.0

    def test_provider_health_failure_rate(self):
        m = ProviderHealthMetrics(success_count=8, failure_count=2)
        assert m.failure_rate == 0.2

    def test_budget_estimate_defaults(self):
        e = BudgetEstimate()
        assert e.affordable is True
        assert e.estimated_cost == 0.0

    def test_budget_status_defaults(self):
        s = BudgetStatus()
        assert s.exceeded is False
        assert s.remaining == 0.0

    def test_validation_result_defaults(self):
        r = ValidationResult()
        assert r.valid is True
        assert r.errors == []

    def test_validation_report_defaults(self):
        r = ValidationReport()
        assert r.overall_valid is True
        assert r.results == []

    def test_quality_result_defaults(self):
        q = QualityResult()
        assert q.overall_score == 0.0
        assert q.visual_quality == 0.0

    def test_generated_asset_defaults(self):
        a = GeneratedAsset()
        assert a.category == AssetCategory.IMAGE
        assert a.cached is False
        assert a.version == 1

    def test_scene_asset_manifest_defaults(self):
        m = SceneAssetManifest()
        assert m.image is None
        assert m.video is None
        assert m.effects == []
        assert m.generation_status == JobStatus.QUEUED

    def test_asset_manifest_defaults(self):
        m = AssetManifest()
        assert m.version == 1
        assert m.is_complete is True  # no scenes = vacuously true
        assert m.scene_count == 0

    def test_asset_manifest_is_complete(self):
        m = AssetManifest(scene_manifests=[
            SceneAssetManifest(generation_status=JobStatus.COMPLETED),
            SceneAssetManifest(generation_status=JobStatus.QUEUED),
        ])
        assert m.is_complete is False

    def test_generation_progress_defaults(self):
        p = GenerationProgress()
        assert p.is_complete is True  # 0 total = complete
        assert p.progress_percentage == 0.0

    def test_generation_progress_update_percentage(self):
        p = GenerationProgress(total_jobs=10, completed=5)
        p.update_percentage()
        assert p.progress_percentage == 50.0

    def test_cache_key_to_hash(self):
        key = CacheKey(prompt="test", provider="imagen", model="imagen-3")
        h = key.to_hash()
        assert len(h) == 64  # SHA-256 hex

    def test_cache_key_deterministic(self):
        key1 = CacheKey(prompt="test", provider="imagen", model="imagen-3")
        key2 = CacheKey(prompt="test", provider="imagen", model="imagen-3")
        assert key1.to_hash() == key2.to_hash()

    def test_cache_key_different_prompts(self):
        key1 = CacheKey(prompt="test1", provider="imagen", model="imagen-3")
        key2 = CacheKey(prompt="test2", provider="imagen", model="imagen-3")
        assert key1.to_hash() != key2.to_hash()

    def test_cache_entry_defaults(self):
        e = CacheEntry()
        assert e.hit_count == 0


# ===========================================================================
# Strategy Engine tests
# ===========================================================================
class TestGenerationStrategyEngine:
    def test_get_economy_strategy(self):
        engine = GenerationStrategyEngine()
        s = engine.get_strategy(GenerationMode.ECONOMY)
        assert s.mode == GenerationMode.ECONOMY
        assert s.resolution == "1280x720"
        assert s.max_cost_usd == 2.0

    def test_get_balanced_strategy(self):
        engine = GenerationStrategyEngine()
        s = engine.get_strategy(GenerationMode.BALANCED)
        assert s.mode == GenerationMode.BALANCED
        assert s.resolution == "1920x1080"
        assert s.max_cost_usd == 10.0

    def test_get_premium_strategy(self):
        engine = GenerationStrategyEngine()
        s = engine.get_strategy(GenerationMode.PREMIUM)
        assert s.mode == GenerationMode.PREMIUM
        assert s.resolution == "3840x2160"
        assert s.max_cost_usd == 50.0

    def test_get_fast_strategy(self):
        engine = GenerationStrategyEngine()
        s = engine.get_strategy(GenerationMode.FAST)
        assert s.mode == GenerationMode.FAST
        assert s.concurrency == 8
        assert s.max_retries == 1

    def test_get_custom_without_name_raises(self):
        engine = GenerationStrategyEngine()
        with pytest.raises(ValueError):
            engine.get_strategy(GenerationMode.CUSTOM)

    def test_register_custom_strategy(self):
        engine = GenerationStrategyEngine()
        custom = GenerationStrategy(
            mode=GenerationMode.CUSTOM,
            resolution="2560x1440",
            max_cost_usd=20.0,
        )
        engine.register_custom_strategy("my_custom", custom)
        result = engine.get_custom_strategy("my_custom")
        assert result is not None
        assert result.resolution == "2560x1440"

    def test_create_strategy_with_overrides(self):
        engine = GenerationStrategyEngine()
        s = engine.create_strategy(
            GenerationMode.BALANCED,
            resolution="2560x1440",
            concurrency=8,
        )
        assert s.resolution == "2560x1440"
        assert s.concurrency == 8
        assert s.mode == GenerationMode.BALANCED

    def test_list_modes(self):
        engine = GenerationStrategyEngine()
        modes = engine.list_modes()
        assert "economy" in modes
        assert "balanced" in modes
        assert "premium" in modes
        assert "fast" in modes
        assert "custom" not in modes

    def test_list_custom_strategies(self):
        engine = GenerationStrategyEngine()
        engine.register_custom_strategy("test1", GenerationStrategy())
        engine.register_custom_strategy("test2", GenerationStrategy())
        customs = engine.list_custom_strategies()
        assert "test1" in customs
        assert "test2" in customs


# ===========================================================================
# Queue Manager tests
# ===========================================================================
class TestQueueManager:
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL)
        await q.enqueue(job)
        assert q.queue_size == 1
        dequeued = await q.dequeue()
        assert dequeued is not None
        assert dequeued.id == job.id
        assert q.queue_size == 0

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        q = QueueManager()
        job_low = GenerationJob(id=uuid4(), priority=JobPriority.LOW)
        job_high = GenerationJob(id=uuid4(), priority=JobPriority.HIGH)
        job_normal = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL)
        await q.enqueue(job_low)
        await q.enqueue(job_high)
        await q.enqueue(job_normal)
        first = await q.dequeue()
        second = await q.dequeue()
        third = await q.dequeue()
        assert first.priority == JobPriority.HIGH
        assert second.priority == JobPriority.NORMAL
        assert third.priority == JobPriority.LOW

    @pytest.mark.asyncio
    async def test_cancel(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL)
        await q.enqueue(job)
        await q.cancel(job.id)
        dequeued = await q.dequeue()
        assert dequeued is None  # cancelled job is skipped

    @pytest.mark.asyncio
    async def test_retry_within_limit(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL, max_retries=3)
        await q.retry(job, "Test error")
        assert job.retry_count == 1
        assert job.status == JobStatus.RETRYING
        assert q.retry_queue_size == 1

    @pytest.mark.asyncio
    async def test_retry_exceeds_limit_to_dead_letter(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL, max_retries=2, retry_count=1)
        await q.retry(job, "Test error")
        assert job.retry_count == 2
        assert job.status == JobStatus.FAILED
        assert q.dead_letter_size == 1

    @pytest.mark.asyncio
    async def test_move_retries_to_queue(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL, max_retries=3)
        await q.retry(job, "Test error")
        count = await q.move_retries_to_queue()
        assert count == 1
        assert q.queue_size == 1
        assert q.retry_queue_size == 0

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        q = QueueManager()
        await q.pause()
        assert q.is_paused is True
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL)
        await q.enqueue(job)
        assert await q.dequeue() is None  # paused
        await q.resume()
        assert q.is_paused is False
        dequeued = await q.dequeue()
        assert dequeued is not None

    @pytest.mark.asyncio
    async def test_dead_letter(self):
        q = QueueManager()
        job = GenerationJob(id=uuid4(), priority=JobPriority.NORMAL)
        await q.dead_letter(job)
        assert q.dead_letter_size == 1
        assert job.status == JobStatus.FAILED

    def test_get_dead_letter_jobs(self):
        q = QueueManager()
        assert q.get_dead_letter_jobs() == []

    def test_clear(self):
        q = QueueManager()
        q.clear()
        assert q.queue_size == 0


# ===========================================================================
# Provider Health Monitor tests
# ===========================================================================
class TestProviderHealthMonitor:
    def test_register_provider(self):
        h = ProviderHealthMonitor()
        h.register_provider("imagen")
        m = h.get_metrics("imagen")
        assert m is not None
        assert m.provider == "imagen"

    def test_record_success(self):
        h = ProviderHealthMonitor()
        h.record_success("imagen", latency_ms=500, cost=0.04, quality=0.85)
        m = h.get_metrics("imagen")
        assert m.success_count == 1
        assert m.latency_ms == 500
        assert m.average_cost == 0.04

    def test_record_failure(self):
        h = ProviderHealthMonitor()
        h.record_failure("imagen")
        m = h.get_metrics("imagen")
        assert m.failure_count == 1

    def test_record_timeout(self):
        h = ProviderHealthMonitor()
        h.record_failure("veo", timeout=True)
        m = h.get_metrics("veo")
        assert m.timeout_count == 1

    def test_auto_disable_on_high_failure_rate(self):
        h = ProviderHealthMonitor()
        h.MAX_FAILURE_RATE = 0.3
        for _ in range(4):
            h.record_success("test_provider")
        for _ in range(3):
            h.record_failure("test_provider")
        m = h.get_metrics("test_provider")
        # 3 failures out of 7 = ~43% > 30%
        assert m.disabled is True

    def test_manual_disable_enable(self):
        h = ProviderHealthMonitor()
        h.disable("test", "Manual disable")
        assert h.is_disabled("test") is True
        h.enable("test")
        assert h.is_disabled("test") is False

    def test_record_quota(self):
        h = ProviderHealthMonitor()
        h.record_quota("imagen", 500)
        m = h.get_metrics("imagen")
        assert m.quota_remaining == 500

    def test_get_healthy_providers(self):
        h = ProviderHealthMonitor()
        h.register_provider("imagen")
        h.register_provider("veo")
        h.disable("veo", "Test")
        healthy = h.get_healthy_providers()
        assert "imagen" in healthy
        assert "veo" not in healthy

    def test_get_all_metrics(self):
        h = ProviderHealthMonitor()
        h.register_provider("imagen")
        all_metrics = h.get_all_metrics()
        assert "imagen" in all_metrics


# ===========================================================================
# Provider Selection Engine tests
# ===========================================================================
class TestProviderSelectionEngine:
    def test_register_and_select(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
            quality_score=0.85,
        )
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test")
        strategy = GenerationStrategy()
        result = engine.select(req, strategy)
        assert result is not None
        assert result[0] == "imagen"
        assert result[1] == "imagen-3"
        assert result[2] == 0.04

    def test_select_no_providers(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        req = GenerationRequest(category=AssetCategory.VIDEO, prompt="test")
        strategy = GenerationStrategy()
        result = engine.select(req, strategy)
        assert result is None

    def test_select_cheaper_provider(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(AssetCategory.IMAGE, "expensive", "model1", lambda req: 1.0, quality_score=0.9)
        engine.register_provider(AssetCategory.IMAGE, "cheap", "model2", lambda req: 0.01, quality_score=0.7)
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test")
        strategy = GenerationStrategy()
        result = engine.select(req, strategy)
        # Cheap provider should win due to cost weight
        assert result is not None
        assert result[0] == "cheap"

    def test_select_skips_unhealthy(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(AssetCategory.IMAGE, "bad", "model1", lambda req: 0.01, quality_score=0.9)
        engine.register_provider(AssetCategory.IMAGE, "good", "model2", lambda req: 0.02, quality_score=0.8)
        health.disable("bad", "Test")
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test")
        strategy = GenerationStrategy()
        result = engine.select(req, strategy)
        assert result is not None
        assert result[0] == "good"

    def test_get_fallback_chain(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(AssetCategory.IMAGE, "p1", "m1", lambda req: 0.01)
        engine.register_provider(AssetCategory.IMAGE, "p2", "m2", lambda req: 0.02)
        chain = engine.get_fallback_chain(AssetCategory.IMAGE)
        assert "p1" in chain
        assert "p2" in chain

    def test_list_providers(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(AssetCategory.IMAGE, "p1", "m1", lambda req: 0.01)
        engine.register_provider(AssetCategory.IMAGE, "p2", "m2", lambda req: 0.02)
        providers = engine.list_providers(AssetCategory.IMAGE)
        assert len(providers) == 2

    def test_preferred_provider(self):
        health = ProviderHealthMonitor()
        engine = ProviderSelectionEngine(health)
        engine.register_provider(AssetCategory.IMAGE, "p1", "m1", lambda req: 0.01, quality_score=0.9)
        engine.register_provider(AssetCategory.IMAGE, "p2", "m2", lambda req: 0.02, quality_score=0.8)
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test")
        strategy = GenerationStrategy(preferred_providers={"image": "p2"})
        result = engine.select(req, strategy)
        # p2 has preference bonus
        assert result is not None
        assert result[0] == "p2"


# ===========================================================================
# Budget Manager tests
# ===========================================================================
class TestBudgetManager:
    def test_set_and_check_budget(self):
        b = BudgetManager()
        b.set_project_budget("proj1", 10.0)
        status = b.get_budget_status("proj1")
        assert status.total_budget == 10.0
        assert status.remaining == 10.0
        assert status.exceeded is False

    def test_estimate_affordable(self):
        b = BudgetManager()
        b.set_project_budget("proj1", 10.0)
        req = GenerationRequest(project_id="proj1", category=AssetCategory.IMAGE)
        est = b.estimate(req, "imagen", "imagen-3", 0.04)
        assert est.affordable is True

    def test_estimate_not_affordable(self):
        b = BudgetManager()
        b.set_project_budget("proj1", 0.05)
        b.record_spend("proj1", "sc1", AssetCategory.IMAGE, 0.04)
        req = GenerationRequest(project_id="proj1", category=AssetCategory.IMAGE)
        est = b.estimate(req, "imagen", "imagen-3", 0.04)
        assert est.affordable is False

    def test_check_budget(self):
        b = BudgetManager()
        b.set_project_budget("proj1", 10.0)
        assert b.check_budget("proj1", 5.0) is True
        b.record_spend("proj1", "sc1", AssetCategory.IMAGE, 8.0)
        assert b.check_budget("proj1", 5.0) is False

    def test_record_spend(self):
        b = BudgetManager()
        b.set_project_budget("proj1", 10.0)
        b.record_spend("proj1", "sc1", AssetCategory.IMAGE, 0.05)
        b.record_spend("proj1", "sc1", AssetCategory.VOICE, 0.01)
        status = b.get_budget_status("proj1")
        assert abs(status.spent - 0.06) < 1e-9
        assert abs(status.per_scene_budget.get("sc1", 0) - 0.06) < 1e-9

    def test_recommend_downgrade_video_to_image(self):
        b = BudgetManager()
        req = GenerationRequest(category=AssetCategory.VIDEO)
        downgrade = b.recommend_downgrade(req)
        assert downgrade == AssetCategory.IMAGE

    def test_recommend_downgrade_image_none(self):
        b = BudgetManager()
        req = GenerationRequest(category=AssetCategory.IMAGE)
        downgrade = b.recommend_downgrade(req)
        assert downgrade is None

    def test_get_project_total(self):
        b = BudgetManager()
        b.record_spend("proj1", "sc1", AssetCategory.IMAGE, 0.05)
        assert b.get_project_total("proj1") == 0.05

    def test_get_scene_total(self):
        b = BudgetManager()
        b.record_spend("proj1", "sc1", AssetCategory.IMAGE, 0.05)
        b.record_spend("proj1", "sc1", AssetCategory.VOICE, 0.01)
        assert abs(b.get_scene_total("proj1", "sc1") - 0.06) < 1e-9

    def test_no_budget_allows_all(self):
        b = BudgetManager()
        assert b.check_budget("proj1", 1000.0) is True


# ===========================================================================
# Concurrency Manager tests
# ===========================================================================
class TestConcurrencyManager:
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        c = ConcurrencyManager(max_workers=2)
        acquired = await c.acquire("imagen", "proj1")
        assert acquired is True
        assert c.active_count == 1
        await c.release("imagen", "proj1")
        assert c.active_count == 0

    @pytest.mark.asyncio
    async def test_available_slots(self):
        c = ConcurrencyManager(max_workers=4)
        assert c.available_slots == 4
        await c.acquire("imagen", "proj1")
        assert c.available_slots == 3
        await c.release("imagen", "proj1")
        assert c.available_slots == 4

    def test_check_quotas_ok(self):
        c = ConcurrencyManager(daily_quota=100, monthly_quota=1000)
        allowed, _ = c.check_quotas()
        assert allowed is True

    def test_check_quotas_daily_exceeded(self):
        c = ConcurrencyManager(daily_quota=1, monthly_quota=1000)
        c.record_job()
        allowed, reason = c.check_quotas()
        assert allowed is False
        assert "Daily" in reason

    def test_check_quotas_monthly_exceeded(self):
        c = ConcurrencyManager(daily_quota=100, monthly_quota=1)
        c.record_job()
        allowed, reason = c.check_quotas()
        assert allowed is False
        assert "Monthly" in reason

    def test_set_provider_limit(self):
        c = ConcurrencyManager()
        c.set_provider_limit("imagen", 3)
        assert "imagen" in c._provider_limits

    def test_set_project_limit(self):
        c = ConcurrencyManager()
        c.set_project_limit("proj1", 5)
        assert "proj1" in c._project_limits

    def test_daily_count(self):
        c = ConcurrencyManager()
        c.record_job()
        c.record_job()
        assert c.get_daily_count() == 2

    def test_monthly_count(self):
        c = ConcurrencyManager()
        c.record_job()
        assert c.get_monthly_count() == 1


# ===========================================================================
# Cache Manager tests
# ===========================================================================
class TestCacheManager:
    def test_make_key(self):
        c = CacheManager()
        req = GenerationRequest(prompt="test")
        key = c.make_key(req, provider="imagen", model="imagen-3")
        assert key.prompt == "test"
        assert key.provider == "imagen"
        assert key.model == "imagen-3"

    def test_put_and_get(self):
        c = CacheManager()
        req = GenerationRequest(prompt="test")
        key = c.make_key(req, provider="imagen", model="imagen-3")
        asset = GeneratedAsset(provider="imagen", model="imagen-3")
        c.put(key, asset)
        result = c.get(key)
        assert result is not None
        assert result.provider == "imagen"

    def test_cache_miss(self):
        c = CacheManager()
        key = CacheKey(prompt="miss", provider="test", model="test")
        result = c.get(key)
        assert result is None
        assert c.misses == 1

    def test_cache_hit_rate(self):
        c = CacheManager()
        req = GenerationRequest(prompt="test")
        key = c.make_key(req, provider="imagen", model="imagen-3")
        c.put(key, GeneratedAsset())
        c.get(key)  # hit
        c.get(CacheKey(prompt="miss", provider="x", model="x"))  # miss
        assert c.hit_rate == 0.5

    def test_invalidate(self):
        c = CacheManager()
        req = GenerationRequest(prompt="test")
        key = c.make_key(req, provider="imagen", model="imagen-3")
        c.put(key, GeneratedAsset())
        assert c.invalidate(key) is True
        assert c.size == 0

    def test_clear(self):
        c = CacheManager()
        c.put(CacheKey(prompt="a", provider="x", model="y"), GeneratedAsset())
        c.clear()
        assert c.size == 0

    def test_eviction(self):
        c = CacheManager(max_entries=2)
        c.put(CacheKey(prompt="a", provider="x", model="y"), GeneratedAsset())
        c.put(CacheKey(prompt="b", provider="x", model="y"), GeneratedAsset())
        c.put(CacheKey(prompt="c", provider="x", model="y"), GeneratedAsset())
        assert c.size == 2  # oldest evicted


# ===========================================================================
# Validation Pipeline tests
# ===========================================================================
class TestValidationPipeline:
    @pytest.mark.asyncio
    async def test_valid_asset(self):
        v = ValidationPipeline()
        asset = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=1024,
            quality_score=0.8,
            storage_uri="local:///test.png",
        )
        report = await v.validate(asset)
        assert report.overall_valid is True

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self):
        v = ValidationPipeline()
        asset = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=0,
            quality_score=0.8,
            storage_uri="local:///test.png",
        )
        report = await v.validate(asset)
        assert report.overall_valid is False
        assert any(r.stage == ValidationStage.FILE_VALIDATION for r in report.results if not r.valid)

    @pytest.mark.asyncio
    async def test_low_quality_rejected(self):
        v = ValidationPipeline(min_quality_score=0.8)
        asset = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=1024,
            quality_score=0.3,
            storage_uri="local:///test.png",
        )
        report = await v.validate(asset)
        assert report.overall_valid is False
        assert any(r.stage == ValidationStage.QUALITY_EVALUATION for r in report.results if not r.valid)

    @pytest.mark.asyncio
    async def test_missing_storage_rejected(self):
        v = ValidationPipeline()
        asset = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=1024,
            quality_score=0.8,
        )
        report = await v.validate(asset)
        assert report.overall_valid is False

    @pytest.mark.asyncio
    async def test_duplicate_detected(self):
        v = ValidationPipeline()
        asset1 = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=1024,
            quality_score=0.8,
            content_hash="abc123",
            storage_uri="local:///test.png",
        )
        await v.validate(asset1)
        asset2 = GeneratedAsset(
            provider="imagen",
            model="imagen-3",
            file_size_bytes=1024,
            quality_score=0.8,
            content_hash="abc123",
            storage_uri="local:///test2.png",
        )
        report = await v.validate(asset2)
        assert any(r.stage == ValidationStage.DUPLICATE_DETECTION for r in report.results if not r.valid)

    @pytest.mark.asyncio
    async def test_placeholder_passes(self):
        v = ValidationPipeline()
        asset = GeneratedAsset(
            provider="test",
            model="test",
            file_size_bytes=1024,
            quality_score=0.8,
            metadata={"placeholder": True},
        )
        report = await v.validate(asset)
        # Placeholder should pass storage validation
        storage_result = [r for r in report.results if r.stage == ValidationStage.STORAGE_VALIDATION][0]
        assert storage_result.valid is True


# ===========================================================================
# Quality Engine tests
# ===========================================================================
class TestQualityEngine:
    def test_evaluate_image(self):
        q = QualityEngine()
        asset = GeneratedAsset(category=AssetCategory.IMAGE, quality_score=0.8)
        result = q.evaluate(asset, visual_quality=0.9, prompt_alignment=0.85)
        assert result.visual_quality == 0.9
        assert result.prompt_alignment == 0.85
        assert result.overall_score > 0

    def test_evaluate_voice(self):
        q = QualityEngine()
        asset = GeneratedAsset(category=AssetCategory.VOICE, quality_score=0.85)
        result = q.evaluate(asset, voice_quality=0.9)
        assert result.voice_quality == 0.9
        assert result.overall_score > 0

    def test_evaluate_subtitle(self):
        q = QualityEngine()
        asset = GeneratedAsset(category=AssetCategory.SUBTITLE, quality_score=0.95)
        result = q.evaluate(asset, subtitle_accuracy=0.98)
        assert result.subtitle_accuracy == 0.98
        assert result.overall_score > 0

    def test_evaluate_batch(self):
        q = QualityEngine()
        assets = [
            GeneratedAsset(category=AssetCategory.IMAGE, quality_score=0.8),
            GeneratedAsset(category=AssetCategory.VOICE, quality_score=0.85),
        ]
        results = q.evaluate_batch(assets)
        assert len(results) == 2

    def test_compute_project_quality(self):
        q = QualityEngine()
        results = [
            QualityResult(overall_score=0.8),
            QualityResult(overall_score=0.9),
        ]
        avg = q.compute_project_quality(results)
        assert abs(avg - 0.85) < 1e-9

    def test_compute_project_quality_empty(self):
        q = QualityEngine()
        assert q.compute_project_quality([]) == 0.0

    def test_default_scores_use_base(self):
        q = QualityEngine()
        asset = GeneratedAsset(category=AssetCategory.IMAGE, quality_score=0.75)
        result = q.evaluate(asset)
        assert result.visual_quality == 0.75
        assert result.overall_score > 0


# ===========================================================================
# Generation Executor tests
# ===========================================================================
class TestGenerationExecutor:
    @pytest.mark.asyncio
    async def test_execute_image_no_gateway(self):
        executor = GenerationExecutor()
        job = GenerationJob(
            request=GenerationRequest(
                category=AssetCategory.IMAGE,
                prompt="AI brain",
                scene_id="sc1",
                project_id="proj1",
            ),
            provider="imagen",
            model="imagen-3",
        )
        asset = await executor.execute(job)
        assert asset.category == AssetCategory.IMAGE
        assert asset.metadata.get("placeholder") is True
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_video_no_gateway(self):
        executor = GenerationExecutor()
        job = GenerationJob(
            request=GenerationRequest(
                category=AssetCategory.VIDEO,
                prompt="AI animation",
                scene_id="sc1",
                project_id="proj1",
            ),
            provider="veo",
            model="veo-3",
        )
        asset = await executor.execute(job)
        assert asset.category == AssetCategory.VIDEO
        assert asset.metadata.get("placeholder") is True

    @pytest.mark.asyncio
    async def test_execute_voice_no_gateway(self):
        executor = GenerationExecutor()
        job = GenerationJob(
            request=GenerationRequest(
                category=AssetCategory.VOICE,
                prompt="Welcome to AI",
                scene_id="sc1",
                project_id="proj1",
            ),
            provider="google_tts",
            model="en-US-Standard-A",
        )
        asset = await executor.execute(job)
        assert asset.category == AssetCategory.VOICE
        assert asset.metadata.get("placeholder") is True

    @pytest.mark.asyncio
    async def test_execute_subtitle(self):
        executor = GenerationExecutor()
        job = GenerationJob(
            request=GenerationRequest(
                category=AssetCategory.SUBTITLE,
                prompt="1\n00:00:00,000 --> 00:00:05,000\nWelcome\n",
                scene_id="sc1",
                project_id="proj1",
            ),
            provider="internal",
            model="subtitle_generator",
        )
        asset = await executor.execute(job)
        assert asset.category == AssetCategory.SUBTITLE
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        cache = CacheManager()
        executor = GenerationExecutor(cache=cache)
        req = GenerationRequest(
            category=AssetCategory.IMAGE,
            prompt="AI brain",
            scene_id="sc1",
            project_id="proj1",
            provider="imagen",
            model="imagen-3",
        )
        job = GenerationJob(request=req, provider="imagen", model="imagen-3")
        asset1 = await executor.execute(job)
        # Second call should hit cache
        job2 = GenerationJob(request=req, provider="imagen", model="imagen-3")
        asset2 = await executor.execute(job2)
        assert asset2.cached is True


# ===========================================================================
# Orchestrator tests
# ===========================================================================
class TestGenerationOrchestrator:
    @pytest.mark.asyncio
    async def test_submit_and_process(self):
        orch = GenerationOrchestrator()
        # Register a provider
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
            quality_score=0.85,
        )
        req = GenerationRequest(
            category=AssetCategory.IMAGE,
            prompt="AI brain",
            scene_id="sc1",
            project_id="proj1",
        )
        job = await orch.submit(req)
        assert job.provider == "imagen"
        assert job.estimated_cost == 0.04

        # Process queue
        assets = await orch.process_queue()
        assert len(assets) == 1
        assert assets[0].category == AssetCategory.IMAGE

    @pytest.mark.asyncio
    async def test_submit_batch(self):
        orch = GenerationOrchestrator()
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
        )
        requests = [
            GenerationRequest(category=AssetCategory.IMAGE, prompt="test1", scene_id="sc1", project_id="proj1"),
            GenerationRequest(category=AssetCategory.IMAGE, prompt="test2", scene_id="sc2", project_id="proj1"),
        ]
        jobs = await orch.submit_batch(requests)
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_cancel_job(self):
        orch = GenerationOrchestrator()
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
        )
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test", scene_id="sc1", project_id="proj1")
        job = await orch.submit(req)
        await orch.cancel_job(job.id)
        assert orch.get_job(job.id).status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_assets_for_scene(self):
        orch = GenerationOrchestrator()
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
        )
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test", scene_id="sc1", project_id="proj1")
        await orch.submit(req)
        await orch.process_queue()
        assets = orch.get_assets_for_scene("sc1")
        assert len(assets) == 1

    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        orch = GenerationOrchestrator()
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
        )
        req = GenerationRequest(category=AssetCategory.IMAGE, prompt="test", scene_id="sc1", project_id="proj1")
        await orch.submit(req)
        p = orch.progress
        assert p.total_jobs == 1
        await orch.process_queue()
        p = orch.progress
        assert p.completed == 1


# ===========================================================================
# Asset Manifest Builder tests
# ===========================================================================
class TestAssetManifestBuilder:
    def test_build_empty(self):
        builder = AssetManifestBuilder()
        manifest = builder.build([], project_id="proj1")
        assert manifest.project_id == "proj1"
        assert manifest.scene_count == 0
        assert manifest.total_cost == 0.0

    def test_build_with_assets(self):
        builder = AssetManifestBuilder()
        assets = [
            GeneratedAsset(scene_id="sc1", category=AssetCategory.IMAGE, cost_usd=0.04, storage_uri="local:///img1.png"),
            GeneratedAsset(scene_id="sc1", category=AssetCategory.VOICE, cost_usd=0.01, storage_uri="local:///voice1.mp3"),
            GeneratedAsset(scene_id="sc2", category=AssetCategory.IMAGE, cost_usd=0.04, storage_uri="local:///img2.png"),
        ]
        manifest = builder.build(assets, project_id="proj1", scene_ids=["sc1", "sc2"])
        assert manifest.scene_count == 2
        assert abs(manifest.total_cost - 0.09) < 1e-9
        assert manifest.total_assets == 3
        sc1 = manifest.scene_manifests[0]
        assert sc1.image is not None
        assert sc1.voice is not None
        assert sc1.video is None

    def test_build_with_durations(self):
        builder = AssetManifestBuilder()
        assets = [
            GeneratedAsset(scene_id="sc1", category=AssetCategory.IMAGE, cost_usd=0.04, storage_uri="local:///img1.png"),
        ]
        manifest = builder.build(
            assets,
            project_id="proj1",
            scene_ids=["sc1"],
            scene_durations={"sc1": 30.0},
        )
        assert manifest.total_duration_seconds == 30.0
        assert manifest.scene_manifests[0].estimated_render_time_seconds == 15.0  # 30 * 0.5

    def test_is_complete(self):
        builder = AssetManifestBuilder()
        assets = [
            GeneratedAsset(scene_id="sc1", category=AssetCategory.IMAGE, cost_usd=0.04, storage_uri="local:///img1.png"),
        ]
        manifest = builder.build(assets, project_id="proj1", scene_ids=["sc1"])
        assert manifest.is_complete is True

    def test_not_complete_missing_storage(self):
        builder = AssetManifestBuilder()
        assets = [
            GeneratedAsset(scene_id="sc1", category=AssetCategory.IMAGE, cost_usd=0.04),
        ]
        manifest = builder.build(assets, project_id="proj1", scene_ids=["sc1"])
        assert manifest.is_complete is False


# ===========================================================================
# Subtitle Generator tests
# ===========================================================================
class TestSubtitleGenerator:
    def test_generate_srt(self):
        gen = SubtitleGenerator()
        srt = gen.generate_srt("Hello world. This is a test.", scene_id="sc1")
        assert "1" in srt
        assert "-->" in srt
        assert "Hello world." in srt
        assert "This is a test." in srt

    def test_generate_vtt(self):
        gen = SubtitleGenerator()
        vtt = gen.generate_vtt("Hello world. This is a test.", scene_id="sc1")
        assert vtt.startswith("WEBVTT")
        assert "-->" in vtt
        assert "Hello world." in vtt

    def test_srt_time_format(self):
        gen = SubtitleGenerator()
        assert gen._format_srt_time(0.0) == "00:00:00,000"
        assert gen._format_srt_time(5.5) == "00:00:05,500"
        assert gen._format_srt_time(65.0) == "00:01:05,000"

    def test_vtt_time_format(self):
        gen = SubtitleGenerator()
        assert gen._format_vtt_time(0.0) == "00:00:00.000"
        assert gen._format_vtt_time(5.5) == "00:00:05.500"

    def test_create_request(self):
        gen = SubtitleGenerator()
        req = gen.create_request("Hello world.", scene_id="sc1", project_id="proj1")
        assert req.category == AssetCategory.SUBTITLE
        assert req.scene_id == "sc1"

    def test_create_asset(self):
        gen = SubtitleGenerator()
        asset = gen.create_asset("Hello world.", scene_id="sc1")
        assert asset.category == AssetCategory.SUBTITLE
        assert asset.quality_score == 0.95

    def test_split_sentences(self):
        gen = SubtitleGenerator()
        sentences = gen._split_sentences("Hello world. This is a test! Really?")
        assert len(sentences) == 3

    def test_wrap_text(self):
        gen = SubtitleGenerator()
        wrapped = gen._wrap_text("This is a very long sentence that should be wrapped", 20)
        lines = wrapped.split("\n")
        assert all(len(line) <= 20 or len(line.split()) == 1 for line in lines)


# ===========================================================================
# Thumbnail Generator tests
# ===========================================================================
class TestThumbnailGenerator:
    def test_generate_prompt(self):
        gen = ThumbnailGenerator()
        prompt = gen.generate_prompt("Understanding AI")
        assert "no text" in prompt.lower()
        assert "no words" in prompt.lower()
        assert "Understanding AI" in prompt
        assert "16:9" in prompt

    def test_generate_variations(self):
        gen = ThumbnailGenerator()
        variations = gen.generate_variations("Understanding AI", count=3)
        assert len(variations) == 3
        assert all("no text" in v.lower() for v in variations)

    def test_clickability_score(self):
        gen = ThumbnailGenerator()
        score = gen.compute_clickability_score("Test", has_face=True, has_contrast=True, has_bold_colors=True, emotion_appeal=0.9)
        assert score > 0.9
        assert score <= 1.0

    def test_clickability_score_minimal(self):
        gen = ThumbnailGenerator()
        score = gen.compute_clickability_score("Test", has_face=False, has_contrast=False, has_bold_colors=False, emotion_appeal=0.0)
        assert score == 0.0

    def test_create_request(self):
        gen = ThumbnailGenerator()
        req = gen.create_request("Understanding AI", scene_id="sc1", project_id="proj1")
        assert req.category == AssetCategory.THUMBNAIL
        assert req.resolution == "1280x720"
        assert req.metadata.get("no_text") is True

    def test_create_asset(self):
        gen = ThumbnailGenerator()
        asset = gen.create_asset("Understanding AI", scene_id="sc1")
        assert asset.category == AssetCategory.THUMBNAIL
        assert "clickability_score" in asset.metadata


# ===========================================================================
# Events tests
# ===========================================================================
class TestGenerationEvents:
    @pytest.mark.asyncio
    async def test_emit_generation_started(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_generation_started(uuid4(), "sc1", "image")

    @pytest.mark.asyncio
    async def test_emit_generation_completed(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_generation_completed(uuid4(), uuid4(), 0.04)

    @pytest.mark.asyncio
    async def test_emit_generation_failed(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_generation_failed(uuid4(), "Test error")

    @pytest.mark.asyncio
    async def test_emit_retry_triggered(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_retry_triggered(uuid4(), 1)

    @pytest.mark.asyncio
    async def test_emit_provider_changed(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_provider_changed(uuid4(), "imagen", "veo")

    @pytest.mark.asyncio
    async def test_emit_budget_exceeded(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_budget_exceeded("proj1", 10.0, 5.0)

    @pytest.mark.asyncio
    async def test_emit_asset_stored(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_asset_stored(uuid4(), "local:///test.png")

    @pytest.mark.asyncio
    async def test_emit_validation_failed(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_validation_failed(uuid4(), "file_validation", "Empty file")

    @pytest.mark.asyncio
    async def test_emit_manifest_completed(self):
        emitter = GenerationEventEmitter(event_bus=None)
        await emitter.emit_manifest_completed(uuid4(), 10, 0.50)

    def test_event_constants(self):
        assert GenerationEvents.GENERATION_STARTED == "GenerationStarted"
        assert GenerationEvents.GENERATION_COMPLETED == "GenerationCompleted"
        assert GenerationEvents.GENERATION_FAILED == "GenerationFailed"
        assert GenerationEvents.RETRY_TRIGGERED == "RetryTriggered"
        assert GenerationEvents.PROVIDER_CHANGED == "ProviderChanged"
        assert GenerationEvents.BUDGET_EXCEEDED == "BudgetExceeded"
        assert GenerationEvents.ASSET_STORED == "AssetStored"
        assert GenerationEvents.VALIDATION_FAILED == "ValidationFailed"
        assert GenerationEvents.MANIFEST_COMPLETED == "ManifestCompleted"


# ===========================================================================
# Integration test — full generation pipeline
# ===========================================================================
class TestGenerationPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the full generation pipeline from request to manifest."""
        orch = GenerationOrchestrator()

        # Register providers
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
            quality_score=0.85,
        )
        orch.provider_selection.register_provider(
            AssetCategory.VOICE,
            "google_tts",
            "en-US-Standard-A",
            lambda req: 0.01,
            quality_score=0.9,
        )

        # Set budget
        orch.budget_manager.set_project_budget("proj1", 10.0)

        # Submit requests
        requests = [
            GenerationRequest(category=AssetCategory.IMAGE, prompt="AI brain", scene_id="sc1", project_id="proj1"),
            GenerationRequest(category=AssetCategory.IMAGE, prompt="Neural network", scene_id="sc2", project_id="proj1"),
            GenerationRequest(category=AssetCategory.VOICE, prompt="Welcome to AI", scene_id="sc1", project_id="proj1"),
        ]
        jobs = await orch.submit_batch(requests)
        assert len(jobs) == 3

        # Process queue
        assets = await orch.process_queue()
        assert len(assets) == 3

        # Check all assets are valid
        for asset in assets:
            assert asset.quality_score > 0

        # Build manifest
        builder = AssetManifestBuilder()
        manifest = builder.build(assets, project_id="proj1", scene_ids=["sc1", "sc2"])
        assert manifest.scene_count == 2
        assert manifest.total_assets == 3
        assert manifest.is_complete is True

        # Check budget was tracked
        status = orch.budget_manager.get_budget_status("proj1")
        assert status.spent > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_budget_downgrade(self):
        """Test that video is downgraded to image when budget is tight."""
        orch = GenerationOrchestrator()

        orch.provider_selection.register_provider(
            AssetCategory.VIDEO,
            "veo",
            "veo-3",
            lambda req: 5.0,
            quality_score=0.85,
        )
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
            quality_score=0.85,
        )

        # Set very low budget
        orch.budget_manager.set_project_budget("proj1", 0.10)
        orch.budget_manager.record_spend("proj1", "sc1", AssetCategory.IMAGE, 0.08)

        req = GenerationRequest(
            category=AssetCategory.VIDEO,
            prompt="AI animation",
            scene_id="sc1",
            project_id="proj1",
        )
        job = await orch.submit(req)
        # Should have been downgraded to image
        assert job.request.category == AssetCategory.IMAGE

    @pytest.mark.asyncio
    async def test_pipeline_with_caching(self):
        """Test that identical requests are cached."""
        orch = GenerationOrchestrator()
        orch.provider_selection.register_provider(
            AssetCategory.IMAGE,
            "imagen",
            "imagen-3",
            lambda req: 0.04,
        )

        req = GenerationRequest(
            category=AssetCategory.IMAGE,
            prompt="AI brain",
            scene_id="sc1",
            project_id="proj1",
            provider="imagen",
            model="imagen-3",
        )

        # First request
        await orch.submit(req)
        assets1 = await orch.process_queue()
        assert len(assets1) == 1
        assert assets1[0].cached is False

        # Second identical request should be cached
        await orch.submit(req)
        assets2 = await orch.process_queue()
        assert len(assets2) == 1
        assert assets2[0].cached is True
