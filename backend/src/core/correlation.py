"""Correlation ID context management for structured logging.

Provides request-scoped correlation IDs that are automatically injected
into every log entry via structlog context variables.

Usage in middleware::

    from src.core.correlation import set_correlation_id, get_correlation_id

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        set_correlation_id(corr_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

import structlog

# Context variables for request-scoped data
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)
_project_id: ContextVar[str | None] = ContextVar("project_id", default=None)
_agent_type: ContextVar[str | None] = ContextVar("agent_type", default=None)


def set_correlation_id(corr_id: str | None) -> None:
    """Set the correlation ID for the current async context.

    Args:
        corr_id: The correlation ID string.
    """
    _correlation_id.set(corr_id)
    if corr_id:
        structlog.contextvars.bind_contextvars(correlation_id=corr_id)
    else:
        structlog.contextvars.unbind_contextvars("correlation_id")


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current async context.

    Returns:
        The correlation ID string, or ``None`` if not set.
    """
    return _correlation_id.get()


def set_job_id(job_id: str | None) -> None:
    """Set the job ID for the current async context."""
    _job_id.set(job_id)
    if job_id:
        structlog.contextvars.bind_contextvars(job_id=job_id)
    else:
        structlog.contextvars.unbind_contextvars("job_id")


def get_job_id() -> str | None:
    """Get the job ID for the current async context."""
    return _job_id.get()


def set_project_id(project_id: str | None) -> None:
    """Set the project ID for the current async context."""
    _project_id.set(project_id)
    if project_id:
        structlog.contextvars.bind_contextvars(project_id=project_id)
    else:
        structlog.contextvars.unbind_contextvars("project_id")


def get_project_id() -> str | None:
    """Get the project ID for the current async context."""
    return _project_id.get()


def set_agent_type(agent_type: str | None) -> None:
    """Set the agent type for the current async context."""
    _agent_type.set(agent_type)
    if agent_type:
        structlog.contextvars.bind_contextvars(agent_type=agent_type)
    else:
        structlog.contextvars.unbind_contextvars("agent_type")


def get_agent_type() -> str | None:
    """Get the agent type for the current async context."""
    return _agent_type.get()


def generate_correlation_id() -> str:
    """Generate a new UUID-based correlation ID."""
    return str(uuid.uuid4())


def clear_context() -> None:
    """Clear all context variables — call at the end of a request/job."""
    set_correlation_id(None)
    set_job_id(None)
    set_project_id(None)
    set_agent_type(None)
