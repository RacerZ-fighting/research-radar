"""Crawler registry and integration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.crawlers.base import BlogCrawler, PaperCrawler
from src.crawlers.allbsides_talk_crawler import AllBsidesTalkCrawler
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.crawlers.blackhat_schedule_crawler import BlackHatScheduleCrawler
from src.crawlers.browser_use_conference_crawler import BrowserUseConferenceCrawler
from src.crawlers.ccs_crawler import CCSCrawler
from src.crawlers.cloudflare_blog_crawler import CloudflareSecurityCrawler
from src.crawlers.defcon_talk_crawler import DefconTalkCrawler
from src.crawlers.ndss_crawler import NDSSCrawler
from src.crawlers.portswigger_crawler import PortSwiggerResearchCrawler
from src.crawlers.project_zero_crawler import ProjectZeroCrawler
from src.crawlers.rss_crawler import RSSFeedCrawler
from src.crawlers.rsac_agenda_crawler import RSACAgendaCrawler
from src.crawlers.sitemap_crawler import SitemapCrawler
from src.crawlers.sp_crawler import SPCrawler
from src.crawlers.usenix_security_crawler import USENIXSecurityCrawler
from src.crawlers.webpage_crawler import WebpageCrawler
from src.config.sources import SourceConfig, enabled_source_configs
from src.models.enums import SourceType

_PAPER_CRAWLER_CLASSES: dict[str, type[PaperCrawler]] = {
    "ndss": NDSSCrawler,
    "sp": SPCrawler,
    "ccs": CCSCrawler,
    "usenix-security": USENIXSecurityCrawler,
    "arxiv": ArxivCrawler,
}

_BLOG_CRAWLER_CLASSES: dict[str, type[BlogCrawler]] = {
    "portswigger": PortSwiggerResearchCrawler,
    "project-zero": ProjectZeroCrawler,
    "cloudflare-security": CloudflareSecurityCrawler,
    "defcon": DefconTalkCrawler,
}

PaperCrawlerFactory = Callable[[], PaperCrawler]
BlogCrawlerFactory = Callable[[], BlogCrawler]


def _build_paper_crawler_factory(config: SourceConfig) -> PaperCrawlerFactory:
    """Build one paper crawler factory from centralized source config."""

    crawler_cls = _PAPER_CRAWLER_CLASSES[config.crawler or ""]
    if config.crawler != "arxiv":
        return crawler_cls

    def build_arxiv_crawler(source_config: SourceConfig = config) -> ArxivCrawler:
        params = source_config.params
        categories = params.get("categories")
        if not isinstance(categories, list):
            categories = None
        max_results = params.get("max_results", 100)
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = 100
        return ArxivCrawler(categories=categories, max_results=max_results)

    return build_arxiv_crawler


def _build_blog_crawler_factory(config: SourceConfig) -> BlogCrawlerFactory:
    """Build one blog crawler factory from centralized source config."""

    if config.crawler == "allbsides":
        return lambda source_config=config: AllBsidesTalkCrawler(source_config)
    if config.crawler == "blackhat-schedule":
        return lambda source_config=config: BlackHatScheduleCrawler(source_config)
    if config.crawler == "rsac-agenda":
        return lambda source_config=config: RSACAgendaCrawler(source_config)
    if config.crawler == "browser-use-conference":
        return lambda source_config=config: BrowserUseConferenceCrawler(source_config)
    return _BLOG_CRAWLER_CLASSES[config.crawler or ""]


PAPER_CRAWLER_REGISTRY: dict[str, PaperCrawlerFactory] = {
    config.slug: _build_paper_crawler_factory(config)
    for config in enabled_source_configs(source_type=SourceType.PAPERS, adapters={"crawler"})
    if config.crawler in _PAPER_CRAWLER_CLASSES
}

BLOG_CRAWLER_REGISTRY: dict[str, BlogCrawlerFactory] = {
    config.slug: _build_blog_crawler_factory(config)
    for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"crawler"})
    if config.crawler in _BLOG_CRAWLER_CLASSES
    or config.crawler in {"allbsides", "blackhat-schedule", "rsac-agenda", "browser-use-conference"}
}
BLOG_CRAWLER_REGISTRY.update(
    {
        config.slug: (lambda source_config=config: RSSFeedCrawler(source_config))
        for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"rss"})
    }
)
BLOG_CRAWLER_REGISTRY.update(
    {
        config.slug: (lambda source_config=config: SitemapCrawler(source_config))
        for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"sitemap"})
    }
)
BLOG_CRAWLER_REGISTRY.update(
    {
        config.slug: (lambda source_config=config: WebpageCrawler(source_config))
        for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"webpage"})
    }
)


def build_default_paper_crawlers() -> dict[str, PaperCrawler]:
    """Instantiate all default conference paper crawlers."""

    return {name: crawler_cls() for name, crawler_cls in PAPER_CRAWLER_REGISTRY.items()}


def build_default_blog_crawlers() -> dict[str, BlogCrawler]:
    """Instantiate all default blog crawlers."""

    return {name: crawler_cls() for name, crawler_cls in BLOG_CRAWLER_REGISTRY.items()}


def crawl_default_papers(
    years: list[int],
    *,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Run all default paper crawlers and save raw outputs."""

    target_dir = output_dir or Path("data/raw/papers")
    saved_files: dict[str, Path] = {}
    for name, crawler in build_default_paper_crawlers().items():
        papers = crawler.fetch_papers(years)
        saved_files[name] = crawler.save_raw(papers, target_dir, metadata={"years": years})
    return saved_files


def crawl_default_blogs(
    limit: int = 20,
    *,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Run all default blog crawlers and save raw outputs."""

    target_dir = output_dir or Path("data/raw/blogs")
    saved_files: dict[str, Path] = {}
    for name, crawler in build_default_blog_crawlers().items():
        articles = crawler.fetch_articles(limit=limit)
        saved_files[name] = crawler.save_raw(articles, target_dir, metadata={"limit": limit})
    return saved_files
