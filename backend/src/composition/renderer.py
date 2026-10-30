"""Composition Renderer Abstraction.

Every renderer must implement:
- load() — Load a composition document
- validate() — Validate the composition for this renderer
- prepare() — Prepare assets and working directory
- render() — Render the video
- monitor() — Monitor rendering progress
- cancel() — Cancel rendering
- cleanup() — Clean up temporary files
- collect_metrics() — Collect rendering metrics

This is a NEW abstraction separate from the existing ``Renderer``
interface in ``src/core/interfaces.py``.  The existing interface
handles low-level operations (merge, concatenate, burn_subtitles).
This abstraction handles full composition-based rendering.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.composition.schema import (
    CompositionDocument,
    QualityReport,
    RenderMetrics,
    RenderProgress,
    RenderStatus,
)
from src.core.logging import get_logger


class CompositionRenderer(ABC):
    """Abstract interface for composition renderers.

    Implementations: FFmpeg (current), MoviePy, Remotion, Cloud GPU,
    WebGL, Native (future).

    The renderer consumes ONLY a ``CompositionDocument`` and produces
    a rendered video file.
    """

    @property
    @abstractmethod
    def renderer_name(self) -> str:
        """Return the renderer name (e.g. "ffmpeg", "moviepy")."""

    @abstractmethod
    async def load(self, composition: CompositionDocument) -> None:
        """Load a composition document into the renderer.

        Args:
            composition: The composition to render.
        """

    @abstractmethod
    async def validate(self) -> list[str]:
        """Validate the loaded composition for this renderer.

        Returns:
            List of validation errors (empty if valid).
        """

    @abstractmethod
    async def prepare(self, output_path: str) -> None:
        """Prepare assets and working directory.

        Args:
            output_path: Destination for the final output.
        """

    @abstractmethod
    async def render(self) -> str:
        """Render the video.

        Returns:
            Path to the rendered video file.
        """

    @abstractmethod
    async def monitor(self) -> RenderProgress:
        """Monitor rendering progress.

        Returns:
            Current ``RenderProgress``.
        """

    @abstractmethod
    async def cancel(self) -> None:
        """Cancel the current rendering operation."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up temporary files and resources."""

    @abstractmethod
    async def collect_metrics(self) -> RenderMetrics:
        """Collect rendering metrics after completion.

        Returns:
            ``RenderMetrics`` with performance data.
        """

    @abstractmethod
    async def validate_output(self, output_path: str) -> QualityReport:
        """Validate the rendered output.

        Args:
            output_path: Path to the rendered video.

        Returns:
            A ``QualityReport`` with validation results.
        """
