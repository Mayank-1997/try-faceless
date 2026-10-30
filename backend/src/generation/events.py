"""Generation Platform events.

Events emitted during the generation lifecycle:
- GenerationStarted
- GenerationCompleted
- GenerationFailed
- RetryTriggered
- ProviderChanged
- BudgetExceeded
- AssetStored
- ValidationFailed
- ManifestCompleted
"""

from __future__ import annotations

from uuid import UUID

from src.core.logging import get_logger


class GenerationEvents:
    """Constants for generation event types."""

    GENERATION_STARTED = "GenerationStarted"
    GENERATION_COMPLETED = "GenerationCompleted"
    GENERATION_FAILED = "GenerationFailed"
    RETRY_TRIGGERED = "RetryTriggered"
    PROVIDER_CHANGED = "ProviderChanged"
    BUDGET_EXCEEDED = "BudgetExceeded"
    ASSET_STORED = "AssetStored"
    VALIDATION_FAILED = "ValidationFailed"
    MANIFEST_COMPLETED = "ManifestCompleted"


class GenerationEventEmitter:
    """Event emitter for generation platform events.

    Uses structured logging for event emission.  When an EventBus is
    available, events are also published to the bus for real-time
    progress tracking via WebSockets/SSE.
    """

    def __init__(self, event_bus: object | None = None) -> None:
        self._event_bus = event_bus
        self._logger = get_logger(__name__)

    async def emit(self, event_type: str, data: dict, *, correlation_id: str | None = None, source: str = "generation") -> None:
        """Emit a generation event."""
        self._logger.info(
            "generation_event_emitted",
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

    async def emit_generation_started(self, job_id: UUID, scene_id: str, category: str, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.GENERATION_STARTED, {"job_id": str(job_id), "scene_id": scene_id, "category": category}, correlation_id=correlation_id, source="generation.executor")

    async def emit_generation_completed(self, job_id: UUID, asset_id: UUID, cost: float, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.GENERATION_COMPLETED, {"job_id": str(job_id), "asset_id": str(asset_id), "cost_usd": cost}, correlation_id=correlation_id, source="generation.executor")

    async def emit_generation_failed(self, job_id: UUID, error: str, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.GENERATION_FAILED, {"job_id": str(job_id), "error": error}, correlation_id=correlation_id, source="generation.executor")

    async def emit_retry_triggered(self, job_id: UUID, retry_count: int, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.RETRY_TRIGGERED, {"job_id": str(job_id), "retry_count": retry_count}, correlation_id=correlation_id, source="generation.executor")

    async def emit_provider_changed(self, job_id: UUID, old_provider: str, new_provider: str, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.PROVIDER_CHANGED, {"job_id": str(job_id), "old_provider": old_provider, "new_provider": new_provider}, correlation_id=correlation_id, source="generation.provider_selection")

    async def emit_budget_exceeded(self, project_id: str, spent: float, budget: float, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.BUDGET_EXCEEDED, {"project_id": project_id, "spent": spent, "budget": budget}, correlation_id=correlation_id, source="generation.budget")

    async def emit_asset_stored(self, asset_id: UUID, storage_uri: str, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.ASSET_STORED, {"asset_id": str(asset_id), "storage_uri": storage_uri}, correlation_id=correlation_id, source="generation.executor")

    async def emit_validation_failed(self, asset_id: UUID, stage: str, reason: str, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.VALIDATION_FAILED, {"asset_id": str(asset_id), "stage": stage, "reason": reason}, correlation_id=correlation_id, source="generation.validation")

    async def emit_manifest_completed(self, manifest_id: UUID, total_assets: int, total_cost: float, *, correlation_id: str | None = None) -> None:
        await self.emit(GenerationEvents.MANIFEST_COMPLETED, {"manifest_id": str(manifest_id), "total_assets": total_assets, "total_cost": total_cost}, correlation_id=correlation_id, source="generation.manifest")
