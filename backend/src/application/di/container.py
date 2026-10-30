"""Dependency injection container — central registry of all service instances.

The ``ServiceContainer`` is the single place where all services are
constructed and wired together.  It replaces module-level globals and
singletons with a controlled, testable container.

Design principles:
- **Single construction point**: each service is created once and shared.
- **Explicit dependencies**: services declare their dependencies in
  ``__init__``, making the wiring graph visible.
- **Testability**: in tests, individual services can be replaced with
  mocks by setting them on the container.
- **Lifecycle management**: ``initialize()`` starts all services,
  ``shutdown()`` cleans them up.

Usage::

    container = ServiceContainer()
    await container.initialize()

    # Access services
    llm = container.llm_gateway
    storage = container.storage_gateway

    # In FastAPI:
    from src.application.di.dependencies import get_container
    @app.get("/")
    async def handler(container: ServiceContainer = Depends(get_container)):
        ...
"""

from __future__ import annotations

from typing import Any

from src.core.config_service import ConfigService
from src.core.exceptions import ConfigurationError
from src.core.logging import get_logger


class ServiceContainer:
    """Central dependency injection container for all application services.

    Holds references to every shared service instance.  Services are
    lazily initialised on first access or eagerly initialised via
    ``initialize()``.

    Attributes are populated after ``initialize()`` is called.  Before
    that, they are ``None``.
    """

    def __init__(self, config: ConfigService | None = None) -> None:
        """Create the container with optional custom configuration.

        Args:
            config: Optional ``ConfigService`` instance. If ``None``,
                a default one is created from environment variables.
        """
        self.config = config or ConfigService()
        self._logger = get_logger(__name__)
        self._initialized = False

        # Service instances — populated by ``initialize()``
        self.llm_gateway: Any = None
        self.image_gateway: Any = None
        self.video_gateway: Any = None
        self.voice_gateway: Any = None
        self.rendering_gateway: Any = None
        self.storage_gateway: Any = None
        self.prompt_manager: Any = None
        self.cost_tracker: Any = None
        self.token_tracker: Any = None
        self.event_bus: Any = None
        self.metrics_collector: Any = None
        self.langfuse_client: Any = None
        self.prompt_executor: Any = None
        self.provider_registry: Any = None

    async def initialize(self) -> None:
        """Eagerly initialise all services in dependency order.

        Services are initialised in a specific order to ensure
        dependencies are available:
        1. Infrastructure (storage, observability)
        2. AI layer (providers, gateways, prompts)
        3. Application services (cost, tokens, events)
        """
        if self._initialized:
            self._logger.warning("container_already_initialized")
            return

        self._logger.info("container_initializing")

        # --- 1. Infrastructure ---
        await self._init_storage()
        await self._init_observability()
        await self._init_langfuse_client()

        # --- 2. AI layer ---
        await self._init_provider_registry()
        await self._init_prompt_manager()
        await self._init_gateways()
        await self._init_prompt_executor()

        # --- 3. Application services ---
        await self._init_cost_tracker()
        await self._init_token_tracker()
        await self._init_event_bus()

        self._initialized = True
        self._logger.info("container_initialized")

    async def shutdown(self) -> None:
        """Shut down all services in reverse dependency order."""
        if not self._initialized:
            return

        self._logger.info("container_shutting_down")

        # Shut down in reverse order
        for attr_name in [
            "event_bus", "token_tracker", "cost_tracker",
            "llm_gateway", "image_gateway", "video_gateway", "voice_gateway",
            "rendering_gateway", "prompt_executor", "prompt_manager", "provider_registry",
            "storage_gateway", "langfuse_client", "metrics_collector",
        ]:
            service = getattr(self, attr_name)
            if service is not None and hasattr(service, "shutdown"):
                try:
                    await service.shutdown()
                except Exception as exc:
                    self._logger.error(
                        "service_shutdown_error",
                        service=attr_name,
                        error=str(exc),
                    )
            setattr(self, attr_name, None)

        self._initialized = False
        self._logger.info("container_shutdown_complete")

    # -----------------------------------------------------------------------
    # Initialisation helpers — each creates its service and stores it
    # -----------------------------------------------------------------------
    async def _init_storage(self) -> None:
        from src.infrastructure.storage.gateway import StorageGateway
        from src.infrastructure.storage.local import LocalStorageProvider

        if self.config.storage.type == "local":
            provider = LocalStorageProvider()
            await provider.initialize(
                _make_provider_config(
                    api_key="",
                    model="local",
                    extra={"base_path": self.config.storage.local_path},
                )
            )
            self.storage_gateway = StorageGateway(provider)
            await self.storage_gateway.initialize()
        else:
            self._logger.warning(
                "storage_provider_not_implemented",
                provider=self.config.storage.type,
            )

    async def _init_observability(self) -> None:
        from src.infrastructure.observability.metrics import MetricsCollector

        self.metrics_collector = MetricsCollector(self.config)

    async def _init_langfuse_client(self) -> None:
        from src.infrastructure.observability.langfuse_client import LangfuseClient

        self.langfuse_client = LangfuseClient(self.config)

    async def _init_provider_registry(self) -> None:
        from src.ai.providers.registry import ProviderRegistry

        self.provider_registry = ProviderRegistry(self.config)
        await self.provider_registry.initialize()

    async def _init_prompt_manager(self) -> None:
        from src.ai.prompts.prompt_manager import PromptManager

        self.prompt_manager = PromptManager()
        await self.prompt_manager.initialize()

    async def _init_gateways(self) -> None:
        from src.ai.gateway.llm_gateway import LLMGateway
        from src.ai.gateway.image_gateway import ImageGateway
        from src.ai.gateway.video_gateway import VideoGateway
        from src.ai.gateway.voice_gateway import VoiceGateway
        from src.rendering.gateway import RenderingGateway

        self.llm_gateway = LLMGateway(
            registry=self.provider_registry,
            config=self.config,
            langfuse_client=self.langfuse_client,
        )
        await self.llm_gateway.initialize()

        self.image_gateway = ImageGateway(
            registry=self.provider_registry,
            config=self.config,
            langfuse_client=self.langfuse_client,
        )
        await self.image_gateway.initialize()

        self.video_gateway = VideoGateway(
            registry=self.provider_registry,
            config=self.config,
            langfuse_client=self.langfuse_client,
        )
        await self.video_gateway.initialize()

        self.voice_gateway = VoiceGateway(
            registry=self.provider_registry,
            config=self.config,
        )
        await self.voice_gateway.initialize()

        self.rendering_gateway = RenderingGateway(self.config)
        await self.rendering_gateway.initialize()

    async def _init_prompt_executor(self) -> None:
        from src.ai.agents.prompt_executor import PromptExecutor

        self.prompt_executor = PromptExecutor(
            llm_gateway=self.llm_gateway,
            prompt_manager=self.prompt_manager,
            langfuse_client=self.langfuse_client,
        )

    async def _init_cost_tracker(self) -> None:
        from src.application.services.cost_tracker import CostTracker

        self.cost_tracker = CostTracker(self.config)

    async def _init_token_tracker(self) -> None:
        from src.application.services.token_tracker import TokenTracker

        self.token_tracker = TokenTracker(self.config)

    async def _init_event_bus(self) -> None:
        from src.application.services.event_bus import EventBus

        self.event_bus = EventBus()
        await self.event_bus.initialize()

    # -----------------------------------------------------------------------
    # Service access with null checks
    # -----------------------------------------------------------------------
    def get_service(self, name: str) -> Any:
        """Get a service by name.

        Args:
            name: The attribute name of the service on the container.

        Returns:
            The service instance.

        Raises:
            ConfigurationError: If the service is not initialised.
        """
        service = getattr(self, name, None)
        if service is None:
            raise ConfigurationError(
                f"Service '{name}' is not initialised. "
                "Call 'await container.initialize()' first."
            )
        return service

    @property
    def is_initialized(self) -> bool:
        return self._initialized


def _make_provider_config(
    *,
    api_key: str,
    model: str,
    max_retries: int = 3,
    request_timeout: int = 120,
    extra: dict[str, Any] | None = None,
):
    """Helper to create a ``ProviderConfig`` without importing at module level."""
    from src.core.interfaces import ProviderConfig

    return ProviderConfig(
        api_key=api_key,
        model=model,
        max_retries=max_retries,
        request_timeout=request_timeout,
        extra=extra or {},
    )
