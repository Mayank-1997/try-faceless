"""Celery tasks for end-to-end video workflow execution.

This task now drives the real research, script, storyboard and scene
planning workflows using the underlying agent graphs. It persists the
produced packages back to the database so the UI displays genuine
workflow outputs. Asset, voice, subtitle, rendering, thumbnail, SEO,
and publishing steps are now wired into the pipeline.

All logs for a single workflow run are also mirrored to a per-project
text file under ``storage/projects/<project_id>/logs/`` so they can be
inspected on the host without reading Docker container logs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from src.application.services.project_service import ProjectService

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.research.workflow import ResearchWorkflowGraph
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.script.workflow import ScriptWorkflowGraph
from src.ai.agents.storyboard.schema import (
    AnimationPlan,
    AnimationPlanResult,
    AssetDecisionResult,
    AssetSceneDecision,
    PlannedScene,
    CameraPlan,
    CameraPlanResult,
    ContinuityResult,
    ScenePackage,
    SceneSegmentationResult,
    StoryAnalysis,
    StoryBeatResult,
    StoryboardPackage,
    StoryboardQualityEvaluation,
    StoryboardReviewResult,
    VisualPlan,
    VisualStoryboardResult,
)
from src.ai.agents.storyboard.workflow import StoryboardWorkflowGraph
from src.application.di.container import ServiceContainer
from src.application.services.direct_cinematic import (
    MAX_KLING_PROMPT_CHARS,
    MAX_VEO_PROMPT_CHARS,
    _active_video_provider,
    direct_clip_prompt,
    max_direct_prompt_chars,
    plan_direct_segments,
)
from src.composition.builder import CompositionBuilder
from src.composition.ffmpeg_renderer import FFmpegCompositionRenderer
from src.composition.pipeline import RenderingPipeline
from src.composition.schema import (
    ExportProfile,
    ProjectPackage,
    QualityReport,
    RenderMetrics,
    TimelineClip,
    TrackType,
)
from src.core.config import get_settings
from src.core.enums import (
    AgentType,
    AIProvider,
    AssetGenerationStatus,
    AssetStatus,
    AssetType,
    CameraAngle,
    CameraMotion,
    JobStatus as WorkflowJobStatus,
    ProjectInputType,
    ResearchStatus,
    SceneGenerationStatus,
    SceneReviewStatus,
    ScriptStatus,
    StorageType,
    StoryboardStatus,
    TransitionType,
    VisualType,
    WorkflowStep,
)
from src.core.interfaces import ImageProvider, LLMProvider, VideoProvider
from src.core.logging import get_logger
from src.domain.entities.asset import ImageAsset, ThumbnailAsset, VideoAsset, VoiceAsset
from src.domain.entities.research import Research
from src.domain.entities.scene import Scene
from src.domain.entities.script import Script
from src.domain.entities.storyboard import Storyboard
from src.generation.schema import (
    AssetCategory,
    AssetManifest,
    GeneratedAsset,
    JobStatus,
    SceneAssetManifest,
)
from src.infrastructure.tasks.celery_app import celery_app
from src.workflow.engine import WorkflowEngine
from src.workflow.state import (
    AssetData,
    ProjectInfo,
    RenderingData,
    ResearchData,
    ResearchSource,
    SceneData,
    ScriptData,
    SEOData,
    StoryboardData,
    TopicData,
    VoiceData,
    WorkflowState,
)

_logger = get_logger(__name__)

# Delay between steps so the frontend polling can observe each transition.
_STEP_DELAY_SECONDS = 3.0


def _now() -> datetime:
    return datetime.now(UTC)


def _create_placeholder_png(width: int = 1920, height: int = 1080, rgb: tuple = (26, 26, 46)) -> bytes:
    """Create a minimal solid-color PNG (no external dependencies).

    Used as a visual placeholder for scenes whose asset type is not
    supported by the stock/AI providers (e.g. ``animation_only``,
    ``chart``, ``diagram``, ``mixed_assets``).
    """
    signature = b"\x89PNG\r\n\x1a\n"

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    idat = zlib.compress(raw, 9)

    return signature + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


# Placeholder palette — cycle through muted colors so adjacent scenes differ
_PLACEHOLDER_COLORS = [
    (26, 26, 46),
    (30, 42, 60),
    (22, 38, 52),
    (34, 34, 58),
    (28, 32, 54),
]


# ---------------------------------------------------------------------------
# Per-project file logging
# ---------------------------------------------------------------------------
_PROJECT_LOG_HANDLER_NAME = "project_file_handler"


def _get_project_log_path(project_id: UUID, workflow_id: UUID) -> Path:
    """Return the local log file path for a workflow run."""
    settings = get_settings()
    log_dir = Path(settings.storage.local_path) / "projects" / str(project_id) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"workflow_{workflow_id}.txt"


def _attach_project_log_handler(project_id: UUID, workflow_id: UUID) -> logging.Handler | None:
    """Attach a file handler to the root logger so all workflow logs
    (structlog + stdlib) are mirrored to a per-project text file.

    Returns the handler so it can be detached later, or ``None`` on failure.
    """
    try:
        log_path = _get_project_log_path(project_id, workflow_id)
        handler = logging.FileHandler(
            filename=str(log_path),
            mode="a",
            encoding="utf-8",
        )
        handler.set_name(_PROJECT_LOG_HANDLER_NAME)
        # structlog renders the message; just pass it through with a newline.
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.DEBUG)

        root = logging.getLogger()
        # Ensure the root logger level doesn't filter out messages before
        # they reach the file handler (default stdlib level is WARNING).
        if root.level > logging.DEBUG:
            root.setLevel(logging.DEBUG)
        root.addHandler(handler)

        # Write a header so the file is self-describing
        header = (
            f"\n{'='*70}\n"
            f"WORKFLOW LOG\n"
            f"  project_id:  {project_id}\n"
            f"  workflow_id: {workflow_id}\n"
            f"  started_at:  {_now().isoformat()}\n"
            f"  log_file:    {log_path}\n"
            f"{'='*70}\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(header)

        _logger.info(
            "project_log_file_attached",
            project_id=str(project_id),
            workflow_id=str(workflow_id),
            log_file=str(log_path),
        )
        return handler
    except Exception as exc:
        _logger.warning("project_log_file_setup_failed", error=str(exc))
        return None


def _detach_project_log_handler(handler: logging.Handler | None, project_id: UUID, workflow_id: UUID) -> None:
    """Detach and close the per-project file handler."""
    if handler is None:
        return
    try:
        root = logging.getLogger()
        root.removeHandler(handler)
        handler.flush()
        handler.close()

        footer = (
            f"\n{'='*70}\n"
            f"WORKFLOW ENDED  finished_at={_now().isoformat()}\n"
            f"{'='*70}\n"
        )
        log_path = _get_project_log_path(project_id, workflow_id)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(footer)
    except Exception as exc:
        _logger.warning("project_log_file_detach_failed", error=str(exc))


async def _hydrate_workflow_state(
    workflow_state: WorkflowState,
    service: "ProjectService",
    project,
    workflow_id: UUID,
) -> None:
    """Populate canonical state fields from repository records.

    The LangGraph agents write their outputs into ``state.research.metadata``,
    ``state.script.metadata``, etc.  This helper loads the persisted entities
    and copies their data into the top-level state fields so the exported
    ``workflow_state.json`` is complete and JSON-safe.
    """
    try:
        workflow_state.project.name = project.title or workflow_state.project.name
        if project.status:
            workflow_state.project.status = project.status
    except Exception:
        pass

    try:
        research = await service._research_repo.get_latest_version(project.id)
        if research:
            sources: list[ResearchSource] = []
            for src in research.sources or []:
                if isinstance(src, dict):
                    sources.append(ResearchSource.model_validate(src))
                elif isinstance(src, str):
                    sources.append(ResearchSource(url=src, title=src))
                else:
                    try:
                        sources.append(ResearchSource.model_validate(src))
                    except Exception:
                        pass
            workflow_state.research = ResearchData(
                query=project.title or "",
                sources=sources,
                key_facts=research.interesting_facts or [],
                summary=research.summary or "",
                keywords=research.keywords or [],
                metadata={"references": research.references or []},
            )
    except Exception as exc:
        _logger.warning("hydrate_research_failed", error=str(exc))

    try:
        script = await service._script_repo.get_latest_version(project.id)
        if script:
            workflow_state.script = ScriptData(
                title=project.title or "",
                content=script.body or "",
                hook=script.hook or "",
                body=script.body or "",
                outro=script.cta or "",
                word_count=script.word_count or 0,
                estimated_duration_seconds=script.estimated_duration_seconds or 0,
            )
    except Exception as exc:
        _logger.warning("hydrate_script_failed", error=str(exc))

    try:
        storyboard = await service._storyboard_repo.get_latest_version(project.id)
        if storyboard:
            beats: list[str] = []
            storyboard_package: dict | None = None
            if storyboard.package_json:
                try:
                    pkg = json.loads(storyboard.package_json)
                    beats = [sp.get("title", "") for sp in pkg.get("scene_packages", []) if sp.get("title")]
                    storyboard_package = pkg
                except Exception:
                    pass
            # Preserve the storyboard_package in metadata so downstream steps
            # (asset/voice/subtitle generation) can read scene narrations from it.
            # Hydration rebuilds the storyboard object from DB entities, which would
            # otherwise wipe the storyboard_package that storyboard_review.py set.
            metadata: dict[str, Any] = {}
            if storyboard_package:
                metadata["storyboard_package"] = storyboard_package
            workflow_state.storyboard = StoryboardData(
                narrative_structure=storyboard.narrative_structure or "",
                act_count=len(beats) or (storyboard.scene_count or 0),
                beats=beats,
                pacing_notes=storyboard.pacing_notes or "",
                metadata=metadata,
            )
    except Exception as exc:
        _logger.warning("hydrate_storyboard_failed", error=str(exc))

    try:
        scenes = [
            s for s in await service._scene_repo.get_by_project(project.id)
            if getattr(s, "workflow_id", workflow_id) == workflow_id
        ]
        scene_data: list[SceneData] = []
        for scene in scenes:
            scene_data.append(
                SceneData(
                    scene_number=scene.scene_number or 0,
                    title=scene.title or "",
                    narration=scene.narration or "",
                    estimated_duration=scene.duration_seconds or 0.0,
                    visual_type=scene.visual_type,
                    camera_angle=scene.camera_angle,
                    camera_motion=scene.camera_motion,
                    lens=scene.lens or None,
                    lighting=scene.lighting or None,
                    composition=scene.composition or None,
                    emotion=scene.emotion or None,
                    transition=scene.transition,
                    subtitle_text=scene.subtitle or None,
                    voice_timing=scene.voice_timing or None,
                    sound_effects=scene.sound_effects or [],
                )
            )
        workflow_state.scenes = scene_data
    except Exception as exc:
        _logger.warning("hydrate_scenes_failed", error=str(exc))

    try:
        scene_ids = {s.id for s in scenes} if "scenes" in locals() else set()
        assets = [
            a for a in await service._asset_repo.get_by_project(project.id)
            if a.scene_id in scene_ids
        ]
        asset_data: list[AssetData] = []
        scene_by_id = {str(s.id): s.scene_number for s in scenes} if "scenes" in locals() else {}
        for asset in assets:
            if isinstance(asset, ImageAsset):
                file_path = asset.storage_ref or ""
            elif isinstance(asset, VideoAsset):
                file_path = asset.storage_ref or ""
            elif isinstance(asset, VoiceAsset):
                file_path = asset.storage_ref or ""
            elif isinstance(asset, ThumbnailAsset):
                file_path = asset.storage_ref or ""
            else:
                file_path = getattr(asset, "storage_ref", "")

            file_size = 0
            if file_path.startswith("local://"):
                try:
                    file_size = os.path.getsize(file_path.replace("local://", "", 1))
                except Exception:
                    pass

            status = AssetStatus.READY if asset.is_ready else AssetStatus.PLANNED
            if getattr(asset, "generation_status", None) and str(asset.generation_status) == "failed":
                status = AssetStatus.FAILED

            provider = asset.provider
            if hasattr(provider, "value"):
                provider = provider.value
            provider = str(provider or "")

            asset_type = asset.asset_type
            if isinstance(asset_type, str):
                try:
                    asset_type = AssetType(asset_type)
                except ValueError:
                    asset_type = AssetType.IMAGE

            asset_data.append(
                AssetData(
                    asset_id=asset.id,
                    scene_number=scene_by_id.get(str(asset.scene_id)),
                    asset_type=asset_type,
                    status=status,
                    provider=provider,
                    file_path=file_path,
                    storage_uri=file_path,
                    file_size_bytes=file_size,
                    cost_usd=asset.generation_cost_usd or 0.0,
                    quality_score=asset.quality_score or 0.0,
                    version=1,
                    generation_metadata={
                        "generation_time_seconds": asset.generation_time_seconds or 0.0,
                        "storage_type": getattr(asset, "storage_type", ""),
                    },
                )
            )
        workflow_state.assets = asset_data

        # Roll per-asset generation spend into the running cost summary so
        # the exported state reflects image/video/voice costs as well as
        # LLM calls.
        cost_by_type: dict[str, float] = {}
        for asset in assets:
            atype = getattr(asset, "asset_type", None)
            atype = atype.value if hasattr(atype, "value") else str(atype or "")
            cost_by_type[atype] = cost_by_type.get(atype, 0.0) + float(
                asset.generation_cost_usd or 0
            )
        workflow_state.cost.image_cost_usd = cost_by_type.get(AssetType.IMAGE.value, 0.0)
        workflow_state.cost.video_cost_usd = cost_by_type.get(AssetType.VIDEO.value, 0.0)
        workflow_state.cost.voice_cost_usd = cost_by_type.get(AssetType.VOICE.value, 0.0)
        workflow_state.cost.total_cost_usd = (
            workflow_state.cost.llm_cost_usd
            + workflow_state.cost.image_cost_usd
            + workflow_state.cost.video_cost_usd
            + workflow_state.cost.voice_cost_usd
            + workflow_state.cost.render_cost_usd
        )

        voice_assets = [a for a in assets if isinstance(a, VoiceAsset)]
        if voice_assets:
            first = voice_assets[0]
            workflow_state.voice = VoiceData(
                language=first.language or "en-US",
                voice_name=first.voice_name or "",
                total_duration_seconds=sum(float(a.duration_seconds or 0) for a in voice_assets),
                total_cost_usd=sum(float(a.generation_cost_usd or 0) for a in voice_assets),
            )
    except Exception as exc:
        _logger.warning("hydrate_assets_failed", error=str(exc))

    try:
        final_video_path = workflow_state.metadata.custom.get("final_video_path", "")
        render_report = workflow_state.metadata.custom.get("render_report", {})
        if final_video_path:
            status = WorkflowJobStatus.COMPLETED if os.path.isfile(final_video_path) else WorkflowJobStatus.FAILED
            file_size = render_report.get("output_size_bytes", 0)
            if not file_size and os.path.isfile(final_video_path):
                try:
                    file_size = os.path.getsize(final_video_path)
                except Exception:
                    pass
            duration = render_report.get("output_duration_seconds", 0.0)
            if not duration:
                try:
                    duration = float(sum(s.estimated_duration or 0 for s in workflow_state.scenes))
                except Exception:
                    pass
            workflow_state.rendering = RenderingData(
                status=status,
                output_path=final_video_path,
                file_size_bytes=file_size,
                duration_seconds=duration,
                resolution=render_report.get("output_resolution", "1920x1080"),
                fps=render_report.get("output_fps", 30),
                render_time_seconds=render_report.get("render_time_seconds", 0.0),
            )
    except Exception as exc:
        _logger.warning("hydrate_rendering_failed", error=str(exc))

    try:
        seo_payload = workflow_state.metadata.custom.get("seo", {})
        if seo_payload:
            workflow_state.seo = SEOData(
                title=seo_payload.get("title", ""),
                description=seo_payload.get("description", ""),
                tags=seo_payload.get("tags", []),
                keywords=seo_payload.get("keywords", []),
                category=seo_payload.get("category", ""),
            )
    except Exception as exc:
        _logger.warning("hydrate_seo_failed", error=str(exc))


async def _save_workflow_state(
    workflow_state: WorkflowState,
    container: ServiceContainer,
    project_id: UUID,
    workflow_id: UUID,
) -> str:
    """Serialize and persist the full WorkflowState for later download."""
    if not getattr(container, "storage_gateway", None):
        _logger.warning("storage_gateway_not_available", project_id=str(project_id))
        return ""

    state_key = f"workflow_state/{project_id}/{workflow_id}/workflow_state.json"
    try:
        data = workflow_state.model_dump_json(indent=2, exclude_none=False).encode("utf-8")
        uri = await container.storage_gateway.upload(
            data, state_key, content_type="application/json"
        )
        _logger.info(
            "workflow_state_saved",
            project_id=str(project_id),
            workflow_id=str(workflow_id),
            key=state_key,
            uri=uri,
            size_bytes=len(data),
        )
        return state_key
    except Exception as exc:
        _logger.error("workflow_state_save_failed", project_id=str(project_id), error=str(exc))
        return ""


@celery_app.task(name="src.infrastructure.tasks.workflow_tasks.execute_workflow_task")
def execute_workflow_task(project_id: str, workflow_id: str) -> None:
    """Run all workflow steps for a project and persist outputs."""
    return asyncio.run(_run_workflow(UUID(project_id), UUID(workflow_id)))


async def _run_workflow(project_id: UUID, workflow_id: UUID) -> None:
    # Lazy import avoids circular imports with project_service.
    from src.application.services.project_service import ProjectService

    # asyncpg connections are bound to the event loop that created them, and
    # Celery worker processes reuse module state across tasks. Instead of
    # sharing the app's global engine (whose pooled connections belong to a
    # different loop, causing "attached to a different loop" / "Event loop is
    # closed" errors), create a dedicated engine bound to *this* task's loop
    # and dispose it when we're done.
    settings = get_settings()
    is_sqlite = settings.database.url.startswith("sqlite")
    engine_kwargs: dict = {"echo": settings.database.echo, "pool_pre_ping": not is_sqlite}
    if not is_sqlite:
        engine_kwargs["pool_recycle"] = 3600
    task_engine = create_async_engine(settings.database.url, **engine_kwargs)
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    container = ServiceContainer()
    langfuse = None
    langfuse_trace_id: str | None = None
    project_log_handler = _attach_project_log_handler(project_id, workflow_id)

    try:
        async with session_factory() as session:
            try:
                service = ProjectService(session)
                project = await service._project_repo.get_by_id(project_id)
                if project is None:
                    raise ValueError(f"Project {project_id} not found")

                await container.initialize()
                llm_count = len(container.provider_registry.get_providers_by_type(LLMProvider))
                if llm_count == 0 and not _is_direct_cinematic(project):
                    raise ValueError(
                        "No LLM provider is configured. Set GEMINI_API_KEY in your "
                        "environment to run the real workflow."
                    )

                engine = WorkflowEngine()
                engine.register_workflow(ResearchWorkflowGraph())
                engine.register_workflow(ScriptWorkflowGraph())
                engine.register_workflow(StoryboardWorkflowGraph())

                workflow_state = _build_initial_state(project)

                # One Langfuse trace per workflow trigger. session_id groups
                # everything for this run; agents attach their generations to
                # this trace via state.metadata.custom["langfuse_trace_id"].
                langfuse = getattr(container, "langfuse_client", None)
                if langfuse is not None:
                    langfuse_trace_id = langfuse.start_trace(
                        name=f"workflow: {project.title}",
                        user_id=str(project.owner_id) if project.owner_id else None,
                        session_id=str(workflow_id),
                        metadata={
                            "project_id": str(project_id),
                            "workflow_id": str(workflow_id),
                            "trigger": "ui",
                            "started_at": _now().isoformat(),
                        },
                    )
                if langfuse_trace_id:
                    workflow_state.metadata.custom["langfuse_trace_id"] = langfuse_trace_id

                current_step = WorkflowStep.INITIALIZATION.value

                while current_step != WorkflowStep.COMPLETED.value:
                    response = await service.advance_workflow(project_id)
                    current_step = response.current_step

                    if current_step == WorkflowStep.COMPLETED.value:
                        await session.commit()

                        # Hydrate the top-level state fields (including the
                        # asset cost rollup) BEFORE logging/tracing so the
                        # reported totals include generated media spend.
                        await _hydrate_workflow_state(workflow_state, service, project, workflow_id)

                        _logger.info(
                            "workflow_finished",
                            project_id=str(project_id),
                            workflow_id=str(workflow_id),
                            total_cost_usd=workflow_state.cost.total_cost_usd,
                            total_tokens=workflow_state.token_usage.total_tokens,
                        )

                        if langfuse is not None and langfuse_trace_id:
                            langfuse.update_trace(
                                trace_id=langfuse_trace_id,
                                output={
                                    "status": "completed",
                                    "final_video_path": workflow_state.metadata.custom.get(
                                        "final_video_path", ""
                                    ),
                                    "thumbnail_uri": workflow_state.metadata.custom.get(
                                        "thumbnail_uri", ""
                                    ),
                                    "total_cost_usd": workflow_state.cost.total_cost_usd,
                                    "total_tokens": workflow_state.token_usage.total_tokens,
                                },
                                metadata={"finished_at": _now().isoformat()},
                            )

                        # Persist the full WorkflowState so the download endpoint
                        # can return it as workflow_state.json.
                        state_key = await _save_workflow_state(
                            workflow_state, container, project_id, workflow_id
                        )
                        if state_key:
                            workflow = await service._workflow_repo.get_by_id(workflow_id)
                            if workflow:
                                workflow.save_checkpoint(state_key)
                                await service._workflow_repo.update(workflow)
                                await session.commit()

                        break

                    _logger.info(
                        "workflow_running_step",
                        project_id=str(project_id),
                        workflow_id=str(workflow_id),
                        step=current_step,
                    )

                    step_started_at = _now()
                    workflow_state = await _create_step_output(
                        service=service,
                        engine=engine,
                        container=container,
                        workflow_state=workflow_state,
                        project=project,
                        workflow_id=workflow_id,
                        step=current_step,
                    )
                    if langfuse is not None and langfuse_trace_id:
                        step_input = workflow_state.metadata.custom.get("step_input", {})
                        step_output = workflow_state.metadata.custom.get("step_output", {})
                        langfuse.span(
                            trace_id=langfuse_trace_id,
                            name=f"step: {current_step}",
                            start_time=step_started_at,
                            end_time=_now(),
                            input_content=step_input,
                            output_content=step_output,
                            metadata={
                                "project_id": str(project_id),
                                "workflow_id": str(workflow_id),
                            },
                        )
                    # Commit each transition immediately so the UI polling can
                    # observe the new step before we sleep.
                    await session.commit()

                    # Persist the full state at every step boundary so a failed
                    # workflow still leaves a checkpoint for debugging (the same
                    # key is overwritten each step, so the file always reflects
                    # the latest completed step).
                    state_key = await _save_workflow_state(
                        workflow_state, container, project_id, workflow_id
                    )
                    if state_key:
                        workflow_row = await service._workflow_repo.get_by_id(workflow_id)
                        if workflow_row:
                            workflow_row.save_checkpoint(state_key)
                            await service._workflow_repo.update(workflow_row)
                            await session.commit()

                    await asyncio.sleep(_STEP_DELAY_SECONDS)

            except Exception as exc:
                _logger.error(
                    "workflow_failed",
                    project_id=str(project_id),
                    workflow_id=str(workflow_id),
                    error=str(exc),
                )
                if langfuse is not None and langfuse_trace_id:
                    langfuse.update_trace(
                        trace_id=langfuse_trace_id,
                        output={"status": "failed", "error": str(exc)},
                        metadata={"failed_at": _now().isoformat()},
                    )
                # Persist the last-known state so a failed run still leaves a
                # checkpoint for debugging.
                state_key = await _save_workflow_state(
                    workflow_state, container, project_id, workflow_id
                )
                workflow = await service._workflow_repo.get_active_workflow(project_id)
                if workflow:
                    if state_key:
                        workflow.save_checkpoint(state_key)
                    workflow.fail(str(exc))
                    await service._workflow_repo.update(workflow)
                await session.commit()
                raise
    finally:
        _detach_project_log_handler(project_log_handler, project_id, workflow_id)
        await container.shutdown()
        await task_engine.dispose()


def _asset_to_generated_asset(asset) -> GeneratedAsset:
    """Convert a domain ``BaseAsset`` into a ``GeneratedAsset`` for the manifest."""
    asset_type_str = asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type)
    provider_str = asset.provider.value if hasattr(asset.provider, "value") else str(asset.provider)
    return GeneratedAsset(
        scene_id=str(asset.scene_id) if asset.scene_id else "",
        category=AssetCategory(asset_type_str),
        provider=provider_str,
        model="",
        storage_uri=asset.storage_ref,
        file_size_bytes=0,
        cost_usd=asset.generation_cost_usd,
        quality_score=asset.quality_score or 0.0,
        generation_time_seconds=asset.generation_time_seconds,
    )


def _find_generated_asset(
    scene_assets: list,
    asset_type: AssetType,
    category: AssetCategory,
) -> GeneratedAsset | None:
    """Find the first asset of a given type and convert it."""
    target = asset_type.value if hasattr(asset_type, "value") else str(asset_type)
    for asset in scene_assets:
        asset_type_value = asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type)
        if asset_type_value == target:
            return _asset_to_generated_asset(asset)
    return None


async def _render_composition_multi_pass(
    container: ServiceContainer,
    project,
    workflow_id: UUID,
    scenes: list,
    asset_by_scene: dict[str, list],
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> ProjectPackage:
    """Render each scene separately and concatenate with -c copy.

    This avoids the huge single-process FFmpeg filter graph that was being
    killed (OOM/timeouts) on long mixed-image/video sequences.
    """
    renderer = FFmpegCompositionRenderer(threads=2)
    pipeline = RenderingPipeline(renderer=renderer)
    parts_dir = os.path.join(
        container.config.storage.local_path,
        "projects",
        str(project.id),
        f".render_parts_{workflow_id}",
    )
    os.makedirs(parts_dir, exist_ok=True)

    part_files: list[str] = []
    total_render_time = 0.0
    total_duration = 0.0
    export_profile = ExportProfile(
        preset="ultrafast",
        resolution=f"{width}x{height}",
        width=width,
        height=height,
        fps=fps,
    )

    for scene in scenes:
        scene_id = str(scene.id)
        duration = float(scene.duration_seconds or 5)
        scene_assets = asset_by_scene.get(scene_id, [])
        sm = SceneAssetManifest(
            scene_id=scene_id,
            scene_number=scene.scene_number,
            estimated_render_time_seconds=duration,
            generation_status=JobStatus.COMPLETED,
            image=_find_generated_asset(scene_assets, AssetType.IMAGE, AssetCategory.IMAGE),
            video=_find_generated_asset(scene_assets, AssetType.VIDEO, AssetCategory.VIDEO),
            voice=_find_generated_asset(scene_assets, AssetType.VOICE, AssetCategory.VOICE),
            subtitles=_find_generated_asset(scene_assets, AssetType.SUBTITLE, AssetCategory.SUBTITLE),
        )
        if not (sm.image or sm.video):
            _logger.warning(
                "multi_pass_scene_no_visual",
                project_id=str(project.id),
                scene_number=scene.scene_number,
                scene_id=scene_id,
            )
            continue

        manifest = AssetManifest(
            project_id=str(project.id),
            scene_manifests=[sm],
            total_duration_seconds=duration,
        )
        builder = CompositionBuilder()
        # Pass camera plan so the builder can pick the right Ken Burns
        # animation direction for this scene.
        cam_plans = {scene_id: {"movement": scene.camera_motion.value if scene.camera_motion else ""}}
        composition = builder.build(
            manifest,
            export_profile=export_profile,
            scene_durations={scene_id: duration},
            camera_plans=cam_plans,
            transition_config=False,
        )
        if _is_direct_cinematic(project) and sm.video and not sm.voice:
            video_path = sm.video.storage_uri.removeprefix("local://")
            probe = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=index", "-of", "csv=p=0", video_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            audio_stream, _ = await probe.communicate()
            if probe.returncode == 0 and audio_stream.strip():
                voice_track = next(t for t in composition.timeline.tracks if t.track_type == TrackType.VOICE)
                voice_track.clips.append(TimelineClip(
                    track_id=voice_track.id, asset_uri=sm.video.storage_uri,
                    asset_type="video", start_time=0, duration=duration,
                ))

        part_path = os.path.join(parts_dir, f"scene_{scene.scene_number:02d}.mp4")
        try:
            package = await pipeline.execute(composition, part_path, project_id=str(project.id))
            if os.path.isfile(package.final_video_path) and os.path.getsize(package.final_video_path) > 0:
                part_files.append(package.final_video_path)
                total_render_time += package.render_report.render_time_seconds
                total_duration += duration
                _logger.info(
                    "multi_pass_scene_rendered",
                    project_id=str(project.id),
                    scene_number=scene.scene_number,
                    part_path=package.final_video_path,
                    size=os.path.getsize(package.final_video_path),
                )
            else:
                _logger.warning(
                    "multi_pass_scene_empty",
                    project_id=str(project.id),
                    scene_number=scene.scene_number,
                    part_path=part_path,
                )
        except Exception as exc:
            _logger.warning(
                "multi_pass_scene_failed",
                project_id=str(project.id),
                scene_number=scene.scene_number,
                error=str(exc),
            )

    if not part_files:
        raise RuntimeError("No scene parts could be rendered")

    list_path = os.path.join(parts_dir, "concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for part in part_files:
            f.write(f"file '{part}'\n")

    concat_start = asyncio.get_event_loop().time()
    # Scene parts are concatenated as-is — scene durations are already
    # sized to the target at planning time (and Veo clip plans cover each
    # scene exactly), so no trimming is applied here.
    concat_args = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", "-movflags", "+faststart", output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *concat_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"concat failed: {stderr.decode('utf-8', errors='ignore')[-500:]}")
    concat_time = asyncio.get_event_loop().time() - concat_start

    file_size = os.path.getsize(output_path) if os.path.isfile(output_path) else 0
    metrics = RenderMetrics(
        render_time_seconds=total_render_time + concat_time,
        output_size_bytes=file_size,
        output_duration_seconds=total_duration,
        output_resolution=f"{export_profile.width}x{export_profile.height}",
        output_fps=export_profile.fps,
    )
    quality = QualityReport()
    return ProjectPackage(
        project_id=str(project.id),
        final_video_path=output_path,
        render_report=metrics,
        quality_report=quality,
    )


async def _combine_scene_subtitles(
    container: ServiceContainer,
    project,
    workflow_id: UUID,
    scenes: list,
) -> str | None:
    """Combine per-scene .srt files into a single video-level .srt file.

    Each scene's .srt has timestamps relative to that scene's start
    (00:00:00).  This function offsets them by the scene's cumulative
    start time so the combined file plays in sync with the final video.

    Returns the path to the combined .srt file, or ``None`` if no
    subtitles were found.
    """
    import re

    storage_path = container.config.storage.local_path
    project_dir = os.path.join(storage_path, "projects", str(project.id))
    subtitles_dir = os.path.join(project_dir, "subtitles")

    # Sort scenes by scene_number to get correct start times
    sorted_scenes = sorted(scenes, key=lambda s: s.scene_number)
    cumulative_offset = 0.0

    entries: list[tuple[float, float, str]] = []

    for scene in sorted_scenes:
        srt_path = os.path.join(subtitles_dir, f"scene_{scene.scene_number}.srt")
        if not os.path.isfile(srt_path):
            continue

        with open(srt_path, encoding="utf-8") as f:
            content = f.read()

        # Parse SRT entries: index, timestamp line, text, blank line
        # Format: "00:00:00,000 --> 00:00:05,000"
        pattern = re.compile(
            r"(\d+)\s*\n"
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*\n"
            r"(.*?)(?=\n\d+\s*\n|\Z)",
            re.DOTALL,
        )

        for match in pattern.finditer(content):
            h1, m1, s1, ms1 = (int(x) for x in match.groups()[1:5])
            h2, m2, s2, ms2 = (int(x) for x in match.groups()[5:9])
            text = match.group(10).strip()

            start_sec = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0 + cumulative_offset
            end_sec = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0 + cumulative_offset
            entries.append((start_sec, end_sec, text))

        cumulative_offset += float(scene.duration_seconds or 5.0)

    if not entries:
        return None

    # Write combined .srt
    combined_path = os.path.join(subtitles_dir, f"{project.id}.srt")

    def _fmt_srt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(combined_path, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(entries, 1):
            f.write(f"{idx}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{text}\n\n")

    _logger.info(
        "combined_subtitle_generated",
        project_id=str(project.id),
        path=combined_path,
        entries=len(entries),
    )
    return combined_path


async def _measure_audio_duration_seconds(audio: bytes) -> float | None:
    """Return the real duration of encoded audio bytes via ffprobe.

    Returns ``None`` when ffprobe is unavailable or the bytes cannot be
    probed (e.g. running on a Windows host without FFmpeg).
    """
    import tempfile

    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio)
            path = tmp.name
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        if proc.returncode == 0:
            return round(float(out.decode().strip()), 2)
    except Exception as exc:
        _logger.debug("audio_duration_probe_failed", error=str(exc))
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
    return None


def _estimate_speech_seconds(text: str, fallback: float | int | None) -> float:
    """Rough narration duration at ~150 wpm (≈2.5 words/sec)."""
    words = len(text.split())
    if words:
        return round(words / 2.5, 2)
    return float(fallback or 5.0)


def _langfuse_trace_id(workflow_state: WorkflowState) -> str | None:
    """Return the Langfuse trace id for this workflow run, if any."""
    return workflow_state.trace_id or workflow_state.metadata.custom.get(
        "langfuse_trace_id"
    )


def _record_asset_cost(
    container: ServiceContainer,
    workflow_state: WorkflowState,
    project,
    scene,
    *,
    agent_type: AgentType,
    category: str,
    provider: str,
    model: str,
    cost_usd: float,
    operation: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a generated-asset cost on the state and the cost tracker."""
    if cost_usd <= 0:
        return
    workflow_state.add_cost(cost_usd, category)
    tracker = getattr(container, "cost_tracker", None)
    if tracker is None:
        return
    try:
        from src.application.services.cost_tracker import CostEntry

        tracker.record(
            CostEntry(
                agent_type=agent_type,
                provider=AIProvider(provider),
                model=model,
                cost_usd=cost_usd,
                project_id=str(project.id),
                scene_id=str(scene.id) if scene is not None else None,
                operation=operation,
                metadata=metadata or {},
            )
        )
    except Exception as exc:
        _logger.warning("cost_record_failed", operation=operation, error=str(exc))


# ---------------------------------------------------------------------------
# Veo video-clip helpers
# ---------------------------------------------------------------------------
def _plan_veo_clip_durations(duration_seconds: float) -> list[int]:
    """Split a scene duration into Veo-supported clip lengths (4/6/8s).

    Veo 3.1 Lite only generates 4-, 6- or 8-second clips.  This returns
    the *minimum billed cover* — the smallest set of clips whose total
    is >= ``duration_seconds``.  Every even duration >= 4 is covered
    exactly (4, 6, 8, 4+6, 6+6, 8+6, …); odd/fractional durations get at
    most ~1s of overshoot, which the renderer trims away.
    """
    import math

    duration = max(float(duration_seconds or 0), 4.0)
    billed = 2 * math.ceil(duration / 2.0)  # smallest even total >= duration
    clips = [8] * (billed // 8)
    remainder = billed % 8
    if remainder == 4:
        clips.append(4)
    elif remainder == 6:
        clips.append(6)
    elif remainder == 2:
        # 8 -> 6+4 covers the extra 2s exactly
        clips.pop()
        clips += [6, 4]
    if not clips:
        clips = [4]
    return clips


def _plan_direct_cinematic_segments(duration_seconds: float) -> list[int]:
    """Plan one initial Veo clip plus 7-second video extensions."""
    return plan_direct_segments(duration_seconds)


def _direct_cinematic_billed_seconds(duration_seconds: float) -> int:
    return sum(_plan_direct_cinematic_segments(duration_seconds))


def _build_veo_prompt(
    sp: ScenePackage, base_prompt: str, shared_context: str = ""
) -> str:
    """Compose a motion-oriented Veo prompt from the scene package.

    ``base_prompt`` (the visual description) describes a static frame;
    Veo performs better with explicit motion and camera language, so the
    camera plan and animation plan are folded in.  ``shared_context`` is
    the storyboard's canonical character/setting description — prepended
    verbatim to every clip so independently generated shots keep the same
    protagonist and location.
    """
    parts: list[str] = []
    if shared_context:
        parts.append(f"Scene bible (keep identical across shots): {shared_context}")
    parts.append(base_prompt)

    vp = sp.visual_plan
    if vp is not None:
        for value in (vp.environment, vp.mood, vp.lighting, vp.visual_style):
            if value:
                parts.append(value)

    cp = sp.camera_plan
    if cp is not None:
        shot = " ".join(
            p for p in (cp.camera_angle, cp.camera_distance) if p
        )
        movement = (cp.movement or "").replace("_", " ")
        if shot and movement and movement != "static":
            parts.append(f"Camera: {shot} shot, {movement}")
        elif movement and movement != "static":
            parts.append(f"Camera movement: {movement}")
        elif shot:
            parts.append(f"Camera: {shot} shot")

    ap = sp.animation_plan
    if ap is not None:
        for value in (ap.object_motion, ap.background_motion):
            if value:
                parts.append(value)

    prompt = ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())
    # Veo accepts ~1024 tokens; keep the prompt comfortably under it.
    return prompt[:3500]


async def _probe_video_dimensions(path: str) -> tuple[int, int] | None:
    """Return (width, height) of the first video stream, or None."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    try:
        w, h = out.decode().strip().split(",")[:2]
        return int(w), int(h)
    except (ValueError, AttributeError):
        return None


async def _probe_video_has_audio(path: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode == 0 and bool(out.strip())


async def _probe_video_bytes_dimensions(video_bytes: bytes) -> tuple[int, int] | None:
    import tempfile

    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            path = tmp.name
        return await _probe_video_dimensions(path)
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


async def _validate_video_bytes(
    video_bytes: bytes,
    *,
    expected_duration: float,
    expected_width: int,
    expected_height: int,
    expected_fps: int,
    require_audio: bool = True,
) -> None:
    """Fail fast when normalization lost duration, frames, or audio."""
    import json
    import tempfile

    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            path = tmp.name
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,width,height,avg_frame_rate,duration",
            "-of", "json", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="ignore")[-400:])
        info = json.loads(out.decode("utf-8"))
        streams = info.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if video is None:
            raise RuntimeError("normalized video has no video stream")
        actual_duration = float(info.get("format", {}).get("duration") or 0)
        if abs(actual_duration - expected_duration) > 0.25:
            raise RuntimeError(
                f"normalized video duration {actual_duration:.3f}s differs from expected {expected_duration:.3f}s"
            )
        if (int(video.get("width", 0)), int(video.get("height", 0))) != (expected_width, expected_height):
            raise RuntimeError("normalized video dimensions do not match the requested intermediate")
        rate = str(video.get("avg_frame_rate", "0/1"))
        numerator, denominator = rate.split("/", 1)
        actual_fps = float(numerator) / float(denominator or 1)
        if abs(actual_fps - expected_fps) > 0.1:
            raise RuntimeError(f"normalized video frame rate is {actual_fps:.3f}, expected {expected_fps}")
        if require_audio and audio is None:
            raise RuntimeError("normalized direct cinematic video has no audio stream")
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


async def _concat_video_clips(
    clips: list[bytes],
    *,
    width: int | None = None,
    height: int | None = None,
    target_duration: float | None = None,
    force_normalize: bool = False,
    fps: int = 24,
) -> bytes:
    """Normalize and concatenate MP4 clips with continuous video/audio PTS.

    Direct cinematic mode always uses the normalized path.  The explainer
    path keeps the stream-copy fast path for already-uniform clips.
    """
    if not clips:
        raise ValueError("At least one video clip is required")
    if len(clips) == 1 and not force_normalize and target_duration is None:
        return clips[0]

    import shutil
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="veo_concat_")
    try:
        clip_paths: list[str] = []
        for i, data in enumerate(clips):
            p = os.path.join(tmpdir, f"clip_{i:02d}.mp4")
            with open(p, "wb") as f:
                f.write(data)
            clip_paths.append(p)

        list_path = os.path.join(tmpdir, "concat.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

        out_path = os.path.join(tmpdir, "scene.mp4")
        dims = [await _probe_video_dimensions(p) for p in clip_paths]
        uniform = dims[0] is not None and all(d == dims[0] for d in dims)
        has_audio = await _probe_video_has_audio(clip_paths[0])
        proc = None
        stderr = b""

        if uniform and not force_normalize and target_duration is None:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", list_path,
                "-c", "copy", "-movflags", "+faststart", out_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

        if proc is None or proc.returncode != 0:
            reference_w, reference_h = next(
                (d for d in dims if d), (width or 1920, height or 1080)
            )
            portrait = (height or reference_h) > (width or reference_w)
            tw, th = (720, 1280) if portrait else (1280, 720)
            video_filter = f"scale={tw}:{th}:flags=lanczos,setsar=1,fps={fps}"
            if target_duration is not None:
                video_filter += f",trim=duration={target_duration},setpts=PTS-STARTPTS"
            args = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", list_path,
                "-map", "0:v:0",
                "-vf", video_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-r", str(fps),
            ]
            if has_audio:
                args.extend(["-map", "0:a:0", "-af", f"atrim=duration={target_duration},asetpts=PTS-STARTPTS" if target_duration is not None else "anull", "-c:a", "aac", "-ar", "48000", "-ac", "2"])
            else:
                args.append("-an")
            args.extend(["-movflags", "+faststart", out_path])
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

        if proc.returncode != 0 or not os.path.isfile(out_path):
            raise RuntimeError(
                f"veo clip concat failed: {stderr.decode('utf-8', errors='ignore')[-600:]}"
            )
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _extract_last_frame_png(video_bytes: bytes) -> bytes | None:
    """Extract the last frame of an MP4 as PNG bytes via FFmpeg.

    Returns ``None`` when FFmpeg is unavailable or extraction fails —
    frame chaining is best-effort and simply skipped in that case.
    """
    import tempfile

    in_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            in_path = tmp.name
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-v", "error",
            "-sseof", "-0.05", "-i", in_path,
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        if proc.returncode == 0 and out:
            return out
        _logger.debug("last_frame_extract_failed", returncode=proc.returncode)
    except Exception as exc:
        _logger.debug("last_frame_extract_failed", error=str(exc))
    finally:
        if in_path:
            try:
                os.unlink(in_path)
            except OSError:
                pass
    return None


async def _generate_scene_video(
    container: ServiceContainer,
    project,
    service: "ProjectService",
    workflow_state: WorkflowState,
    scene,
    sp: ScenePackage,
    prompt: str,
    *,
    shared_context: str = "",
    first_frame: bytes | None = None,
) -> tuple[dict[str, Any], bytes | None]:
    """Generate a Veo video for one scene and persist it as a VideoAsset.

    The scene duration is covered by 4/6/8s Veo clips which are
    concatenated into a single per-scene MP4, so downstream rendering
    treats it exactly like a stock video clip.  Each clip call is traced
    in Langfuse and its real cost recorded on the workflow state and the
    cost tracker.

    Frame chaining: ``first_frame`` (the previous clip's last frame, as
    PNG bytes) is fed to the first clip as its starting image, and each
    subsequent clip is seeded with the last frame of the clip before it.
    Returns the final clip's last frame so the *next scene* can keep the
    same character/setting too.
    """
    veo_prompt = _build_veo_prompt(sp, prompt, shared_context)
    beats = sp.metadata.get("clip_beats")
    clip_durations = (
        _plan_direct_cinematic_segments(float(sp.duration_seconds or 8))
        if beats is not None
        else _plan_veo_clip_durations(float(sp.duration_seconds or 8))
    )
    if beats is not None:
        if len(beats) != len(clip_durations):
            raise ValueError("Clip beat count does not match direct cinematic extension plan")
        return await _generate_direct_scene_video(
            container,
            project,
            service,
            workflow_state,
            scene,
            sp,
            prompt,
            shared_context=shared_context,
            first_frame=first_frame,
        )
    trace_id = _langfuse_trace_id(workflow_state)
    out_w, out_h = _target_dimensions(workflow_state)

    clip_bytes: list[bytes] = []
    clip_prompts: list[str] = []
    total_cost = 0.0
    total_latency_ms = 0.0
    provider_name = "veo"
    model = ""
    seed_frame = first_frame
    for clip_index, clip_secs in enumerate(clip_durations):
        input_frame_supplied = seed_frame is not None
        clip_prompt = veo_prompt
        if beats is not None:
            # Only the first clip receives the full production spec —
            # it establishes the world.  Repeating it on continuation
            # clips re-narrates the whole action arc, which fights the
            # seeded frame and makes Veo compress or restart the action.
            spec = f"Fixed production specification: {prompt}. " if clip_index == 0 else ""
            continuation = (
                "The supplied image is this clip's exact first frame; continue its motion and camera. "
                "Do not restart or repeat earlier action."
                if seed_frame
                else "Establish the subject and setting."
            )
            clip_prompt = (
                f"{spec}Same subject and location throughout: {shared_context}. "
                f"Avoid: {sp.metadata.get('avoid') or 'unrequested changes to subject, location and props'}. "
                f"This clip is part {clip_index + 1} of {len(beats)}; show ONLY this action beat: {beats[clip_index]}. "
                f"{continuation}"
            )
        try:
            result = await container.video_gateway.generate_video(
                clip_prompt,
                duration_seconds=float(clip_secs),
                width=out_w,
                height=out_h,
                fps=24,  # Veo output is 24 fps; the renderer normalises to project fps
                image=seed_frame,
                allow_fallback=beats is None,
                correlation_id=f"asset-scene-{sp.scene_number}-clip-{clip_index}",
                trace_id=trace_id,
                generation_name=f"video_generation_scene_{sp.scene_number}_clip_{clip_index}",
            )
        except Exception as exc:
            _logger.error("video_clip_generation_failed", scene_number=sp.scene_number, clip_index=clip_index, input_frame_supplied=input_frame_supplied, error=str(exc))
            raise
        if beats is not None and result.provider != "veo":
            raise RuntimeError(f"Direct cinematic clip used unexpected provider: {result.provider}")
        clip_prompts.append(clip_prompt)
        clip_bytes.append(result.output)
        total_cost += result.cost_usd
        total_latency_ms += result.latency_ms
        provider_name = result.provider
        model = result.model
        if clip_index < len(clip_durations) - 1:
            # Chain the next clip to this clip's final frame so the
            # character/setting/camera feel continuous rather than a
            # fresh text-to-video sampling.
            seed_frame = await _extract_last_frame_png(result.output)
            if seed_frame is None:
                _logger.warning(
                    "veo_frame_chain_skipped",
                    scene_number=sp.scene_number,
                    clip_index=clip_index,
                )
                if beats is not None:
                    raise RuntimeError("Direct cinematic frame handoff failed")
        workflow_state.metadata.custom.setdefault("video_clips", []).append({
            "scene_number": sp.scene_number, "clip_index": clip_index,
            "duration_seconds": clip_secs, "prompt": clip_prompt,
            "input_frame_supplied": input_frame_supplied,
            "next_frame_extracted": seed_frame is not None if clip_index < len(clip_durations) - 1 else None,
            "provider": result.provider, "cost_usd": result.cost_usd,
        })
        _record_asset_cost(
            container, workflow_state, project, scene,
            agent_type=AgentType.VIDEO_PROMPT,
            category="video",
            provider=result.provider,
            model=result.model,
            cost_usd=result.cost_usd,
            operation="video_generation",
            metadata={
                "scene_number": sp.scene_number,
                "clip_index": clip_index,
                "clip_duration_seconds": clip_secs,
            },
        )

    last_frame = await _extract_last_frame_png(clip_bytes[-1]) if clip_bytes else None
    if beats is not None and last_frame is None:
        raise RuntimeError("Direct cinematic final video has no extractable last frame")
    video_bytes = await _concat_video_clips(clip_bytes, width=out_w, height=out_h)

    storage_path = f"projects/{project.id}/videos/scene_{sp.scene_number}.mp4"
    storage_uri = await container.storage_gateway.upload(
        video_bytes, storage_path, content_type="video/mp4"
    )
    asset = VideoAsset(
        project_id=project.id,
        scene_id=scene.id,
        prompt=clip_prompts[0],
        width=out_w,
        height=out_h,
        duration_seconds=sum(clip_durations),
        fps=24,
        format="mp4",
        provider=AIProvider(provider_name),
        generation_cost_usd=total_cost,
        generation_time_seconds=total_latency_ms / 1000.0,
        generation_status=AssetGenerationStatus.READY,
        storage_type=StorageType.LOCAL,
        storage_ref=storage_uri,
        quality_score=0.0 if beats is not None else 0.85,
    )
    await service._asset_repo.create(asset)
    # The scene slot must equal the *generated* clip total so the renderer
    # concatenates the footage as-is without trimming anything.
    scene.duration_seconds = float(sum(clip_durations))
    scene.visual_type = VisualType.AI_VIDEO
    await service._scene_repo.update(scene)

    # Final frame of the last clip seeds the NEXT scene's first clip —
    # this is what keeps character/setting identical across scene cuts.
    _logger.info(
        "video_asset_generated",
        scene_number=sp.scene_number,
        clips=len(clip_durations),
        clip_durations=clip_durations,
        cost=total_cost,
        model=model,
        frame_chained=first_frame is not None,
    )
    return {
        "scene_number": sp.scene_number,
        "type": "video",
        "storage_uri": storage_uri,
        "cost_usd": total_cost,
        "clips": len(clip_durations),
        "frame_chained": first_frame is not None,
    }, last_frame


async def _generate_direct_scene_video(
    container: ServiceContainer,
    project,
    service: "ProjectService",
    workflow_state: WorkflowState,
    scene,
    sp: ScenePackage,
    prompt: str,
    *,
    shared_context: str = "",
    first_frame: bytes | None = None,
) -> tuple[dict[str, Any], bytes | None]:
    """Generate direct cinematic footage using Veo video extension."""
    beats = sp.metadata.get("clip_beats") or []
    clip_durations = _plan_direct_cinematic_segments(float(sp.duration_seconds or 8))
    if len(beats) != len(clip_durations):
        raise ValueError("Clip beat count does not match direct cinematic extension plan")

    trace_id = _langfuse_trace_id(workflow_state)
    out_w, out_h = _target_dimensions(workflow_state)
    normalized_w, normalized_h = (720, 1280) if out_h > out_w else (1280, 720)
    target_duration = float(sp.duration_seconds or sum(clip_durations))
    remote_video: Any | None = None
    latest_video = b""
    total_cost = 0.0
    total_latency_ms = 0.0
    provider_name = "veo"
    model = ""
    prompt_history: list[str] = []

    for clip_index, segment_seconds in enumerate(clip_durations):
        clip_prompt = direct_clip_prompt(
            prompt,
            shared_context,
            sp.metadata.get("avoid") or "",
            beats,
            clip_index,
        )
        prompt_history.append(clip_prompt)
        if clip_index == 0:
            result = await container.video_gateway.generate_video_with_resource(
                clip_prompt,
                duration_seconds=float(segment_seconds),
                width=normalized_w,
                height=normalized_h,
                fps=24,
                image=first_frame,
                resolution="720p",
                # Kling has a native negative_prompt field — the avoid text is
                # routed there instead of being embedded in the prompt (the
                # composed prompt omits it for Kling), keeping inside Kling's
                # tighter 3072-char limit. Harmless for Veo, which also
                # accepts negative_prompt natively.
                negative_prompt=sp.metadata.get("avoid") or None,
                correlation_id=f"asset-scene-{sp.scene_number}-initial",
                trace_id=trace_id,
                generation_name=f"video_generation_scene_{sp.scene_number}_initial",
            )
            mode = "initial"
            input_video_supplied = False
        else:
            if remote_video is None:
                raise RuntimeError("Veo extension lost the remote video resource")
            result = await container.video_gateway.extend_video(
                remote_video,
                clip_prompt,
                duration_seconds=float(segment_seconds),
                width=720,
                height=1280 if out_h > out_w else 720,
                fps=24,
                correlation_id=f"asset-scene-{sp.scene_number}-extension-{clip_index}",
                trace_id=trace_id,
                generation_name=f"video_extension_scene_{sp.scene_number}_segment_{clip_index}",
            )
            mode = "extension"
            input_video_supplied = True

        actual_dimensions = await _probe_video_bytes_dimensions(result.output)
        # Veo's server-side extension requires a 720p source video; other
        # providers (e.g. Kling last-frame chaining) are resolution-agnostic.
        if result.provider == "veo" and actual_dimensions != (normalized_w, normalized_h):
            raise RuntimeError(
                "Veo extension source must be 720p before continuing; "
                f"got dimensions {actual_dimensions}"
            )
        remote_video = result.metadata.get("remote_video")
        if clip_index < len(clip_durations) - 1 and remote_video is None:
            raise RuntimeError("Veo extension did not return a remote video resource")
        latest_video = result.output
        provider_name = result.provider
        model = result.model
        total_cost += result.cost_usd
        total_latency_ms += result.latency_ms
        workflow_state.metadata.custom.setdefault("video_clips", []).append({
            "scene_number": sp.scene_number,
            "clip_index": clip_index,
            "duration_seconds": segment_seconds,
            "prompt": clip_prompt,
            "generation_mode": mode,
            "input_frame_supplied": False,
            "input_video_supplied": input_video_supplied,
            "remote_video_retained": remote_video is not None,
            "provider": result.provider,
            "cost_usd": result.cost_usd,
        })
        _record_asset_cost(
            container,
            workflow_state,
            project,
            scene,
            agent_type=AgentType.VIDEO_PROMPT,
            category="video",
            provider=result.provider,
            model=result.model,
            cost_usd=result.cost_usd,
            operation="video_extension" if mode == "extension" else "video_generation",
            metadata={
                "scene_number": sp.scene_number,
                "clip_index": clip_index,
                "clip_duration_seconds": segment_seconds,
                "generation_mode": mode,
            },
        )

    if not latest_video:
        raise RuntimeError("Veo direct cinematic generation returned no video")
    video_bytes = await _concat_video_clips(
        [latest_video],
        width=out_w,
        height=out_h,
        target_duration=target_duration,
        force_normalize=True,
    )
    await _validate_video_bytes(
        video_bytes,
        expected_duration=target_duration,
        expected_width=normalized_w,
        expected_height=normalized_h,
        expected_fps=24,
        require_audio=True,
    )
    last_frame = await _extract_last_frame_png(video_bytes)
    if last_frame is None:
        raise RuntimeError("Direct cinematic final video has no extractable last frame")

    storage_path = f"projects/{project.id}/videos/scene_{sp.scene_number}.mp4"
    storage_uri = await container.storage_gateway.upload(
        video_bytes, storage_path, content_type="video/mp4"
    )
    asset = VideoAsset(
        project_id=project.id,
        scene_id=scene.id,
        prompt=prompt_history[0],
        width=out_w,
        height=out_h,
        duration_seconds=target_duration,
        fps=24,
        format="mp4",
        provider=AIProvider(provider_name),
        generation_cost_usd=total_cost,
        generation_time_seconds=total_latency_ms / 1000.0,
        generation_status=AssetGenerationStatus.READY,
        storage_type=StorageType.LOCAL,
        storage_ref=storage_uri,
        quality_score=0.0,
    )
    await service._asset_repo.create(asset)
    scene.duration_seconds = target_duration
    scene.visual_type = VisualType.AI_VIDEO
    await service._scene_repo.update(scene)
    _logger.info(
        "video_asset_generated",
        scene_number=sp.scene_number,
        clips=len(clip_durations),
        clip_durations=clip_durations,
        generated_duration_seconds=sum(clip_durations),
        output_duration_seconds=target_duration,
        cost=total_cost,
        model=model,
        generation_mode="video_extension",
    )
    return {
        "scene_number": sp.scene_number,
        "type": "video",
        "storage_uri": storage_uri,
        "cost_usd": total_cost,
        "clips": len(clip_durations),
        "frame_chained": False,
        "video_extension": True,
    }, last_frame


def _set_step_io(
    workflow_state: WorkflowState,
    step: str,
    input_data: dict,
    output_data: dict,
) -> None:
    """Attach concise step-level input/output for Langfuse tracing."""
    workflow_state.metadata.custom["step_input"] = {"step": step, **input_data}
    workflow_state.metadata.custom["step_output"] = {"step": step, **output_data}


async def _create_step_output(
    service: ProjectService,
    engine: WorkflowEngine,
    container: ServiceContainer,
    workflow_state: WorkflowState,
    project,
    workflow_id: UUID,
    step: str,
) -> WorkflowState:
    if _is_direct_cinematic(project) and step in {
        WorkflowStep.RESEARCH.value, WorkflowStep.SCRIPTING.value,
        WorkflowStep.VOICE_GENERATION.value, WorkflowStep.SUBTITLE_GENERATION.value,
        WorkflowStep.SEO.value,
    } and (step not in {WorkflowStep.VOICE_GENERATION.value, WorkflowStep.SUBTITLE_GENERATION.value} or not (getattr(project, "metadata", None) or {}).get("narration_text")):
        _set_step_io(workflow_state, step, {"mode": "direct_cinematic"}, {"skipped": True})
        return workflow_state

    if step == WorkflowStep.RESEARCH.value:
        _set_step_io(
            workflow_state,
            step,
            {"project_title": project.title, "project_description": project.description or ""},
            {},
        )
        result = await _execute_workflow(
            engine=engine,
            container=container,
            workflow_state=workflow_state,
            workflow_name="research_workflow",
        )
        package = _get_research_package(result.state)
        research = _research_package_to_entity(project, workflow_id, package)
        await service._research_repo.create(research)
        _set_step_io(
            result.state,
            step,
            {"project_title": project.title, "project_description": project.description or ""},
            {
                "research_overview": (package.summary.overview or "")[:300] if package.summary else "",
                "sources_count": len(package.web_research.items) if package.web_research else 0,
                "keywords": list(package.keywords.primary_keywords[:10]) if package.keywords else [],
            },
        )
        return result.state

    if step == WorkflowStep.SCRIPTING.value:
        _set_step_io(
            workflow_state,
            step,
            {"project_title": project.title},
            {},
        )
        result = await _execute_workflow(
            engine=engine,
            container=container,
            workflow_state=workflow_state,
            workflow_name="script_workflow",
        )
        package = _get_script_package(result.state)
        script = _script_package_to_entity(project, workflow_id, package)
        await service._script_repo.create(script)
        _set_step_io(
            result.state,
            step,
            {"project_title": project.title},
            {
                "hook": (package.hook_result.selected_hook.content if package.hook_result.selected_hook else "")[:200],
                "word_count": package.word_count,
                "estimated_duration_seconds": package.estimated_duration_seconds,
            },
        )
        return result.state

    if step == WorkflowStep.STORYBOARD.value and _is_direct_cinematic(project):
        package = _build_direct_storyboard(project, workflow_state)
        workflow_state.storyboard.metadata["storyboard_package"] = package.model_dump(mode="json")
        storyboard = _storyboard_package_to_entity(project, workflow_id, package)
        await service._storyboard_repo.create(storyboard)
        _set_step_io(workflow_state, step, {"mode": "direct_cinematic"}, {"scene_count": 1, "clip_beats": len(package.scene_packages[0].metadata["clip_beats"])})
        return workflow_state

    if step == WorkflowStep.STORYBOARD.value:
        _set_step_io(
            workflow_state,
            step,
            {"project_title": project.title},
            {},
        )
        result = await _execute_workflow(
            engine=engine,
            container=container,
            workflow_state=workflow_state,
            workflow_name="storyboard_workflow",
        )
        package = _get_storyboard_package(result.state)
        storyboard = _storyboard_package_to_entity(project, workflow_id, package)
        await service._storyboard_repo.create(storyboard)
        _set_step_io(
            result.state,
            step,
            {"project_title": project.title},
            {
                "scene_count": len(package.scene_packages),
                "estimated_timeline_minutes": package.estimated_timeline_minutes,
            },
        )
        return result.state

    if step == WorkflowStep.SCENE_PLANNING.value:
        package = _get_storyboard_package(workflow_state)
        _set_step_io(
            workflow_state,
            step,
            {"scene_count": len(package.scene_packages)},
            {},
        )
        latest = await service._storyboard_repo.get_latest_version(project.id)
        storyboard_id = latest.id if latest else None
        created_scenes = []
        for scene in _scene_packages_to_entities(project, workflow_id, storyboard_id, package):
            await service._scene_repo.create(scene)
            created_scenes.append(scene.scene_number)
        _set_step_io(
            workflow_state,
            step,
            {"scene_count": len(package.scene_packages)},
            {
                "scenes_created": len(created_scenes),
                "scene_numbers": created_scenes,
            },
        )
        return workflow_state

    if step == WorkflowStep.ASSET_GENERATION.value:
        package = _get_storyboard_package(workflow_state)
        if _is_direct_cinematic(project):
            if (len(package.scene_packages) != 1 or
                package.scene_packages[0].visual_plan.visual_description != project.description.strip() or
                package.visual_plans.shared_context != (getattr(project, "metadata", None) or {}).get("visual_anchor", "").strip() or
                package.scene_packages[0].metadata.get("clip_beats") != (getattr(project, "metadata", None) or {}).get("clip_beats")):
                raise ValueError("Direct cinematic storyboard changed the production specification")
        scenes = [
            s for s in await service._scene_repo.get_by_project(project.id)
            if getattr(s, "workflow_id", workflow_id) == workflow_id
        ]
        scene_by_number = {s.scene_number: s for s in scenes}
        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "asset_types": [sp.asset_type or "ai_video" for sp in package.scene_packages],
            },
            {},
        )
        generated_assets: list[dict] = []
        generation_errors: list[dict] = []

        # When USE_VEO is enabled and a video provider is registered,
        # scenes are rendered from AI-generated video clips instead of
        # still images.  A per-scene Veo failure falls back to the image
        # path below so the run never dies on a single bad clip.
        veo_enabled = bool(
            getattr(container.config.veo, "enabled", False)
            and container.video_gateway is not None
        )
        kling_enabled = bool(
            getattr(getattr(container.config, "kling", None), "enabled", False)
            and getattr(container.config.kling, "api_key", "")
        )
        video_provider_names = set(
            container.provider_registry.get_provider_names_by_type(VideoProvider)
        )
        # Direct-cinematic works with any AI video provider registered as
        # primary — Kling's i2v-chained segments fulfil the same contract as
        # Veo's extension API (one combined clip per call).
        direct_provider_available = bool(
            {"veo", "kling"} & video_provider_names
        )
        # Canonical character/setting description produced once by the
        # visual storyboard agent and prepended verbatim to every clip
        # prompt — the primary fix for per-clip character/environment
        # drift.  Older storyboards simply have no bible (empty string).
        shared_context = getattr(package.visual_plans, "shared_context", "") or ""
        # Last frame of the previous scene's final clip, fed to this
        # scene's first clip (image-to-video) so the cut is visually
        # continuous instead of an independent re-sampling.
        last_frame: bytes | None = None
        if _is_direct_cinematic(project) and not (
            (veo_enabled or kling_enabled) and direct_provider_available
        ):
            raise ValueError(
                "Direct cinematic mode requires an available video provider "
                "(Kling or Veo)"
            )

        for sp in package.scene_packages:
            scene = scene_by_number.get(sp.scene_number)
            if not scene:
                _logger.warning("asset_scene_not_found", scene_number=sp.scene_number)
                continue

            prompt = sp.visual_plan.visual_description or sp.visual_prompt_summary or sp.title
            if not prompt:
                _logger.warning("asset_prompt_missing", scene_number=sp.scene_number)
                continue

            visual = (sp.asset_type or "ai_video").lower()
            is_direct = _is_direct_cinematic(project)
            if is_direct:
                # Redirect ALL non-image asset types to ai_image for the
                # still-image fallback path — used only when video generation
                # is disabled or a clip generation fails.
                if visual not in ("stock_image", "ai_image", "image"):
                    _logger.info(
                        "asset_type_redirected_to_ai_image",
                        scene_number=sp.scene_number,
                        original_asset_type=visual,
                    )
                    visual = "ai_image"
            else:
                # Research flow: free stock media only — paid generation
                # providers (Veo/Kling/Imagen) are never used here.
                visual = (
                    "stock_video" if visual in _STOCK_VIDEO_TYPES else "stock_image"
                )
            try:
                if is_direct and (veo_enabled or kling_enabled):
                    try:
                        asset_info, last_frame = await _generate_scene_video(
                            container, project, service, workflow_state,
                            scene, sp, prompt,
                            shared_context=shared_context,
                            first_frame=last_frame,
                        )
                        generated_assets.append(asset_info)
                        continue
                    except Exception as veo_exc:
                        _logger.error(
                            "veo_scene_generation_failed",
                            scene_number=sp.scene_number,
                            error=str(veo_exc),
                        )
                        if _is_direct_cinematic(project):
                            raise
                        generation_errors.append(
                            {
                                "scene_number": sp.scene_number,
                                "error": f"veo: {veo_exc}",
                                "fallback": "image",
                            }
                        )
                if visual == "stock_video":
                    provider = _find_provider(container, VideoProvider, "stock_video")
                    if provider is None:
                        _logger.warning(
                            "stock_video_provider_missing",
                            scene_number=sp.scene_number,
                        )
                        visual = "stock_image"  # fall back to a still image
                    else:
                        vw, vh = _target_dimensions(workflow_state)
                        video_bytes = await provider.generate_video(
                            prompt,
                            duration_seconds=sp.duration_seconds or 5.0,
                            width=vw,
                            height=vh,
                        )
                        storage_path = f"projects/{project.id}/videos/scene_{sp.scene_number}.mp4"
                        storage_uri = await container.storage_gateway.upload(
                            video_bytes, storage_path, content_type="video/mp4"
                        )
                        asset = VideoAsset(
                            project_id=project.id,
                            scene_id=scene.id,
                            prompt=prompt,
                            width=vw,
                            height=vh,
                            duration_seconds=sp.duration_seconds or 5.0,
                            fps=30,
                            format="mp4",
                            provider=AIProvider.STOCK_VIDEO,
                            generation_cost_usd=0.0,
                            generation_time_seconds=0.0,
                            generation_status=AssetGenerationStatus.READY,
                            storage_type=StorageType.LOCAL,
                            storage_ref=storage_uri,
                            quality_score=0.85,
                        )
                        await service._asset_repo.create(asset)
                        scene.visual_type = VisualType.STOCK_FOOTAGE
                        await service._scene_repo.update(scene)
                        generated_assets.append(
                            {
                                "scene_number": sp.scene_number,
                                "type": "video",
                                "storage_uri": storage_uri,
                                "cost_usd": 0.0,
                            }
                        )
                        _logger.info(
                            "stock_video_asset_generated",
                            scene_number=sp.scene_number,
                        )
                        continue
                if visual in ("stock_image", "ai_image", "image"):
                    img_w, img_h = _target_dimensions(workflow_state)
                    if is_direct:
                        if container.image_gateway is None:
                            _logger.warning("image_gateway_not_available", scene_number=sp.scene_number)
                            continue
                        result = await container.image_gateway.generate_image(
                            prompt,
                            width=img_w,
                            height=img_h,
                            trace_id=_langfuse_trace_id(workflow_state),
                            correlation_id=f"asset-scene-{sp.scene_number}",
                            generation_name=f"asset_generation_scene_{sp.scene_number}",
                        )
                        img_bytes = result.output
                        provider_name = result.provider
                        img_model = result.model
                        img_cost = result.cost_usd
                        img_latency_ms = result.latency_ms
                    else:
                        provider = _find_provider(
                            container, ImageProvider, "stock_image"
                        )
                        if provider is None:
                            _logger.warning(
                                "stock_image_provider_missing",
                                scene_number=sp.scene_number,
                            )
                            color = _PLACEHOLDER_COLORS[
                                (sp.scene_number - 1) % len(_PLACEHOLDER_COLORS)
                            ]
                            img_bytes = _create_placeholder_png(img_w, img_h, color)
                            provider_name = AIProvider.STOCK_IMAGE.value
                            img_model = "placeholder"
                            img_cost = 0.0
                            img_latency_ms = 0
                        else:
                            img_bytes = await provider.generate_image(
                                prompt, width=img_w, height=img_h
                            )
                            provider_name = AIProvider.STOCK_IMAGE.value
                            img_model = "stock"
                            img_cost = 0.0
                            img_latency_ms = 0
                        img_bytes = await provider.generate_image(
                            prompt, width=img_w, height=img_h
                        )
                        provider_name = AIProvider.STOCK_IMAGE.value
                        img_model = "stock"
                        img_cost = 0.0
                        img_latency_ms = 0
                    storage_path = f"projects/{project.id}/images/scene_{sp.scene_number}.png"
                    storage_uri = await container.storage_gateway.upload(
                        img_bytes, storage_path, content_type="image/png"
                    )
                    asset = ImageAsset(
                        project_id=project.id,
                        scene_id=scene.id,
                        prompt=prompt,
                        width=img_w,
                        height=img_h,
                        format="png",
                        provider=AIProvider(provider_name),
                        generation_cost_usd=img_cost,
                        generation_time_seconds=img_latency_ms / 1000.0,
                        generation_status=AssetGenerationStatus.READY,
                        storage_type=StorageType.LOCAL,
                        storage_ref=storage_uri,
                        quality_score=0.85,
                    )
                    await service._asset_repo.create(asset)
                    _record_asset_cost(
                        container, workflow_state, project, scene,
                        agent_type=AgentType.IMAGE_PROMPT,
                        category="image",
                        provider=provider_name,
                        model=img_model,
                        cost_usd=img_cost,
                        operation="image_generation",
                        metadata={"scene_number": sp.scene_number},
                    )
                    scene.visual_type = (
                        VisualType.STOCK_IMAGE
                        if visual == "stock_image"
                        else VisualType.AI_IMAGE
                    )
                    await service._scene_repo.update(scene)
                    generated_assets.append(
                        {
                            "scene_number": sp.scene_number,
                            "type": "image",
                            "storage_uri": storage_uri,
                            "cost_usd": img_cost,
                        }
                    )
                    _logger.info(
                        "image_asset_generated",
                        scene_number=sp.scene_number,
                        cost=result.cost_usd,
                    )
                else:
                    # Safety net: generate a placeholder for truly
                    # unsupported asset types (should not happen since
                    # all types are redirected to ai_image above).
                    color = _PLACEHOLDER_COLORS[(sp.scene_number - 1) % len(_PLACEHOLDER_COLORS)]
                    ph_w, ph_h = _target_dimensions(workflow_state)
                    png_bytes = _create_placeholder_png(ph_w, ph_h, color)
                    storage_path = f"projects/{project.id}/images/scene_{sp.scene_number}.png"
                    storage_uri = await container.storage_gateway.upload(
                        png_bytes, storage_path, content_type="image/png"
                    )
                    asset = ImageAsset(
                        project_id=project.id,
                        scene_id=scene.id,
                        prompt=f"[placeholder] {sp.title}",
                        width=ph_w,
                        height=ph_h,
                        format="png",
                        provider=AIProvider.GEMINI,
                        generation_cost_usd=0.0,
                        generation_time_seconds=0.0,
                        generation_status=AssetGenerationStatus.READY,
                        storage_type=StorageType.LOCAL,
                        storage_ref=storage_uri,
                        quality_score=0.5,
                    )
                    await service._asset_repo.create(asset)
                    scene.visual_type = VisualType.IMAGE
                    await service._scene_repo.update(scene)
                    generated_assets.append(
                        {
                            "scene_number": sp.scene_number,
                            "type": "placeholder_image",
                            "storage_uri": storage_uri,
                            "cost_usd": 0.0,
                        }
                    )
                    _logger.info(
                        "placeholder_image_generated",
                        scene_number=sp.scene_number,
                        asset_type=visual,
                    )
            except Exception as exc:
                _logger.error(
                    "asset_generation_failed",
                    scene_number=sp.scene_number,
                    error=str(exc),
                )
                generation_errors.append(
                    {"scene_number": sp.scene_number, "error": str(exc)}
                )
                scene.generation_status = SceneGenerationStatus.FAILED
                await service._scene_repo.update(scene)
                if _is_direct_cinematic(project):
                    raise

        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "asset_types": [sp.asset_type or "ai_video" for sp in package.scene_packages],
            },
            {
                "assets_generated": generated_assets,
                "errors": generation_errors,
            },
        )
        return workflow_state

    if step == WorkflowStep.VOICE_GENERATION.value:
        package = _get_storyboard_package(workflow_state)
        scenes = [
            s for s in await service._scene_repo.get_by_project(project.id)
            if getattr(s, "workflow_id", workflow_id) == workflow_id
        ]
        scene_by_number = {s.scene_number: s for s in scenes}
        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "narration_lengths": [len(sp.narration or "") for sp in package.scene_packages],
            },
            {},
        )
        voice_assets: list[dict] = []
        voice_errors: list[dict] = []

        # Pass 1 — generate narration audio at the default rate and measure
        # the real duration of every clip with ffprobe.
        generated: list[dict[str, Any]] = []
        for sp in package.scene_packages:
            scene = scene_by_number.get(sp.scene_number)
            if not scene or not sp.narration:
                _logger.warning("voice_narration_missing", scene_number=sp.scene_number)
                continue
            try:
                result = await container.voice_gateway.generate_speech(
                    sp.narration,
                    language="en-US",
                )
                measured = await _measure_audio_duration_seconds(result.output)
                if measured is None:
                    measured = _estimate_speech_seconds(sp.narration, sp.duration_seconds)
                generated.append(
                    {
                        "sp": sp,
                        "scene": scene,
                        "result": result,
                        "audio_seconds": measured,
                        "speaking_rate": 1.0,
                    }
                )
            except Exception as exc:
                _logger.error(
                    "voice_generation_failed",
                    scene_number=sp.scene_number,
                    error=str(exc),
                )
                voice_errors.append(
                    {"scene_number": sp.scene_number, "error": str(exc)}
                )

        # Corrective pass — if the synthesized audio drifts from the
        # user-requested total duration, regenerate once at a proportional
        # speaking rate so narration fits the planned timeline.
        target_seconds = (
            workflow_state.project.target_duration_seconds
            or getattr(project, "target_duration_seconds", None)
        )
        total_audio = sum(g["audio_seconds"] for g in generated)
        if (
            target_seconds
            and generated
            and abs(total_audio - target_seconds) > max(3.0, target_seconds * 0.05)
        ):
            rate = min(max(total_audio / target_seconds, 0.8), 1.35)
            if abs(rate - 1.0) > 0.02:
                _logger.info(
                    "voice_speaking_rate_correction",
                    project_id=str(project.id),
                    audio_seconds=total_audio,
                    target_seconds=target_seconds,
                    speaking_rate=rate,
                )
                for g in generated:
                    sp = g["sp"]
                    try:
                        result = await container.voice_gateway.generate_speech(
                            sp.narration,
                            language="en-US",
                            speaking_rate=rate,
                        )
                        measured = await _measure_audio_duration_seconds(result.output)
                        g["result"] = result
                        g["audio_seconds"] = (
                            measured if measured is not None
                            else round(g["audio_seconds"] / rate, 2)
                        )
                        g["speaking_rate"] = rate
                    except Exception as exc:
                        _logger.warning(
                            "voice_rate_correction_failed",
                            scene_number=sp.scene_number,
                            error=str(exc),
                        )

        if _is_direct_cinematic(project) and any(g["audio_seconds"] > g["sp"].duration_seconds + 0.25 for g in generated):
            raise ValueError("Narration exceeds the direct cinematic scene duration")

        # Persist — upload audio and record assets.  ``scene.duration_seconds``
        # stays at the planned (target-normalised) value so the rendered
        # video tracks the requested duration; the measured audio length is
        # kept on the asset for observability.
        for g in generated:
            sp = g["sp"]
            scene = g["scene"]
            result = g["result"]
            audio_seconds = g["audio_seconds"]
            try:
                storage_path = f"projects/{project.id}/voice/scene_{sp.scene_number}.mp3"
                storage_uri = await container.storage_gateway.upload(
                    result.output, storage_path, content_type="audio/mp3"
                )
                asset = VoiceAsset(
                    project_id=project.id,
                    scene_id=scene.id,
                    duration_seconds=float(audio_seconds),
                    language="en-US",
                    voice_name=result.provider,
                    speaking_rate=g["speaking_rate"],
                    format="mp3",
                    provider=AIProvider(result.provider),
                    generation_cost_usd=result.cost_usd,
                    generation_time_seconds=result.latency_ms / 1000.0,
                    generation_status=AssetGenerationStatus.READY,
                    storage_type=StorageType.LOCAL,
                    storage_ref=storage_uri,
                    quality_score=0.9,
                )
                await service._asset_repo.create(asset)
                _record_asset_cost(
                    container, workflow_state, project, scene,
                    agent_type=AgentType.VOICE,
                    category="voice",
                    provider=result.provider,
                    model=result.model,
                    cost_usd=result.cost_usd,
                    operation="voice_generation",
                    metadata={
                        "scene_number": sp.scene_number,
                        "audio_seconds": audio_seconds,
                        "speaking_rate": g["speaking_rate"],
                    },
                )
                voice_assets.append(
                    {
                        "scene_number": sp.scene_number,
                        "storage_uri": storage_uri,
                        "cost_usd": result.cost_usd,
                        "audio_seconds": audio_seconds,
                    }
                )
                _logger.info(
                    "voice_asset_generated",
                    scene_number=sp.scene_number,
                    cost=result.cost_usd,
                    audio_seconds=audio_seconds,
                )
            except Exception as exc:
                _logger.error(
                    "voice_generation_failed",
                    scene_number=sp.scene_number,
                    error=str(exc),
                )
                voice_errors.append(
                    {"scene_number": sp.scene_number, "error": str(exc)}
                )

        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "narration_lengths": [len(sp.narration or "") for sp in package.scene_packages],
            },
            {
                "voice_assets": voice_assets,
                "errors": voice_errors,
            },
        )
        return workflow_state

    if step == WorkflowStep.SUBTITLE_GENERATION.value:
        package = _get_storyboard_package(workflow_state)
        scenes = [
            s for s in await service._scene_repo.get_by_project(project.id)
            if getattr(s, "workflow_id", workflow_id) == workflow_id
        ]
        scene_by_number = {s.scene_number: s for s in scenes}
        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "narration_lengths": [len(sp.narration or "") for sp in package.scene_packages],
            },
            {},
        )
        subtitles_generated: list[dict] = []
        subtitle_errors: list[dict] = []

        for sp in package.scene_packages:
            scene = scene_by_number.get(sp.scene_number)
            if not scene or not sp.narration:
                continue
            try:
                srt = _narration_to_srt(sp.narration, sp.scene_number, sp.duration_seconds or 5)
                scene.subtitle = srt
                await service._scene_repo.update(scene)

                # Upload SRT to storage and create an asset record
                if container.storage_gateway is not None:
                    storage_path = f"projects/{project.id}/subtitles/scene_{sp.scene_number}.srt"
                    storage_uri = await container.storage_gateway.upload(
                        srt.encode("utf-8"), storage_path, content_type="text/plain"
                    )
                    from src.domain.entities.asset import SubtitleAsset

                    asset = SubtitleAsset(
                        project_id=project.id,
                        scene_id=scene.id,
                        language="en",
                        format="srt",
                        word_count=len(sp.narration.split()),
                        provider=AIProvider.EDGE_TTS,
                        generation_cost_usd=0.0,
                        generation_status=AssetGenerationStatus.READY,
                        storage_type=StorageType.LOCAL,
                        storage_ref=storage_uri,
                        quality_score=0.95,
                    )
                    await service._asset_repo.create(asset)

                subtitles_generated.append(
                    {
                        "scene_number": sp.scene_number,
                        "srt_length": len(srt),
                        "storage_uri": storage_uri if container.storage_gateway else None,
                    }
                )
                _logger.info("subtitle_generated", scene_number=sp.scene_number)
            except Exception as exc:
                _logger.error(
                    "subtitle_generation_failed",
                    scene_number=sp.scene_number,
                    error=str(exc),
                )
                subtitle_errors.append(
                    {"scene_number": sp.scene_number, "error": str(exc)}
                )

        _set_step_io(
            workflow_state,
            step,
            {
                "scene_numbers": [sp.scene_number for sp in package.scene_packages],
                "narration_lengths": [len(sp.narration or "") for sp in package.scene_packages],
            },
            {
                "subtitles_generated": subtitles_generated,
                "errors": subtitle_errors,
            },
        )
        return workflow_state

    if step == WorkflowStep.RENDERING.value:
        _logger.info("rendering_step_started", project_id=str(project.id))
        _set_step_io(
            workflow_state,
            step,
            {"project_id": str(project.id)},
            {},
        )
        try:
            scenes = [
                s for s in await service._scene_repo.get_by_project(project.id)
                if getattr(s, "workflow_id", workflow_id) == workflow_id
            ]
            scene_ids = {s.id for s in scenes}
            assets = [
                a for a in await service._asset_repo.get_by_project(project.id)
                if a.scene_id in scene_ids
            ]
            asset_by_scene: dict[str, list] = {}
            for asset in assets:
                if asset.scene_id:
                    asset_by_scene.setdefault(str(asset.scene_id), []).append(asset)

            _set_step_io(
                workflow_state,
                step,
                {
                    "project_id": str(project.id),
                    "scene_count": len(scenes),
                    "asset_count": len(assets),
                },
                {},
            )

            output_path = (
                f"{container.config.storage.local_path}"
                f"/projects/{project.id}/final_video.mp4"
            )
            render_w, render_h = _target_dimensions(workflow_state)
            render_fps = 24 if _is_direct_cinematic(project) else 30
            project_package = await _render_composition_multi_pass(
                container, project, workflow_id, scenes, asset_by_scene, output_path,
                width=render_w, height=render_h, fps=render_fps,
            )

            # Generate a combined .srt subtitle file for the whole video
            # so it can be used as a separate subtitle track (e.g. for
            # YouTube upload or external players) instead of being
            # burned into the video.
            try:
                await _combine_scene_subtitles(
                    container, project, workflow_id, scenes
                )
            except Exception as sub_exc:
                _logger.warning(
                    "combined_subtitle_failed",
                    project_id=str(project.id),
                    error=str(sub_exc),
                )

            workflow_state.metadata.custom["final_video_path"] = project_package.final_video_path
            workflow_state.metadata.custom["render_report"] = project_package.render_report.model_dump()
            _set_step_io(
                workflow_state,
                step,
                {
                    "project_id": str(project.id),
                    "scene_count": len(scenes),
                    "asset_count": len(assets),
                },
                {
                    "final_video_path": project_package.final_video_path,
                    "render_time_seconds": project_package.render_report.render_time_seconds,
                    "output_size_bytes": project_package.render_report.output_size_bytes,
                },
            )
            _logger.info(
                "rendering_step_completed",
                project_id=str(project.id),
                output_path=project_package.final_video_path,
            )
        except Exception as exc:
            _logger.error("rendering_step_failed", project_id=str(project.id), error=str(exc))
            workflow_state.metadata.custom["rendering_error"] = str(exc)
            _set_step_io(
                workflow_state,
                step,
                {"project_id": str(project.id)},
                {"error": str(exc)},
            )

        return workflow_state

    if step == WorkflowStep.THUMBNAIL.value:
        _logger.info("thumbnail_step_started", project_id=str(project.id))
        _set_step_io(
            workflow_state,
            step,
            {"project_id": str(project.id)},
            {},
        )
        try:
            assets = await service._asset_repo.get_by_project(
                project.id, asset_type=AssetType.IMAGE
            )

            thumbnail_ref = ""
            if assets:
                # Use the first image asset as the thumbnail
                source = assets[0]
                thumbnail_ref = source.storage_ref
                _set_step_io(
                    workflow_state,
                    step,
                    {
                        "project_id": str(project.id),
                        "source_asset_id": str(source.id),
                    },
                    {},
                )
                tw, th = _target_dimensions(workflow_state)
                thumb = ThumbnailAsset(
                    project_id=project.id,
                    scene_id=source.scene_id,
                    width=tw,
                    height=th,
                    format="png",
                    is_default=True,
                    provider=source.provider,
                    generation_cost_usd=0.0,
                    generation_status=AssetGenerationStatus.READY,
                    storage_type=StorageType.LOCAL,
                    storage_ref=source.storage_ref,
                    quality_score=source.quality_score,
                )
                await service._asset_repo.create(thumb)
            else:
                # No image asset — extract a frame from the final video
                final_video = workflow_state.metadata.custom.get("final_video_path", "")
                if final_video and os.path.isfile(final_video):
                    import asyncio as _aio
                    import subprocess

                    thumb_dir = os.path.join(
                        get_settings().storage.local_path,
                        "projects",
                        str(project.id),
                        "thumbnails",
                    )
                    os.makedirs(thumb_dir, exist_ok=True)
                    thumb_path = os.path.join(thumb_dir, "thumbnail.png")
                    proc = await _aio.create_subprocess_exec(
                        "ffmpeg", "-y",
                        "-ss", "1",
                        "-i", final_video,
                        "-frames:v", "1",
                        "-q:v", "2",
                        thumb_path,
                        stdout=_aio.subprocess.PIPE,
                        stderr=_aio.subprocess.PIPE,
                    )
                    _, _err = await proc.communicate()
                    if proc.returncode == 0 and os.path.isfile(thumb_path):
                        with open(thumb_path, "rb") as f:
                            thumb_data = f.read()
                        storage_path = f"projects/{project.id}/thumbnails/thumbnail.png"
                        thumbnail_ref = await container.storage_gateway.upload(
                            thumb_data, storage_path, content_type="image/png"
                        )
                        tw, th = _target_dimensions(workflow_state)
                        thumb = ThumbnailAsset(
                            project_id=project.id,
                            scene_id=None,
                            width=tw,
                            height=th,
                            format="png",
                            is_default=True,
                            provider=AIProvider.GEMINI,
                            generation_cost_usd=0.0,
                            generation_status=AssetGenerationStatus.READY,
                            storage_type=StorageType.LOCAL,
                            storage_ref=thumbnail_ref,
                            quality_score=0.8,
                        )
                        await service._asset_repo.create(thumb)
                        _logger.info(
                            "thumbnail_extracted_from_video",
                            project_id=str(project.id),
                            uri=thumbnail_ref,
                        )
                    else:
                        _logger.warning(
                            "thumbnail_frame_extraction_failed",
                            project_id=str(project.id),
                            returncode=proc.returncode,
                        )
                else:
                    _logger.warning(
                        "thumbnail_no_image_or_video",
                        project_id=str(project.id),
                    )

            if thumbnail_ref:
                workflow_state.metadata.custom["thumbnail_uri"] = thumbnail_ref
                _set_step_io(
                    workflow_state,
                    step,
                    {"project_id": str(project.id)},
                    {"thumbnail_uri": thumbnail_ref},
                )
                _logger.info(
                    "thumbnail_step_completed",
                    project_id=str(project.id),
                    uri=thumbnail_ref,
                )
            else:
                _set_step_io(
                    workflow_state,
                    step,
                    {"project_id": str(project.id)},
                    {"warning": "no_thumbnail_source"},
                )
        except Exception as exc:
            _logger.error("thumbnail_step_failed", project_id=str(project.id), error=str(exc))
            _set_step_io(
                workflow_state,
                step,
                {"project_id": str(project.id)},
                {"error": str(exc)},
            )

        return workflow_state

    if step == WorkflowStep.SEO.value:
        _logger.info("seo_step_started", project_id=str(project.id))
        seo_input = {
            "project_title": project.title,
            "project_description": project.description or "",
        }
        _set_step_io(workflow_state, step, seo_input, {})
        try:
            prompt = (
                f"Generate YouTube metadata for a video about: {project.title}.\n"
                f"Description: {project.description or 'No description provided'}.\n"
                "Return only a JSON object with: title (string, max 60 chars), "
                "description (string, max 200 chars), tags (list of 5 strings)."
            )
            if container.llm_gateway is not None:
                seo_trace_id = None
                try:
                    seo_trace_id = workflow_state.metadata.custom.get("langfuse_trace_id")
                except (AttributeError, KeyError):
                    seo_trace_id = None
                result = await container.llm_gateway.generate_json(
                    prompt,
                    use_flash=True,
                    trace_id=seo_trace_id,
                    generation_name="agent: seo",
                )
                seo_payload = result.output if isinstance(result.output, dict) else {}
                workflow_state.metadata.custom["seo"] = seo_payload
                _set_step_io(workflow_state, step, seo_input, {"seo": seo_payload})
                _logger.info(
                    "seo_step_completed",
                    project_id=str(project.id),
                    title=seo_payload.get("title"),
                )
            else:
                fallback_seo = {
                    "title": project.title,
                    "description": project.description or project.title,
                    "tags": [project.title.lower().replace(" ", "_")],
                }
                workflow_state.metadata.custom["seo"] = fallback_seo
                _set_step_io(workflow_state, step, seo_input, {"seo": fallback_seo})
        except Exception as exc:
            _logger.error("seo_step_failed", project_id=str(project.id), error=str(exc))
            _set_step_io(workflow_state, step, seo_input, {"error": str(exc)})

        return workflow_state

    # PUBLISHING step is temporarily disabled; SEO is the final content step.
    # if step == WorkflowStep.PUBLISHING.value:
    #     _logger.info("publishing_step_started", project_id=str(project.id))
    #     try:
    #         video_path = workflow_state.metadata.custom.get("final_video_path", "")
    #         thumbnail_uri = workflow_state.metadata.custom.get("thumbnail_uri", "")
    #         seo = workflow_state.metadata.custom.get("seo", {})
    #         plan = {
    #             "project_id": str(project.id),
    #             "platforms": ["youtube"],
    #             "video_path": video_path,
    #             "thumbnail_path": thumbnail_uri,
    #             "metadata": seo,
    #             "status": "ready",
    #         }
    #         workflow_state.metadata.custom["publishing_plan"] = plan
    #         _logger.info(
    #             "publishing_plan_created",
    #             project_id=str(project.id),
    #             platforms=["youtube"],
    #         )
    #     except Exception as exc:
    #         _logger.error("publishing_step_failed", project_id=str(project.id), error=str(exc))
    #
    #     return workflow_state

    _logger.info(
        "workflow_step_skipped_output",
        project_id=str(project.id),
        workflow_id=str(workflow_id),
        step=step,
    )
    return workflow_state


async def _execute_workflow(
    engine: WorkflowEngine,
    container: ServiceContainer,
    workflow_state: WorkflowState,
    workflow_name: str,
) -> Any:
    return await engine.execute(
        workflow_name=workflow_name,
        initial_state=workflow_state,
        project_id=workflow_state.project.project_id,
        user_id=workflow_state.project.user_id,
        config=container.config,
        gateways={"llm": container.llm_gateway},
        services={
            "prompt_executor": container.prompt_executor,
            "cost_tracker": container.cost_tracker,
            "token_tracker": container.token_tracker,
            "event_bus": container.event_bus,
            "langfuse_client": container.langfuse_client,
            "metrics_collector": container.metrics_collector,
        },
        timeout_seconds=1200,
    )


def _find_provider(container, provider_type, name: str):
    """Return the registered provider with the given name, or ``None``."""
    for p in container.provider_registry.get_providers_by_type(provider_type):
        if getattr(p.provider_name, "value", p.provider_name) == name:
            return p
    return None


# Asset types that map to stock VIDEO for the research flow (free stock
# footage — never paid generation providers).
_STOCK_VIDEO_TYPES = {
    "stock_video",
    "stock_footage",
    "ai_video",
    "video",
    "mixed_assets",
    "animation",
    "animation_only",
}


def _is_direct_cinematic(project) -> bool:
    return (getattr(project, "metadata", None) or {}).get("production_mode") == "direct_cinematic"


def _build_direct_storyboard(project, state: WorkflowState) -> StoryboardPackage:
    metadata = getattr(project, "metadata", None) or {}
    duration = state.project.target_duration_seconds
    beats = metadata.get("clip_beats") or []
    expected = _plan_direct_cinematic_segments(duration)
    if not project.description or not metadata.get("visual_anchor") or len(beats) != len(expected) or any(not str(beat).strip() for beat in beats):
        raise ValueError(f"Direct cinematic storyboard requires a description, fixed visual anchor, and exactly {len(expected)} clip beats")
    provider = _active_video_provider()
    prompt_limit = MAX_KLING_PROMPT_CHARS if provider == "kling" else MAX_VEO_PROMPT_CHARS
    if provider == "kling" and not get_settings().kling.api_key:
        raise ValueError("Direct cinematic video requires FAL_KEY for Kling")
    if provider == "veo" and not get_settings().veo.enabled:
        raise ValueError("Direct cinematic video requires Veo to be enabled")
    if max_direct_prompt_chars(project.description, metadata["visual_anchor"], metadata.get("avoid", ""), beats) > prompt_limit:
        raise ValueError(f"Direct cinematic specification exceeds the {provider} prompt limit")
    narration = metadata.get("narration_text", "")
    if narration and len(narration.split()) > duration * 2:
        raise ValueError("Direct cinematic narration exceeds the duration budget")
    prompt = project.description.strip()
    scene = PlannedScene(scene_id="sc1", scene_number=1, title=project.title, narration=narration, estimated_duration_seconds=duration, scene_goal=prompt, scene_type="ai_video")
    visual = VisualPlan(scene_id="sc1", visual_description=prompt, environment=metadata["visual_anchor"].strip())
    per_second = (
        get_settings().cost.kling_per_second
        if provider == "kling"
        else get_settings().cost.veo_per_second
    )
    cost = round(per_second * _direct_cinematic_billed_seconds(duration), 4)
    decision = AssetSceneDecision(scene_id="sc1", asset_type="ai_video", estimated_generation_cost=cost, rationale=f"Direct cinematic {provider} generation")
    package_scene = ScenePackage(scene_id="sc1", scene_number=1, title=project.title, narration=narration, duration_seconds=duration, visual_prompt_summary=prompt, asset_type="ai_video", visual_plan=visual, estimated_cost=cost, metadata={"clip_beats": beats, "avoid": metadata.get("avoid", "")})
    return StoryboardPackage(
        scenes=SceneSegmentationResult(scenes=[scene], total_scenes=1, total_duration_seconds=duration),
        visual_plans=VisualStoryboardResult(visual_plans=[visual], shared_context=metadata["visual_anchor"].strip()),
        asset_decisions=AssetDecisionResult(decisions=[decision], total_estimated_cost=cost),
        continuity=ContinuityResult(aspect_ratio="9:16" if state.project.target_resolution == "1080x1920" else "16:9"),
        review=StoryboardReviewResult(passed=True), scene_packages=[package_scene], estimated_budget=cost,
    )


def _build_initial_state(project) -> WorkflowState:
    topic = project.title
    if project.description:
        topic = f"{topic}: {project.description}"
    aspect_ratio = (getattr(project, "metadata", None) or {}).get("aspect_ratio", "16:9")
    state = WorkflowState(
        project=ProjectInfo(
            project_id=project.id,
            user_id=project.owner_id,
            name=project.title,
            input_type=ProjectInputType.TOPIC,
            target_duration_seconds=project.target_duration_seconds or 600,
            target_resolution="1080x1920" if aspect_ratio == "9:16" else "1920x1080",
        ),
        topic=TopicData(raw_topic=topic),
    )
    state.metadata.custom["production_mode"] = (getattr(project, "metadata", None) or {}).get("production_mode", "explainer")
    return state


def _target_dimensions(workflow_state: WorkflowState) -> tuple[int, int]:
    """(width, height) for generated assets, from the project's chosen aspect."""
    res = workflow_state.project.target_resolution or "1920x1080"
    try:
        w, h = res.split("x", 1)
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 1920, 1080


def _get_research_package(state: WorkflowState) -> ResearchPackage:
    data = state.research.metadata.get("research_package")
    if not data:
        _logger.warning("research_package_missing_in_state")
        return ResearchPackage()
    return ResearchPackage.model_validate(data)


def _get_script_package(state: WorkflowState) -> ScriptPackage:
    data = state.script.metadata.get("script_package")
    if not data:
        _logger.warning("script_package_missing_in_state")
        return ScriptPackage()
    return ScriptPackage.model_validate(data)


def _get_storyboard_package(state: WorkflowState) -> StoryboardPackage:
    data = state.storyboard.metadata.get("storyboard_package")
    if not data:
        _logger.warning("storyboard_package_missing_in_state")
        # Fallback: assemble a package from the individual metadata keys
        # set by the storyboard agents.  This handles the case where the
        # final ``storyboard_review`` agent failed (e.g. due to an
        # exception) and never assembled the package.
        fallback = _assemble_storyboard_package_fallback(state)
        if fallback is not None:
            _logger.info("storyboard_package_assembled_fallback")
            # Save to metadata so subsequent calls don't need to reassemble
            state.storyboard.metadata["storyboard_package"] = fallback.model_dump()
            return fallback
        return StoryboardPackage()
    return StoryboardPackage.model_validate(data)


def _assemble_storyboard_package_fallback(
    state: WorkflowState,
) -> StoryboardPackage | None:
    """Assemble a ``StoryboardPackage`` from individual metadata keys.

    This is a fallback for when the ``storyboard_review`` agent failed
    and never assembled the final package.  It reads the metadata keys
    set by the preceding storyboard agents (story_analysis, story_beats,
    scenes, visual_plans, camera_plans, animation_plans, asset_decisions,
    continuity) and builds a package from them.

    Returns ``None`` if no scene data is available.
    """
    meta = state.storyboard.metadata
    scenes_data = meta.get("scenes", {})
    scenes = SceneSegmentationResult.model_validate(scenes_data)
    if not scenes.scenes:
        return None

    story_analysis = StoryAnalysis.model_validate(meta.get("story_analysis", {}))
    story_beats = StoryBeatResult.model_validate(meta.get("story_beats", {}))
    visual_plans = VisualStoryboardResult.model_validate(meta.get("visual_plans", {}))
    camera_plans = CameraPlanResult.model_validate(meta.get("camera_plans", {}))
    animation_plans = AnimationPlanResult.model_validate(meta.get("animation_plans", {}))
    asset_decisions = AssetDecisionResult.model_validate(meta.get("asset_decisions", {}))
    continuity = ContinuityResult.model_validate(meta.get("continuity", {}))
    review = StoryboardReviewResult.model_validate(meta.get("review", {}))

    # Build per-scene packages (same logic as StoryboardReviewAgent._assemble_package)
    vp_map = {p.scene_id: p for p in visual_plans.visual_plans}
    cp_map = {p.scene_id: p for p in camera_plans.camera_plans}
    ap_map = {p.scene_id: p for p in animation_plans.animation_plans}
    ad_map = {d.scene_id: d for d in asset_decisions.decisions}

    scene_packages: list[ScenePackage] = []
    for scene in scenes.scenes:
        vp = vp_map.get(scene.scene_id)
        cp = cp_map.get(scene.scene_id)
        ap = ap_map.get(scene.scene_id)
        ad = ad_map.get(scene.scene_id)

        scene_packages.append(ScenePackage(
            scene_id=scene.scene_id,
            scene_number=scene.scene_number,
            title=scene.title,
            narration=scene.narration,
            duration_seconds=scene.estimated_duration_seconds,
            visual_prompt_summary=vp.visual_description if vp else "",
            asset_type=ad.asset_type if ad else "",
            camera_plan=cp or CameraPlan(),
            animation_plan=ap or AnimationPlan(),
            visual_plan=vp or VisualPlan(),
            transition=ap.entrance_transition if ap else "",
            priority=scene.metadata.get("priority", "medium"),
            dependencies=scene.metadata.get("dependencies", []),
            estimated_cost=ad.estimated_generation_cost if ad else 0.0,
            estimated_tokens=scene.metadata.get("estimated_tokens", 0),
            quality_score=review.overall_score,
        ))

    quality = StoryboardQualityEvaluation(
        visual_diversity=review.visual_variety_score,
        scene_balance=review.scene_balance_score,
        narrative_consistency=review.narrative_consistency_score,
        camera_variety=review.camera_variety_score,
        animation_quality=review.animation_quality_score,
        budget_efficiency=review.budget_efficiency_score,
        overall_production_score=review.overall_score,
    )

    timeline_minutes = int(scenes.total_scenes * 1.3)

    return StoryboardPackage(
        story_analysis=story_analysis,
        story_beats=story_beats,
        scenes=scenes,
        visual_plans=visual_plans,
        camera_plans=camera_plans,
        animation_plans=animation_plans,
        asset_decisions=asset_decisions,
        continuity=continuity,
        review=review,
        quality=quality,
        scene_packages=scene_packages,
        estimated_budget=asset_decisions.total_estimated_cost,
        estimated_timeline_minutes=timeline_minutes,
    )


def _research_package_to_entity(
    project,
    workflow_id: UUID,
    package: ResearchPackage,
) -> Research:
    return Research(
        project_id=project.id,
        workflow_id=workflow_id,
        summary=package.summary.overview,
        timeline=package.summary.timeline,
        interesting_facts=package.summary.important_facts,
        sources=package.web_research.references or package.all_references,
        keywords=package.all_keywords,
        references=package.all_references,
        statistics={"items": package.summary.statistics},
        audience_pain_points=(
            package.audience.primary_persona.pain_points
            if package.audience and package.audience.primary_persona
            else []
        ),
        version=1,
        status=ResearchStatus.COMPLETED,
        created_by=None,
        created_at=_now(),
        updated_at=_now(),
    )


def _script_package_to_entity(
    project,
    workflow_id: UUID,
    package: ScriptPackage,
) -> Script:
    hook = ""
    if package.hook_result and package.hook_result.selected_hook:
        hook = package.hook_result.selected_hook.content
    cta = ""
    if package.cta_result and package.cta_result.primary_cta:
        cta = package.cta_result.primary_cta.content
    return Script(
        project_id=project.id,
        workflow_id=workflow_id,
        hook=hook,
        body=package.full_script or package.assemble_full_script(),
        cta=cta,
        word_count=package.word_count,
        estimated_duration_seconds=package.estimated_duration_seconds,
        version=1,
        language=project.language,
        status=ScriptStatus.APPROVED,
        created_by=None,
        created_at=_now(),
        updated_at=_now(),
    )


def _storyboard_package_to_entity(
    project,
    workflow_id: UUID,
    package: StoryboardPackage,
) -> Storyboard:
    total_duration = sum(
        sp.duration_seconds for sp in package.scene_packages
    )
    if not total_duration:
        total_duration = package.estimated_timeline_minutes * 60
    return Storyboard(
        project_id=project.id,
        workflow_id=workflow_id,
        version=1,
        scene_count=package.scene_count,
        estimated_duration_seconds=total_duration,
        style=project.video_style,
        status=StoryboardStatus.APPROVED,
        narrative_structure=package.story_analysis.narrative_flow,
        pacing_notes=package.continuity.transition_consistency or "",
        package_json=package.model_dump_json(),
        created_by=None,
        created_at=_now(),
        updated_at=_now(),
    )


def _scene_packages_to_entities(
    project,
    workflow_id: UUID,
    storyboard_id: UUID | None,
    package: StoryboardPackage,
) -> list[Scene]:
    scenes: list[Scene] = []
    default_visual = "ai_video" if _veo_pipeline_enabled() else "image"
    for idx, sp in enumerate(package.scene_packages, start=1):
        scene_number = sp.scene_number or idx
        visual = sp.asset_type or default_visual
        if visual == "ai_image":
            visual = "image"
        elif visual == "stock_video":
            visual = "stock_footage"
        scenes.append(
            Scene(
                project_id=project.id,
                storyboard_id=storyboard_id,
                workflow_id=workflow_id,
                scene_number=scene_number,
                title=sp.title or f"Scene {scene_number}",
                duration_seconds=float(sp.duration_seconds or 0),
                narration=sp.narration,
                importance_score=sp.quality_score or 0.8,
                emotion="curious",
                visual_type=_safe_visual_type(visual),
                camera_angle=_safe_camera_angle(
                    sp.camera_plan.camera_angle if sp.camera_plan else None
                ),
                camera_motion=_safe_camera_motion(
                    sp.camera_plan.movement if sp.camera_plan else None
                ),
                lens=sp.camera_plan.lens if sp.camera_plan else "standard",
                lighting=sp.visual_plan.lighting if sp.visual_plan else None,
                composition=sp.visual_plan.composition if sp.visual_plan else None,
                transition=TransitionType.CUT,
                subtitle=None,
                voice_timing={},
                background_music=None,
                sound_effects=[],
                generation_status=SceneGenerationStatus.PENDING,
                review_status=SceneReviewStatus.PENDING,
                created_by=None,
                created_at=_now(),
                updated_at=_now(),
            )
        )
    return scenes


def _safe_visual_type(value: str | None) -> VisualType:
    if not value:
        return VisualType.IMAGE
    try:
        return VisualType(value)
    except ValueError:
        _logger.warning("unknown_visual_type", value=value)
        return VisualType.IMAGE


def _veo_pipeline_enabled() -> bool:
    """True when the ASSET_GENERATION step will render scenes from Veo clips."""
    try:
        from src.core.config import get_settings

        return bool(getattr(get_settings().veo, "enabled", False))
    except Exception:
        return False


def _narration_to_srt(narration: str, scene_number: int, duration_seconds: int) -> str:
    """Convert a scene narration into an SRT subtitle with readable chunks.

    Splits the narration into ~8-word chunks and distributes them evenly
    across the scene duration.
    """
    words = narration.strip().split()
    if not words:
        return ""

    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= 8:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))

    total_secs = max(1, duration_seconds)
    chunk_dur = total_secs / len(chunks)

    def _fmt_ts(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines: list[str] = []
    for idx, chunk in enumerate(chunks):
        start = idx * chunk_dur
        end = min((idx + 1) * chunk_dur, total_secs)
        lines.append(str(idx + 1))
        lines.append(f"{_fmt_ts(start)} --> {_fmt_ts(end)}")
        lines.append(chunk)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _safe_camera_angle(value: str | None) -> CameraAngle | None:
    if not value:
        return None
    try:
        return CameraAngle(value)
    except ValueError:
        _logger.warning("unknown_camera_angle", value=value)
        return None


def _safe_camera_motion(value: str | None) -> CameraMotion | None:
    if not value:
        return None
    try:
        return CameraMotion(value)
    except ValueError:
        _logger.warning("unknown_camera_motion", value=value)
        return None
