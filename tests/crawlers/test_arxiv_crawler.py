"""Tests for the arXiv crawler."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from src.crawlers.arxiv_crawler import ArxivCrawler


def test_arxiv_crawler_queries_categories_separately(monkeypatch) -> None:
    """Multi-category arXiv fetches should avoid one large OR query."""

    seen_queries: list[str] = []

    def fake_fetch_url(url: str) -> str:
        query = parse_qs(urlparse(url).query)["search_query"][0]
        seen_queries.append(query)
        category = query.removeprefix("cat:")
        return _atom_feed(
            [
                {
                    "id": f"2607.{len(seen_queries):05d}",
                    "title": f"{category} paper",
                    "category": category,
                }
            ]
        )

    monkeypatch.setattr("src.crawlers.arxiv_crawler.time.sleep", lambda _: None)
    crawler = ArxivCrawler(categories=["cs.CR", "cs.SE", "cs.PL"], max_results=6)
    monkeypatch.setattr(crawler, "fetch_url", fake_fetch_url)

    papers = crawler.fetch_papers([2026])

    assert seen_queries == ["cat:cs.CR", "cat:cs.SE", "cat:cs.PL"]
    assert all(" OR " not in query for query in seen_queries)
    assert [paper["categories"][0] for paper in papers] == ["cs.CR", "cs.SE", "cs.PL"]


def test_arxiv_crawler_deduplicates_cross_listed_papers(monkeypatch) -> None:
    """Cross-listed arXiv papers should not be returned multiple times."""

    def fake_fetch_url(url: str) -> str:
        query = parse_qs(urlparse(url).query)["search_query"][0]
        category = query.removeprefix("cat:")
        return _atom_feed(
            [
                {
                    "id": "2607.00042",
                    "title": "Cross listed security paper",
                    "category": category,
                }
            ]
        )

    monkeypatch.setattr("src.crawlers.arxiv_crawler.time.sleep", lambda _: None)
    crawler = ArxivCrawler(categories=["cs.CR", "cs.SE"], max_results=4)
    monkeypatch.setattr(crawler, "fetch_url", fake_fetch_url)

    papers = crawler.fetch_papers([2026])

    assert len(papers) == 1
    assert papers[0]["arxiv_id"] == "2607.00042"


def _atom_feed(entries: list[dict[str, str]]) -> str:
    """Return a minimal arXiv Atom feed for tests."""

    rendered_entries = "\n".join(_entry(**entry) for entry in entries)
    return f"""
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      {rendered_entries}
    </feed>
    """


def _entry(*, id: str, title: str, category: str) -> str:
    """Return one minimal arXiv entry."""

    return f"""
    <entry>
      <id>https://arxiv.org/abs/{id}v1</id>
      <title>{title}</title>
      <summary>Example abstract for {title}.</summary>
      <published>2026-07-02T00:00:00Z</published>
      <author><name>Alice Example</name></author>
      <arxiv:primary_category term="{category}"/>
      <category term="{category}"/>
      <link title="pdf" href="https://arxiv.org/pdf/{id}"/>
    </entry>
    """
