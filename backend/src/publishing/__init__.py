"""Publishing & Distribution Platform — Phase 11.

Distributes generated content to multiple destinations.

Pipeline:
    ProjectPackage → PublishingPlanner → PublishingPlan
    → PublishingStrategyEngine → PublishingQueue
    → Publisher (YouTube, LinkedIn, ...) → PublishingReport

The Publisher interface is provider-independent.
New platforms can be added by implementing the Publisher ABC.
"""

from __future__ import annotations

# Schema
from src.publishing.schema import (
    AuthCredential,
    AuthMethod,
    FailoverStrategy,
    PlatformConfig,
    PlatformRequirements,
    PublishingJob,
    PublishingJobStatus,
    PublishingMetadata,
    PublishingMetrics,
    PublishingMode,
    PublishingPlatform,
    PublishingPlan,
    PublishingPriority,
    PublishingProgress,
    PublishingReport,
    PublishingStrategy,
    PublishingTask,
    RetryStrategy,
    ScheduleConfig,
    ThumbnailFormat,
    ThumbnailSpec,
    YouTubeCategory,
    YouTubeLicense,
)

# Events
from src.publishing.events import PublishingEventEmitter, PublishingEvents

# Publisher interface
from src.publishing.publisher import Publisher

# Components
from src.publishing.auth import AuthenticationManager
from src.publishing.metadata import MetadataEngine
from src.publishing.thumbnail import ThumbnailManager
from src.publishing.validator import PublishingValidator
from src.publishing.youtube import YouTubePublisher
from src.publishing.planner import PublishingPlanner
from src.publishing.strategy import PublishingStrategyEngine
from src.publishing.queue import PublishingQueue
from src.publishing.scheduler import SchedulingEngine
from src.publishing.progress import ProgressTracker

__all__ = [
    # Schema
    "AuthCredential",
    "AuthMethod",
    "FailoverStrategy",
    "PlatformConfig",
    "PlatformRequirements",
    "PublishingJob",
    "PublishingJobStatus",
    "PublishingMetadata",
    "PublishingMetrics",
    "PublishingMode",
    "PublishingPlatform",
    "PublishingPlan",
    "PublishingPriority",
    "PublishingProgress",
    "PublishingReport",
    "PublishingStrategy",
    "PublishingTask",
    "RetryStrategy",
    "ScheduleConfig",
    "ThumbnailFormat",
    "ThumbnailSpec",
    "YouTubeCategory",
    "YouTubeLicense",
    # Events
    "PublishingEventEmitter",
    "PublishingEvents",
    # Publisher interface
    "Publisher",
    # Components
    "AuthenticationManager",
    "MetadataEngine",
    "ThumbnailManager",
    "PublishingValidator",
    "YouTubePublisher",
    "PublishingPlanner",
    "PublishingStrategyEngine",
    "PublishingQueue",
    "SchedulingEngine",
    "ProgressTracker",
]
