"""Composition Platform events.

Events emitted during the composition and rendering lifecycle:
- CompositionCreated
- CompositionValidated
- RenderPlanned
- RenderingStarted
- EncodingStarted
- EncodingCompleted
- RenderingCompleted
- RenderingFailed
- ProjectPackageGenerated
"""

from __future__ import annotations

from uuid import UUID

from src.core.logging import get_logger


class CompositionEvents:
    """Constants for composition event types."""

    COMPOSITION_CREATED = "CompositionCreated"
    COMPOSITION_VALIDATED = "CompositionValidated"
    RENDER_PLANNED = "RenderPlanned"
    RENDERING_STARTED = "RenderingStarted"
    ENCODING_STARTED = "EncodingStarted"
    ENCODING_COMPLETED = "EncodingCompleted"
    RENDERING_COMPLETED = "RenderingCompleted"
    RENDERING_FAILED = "RenderingFailed"
    PROJECT_PACKAGE_GENERATED = "ProjectPackageGenerated"


class CompositionEventEmitter:
    """Event emitter for composition platform events.

    Uses structured logging for event emission.  When an EventBus is
    available, events are also published to the bus for real-time
    progress tracking via WebSockets/SSE.
    """

    def __init__(self, event_bus: object | None = None) -> None:
        self._event_bus = event_bus
        self._logger = get_logger(__name__)

    async def emit(self, event_type: str, data: dict, *, correlation_id: str | None = None, source: str = "composition") -> None:
        """Emit a composition event."""
        self._logger.info(
            "composition_event_emitted",
            event_type=event_type,
            correlation_id=correlation_id,
            source=source,
            **{k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
        )
        if self._event_bus is not None:
            try:
                await self._event_bus.publish(event_type, data)  # type: ignore[attr-defined]
            except Exception:
                pass

    async def emit_composition_created(self, composition_id: UUID, scene_count: int, track_count: int, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.COMPOSITION_CREATED, {"composition_id": str(composition_id), "scene_count": scene_count, "track_count": track_count}, correlation_id=correlation_id, source="composition.builder")

    async def emit_composition_validated(self, composition_id: UUID, valid: bool, errors: int, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.COMPOSITION_VALIDATED, {"composition_id": str(composition_id), "valid": valid, "errors": errors}, correlation_id=correlation_id, source="composition.validator")

    async def emit_render_planned(self, composition_id: UUID, estimated_time: float, complexity: float, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.RENDER_PLANNED, {"composition_id": str(composition_id), "estimated_time": estimated_time, "complexity": complexity}, correlation_id=correlation_id, source="composition.planner")

    async def emit_rendering_started(self, job_id: UUID, composition_id: UUID, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.RENDERING_STARTED, {"job_id": str(job_id), "composition_id": str(composition_id)}, correlation_id=correlation_id, source="composition.pipeline")

    async def emit_encoding_started(self, job_id: UUID, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.ENCODING_STARTED, {"job_id": str(job_id)}, correlation_id=correlation_id, source="composition.renderer")

    async def emit_encoding_completed(self, job_id: UUID, output_size: int, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.ENCODING_COMPLETED, {"job_id": str(job_id), "output_size": output_size}, correlation_id=correlation_id, source="composition.renderer")

    async def emit_rendering_completed(self, job_id: UUID, output_path: str, render_time: float, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.RENDERING_COMPLETED, {"job_id": str(job_id), "output_path": output_path, "render_time": render_time}, correlation_id=correlation_id, source="composition.pipeline")

    async def emit_rendering_failed(self, job_id: UUID, error: str, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.RENDERING_FAILED, {"job_id": str(job_id), "error": error}, correlation_id=correlation_id, source="composition.pipeline")

    async def emit_project_package_generated(self, package_id: UUID, project_id: str, *, correlation_id: str | None = None) -> None:
        await self.emit(CompositionEvents.PROJECT_PACKAGE_GENERATED, {"package_id": str(package_id), "project_id": project_id}, correlation_id=correlation_id, source="composition.export")
