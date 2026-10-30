"""Celery application for background job processing.

All long-running tasks (AI generation, rendering, publishing) are
dispatched as Celery tasks.  The worker processes consume from the
Redis broker.

Task naming convention: ``src.infrastructure.tasks.<module>.<task_name>``
"""

from __future__ import annotations

from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_video_studio",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Time limits
    task_soft_time_limit=settings.celery.task_soft_time_limit,
    task_time_limit=settings.celery.task_time_limit,
    # Worker tuning
    worker_concurrency=settings.celery.worker_concurrency,
    worker_prefetch_multiplier=settings.celery.worker_prefetch_multiplier,
    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_extended=True,
    # Auto-discovery
    include=[
        "src.infrastructure.tasks.generation_tasks",
        "src.infrastructure.tasks.rendering_tasks",
        "src.infrastructure.tasks.publishing_tasks",
        "src.infrastructure.tasks.workflow_tasks",
    ],
)

celery_app.autodiscover_tasks(
    packages=[
        "src.infrastructure.tasks",
    ],
)
