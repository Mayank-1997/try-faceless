"""Rendering Gateway — unified interface for video rendering operations.

The application never calls FFmpeg directly.  All rendering operations
go through the Rendering Gateway, which delegates to the configured
renderer (FFmpeg, Cloud Rendering, MoviePy, etc.).

Exposes:
- ``render()`` — render a complete video from scene definitions.
- ``merge()`` — merge video and audio tracks.
- ``concatenate()`` — concatenate multiple video clips.
- ``burn_subtitles()`` — burn subtitles into a video.
- ``generate_thumbnail()`` — extract a thumbnail from a video.
"""

from __future__ import annotations

from typing import Any

from src.core.config_service import ConfigService
from src.core.exceptions import RenderingError
from src.core.interfaces import HealthStatus, ProviderConfig, Renderer
from src.core.logging import get_logger


class RenderingGateway:
    """Unified gateway for video rendering operations.

    Wraps a single ``Renderer`` instance and adds structured logging
    and error handling.
    """

    def __init__(self, config: ConfigService) -> None:
        """Create the Rendering Gateway.

        Args:
            config: The application configuration service.
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._renderer: Renderer | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialise the configured renderer."""
        from src.rendering.ffmpeg import FFmpegRenderer

        renderer = FFmpegRenderer()
        await renderer.initialize(
            ProviderConfig(
                api_key="",
                model="ffmpeg",
                extra={
                    "path": self._config.ffmpeg.path,
                    "ffprobe_path": self._config.ffmpeg.ffprobe_path,
                    "threads": self._config.ffmpeg.threads,
                    "preset": self._config.ffmpeg.preset,
                    "crf": self._config.ffmpeg.crf,
                },
            )
        )
        self._renderer = renderer
        self._initialized = True
        self._logger.info(
            "rendering_gateway_initialized",
            renderer=renderer.renderer_name,
        )

    def _ensure_initialized(self) -> Renderer:
        if not self._initialized or self._renderer is None:
            raise RenderingError("Rendering Gateway is not initialised")
        return self._renderer

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

        Args:
            scenes: Ordered list of scene dictionaries.
            output_path: Destination file path.
            width: Output width.
            height: Output height.
            fps: Frames per second.
            **kwargs: Renderer-specific options.

        Returns:
            Path to the rendered video file.
        """
        renderer = self._ensure_initialized()
        self._logger.info(
            "rendering_start",
            scene_count=len(scenes),
            output_path=output_path,
            resolution=f"{width}x{height}",
            fps=fps,
        )
        try:
            result = await renderer.render(
                scenes,
                output_path,
                width=width,
                height=height,
                fps=fps,
                **kwargs,
            )
            self._logger.info("rendering_success", output_path=result)
            return result
        except Exception as exc:
            self._logger.error("rendering_failed", error=str(exc))
            raise RenderingError(f"Render failed: {exc}")

    async def merge(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Merge a video track with an audio track."""
        renderer = self._ensure_initialized()
        try:
            result = await renderer.merge(video_path, audio_path, output_path, **kwargs)
            self._logger.info("merge_success", output_path=result)
            return result
        except Exception as exc:
            self._logger.error("merge_failed", error=str(exc))
            raise RenderingError(f"Merge failed: {exc}")

    async def concatenate(self, video_paths: list[str], output_path: str, **kwargs: Any) -> str:
        """Concatenate multiple video clips."""
        renderer = self._ensure_initialized()
        try:
            result = await renderer.concatenate(video_paths, output_path, **kwargs)
            self._logger.info("concatenate_success", output_path=result, clip_count=len(video_paths))
            return result
        except Exception as exc:
            self._logger.error("concatenate_failed", error=str(exc))
            raise RenderingError(f"Concatenate failed: {exc}")

    async def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Burn subtitles into a video."""
        renderer = self._ensure_initialized()
        try:
            result = await renderer.burn_subtitles(video_path, subtitle_path, output_path, **kwargs)
            self._logger.info("burn_subtitles_success", output_path=result)
            return result
        except Exception as exc:
            self._logger.error("burn_subtitles_failed", error=str(exc))
            raise RenderingError(f"Burn subtitles failed: {exc}")

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
        """Generate a thumbnail from a video."""
        renderer = self._ensure_initialized()
        try:
            result = await renderer.generate_thumbnail(
                video_path,
                output_path,
                timestamp=timestamp,
                width=width,
                height=height,
                **kwargs,
            )
            self._logger.info("thumbnail_success", output_path=result)
            return result
        except Exception as exc:
            self._logger.error("thumbnail_failed", error=str(exc))
            raise RenderingError(f"Thumbnail generation failed: {exc}")

    async def health_check(self) -> HealthStatus:
        """Check renderer health."""
        renderer = self._ensure_initialized()
        return HealthStatus(
            healthy=True,
            service="rendering",
            details={"renderer": renderer.renderer_name},
        )

    async def shutdown(self) -> None:
        """Release resources."""
        if self._renderer is not None:
            await self._renderer.shutdown()
        self._initialized = False
        self._logger.info("rendering_gateway_shutdown")
