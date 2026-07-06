"""Tests for the generic RSS/Atom crawler."""

from __future__ import annotations

import pytest

from src.config.sources import SourceConfig
from src.crawlers.rss_crawler import RSSFeedCrawler
from src.exceptions import CrawlerError
from src.models.enums import SourceType


def test_rss_feed_crawler_parses_common_rss_fields() -> None:
    """RSS parsing should produce the same raw article shape as custom blog crawlers."""

    crawler = RSSFeedCrawler(_source_config())
    feed = """
    <rss version="2.0">
      <channel>
        <item>
          <title>Frontier model safety update</title>
          <link>https://example.com/news/frontier-model-safety</link>
          <description>Research notes on model behavior and security.</description>
          <pubDate>Tue, 16 Jun 2026 10:00:00 GMT</pubDate>
          <author>research@example.com (Example Research)</author>
          <category>AI Security</category>
        </item>
      </channel>
    </rss>
    """

    articles = crawler.parse_feed(feed)

    assert len(articles) == 1
    assert articles[0]["title"] == "Frontier model safety update"
    assert articles[0]["article_url"] == "https://example.com/news/frontier-model-safety"
    assert articles[0]["published_at"] == "2026-06-16"
    assert articles[0]["excerpt"] == "Research notes on model behavior and security."
    assert articles[0]["authors"] == ["Example Research"]
    assert articles[0]["tags"] == ["AI Security"]
    assert articles[0]["source_type"] == "blogs"


def test_rss_feed_crawler_uses_source_tags_when_entry_has_no_tags() -> None:
    """Configured source tags should be used as a fallback."""

    crawler = RSSFeedCrawler(_source_config())
    feed = """
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Agent safety note</title>
        <link href="https://example.com/news/agent-safety-note"/>
        <updated>2026-06-16T12:00:00Z</updated>
        <summary>Short note.</summary>
      </entry>
    </feed>
    """

    articles = crawler.parse_feed(feed)

    assert len(articles) == 1
    assert articles[0]["tags"] == ["frontier-ai", "ai-security"]


def test_rss_feed_crawler_rejects_empty_malformed_feed() -> None:
    """A malformed feed with no entries should fail explicitly."""

    crawler = RSSFeedCrawler(_source_config())

    with pytest.raises(CrawlerError):
        crawler.parse_feed("<rss><channel><item></channel></rss>")


def _source_config() -> SourceConfig:
    """Return one synthetic RSS source config."""

    return SourceConfig(
        slug="example-rss",
        name="Example RSS",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="rss",
        enabled=True,
        crawler=None,
        aliases=("example",),
        urls={"rss": "https://example.com/rss.xml", "homepage": "https://example.com/news"},
        filters={},
        tags=("frontier-ai", "ai-security"),
    )
