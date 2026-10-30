"""Comprehensive tests for the Publishing & Distribution Platform (Phase 11).

Covers:
- Schema tests (all models, enums, defaults, computed properties)
- Authentication manager tests
- Metadata engine tests
- Thumbnail manager tests
- Publishing validator tests
- YouTube publisher tests
- Publishing planner tests
- Publishing strategy engine tests
- Publishing queue tests
- Scheduling engine tests
- Progress tracker tests
- Events tests
- Integration test (full pipeline)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.publishing.schema import (
    AuthCredential,
    AuthMethod,
    FailoverStrategy,
    PlatformConfig,
    PlatformRequirements,
    PublishingJob,
    PublishingJobStatus,
    PublishingMetadata,
    PublishingMetrics,
    PublishingMode,
    PublishingPlatform,
    PublishingPlan,
    PublishingPriority,
    PublishingProgress,
    PublishingReport,
    PublishingStrategy,
    PublishingTask,
    RetryStrategy,
    ScheduleConfig,
    ThumbnailFormat,
    ThumbnailSpec,
    YouTubeCategory,
    YouTubeLicense,
)
from src.publishing.events import PublishingEventEmitter, PublishingEvents
from src.publishing.publisher import Publisher
from src.publishing.auth import AuthenticationManager
from src.publishing.metadata import MetadataEngine
from src.publishing.thumbnail import ThumbnailManager
from src.publishing.validator import PublishingValidator
from src.publishing.youtube import YouTubePublisher
from src.publishing.planner import PublishingPlanner
from src.publishing.strategy import PublishingStrategyEngine
from src.publishing.queue import PublishingQueue
from src.publishing.scheduler import SchedulingEngine
from src.publishing.progress import ProgressTracker


def run_async(coro):
    """Run an async coroutine synchronously (Python 3.12+ compatible)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("Cannot run in a running event loop")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ===========================================================================
# Schema Tests
# ===========================================================================
class TestSchema:
    def test_publishing_platform_values(self):
        assert PublishingPlatform.YOUTUBE == "youtube"
        assert PublishingPlatform.LINKEDIN == "linkedin"
        assert PublishingPlatform.TIKTOK == "tiktok"
        assert PublishingPlatform.CUSTOM == "custom"

    def test_publishing_mode_values(self):
        assert PublishingMode.IMMEDIATE == "immediate"
        assert PublishingMode.SCHEDULED == "scheduled"
        assert PublishingMode.DRAFT == "draft"
        assert PublishingMode.MULTI_PLATFORM == "multi_platform"

    def test_publishing_job_status_values(self):
        assert PublishingJobStatus.QUEUED == "queued"
        assert PublishingJobStatus.UPLOADING == "uploading"
        assert PublishingJobStatus.COMPLETED == "completed"
        assert PublishingJobStatus.FAILED == "failed"
        assert PublishingJobStatus.CANCELLED == "cancelled"

    def test_publishing_priority_ordering(self):
        assert PublishingPriority.CRITICAL < PublishingPriority.HIGH
        assert PublishingPriority.HIGH < PublishingPriority.NORMAL
        assert PublishingPriority.NORMAL < PublishingPriority.LOW
        assert PublishingPriority.LOW < PublishingPriority.BACKGROUND

    def test_auth_method_values(self):
        assert AuthMethod.OAUTH2 == "oauth2"
        assert AuthMethod.API_KEY == "api_key"
        assert AuthMethod.REFRESH_TOKEN == "refresh_token"

    def test_youtube_category_values(self):
        assert YouTubeCategory.EDUCATION == "27"
        assert YouTubeCategory.MUSIC == "10"
        assert YouTubeCategory.SCIENCE_TECH == "28"

    def test_youtube_license_values(self):
        assert YouTubeLicense.YOUTUBE == "youtube"
        assert YouTubeLicense.CREATIVE_COMMON == "creativeCommon"

    def test_thumbnail_format_values(self):
        assert ThumbnailFormat.PNG == "png"
        assert ThumbnailFormat.JPG == "jpg"

    def test_retry_strategy_values(self):
        assert RetryStrategy.NONE == "none"
        assert RetryStrategy.EXPONENTIAL_BACKOFF == "exponential_backoff"

    def test_failover_strategy_values(self):
        assert FailoverStrategy.NONE == "none"
        assert FailoverStrategy.SKIP_FAILED == "skip_failed"
        assert FailoverStrategy.ABORT_ALL == "abort_all"

    def test_publishing_metadata_defaults(self):
        meta = PublishingMetadata()
        assert meta.title == ""
        assert meta.tags == []
        assert meta.language == "en"
        assert meta.privacy_status == "private"
        assert meta.license == "youtube"
        assert meta.made_for_kids is False

    def test_publishing_metadata_computed(self):
        meta = PublishingMetadata(title="Test Title", description="Desc", tags=["a", "b"])
        assert meta.title_length == 10
        assert meta.description_length == 4
        assert meta.tag_count == 2

    def test_auth_credential_defaults(self):
        cred = AuthCredential()
        assert cred.is_expired is False  # No expiry set
        assert cred.is_valid is False  # No access token

    def test_auth_credential_valid(self):
        cred = AuthCredential(
            access_token="token123",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert cred.is_valid is True
        assert cred.is_expired is False

    def test_auth_credential_expired(self):
        cred = AuthCredential(
            access_token="token123",
            token_expiry=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert cred.is_expired is True
        assert cred.is_valid is False

    def test_thumbnail_spec_defaults(self):
        spec = ThumbnailSpec()
        assert spec.width == 1280
        assert spec.height == 720
        assert spec.format == ThumbnailFormat.JPG
        assert spec.aspect_ratio == "1280:720"

    def test_publishing_task_defaults(self):
        task = PublishingTask()
        assert task.status == PublishingJobStatus.QUEUED
        assert task.priority == PublishingPriority.NORMAL
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_publishing_task_is_terminal(self):
        task = PublishingTask(status=PublishingJobStatus.COMPLETED)
        assert task.is_terminal is True
        task2 = PublishingTask(status=PublishingJobStatus.QUEUED)
        assert task2.is_terminal is False

    def test_publishing_task_execution_time(self):
        task = PublishingTask()
        assert task.execution_time_seconds == 0.0
        task.started_at = datetime.now(timezone.utc)
        assert task.execution_time_seconds > 0.0

    def test_publishing_plan_defaults(self):
        plan = PublishingPlan()
        assert plan.task_count == 0
        assert plan.platform_count == 0
        assert plan.platforms == []

    def test_publishing_plan_platforms(self):
        t1 = PublishingTask(platform=PublishingPlatform.YOUTUBE)
        t2 = PublishingTask(platform=PublishingPlatform.LINKEDIN)
        plan = PublishingPlan(tasks=[t1, t2])
        assert len(plan.platforms) == 2
        assert PublishingPlatform.YOUTUBE in plan.platforms

    def test_publishing_report_defaults(self):
        report = PublishingReport()
        assert report.is_successful is True  # No errors, status COMPLETED

    def test_publishing_report_failed(self):
        report = PublishingReport(
            status=PublishingJobStatus.FAILED,
            errors=["Upload failed"],
        )
        assert report.is_successful is False

    def test_publishing_job_defaults(self):
        job = PublishingJob()
        assert job.status == PublishingJobStatus.QUEUED
        assert job.is_terminal is False

    def test_publishing_job_is_terminal(self):
        job = PublishingJob(status=PublishingJobStatus.COMPLETED)
        assert job.is_terminal is True
        job2 = PublishingJob(status=PublishingJobStatus.DRAFT_SAVED)
        assert job2.is_terminal is True

    def test_schedule_config_immediate(self):
        config = ScheduleConfig(mode=PublishingMode.IMMEDIATE)
        assert config.is_immediate is True
        assert config.is_scheduled is False

    def test_schedule_config_scheduled(self):
        config = ScheduleConfig(
            mode=PublishingMode.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert config.is_scheduled is True
        assert config.is_immediate is False

    def test_platform_requirements_defaults(self):
        req = PlatformRequirements()
        assert req.max_title_length == 100
        assert req.requires_auth is True

    def test_publishing_strategy_defaults(self):
        strategy = PublishingStrategy()
        assert strategy.mode == PublishingMode.IMMEDIATE
        assert PublishingPlatform.YOUTUBE in strategy.platforms
        assert strategy.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF


# ===========================================================================
# Authentication Manager Tests
# ===========================================================================
class TestAuthenticationManager:
    def test_authenticate_oauth2(self):
        mgr = AuthenticationManager()
        config = PlatformConfig(
            client_id="test_client",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/youtube"],
        )
        cred = run_async(mgr.authenticate(PublishingPlatform.YOUTUBE, config))
        assert cred.access_token != ""
        assert cred.refresh_token != ""
        assert cred.auth_method == AuthMethod.OAUTH2
        assert cred.is_valid is True

    def test_authenticate_api_key(self):
        mgr = AuthenticationManager()
        config = PlatformConfig(api_key="test_api_key")
        cred = run_async(mgr.authenticate(PublishingPlatform.TWITTER, config))
        assert cred.auth_method == AuthMethod.API_KEY

    def test_authenticate_missing_credentials(self):
        mgr = AuthenticationManager()
        config = PlatformConfig()
        with pytest.raises(ValueError):
            run_async(mgr.authenticate(PublishingPlatform.YOUTUBE, config))

    def test_store_and_get_credential(self):
        mgr = AuthenticationManager()
        cred = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            access_token="token123",
        )
        run_async(mgr.store_credential(cred))
        retrieved = run_async(mgr.get_credential(PublishingPlatform.YOUTUBE))
        assert retrieved is not None
        assert retrieved.access_token == "token123"

    def test_get_credential_not_found(self):
        mgr = AuthenticationManager()
        result = run_async(mgr.get_credential(PublishingPlatform.LINKEDIN))
        assert result is None

    def test_delete_credential(self):
        mgr = AuthenticationManager()
        cred = AuthCredential(platform=PublishingPlatform.YOUTUBE, access_token="token")
        run_async(mgr.store_credential(cred))
        assert run_async(mgr.delete_credential(PublishingPlatform.YOUTUBE)) is True
        assert run_async(mgr.get_credential(PublishingPlatform.YOUTUBE)) is None

    def test_delete_credential_not_found(self):
        mgr = AuthenticationManager()
        assert run_async(mgr.delete_credential(PublishingPlatform.LINKEDIN)) is False

    def test_validate_credential(self):
        mgr = AuthenticationManager()
        cred = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            access_token="token",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        run_async(mgr.store_credential(cred))
        assert run_async(mgr.validate_credential(PublishingPlatform.YOUTUBE)) is True

    def test_validate_credential_expired(self):
        mgr = AuthenticationManager()
        cred = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            access_token="token",
            token_expiry=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        run_async(mgr.store_credential(cred))
        assert run_async(mgr.validate_credential(PublishingPlatform.YOUTUBE)) is False

    def test_refresh_credential(self):
        mgr = AuthenticationManager()
        cred = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            access_token="old_token",
            refresh_token="refresh_token",
            token_expiry=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        run_async(mgr.store_credential(cred))
        config = PlatformConfig(refresh_token="refresh_token")
        refreshed = run_async(mgr.refresh_credential(PublishingPlatform.YOUTUBE, config))
        assert refreshed is not None
        assert refreshed.is_expired is False

    def test_refresh_credential_not_found(self):
        mgr = AuthenticationManager()
        config = PlatformConfig()
        result = run_async(mgr.refresh_credential(PublishingPlatform.LINKEDIN, config))
        assert result is None

    def test_credential_count(self):
        mgr = AuthenticationManager()
        run_async(mgr.store_credential(AuthCredential(platform=PublishingPlatform.YOUTUBE, access_token="t1")))
        run_async(mgr.store_credential(AuthCredential(platform=PublishingPlatform.LINKEDIN, access_token="t2")))
        assert mgr.credential_count == 2

    def test_list_platforms(self):
        mgr = AuthenticationManager()
        run_async(mgr.store_credential(AuthCredential(platform=PublishingPlatform.YOUTUBE, access_token="t1")))
        run_async(mgr.store_credential(AuthCredential(platform=PublishingPlatform.LINKEDIN, access_token="t2")))
        platforms = mgr.list_platforms()
        assert PublishingPlatform.YOUTUBE in platforms
        assert PublishingPlatform.LINKEDIN in platforms


# ===========================================================================
# Metadata Engine Tests
# ===========================================================================
class TestMetadataEngine:
    def test_generate_metadata_basic(self):
        engine = MetadataEngine()
        meta = engine.generate_metadata(
            title="Test Video",
            description="A test description",
            keywords=["python", "tutorial", "programming"],
            platform=PublishingPlatform.YOUTUBE,
        )
        assert meta.title == "Test Video"
        assert meta.description == "A test description"
        assert "python" in meta.tags
        assert "tutorial" in meta.tags

    def test_generate_metadata_truncates_title(self):
        engine = MetadataEngine()
        long_title = "A" * 200
        meta = engine.generate_metadata(title=long_title, platform=PublishingPlatform.YOUTUBE)
        assert len(meta.title) <= 100

    def test_generate_metadata_truncates_description(self):
        engine = MetadataEngine()
        long_desc = "A" * 6000
        meta = engine.generate_metadata(description=long_desc, platform=PublishingPlatform.YOUTUBE)
        assert len(meta.description) <= 5000

    def test_generate_metadata_hashtags_youtube(self):
        engine = MetadataEngine()
        meta = engine.generate_metadata(
            keywords=["python", "tutorial"],
            platform=PublishingPlatform.YOUTUBE,
        )
        # YouTube doesn't use hashtags
        assert meta.hashtags == []

    def test_generate_metadata_hashtags_instagram(self):
        engine = MetadataEngine()
        meta = engine.generate_metadata(
            keywords=["python", "tutorial"],
            platform=PublishingPlatform.INSTAGRAM,
        )
        assert len(meta.hashtags) > 0
        assert any("python" in h for h in meta.hashtags)

    def test_generate_metadata_seo(self):
        engine = MetadataEngine()
        meta = engine.generate_metadata(
            title="Test",
            description="Desc",
            keywords=["kw1"],
            platform=PublishingPlatform.YOUTUBE,
        )
        assert "og:title" in meta.seo_metadata
        assert "twitter:card" in meta.seo_metadata

    def test_generate_metadata_platform_specific(self):
        engine = MetadataEngine()
        meta = engine.generate_metadata(platform=PublishingPlatform.YOUTUBE)
        assert "category" in meta.platform_metadata
        assert "license" in meta.platform_metadata

    def test_validate_metadata_valid(self):
        engine = MetadataEngine()
        meta = PublishingMetadata(title="Test", description="Desc", tags=["a"])
        errors = engine.validate_metadata(meta, PublishingPlatform.YOUTUBE)
        assert errors == []

    def test_validate_metadata_no_title(self):
        engine = MetadataEngine()
        meta = PublishingMetadata(title="")
        errors = engine.validate_metadata(meta, PublishingPlatform.YOUTUBE)
        assert any("Title is required" in e for e in errors)

    def test_validate_metadata_title_too_long(self):
        engine = MetadataEngine()
        meta = PublishingMetadata(title="A" * 200)
        errors = engine.validate_metadata(meta, PublishingPlatform.YOUTUBE)
        assert any("Title exceeds" in e for e in errors)

    def test_validate_metadata_too_many_tags(self):
        engine = MetadataEngine()
        meta = PublishingMetadata(title="Test", tags=["tag"] * 600)
        errors = engine.validate_metadata(meta, PublishingPlatform.YOUTUBE)
        assert any("Too many tags" in e for e in errors)

    def test_get_title_limit(self):
        engine = MetadataEngine()
        assert engine.get_title_limit(PublishingPlatform.YOUTUBE) == 100
        assert engine.get_title_limit(PublishingPlatform.MEDIUM) == 200

    def test_get_description_limit(self):
        engine = MetadataEngine()
        assert engine.get_description_limit(PublishingPlatform.YOUTUBE) == 5000


# ===========================================================================
# Thumbnail Manager Tests
# ===========================================================================
class TestThumbnailManager:
    def test_get_spec_youtube(self):
        mgr = ThumbnailManager()
        spec = mgr.get_spec(PublishingPlatform.YOUTUBE)
        assert spec.width == 1280
        assert spec.height == 720
        assert spec.format == ThumbnailFormat.JPG

    def test_get_spec_instagram(self):
        mgr = ThumbnailManager()
        spec = mgr.get_spec(PublishingPlatform.INSTAGRAM)
        assert spec.width == 1080
        assert spec.height == 1080

    def test_get_spec_tiktok(self):
        mgr = ThumbnailManager()
        spec = mgr.get_spec(PublishingPlatform.TIKTOK)
        assert spec.height == 1920

    def test_validate_thumbnail_empty_path(self):
        mgr = ThumbnailManager()
        errors = mgr.validate_thumbnail("", PublishingPlatform.YOUTUBE)
        assert any("empty" in e for e in errors)

    def test_validate_thumbnail_not_found(self):
        mgr = ThumbnailManager()
        errors = mgr.validate_thumbnail("/nonexistent/thumb.jpg", PublishingPlatform.YOUTUBE)
        assert any("not found" in e for e in errors)

    def test_validate_thumbnail_valid(self, tmp_path):
        mgr = ThumbnailManager()
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"x" * 1024)
        errors = mgr.validate_thumbnail(str(thumb), PublishingPlatform.YOUTUBE)
        assert errors == []

    def test_validate_thumbnail_too_large(self, tmp_path):
        mgr = ThumbnailManager()
        thumb = tmp_path / "large.jpg"
        thumb.write_bytes(b"x" * (3 * 1024 * 1024))  # 3MB > 2MB limit
        errors = mgr.validate_thumbnail(str(thumb), PublishingPlatform.YOUTUBE)
        assert any("exceeds limit" in e for e in errors)

    def test_generate_variant_path(self):
        mgr = ThumbnailManager()
        path = mgr.generate_variant_path("/tmp/thumb.jpg", PublishingPlatform.YOUTUBE)
        assert "youtube" in path
        assert path.endswith(".jpg")

    def test_get_thumbnail_metadata(self, tmp_path):
        mgr = ThumbnailManager()
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"x" * 1024)
        meta = mgr.get_thumbnail_metadata(str(thumb), PublishingPlatform.YOUTUBE)
        assert meta["platform"] == "youtube"
        assert meta["width"] == 1280
        assert meta["file_size_bytes"] == 1024

    def test_needs_resize(self, tmp_path):
        mgr = ThumbnailManager()
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"x" * 1024)
        assert mgr.needs_resize(str(thumb), PublishingPlatform.YOUTUBE) is True

    def test_list_platform_specs(self):
        mgr = ThumbnailManager()
        specs = mgr.list_platform_specs()
        assert "youtube" in specs
        assert "instagram" in specs
        assert specs["youtube"]["width"] == 1280


# ===========================================================================
# Publishing Validator Tests
# ===========================================================================
class TestPublishingValidator:
    def test_validate_task_valid(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test Video"),
        )
        errors, warnings = validator.validate_task(task)
        assert errors == []

    def test_validate_task_no_video(self):
        validator = PublishingValidator()
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("Video path is empty" in e for e in errors)

    def test_validate_task_video_not_found(self):
        validator = PublishingValidator()
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path="/nonexistent/video.mp4",
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("not found" in e for e in errors)

    def test_validate_task_no_title(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title=""),
        )
        errors, _ = validator.validate_task(task)
        assert any("Title is required" in e for e in errors)

    def test_validate_task_title_too_long(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="A" * 200),
        )
        errors, _ = validator.validate_task(task)
        assert any("Title exceeds" in e for e in errors)

    def test_validate_task_unsupported_format(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.xyz"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("Unsupported video format" in e for e in errors)

    def test_validate_task_scheduled_no_time(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            mode=PublishingMode.SCHEDULED,
            scheduled_at=None,
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("scheduled_at" in e for e in errors)

    def test_validate_task_scheduled_past_time(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            mode=PublishingMode.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("future" in e for e in errors)

    def test_validate_task_thumbnail_required(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.LINKEDIN,
            video_path=str(video),
            thumbnail_path="",
            metadata=PublishingMetadata(title="Test"),
        )
        errors, _ = validator.validate_task(task)
        assert any("Thumbnail is required" in e for e in errors)

    def test_validate_task_auth_warning(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test"),
        )
        _, warnings = validator.validate_task(task)
        assert any("Authentication" in w for w in warnings)

    def test_get_requirements(self):
        validator = PublishingValidator()
        req = validator.get_requirements(PublishingPlatform.YOUTUBE)
        assert req.max_title_length == 100
        assert req.max_description_length == 5000

    def test_validate_project_package_valid(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "final_video_path": str(video),
            "project_id": "proj1",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {},
        })()
        errors = validator.validate_project_package(package)
        assert errors == []

    def test_validate_project_package_no_video(self):
        validator = PublishingValidator()
        package = type("MockPackage", (), {
            "final_video_path": "",
            "project_id": "proj1",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {},
        })()
        errors = validator.validate_project_package(package)
        assert any("no final video" in e for e in errors)

    def test_validate_project_package_quality_failed(self, tmp_path):
        validator = PublishingValidator()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "final_video_path": str(video),
            "project_id": "proj1",
            "quality_report": type("MockReport", (), {"overall_pass": False})(),
            "metadata": {},
        })()
        errors = validator.validate_project_package(package)
        assert any("quality" in e for e in errors)


# ===========================================================================
# YouTube Publisher Tests
# ===========================================================================
class TestYouTubePublisher:
    def test_platform_name(self):
        publisher = YouTubePublisher()
        assert publisher.platform_name == "youtube"

    def test_platform(self):
        publisher = YouTubePublisher()
        assert publisher.platform == PublishingPlatform.YOUTUBE

    def test_authenticate(self):
        publisher = YouTubePublisher()
        config = PlatformConfig(client_id="test_client", client_secret="test_secret")
        cred = run_async(publisher.authenticate(config))
        assert cred.access_token != ""
        assert cred.platform == PublishingPlatform.YOUTUBE

    def test_authenticate_missing_credentials(self):
        publisher = YouTubePublisher()
        config = PlatformConfig()
        with pytest.raises(ValueError):
            run_async(publisher.authenticate(config))

    def test_validate_valid_task(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test"),
        )
        errors = run_async(publisher.validate(task))
        assert errors == []

    def test_validate_invalid_task(self):
        publisher = YouTubePublisher()
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path="",
            metadata=PublishingMetadata(title=""),
        )
        errors = run_async(publisher.validate(task))
        assert len(errors) > 0

    def test_prepare_sets_defaults(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test"),
        )
        prepared = run_async(publisher.prepare(task))
        assert prepared.metadata.category == "27"  # Education default
        assert prepared.metadata.license == "youtube"
        assert prepared.metadata.privacy_status == "private"

    def test_publish_success(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test Video", tags=["test"]),
        )
        cred = AuthCredential(
            platform=PublishingPlatform.YOUTUBE,
            access_token="token",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        report = run_async(publisher.publish(task, cred))
        assert report.status == PublishingJobStatus.COMPLETED
        assert report.video_id != ""
        assert "youtube.com" in report.video_url
        assert report.is_successful is True

    def test_publish_with_thumbnail(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            thumbnail_path=str(thumb),
            metadata=PublishingMetadata(title="Test"),
        )
        cred = AuthCredential(access_token="token")
        report = run_async(publisher.publish(task, cred))
        assert report.thumbnail_uploaded is True

    def test_publish_draft_mode(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            mode=PublishingMode.DRAFT,
            metadata=PublishingMetadata(title="Test"),
        )
        cred = AuthCredential(access_token="token")
        report = run_async(publisher.publish(task, cred))
        assert report.status == PublishingJobStatus.DRAFT_SAVED

    def test_publish_validation_failure(self):
        publisher = YouTubePublisher()
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path="",
            metadata=PublishingMetadata(title=""),
        )
        cred = AuthCredential(access_token="token")
        report = run_async(publisher.publish(task, cred))
        assert report.status == PublishingJobStatus.FAILED
        assert len(report.errors) > 0

    def test_schedule(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
            metadata=PublishingMetadata(title="Test"),
        )
        cred = AuthCredential(access_token="token")
        scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
        report = run_async(publisher.schedule(task, scheduled_at, cred))
        assert report.status == PublishingJobStatus.SCHEDULED

    def test_cancel(self):
        publisher = YouTubePublisher()
        task_id = uuid4()
        cred = AuthCredential(access_token="token")
        result = run_async(publisher.cancel(task_id, cred))
        assert result is True

    def test_monitor_queued(self):
        publisher = YouTubePublisher()
        task = PublishingTask(status=PublishingJobStatus.QUEUED)
        progress = run_async(publisher.monitor(task))
        assert progress.status == PublishingJobStatus.QUEUED

    def test_monitor_completed(self):
        publisher = YouTubePublisher()
        task = PublishingTask(status=PublishingJobStatus.COMPLETED)
        progress = run_async(publisher.monitor(task))
        assert progress.progress_percentage == 100.0

    def test_collect_metrics(self, tmp_path):
        publisher = YouTubePublisher()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        task = PublishingTask(
            platform=PublishingPlatform.YOUTUBE,
            video_path=str(video),
        )
        metrics = run_async(publisher.collect_metrics(task))
        assert metrics.upload_bytes == 1024
        assert metrics.total_api_calls > 0


# ===========================================================================
# Publishing Planner Tests
# ===========================================================================
class TestPublishingPlanner:
    def _make_package(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        return type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": "",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {"title": "Test Video"},
        })()

    def test_plan_basic(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        strategy = PublishingStrategy(platforms=[PublishingPlatform.YOUTUBE])
        plan = planner.plan(
            package,
            strategy,
            project_metadata={"title": "Test", "description": "Desc", "keywords": ["test"]},
        )
        assert plan.task_count == 1
        assert plan.project_id == "proj1"
        assert plan.platforms == [PublishingPlatform.YOUTUBE]

    def test_plan_multi_platform(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        strategy = PublishingStrategy(
            mode=PublishingMode.MULTI_PLATFORM,
            platforms=[PublishingPlatform.YOUTUBE, PublishingPlatform.LINKEDIN],
        )
        plan = planner.plan(package, strategy, project_metadata={"title": "Test"})
        assert plan.task_count == 2
        assert plan.platform_count == 2

    def test_plan_has_metadata(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        strategy = PublishingStrategy()
        plan = planner.plan(
            package,
            strategy,
            project_metadata={"title": "My Title", "keywords": ["kw1", "kw2"]},
        )
        assert plan.tasks[0].metadata.title == "My Title"
        assert "kw1" in plan.tasks[0].metadata.tags

    def test_plan_has_thumbnail_specs(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        strategy = PublishingStrategy(platforms=[PublishingPlatform.YOUTUBE, PublishingPlatform.INSTAGRAM])
        plan = planner.plan(package, strategy, project_metadata={"title": "Test"})
        assert "youtube" in plan.thumbnail_specs
        assert "instagram" in plan.thumbnail_specs

    def test_plan_estimated_time(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        strategy = PublishingStrategy()
        plan = planner.plan(package, strategy, project_metadata={"title": "Test"})
        assert plan.estimated_publishing_time > 0

    def test_plan_scheduled_mode(self, tmp_path):
        planner = PublishingPlanner()
        package = self._make_package(tmp_path)
        scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
        strategy = PublishingStrategy(
            mode=PublishingMode.SCHEDULED,
            schedule=ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at),
        )
        plan = planner.plan(package, strategy, project_metadata={"title": "Test"})
        assert plan.mode == PublishingMode.SCHEDULED
        assert plan.tasks[0].scheduled_at is not None

    def test_plan_validation_errors(self, tmp_path):
        planner = PublishingPlanner()
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": "",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {},  # No title
        })()
        strategy = PublishingStrategy()
        plan = planner.plan(package, strategy, project_metadata={})
        assert len(plan.validation_errors) > 0


# ===========================================================================
# Publishing Strategy Engine Tests
# ===========================================================================
class TestPublishingStrategyEngine:
    def test_get_preset_immediate(self):
        engine = PublishingStrategyEngine()
        strategy = engine.get_preset("immediate")
        assert strategy is not None
        assert strategy.mode == PublishingMode.IMMEDIATE

    def test_get_preset_scheduled(self):
        engine = PublishingStrategyEngine()
        strategy = engine.get_preset("scheduled")
        assert strategy is not None
        assert strategy.mode == PublishingMode.SCHEDULED

    def test_get_preset_draft(self):
        engine = PublishingStrategyEngine()
        strategy = engine.get_preset("draft")
        assert strategy is not None
        assert strategy.mode == PublishingMode.DRAFT

    def test_get_preset_multi_platform(self):
        engine = PublishingStrategyEngine()
        strategy = engine.get_preset("multi_platform")
        assert strategy is not None
        assert strategy.mode == PublishingMode.MULTI_PLATFORM
        assert len(strategy.platforms) >= 2

    def test_get_preset_nonexistent(self):
        engine = PublishingStrategyEngine()
        assert engine.get_preset("nonexistent") is None

    def test_list_presets(self):
        engine = PublishingStrategyEngine()
        presets = engine.list_presets()
        assert "immediate" in presets
        assert "draft" in presets
        assert "multi_platform" in presets

    def test_create_strategy_custom(self):
        engine = PublishingStrategyEngine()
        strategy = engine.create_strategy(
            mode=PublishingMode.SCHEDULED,
            platforms=[PublishingPlatform.YOUTUBE, PublishingPlatform.TWITTER],
            max_retries=5,
        )
        assert strategy.mode == PublishingMode.SCHEDULED
        assert len(strategy.platforms) == 2
        assert strategy.max_retries == 5

    def test_create_schedule(self):
        engine = PublishingStrategyEngine()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = engine.create_schedule(scheduled_at)
        assert config.is_scheduled is True
        assert config.scheduled_at == scheduled_at

    def test_validate_strategy_valid(self):
        engine = PublishingStrategyEngine()
        strategy = engine.get_preset("immediate")
        errors = engine.validate_strategy(strategy)
        assert errors == []

    def test_validate_strategy_no_platforms(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(platforms=[])
        errors = engine.validate_strategy(strategy)
        assert any("at least one platform" in e for e in errors)

    def test_validate_strategy_scheduled_no_time(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(
            mode=PublishingMode.SCHEDULED,
            schedule=ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=None),
        )
        errors = engine.validate_strategy(strategy)
        assert any("scheduled_at" in e for e in errors)

    def test_validate_strategy_multi_platform_one_platform(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(
            mode=PublishingMode.MULTI_PLATFORM,
            platforms=[PublishingPlatform.YOUTUBE],
        )
        errors = engine.validate_strategy(strategy)
        assert any("at least 2" in e for e in errors)

    def test_get_retry_delay_exponential(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_delay_seconds=60.0,
        )
        assert engine.get_retry_delay(strategy, 0) == 60.0
        assert engine.get_retry_delay(strategy, 1) == 120.0
        assert engine.get_retry_delay(strategy, 2) == 240.0

    def test_get_retry_delay_linear(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            retry_delay_seconds=60.0,
        )
        assert engine.get_retry_delay(strategy, 0) == 60.0
        assert engine.get_retry_delay(strategy, 1) == 120.0

    def test_get_retry_delay_fixed(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(
            retry_strategy=RetryStrategy.FIXED_DELAY,
            retry_delay_seconds=30.0,
        )
        assert engine.get_retry_delay(strategy, 0) == 30.0
        assert engine.get_retry_delay(strategy, 5) == 30.0

    def test_get_retry_delay_none(self):
        engine = PublishingStrategyEngine()
        strategy = PublishingStrategy(retry_strategy=RetryStrategy.NONE)
        assert engine.get_retry_delay(strategy, 0) == 0.0


# ===========================================================================
# Publishing Queue Tests
# ===========================================================================
class TestPublishingQueue:
    def test_submit_and_dequeue(self):
        q = PublishingQueue()
        job = PublishingJob(priority=PublishingPriority.NORMAL)
        run_async(q.submit(job))
        assert q.queue_size == 1
        dequeued = run_async(q.dequeue())
        assert dequeued is not None
        assert dequeued.id == job.id

    def test_priority_ordering(self):
        q = PublishingQueue()
        low = PublishingJob(id=uuid4(), priority=PublishingPriority.LOW)
        high = PublishingJob(id=uuid4(), priority=PublishingPriority.HIGH)
        run_async(q.submit(low))
        run_async(q.submit(high))
        first = run_async(q.dequeue())
        assert first.priority == PublishingPriority.HIGH

    def test_complete(self):
        q = PublishingQueue()
        job = PublishingJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        assert run_async(q.complete(job.id)) is True
        assert q.completed_count == 1

    def test_fail_with_retry(self):
        q = PublishingQueue()
        job = PublishingJob(max_retries=2)
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.fail(job.id, "error"))
        assert q.queue_size == 1  # back in queue for retry

    def test_fail_dead_letter(self):
        q = PublishingQueue()
        job = PublishingJob(max_retries=0)
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.fail(job.id, "error"))
        assert q.dead_letter_count == 1

    def test_cancel_active(self):
        q = PublishingQueue()
        job = PublishingJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        assert run_async(q.cancel(job.id)) is True
        assert job.status == PublishingJobStatus.CANCELLED

    def test_cancel_queued(self):
        q = PublishingQueue()
        job = PublishingJob()
        run_async(q.submit(job))
        assert run_async(q.cancel(job.id)) is True
        assert q.queue_size == 0

    def test_pause_resume(self):
        q = PublishingQueue()
        q.pause()
        assert q.is_paused is True
        assert run_async(q.dequeue()) is None
        q.resume()
        assert q.is_paused is False

    def test_get_job(self):
        q = PublishingQueue()
        job = PublishingJob()
        run_async(q.submit(job))
        found = q.get_job(job.id)
        assert found is not None
        assert found.id == job.id

    def test_clear_completed(self):
        q = PublishingQueue()
        job = PublishingJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.complete(job.id))
        assert q.clear_completed() == 1
        assert q.completed_count == 0

    def test_get_dead_letter_jobs(self):
        q = PublishingQueue()
        job = PublishingJob(max_retries=0)
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.fail(job.id, "error"))
        dead = q.get_dead_letter_jobs()
        assert len(dead) == 1


# ===========================================================================
# Scheduling Engine Tests
# ===========================================================================
class TestSchedulingEngine:
    def test_schedule_immediate(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        config = ScheduleConfig(mode=PublishingMode.IMMEDIATE)
        result = engine.schedule_task(task, config)
        assert result.mode == PublishingMode.IMMEDIATE
        assert result.scheduled_at is None

    def test_schedule_scheduled(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        result = engine.schedule_task(task, config)
        assert result.mode == PublishingMode.SCHEDULED
        assert result.scheduled_at is not None

    def test_schedule_past_time_raises(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        config = ScheduleConfig(
            mode=PublishingMode.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with pytest.raises(ValueError, match="future"):
            engine.schedule_task(task, config)

    def test_schedule_scheduled_no_time_raises(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=None)
        with pytest.raises(ValueError, match="scheduled_at"):
            engine.schedule_task(task, config)

    def test_schedule_draft(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        config = ScheduleConfig(mode=PublishingMode.DRAFT)
        result = engine.schedule_task(task, config)
        assert result.mode == PublishingMode.DRAFT

    def test_get_scheduled_time(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        engine.schedule_task(task, config)
        result = engine.get_scheduled_time(task.id)
        assert result is not None

    def test_get_due_tasks(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        # Schedule 1 second in the future
        soon = datetime.now(timezone.utc) + timedelta(seconds=1)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=soon)
        engine.schedule_task(task, config)
        # Check with a "now" that is after the scheduled time
        future_now = datetime.now(timezone.utc) + timedelta(seconds=2)
        due = engine.get_due_tasks(now=future_now)
        assert task.id in due

    def test_cancel_schedule(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        engine.schedule_task(task, config)
        assert engine.cancel_schedule(task.id) is True
        assert engine.get_scheduled_time(task.id) is None

    def test_cancel_schedule_not_found(self):
        engine = SchedulingEngine()
        assert engine.cancel_schedule(uuid4()) is False

    def test_scheduled_count(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        engine.schedule_task(task, config)
        assert engine.scheduled_count == 1

    def test_list_scheduled_tasks(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        engine.schedule_task(task, config)
        scheduled = engine.list_scheduled_tasks()
        assert task.id in scheduled

    def test_create_schedule_config(self):
        engine = SchedulingEngine()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
        config = engine.create_schedule_config(
            mode=PublishingMode.SCHEDULED,
            scheduled_at=scheduled_at,
            timezone_str="America/New_York",
        )
        assert config.timezone == "America/New_York"
        assert config.is_scheduled is True

    def test_next_run_time(self):
        engine = SchedulingEngine()
        task = PublishingTask()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        config = ScheduleConfig(mode=PublishingMode.SCHEDULED, scheduled_at=scheduled_at)
        engine.schedule_task(task, config)
        assert engine.next_run_time(task.id) == scheduled_at


# ===========================================================================
# Progress Tracker Tests
# ===========================================================================
class TestProgressTracker:
    def test_register(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        progress = tracker.register(task_id)
        assert progress.task_id == task_id
        assert progress.status == PublishingJobStatus.QUEUED

    def test_update(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        tracker.register(task_id)
        progress = tracker.update(
            task_id,
            status=PublishingJobStatus.UPLOADING,
            percentage=50.0,
            stage="uploading",
            upload_progress=45.0,
        )
        assert progress.status == PublishingJobStatus.UPLOADING
        assert progress.progress_percentage == 50.0
        assert progress.upload_progress == 45.0
        assert "uploading" in progress.stages_completed

    def test_get(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        tracker.register(task_id)
        progress = tracker.get(task_id)
        assert progress is not None

    def test_subscribe(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        tracker.register(task_id)
        updates: list[PublishingProgress] = []
        tracker.subscribe(task_id, lambda p: updates.append(p))
        tracker.update(task_id, percentage=25.0)
        assert len(updates) == 1
        assert updates[0].progress_percentage == 25.0

    def test_unsubscribe(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        tracker.register(task_id)
        updates: list[PublishingProgress] = []
        cb = lambda p: updates.append(p)
        tracker.subscribe(task_id, cb)
        tracker.unsubscribe(task_id, cb)
        tracker.update(task_id, percentage=50.0)
        assert len(updates) == 0

    def test_remove(self):
        tracker = ProgressTracker()
        task_id = uuid4()
        tracker.register(task_id)
        tracker.remove(task_id)
        assert tracker.get(task_id) is None

    def test_active_tasks(self):
        tracker = ProgressTracker()
        tracker.register(uuid4())
        tracker.register(uuid4())
        assert tracker.active_tasks == 2

    def test_get_all_progress(self):
        tracker = ProgressTracker()
        tracker.register(uuid4())
        tracker.register(uuid4())
        all_progress = tracker.get_all_progress()
        assert len(all_progress) == 2


# ===========================================================================
# Events Tests
# ===========================================================================
class TestPublishingEvents:
    def test_event_constants(self):
        assert PublishingEvents.PUBLISHING_PLANNED == "PublishingPlanned"
        assert PublishingEvents.PUBLISHING_STARTED == "PublishingStarted"
        assert PublishingEvents.UPLOAD_PROGRESS == "UploadProgress"
        assert PublishingEvents.PUBLISHING_COMPLETED == "PublishingCompleted"
        assert PublishingEvents.PUBLISHING_FAILED == "PublishingFailed"
        assert PublishingEvents.RETRY_TRIGGERED == "RetryTriggered"
        assert PublishingEvents.SCHEDULE_CREATED == "ScheduleCreated"
        assert PublishingEvents.DRAFT_SAVED == "DraftSaved"

    def test_emit_publishing_planned(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_publishing_planned(uuid4(), "proj1", 2))

    def test_emit_publishing_started(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_publishing_started(uuid4(), "youtube"))

    def test_emit_upload_progress(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_upload_progress(uuid4(), 75.0, 1024))

    def test_emit_publishing_completed(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_publishing_completed(uuid4(), "youtube", "https://youtube.com/watch?v=123"))

    def test_emit_publishing_failed(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_publishing_failed(uuid4(), "youtube", "Upload failed"))

    def test_emit_retry_triggered(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_retry_triggered(uuid4(), 1, 3))

    def test_emit_schedule_created(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_schedule_created(uuid4(), datetime.now().isoformat(), "youtube"))

    def test_emit_draft_saved(self):
        emitter = PublishingEventEmitter()
        run_async(emitter.emit_draft_saved(uuid4(), "youtube", "draft123"))


# ===========================================================================
# Publisher Interface Tests
# ===========================================================================
class TestPublisherInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Publisher()  # type: ignore[abstract]

    def test_youtube_publisher_is_publisher(self):
        publisher = YouTubePublisher()
        assert isinstance(publisher, Publisher)


# ===========================================================================
# Integration Tests
# ===========================================================================
class TestIntegration:
    def test_full_planning_pipeline(self, tmp_path):
        """Test the full pipeline from ProjectPackage to PublishingPlan."""
        # 1. Create mock ProjectPackage
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": "",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {"title": "Test Video"},
        })()

        # 2. Create strategy
        strategy_engine = PublishingStrategyEngine()
        strategy = strategy_engine.create_strategy(
            mode=PublishingMode.IMMEDIATE,
            platforms=[PublishingPlatform.YOUTUBE],
        )

        # 3. Plan
        planner = PublishingPlanner()
        plan = planner.plan(
            package,
            strategy,
            project_metadata={
                "title": "Amazing Tutorial",
                "description": "Learn Python in 10 minutes",
                "keywords": ["python", "tutorial", "coding"],
                "category": "27",
            },
        )
        assert plan.task_count == 1
        assert plan.tasks[0].metadata.title == "Amazing Tutorial"
        assert "python" in plan.tasks[0].metadata.tags

        # 4. Validate
        validator = PublishingValidator()
        errors, warnings = validator.validate_task(plan.tasks[0])
        assert errors == []

    def test_full_publishing_pipeline(self, tmp_path):
        """Test the full pipeline from plan to publishing report."""
        # 1. Create mock ProjectPackage
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": str(thumb),
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {"title": "Test Video"},
        })()

        # 2. Plan
        strategy_engine = PublishingStrategyEngine()
        strategy = strategy_engine.get_preset("immediate")
        planner = PublishingPlanner()
        plan = planner.plan(
            package,
            strategy,
            project_metadata={"title": "Test Video", "keywords": ["test"]},
        )

        # 3. Authenticate
        auth_mgr = AuthenticationManager()
        config = PlatformConfig(client_id="test_client", client_secret="test_secret")
        cred = run_async(auth_mgr.authenticate(PublishingPlatform.YOUTUBE, config))

        # 4. Publish
        publisher = YouTubePublisher()
        task = plan.tasks[0]
        report = run_async(publisher.publish(task, cred))

        assert report.status == PublishingJobStatus.COMPLETED
        assert report.video_url != ""
        assert report.thumbnail_uploaded is True
        assert report.is_successful is True

    def test_multi_platform_pipeline(self, tmp_path):
        """Test multi-platform planning."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": "",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {},
        })()

        strategy_engine = PublishingStrategyEngine()
        strategy = strategy_engine.get_preset("multi_platform")
        planner = PublishingPlanner()
        plan = planner.plan(package, strategy, project_metadata={"title": "Test"})

        assert plan.task_count == 2
        platforms = plan.platforms
        assert PublishingPlatform.YOUTUBE in platforms
        assert PublishingPlatform.LINKEDIN in platforms

    def test_scheduled_pipeline(self, tmp_path):
        """Test scheduled publishing pipeline."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)
        package = type("MockPackage", (), {
            "id": uuid4(),
            "project_id": "proj1",
            "final_video_path": str(video),
            "thumbnail_path": "",
            "quality_report": type("MockReport", (), {"overall_pass": True})(),
            "metadata": {},
        })()

        # Create scheduled strategy
        scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
        strategy_engine = PublishingStrategyEngine()
        schedule_config = strategy_engine.create_schedule(scheduled_at)
        strategy = strategy_engine.create_strategy(
            mode=PublishingMode.SCHEDULED,
            schedule=schedule_config,
        )

        # Plan
        planner = PublishingPlanner()
        plan = planner.plan(package, strategy, project_metadata={"title": "Scheduled Video"})

        assert plan.mode == PublishingMode.SCHEDULED
        assert plan.tasks[0].scheduled_at is not None

        # Schedule
        scheduler = SchedulingEngine()
        scheduled_task = scheduler.schedule_task(plan.tasks[0], schedule_config)
        assert scheduled_task.mode == PublishingMode.SCHEDULED
        assert scheduler.scheduled_count == 1

    def test_queue_and_progress_pipeline(self, tmp_path):
        """Test queue submission and progress tracking."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"x" * 1024)

        # Create a publishing job
        job = PublishingJob(
            project_id="proj1",
            platform=PublishingPlatform.YOUTUBE,
            priority=PublishingPriority.NORMAL,
        )

        # Submit to queue
        queue = PublishingQueue()
        run_async(queue.submit(job))
        assert queue.queue_size == 1

        # Dequeue
        dequeued = run_async(queue.dequeue())
        assert dequeued is not None

        # Track progress
        tracker = ProgressTracker()
        tracker.register(dequeued.task_id)
        tracker.update(dequeued.task_id, status=PublishingJobStatus.UPLOADING, percentage=50.0)
        progress = tracker.get(dequeued.task_id)
        assert progress is not None
        assert progress.progress_percentage == 50.0

        # Complete
        run_async(queue.complete(dequeued.id))
        assert queue.completed_count == 1
