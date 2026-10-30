"""Provider Selection Engine.

Selects the optimal provider for each generation request by evaluating:
- Cost
- Latency
- Availability
- Quality
- Quota
- Rate limits
- Historical performance
- User preference

Supports automatic fallback when the primary provider fails or is unhealthy.
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.health import ProviderHealthMonitor
from src.generation.schema import AssetCategory, GenerationRequest, GenerationStrategy


class ProviderSelectionEngine:
    """Selects the best provider for a generation request.

    Scoring algorithm weights cost, latency, availability, quality,
    and user preference to produce a composite score per provider.
    The highest-scoring provider is selected.  If it fails, the next
    provider is tried (fallback).
    """

    # Default scoring weights
    _WEIGHTS = {
        "cost": 0.25,
        "latency": 0.15,
        "availability": 0.30,
        "quality": 0.20,
        "preference": 0.10,
    }

    def __init__(self, health_monitor: ProviderHealthMonitor) -> None:
        self._logger = get_logger(__name__)
        self._health = health_monitor
        # provider registry: category -> list of (provider_name, model, cost_fn)
        self._providers: dict[AssetCategory, list[dict[str, Any]]] = {}

    def register_provider(
        self,
        category: AssetCategory,
        provider_name: str,
        model: str,
        cost_fn: Any,
        *,
        quality_score: float = 0.8,
    ) -> None:
        """Register a provider for a category.

        Args:
            category: Asset category (image, video, voice, etc.).
            provider_name: Provider name (e.g. "imagen", "veo").
            model: Model name.
            cost_fn: Function that takes a request and returns estimated cost.
            quality_score: Baseline quality score for this provider.
        """
        if category not in self._providers:
            self._providers[category] = []
        self._providers[category].append({
            "name": provider_name,
            "model": model,
            "cost_fn": cost_fn,
            "quality_score": quality_score,
        })
        self._logger.info("provider_registered", category=category.value, provider=provider_name, model=model)

    def select(
        self,
        request: GenerationRequest,
        strategy: GenerationStrategy,
    ) -> tuple[str, str, float] | None:
        """Select the best provider for a request.

        Args:
            request: The generation request.
            strategy: The active generation strategy.

        Returns:
            Tuple of (provider_name, model, estimated_cost) or ``None``.
        """
        candidates = self._providers.get(request.category, [])
        if not candidates:
            self._logger.warning("no_providers_for_category", category=request.category.value)
            return None

        # Check strategy preferences first
        preferred = strategy.preferred_providers.get(request.category.value)
        preferred_model = strategy.preferred_models.get(request.category.value)

        scored: list[tuple[float, dict[str, Any], float]] = []
        for provider in candidates:
            # Skip unhealthy providers
            metrics = self._health.get_metrics(provider["name"])
            if metrics is not None and (metrics.disabled or not metrics.healthy):
                continue

            # Estimate cost
            try:
                estimated_cost = provider["cost_fn"](request)
            except Exception:
                estimated_cost = 999.0

            # Compute composite score
            availability = metrics.availability if metrics else 1.0
            latency = metrics.latency_ms if metrics else 100.0
            quality = provider["quality_score"]

            # Normalize scores (higher is better)
            cost_score = 1.0 / (1.0 + estimated_cost) if estimated_cost > 0 else 1.0
            latency_score = 1.0 / (1.0 + latency / 1000.0) if latency > 0 else 1.0
            pref_score = 1.0 if preferred == provider["name"] else 0.5

            composite = (
                self._WEIGHTS["cost"] * cost_score
                + self._WEIGHTS["latency"] * latency_score
                + self._WEIGHTS["availability"] * availability
                + self._WEIGHTS["quality"] * quality
                + self._WEIGHTS["preference"] * pref_score
            )

            scored.append((composite, provider, estimated_cost))

        if not scored:
            # All providers unhealthy — fall back to any
            self._logger.warning("all_providers_unhealthy", category=request.category.value)
            for provider in candidates:
                try:
                    cost = provider["cost_fn"](request)
                except Exception:
                    cost = 0.0
                return (provider["name"], preferred_model or provider["model"], cost)
            return None

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_provider, best_cost = scored[0]

        model = preferred_model or best_provider["model"]
        self._logger.info(
            "provider_selected",
            provider=best_provider["name"],
            model=model,
            score=best_score,
            estimated_cost=best_cost,
            category=request.category.value,
        )
        return (best_provider["name"], model, best_cost)

    def get_fallback_chain(self, category: AssetCategory) -> list[str]:
        """Get the ordered list of fallback providers for a category.

        Args:
            category: Asset category.

        Returns:
            List of provider names in fallback order.
        """
        candidates = self._providers.get(category, [])
        healthy = [
            p["name"] for p in candidates
            if not self._health.is_disabled(p["name"])
        ]
        return healthy

    def list_providers(self, category: AssetCategory) -> list[str]:
        """List all registered providers for a category."""
        return [p["name"] for p in self._providers.get(category, [])]
