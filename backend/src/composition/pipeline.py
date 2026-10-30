"""Rendering Pipeline.

Pipeline stages:
1. Load Composition
2. Validate Composition
3. Prepare Assets
4. Compile Timeline
5. Compose Layers
6. Apply Animations
7. Apply Effects
8. Render Subtitles
9. Mix Audio
10. Encode Video
11. Validate Output
12. Optimize Output
13. Generate Project Package
"""

from __future__ import annotations

import time
from typing import Any

from src.composition.events import CompositionEventEmitter, CompositionEvents
from src.composition.ffmpeg_renderer import FFmpegCompositionRenderer
from src.composition.optimizer import CompositionOptimizer
from src.composition.renderer import CompositionRenderer
from src.composition.schema import (
    CompositionDocument,
    ProjectPackage,
    QualityReport,
    RenderMetrics,
    RenderProgress,
    RenderStatus,
)
from src.composition.timeline_compiler import TimelineCompiler
from src.composition.validator import CompositionValidator
from src.core.logging import get_logger


class RenderingPipeline:
    """Orchestrates the full rendering pipeline.

    Executes all pipeline stages in order, emitting events at each
    stage.  Delegates actual rendering to the ``CompositionRenderer``.
    """

    def __init__(
        self,
        renderer: CompositionRenderer | None = None,
        *,
        validator: CompositionValidator | None = None,
        optimizer: CompositionOptimizer | None = None,
        timeline_compiler: TimelineCompiler | None = None,
        event_emitter: CompositionEventEmitter | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._renderer = renderer or FFmpegCompositionRenderer()
        self._validator = validator or CompositionValidator()
        self._optimizer = optimizer or CompositionOptimizer()
        self._timeline_compiler = timeline_compiler or TimelineCompiler()
        self._events = event_emitter or CompositionEventEmitter()
        self._progress = RenderProgress()

    async def execute(
        self,
        composition: CompositionDocument,
        output_path: str,
        *,
        project_id: str = "",
    ) -> ProjectPackage:
        """Execute the full rendering pipeline.

        Args:
            composition: The composition to render.
            output_path: Destination for the final video.
            project_id: Project identifier.

        Returns:
            A ``ProjectPackage`` with all outputs.
        """
        start_time = time.monotonic()
        corr_id = str(composition.id)

        # Stage 1: Load Composition
        self._progress.current_stage = "load_composition"
        await self._renderer.load(composition)
        self._progress.stages_completed.append("load_composition")

        # Stage 2: Validate Composition
        self._progress.current_stage = "validate_composition"
        errors = await self._renderer.validate()
        if errors:
            self._logger.error("renderer_validation_failed", errors=errors)
            raise ValueError(f"Renderer validation failed: {'; '.join(errors)}")

        validation_meta = await self._validator.validate(composition)
        if not validation_meta.valid:
            raise ValueError(f"Composition validation failed: {'; '.join(validation_meta.errors)}")
        self._progress.stages_completed.append("validate_composition")

        # Stage 3: Prepare Assets
        self._progress.current_stage = "prepare_assets"
        await self._renderer.prepare(output_path)
        self._progress.stages_completed.append("prepare_assets")

        # Stage 4: Compile Timeline
        self._progress.current_stage = "compile_timeline"
        compiled = self._timeline_compiler.compile(composition)
        self._progress.total_frames = compiled["total_frames"]
        self._progress.stages_completed.append("compile_timeline")

        # Stage 5: Optimize
        self._progress.current_stage = "optimize"
        self._optimizer.optimize(composition)
        self._progress.stages_completed.append("optimize")

        # Stage 6-10: Render (delegated to renderer)
        self._progress.current_stage = "rendering"
        self._progress.status = RenderStatus.RENDERING
        await self._events.emit_rendering_started(
            job_id=composition.id, composition_id=composition.id, correlation_id=corr_id,
        )

        rendered_path = await self._renderer.render()
        self._progress.stages_completed.append("rendering")

        # Stage 11: Validate Output
        self._progress.current_stage = "validate_output"
        quality_report = await self._renderer.validate_output(rendered_path)
        self._progress.stages_completed.append("validate_output")

        # Collect metrics
        metrics = await self._renderer.collect_metrics()
        metrics.render_time_seconds = time.monotonic() - start_time

        # Cleanup
        await self._renderer.cleanup()

        # Stage 12: Generate Project Package
        self._progress.current_stage = "generate_package"
        package = ProjectPackage(
            project_id=project_id or composition.project_id,
            composition_document=composition,
            final_video_path=rendered_path,
            render_report=metrics,
            quality_report=quality_report,
            performance_metrics=metrics,
            timeline=composition.timeline,
            cost_summary={
                "total_cost": composition.metadata.get("total_cost", 0.0),
                "render_time_seconds": metrics.render_time_seconds,
            },
        )
        self._progress.stages_completed.append("generate_package")

        # Complete
        self._progress.status = RenderStatus.COMPLETED
        self._progress.progress_percentage = 100.0

        await self._events.emit_rendering_completed(
            job_id=composition.id, output_path=rendered_path, render_time=metrics.render_time_seconds,
            correlation_id=corr_id,
        )
        await self._events.emit_project_package_generated(
            package_id=package.id, project_id=package.project_id, correlation_id=corr_id,
        )

        self._logger.info(
            "pipeline_complete",
            composition_id=str(composition.id),
            output_path=rendered_path,
            render_time=metrics.render_time_seconds,
            quality_pass=quality_report.overall_pass,
        )

        return package

    async def cancel(self) -> None:
        """Cancel the current rendering operation."""
        await self._renderer.cancel()
        self._progress.status = RenderStatus.CANCELLED

    @property
    def progress(self) -> RenderProgress:
        """Current pipeline progress."""
        return self._progress
