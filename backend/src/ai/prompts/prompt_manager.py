"""Prompt Management System — loading, versioning, validation, caching, and rendering.

Prompts are stored as files in the ``prompts/`` directory, organised by
agent type.  Each prompt file contains:

1. A YAML frontmatter block with metadata (version, author, description,
   variables, model_compatibility).
2. The prompt template body with ``{{variable}}`` placeholders.

File naming convention::

    prompts/<agent_type>/<prompt_name>.v<major>.<minor>.md

Example::

    prompts/research/web_search.v1.0.md

The ``PromptManager`` implements the ``PromptLoader`` interface and
provides:
- Loading by agent type, name, and optional version.
- Version resolution (latest version if not specified).
- Template rendering with variable substitution.
- Metadata extraction from YAML frontmatter.
- In-memory caching for loaded templates.
- Validation of required variables before rendering.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import (
    PromptNotFoundError,
    PromptRenderingError,
    PromptValidationError,
)
from src.core.interfaces import PromptLoader
from src.core.logging import get_logger


# Regex to parse YAML frontmatter (---\n...\n---)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

# Regex to find {{variable}} placeholders
_VARIABLE_RE = re.compile(r"\{\{(\w+)\}\}")


class PromptMetadata:
    """Metadata extracted from a prompt file's YAML frontmatter.

    Attributes:
        version: Semantic version string (e.g. "1.0").
        author: Author name.
        description: Human-readable description of the prompt's purpose.
        variables: List of expected template variable names.
        model_compatibility: List of model names this prompt is designed for.
        tags: Optional tags for categorisation.
    """

    def __init__(
        self,
        version: str,
        author: str = "unknown",
        description: str = "",
        variables: list[str] | None = None,
        model_compatibility: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.version = version
        self.author = author
        self.description = description
        self.variables = variables or []
        self.model_compatibility = model_compatibility or []
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "variables": self.variables,
            "model_compatibility": self.model_compatibility,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptMetadata:
        return cls(
            version=data.get("version", "0.0"),
            author=data.get("author", "unknown"),
            description=data.get("description", ""),
            variables=data.get("variables", []),
            model_compatibility=data.get("model_compatibility", []),
            tags=data.get("tags", []),
        )


class _CachedPrompt:
    """Internal cache entry for a loaded prompt."""

    def __init__(self, template: str, metadata: PromptMetadata, file_path: Path) -> None:
        self.template = template
        self.metadata = metadata
        self.file_path = file_path


class PromptManager(PromptLoader):
    """File-based prompt loader with versioning, caching, and rendering.

    Implements the ``PromptLoader`` interface.  Prompts are loaded from
    the filesystem and cached in memory for the lifetime of the process.
    """

    def __init__(self, prompts_dir: str | Path | None = None) -> None:
        """Create the prompt manager.

        Args:
            prompts_dir: Path to the ``prompts/`` directory. If ``None``,
                defaults to ``<project_root>/backend/prompts/``.
        """
        if prompts_dir is None:
            # Default: backend/prompts/ relative to this file
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            prompts_dir = project_root / "backend" / "prompts"

        self._prompts_dir = Path(prompts_dir)
        self._logger = get_logger(__name__)
        self._cache: dict[str, _CachedPrompt] = {}
        self._version_index: dict[str, list[tuple[str, Path]]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Scan the prompts directory and build the version index."""
        if not self._prompts_dir.exists():
            self._logger.warning(
                "prompts_dir_not_found",
                path=str(self._prompts_dir),
            )
            self._initialized = True
            return

        self._build_version_index()
        self._logger.info(
            "prompt_manager_initialized",
            prompts_dir=str(self._prompts_dir),
            prompt_count=len(self._version_index),
        )
        self._initialized = True

    async def load(self, agent_type: str, prompt_name: str, version: str | None = None) -> str:
        """Load a prompt template by agent type, name, and optional version.

        Args:
            agent_type: The agent category (e.g. "research", "script").
            prompt_name: The specific prompt name (e.g. "web_search").
            version: Semantic version string. If ``None``, loads the latest.

        Returns:
            The raw prompt template string with ``{{variable}}`` placeholders.

        Raises:
            PromptNotFoundError: If the prompt cannot be found.
        """
        cache_key = f"{agent_type}/{prompt_name}/{version or 'latest'}"

        if cache_key in self._cache:
            return self._cache[cache_key].template

        file_path = self._resolve_prompt_path(agent_type, prompt_name, version)
        if file_path is None:
            raise PromptNotFoundError(agent_type, prompt_name, version)

        content = file_path.read_text(encoding="utf-8")
        template, metadata = self._parse_prompt_file(content)

        self._cache[cache_key] = _CachedPrompt(template, metadata, file_path)
        self._logger.info(
            "prompt_loaded",
            agent_type=agent_type,
            prompt_name=prompt_name,
            version=metadata.version,
        )
        return template

    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Render a prompt template by substituting variables.

        Args:
            template: The raw template string with ``{{variable}}`` placeholders.
            variables: Dictionary of variable names to values.

        Returns:
            The rendered prompt string with all variables substituted.

        Raises:
            PromptRenderingError: If required variables are missing.
        """
        # Find all variables in the template
        required = set(_VARIABLE_RE.findall(template))
        provided = set(variables.keys())
        missing = required - provided

        if missing:
            raise PromptRenderingError(template[:50] + "...", sorted(missing))

        # Substitute variables
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

        return rendered

    async def get_metadata(
        self,
        agent_type: str,
        prompt_name: str,
        version: str | None = None,
    ) -> dict[str, Any]:
        """Get metadata for a prompt template.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.
            version: Semantic version. If ``None``, uses the latest.

        Returns:
            Dictionary containing metadata (version, author, description,
            variables, model_compatibility, tags).
        """
        cache_key = f"{agent_type}/{prompt_name}/{version or 'latest'}"

        if cache_key in self._cache:
            return self._cache[cache_key].metadata.to_dict()

        file_path = self._resolve_prompt_path(agent_type, prompt_name, version)
        if file_path is None:
            raise PromptNotFoundError(agent_type, prompt_name, version)

        content = file_path.read_text(encoding="utf-8")
        _, metadata = self._parse_prompt_file(content)

        return metadata.to_dict()

    async def list_versions(self, agent_type: str, prompt_name: str) -> list[str]:
        """List all available versions of a prompt.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.

        Returns:
            List of version strings, sorted from newest to oldest.
        """
        key = f"{agent_type}/{prompt_name}"
        versions = self._version_index.get(key, [])
        return [v for v, _ in versions]

    async def list_prompts(self, agent_type: str) -> list[str]:
        """List all prompt names available for an agent type.

        Args:
            agent_type: The agent category.

        Returns:
            List of prompt names.
        """
        prompt_names: set[str] = set()
        prefix = f"{agent_type}/"
        for key in self._version_index:
            if key.startswith(prefix):
                prompt_name = key[len(prefix):]
                prompt_names.add(prompt_name)
        return sorted(prompt_names)

    async def load_and_render(
        self,
        agent_type: str,
        prompt_name: str,
        variables: dict[str, Any],
        version: str | None = None,
    ) -> str:
        """Convenience method: load a prompt and render it in one call.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.
            variables: Template variables to substitute.
            version: Optional version. If ``None``, uses the latest.

        Returns:
            The rendered prompt string.
        """
        template = await self.load(agent_type, prompt_name, version)
        return self.render(template, variables)

    async def shutdown(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._version_index.clear()
        self._logger.info("prompt_manager_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    def _build_version_index(self) -> None:
        """Scan the prompts directory and index all prompt files by version."""
        self._version_index.clear()

        for agent_dir in self._prompts_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_type = agent_dir.name

            for prompt_file in agent_dir.glob("*.md"):
                # Parse filename: <name>.v<major>.<minor>.md
                stem = prompt_file.stem  # e.g. "web_search.v1.0"
                parts = stem.rsplit(".v", 1)

                if len(parts) == 2:
                    prompt_name = parts[0]
                    version = parts[1]
                else:
                    # No version in filename — treat as v1.0
                    prompt_name = stem
                    version = "1.0"

                key = f"{agent_type}/{prompt_name}"
                if key not in self._version_index:
                    self._version_index[key] = []
                self._version_index[key].append((version, prompt_file))

        # Sort each prompt's versions in descending order (newest first)
        for key in self._version_index:
            self._version_index[key].sort(key=lambda x: x[0], reverse=True)

    def _resolve_prompt_path(
        self,
        agent_type: str,
        prompt_name: str,
        version: str | None,
    ) -> Path | None:
        """Resolve a prompt file path from the version index.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.
            version: Optional version. If ``None``, returns the latest.

        Returns:
            Path to the prompt file, or ``None`` if not found.
        """
        key = f"{agent_type}/{prompt_name}"
        versions = self._version_index.get(key, [])

        if not versions:
            return None

        if version is None:
            # Return the latest (first in sorted list)
            return versions[0][1]

        # Find the specific version
        for v, path in versions:
            if v == version:
                return path

        return None

    @staticmethod
    def _parse_prompt_file(content: str) -> tuple[str, PromptMetadata]:
        """Parse a prompt file into template and metadata.

        Args:
            content: The raw file content.

        Returns:
            Tuple of (template_string, PromptMetadata).

        Raises:
            PromptValidationError: If the file format is invalid.
        """
        match = _FRONTMATTER_RE.match(content)

        if match:
            yaml_block = match.group(1)
            template = match.group(2).strip()
            try:
                metadata_dict = yaml.safe_load(yaml_block) or {}
            except yaml.YAMLError as exc:
                raise PromptValidationError(f"YAML parsing error: {exc}")
            metadata = PromptMetadata.from_dict(metadata_dict)
        else:
            # No frontmatter — treat entire content as template
            template = content.strip()
            metadata = PromptMetadata(version="0.0")

        # Extract variables from template if not in metadata
        template_vars = set(_VARIABLE_RE.findall(template))
        if not metadata.variables:
            metadata.variables = sorted(template_vars)

        return template, metadata
