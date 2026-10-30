"""Render Planner.

Generates a ``RenderPlan`` before rendering begins.

Estimates:
- Execution time
- CPU usage
- Memory usage
- Disk usage
- GPU usage
- Rendering complexity
- Expected output size
- Potential bottlenecks
- Optimization suggestions

The planner optimizes execution before rendering begins.
"""

from __future__ import annotations

from typing import Any

from src.composition.events import CompositionEventEmitter
from src.composition.schema import CompositionDocument, RenderPlan, TrackType
from src.core.logging import get_logger


class RenderPlanner:
    """Plans rendering execution before it begins.

    Analyzes the composition and produces a ``RenderPlan`` with
    resource estimates and optimization suggestions.
    """

    def __init__(self, event_emitter: CompositionEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or CompositionEventEmitter()

    async def plan(self, composition: CompositionDocument) -> RenderPlan:
        """Generate a render plan for a composition.

        Args:
            composition: The composition to plan for.

        Returns:
            A ``RenderPlan`` with estimates and suggestions.
        """
        duration = composition.total_duration
        scene_count = composition.scene_count
        track_count = composition.track_count
        clip_count = sum(len(t.clips) for t in composition.timeline.tracks)
        transition_count = len(composition.transitions)
        effect_count = len(composition.effects)
        animation_count = len(composition.image_animations)
        text_count = len(composition.text_overlays)

        # Complexity score (0.0 to 10.0)
        complexity = (
            scene_count * 0.5
            + clip_count * 0.2
            + transition_count * 0.3
            + effect_count * 0.4
            + animation_count * 0.3
            + text_count * 0.2
        )
        complexity = min(10.0, complexity)

        # Time estimates (rough heuristics)
        base_render_time = duration * 1.5  # 1.5x realtime for 1080p
        is_4k = composition.export_profile.width >= 3840 or composition.export_profile.resolution == "3840x2160"
        is_1440p = composition.export_profile.width >= 2560 or composition.export_profile.resolution == "2560x1440"
        if is_4k or is_1440p:
            base_render_time *= 3.0  # 4K/1440p is much slower
        transition_time = transition_count * 2.0  # each transition adds ~2s
        effect_time = effect_count * 1.0
        encoding_time = duration * 0.5

        total_time = base_render_time + transition_time + effect_time + encoding_time

        # Memory estimates
        base_memory = 256  # MB
        per_track_memory = 32
        per_effect_memory = 64
        memory_mb = base_memory + track_count * per_track_memory + effect_count * per_effect_memory
        if is_4k:
            memory_mb *= 2

        # Disk estimates
        output_size_mb = int(duration * 2.5)  # ~2.5MB/s for 1080p H.264
        if is_4k:
            output_size_mb *= 4
        disk_mb = output_size_mb + 512  # temp files

        # CPU/GPU
        cpu_usage = min(100.0, 30.0 + complexity * 7.0)
        gpu_usage = 0.0
        if composition.export_profile.hardware_acceleration:
            gpu_usage = min(100.0, 20.0 + complexity * 5.0)

        # Bottlenecks
        bottlenecks: list[str] = []
        if complexity > 7.0:
            bottlenecks.append("High rendering complexity — consider reducing effects or transitions")
        if memory_mb > 2048:
            bottlenecks.append(f"High memory usage ({memory_mb}MB) — may cause swapping")
        if duration > 600:
            bottlenecks.append("Long video (>10min) — consider segment rendering")
        if transition_count > scene_count:
            bottlenecks.append("Many transitions — each adds render time")

        # Optimization suggestions
        suggestions: list[str] = []
        if composition.export_profile.preset not in ("fast", "veryfast", "ultrafast"):
            suggestions.append("Use faster encoding preset for reduced render time")
        if not composition.export_profile.hardware_acceleration:
            suggestions.append("Enable hardware acceleration (NVENC/QSV) for faster encoding")
        if effect_count > 10:
            suggestions.append("Consider pre-rendering effects to reduce real-time processing")
        if scene_count > 20:
            suggestions.append("Consider parallel scene rendering for faster throughput")

        # Scene render order
        scene_order = [s.scene_id for s in composition.scenes]

        plan = RenderPlan(
            composition_id=composition.id,
            estimated_execution_time=total_time,
            estimated_cpu_usage=cpu_usage,
            estimated_memory_mb=memory_mb,
            estimated_disk_mb=disk_mb,
            estimated_gpu_usage=gpu_usage,
            rendering_complexity=complexity,
            expected_output_size_mb=output_size_mb,
            potential_bottlenecks=bottlenecks,
            optimization_suggestions=suggestions,
            scene_render_order=scene_order,
            parallelizable=scene_count > 5 and complexity < 8.0,
        )

        await self._events.emit_render_planned(composition.id, total_time, complexity)

        self._logger.info(
            "render_planned",
            composition_id=str(composition.id),
            estimated_time=total_time,
            complexity=complexity,
            memory_mb=memory_mb,
            bottlenecks=len(bottlenecks),
        )

        return plan
