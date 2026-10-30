"""Image Animation Engine.

Supports scale, translate, rotate, opacity, crop, depth illusion,
parallax, and motion presets for image clips.
"""

from __future__ import annotations

from src.composition.schema import EasingType, ImageAnimation, ImageAnimationType
from src.core.logging import get_logger


class ImageAnimationEngine:
    """Generates and manages image animations.

    Produces ``ImageAnimation`` configurations that the renderer
    translates into FFmpeg filter expressions.
    """

    # Motion presets
    _PRESETS: dict[str, dict[str, float]] = {
        "zoom_in": {"start": 1.0, "end": 1.15},
        "zoom_out": {"start": 1.15, "end": 1.0},
        "pan_left": {"start": 0.0, "end": -0.1},
        "pan_right": {"start": 0.0, "end": 0.1},
        "fade_in": {"start": 0.0, "end": 1.0},
        "fade_out": {"start": 1.0, "end": 0.0},
        "rotate_cw": {"start": 0.0, "end": 5.0},
        "rotate_ccw": {"start": 0.0, "end": -5.0},
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def scale(
        self,
        duration: float = 5.0,
        *,
        start: float = 1.0,
        end: float = 1.1,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> ImageAnimation:
        """Create a scale animation.

        Args:
            duration: Duration in seconds.
            start: Starting scale.
            end: Ending scale.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for scaling.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.SCALE,
            start_value=start,
            end_value=end,
            duration=duration,
            easing=easing,
        )

    def translate(
        self,
        duration: float = 5.0,
        *,
        start: float = 0.0,
        end: float = 0.1,
        direction: str = "right",
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> ImageAnimation:
        """Create a translate animation.

        Args:
            duration: Duration in seconds.
            start: Starting offset (normalized).
            end: Ending offset (normalized).
            direction: Direction (left, right, up, down).
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for translation.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.TRANSLATE,
            start_value=start,
            end_value=end,
            duration=duration,
            easing=easing,
            direction=direction,
        )

    def rotate(
        self,
        duration: float = 5.0,
        *,
        start: float = 0.0,
        end: float = 5.0,
        easing: EasingType = EasingType.LINEAR,
    ) -> ImageAnimation:
        """Create a rotation animation.

        Args:
            duration: Duration in seconds.
            start: Starting angle in degrees.
            end: Ending angle in degrees.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for rotation.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.ROTATE,
            start_value=start,
            end_value=end,
            duration=duration,
            easing=easing,
        )

    def opacity(
        self,
        duration: float = 5.0,
        *,
        start: float = 0.0,
        end: float = 1.0,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> ImageAnimation:
        """Create an opacity (fade) animation.

        Args:
            duration: Duration in seconds.
            start: Starting opacity (0.0 to 1.0).
            end: Ending opacity (0.0 to 1.0).
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for opacity.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.OPACITY,
            start_value=start,
            end_value=end,
            duration=duration,
            easing=easing,
        )

    def crop(
        self,
        duration: float = 5.0,
        *,
        start: float = 1.0,
        end: float = 0.8,
        easing: EasingType = EasingType.EASE_IN_OUT,
    ) -> ImageAnimation:
        """Create a crop animation (zoom-in via crop).

        Args:
            duration: Duration in seconds.
            start: Starting crop ratio (1.0 = full).
            end: Ending crop ratio.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for crop.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.CROP,
            start_value=start,
            end_value=end,
            duration=duration,
            easing=easing,
        )

    def depth_illusion(
        self,
        duration: float = 5.0,
        *,
        depth: float = 0.05,
        easing: EasingType = EasingType.EASE_OUT,
    ) -> ImageAnimation:
        """Create a depth illusion effect (scale + slight translate).

        Args:
            duration: Duration in seconds.
            depth: Depth amount.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for depth illusion.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.DEPTH_ILLUSION,
            start_value=1.0,
            end_value=1.0 + depth,
            duration=duration,
            easing=easing,
        )

    def parallax(
        self,
        duration: float = 5.0,
        *,
        depth: float = 0.05,
        easing: EasingType = EasingType.EASE_OUT,
    ) -> ImageAnimation:
        """Create a parallax animation.

        Args:
            duration: Duration in seconds.
            depth: Parallax depth.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` for parallax.
        """
        return ImageAnimation(
            animation_type=ImageAnimationType.PARALLAX,
            start_value=0.0,
            end_value=depth,
            duration=duration,
            easing=easing,
        )

    def preset(self, name: str, duration: float = 5.0, easing: EasingType = EasingType.EASE_IN_OUT) -> ImageAnimation:
        """Create an animation from a named preset.

        Args:
            name: Preset name (zoom_in, zoom_out, pan_left, etc.).
            duration: Duration in seconds.
            easing: Easing curve.

        Returns:
            An ``ImageAnimation`` from the preset.
        """
        if name not in self._PRESETS:
            raise ValueError(f"Unknown preset: {name}. Available: {list(self._PRESETS.keys())}")

        p = self._PRESETS[name]
        if "zoom" in name:
            return self.scale(duration, start=p["start"], end=p["end"], easing=easing)
        elif "pan" in name:
            return self.translate(duration, start=p["start"], end=p["end"], direction=name.replace("pan_", ""), easing=easing)
        elif "fade" in name:
            return self.opacity(duration, start=p["start"], end=p["end"], easing=easing)
        elif "rotate" in name:
            return self.rotate(duration, start=p["start"], end=p["end"], easing=easing)
        else:
            return ImageAnimation(
                animation_type=ImageAnimationType.MOTION_PRESET,
                preset_name=name,
                start_value=p.get("start", 0.0),
                end_value=p.get("end", 1.0),
                duration=duration,
                easing=easing,
            )

    def list_presets(self) -> list[str]:
        """List all available preset names."""
        return list(self._PRESETS.keys())

    def to_ffmpeg_filter(self, animation: ImageAnimation, width: int = 1920, height: int = 1080, fps: int = 30) -> str:
        """Convert an image animation to an FFmpeg filter string.

        Args:
            animation: The image animation.
            width: Output width.
            height: Output height.
            fps: Frames per second.

        Returns:
            FFmpeg filter string.
        """
        total_frames = int(animation.duration * fps)
        t = animation.duration

        if animation.animation_type == ImageAnimationType.SCALE:
            return (
                f"scale={width}*{animation.start_value}:{height}*{animation.start_value},"
                f"scale={width}:{height}:flags=lanczos"
            )
        elif animation.animation_type == ImageAnimationType.OPACITY:
            return f"fade=t=in:st=0:d={t}:alpha={animation.start_value}"
        elif animation.animation_type == ImageAnimationType.ROTATE:
            return f"rotate={animation.end_value}*PI/180:ow={width}:oh={height}"
        elif animation.animation_type == ImageAnimationType.TRANSLATE:
            return f"crop={width}:{height}:x={animation.end_x * width if hasattr(animation, 'end_x') else 0}:y=0"
        else:
            return f"scale={width}:{height}"
