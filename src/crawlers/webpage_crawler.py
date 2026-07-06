"""Generic listing-page crawler for article-like web sources."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any
from urllib.parse import urldefrag

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text

logger = logging.getLogger(__name__)

GENERIC_LINK_TITLES = {"", "article", "blog", "read more", "learn more", "website", "show content"}
DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}\s+[A-Z][a-z]{2,8}\s+\d{4}\b"),
    re.compile(r"\b[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
]
DATE_FORMATS = ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d")


class WebpageCrawler(BlogCrawler):
    """Fetch recent article-like links from a configured HTML listing page."""

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type.value != "blogs":
            raise ValueError("WebpageCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.listing_url = self._select_listing_url()

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch and parse the configured listing page."""

        html = self.fetch_url(self.listing_url)
        return self.parse_listing_page(html, limit=limit)

    def parse_listing_page(self, html: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse one HTML listing page into normalized raw article dictionaries."""

        soup = BeautifulSoup(html, "html.parser")
        articles: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for link in soup.select("a[href]"):
            article = self._link_to_article(link)
            if article is None:
                continue
            article_url = article["article_url"]
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)
            articles.append(article)
            if len(articles) >= limit:
                break

        return articles

    def _select_listing_url(self) -> str:
        """Return the first configured URL suitable for listing-page extraction."""

        for key in ("listing", "events", "library", "archives", "homepage"):
            url = self.source_config.urls.get(key)
            if url:
                return url
        raise ValueError(f"Webpage source requires one listing-like URL: {self.source_config.slug}")

    def _link_to_article(self, link: Tag) -> dict[str, Any] | None:
        """Convert one anchor node into an article record when it passes filters."""

        href = str(link.get("href") or "")
        article_url = self.to_absolute_url(self.listing_url, href)
        if not article_url or not article_url.startswith(("http://", "https://")):
            return None
        article_url = urldefrag(article_url).url

        link_text = clean_text(link.get_text(" ", strip=True))
        if not self._url_allowed(article_url) or not self._text_allowed(link_text):
            return None

        title = self._extract_title(link, article_url)
        if not title:
            return None

        excerpt = self._extract_excerpt(link)
        published_at = self._extract_date(link)
        tags = list(self.source_config.tags)

        return {
            "title": title,
            "authors": [],
            "published_at": published_at,
            "source_url": self.listing_url,
            "article_url": article_url,
            "excerpt": excerpt,
            "tags": tags,
            "source_type": "blogs",
        }

    def _extract_title(self, link: Tag, article_url: str) -> str:
        """Extract a useful title from a link node with a URL-slug fallback."""

        for selector in ("h1", "h2", "h3", "h4", "[class*=title i]"):
            title_node = link.select_one(selector)
            title = clean_text(title_node.get_text(" ", strip=True) if title_node else "")
            if title and title.lower() not in GENERIC_LINK_TITLES:
                return title

        title = clean_text(str(link.get("title") or ""))
        if title and title.lower() not in GENERIC_LINK_TITLES:
            return title

        link_text = clean_text(link.get_text(" ", strip=True))
        link_text = self._remove_date_text(link_text)
        if link_text and link_text.lower() not in GENERIC_LINK_TITLES:
            return link_text

        return self._title_from_url(article_url)

    def _extract_excerpt(self, link: Tag) -> str | None:
        """Extract a short excerpt when the listing includes one."""

        paragraph = link.find("p")
        if paragraph is None:
            return None
        excerpt = clean_text(paragraph.get_text(" ", strip=True))
        return excerpt or None

    def _extract_date(self, link: Tag) -> str | None:
        """Extract and normalize a date from common listing-page markup."""

        time_node = link.find("time")
        if time_node is not None:
            candidate = clean_text(str(time_node.get("datetime") or time_node.get_text(" ", strip=True)))
            normalized = self._normalize_date(candidate)
            if normalized:
                return normalized

        link_text = clean_text(link.get_text(" ", strip=True))
        for pattern in DATE_PATTERNS:
            match = pattern.search(link_text)
            if match:
                normalized = self._normalize_date(match.group(0))
                if normalized:
                    return normalized
        return None

    def _normalize_date(self, value: str | None) -> str | None:
        """Normalize common article date strings to YYYY-MM-DD."""

        cleaned = clean_text(value)
        if not cleaned:
            return None
        if len(cleaned) >= 10 and cleaned[4:5] == "-" and cleaned[7:8] == "-":
            return cleaned[:10]
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def _remove_date_text(self, value: str) -> str:
        """Remove leading date text from a concatenated anchor label."""

        cleaned = value
        for pattern in DATE_PATTERNS:
            cleaned = pattern.sub(" ", cleaned)
        return clean_text(cleaned)

    def _title_from_url(self, url: str) -> str:
        """Build a readable fallback title from the final URL path segment."""

        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if "." in slug:
            slug = slug.rsplit(".", 1)[0]
        return clean_text(slug.replace("-", " ").replace("_", " "))

    def _url_allowed(self, url: str) -> bool:
        """Return whether one URL passes configured URL filters."""

        include_prefixes = [str(item) for item in self.source_config.filters.get("include_url_prefixes", [])]
        include_contains = [str(item) for item in self.source_config.filters.get("include_url_contains", [])]
        exclude_prefixes = [str(item) for item in self.source_config.filters.get("exclude_url_prefixes", [])]
        exclude_contains = [str(item) for item in self.source_config.filters.get("exclude_url_contains", [])]

        if include_prefixes and not any(url.startswith(prefix) for prefix in include_prefixes):
            return False
        if include_contains and not any(fragment in url for fragment in include_contains):
            return False
        if exclude_prefixes and any(url.startswith(prefix) for prefix in exclude_prefixes):
            return False
        if exclude_contains and any(fragment in url for fragment in exclude_contains):
            return False
        return True

    def _text_allowed(self, text: str) -> bool:
        """Return whether one link label passes configured text filters."""

        include_values = [str(item).lower() for item in self.source_config.filters.get("include_text_contains", [])]
        exclude_values = [str(item).lower() for item in self.source_config.filters.get("exclude_text_contains", [])]
        normalized = text.lower()
        if include_values and not any(value in normalized for value in include_values):
            return False
        if exclude_values and any(value in normalized for value in exclude_values):
            return False
        return True
