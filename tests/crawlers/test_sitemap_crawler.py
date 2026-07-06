"""Tests for the generic sitemap crawler."""

from __future__ import annotations

from src.config.sources import SourceConfig
from src.crawlers.sitemap_crawler import SitemapCrawler
from src.models.enums import SourceType


def test_sitemap_crawler_filters_urls_and_uses_lastmod() -> None:
    """Sitemap parsing should keep configured URLs and preserve lastmod dates."""

    crawler = SitemapCrawler(_source_config())
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.anthropic.com/news/claude-code-security</loc>
        <lastmod>2026-02-20T17:59:33.000Z</lastmod>
      </url>
      <url>
        <loc>https://www.anthropic.com/careers</loc>
        <lastmod>2026-02-21T00:00:00.000Z</lastmod>
      </url>
    </urlset>
    """

    entries = crawler.parse_sitemap(xml)

    assert len(entries) == 1
    assert entries[0].url == "https://www.anthropic.com/news/claude-code-security"
    assert entries[0].lastmod == "2026-02-20T17:59:33.000Z"


def test_sitemap_crawler_uses_listing_metadata_for_title_date_and_subject() -> None:
    """Listing page metadata should override URL-derived fallback titles."""

    crawler = SitemapCrawler(_source_config())
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.anthropic.com/news/AI-enabled-cyber-threats-mitre-attack</loc>
        <lastmod>2026-06-03T16:18:23.000Z</lastmod>
      </url>
    </urlset>
    """
    listing = """
    <a href="/news/AI-enabled-cyber-threats-mitre-attack">
      <div><time>Jun 3, 2026</time><span>Policy</span></div>
      <span>What we learned mapping a year’s worth of AI-enabled cyber threats</span>
    </a>
    """
    entries = crawler.parse_sitemap(xml)
    metadata = crawler.parse_listing_page(listing)

    article = crawler._entry_to_article(entries[0], metadata)

    assert article is not None
    assert article["title"] == "What we learned mapping a year’s worth of AI-enabled cyber threats"
    assert article["published_at"] == "2026-06-03"
    assert article["article_url"] == "https://www.anthropic.com/news/AI-enabled-cyber-threats-mitre-attack"
    assert article["tags"] == ["frontier-ai", "ai-security", "Policy"]


def test_sitemap_crawler_fetches_detail_excerpt_for_limited_entries() -> None:
    """Sitemap sources should enrich limited entries with article detail body text."""

    crawler = SitemapCrawler(_source_config())
    sitemap = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.anthropic.com/news/claude-sonnet-5</loc>
        <lastmod>2026-06-30T10:00:00.000Z</lastmod>
      </url>
      <url>
        <loc>https://www.anthropic.com/news/redeploying-fable-5</loc>
        <lastmod>2026-06-29T10:00:00.000Z</lastmod>
      </url>
    </urlset>
    """
    listing = """
    <a href="/news/claude-sonnet-5">
      <time>Jun 30, 2026</time>
      <span>Product</span>
      <span>Introducing Claude Sonnet 5</span>
    </a>
    """
    detail = """
    <html>
      <body>
        <nav>Navigation should not be included.</nav>
        <article>
          <h1>Introducing Claude Sonnet 5</h1>
          <p>Claude Sonnet 5 is built to be the most agentic Sonnet model yet.</p>
          <p>It can make plans, use tools like browsers and terminals, and run autonomously.</p>
        </article>
      </body>
    </html>
    """
    fetched_urls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetched_urls.append(url)
        if url.endswith("sitemap.xml"):
            return sitemap
        if url == "https://www.anthropic.com/news":
            return listing
        if url == "https://www.anthropic.com/news/claude-sonnet-5":
            return detail
        raise AssertionError(f"Unexpected fetch: {url}")

    crawler.fetch_url = fake_fetch  # type: ignore[method-assign]

    articles = crawler.fetch_articles(limit=1)

    assert len(articles) == 1
    assert articles[0]["title"] == "Introducing Claude Sonnet 5"
    assert "most agentic Sonnet model" in articles[0]["excerpt"]
    assert "Navigation should not be included" not in articles[0]["excerpt"]
    assert "https://www.anthropic.com/news/redeploying-fable-5" not in fetched_urls


def _source_config() -> SourceConfig:
    """Return one synthetic sitemap source config."""

    return SourceConfig(
        slug="anthropic-news",
        name="Anthropic News",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="sitemap",
        enabled=True,
        crawler=None,
        aliases=("anthropic",),
        urls={
            "homepage": "https://www.anthropic.com/news",
            "sitemap": "https://www.anthropic.com/sitemap.xml",
        },
        filters={"include_url_prefixes": ["https://www.anthropic.com/news/"]},
        tags=("frontier-ai", "ai-security"),
    )
