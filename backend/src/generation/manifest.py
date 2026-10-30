"""Asset Manifest Builder.

Generates an ``AssetManifest`` from generated assets.

For every scene includes:
- Scene ID
- Image
- Video
- Voice
- Music
- Subtitles
- Effects
- Estimated render time
- Estimated scene cost
- Dependencies
- Generation status

At project level includes:
- Total duration
- Total cost
- Total assets
- Estimated rendering time

The Rendering Engine in Phase 10 must consume only ``AssetManifest``.
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.events import GenerationEventEmitter
from src.generation.schema import (
    AssetCategory,
    AssetManifest,
    GeneratedAsset,
    JobStatus,
    SceneAssetManifest,
)


class AssetManifestBuilder:
    """Builds an ``AssetManifest`` from generated assets.

    Groups assets by scene, computes per-scene and project-level
    totals, and produces the final manifest consumed by the
    Rendering Engine (Phase 10).
    """

    def __init__(self, event_emitter: GenerationEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or GenerationEventEmitter()

    def build(
        self,
        assets: list[GeneratedAsset],
        *,
        project_id: str = "",
        scene_ids: list[str] | None = None,
        scene_durations: dict[str, float] | None = None,
    ) -> AssetManifest:
        """Build an asset manifest from generated assets.

        Args:
            assets: All generated assets.
            project_id: Project identifier.
            scene_ids: Ordered list of scene IDs (for proper ordering).
            scene_durations: Mapping of scene_id to duration in seconds.

        Returns:
            A complete ``AssetManifest``.
        """
        # Group assets by scene
        scene_assets: dict[str, list[GeneratedAsset]] = {}
        for asset in assets:
            sid = asset.scene_id or "unknown"
            if sid not in scene_assets:
                scene_assets[sid] = []
            scene_assets[sid].append(asset)

        # Determine scene order
        if scene_ids is None:
            scene_ids = sorted(scene_assets.keys())

        if scene_durations is None:
            scene_durations = {}

        # Build per-scene manifests
        scene_manifests: list[SceneAssetManifest] = []
        total_cost = 0.0
        total_assets = 0
        total_duration = 0.0
        total_render_time = 0.0

        for idx, scene_id in enumerate(scene_ids):
            scene_asset_list = scene_assets.get(scene_id, [])
            manifest = self._build_scene_manifest(scene_id, idx + 1, scene_asset_list)
            if scene_id in scene_durations:
                manifest.estimated_render_time_seconds = scene_durations[scene_id] * 0.5  # rough estimate
            scene_manifests.append(manifest)
            total_cost += manifest.estimated_scene_cost
            total_assets += sum(1 for a in scene_asset_list if a.storage_uri or a.metadata.get("placeholder"))
            total_duration += scene_durations.get(scene_id, 0.0)
            total_render_time += manifest.estimated_render_time_seconds

        manifest = AssetManifest(
            project_id=project_id,
            scene_manifests=scene_manifests,
            total_duration_seconds=total_duration,
            total_cost=total_cost,
            total_assets=total_assets,
            estimated_rendering_time_seconds=total_render_time,
        )

        self._logger.info(
            "manifest_built",
            project_id=project_id,
            scenes=len(scene_manifests),
            total_assets=total_assets,
            total_cost=total_cost,
        )
        return manifest

    def _build_scene_manifest(
        self,
        scene_id: str,
        scene_number: int,
        assets: list[GeneratedAsset],
    ) -> SceneAssetManifest:
        """Build a manifest for a single scene."""
        manifest = SceneAssetManifest(
            scene_id=scene_id,
            scene_number=scene_number,
        )

        scene_cost = 0.0
        all_completed = True

        for asset in assets:
            if asset.category == AssetCategory.IMAGE:
                manifest.image = asset
            elif asset.category == AssetCategory.VIDEO:
                manifest.video = asset
            elif asset.category == AssetCategory.VOICE:
                manifest.voice = asset
            elif asset.category == AssetCategory.MUSIC:
                manifest.music = asset
            elif asset.category == AssetCategory.SUBTITLE:
                manifest.subtitles = asset
            elif asset.category == AssetCategory.SOUND_EFFECT:
                manifest.effects.append(asset)

            scene_cost += asset.cost_usd
            # Check if generation is complete (has storage URI or is placeholder)
            if not (asset.storage_uri or asset.metadata.get("placeholder") or asset.metadata.get("framework_only")):
                all_completed = False

        manifest.estimated_scene_cost = scene_cost
        manifest.generation_status = JobStatus.COMPLETED if all_completed and assets else JobStatus.QUEUED
        return manifest
