"""Text Engine.

Supports titles, lower thirds, captions, credits, watermarks, callouts,
animated text, and custom fonts.
"""

from __future__ import annotations

from src.composition.schema import TextOverlay, TextType
from src.core.logging import get_logger


class TextEngine:
    """Generates and manages text overlays.

    Produces ``TextOverlay`` configurations that the renderer
    translates into FFmpeg drawtext filter expressions.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def title(self, content: str, *, duration: float = 3.0, position_y: float = 0.1, font_size: int = 72) -> TextOverlay:
        """Create a title overlay.

        Args:
            content: Title text.
            duration: Display duration in seconds.
            position_y: Vertical position (normalized 0-1).
            font_size: Font size.

        Returns:
            A title ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.TITLE,
            content=content,
            font_size=font_size,
            position_y=position_y,
            duration=duration,
            animation="fade_in",
        )

    def lower_third(self, content: str, *, duration: float = 5.0, position_y: float = 0.8) -> TextOverlay:
        """Create a lower third overlay.

        Args:
            content: Lower third text.
            duration: Display duration in seconds.
            position_y: Vertical position (normalized 0-1).

        Returns:
            A lower third ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.LOWER_THIRD,
            content=content,
            font_size=36,
            position_y=position_y,
            duration=duration,
            background_color="#00000080",
        )

    def caption(self, content: str, *, start_time: float = 0.0, duration: float = 2.0) -> TextOverlay:
        """Create a caption overlay.

        Args:
            content: Caption text.
            start_time: Start time in seconds.
            duration: Display duration in seconds.

        Returns:
            A caption ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.CAPTION,
            content=content,
            font_size=28,
            position_y=0.9,
            start_time=start_time,
            duration=duration,
        )

    def credits(self, content: str, *, duration: float = 10.0) -> TextOverlay:
        """Create a credits overlay.

        Args:
            content: Credits text (multiline).
            duration: Display duration in seconds.

        Returns:
            A credits ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.CREDITS,
            content=content,
            font_size=32,
            position_y=0.5,
            duration=duration,
            animation="scroll_up",
        )

    def watermark(self, content: str, *, position_x: float = 0.9, position_y: float = 0.05) -> TextOverlay:
        """Create a watermark overlay.

        Args:
            content: Watermark text.
            position_x: Horizontal position (normalized 0-1).
            position_y: Vertical position (normalized 0-1).

        Returns:
            A watermark ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.WATERMARK,
            content=content,
            font_size=20,
            position_x=position_x,
            position_y=position_y,
            duration=999999,  # entire video
            opacity=0.5,
        )

    def callout(self, content: str, *, position_x: float = 0.2, position_y: float = 0.3, duration: float = 3.0) -> TextOverlay:
        """Create a callout overlay.

        Args:
            content: Callout text.
            position_x: Horizontal position (normalized 0-1).
            position_y: Vertical position (normalized 0-1).
            duration: Display duration in seconds.

        Returns:
            A callout ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.CALLOUT,
            content=content,
            font_size=36,
            position_x=position_x,
            position_y=position_y,
            duration=duration,
            background_color="#FF000080",
        )

    def animated_text(self, content: str, *, animation: str = "fade_in", duration: float = 3.0, font_size: int = 48) -> TextOverlay:
        """Create an animated text overlay.

        Args:
            content: Text content.
            animation: Animation type (fade_in, slide_in, typewriter, etc.).
            duration: Display duration in seconds.
            font_size: Font size.

        Returns:
            An animated text ``TextOverlay``.
        """
        return TextOverlay(
            text_type=TextType.ANIMATED_TEXT,
            content=content,
            font_size=font_size,
            duration=duration,
            animation=animation,
        )

    def to_ffmpeg_drawtext(self, overlay: TextOverlay, width: int = 1920, height: int = 1080) -> str:
        """Convert a text overlay to an FFmpeg drawtext filter string.

        Args:
            overlay: The text overlay.
            width: Video width.
            height: Video height.

        Returns:
            FFmpeg drawtext filter string.
        """
        x = int(overlay.position_x * width)
        y = int(overlay.position_y * height)
        escaped = overlay.content.replace("'", "\\'").replace(":", "\\:")

        filter_parts = [
            f"drawtext=font='{overlay.font_family}':text='{escaped}'",
            f"fontsize={overlay.font_size}",
            f"fontcolor={overlay.font_color}",
            f"x={x}:y={y}",
            f"enable='between(t,{overlay.start_time},{overlay.start_time + overlay.duration})'",
        ]

        if overlay.background_color:
            filter_parts.append(f"box=1:boxcolor={overlay.background_color}")

        return ":".join(filter_parts)

    def list_text_types(self) -> list[str]:
        """List all available text types."""
        return [t.value for t in TextType]
