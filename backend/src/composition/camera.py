"""Camera Motion Engine.

Supports pan, zoom, tilt, orbit, Ken Burns, parallax, and custom camera paths.
All motions support easing curves.
"""

from __future__ import annotations

from src.composition.schema import CameraMotion, CameraMotionType, EasingType
from src.core.logging import get_logger


class CameraMotionEngine:
    """Generates and manages camera motions for scenes.

    Produces ``CameraMotion`` configurations that the renderer
    translates into FFmpeg zoompan/xfade filters.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def ken_burns(
        self,
        duration: float = 5.0,
        *,
        start_zoom: float = 1.0,
        end_zoom: float = 1.15,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> CameraMotion:
        """Create a Ken Burns effect (slow zoom + pan).

        Args:
            duration: Duration in seconds.
            start_zoom: Starting zoom level.
            end_zoom: Ending zoom level.
            pan_x: Horizontal pan offset (normalized -1 to 1).
            pan_y: Vertical pan offset (normalized -1 to 1).
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for Ken Burns.
        """
        return CameraMotion(
            motion_type=CameraMotionType.KEN_BURNS,
            start_zoom=start_zoom,
            end_zoom=end_zoom,
            start_x=0.0,
            start_y=0.0,
            end_x=pan_x,
            end_y=pan_y,
            duration=duration,
            easing=easing,
        )

    def pan(
        self,
        duration: float = 5.0,
        *,
        start_x: float = 0.0,
        end_x: float = 0.1,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> CameraMotion:
        """Create a horizontal pan.

        Args:
            duration: Duration in seconds.
            start_x: Starting X position (normalized).
            end_x: Ending X position (normalized).
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for pan.
        """
        return CameraMotion(
            motion_type=CameraMotionType.PAN,
            start_x=start_x,
            end_x=end_x,
            start_zoom=1.0,
            end_zoom=1.0,
            duration=duration,
            easing=easing,
        )

    def zoom(
        self,
        duration: float = 5.0,
        *,
        start_zoom: float = 1.0,
        end_zoom: float = 1.3,
        target_x: float = 0.5,
        target_y: float = 0.5,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> CameraMotion:
        """Create a zoom effect.

        Args:
            duration: Duration in seconds.
            start_zoom: Starting zoom level.
            end_zoom: Ending zoom level.
            target_x: Zoom target X (normalized 0-1).
            target_y: Zoom target Y (normalized 0-1).
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for zoom.
        """
        return CameraMotion(
            motion_type=CameraMotionType.ZOOM,
            start_zoom=start_zoom,
            end_zoom=end_zoom,
            start_x=target_x,
            end_x=target_x,
            start_y=target_y,
            end_y=target_y,
            duration=duration,
            easing=easing,
        )

    def tilt(
        self,
        duration: float = 5.0,
        *,
        start_y: float = 0.0,
        end_y: float = 0.1,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> CameraMotion:
        """Create a vertical tilt.

        Args:
            duration: Duration in seconds.
            start_y: Starting Y position (normalized).
            end_y: Ending Y position (normalized).
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for tilt.
        """
        return CameraMotion(
            motion_type=CameraMotionType.TILT,
            start_y=start_y,
            end_y=end_y,
            start_zoom=1.0,
            end_zoom=1.0,
            duration=duration,
            easing=easing,
        )

    def orbit(
        self,
        duration: float = 5.0,
        *,
        radius: float = 0.1,
        easing: EasingType = EasingType.LINEAR,
    ) -> CameraMotion:
        """Create an orbit motion.

        Args:
            duration: Duration in seconds.
            radius: Orbit radius (normalized).
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for orbit.
        """
        return CameraMotion(
            motion_type=CameraMotionType.ORBIT,
            start_x=-radius,
            end_x=radius,
            start_y=-radius,
            end_y=radius,
            start_zoom=1.0,
            end_zoom=1.0,
            duration=duration,
            easing=easing,
        )

    def parallax(
        self,
        duration: float = 5.0,
        *,
        depth: float = 0.05,
        easing: EasingType = EasingType.EASE_OUT,
    ) -> CameraMotion:
        """Create a parallax effect.

        Args:
            duration: Duration in seconds.
            depth: Parallax depth amount.
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` for parallax.
        """
        return CameraMotion(
            motion_type=CameraMotionType.PARALLAX,
            start_x=-depth,
            end_x=depth,
            start_zoom=1.0,
            end_zoom=1.0 + depth,
            duration=duration,
            easing=easing,
        )

    def custom_path(
        self,
        path_points: list[dict[str, float]],
        duration: float = 5.0,
        easing: EasingType = EasingType.LINEAR,
    ) -> CameraMotion:
        """Create a custom camera path.

        Args:
            path_points: List of {x, y, zoom} points.
            duration: Duration in seconds.
            easing: Easing curve.

        Returns:
            A ``CameraMotion`` with a custom path.
        """
        return CameraMotion(
            motion_type=CameraMotionType.CUSTOM,
            custom_path=path_points,
            duration=duration,
            easing=easing,
        )

    def to_ffmpeg_filter(self, motion: CameraMotion, width: int = 1920, height: int = 1080, fps: int = 30) -> str:
        """Convert a camera motion to an FFmpeg zoompan filter string.

        Args:
            motion: The camera motion.
            width: Output width.
            height: Output height.
            fps: Frames per second.

        Returns:
            FFmpeg filter string for the zoompan filter.
        """
        total_frames = int(motion.duration * fps)

        if motion.motion_type == CameraMotionType.ZOOM or motion.motion_type == CameraMotionType.KEN_BURNS:
            # zoompan filter for zoom/ken_burns
            zoom_expr = (
                f"zoompan=z='if(lte(on,{total_frames}),"
                f"{motion.start_zoom}+({motion.end_zoom}-{motion.start_zoom})*on/{total_frames},"
                f"{motion.end_zoom})':"
                f"x='iw/2-(iw/zoom/2)+{motion.end_x}*iw':"
                f"y='ih/2-(ih/zoom/2)+{motion.end_y}*ih':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )
            return zoom_expr

        elif motion.motion_type == CameraMotionType.PAN:
            return (
                f"crop=w={width}:h={height}:"
                f"x='(iw-{width})*if(lte(on,{total_frames}),"
                f"{motion.start_x}+({motion.end_x}-{motion.start_x})*on/{total_frames},"
                f"{motion.end_x})':"
                f"y=0"
            )

        elif motion.motion_type == CameraMotionType.TILT:
            return (
                f"crop=w={width}:h={height}:"
                f"x=0:"
                f"y='(ih-{height})*if(lte(on,{total_frames}),"
                f"{motion.start_y}+({motion.end_y}-{motion.start_y})*on/{total_frames},"
                f"{motion.end_y})'"
            )

        # Default: no motion
        return f"scale={width}:{height}"
