"""Generation Strategy Engine.

Converts storyboard decisions into an optimized execution strategy.
Supports economy, balanced, premium, fast, and custom modes.

Each strategy determines:
- Image vs video ratio
- Provider selection
- Model selection
- Resolution
- Retry policy
- Concurrency
- Maximum cost
- Quality threshold
- Execution priority
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.schema import GenerationMode, GenerationStrategy, JobPriority


class GenerationStrategyEngine:
    """Engine for creating and managing generation strategies.

    Converts storyboard asset decisions into an execution strategy
    that balances cost, quality, and speed according to the selected mode.
    """

    # Predefined strategy presets
    _PRESETS: dict[GenerationMode, GenerationStrategy] = {
        GenerationMode.ECONOMY: GenerationStrategy(
            mode=GenerationMode.ECONOMY,
            image_video_ratio=0.9,  # mostly images (cheaper)
            resolution="1280x720",
            max_retries=2,
            concurrency=2,
            max_cost_usd=2.0,
            quality_threshold=0.5,
            execution_priority=JobPriority.LOW,
            enable_caching=True,
            enable_fallback=True,
        ),
        GenerationMode.BALANCED: GenerationStrategy(
            mode=GenerationMode.BALANCED,
            image_video_ratio=0.7,
            resolution="1920x1080",
            max_retries=3,
            concurrency=4,
            max_cost_usd=10.0,
            quality_threshold=0.7,
            execution_priority=JobPriority.NORMAL,
            enable_caching=True,
            enable_fallback=True,
        ),
        GenerationMode.PREMIUM: GenerationStrategy(
            mode=GenerationMode.PREMIUM,
            image_video_ratio=0.4,  # more video (higher quality)
            resolution="3840x2160",
            max_retries=5,
            concurrency=6,
            max_cost_usd=50.0,
            quality_threshold=0.9,
            execution_priority=JobPriority.HIGH,
            enable_caching=True,
            enable_fallback=True,
        ),
        GenerationMode.FAST: GenerationStrategy(
            mode=GenerationMode.FAST,
            image_video_ratio=0.95,  # images are faster
            resolution="1280x720",
            max_retries=1,
            concurrency=8,
            max_cost_usd=5.0,
            quality_threshold=0.5,
            execution_priority=JobPriority.CRITICAL,
            enable_caching=True,
            enable_fallback=False,
        ),
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._custom_strategies: dict[str, GenerationStrategy] = {}

    def get_strategy(self, mode: GenerationMode | str) -> GenerationStrategy:
        """Get a strategy by mode.

        Args:
            mode: The generation mode (economy, balanced, premium, fast, custom).

        Returns:
            The corresponding ``GenerationStrategy``.
        """
        if isinstance(mode, str):
            mode = GenerationMode(mode)

        if mode == GenerationMode.CUSTOM:
            raise ValueError("Custom mode requires a strategy name. Use get_custom_strategy().")

        strategy = self._PRESETS[mode].model_copy()
        self._logger.info("strategy_selected", mode=mode.value, resolution=strategy.resolution, max_cost=strategy.max_cost_usd)
        return strategy

    def get_custom_strategy(self, name: str) -> GenerationStrategy | None:
        """Get a custom strategy by name.

        Args:
            name: The custom strategy name.

        Returns:
            The custom strategy, or ``None`` if not found.
        """
        return self._custom_strategies.get(name)

    def register_custom_strategy(self, name: str, strategy: GenerationStrategy) -> None:
        """Register a custom strategy.

        Args:
            name: Unique name for the strategy.
            strategy: The strategy configuration.
        """
        strategy.mode = GenerationMode.CUSTOM
        self._custom_strategies[name] = strategy
        self._logger.info("custom_strategy_registered", name=name)

    def create_strategy(
        self,
        mode: GenerationMode = GenerationMode.BALANCED,
        *,
        image_video_ratio: float | None = None,
        resolution: str | None = None,
        max_retries: int | None = None,
        concurrency: int | None = None,
        max_cost_usd: float | None = None,
        quality_threshold: float | None = None,
        execution_priority: JobPriority | None = None,
        enable_caching: bool | None = None,
        enable_fallback: bool | None = None,
        preferred_providers: dict[str, str] | None = None,
        preferred_models: dict[str, str] | None = None,
    ) -> GenerationStrategy:
        """Create a strategy from a preset with optional overrides.

        Args:
            mode: Base mode to start from.
            image_video_ratio: Override image/video ratio.
            resolution: Override resolution.
            max_retries: Override max retries.
            concurrency: Override concurrency.
            max_cost_usd: Override max cost.
            quality_threshold: Override quality threshold.
            execution_priority: Override execution priority.
            enable_caching: Override caching.
            enable_fallback: Override fallback.
            preferred_providers: Override preferred providers.
            preferred_models: Override preferred models.

        Returns:
            A customized ``GenerationStrategy``.
        """
        base = self.get_strategy(mode) if mode != GenerationMode.CUSTOM else GenerationStrategy(mode=GenerationMode.CUSTOM)

        updates: dict[str, Any] = {}
        if image_video_ratio is not None:
            updates["image_video_ratio"] = image_video_ratio
        if resolution is not None:
            updates["resolution"] = resolution
        if max_retries is not None:
            updates["max_retries"] = max_retries
        if concurrency is not None:
            updates["concurrency"] = concurrency
        if max_cost_usd is not None:
            updates["max_cost_usd"] = max_cost_usd
        if quality_threshold is not None:
            updates["quality_threshold"] = quality_threshold
        if execution_priority is not None:
            updates["execution_priority"] = execution_priority
        if enable_caching is not None:
            updates["enable_caching"] = enable_caching
        if enable_fallback is not None:
            updates["enable_fallback"] = enable_fallback
        if preferred_providers is not None:
            updates["preferred_providers"] = preferred_providers
        if preferred_models is not None:
            updates["preferred_models"] = preferred_models

        return base.model_copy(update=updates)

    def list_modes(self) -> list[str]:
        """List all available generation modes."""
        return [m.value for m in GenerationMode if m != GenerationMode.CUSTOM]

    def list_custom_strategies(self) -> list[str]:
        """List all registered custom strategy names."""
        return list(self._custom_strategies.keys())
