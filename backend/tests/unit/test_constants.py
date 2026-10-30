"""Unit tests for application constants."""

from __future__ import annotations

from src.core import constants


class TestConstants:
    """Verify that constants are sensible and internally consistent."""

    def test_page_size_bounds(self) -> None:
        assert constants.DEFAULT_PAGE_SIZE > 0
        assert constants.MAX_PAGE_SIZE >= constants.DEFAULT_PAGE_SIZE

    def test_job_retry_constants(self) -> None:
        assert constants.MAX_JOB_RETRIES > 0
        assert constants.JOB_RETRY_BACKOFF_BASE >= 2
        assert constants.JOB_RETRY_BACKOFF_MAX > 0

    def test_video_constants(self) -> None:
        assert constants.DEFAULT_FPS > 0
        assert constants.DEFAULT_RESOLUTION_WIDTH > 0
        assert constants.DEFAULT_RESOLUTION_HEIGHT > 0

    def test_quality_score_bounds(self) -> None:
        assert constants.MIN_QUALITY_SCORE == 0.0
        assert constants.MAX_QUALITY_SCORE == 1.0
        assert constants.MIN_ACCEPTABLE_QUALITY > constants.MIN_QUALITY_SCORE
        assert constants.MIN_ACCEPTABLE_QUALITY < constants.MAX_QUALITY_SCORE

    def test_workflow_timeout(self) -> None:
        assert constants.WORKFLOW_TIMEOUT_SECONDS > 0
        assert constants.PARALLEL_BRANCH_TIMEOUT > 0
        assert constants.PARALLEL_BRANCH_TIMEOUT < constants.WORKFLOW_TIMEOUT_SECONDS

    def test_allowed_extensions_are_tuples(self) -> None:
        assert isinstance(constants.ALLOWED_IMAGE_EXTENSIONS, tuple)
        assert isinstance(constants.ALLOWED_VIDEO_EXTENSIONS, tuple)
        assert isinstance(constants.ALLOWED_AUDIO_EXTENSIONS, tuple)

    def test_all_extensions_start_with_dot(self) -> None:
        for ext in (
            *constants.ALLOWED_IMAGE_EXTENSIONS,
            *constants.ALLOWED_VIDEO_EXTENSIONS,
            *constants.ALLOWED_AUDIO_EXTENSIONS,
        ):
            assert ext.startswith(".")
