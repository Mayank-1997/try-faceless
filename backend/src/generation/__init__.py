"""Generation Platform — centralized execution engine for all media generation.

Phase 9: Generation Platform & Intelligent Asset Generation.

The platform transforms storyboard decisions into production-ready
media assets through a pipeline of:

    Storyboard → Strategy Engine → Orchestrator → Queue Manager →
    Provider Selection → Generation Executor → Validation Pipeline →
    Asset Repository → Asset Manifest

Key principle: **AI agents never call providers directly.**
All media generation flows through this platform.

Modules:
- ``GenerationStrategyEngine`` — Converts storyboard to execution strategy
- ``GenerationOrchestrator`` — Top-level coordinator
- ``QueueManager`` — Priority-based async job queue
- ``ProviderSelectionEngine`` — Optimal provider selection with fallback
- ``BudgetManager`` — Cost estimation and enforcement
- ``ConcurrencyManager`` — Throttling and quotas
- ``ProviderHealthMonitor`` — Provider health tracking
- ``CacheManager`` — Generation deduplication
- ``GenerationExecutor`` — The ONLY component that calls providers
- ``ValidationPipeline`` — 10-stage asset validation
- ``QualityEngine`` — Multi-dimension quality evaluation
- ``AssetManifestBuilder`` — Builds final manifest for rendering engine
- ``SubtitleGenerator`` — SRT/VTT subtitle generation
- ``ThumbnailGenerator`` — Thumbnail prompt generation
- ``GenerationEventEmitter`` — Lifecycle events
"""

from src.generation.budget import BudgetManager
from src.generation.cache import CacheManager
from src.generation.concurrency import ConcurrencyManager
from src.generation.events import GenerationEventEmitter, GenerationEvents
from src.generation.executor import GenerationExecutor
from src.generation.health import ProviderHealthMonitor
from src.generation.manifest import AssetManifestBuilder
from src.generation.orchestrator import GenerationOrchestrator
from src.generation.provider_selection import ProviderSelectionEngine
from src.generation.quality import QualityEngine
from src.generation.queue_manager import QueueManager
from src.generation.schema import (
    AssetCategory,
    AssetManifest,
    BudgetEstimate,
    BudgetStatus,
    CacheEntry,
    CacheKey,
    GeneratedAsset,
    GenerationJob,
    GenerationMode,
    GenerationProgress,
    GenerationRequest,
    GenerationStrategy,
    JobPriority,
    JobStatus,
    ProviderHealthMetrics,
    QualityResult,
    SceneAssetManifest,
    ValidationReport,
    ValidationResult,
    ValidationStage,
)
from src.generation.strategy import GenerationStrategyEngine
from src.generation.subtitle import SubtitleGenerator
from src.generation.thumbnail import ThumbnailGenerator
from src.generation.validation import ValidationPipeline
