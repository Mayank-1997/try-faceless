"""Structured logging configuration using ``structlog``.

Provides JSON-formatted logs in production and human-readable colored
logs in development.  Every log entry includes a timestamp, log level,
event name, and arbitrary structured key-value pairs.

Usage::

    from src.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("agent_started", agent="research", project_id=uuid)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.core.config import get_settings


def _add_app_context(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Inject application-wide metadata into every log entry."""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.environment
    return event_dict


def configure_logging() -> None:
    """Configure structlog and stdlib logging once at application startup.

    - **Development**: pretty-printed colored console output.
    - **Staging/Production**: JSON-formatted lines for log aggregation.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors for both structlog and stdlib integration
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_development:
        # Human-readable colored output for development
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON for production log aggregation (Datadog, Loki, etc.)
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging into structlog so libraries (uvicorn, sqlalchemy)
    # produce structured logs as well.
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stderr,
        force=True,
    )

    for noisy_logger in ("uvicorn.access",):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    # Optional Grafana Cloud Loki shipping (env-gated; no-op when unset).
    try:
        from src.core.loki import install_loki_handler

        if install_loki_handler(settings):
            logging.getLogger(__name__).info("loki_log_shipping_enabled")
    except Exception:
        logging.getLogger(__name__).warning(
            "loki_handler_init_failed", exc_info=True
        )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger.

    Args:
        name: Module name (typically ``__name__``).  If ``None``, returns
            the root logger.
    """
    return structlog.get_logger(name)
