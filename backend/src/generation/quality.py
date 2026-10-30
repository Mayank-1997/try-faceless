"""Quality Engine.

Evaluates generated assets on multiple dimensions:
- Visual quality
- Prompt alignment
- Voice quality
- Subtitle accuracy
- Consistency
- Brand compliance
- Overall production score
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.schema import AssetCategory, GeneratedAsset, QualityResult


class QualityEngine:
    """Evaluates the quality of generated assets.

    Produces a ``QualityResult`` with per-dimension scores and an
    overall composite score.  The overall score is a weighted average
    of the relevant dimensions for the asset category.
    """

    # Weights for overall score by category
    _WEIGHTS: dict[AssetCategory, dict[str, float]] = {
        AssetCategory.IMAGE: {
            "visual_quality": 0.4,
            "prompt_alignment": 0.3,
            "consistency": 0.2,
            "brand_compliance": 0.1,
        },
        AssetCategory.VIDEO: {
            "visual_quality": 0.35,
            "prompt_alignment": 0.25,
            "consistency": 0.2,
            "brand_compliance": 0.1,
            "voice_quality": 0.1,
        },
        AssetCategory.VOICE: {
            "voice_quality": 0.5,
            "prompt_alignment": 0.2,
            "consistency": 0.15,
            "brand_compliance": 0.15,
        },
        AssetCategory.SUBTITLE: {
            "subtitle_accuracy": 0.5,
            "prompt_alignment": 0.2,
            "consistency": 0.15,
            "brand_compliance": 0.15,
        },
        AssetCategory.THUMBNAIL: {
            "visual_quality": 0.4,
            "prompt_alignment": 0.3,
            "brand_compliance": 0.3,
        },
        AssetCategory.MUSIC: {
            "consistency": 0.4,
            "brand_compliance": 0.4,
            "prompt_alignment": 0.2,
        },
        AssetCategory.SOUND_EFFECT: {
            "consistency": 0.3,
            "brand_compliance": 0.3,
            "prompt_alignment": 0.4,
        },
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def evaluate(
        self,
        asset: GeneratedAsset,
        *,
        visual_quality: float | None = None,
        prompt_alignment: float | None = None,
        voice_quality: float | None = None,
        subtitle_accuracy: float | None = None,
        consistency: float | None = None,
        brand_compliance: float | None = None,
    ) -> QualityResult:
        """Evaluate the quality of a generated asset.

        If scores are not provided, defaults are used based on the
        asset's existing quality_score and metadata.

        Args:
            asset: The generated asset.
            visual_quality: Visual quality score (0.0 to 1.0).
            prompt_alignment: Prompt alignment score (0.0 to 1.0).
            voice_quality: Voice quality score (0.0 to 1.0).
            subtitle_accuracy: Subtitle accuracy score (0.0 to 1.0).
            consistency: Consistency score (0.0 to 1.0).
            brand_compliance: Brand compliance score (0.0 to 1.0).

        Returns:
            A ``QualityResult`` with all dimension scores and overall score.
        """
        base = asset.quality_score if asset.quality_score > 0 else 0.7

        vq = visual_quality if visual_quality is not None else base
        pa = prompt_alignment if prompt_alignment is not None else base
        vq_voice = voice_quality if voice_quality is not None else base
        sa = subtitle_accuracy if subtitle_accuracy is not None else base
        cons = consistency if consistency is not None else base
        bc = brand_compliance if brand_compliance is not None else base

        # Compute overall score using category-specific weights
        weights = self._WEIGHTS.get(asset.category, self._WEIGHTS[AssetCategory.IMAGE])
        scores = {
            "visual_quality": vq,
            "prompt_alignment": pa,
            "voice_quality": vq_voice,
            "subtitle_accuracy": sa,
            "consistency": cons,
            "brand_compliance": bc,
        }

        overall = 0.0
        for dim, weight in weights.items():
            overall += weight * scores.get(dim, 0.0)

        result = QualityResult(
            asset_id=asset.id,
            visual_quality=vq,
            prompt_alignment=pa,
            voice_quality=vq_voice,
            subtitle_accuracy=sa,
            consistency=cons,
            brand_compliance=bc,
            overall_score=overall,
            metadata={
                "category": asset.category.value,
                "weights": weights,
            },
        )

        self._logger.info(
            "quality_evaluated",
            asset_id=str(asset.id),
            overall_score=overall,
            category=asset.category.value,
        )
        return result

    def evaluate_batch(self, assets: list[GeneratedAsset]) -> list[QualityResult]:
        """Evaluate quality for a batch of assets.

        Args:
            assets: List of generated assets.

        Returns:
            List of ``QualityResult`` objects.
        """
        return [self.evaluate(a) for a in assets]

    def compute_project_quality(self, results: list[QualityResult]) -> float:
        """Compute an overall quality score for a project.

        Args:
            results: Quality results for all assets in the project.

        Returns:
            Average overall quality score.
        """
        if not results:
            return 0.0
        return sum(r.overall_score for r in results) / len(results)
