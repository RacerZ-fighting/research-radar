"""Helpers for editing and testing configured sources from the web console."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from src.config.sources import DEFAULT_SOURCE_CONFIG_PATH, SourceConfig, load_source_configs
from src.crawlers.registry import BLOG_CRAWLER_REGISTRY, PAPER_CRAWLER_REGISTRY
from src.crawlers.rss_crawler import RSSFeedCrawler
from src.crawlers.sitemap_crawler import SitemapCrawler
from src.crawlers.webpage_crawler import WebpageCrawler
from src.models.enums import SourceType
from src.timezone import app_today


@dataclass(frozen=True, slots=True)
class SourceTestResult:
    """Result of a source test fetch."""

    ok: bool
    message: str
    items: list[dict[str, Any]]


def load_source_payload(config_path: Path | None = None) -> dict[str, Any]:
    """Load the mutable source config JSON payload."""

    path = config_path or DEFAULT_SOURCE_CONFIG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def save_source_payload(payload: dict[str, Any], config_path: Path | None = None) -> None:
    """Persist the source config JSON payload."""

    path = config_path or DEFAULT_SOURCE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_source_configs(config_path: Path | None = None) -> list[SourceConfig]:
    """Return all configured sources."""

    return load_source_configs(config_path)


def upsert_source_from_form(form: dict[str, str], config_path: Path | None = None) -> SourceConfig:
    """Create or update one source from web form fields."""

    payload = load_source_payload(config_path)
    sources = [source for source in payload.get("sources", []) if isinstance(source, dict)]
    source = _source_dict_from_form(form)
    existing_index = next((index for index, item in enumerate(sources) if item.get("slug") == source["slug"]), None)
    if existing_index is None:
        sources.append(source)
    else:
        sources[existing_index] = source
    payload["sources"] = sources
    save_source_payload(payload, config_path)
    return SourceConfig.from_dict(source)


def toggle_source(slug: str, config_path: Path | None = None) -> SourceConfig:
    """Toggle one source enabled flag and return its new config."""

    payload = load_source_payload(config_path)
    for source in payload.get("sources", []):
        if isinstance(source, dict) and source.get("slug") == slug:
            source["enabled"] = not bool(source.get("enabled", True))
            save_source_payload(payload, config_path)
            return SourceConfig.from_dict(source)
    raise ValueError(f"Unknown source: {slug}")


def test_source_fetch(slug: str, config_path: Path | None = None, *, limit: int = 3) -> SourceTestResult:
    """Fetch a small sample from one configured source."""

    configs = {config.slug: config for config in load_source_configs(config_path)}
    config = configs.get(slug)
    if config is None:
        return SourceTestResult(ok=False, message=f"Unknown source: {slug}", items=[])

    try:
        if config.source_type == SourceType.BLOGS:
            crawler = build_blog_crawler(config)
            items = crawler.fetch_articles(limit=limit)
        elif config.source_type == SourceType.PAPERS and config.slug in PAPER_CRAWLER_REGISTRY:
            crawler = PAPER_CRAWLER_REGISTRY[config.slug]()
            items = crawler.fetch_papers([app_today().year])[:limit]
        else:
            return SourceTestResult(
                ok=False,
                message=f"Testing is not available for adapter={config.adapter}",
                items=[],
            )
    except Exception as exc:
        return SourceTestResult(ok=False, message=str(exc), items=[])

    return SourceTestResult(ok=True, message=f"Fetched {len(items)} items from {config.name}", items=items[:limit])


def build_blog_crawler(config: SourceConfig):
    """Build a blog crawler for one source config."""

    if config.adapter == "rss":
        return RSSFeedCrawler(config)
    if config.adapter == "sitemap":
        return SitemapCrawler(config)
    if config.adapter == "webpage":
        return WebpageCrawler(config)
    if config.adapter == "crawler" and config.slug in BLOG_CRAWLER_REGISTRY:
        return BLOG_CRAWLER_REGISTRY[config.slug]()
    raise ValueError(f"Testing is not available for adapter={config.adapter}")


def _source_dict_from_form(form: dict[str, str]) -> dict[str, Any]:
    """Convert flat form fields into a source config dict."""

    slug = _slugify(form.get("slug") or form.get("name") or "")
    if not slug:
        raise ValueError("Source slug is required")

    source_type = form.get("source_type") or "blogs"
    track = form.get("track") or ("academic" if source_type == "papers" else "industry")
    tier = form.get("tier") or ("t2-arxiv" if source_type == "papers" else "t3-research-blog")
    adapter = form.get("adapter") or "webpage"
    urls = {
        key.removeprefix("url_"): value.strip()
        for key, value in form.items()
        if key.startswith("url_") and value.strip()
    }
    filters = {
        key: _split_values(form.get(key, ""))
        for key in ("include_url_prefixes", "include_url_contains", "exclude_url_contains", "exclude_text_contains")
        if _split_values(form.get(key, ""))
    }
    source: dict[str, Any] = {
        "slug": slug,
        "name": (form.get("name") or slug).strip(),
        "source_type": source_type,
        "tier": tier,
        "track": track,
        "adapter": adapter,
        "enabled": form.get("enabled", "false").lower() == "true",
        "aliases": _split_values(form.get("aliases", "")),
        "urls": urls,
        "tags": _split_values(form.get("tags", "")),
    }
    crawler = form.get("crawler", "").strip()
    if crawler:
        source["crawler"] = crawler
    if filters:
        source["filters"] = filters
    return source


def _split_values(raw_value: str) -> list[str]:
    """Split comma or newline separated form values."""

    return [item.strip() for item in re.split(r"[,\n]", raw_value or "") if item.strip()]


def _slugify(value: str) -> str:
    """Return a conservative source slug."""

    return re.sub(r"[^a-z0-9-]+", "-", value.strip().lower().replace("_", "-")).strip("-")
