"""Tests for the generic listing-page crawler."""

from __future__ import annotations

from src.config.sources import SourceConfig
from src.crawlers.webpage_crawler import WebpageCrawler
from src.models.enums import SourceType


def test_webpage_crawler_parses_brutecat_style_listing() -> None:
    """The generic crawler should handle compact article-card anchors."""

    crawler = WebpageCrawler(_source_config("https://brutecat.com/articles"))
    html = """
    <a class="entry__link" href="/articles/hacking-google-with-ai/">
      <time class="entry__date" datetime="2026-06-11T00:00:00.000Z">11 Jun 2026</time>
      <h2 class="entry__title">Hacking Google with A.I. for $500,000</h2>
      <p class="entry__abstract">What happens when an AI agent targets large systems?</p>
    </a>
    """

    articles = crawler.parse_listing_page(html)

    assert len(articles) == 1
    assert articles[0]["title"] == "Hacking Google with A.I. for $500,000"
    assert articles[0]["published_at"] == "2026-06-11"
    assert articles[0]["article_url"] == "https://brutecat.com/articles/hacking-google-with-ai/"
    assert articles[0]["excerpt"] == "What happens when an AI agent targets large systems?"
    assert articles[0]["tags"] == ["security"]


def test_webpage_crawler_parses_hacktron_style_listing() -> None:
    """Date text inside a link should be normalized without polluting the title."""

    crawler = WebpageCrawler(_source_config("https://www.hacktron.ai/blog"))
    html = """
    <a href="/blog/metabase-cloud">
      <h3>Metabase Cloud: The winner takes it all</h3>
      <p>We could have pwned every cloud customer.</p>
      <span>June 25, 2026</span>
    </a>
    """

    articles = crawler.parse_listing_page(html)

    assert len(articles) == 1
    assert articles[0]["title"] == "Metabase Cloud: The winner takes it all"
    assert articles[0]["published_at"] == "2026-06-25"
    assert articles[0]["article_url"] == "https://www.hacktron.ai/blog/metabase-cloud"


def test_webpage_crawler_filters_and_deduplicates_links() -> None:
    """Configured URL filters should suppress unrelated links and duplicates."""

    crawler = WebpageCrawler(
        _source_config(
            "https://example.com/blog",
            filters={"include_url_prefixes": ["https://example.com/blog/"]},
        )
    )
    html = """
    <a href="/about">About</a>
    <a href="/blog/first"><h2>First post</h2></a>
    <a href="/blog/first#comments"><h2>First post duplicate</h2></a>
    """

    articles = crawler.parse_listing_page(html)

    assert [article["title"] for article in articles] == ["First post"]


def _source_config(
    listing_url: str,
    *,
    filters: dict[str, object] | None = None,
) -> SourceConfig:
    """Return one synthetic webpage source config."""

    return SourceConfig(
        slug="example-webpage",
        name="Example Webpage",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="webpage",
        enabled=True,
        crawler=None,
        aliases=("example",),
        urls={"listing": listing_url},
        filters=filters or {"include_url_prefixes": [listing_url.rstrip("/") + "/"]},
        tags=("security",),
    )
