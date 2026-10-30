"""Tests for the Correlation ID context management."""

from __future__ import annotations

import pytest

from src.core.correlation import (
    clear_context,
    generate_correlation_id,
    get_agent_type,
    get_correlation_id,
    get_job_id,
    get_project_id,
    set_agent_type,
    set_correlation_id,
    set_job_id,
    set_project_id,
)


class TestCorrelationId:
    def test_set_and_get(self):
        set_correlation_id("test-corr-123")
        assert get_correlation_id() == "test-corr-123"
        clear_context()

    def test_clear(self):
        set_correlation_id("test-corr-456")
        clear_context()
        assert get_correlation_id() is None

    def test_generate(self):
        corr_id = generate_correlation_id()
        assert isinstance(corr_id, str)
        assert len(corr_id) > 10

    def test_generate_unique(self):
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()
        assert id1 != id2


class TestJobId:
    def test_set_and_get(self):
        set_job_id("job-789")
        assert get_job_id() == "job-789"
        clear_context()

    def test_clear(self):
        set_job_id("job-000")
        clear_context()
        assert get_job_id() is None


class TestProjectId:
    def test_set_and_get(self):
        set_project_id("proj-abc")
        assert get_project_id() == "proj-abc"
        clear_context()

    def test_clear(self):
        set_project_id("proj-xyz")
        clear_context()
        assert get_project_id() is None


class TestAgentType:
    def test_set_and_get(self):
        set_agent_type("director")
        assert get_agent_type() == "director"
        clear_context()

    def test_clear(self):
        set_agent_type("scene_planner")
        clear_context()
        assert get_agent_type() is None


class TestClearContext:
    def test_clears_all(self):
        set_correlation_id("corr-1")
        set_job_id("job-1")
        set_project_id("proj-1")
        set_agent_type("director")
        clear_context()
        assert get_correlation_id() is None
        assert get_job_id() is None
        assert get_project_id() is None
        assert get_agent_type() is None
