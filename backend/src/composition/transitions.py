"""Transition Engine.

Supports fade, crossfade, slide, push, zoom, blur, dissolve, and custom
transitions with easing curves.
"""

from __future__ import annotations

from src.composition.schema import EasingType, Transition, TransitionType
from src.core.logging import get_logger


class TransitionEngine:
    """Generates and manages transitions between scenes and clips.

    Produces ``Transition`` configurations that the renderer
    translates into FFmpeg xfade filter expressions.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def fade(self, duration: float = 1.0, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a fade transition.

        Args:
            duration: Transition duration in seconds.
            from_scene: Source scene ID.
            to_scene: Target scene ID.

        Returns:
            A fade ``Transition``.
        """
        return Transition(
            transition_type=TransitionType.FADE,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
        )

    def crossfade(self, duration: float = 1.0, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a crossfade transition."""
        return Transition(
            transition_type=TransitionType.CROSSFADE,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
        )

    def slide(self, duration: float = 0.5, *, direction: str = "left", from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a slide transition.

        Args:
            duration: Transition duration in seconds.
            direction: Slide direction (left, right, up, down).
            from_scene: Source scene ID.
            to_scene: Target scene ID.

        Returns:
            A slide ``Transition``.
        """
        return Transition(
            transition_type=TransitionType.SLIDE,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
            params={"direction": direction},
        )

    def push(self, duration: float = 0.5, *, direction: str = "right", from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a push transition."""
        return Transition(
            transition_type=TransitionType.PUSH,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
            params={"direction": direction},
        )

    def zoom(self, duration: float = 0.5, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a zoom transition."""
        return Transition(
            transition_type=TransitionType.ZOOM,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
        )

    def blur(self, duration: float = 0.5, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a blur transition."""
        return Transition(
            transition_type=TransitionType.BLUR,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
        )

    def dissolve(self, duration: float = 0.5, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a dissolve transition."""
        return Transition(
            transition_type=TransitionType.DISSOLVE,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
        )

    def custom(self, name: str, duration: float = 0.5, params: dict | None = None, *, from_scene: str = "", to_scene: str = "") -> Transition:
        """Create a custom transition.

        Args:
            name: Custom transition name.
            duration: Transition duration in seconds.
            params: Custom parameters.
            from_scene: Source scene ID.
            to_scene: Target scene ID.

        Returns:
            A custom ``Transition``.
        """
        return Transition(
            transition_type=TransitionType.CUSTOM,
            duration=duration,
            from_scene_id=from_scene,
            to_scene_id=to_scene,
            params={"name": name, **(params or {})},
        )

    def to_ffmpeg_xfade(self, transition: Transition, offset: float = 0.0) -> str:
        """Convert a transition to an FFmpeg xfade filter expression.

        Args:
            transition: The transition.
            offset: Offset in seconds where the transition starts.

        Returns:
            FFmpeg xfade filter string.
        """
        type_map = {
            TransitionType.FADE: "fade",
            TransitionType.CROSSFADE: "fade",
            TransitionType.SLIDE: "slideleft",
            TransitionType.PUSH: "slideleft",
            TransitionType.ZOOM: "zoomin",
            TransitionType.BLUR: "smoothleft",
            TransitionType.DISSOLVE: "dissolve",
        }

        xfade_type = type_map.get(transition.transition_type, "fade")

        # Handle direction for slide/push
        if transition.transition_type in (TransitionType.SLIDE, TransitionType.PUSH):
            direction = transition.params.get("direction", "left")
            dir_map = {"left": "slideleft", "right": "slideright", "up": "slideup", "down": "slidedown"}
            xfade_type = dir_map.get(direction, "slideleft")

        return f"xfade=transition={xfade_type}:duration={transition.duration}:offset={offset}"

    def list_transition_types(self) -> list[str]:
        """List all available transition types."""
        return [t.value for t in TransitionType]
