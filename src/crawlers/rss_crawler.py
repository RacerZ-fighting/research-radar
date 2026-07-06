"""Generic RSS/Atom source crawler."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from time import struct_time
from typing import Any

import feedparser

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text
from src.exceptions import CrawlerError

logger = logging.getLogger(__name__)


class RSSFeedCrawler(BlogCrawler):
    """Fetch recent articles from a configured RSS or Atom feed."""

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type.value != "blogs":
            raise ValueError("RSSFeedCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.feed_url = source_config.urls.get("rss") or source_config.urls.get("feed")
        self.homepage_url = source_config.urls.get("homepage") or source_config.urls.get("listing") or self.feed_url
        if not self.feed_url:
            raise ValueError(f"RSS source requires urls.rss or urls.feed: {source_config.slug}")

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch and parse recent feed entries."""

        feed_text = self.fetch_url(self.feed_url)
        return self.parse_feed(feed_text, limit=limit)

    def parse_feed(self, feed_text: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse RSS/Atom text into normalized raw article dictionaries."""

        parsed = feedparser.parse(feed_text)
        is_malformed = bool(getattr(parsed, "bozo", 0))
        if is_malformed:
            exception = getattr(parsed, "bozo_exception", None)
            logger.warning("Feedparser reported a malformed feed for %s: %s", self.source_slug, exception)
            if not getattr(parsed, "entries", []):
                raise CrawlerError(f"Malformed RSS feed for {self.source_slug}: {exception}")

        articles: list[dict[str, Any]] = []
        for entry in getattr(parsed, "entries", [])[:limit]:
            article = self._entry_to_article(entry)
            if article is not None:
                articles.append(article)
        if is_malformed and not articles:
            raise CrawlerError(f"Malformed RSS feed for {self.source_slug}: no valid entries")
        return articles

    def _entry_to_article(self, entry: Any) -> dict[str, Any] | None:
        """Convert one feedparser entry into the project's raw blog shape."""

        title = clean_text(entry.get("title"))
        article_url = clean_text(entry.get("link"))
        if not title or not article_url:
            return None

        published_at = self._format_struct_time(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        excerpt = clean_text(
            entry.get("summary")
            or entry.get("description")
            or self._first_content_value(entry)
        ) or None
        authors = self._extract_authors(entry)
        tags = self._extract_tags(entry)

        return {
            "title": title,
            "authors": authors,
            "published_at": published_at,
            "source_url": self.homepage_url or self.feed_url,
            "article_url": article_url,
            "excerpt": excerpt,
            "tags": tags,
            "source_type": "blogs",
        }

    def _extract_authors(self, entry: Any) -> list[str]:
        """Extract author names from feedparser's flexible entry shape."""

        authors: list[str] = []
        for author in entry.get("authors", []) or []:
            name = clean_text(author.get("name") if isinstance(author, dict) else str(author))
            if name and name not in authors:
                authors.append(name)
        if not authors and entry.get("author"):
            authors.append(clean_text(entry.get("author")))
        return authors

    def _extract_tags(self, entry: Any) -> list[str]:
        """Extract tags/categories from one feed entry."""

        tags: list[str] = []
        for tag in entry.get("tags", []) or []:
            value = ""
            if isinstance(tag, dict):
                value = clean_text(tag.get("term") or tag.get("label"))
            else:
                value = clean_text(str(tag))
            if value and value not in tags:
                tags.append(value)
        return tags or list(self.source_config.tags)

    def _first_content_value(self, entry: Any) -> str:
        """Return the first content value from Atom content entries."""

        for content in entry.get("content", []) or []:
            if isinstance(content, dict) and content.get("value"):
                return str(content["value"])
        return ""

    def _format_struct_time(self, value: struct_time | None) -> str | None:
        """Convert feedparser parsed dates into an ISO date string."""

        if value is None:
            return None
        try:
            dt = datetime(*value[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None
        return dt.date().isoformat()
