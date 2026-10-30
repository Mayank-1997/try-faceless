"""Cost tracking entity — granular cost records at multiple levels.

Costs are tracked per user, project, workflow, job, scene, asset, and
provider. Aggregations are computed by period (daily, monthly).
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import AIProvider, CostPeriod


class CostRecord:
    """A single cost tracking record.

    Attributes:
        id: UUID primary key.
        user_id: UUID of the user who incurred the cost.
        project_id: UUID of the project.
        workflow_id: UUID of the workflow (optional).
        job_id: UUID of the job (optional).
        scene_id: UUID of the scene (optional).
        asset_id: UUID of the asset (optional).
        provider: AI provider that charged the cost.
        cost_usd: Cost amount in USD.
        cost_category: Category (llm, image, video, voice, render, other).
        period: Aggregation period.
        period_start: Start of the aggregation period.
        period_end: End of the aggregation period.
        metadata: Additional cost metadata.
        created_at: Record creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        job_id: UUID | None = None,
        scene_id: UUID | None = None,
        asset_id: UUID | None = None,
        provider: AIProvider | str = "",
        cost_usd: float = 0.0,
        cost_category: str = "llm",
        period: CostPeriod = CostPeriod.DAILY,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.user_id = user_id
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.job_id = job_id
        self.scene_id = scene_id
        self.asset_id = asset_id
        self.provider = provider
        self.cost_usd = cost_usd
        self.cost_category = cost_category
        self.period = period
        self.period_start = period_start
        self.period_end = period_end
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(dt_timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "scene_id": str(self.scene_id) if self.scene_id else None,
            "asset_id": str(self.asset_id) if self.asset_id else None,
            "provider": self.provider.value if hasattr(self.provider, "value") else str(self.provider),
            "cost_usd": self.cost_usd,
            "cost_category": self.cost_category,
            "period": self.period.value,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
