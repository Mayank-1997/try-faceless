"""Metadata Engine.

Generates publishing metadata:
- Title
- Description
- Tags
- Keywords
- Category
- Hashtags
- Language
- SEO metadata
- Platform metadata
"""

from __future__ import annotations

import re
from typing import Any

from src.publishing.schema import PublishingMetadata, PublishingPlatform, YouTubeCategory
from src.core.logging import get_logger


class MetadataEngine:
    """Generates and optimizes publishing metadata.

    Takes raw project metadata (title, description, keywords) and
    produces platform-optimized metadata with proper length limits,
    SEO optimization, and hashtag generation.
    """

    # Platform-specific limits
    TITLE_LIMITS: dict[PublishingPlatform, int] = {
        PublishingPlatform.YOUTUBE: 100,
        PublishingPlatform.LINKEDIN: 100,
        PublishingPlatform.MEDIUM: 200,
        PublishingPlatform.WORDPRESS: 200,
        PublishingPlatform.TWITTER: 100,
        PublishingPlatform.FACEBOOK: 100,
        PublishingPlatform.INSTAGRAM: 100,
        PublishingPlatform.TIKTOK: 100,
        PublishingPlatform.PODCAST: 200,
        PublishingPlatform.CUSTOM: 200,
    }

    DESCRIPTION_LIMITS: dict[PublishingPlatform, int] = {
        PublishingPlatform.YOUTUBE: 5000,
        PublishingPlatform.LINKEDIN: 3000,
        PublishingPlatform.MEDIUM: 10000,
        PublishingPlatform.WORDPRESS: 50000,
        PublishingPlatform.TWITTER: 1000,
        PublishingPlatform.FACEBOOK: 63206,
        PublishingPlatform.INSTAGRAM: 2200,
        PublishingPlatform.TIKTOK: 2200,
        PublishingPlatform.PODCAST: 4000,
        PublishingPlatform.CUSTOM: 5000,
    }

    MAX_TAGS: dict[PublishingPlatform, int] = {
        PublishingPlatform.YOUTUBE: 500,
        PublishingPlatform.LINKEDIN: 50,
        PublishingPlatform.MEDIUM: 50,
        PublishingPlatform.WORDPRESS: 100,
        PublishingPlatform.TWITTER: 30,
        PublishingPlatform.FACEBOOK: 50,
        PublishingPlatform.INSTAGRAM: 30,
        PublishingPlatform.TIKTOK: 30,
        PublishingPlatform.PODCAST: 50,
        PublishingPlatform.CUSTOM: 100,
    }

    MAX_TAG_LENGTH: dict[PublishingPlatform, int] = {
        PublishingPlatform.YOUTUBE: 30,
        PublishingPlatform.LINKEDIN: 60,
        PublishingPlatform.MEDIUM: 60,
        PublishingPlatform.WORDPRESS: 50,
        PublishingPlatform.TWITTER: 50,
        PublishingPlatform.FACEBOOK: 50,
        PublishingPlatform.INSTAGRAM: 50,
        PublishingPlatform.TIKTOK: 50,
        PublishingPlatform.PODCAST: 50,
        PublishingPlatform.CUSTOM: 50,
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def generate_metadata(
        self,
        *,
        title: str = "",
        description: str = "",
        keywords: list[str] | None = None,
        category: str = "",
        language: str = "en",
        platform: PublishingPlatform = PublishingPlatform.YOUTUBE,
        project_metadata: dict[str, Any] | None = None,
    ) -> PublishingMetadata:
        """Generate platform-optimized metadata.

        Args:
            title: Raw title.
            description: Raw description.
            keywords: Raw keywords.
            category: Category string.
            language: Content language code.
            platform: Target platform.
            project_metadata: Additional project metadata.

        Returns:
            A ``PublishingMetadata`` optimized for the platform.
        """
        project_metadata = project_metadata or {}
        keywords = keywords or []

        # Truncate title to platform limit
        title_limit = self.TITLE_LIMITS.get(platform, 200)
        optimized_title = self._truncate_title(title, title_limit)

        # Truncate description to platform limit
        desc_limit = self.DESCRIPTION_LIMITS.get(platform, 5000)
        optimized_description = self._optimize_description(description, desc_limit)

        # Generate tags from keywords
        max_tags = self.MAX_TAGS.get(platform, 100)
        max_tag_length = self.MAX_TAG_LENGTH.get(platform, 50)
        tags = self._generate_tags(keywords, max_tags, max_tag_length)

        # Generate hashtags
        hashtags = self._generate_hashtags(keywords, platform)

        # Generate SEO metadata
        seo = self._generate_seo_metadata(title, description, keywords)

        # Platform-specific metadata
        platform_meta = self._generate_platform_metadata(platform, project_metadata)

        metadata = PublishingMetadata(
            title=optimized_title,
            description=optimized_description,
            tags=tags,
            keywords=keywords,
            category=category,
            hashtags=hashtags,
            language=language,
            seo_metadata=seo,
            platform_metadata=platform_meta,
        )

        self._logger.info(
            "metadata_generated",
            platform=platform.value,
            title_length=len(optimized_title),
            tag_count=len(tags),
            hashtag_count=len(hashtags),
        )

        return metadata

    def _truncate_title(self, title: str, limit: int) -> str:
        """Truncate title to the platform limit."""
        if len(title) <= limit:
            return title
        # Truncate at word boundary
        truncated = title[: limit - 3]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated + "..."

    def _optimize_description(self, description: str, limit: int) -> str:
        """Optimize description for the platform."""
        if len(description) <= limit:
            return description
        return description[:limit]

    def _generate_tags(self, keywords: list[str], max_tags: int, max_tag_length: int) -> list[str]:
        """Generate tags from keywords."""
        tags: list[str] = []
        seen: set[str] = set()
        for kw in keywords:
            tag = kw.strip().lower()[:max_tag_length]
            if tag and tag not in seen and len(tags) < max_tags:
                tags.append(tag)
                seen.add(tag)
        return tags

    def _generate_hashtags(self, keywords: list[str], platform: PublishingPlatform) -> list[str]:
        """Generate hashtags from keywords."""
        if platform == PublishingPlatform.YOUTUBE:
            # YouTube doesn't use hashtags in the same way
            return []

        max_hashtags = 30 if platform == PublishingPlatform.INSTAGRAM else 10
        hashtags: list[str] = []
        seen: set[str] = set()
        for kw in keywords:
            # Convert to hashtag: remove special chars, capitalize words
            tag = re.sub(r"[^a-zA-Z0-9]", "", kw.strip())
            if tag and tag not in seen and len(hashtags) < max_hashtags:
                hashtags.append(f"#{tag}")
                seen.add(tag)
        return hashtags

    def _generate_seo_metadata(
        self, title: str, description: str, keywords: list[str]
    ) -> dict[str, Any]:
        """Generate SEO metadata."""
        return {
            "og:title": title[:100],
            "og:description": description[:200],
            "og:type": "video.other",
            "keywords": ", ".join(keywords[:20]),
            "twitter:card": "summary_large_image",
            "twitter:title": title[:70],
            "twitter:description": description[:200],
        }

    def _generate_platform_metadata(
        self, platform: PublishingPlatform, project_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate platform-specific metadata."""
        meta: dict[str, Any] = {}
        if platform == PublishingPlatform.YOUTUBE:
            meta["category"] = project_metadata.get("category", YouTubeCategory.EDUCATION.value)
            meta["license"] = project_metadata.get("license", "youtube")
            meta["made_for_kids"] = project_metadata.get("made_for_kids", False)
            meta["embeddable"] = project_metadata.get("embeddable", True)
            meta["public_stats_viewable"] = project_metadata.get("public_stats_viewable", True)
            meta["notify_subscribers"] = project_metadata.get("notify_subscribers", True)
        elif platform == PublishingPlatform.LINKEDIN:
            meta["visibility"] = project_metadata.get("visibility", "PUBLIC")
            meta["reshared"] = False
        elif platform == PublishingPlatform.MEDIUM:
            meta["publish_status"] = project_metadata.get("publish_status", "public")
            meta["license"] = project_metadata.get("license", "all-rights-reserved")
        elif platform == PublishingPlatform.WORDPRESS:
            meta["post_status"] = project_metadata.get("post_status", "publish")
            meta["comment_status"] = "open"
        elif platform == PublishingPlatform.TWITTER:
            meta["reply_settings"] = "everyone"
        return meta

    def validate_metadata(
        self, metadata: PublishingMetadata, platform: PublishingPlatform
    ) -> list[str]:
        """Validate metadata against platform requirements.

        Args:
            metadata: The metadata to validate.
            platform: Target platform.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []
        title_limit = self.TITLE_LIMITS.get(platform, 200)
        desc_limit = self.DESCRIPTION_LIMITS.get(platform, 5000)
        max_tags = self.MAX_TAGS.get(platform, 100)
        max_tag_length = self.MAX_TAG_LENGTH.get(platform, 50)

        if not metadata.title:
            errors.append("Title is required")
        elif len(metadata.title) > title_limit:
            errors.append(f"Title exceeds {title_limit} characters (got {len(metadata.title)})")

        if len(metadata.description) > desc_limit:
            errors.append(f"Description exceeds {desc_limit} characters (got {len(metadata.description)})")

        if len(metadata.tags) > max_tags:
            errors.append(f"Too many tags: {len(metadata.tags)} (max {max_tags})")

        for tag in metadata.tags:
            if len(tag) > max_tag_length:
                errors.append(f"Tag '{tag}' exceeds {max_tag_length} characters")

        return errors

    def get_title_limit(self, platform: PublishingPlatform) -> int:
        """Get the title length limit for a platform."""
        return self.TITLE_LIMITS.get(platform, 200)

    def get_description_limit(self, platform: PublishingPlatform) -> int:
        """Get the description length limit for a platform."""
        return self.DESCRIPTION_LIMITS.get(platform, 5000)
