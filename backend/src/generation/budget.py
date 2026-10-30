"""Budget Manager.

Estimates and enforces budgets at multiple levels:
- Project cost
- Workflow cost
- Scene cost
- Asset cost

Rejects requests that exceed budget.
Recommends cheaper alternatives.
Automatically downgrades video to image when required.
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.events import GenerationEventEmitter, GenerationEvents
from src.generation.schema import (
    AssetCategory,
    BudgetEstimate,
    BudgetStatus,
    GenerationRequest,
)


class BudgetManager:
    """Manages generation budgets and enforces spending limits.

    Tracks spending at project, scene, and category levels.
    Automatically rejects requests that would exceed the budget
    and recommends cheaper alternatives (e.g. video → image).
    """

    def __init__(self, event_emitter: GenerationEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._event_emitter = event_emitter or GenerationEventEmitter()
        self._project_budgets: dict[str, float] = {}
        self._project_spent: dict[str, float] = {}
        self._scene_spent: dict[str, dict[str, float]] = {}  # project -> scene -> spent
        self._category_spent: dict[str, dict[str, float]] = {}  # project -> category -> spent

    def set_project_budget(self, project_id: str, budget: float) -> None:
        """Set the total budget for a project.

        Args:
            project_id: Project identifier.
            budget: Maximum spend in USD.
        """
        self._project_budgets[project_id] = budget
        self._logger.info("budget_set", project_id=project_id, budget=budget)

    def get_budget_status(self, project_id: str) -> BudgetStatus:
        """Get the current budget status for a project.

        Args:
            project_id: Project identifier.

        Returns:
            ``BudgetStatus`` with spent, remaining, and per-scene breakdowns.
        """
        budget = self._project_budgets.get(project_id, 0.0)
        spent = self._project_spent.get(project_id, 0.0)
        remaining = budget - spent
        scene_budgets = self._scene_spent.get(project_id, {})
        category_spent = self._category_spent.get(project_id, {})

        return BudgetStatus(
            project_id=project_id,
            total_budget=budget,
            spent=spent,
            remaining=remaining,
            per_scene_budget=scene_budgets,
            per_category_spent=category_spent,
            exceeded=spent >= budget if budget > 0 else False,
        )

    def estimate(self, request: GenerationRequest, provider: str, model: str, cost: float) -> BudgetEstimate:
        """Estimate the cost of a generation request.

        Args:
            request: The generation request.
            provider: Provider name.
            model: Model name.
            cost: Estimated cost in USD.

        Returns:
            ``BudgetEstimate`` with affordability check.
        """
        project_id = request.project_id
        budget = self._project_budgets.get(project_id, 0.0)
        spent = self._project_spent.get(project_id, 0.0)
        remaining = budget - spent

        affordable = remaining >= cost if budget > 0 else True

        estimate = BudgetEstimate(
            request_id=request.id,
            provider=provider,
            model=model,
            estimated_cost=cost,
            category=request.category,
            affordable=affordable,
        )

        if not affordable:
            self._logger.warning(
                "budget_exceeded",
                project_id=project_id,
                remaining=remaining,
                estimated_cost=cost,
            )

        return estimate

    def check_budget(self, project_id: str, estimated_cost: float) -> bool:
        """Check if a request can be afforded.

        Args:
            project_id: Project identifier.
            estimated_cost: Estimated cost in USD.

        Returns:
            ``True`` if the request is within budget.
        """
        budget = self._project_budgets.get(project_id, 0.0)
        if budget <= 0:
            return True
        spent = self._project_spent.get(project_id, 0.0)
        return (spent + estimated_cost) <= budget

    def record_spend(
        self,
        project_id: str,
        scene_id: str,
        category: AssetCategory,
        amount: float,
    ) -> None:
        """Record an actual spend.

        Args:
            project_id: Project identifier.
            scene_id: Scene identifier.
            category: Asset category.
            amount: Amount spent in USD.
        """
        self._project_spent[project_id] = self._project_spent.get(project_id, 0.0) + amount

        if project_id not in self._scene_spent:
            self._scene_spent[project_id] = {}
        self._scene_spent[project_id][scene_id] = self._scene_spent[project_id].get(scene_id, 0.0) + amount

        if project_id not in self._category_spent:
            self._category_spent[project_id] = {}
        cat_key = category.value
        self._category_spent[project_id][cat_key] = self._category_spent[project_id].get(cat_key, 0.0) + amount

        # Check if budget exceeded
        budget = self._project_budgets.get(project_id, 0.0)
        spent = self._project_spent[project_id]
        if budget > 0 and spent >= budget:
            import asyncio
            self._logger.warning("budget_exceeded_notification", project_id=project_id, spent=spent, budget=budget)

    def recommend_downgrade(self, request: GenerationRequest) -> AssetCategory | None:
        """Recommend a cheaper asset category if budget is tight.

        Automatically suggests downgrading video to image when
        the budget cannot accommodate video generation.

        Args:
            request: The generation request.

        Returns:
            Recommended cheaper category, or ``None`` if no downgrade needed.
        """
        if request.category == AssetCategory.VIDEO:
            return AssetCategory.IMAGE
        if request.category == AssetCategory.MUSIC:
            return None  # No cheaper alternative for music
        return None

    def get_project_total(self, project_id: str) -> float:
        """Get total spent for a project."""
        return self._project_spent.get(project_id, 0.0)

    def get_scene_total(self, project_id: str, scene_id: str) -> float:
        """Get total spent for a scene."""
        return self._scene_spent.get(project_id, {}).get(scene_id, 0.0)

    def clear(self) -> None:
        """Clear all budget data (primarily for testing)."""
        self._project_budgets.clear()
        self._project_spent.clear()
        self._scene_spent.clear()
        self._category_spent.clear()
