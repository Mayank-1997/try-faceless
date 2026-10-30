"""FFmpeg renderer — concrete implementation of the ``Renderer`` interface.

Wraps FFmpeg CLI commands behind the common ``Renderer`` interface.
All FFmpeg calls go through ``asyncio.subprocess`` for async compatibility.

Supported operations:
- ``render()`` — render a video from scene definitions (Phase 7).
- ``merge()`` — merge video and audio tracks.
- ``concatenate()`` — concatenate multiple video clips.
- ``burn_subtitles()`` — burn SRT/VTT subtitles into a video.
- ``generate_thumbnail()`` — extract a frame as a thumbnail image.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

from src.core.exceptions import RenderingError
from src.core.interfaces import ProviderConfig, Renderer
from src.core.logging import get_logger


class FFmpegRenderer(Renderer):
    """FFmpeg implementation of the ``Renderer`` interface."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._ffmpeg_path: str = "ffmpeg"
        self._ffprobe_path: str = "ffprobe"
        self._threads: int = 4
        self._preset: str = "medium"
        self._crf: int = 23
        self._logger = get_logger(__name__)
        self._initialized = False

    @property
    def renderer_name(self) -> str:
        return "ffmpeg"

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the FFmpeg renderer.

        Args:
            config: Provider configuration with FFmpeg paths and settings.
        """
        self._config = config
        self._ffmpeg_path = config.extra.get("path", "ffmpeg")
        self._ffprobe_path = config.extra.get("ffprobe_path", "ffprobe")
        self._threads = config.extra.get("threads", 4)
        self._preset = config.extra.get("preset", "medium")
        self._crf = config.extra.get("crf", 23)
        self._initialized = True
        self._logger.info(
            "ffmpeg_renderer_initialized",
            path=self._ffmpeg_path,
            threads=self._threads,
            preset=self._preset,
            crf=self._crf,
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RenderingError("FFmpeg renderer is not initialised")

    async def _run_ffmpeg(self, args: list[str]) -> tuple[int, str, str]:
        """Run an FFmpeg command and return (returncode, stdout, stderr).

        Args:
            args: Command-line arguments (without the ``ffmpeg`` prefix).

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        cmd = [self._ffmpeg_path, "-y", *args]
        self._logger.debug("ffmpeg_command", cmd=" ".join(cmd))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")
            raise RenderingError(f"FFmpeg failed (code {process.returncode}): {error_msg}")

        return process.returncode, stdout.decode(), stderr.decode()

    async def render(
        self,
        scenes: list[dict[str, Any]],
        output_path: str,
        *,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        **kwargs: Any,
    ) -> str:
        """Render a complete video from scene definitions.

        Full implementation will be added in Phase 7 when scene
        structures are finalised.  The method signature and error
        handling are in place.
        """
        self._ensure_initialized()
        # TODO: Implement full scene-based rendering in Phase 7
        raise RenderingError(
            "Full scene rendering will be implemented in Phase 7. "
            "Use merge/concatenate/burn_subtitles for individual operations."
        )

    async def merge(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Merge a video track with an audio track using FFmpeg.

        Replaces the video's audio with the provided audio track.

        Args:
            video_path: Path to the input video file.
            audio_path: Path to the input audio file.
            output_path: Destination for the merged output.

        Returns:
            Path to the merged file.
        """
        self._ensure_initialized()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ]

        await self._run_ffmpeg(args)
        return output_path

    async def concatenate(self, video_paths: list[str], output_path: str, **kwargs: Any) -> str:
        """Concatenate multiple video clips into a single video.

        Uses FFmpeg's concat demuxer for efficient stream copying.

        Args:
            video_paths: Ordered list of video file paths.
            output_path: Destination for the concatenated output.

        Returns:
            Path to the concatenated file.
        """
        self._ensure_initialized()

        if not video_paths:
            raise RenderingError("Cannot concatenate empty list of videos")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Create a temporary concat list file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as concat_file:
            for path in video_paths:
                # FFmpeg concat requires absolute paths and single quotes
                abs_path = os.path.abspath(path)
                concat_file.write(f"file '{abs_path}'\n")
            concat_file_path = concat_file.name

        try:
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file_path,
                "-c", "copy",
                output_path,
            ]
            await self._run_ffmpeg(args)
            return output_path
        finally:
            os.unlink(concat_file_path)

    async def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Burn subtitle file into a video (hardcode subtitles).

        Uses FFmpeg's ``subtitles`` filter to render subtitles directly
        onto the video frames.

        Args:
            video_path: Path to the input video.
            subtitle_path: Path to the subtitle file (SRT or VTT).
            output_path: Destination for the output.

        Keyword Args:
            font_size: Subtitle font size (default 24).
            font_color: Subtitle font color (default "white").
            outline_color: Outline color (default "black").
            outline_width: Outline width (default 2).
        """
        self._ensure_initialized()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        font_size = kwargs.get("font_size", 24)
        font_color = kwargs.get("font_color", "white")
        outline_color = kwargs.get("outline_color", "black")
        outline_width = kwargs.get("outline_width", 2)

        # Escape the subtitle path for FFmpeg filter syntax
        escaped_sub_path = subtitle_path.replace("\\", "/").replace(":", "\\:")

        subtitle_filter = (
            f"subtitles='{escaped_sub_path}':"
            f"force_style='FontSize={font_size},"
            f"PrimaryColour={font_color},"
            f"OutlineColour={outline_color},"
            f"Outline={outline_width}'"
        )

        args = [
            "-i", video_path,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", self._preset,
            "-crf", str(self._crf),
            "-threads", str(self._threads),
            output_path,
        ]

        await self._run_ffmpeg(args)
        return output_path

    async def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        *,
        timestamp: float = 0.0,
        width: int = 1280,
        height: int = 720,
        **kwargs: Any,
    ) -> str:
        """Extract a thumbnail frame from a video.

        Args:
            video_path: Path to the source video.
            output_path: Destination for the thumbnail image.
            timestamp: Time in seconds to extract the frame at.
            width: Thumbnail width.
            height: Thumbnail height.

        Returns:
            Path to the generated thumbnail.
        """
        self._ensure_initialized()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        args = [
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-s", f"{width}x{height}",
            "-q:v", "2",
            output_path,
        ]

        await self._run_ffmpeg(args)
        return output_path

    async def shutdown(self) -> None:
        """Release resources."""
        self._initialized = False
        self._logger.info("ffmpeg_renderer_shutdown")
