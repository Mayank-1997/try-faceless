"""Video Effects Engine.

Supports brightness, contrast, color correction, blur, sharpen, glow,
noise reduction, vignette, and future LUT support.
"""

from __future__ import annotations

from src.composition.schema import VideoEffect, VideoEffectType
from src.core.logging import get_logger


class VideoEffectsEngine:
    """Generates and manages video effects.

    Produces ``VideoEffect`` configurations that the renderer
    translates into FFmpeg filter expressions.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def brightness(self, intensity: float = 0.1, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a brightness effect.

        Args:
            intensity: Brightness adjustment (-1.0 to 1.0).
            target_clip_id: Clip to apply to.

        Returns:
            A brightness ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.BRIGHTNESS,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"eq_brightness": intensity},
        )

    def contrast(self, intensity: float = 1.2, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a contrast effect.

        Args:
            intensity: Contrast multiplier (1.0 = normal).
            target_clip_id: Clip to apply to.

        Returns:
            A contrast ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.CONTRAST,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"eq_contrast": intensity},
        )

    def color_correction(self, saturation: float = 1.0, gamma: float = 1.0, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a color correction effect.

        Args:
            saturation: Saturation multiplier (1.0 = normal).
            gamma: Gamma correction (1.0 = normal).
            target_clip_id: Clip to apply to.

        Returns:
            A color correction ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.COLOR_CORRECTION,
            intensity=saturation,
            target_clip_id=target_clip_id,
            params={"eq_saturation": saturation, "eq_gamma": gamma},
        )

    def blur(self, radius: float = 2.0, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a blur effect.

        Args:
            radius: Blur radius in pixels.
            target_clip_id: Clip to apply to.

        Returns:
            A blur ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.BLUR,
            intensity=radius,
            target_clip_id=target_clip_id,
            params={"boxblur": radius},
        )

    def sharpen(self, intensity: float = 1.0, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a sharpen effect.

        Args:
            intensity: Sharpen intensity.
            target_clip_id: Clip to apply to.

        Returns:
            A sharpen ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.SHARPEN,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"unsharp": intensity},
        )

    def glow(self, intensity: float = 0.5, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a glow effect.

        Args:
            intensity: Glow intensity (0.0 to 1.0).
            target_clip_id: Clip to apply to.

        Returns:
            A glow ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.GLOW,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"glow": intensity},
        )

    def noise_reduction(self, intensity: float = 0.5, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a noise reduction effect.

        Args:
            intensity: Reduction strength (0.0 to 1.0).
            target_clip_id: Clip to apply to.

        Returns:
            A noise reduction ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.NOISE_REDUCTION,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"hqdn3d": intensity},
        )

    def vignette(self, intensity: float = 0.5, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a vignette effect.

        Args:
            intensity: Vignette intensity (0.0 to 1.0).
            target_clip_id: Clip to apply to.

        Returns:
            A vignette ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.VIGNETTE,
            intensity=intensity,
            target_clip_id=target_clip_id,
            params={"vignette": intensity},
        )

    def lut(self, lut_file: str, *, target_clip_id: str | None = None) -> VideoEffect:
        """Create a LUT (Look-Up Table) effect.

        Args:
            lut_file: Path to the LUT file.
            target_clip_id: Clip to apply to.

        Returns:
            A LUT ``VideoEffect``.
        """
        return VideoEffect(
            effect_type=VideoEffectType.LUT,
            intensity=1.0,
            target_clip_id=target_clip_id,
            params={"lut_file": lut_file},
        )

    def to_ffmpeg_filter(self, effect: VideoEffect) -> str:
        """Convert a video effect to an FFmpeg filter string.

        Args:
            effect: The video effect.

        Returns:
            FFmpeg filter string.
        """
        if effect.effect_type == VideoEffectType.BRIGHTNESS:
            return f"eq=brightness={effect.params.get('eq_brightness', 0.0)}"
        elif effect.effect_type == VideoEffectType.CONTRAST:
            return f"eq=contrast={effect.params.get('eq_contrast', 1.0)}"
        elif effect.effect_type == VideoEffectType.COLOR_CORRECTION:
            return f"eq=saturation={effect.params.get('eq_saturation', 1.0)}:gamma={effect.params.get('eq_gamma', 1.0)}"
        elif effect.effect_type == VideoEffectType.BLUR:
            return f"boxblur={effect.params.get('boxblur', 2.0)}"
        elif effect.effect_type == VideoEffectType.SHARPEN:
            return f"unsharp=5:5:{effect.params.get('unsharp', 1.0)}:5:5:0.0"
        elif effect.effect_type == VideoEffectType.VIGNETTE:
            return f"vignette=PI/4"
        elif effect.effect_type == VideoEffectType.NOISE_REDUCTION:
            return f"hqdn3d={effect.params.get('hqdn3d', 0.5)}"
        elif effect.effect_type == VideoEffectType.LUT:
            return f"lut3d={effect.params.get('lut_file', '')}"
        else:
            return ""

    def list_effect_types(self) -> list[str]:
        """List all available effect types."""
        return [e.value for e in VideoEffectType]
