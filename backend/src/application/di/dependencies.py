"""FastAPI dependency injection providers.

These functions are used with ``Depends()`` in FastAPI routers to
inject services from the ``ServiceContainer``.

Usage::

    from src.application.di.dependencies import get_container, get_llm_gateway

    @router.get("/generate")
    async def generate(
        llm: LLMGateway = Depends(get_llm_gateway),
    ):
        ...
"""

from __future__ import annotations

from fastapi import Depends, Request

from src.application.di.container import ServiceContainer
from src.core.config_service import ConfigService


def get_container(request: Request) -> ServiceContainer:
    """Retrieve the ``ServiceContainer`` from the FastAPI application state.

    The container is stored on ``app.state.container`` during application
    startup (see ``main.py`` lifespan).

    Args:
        request: The incoming FastAPI request.

    Returns:
        The ``ServiceContainer`` instance.
    """
    container: ServiceContainer | None = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError(
            "ServiceContainer is not initialised. "
            "Ensure the application lifespan has run."
        )
    return container


def get_config(request: Request) -> ConfigService:
    """Retrieve the ``ConfigService`` from the application state."""
    return get_container(request).config


def get_llm_gateway(request: Request):
    """Inject the LLM Gateway."""
    return get_container(request).get_service("llm_gateway")


def get_image_gateway(request: Request):
    """Inject the Image Gateway."""
    return get_container(request).get_service("image_gateway")


def get_video_gateway(request: Request):
    """Inject the Video Gateway."""
    return get_container(request).get_service("video_gateway")


def get_voice_gateway(request: Request):
    """Inject the Voice Gateway."""
    return get_container(request).get_service("voice_gateway")


def get_rendering_gateway(request: Request):
    """Inject the Rendering Gateway."""
    return get_container(request).get_service("rendering_gateway")


def get_storage_gateway(request: Request):
    """Inject the Storage Gateway."""
    return get_container(request).get_service("storage_gateway")


def get_prompt_manager(request: Request):
    """Inject the Prompt Manager."""
    return get_container(request).get_service("prompt_manager")


def get_cost_tracker(request: Request):
    """Inject the Cost Tracker."""
    return get_container(request).get_service("cost_tracker")


def get_token_tracker(request: Request):
    """Inject the Token Tracker."""
    return get_container(request).get_service("token_tracker")


def get_event_bus(request: Request):
    """Inject the Event Bus."""
    return get_container(request).get_service("event_bus")


def get_metrics_collector(request: Request):
    """Inject the Metrics Collector."""
    return get_container(request).get_service("metrics_collector")


def get_provider_registry(request: Request):
    """Inject the Provider Registry."""
    return get_container(request).get_service("provider_registry")
