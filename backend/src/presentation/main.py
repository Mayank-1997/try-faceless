"""FastAPI application factory and lifespan management.

This is the single entry point for the ASGI server (uvicorn).

Responsibilities:
- Configure structured logging on startup.
- Initialise database engine and Redis connection.
- Register all routers, middleware, and exception handlers.
- Gracefully dispose resources on shutdown.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.di.container import ServiceContainer
from src.application.services.token_service import TokenService
from src.core.config_service import ConfigService
from src.core.exceptions import AppError
from src.core.logging import configure_logging, get_logger
from src.presentation.handlers.auth_handlers import app_error_handler
from src.presentation.middleware.auth import AuthMiddleware
from src.presentation.middleware.correlation import CorrelationIdMiddleware
from src.presentation.routers.api_keys import router as api_keys_router
from src.presentation.routers.auth import router as auth_router
from src.presentation.routers.projects import router as projects_router
from src.presentation.routers.sessions import router as sessions_router
from src.presentation.routers.production import router as production_router
from src.presentation.routers.platform import router as platform_router
from src.presentation.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown logic."""
    config = ConfigService()
    configure_logging()
    logger = get_logger(__name__)

    logger.info(
        "application_starting",
        app=config.app_name,
        env=config.environment,
        port=config.settings.port,
    )

    # Validate configuration
    issues = config.validate()
    for issue in issues:
        logger.warning("config_issue", issue=issue)

    # --- Initialise service container ---
    container = ServiceContainer(config=config)
    await container.initialize()
    app.state.container = container
    app.state.config = config

    logger.info("service_container_initialized")

    # --- Database: verify connectivity & auto-create tables (SQLite dev mode) ---
    from src.infrastructure.database.engine import engine, dispose_engine, AsyncSessionLocal

    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("SELECT 1"))

        # Auto-create tables in development mode
        if config.is_development:
            import src.persistence.models  # noqa: F401 — ensure all models are imported
            from src.persistence.models.base import Base
            await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")

    logger.info("database_connected", host=config.database.host)

    # --- Seed default roles and permissions ---
    from src.application.services.role_service import RolePermissionSeeder

    async with AsyncSessionLocal() as session:
        await RolePermissionSeeder.seed_defaults(session)
        await session.commit()
    logger.info("default_roles_seeded")

    # --- Verify Redis connectivity (optional in dev mode) ---
    from src.infrastructure.cache.redis_client import get_redis_client, close_redis

    try:
        redis = get_redis_client()
        await redis.ping()
        logger.info("redis_connected", host=config.redis.host)
    except Exception as exc:
        logger.warning("redis_not_available", error=str(exc))

    yield

    # --- Shutdown ---
    logger.info("application_stopping")
    await container.shutdown()
    await dispose_engine()
    try:
        await close_redis()
    except Exception:
        pass
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Application factory — builds and returns the configured FastAPI app."""
    config = ConfigService()

    app = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="Autonomous AI-powered YouTube Content Studio API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: correlation ID first) ---
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Auth middleware ---
    token_service = TokenService()
    app.add_middleware(AuthMiddleware, token_service=token_service)

    # --- Routers ---
    app.include_router(auth_router, prefix=config.api_prefix)
    app.include_router(users_router, prefix=config.api_prefix)
    app.include_router(api_keys_router, prefix=config.api_prefix)
    app.include_router(sessions_router, prefix=config.api_prefix)
    app.include_router(projects_router, prefix=config.api_prefix)
    app.include_router(production_router, prefix=config.api_prefix)
    app.include_router(platform_router, prefix=config.api_prefix)

    # --- Exception handlers ---
    app.add_exception_handler(AppError, app_error_handler)

    # --- Health check ---
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "app": config.app_name}

    return app


app = create_app()
