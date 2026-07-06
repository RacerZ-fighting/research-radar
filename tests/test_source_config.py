"""Tests for centralized source configuration."""

from __future__ import annotations

from src.config.sources import (
    enabled_crawler_configs,
    enabled_source_configs,
    infer_source_tier,
    resolve_source_slug,
    source_configs_by_slug,
)
from src.crawlers.allbsides_talk_crawler import AllBsidesTalkCrawler
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.crawlers.blackhat_schedule_crawler import BlackHatScheduleCrawler
from src.crawlers.browser_use_conference_crawler import BrowserUseConferenceCrawler
from src.crawlers.defcon_talk_crawler import DefconTalkCrawler
from src.crawlers.registry import BLOG_CRAWLER_REGISTRY, PAPER_CRAWLER_REGISTRY
from src.models.enums import SourceType


def test_source_config_loads_current_enabled_sources() -> None:
    """The centralized config should expose the current default crawler sources."""

    configs = source_configs_by_slug()

    assert configs["ndss"].tier == "t1-conference"
    assert configs["arxiv"].tier == "t2-arxiv"
    assert configs["portswigger"].tier == "t3-research-blog"
    assert configs["openai-blog"].enabled is True
    assert "cloudflare-security" not in configs
    assert "trail-of-bits" not in configs
    assert configs["arxiv"].params["max_results"] == 30
    assert "daily-disabled" in configs["project-zero"].tags


def test_enabled_crawler_configs_exclude_disabled_rss_placeholders() -> None:
    """Only enabled crawler-backed sources should participate in default crawling."""

    blog_slugs = {config.slug for config in enabled_crawler_configs(source_type=SourceType.BLOGS)}

    assert blog_slugs == {
        "portswigger",
        "project-zero",
        "blackhat-usa",
        "blackhat-asia",
        "blackhat-europe",
        "defcon",
        "bsidessf",
    }
    assert "openai-blog" not in blog_slugs
    assert "brutecat" not in blog_slugs


def test_enabled_rss_sources_are_registered_for_crawl() -> None:
    """Enabled RSS sources should be available through the crawl registry."""

    rss_slugs = {config.slug for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"rss"})}

    assert rss_slugs == {"openai-blog"}
    assert "openai-blog" in BLOG_CRAWLER_REGISTRY


def test_arxiv_registry_uses_source_params() -> None:
    """arXiv crawler should use centralized fetch limits and categories."""

    crawler = PAPER_CRAWLER_REGISTRY["arxiv"]()

    assert isinstance(crawler, ArxivCrawler)
    assert crawler.max_results == 30
    assert crawler.categories == ["cs.CR", "cs.SE", "cs.PL"]


def test_enabled_sitemap_sources_are_registered_for_crawl() -> None:
    """Enabled sitemap sources should be available through the crawl registry."""

    sitemap_slugs = {
        config.slug for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"sitemap"})
    }

    assert sitemap_slugs == {"anthropic-news"}
    assert "anthropic-news" in BLOG_CRAWLER_REGISTRY


def test_enabled_webpage_sources_are_registered_for_crawl() -> None:
    """Enabled webpage sources should be available through the crawl registry."""

    webpage_slugs = {
        config.slug for config in enabled_source_configs(source_type=SourceType.BLOGS, adapters={"webpage"})
    }

    assert "brutecat" in webpage_slugs
    assert "hacktron-ai" in webpage_slugs
    assert "blackhat-usa" not in webpage_slugs
    assert "rsac" not in webpage_slugs
    assert "defcon" not in webpage_slugs
    assert "bsidessf" not in webpage_slugs
    assert "brutecat" in BLOG_CRAWLER_REGISTRY


def test_defcon_registry_uses_talk_crawler() -> None:
    """DEF CON should use the dedicated talk parser rather than generic webpage links."""

    crawler = BLOG_CRAWLER_REGISTRY["defcon"]()

    assert isinstance(crawler, DefconTalkCrawler)


def test_bsidessf_registry_uses_allbsides_fallback_crawler() -> None:
    """BSidesSF should use the AllBSides fallback while Sched is Cloudflare-blocked."""

    crawler = BLOG_CRAWLER_REGISTRY["bsidessf"]()

    assert isinstance(crawler, AllBsidesTalkCrawler)
    assert crawler.organizer_slug == "bsidessf"
    assert crawler.event_year == 2026


def test_blackhat_registry_uses_official_schedule_crawler_for_published_schedules() -> None:
    """Black Hat events with published schedules should use the official schedule parser."""

    expected_urls = {
        "blackhat-usa": "https://www.blackhat.com/us-26/briefings/schedule/index.html",
        "blackhat-asia": "https://blackhat.com/asia-26/briefings/schedule/index.html",
    }

    for slug, schedule_url in expected_urls.items():
        crawler = BLOG_CRAWLER_REGISTRY[slug]()

        assert isinstance(crawler, BlackHatScheduleCrawler)
        assert crawler.schedule_url == schedule_url
        assert crawler.cookie_env == "BLACKHAT_COOKIE"


def test_unpublished_blackhat_registry_uses_browser_use_crawler() -> None:
    """Black Hat events without a published official schedule should keep browser-use for now."""

    crawler = BLOG_CRAWLER_REGISTRY["blackhat-europe"]()

    assert isinstance(crawler, BrowserUseConferenceCrawler)


def test_rsac_source_is_not_registered() -> None:
    """RSAC should stay out of the configured crawl registry."""

    configs = source_configs_by_slug()

    assert "rsac" not in configs
    assert "rsac" not in BLOG_CRAWLER_REGISTRY


def test_resolve_source_slug_accepts_aliases() -> None:
    """CLI source resolution should use configured aliases."""

    assert resolve_source_slug("project_zero") == "project-zero"
    assert resolve_source_slug("PortSwigger Research") == "portswigger"
    assert resolve_source_slug("USENIX_SECURITY") == "usenix-security"


def test_infer_source_tier_uses_central_config() -> None:
    """Normalization tier inference should come from central source metadata."""

    assert infer_source_tier("Brutecat Articles", SourceType.BLOGS) == "t3-research-blog"
    assert infer_source_tier("arXiv", SourceType.PAPERS) == "t2-arxiv"
    assert infer_source_tier("Unlisted Blog", SourceType.BLOGS) == "blog"
