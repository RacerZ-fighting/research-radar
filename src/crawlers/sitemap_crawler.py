"""Generic sitemap-backed source crawler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text
from src.exceptions import CrawlerError

logger = logging.getLogger(__name__)

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
DETAIL_EXCERPT_MAX_CHARS = 6000


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    """One URL discovered from a sitemap."""

    url: str
    lastmod: str | None


class SitemapCrawler(BlogCrawler):
    """Fetch article-like entries from a configured XML sitemap."""

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type.value != "blogs":
            raise ValueError("SitemapCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.sitemap_url = source_config.urls.get("sitemap")
        self.homepage_url = source_config.urls.get("homepage") or source_config.urls.get("listing")
        if not self.sitemap_url:
            raise ValueError(f"Sitemap source requires urls.sitemap: {source_config.slug}")

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch sitemap entries and return recent article-like records."""

        sitemap_text = self.fetch_url(self.sitemap_url)
        entries = self.parse_sitemap(sitemap_text)
        listing_metadata = self._load_listing_metadata()
        articles = [self._entry_to_article(entry, listing_metadata) for entry in entries[:limit]]
        articles = [article for article in articles if article is not None]
        return articles

    def parse_sitemap(self, xml_text: str) -> list[SitemapEntry]:
        """Parse a URL sitemap and filter configured article URLs."""

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise CrawlerError(f"Failed to parse sitemap for {self.source_slug}: {exc}") from exc

        if root.tag.endswith("sitemapindex"):
            return self._parse_sitemap_index(root)

        entries: list[SitemapEntry] = []
        for url_node in root.findall(f"{SITEMAP_NS}url"):
            loc = self._child_text(url_node, "loc")
            if not loc or not self._url_allowed(loc):
                continue
            entries.append(SitemapEntry(url=loc, lastmod=self._child_text(url_node, "lastmod")))

        return sorted(entries, key=lambda entry: entry.lastmod or "", reverse=True)

    def parse_listing_page(self, html: str) -> dict[str, dict[str, str]]:
        """Extract link metadata from a listing page."""

        soup = BeautifulSoup(html, "html.parser")
        metadata: dict[str, dict[str, str]] = {}
        base_url = self.homepage_url or self.sitemap_url

        for link in soup.select("a[href]"):
            article_url = urljoin(base_url, str(link.get("href") or ""))
            if not self._url_allowed(article_url):
                continue
            span_nodes = link.find_all("span")
            title = clean_text(span_nodes[-1].get_text(" ", strip=True)) if span_nodes else clean_text(link.get_text(" ", strip=True))
            date_node = link.select_one("time")
            subject_node = span_nodes[0] if len(span_nodes) > 1 else None
            item: dict[str, str] = {}
            if title:
                item["title"] = title
            if date_node:
                item["published_at"] = clean_text(date_node.get("datetime") or date_node.get_text(" ", strip=True))
            if subject_node:
                item["subject"] = clean_text(subject_node.get_text(" ", strip=True))
            if item:
                metadata[article_url] = item

        return metadata

    def _parse_sitemap_index(self, root: ET.Element) -> list[SitemapEntry]:
        """Parse a sitemap index by fetching child sitemaps."""

        entries: list[SitemapEntry] = []
        for sitemap_node in root.findall(f"{SITEMAP_NS}sitemap"):
            child_url = self._child_text(sitemap_node, "loc")
            if not child_url:
                continue
            try:
                entries.extend(self.parse_sitemap(self.fetch_url(child_url)))
            except CrawlerError:
                logger.warning("Skipping failed child sitemap for %s: %s", self.source_slug, child_url)
        return sorted(entries, key=lambda entry: entry.lastmod or "", reverse=True)

    def _load_listing_metadata(self) -> dict[str, dict[str, str]]:
        """Load optional listing-page metadata for discovered URLs."""

        if not self.homepage_url:
            return {}
        try:
            return self.parse_listing_page(self.fetch_url(self.homepage_url))
        except CrawlerError:
            logger.warning("Failed to fetch listing metadata for %s", self.source_slug)
            return {}

    def _entry_to_article(
        self,
        entry: SitemapEntry,
        listing_metadata: dict[str, dict[str, str]],
    ) -> dict[str, Any] | None:
        """Convert one sitemap entry into the project's raw blog shape."""

        metadata = listing_metadata.get(entry.url, {})
        title = clean_text(metadata.get("title")) or self._title_from_url(entry.url)
        if not title:
            return None
        published_at = self._normalize_date(metadata.get("published_at")) or self._normalize_date(entry.lastmod)
        tags = list(self.source_config.tags)
        subject = clean_text(metadata.get("subject"))
        if subject and subject not in tags:
            tags.append(subject)

        return {
            "title": title,
            "authors": [],
            "published_at": published_at,
            "source_url": self.homepage_url or self.sitemap_url,
            "article_url": entry.url,
            "excerpt": self._load_article_excerpt(entry.url),
            "tags": tags,
            "source_type": "blogs",
        }

    def _load_article_excerpt(self, url: str) -> str | None:
        """Fetch one article page and extract readable body text."""

        try:
            return self._extract_article_text(self.fetch_url(url))
        except CrawlerError:
            logger.warning("Failed to fetch article detail for %s: %s", self.source_slug, url)
            return None

    def _extract_article_text(self, html: str) -> str | None:
        """Extract the most useful article body text from a detail page."""

        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("script, style, noscript, svg, nav, footer, header"):
            node.decompose()

        candidates = soup.select("article, main")
        if not candidates:
            candidates = [soup.body] if soup.body else []

        best_text = ""
        for candidate in candidates:
            if candidate is None:
                continue
            text = clean_text(candidate.get_text(" ", strip=True))
            if len(text) > len(best_text):
                best_text = text

        if not best_text:
            return None
        if len(best_text) > DETAIL_EXCERPT_MAX_CHARS:
            return best_text[:DETAIL_EXCERPT_MAX_CHARS].rstrip() + "..."
        return best_text

    def _child_text(self, node: ET.Element, child_name: str) -> str | None:
        """Return text for one sitemap child node."""

        child = node.find(f"{SITEMAP_NS}{child_name}")
        if child is None or child.text is None:
            return None
        return clean_text(child.text)

    def _url_allowed(self, url: str) -> bool:
        """Return whether one URL passes configured filters."""

        include_prefixes = [str(prefix) for prefix in self.source_config.filters.get("include_url_prefixes", [])]
        exclude_prefixes = [str(prefix) for prefix in self.source_config.filters.get("exclude_url_prefixes", [])]
        if include_prefixes and not any(url.startswith(prefix) for prefix in include_prefixes):
            return False
        if exclude_prefixes and any(url.startswith(prefix) for prefix in exclude_prefixes):
            return False
        return True

    def _normalize_date(self, value: str | None) -> str | None:
        """Normalize sitemap/listing dates to YYYY-MM-DD when possible."""

        cleaned = clean_text(value)
        if not cleaned:
            return None
        if len(cleaned) >= 10 and cleaned[4:5] == "-" and cleaned[7:8] == "-":
            return cleaned[:10]
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return cleaned

    def _title_from_url(self, url: str) -> str:
        """Build a readable fallback title from the final URL path segment."""

        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return clean_text(slug.replace("-", " "))
