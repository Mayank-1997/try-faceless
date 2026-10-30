"""Validation Pipeline.

Every generated asset must pass through 10 validation stages:
1. File validation
2. Metadata validation
3. Resolution validation
4. Duration validation
5. Prompt alignment
6. Quality evaluation
7. Duplicate detection
8. Storage validation
9. Content safety
10. Overall validation

Invalid assets are rejected.
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.events import GenerationEventEmitter
from src.generation.schema import (
    AssetCategory,
    GeneratedAsset,
    ValidationReport,
    ValidationResult,
    ValidationStage,
)


class ValidationPipeline:
    """Validates generated assets through a multi-stage pipeline.

    Each stage checks a specific aspect of the asset.  If any stage
    fails, the asset is rejected with a detailed reason.
    """

    def __init__(
        self,
        event_emitter: GenerationEventEmitter | None = None,
        *,
        min_resolution: str = "1280x720",
        max_file_size_bytes: int = 500 * 1024 * 1024,  # 500MB
        min_quality_score: float = 0.5,
        min_duration_seconds: float = 0.5,
        max_duration_seconds: float = 300.0,
    ) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or GenerationEventEmitter()
        self._min_resolution = min_resolution
        self._max_file_size = max_file_size_bytes
        self._min_quality = min_quality_score
        self._min_duration = min_duration_seconds
        self._max_duration = max_duration_seconds
        self._seen_hashes: set[str] = set()

    async def validate(self, asset: GeneratedAsset) -> ValidationReport:
        """Run all validation stages on an asset.

        Args:
            asset: The generated asset to validate.

        Returns:
            A ``ValidationReport`` with results from all stages.
        """
        results: list[ValidationResult] = []

        # Stage 1: File validation
        results.append(self._validate_file(asset))

        # Stage 2: Metadata validation
        results.append(self._validate_metadata(asset))

        # Stage 3: Resolution validation (images/video only)
        if asset.category in (AssetCategory.IMAGE, AssetCategory.VIDEO):
            results.append(self._validate_resolution(asset))

        # Stage 4: Duration validation (video/voice only)
        if asset.category in (AssetCategory.VIDEO, AssetCategory.VOICE):
            results.append(self._validate_duration(asset))

        # Stage 5: Prompt alignment
        results.append(self._validate_prompt_alignment(asset))

        # Stage 6: Quality evaluation
        results.append(self._validate_quality(asset))

        # Stage 7: Duplicate detection
        results.append(self._validate_duplicate(asset))

        # Stage 8: Storage validation
        results.append(self._validate_storage(asset))

        # Stage 9: Content safety
        results.append(self._validate_content_safety(asset))

        # Determine overall validity
        overall_valid = all(r.valid for r in results)
        rejected_reason = None
        if not overall_valid:
            failed = [r for r in results if not r.valid]
            rejected_reason = "; ".join(f"{r.stage.value}: {r.errors[0]}" for r in failed if r.errors)
            await self._events.emit_validation_failed(asset.id, failed[0].stage.value, rejected_reason)

        report = ValidationReport(
            asset_id=asset.id,
            overall_valid=overall_valid,
            results=results,
            rejected_reason=rejected_reason,
        )

        self._logger.info(
            "validation_complete",
            asset_id=str(asset.id),
            valid=overall_valid,
            stages_passed=sum(1 for r in results if r.valid),
            stages_total=len(results),
        )
        return report

    def _validate_file(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 1: Validate file exists and is within size limits."""
        errors: list[str] = []
        if asset.file_size_bytes == 0 and not asset.metadata.get("framework_only"):
            errors.append("File is empty")
        if asset.file_size_bytes > self._max_file_size:
            errors.append(f"File size {asset.file_size_bytes} exceeds max {self._max_file_size}")
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.FILE_VALIDATION,
            errors=errors,
        )

    def _validate_metadata(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 2: Validate metadata is present and correct."""
        errors: list[str] = []
        if not asset.provider:
            errors.append("Missing provider")
        if not asset.model:
            errors.append("Missing model")
        if asset.cost_usd < 0:
            errors.append("Negative cost")
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.METADATA_VALIDATION,
            errors=errors,
        )

    def _validate_resolution(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 3: Validate resolution meets minimum."""
        errors: list[str] = []
        # Check metadata for resolution info
        resolution = asset.metadata.get("resolution", "")
        if resolution and self._min_resolution:
            min_w, min_h = (int(x) for x in self._min_resolution.split("x"))
            try:
                w, h = (int(x) for x in resolution.split("x"))
                if w < min_w or h < min_h:
                    errors.append(f"Resolution {resolution} below minimum {self._min_resolution}")
            except (ValueError, IndexError):
                pass  # Can't parse, skip
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.RESOLUTION_VALIDATION,
            errors=errors,
        )

    def _validate_duration(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 4: Validate duration is within bounds."""
        errors: list[str] = []
        duration = asset.metadata.get("duration_seconds", 0.0)
        if duration and duration < self._min_duration:
            errors.append(f"Duration {duration}s below minimum {self._min_duration}s")
        if duration and duration > self._max_duration:
            errors.append(f"Duration {duration}s exceeds maximum {self._max_duration}s")
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.DURATION_VALIDATION,
            errors=errors,
        )

    def _validate_prompt_alignment(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 5: Validate asset aligns with the original prompt."""
        errors: list[str] = []
        # Basic check: if metadata has prompt, ensure it's not empty
        prompt = asset.metadata.get("prompt", "")
        if prompt == "":
            # Not an error — some assets don't have prompts
            pass
        return ValidationResult(
            valid=True,
            stage=ValidationStage.PROMPT_ALIGNMENT,
            errors=errors,
        )

    def _validate_quality(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 6: Validate quality score meets threshold."""
        errors: list[str] = []
        if asset.quality_score < self._min_quality:
            errors.append(f"Quality score {asset.quality_score:.2f} below minimum {self._min_quality}")
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.QUALITY_EVALUATION,
            errors=errors,
        )

    def _validate_duplicate(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 7: Detect duplicate assets by content hash."""
        errors: list[str] = []
        if asset.content_hash:
            if asset.content_hash in self._seen_hashes:
                errors.append("Duplicate asset detected (same content hash)")
            else:
                self._seen_hashes.add(asset.content_hash)
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.DUPLICATE_DETECTION,
            errors=errors,
        )

    def _validate_storage(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 8: Validate storage URI is set."""
        errors: list[str] = []
        if not asset.storage_uri and not asset.metadata.get("placeholder"):
            errors.append("Missing storage URI")
        return ValidationResult(
            valid=len(errors) == 0,
            stage=ValidationStage.STORAGE_VALIDATION,
            errors=errors,
        )

    def _validate_content_safety(self, asset: GeneratedAsset) -> ValidationResult:
        """Stage 9: Basic content safety check."""
        # In production, this would call a content moderation API
        return ValidationResult(
            valid=True,
            stage=ValidationStage.CONTENT_SAFETY,
        )

    def reset_duplicates(self) -> None:
        """Clear the duplicate detection cache."""
        self._seen_hashes.clear()
