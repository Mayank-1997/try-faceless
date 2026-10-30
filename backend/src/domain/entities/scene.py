"""Scene entity — individual scene definition within a project.

Scenes are one of the most important entities. Each scene contains
narration, visual directives (camera, lighting, composition), audio
cues, generation status, and review status.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import (
    CameraAngle,
    CameraMotion,
    SceneGenerationStatus,
    SceneReviewStatus,
    TransitionType,
    VisualType,
)


class Scene:
    """A single scene within a project's storyboard.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        storyboard_id: UUID of the storyboard that defined this scene.
        workflow_id: UUID of the workflow that produced this scene.
        scene_number: 1-based ordinal within the storyboard.
        title: Short scene title.
        duration_seconds: Planned scene duration.
        narration: Full narration text for this scene.
        importance_score: Visual importance (0.0–1.0).
        emotion: Emotional tone of the scene.
        visual_type: Type of visual content required.
        camera_angle: Camera angle directive.
        camera_motion: Camera movement directive.
        lens: Lens specification.
        lighting: Lighting description.
        composition: Composition/framing description.
        transition: Transition to the next scene.
        subtitle: Subtitle text for this scene.
        voice_timing: Voice timing metadata.
        background_music: Background music suggestion.
        sound_effects: List of sound effect descriptions.
        generation_status: Asset generation lifecycle.
        review_status: Human review status.
        created_by: UUID of the user or agent that created this scene.
        updated_by: UUID of the last user who updated this scene.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        storyboard_id: UUID | None = None,
        workflow_id: UUID | None = None,
        scene_number: int = 0,
        title: str = "",
        duration_seconds: float = 0.0,
        narration: str = "",
        importance_score: float = 0.0,
        emotion: str = "",
        visual_type: VisualType = VisualType.IMAGE,
        camera_angle: CameraAngle | None = None,
        camera_motion: CameraMotion | None = None,
        lens: str | None = None,
        lighting: str | None = None,
        composition: str | None = None,
        transition: TransitionType | None = None,
        subtitle: str | None = None,
        voice_timing: dict[str, Any] | None = None,
        background_music: str | None = None,
        sound_effects: list[str] | None = None,
        generation_status: SceneGenerationStatus = SceneGenerationStatus.PENDING,
        review_status: SceneReviewStatus = SceneReviewStatus.PENDING,
        created_by: UUID | None = None,
        updated_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.storyboard_id = storyboard_id
        self.workflow_id = workflow_id
        self.scene_number = scene_number
        self.title = title
        self.duration_seconds = duration_seconds
        self.narration = narration
        self.importance_score = importance_score
        self.emotion = emotion
        self.visual_type = visual_type
        self.camera_angle = camera_angle
        self.camera_motion = camera_motion
        self.lens = lens
        self.lighting = lighting
        self.composition = composition
        self.transition = transition
        self.subtitle = subtitle
        self.voice_timing = voice_timing or {}
        self.background_music = background_music
        self.sound_effects = sound_effects or []
        self.generation_status = generation_status
        self.review_status = review_status
        self.created_by = created_by
        self.updated_by = updated_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def mark_generated(self) -> None:
        """Mark scene assets as fully generated."""
        self.generation_status = SceneGenerationStatus.GENERATED
        self.updated_at = datetime.now(dt_timezone.utc)

    def mark_failed(self) -> None:
        """Mark scene asset generation as failed."""
        self.generation_status = SceneGenerationStatus.FAILED
        self.updated_at = datetime.now(dt_timezone.utc)

    def approve(self) -> None:
        """Approve the scene in human review."""
        self.review_status = SceneReviewStatus.APPROVED
        self.updated_at = datetime.now(dt_timezone.utc)

    def reject(self) -> None:
        """Reject the scene in human review."""
        self.review_status = SceneReviewStatus.REJECTED
        self.updated_at = datetime.now(dt_timezone.utc)

    def request_revision(self) -> None:
        """Request revision for the scene."""
        self.review_status = SceneReviewStatus.NEEDS_REVISION
        self.updated_at = datetime.now(dt_timezone.utc)

    @property
    def is_ready_for_review(self) -> bool:
        """Check if scene is ready for human review."""
        return self.generation_status == SceneGenerationStatus.GENERATED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "storyboard_id": str(self.storyboard_id) if self.storyboard_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "scene_number": self.scene_number,
            "title": self.title,
            "duration_seconds": self.duration_seconds,
            "narration": self.narration,
            "importance_score": self.importance_score,
            "emotion": self.emotion,
            "visual_type": self.visual_type.value,
            "camera_angle": self.camera_angle.value if self.camera_angle else None,
            "camera_motion": self.camera_motion.value if self.camera_motion else None,
            "lens": self.lens,
            "lighting": self.lighting,
            "composition": self.composition,
            "transition": self.transition.value if self.transition else None,
            "subtitle": self.subtitle,
            "voice_timing": self.voice_timing,
            "background_music": self.background_music,
            "sound_effects": self.sound_effects,
            "generation_status": self.generation_status.value,
            "review_status": self.review_status.value,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
