"""Tests for per-project workflow file logging."""

from __future__ import annotations

import logging
from uuid import uuid4

import pytest

from src.core.config import get_settings
from src.infrastructure.tasks.workflow_tasks import (
    _attach_project_log_handler,
    _detach_project_log_handler,
    _get_project_log_path,
)


@pytest.fixture()
def storage_tmp(tmp_path, monkeypatch):
    """Point STORAGE_LOCAL_PATH at a temp dir and clear the settings cache."""
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


class TestProjectFileLogging:
    def test_log_path_is_under_project_logs_dir(self, storage_tmp):
        """The log file lands under storage/projects/<pid>/logs/."""
        project_id = uuid4()
        workflow_id = uuid4()
        path = _get_project_log_path(project_id, workflow_id)

        assert str(project_id) in str(path)
        assert "logs" in str(path)
        assert str(workflow_id) in path.name
        assert path.suffix == ".txt"
        assert path.parent.exists()

    def test_attach_and_detach_handler(self, storage_tmp):
        """Attaching adds a handler; detaching removes it and writes a footer."""
        project_id = uuid4()
        workflow_id = uuid4()
        root = logging.getLogger()
        count_before = len(root.handlers)

        handler = _attach_project_log_handler(project_id, workflow_id)
        assert handler is not None
        assert len(root.handlers) == count_before + 1

        # Write a test log through stdlib logging (structlog routes through
        # stdlib in production after configure_logging() is called)
        test_logger = logging.getLogger("test_project_logging")
        test_logger.info("test_log_message_stdlib")
        handler.flush()

        # Detach
        _detach_project_log_handler(handler, project_id, workflow_id)
        assert len(root.handlers) == count_before

        # Verify the file was written
        log_path = _get_project_log_path(project_id, workflow_id)
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "WORKFLOW LOG" in content
        assert "test_log_message_stdlib" in content
        assert "WORKFLOW ENDED" in content
        assert str(project_id) in content
        assert str(workflow_id) in content

    def test_detach_none_is_noop(self):
        """Detaching None does nothing and does not raise."""
        _detach_project_log_handler(None, uuid4(), uuid4())
