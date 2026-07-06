"""Tests for the browser-use conference crawler."""

from __future__ import annotations

import asyncio

import pytest

from src.config.sources import SourceConfig
from src.crawlers.browser_use_conference_crawler import BrowserUseConferenceCrawler
from src.exceptions import CrawlerError
from src.models.enums import SourceType


def test_browser_use_conference_crawler_parses_agent_json() -> None:
    """Browser-use JSON output should become conference-topic raw items."""

    captured_tasks: list[str] = []

    def runner(task: str) -> str:
        captured_tasks.append(task)
        return """
        ```json
        {
          "items": [
            {
              "title": "Breaking AI Agent Sandboxes",
              "authors": ["Ada Example", "Grace Example"],
              "date": "2026-08-05",
              "article_url": "https://blackhat.com/us-26/briefings/schedule/#agent-sandboxes",
              "source_url": "https://blackhat.com/us-26/briefings/schedule/",
              "excerpt": "A technical session about escaping AI coding agent sandboxes.",
              "conference": "Black Hat USA 2026",
              "tags": ["ai-agents", "sandbox-escape"]
            }
          ]
        }
        ```
        """

    crawler = BrowserUseConferenceCrawler(_source_config(), runner=runner)
    articles = crawler.fetch_articles(limit=5)

    assert len(articles) == 1
    assert "Black Hat USA 2026" in captured_tasks[0]
    assert "https://blackhat.com/us-26/briefings/schedule/" in captured_tasks[0]
    assert articles[0] == {
        "title": "Breaking AI Agent Sandboxes",
        "authors": ["Ada Example", "Grace Example"],
        "published_at": "2026-08-05",
        "source_url": "https://blackhat.com/us-26/briefings/schedule/",
        "article_url": "https://blackhat.com/us-26/briefings/schedule/#agent-sandboxes",
        "excerpt": "A technical session about escaping AI coding agent sandboxes.",
        "conference": "Black Hat USA 2026",
        "tags": [
            "industry-conference",
            "security-conference",
            "talks",
            "blackhat-usa",
            "black-hat-usa-2026",
            "ai-agents",
            "sandbox-escape",
        ],
        "source_type": "blogs",
    }


def test_browser_use_conference_crawler_prompt_avoids_search_and_captcha() -> None:
    """The agent prompt should fail closed on bot checks instead of chasing CAPTCHA loops."""

    crawler = BrowserUseConferenceCrawler(_source_config(), runner=lambda _: '{"items": []}')
    task = crawler._build_task(["https://blackhat.com/us-26/briefings/schedule/"], limit=5)

    assert "Do not use search engines" in task
    assert "Do not attempt to solve CAPTCHA" in task
    assert '"items": []' in task


def test_browser_use_conference_crawler_deduplicates_and_falls_back_to_source_url() -> None:
    """Missing item URLs should fall back to the schedule URL and duplicates should collapse."""

    def runner(_: str) -> str:
        return {
            "items": [
                {"title": "One Talk", "speakers": "Alice and Bob", "description": "First copy"},
                {"title": "One Talk", "speakers": "Alice and Bob", "description": "Duplicate copy"},
            ]
        }.__repr__().replace("'", '"')

    crawler = BrowserUseConferenceCrawler(_source_config(), runner=runner)
    articles = crawler.fetch_articles(limit=5)

    assert len(articles) == 1
    assert articles[0]["article_url"] == "https://blackhat.com/us-26/briefings/schedule/"
    assert articles[0]["authors"] == ["Alice", "Bob"]


def test_browser_use_conference_crawler_rejects_responses_only_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """browser-use should fail fast when only a Responses API endpoint is configured."""

    monkeypatch.delenv("BROWSER_USE_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://example.test/v1/responses")
    crawler = BrowserUseConferenceCrawler(_source_config())

    with pytest.raises(CrawlerError, match="chat/completions"):
        asyncio.run(crawler._run_browser_use_async("extract one item"))


def test_browser_use_conference_crawler_prefers_browser_use_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The browser-use API key should be read independently from the main OpenAI key."""

    monkeypatch.setenv("BROWSER_USE_API_KEY", "browser-use-key")
    monkeypatch.setenv("OPENAI_API_KEY", "main-openai-key")
    crawler = BrowserUseConferenceCrawler(_source_config())

    assert crawler._browser_use_api_key() == "browser-use-key"


def test_browser_use_conference_crawler_defaults_dashscope_to_qwen_vl_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DashScope browser-use runs should default to the tested Qwen vision model."""

    monkeypatch.delenv("BROWSER_USE_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL_STANDARD", "gpt-5.4")
    crawler = BrowserUseConferenceCrawler(_source_config())

    assert crawler._browser_use_model("https://dashscope.aliyuncs.com/compatible-mode/v1") == "qwen-vl-max"


def test_browser_use_conference_crawler_does_not_reuse_main_key_across_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DashScope browser-use endpoint should require its own API key."""

    monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
    monkeypatch.setenv("BROWSER_USE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://example.test/v1/responses")
    monkeypatch.setenv("OPENAI_API_KEY", "main-openai-key")
    crawler = BrowserUseConferenceCrawler(_source_config())

    assert crawler._browser_use_api_key() is None


def _source_config() -> SourceConfig:
    """Return one synthetic browser-use conference source config."""

    return SourceConfig(
        slug="blackhat-usa",
        name="Black Hat USA",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="crawler",
        enabled=True,
        crawler="browser-use-conference",
        aliases=("black hat usa",),
        urls={
            "homepage": "https://blackhat.com/us-26/",
            "schedule": "https://blackhat.com/us-26/briefings/schedule/",
        },
        filters={},
        params={
            "event_label": "Black Hat USA 2026",
            "target_urls": ["https://blackhat.com/us-26/briefings/schedule/"],
        },
        tags=("industry-conference", "security-conference", "talks"),
    )
