"""Tests for the Prompt Manager."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.ai.prompts.prompt_manager import PromptManager
from src.core.exceptions import PromptNotFoundError, PromptRenderingError


@pytest.fixture
def temp_prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with sample prompt files."""
    research_dir = tmp_path / "research"
    research_dir.mkdir(parents=True)

    # Create a versioned prompt file with frontmatter
    (research_dir / "web_search.v1.0.md").write_text(
        "---\n"
        "version: '1.0'\n"
        "author: test\n"
        "description: Web search prompt\n"
        "variables:\n"
        "  - topic\n"
        "  - max_results\n"
        "model_compatibility:\n"
        "  - gemini-2.5-pro\n"
        "---\n"
        "Search the web for {{topic}} and return {{max_results}} results.\n",
        encoding="utf-8",
    )

    # Create a second version
    (research_dir / "web_search.v1.1.md").write_text(
        "---\n"
        "version: '1.1'\n"
        "author: test\n"
        "description: Updated web search prompt\n"
        "variables:\n"
        "  - topic\n"
        "  - max_results\n"
        "---\n"
        "Search the web for {{topic}} and return up to {{max_results}} results.\n",
        encoding="utf-8",
    )

    # Create a prompt without version in filename
    (research_dir / "summarize.md").write_text(
        "---\n"
        "version: '1.0'\n"
        "description: Summarize content\n"
        "---\n"
        "Summarize the following: {{content}}\n",
        encoding="utf-8",
    )

    return tmp_path


class TestPromptManager:
    @pytest.mark.asyncio
    async def test_initialize(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_load_latest_version(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        template = await manager.load("research", "web_search")
        assert "up to" in template  # v1.1 should be loaded as latest

    @pytest.mark.asyncio
    async def test_load_specific_version(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        template = await manager.load("research", "web_search", version="1.0")
        assert "return" in template
        assert "up to" not in template

    @pytest.mark.asyncio
    async def test_load_not_found(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        with pytest.raises(PromptNotFoundError):
            await manager.load("research", "nonexistent")

    @pytest.mark.asyncio
    async def test_render(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        template = await manager.load("research", "web_search", version="1.0")
        rendered = manager.render(template, {"topic": "AI", "max_results": "10"})
        assert "AI" in rendered
        assert "10" in rendered

    def test_render_missing_variables(self):
        manager = PromptManager(prompts_dir="/nonexistent")
        template = "Hello {{name}}, you are {{age}} years old."
        with pytest.raises(PromptRenderingError):
            manager.render(template, {"name": "Alice"})

    def test_render_no_variables(self):
        manager = PromptManager(prompts_dir="/nonexistent")
        template = "This is a static prompt."
        rendered = manager.render(template, {})
        assert rendered == "This is a static prompt."

    @pytest.mark.asyncio
    async def test_get_metadata(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        metadata = await manager.get_metadata("research", "web_search", version="1.0")
        assert metadata["version"] == "1.0"
        assert metadata["author"] == "test"
        assert "topic" in metadata["variables"]
        assert "max_results" in metadata["variables"]
        assert "gemini-2.5-pro" in metadata["model_compatibility"]

    @pytest.mark.asyncio
    async def test_list_versions(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        versions = await manager.list_versions("research", "web_search")
        assert "1.0" in versions
        assert "1.1" in versions
        # Newest first
        assert versions[0] == "1.1"

    @pytest.mark.asyncio
    async def test_list_prompts(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        prompts = await manager.list_prompts("research")
        assert "web_search" in prompts
        assert "summarize" in prompts

    @pytest.mark.asyncio
    async def test_load_and_render(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        rendered = await manager.load_and_render(
            "research", "web_search",
            {"topic": "machine learning", "max_results": "5"},
            version="1.0",
        )
        assert "machine learning" in rendered
        assert "5" in rendered

    @pytest.mark.asyncio
    async def test_caching(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        # First load — populates cache
        template1 = await manager.load("research", "web_search", version="1.0")
        # Second load — should come from cache
        template2 = await manager.load("research", "web_search", version="1.0")
        assert template1 == template2

    @pytest.mark.asyncio
    async def test_nonexistent_dir(self):
        manager = PromptManager(prompts_dir=Path("/nonexistent/path"))
        await manager.initialize()
        # Should not raise, just have empty index
        prompts = await manager.list_prompts("research")
        assert prompts == []

    @pytest.mark.asyncio
    async def test_shutdown(self, temp_prompts_dir):
        manager = PromptManager(prompts_dir=temp_prompts_dir)
        await manager.initialize()
        await manager.shutdown()
        assert len(manager._cache) == 0
