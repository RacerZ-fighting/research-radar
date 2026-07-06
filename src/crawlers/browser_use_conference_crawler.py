"""Browser-use backed crawler for Cloudflare-heavy conference agenda pages."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text, split_authors
from src.exceptions import CrawlerError

BrowserUseRunner = Callable[[str], str]


class BrowserUseConferenceCrawler(BlogCrawler):
    """Use browser-use to extract conference sessions into blog-like raw items."""

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        runner: BrowserUseRunner | None = None,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type.value != "blogs":
            raise ValueError("BrowserUseConferenceCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.runner = runner

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Run browser-use and return normalized conference topic records."""

        target_urls = self._target_urls()
        if not target_urls:
            raise CrawlerError(f"Browser-use source requires at least one target URL: {self.source_slug}")

        task = self._build_task(target_urls, limit=limit)
        raw_output = self.runner(task) if self.runner else self._run_browser_use(task)
        return self.parse_browser_use_output(raw_output, limit=limit)

    def parse_browser_use_output(self, raw_output: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse browser-use JSON output into normalized raw article dictionaries."""

        payload = self._decode_json_payload(raw_output)
        raw_items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(raw_items, list):
            raise CrawlerError(f"Browser-use output for {self.source_slug} did not contain an items list")

        articles: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            article = self._normalize_item(raw_item)
            if article is None:
                continue
            dedupe_key = article["article_url"] or article["title"].lower()
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            articles.append(article)
            if len(articles) >= limit:
                break
        return articles

    def _normalize_item(self, raw_item: dict[str, Any]) -> dict[str, Any] | None:
        """Convert one agent-extracted item into the raw blog-like item shape."""

        title = clean_text(
            str(
                raw_item.get("title")
                or raw_item.get("session_title")
                or raw_item.get("talk_title")
                or raw_item.get("name")
                or ""
            )
        )
        if not title:
            return None

        article_url = clean_text(str(raw_item.get("article_url") or raw_item.get("url") or ""))
        source_url = clean_text(str(raw_item.get("source_url") or "")) or self._target_urls()[0]
        if not article_url:
            article_url = source_url

        excerpt = clean_text(
            str(
                raw_item.get("excerpt")
                or raw_item.get("abstract")
                or raw_item.get("description")
                or raw_item.get("summary")
                or ""
            )
        )
        authors = self._normalize_authors(raw_item.get("authors") or raw_item.get("speakers"))
        published_at = self._normalize_date(raw_item.get("published_at") or raw_item.get("date"))
        conference = clean_text(str(raw_item.get("conference") or self.source_config.name))
        tags = self._merge_tags(raw_item.get("tags"), conference)

        return {
            "title": title,
            "authors": authors,
            "published_at": published_at,
            "source_url": source_url,
            "article_url": article_url,
            "excerpt": excerpt or None,
            "conference": conference,
            "tags": tags,
            "source_type": "blogs",
        }

    def _build_task(self, target_urls: list[str], *, limit: int) -> str:
        """Build a deterministic extraction prompt for browser-use."""

        event_label = clean_text(str(self.source_config.params.get("event_label") or self.source_config.name))
        urls_text = "\n".join(f"- {url}" for url in target_urls)
        return f"""
You are extracting cybersecurity conference agenda items for Research Radar.

Conference source: {self.source_config.name}
Event label: {event_label}
Target URLs:
{urls_text}

Open the target pages in a browser. If a page has cookie banners or harmless popups, dismiss them.
Extract up to {limit} technical briefing/session/talk items that describe security research topics.
Ignore navigation links, registration pages, sponsor pages, venue pages, trainings without a concrete topic,
marketing copy, and duplicate schedule entries.
Do not use search engines or third-party fallback pages. Do not attempt to solve CAPTCHA, Cloudflare,
bot checks, login walls, or image challenges. If the target page is blocked or inaccessible, stop and
return this exact JSON: {{"items": []}}.

Return only valid JSON with this exact shape:
{{
  "items": [
    {{
      "title": "session or talk title",
      "authors": ["speaker one", "speaker two"],
      "date": "YYYY-MM-DD or null",
      "article_url": "detail page URL if visible, otherwise schedule URL",
      "source_url": "page URL where this item was found",
      "excerpt": "abstract or short topic description",
      "conference": "{event_label}",
      "tags": ["short-topic-tag"]
    }}
  ]
}}
""".strip()

    def _target_urls(self) -> list[str]:
        """Return configured browser-use target pages."""

        configured = self.source_config.params.get("target_urls")
        if isinstance(configured, list):
            urls = [clean_text(str(url)) for url in configured if clean_text(str(url))]
            if urls:
                return urls

        urls: list[str] = []
        for key in ("schedule", "agenda", "library", "events", "homepage"):
            url = clean_text(self.source_config.urls.get(key))
            if url:
                urls.append(url)
        return list(dict.fromkeys(urls))

    def _run_browser_use(self, task: str) -> str:
        """Run browser-use with the configured OpenAI-compatible model."""

        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._run_browser_use_async(task))
        raise CrawlerError("Browser-use crawler cannot run inside an already active event loop")

    async def _run_browser_use_async(self, task: str) -> str:
        """Async browser-use execution."""

        browser_use_base_url = os.getenv("BROWSER_USE_BASE_URL")
        openai_base_url = os.getenv("OPENAI_BASE_URL")
        if not browser_use_base_url and self._is_responses_only_url(openai_base_url):
            raise CrawlerError(
                "browser-use requires an OpenAI-compatible /v1/chat/completions endpoint. "
                "Current OPENAI_BASE_URL points to a Responses-only endpoint; set BROWSER_USE_BASE_URL separately."
            )
        base_url = browser_use_base_url or self._normalize_openai_base_url(openai_base_url)
        model = self._browser_use_model(base_url)
        headless = os.getenv("BROWSER_USE_HEADLESS", "true").strip().lower() not in {"0", "false", "no"}
        max_failures = int(os.getenv("BROWSER_USE_MAX_FAILURES", "2"))
        max_steps = int(os.getenv("BROWSER_USE_MAX_STEPS", "5"))

        try:
            from browser_use import Agent, Browser, ChatOpenAI
        except ImportError as exc:
            raise CrawlerError(
                "browser-use is not installed. Install project requirements or run: pip install browser-use"
            ) from exc

        llm_kwargs: dict[str, Any] = {"model": model}
        if base_url:
            llm_kwargs["base_url"] = base_url
        api_key = self._browser_use_api_key()
        if not api_key:
            raise CrawlerError(
                "browser-use requires BROWSER_USE_API_KEY for this endpoint. "
                "Set it separately from the main Responses API key."
            )
        if api_key:
            llm_kwargs["api_key"] = api_key
        llm_kwargs["max_retries"] = int(os.getenv("BROWSER_USE_LLM_MAX_RETRIES", "1"))
        llm_kwargs["temperature"] = float(os.getenv("BROWSER_USE_TEMPERATURE", "0"))
        if base_url and "api.openai.com" not in str(base_url):
            llm_kwargs.update(
                {
                    "add_schema_to_system_prompt": True,
                    "dont_force_structured_output": True,
                    "remove_min_items_from_schema": True,
                    "remove_defaults_from_schema": True,
                }
            )
        llm = ChatOpenAI(**llm_kwargs)
        browser = Browser(headless=headless)
        try:
            agent = Agent(task=task, llm=llm, browser=browser, max_failures=max_failures)
            history = await agent.run(max_steps=max_steps)
            result = history.final_result()
        finally:
            close = getattr(browser, "close", None)
            if close:
                maybe_awaitable = close()
                if hasattr(maybe_awaitable, "__await__"):
                    await maybe_awaitable

        if not result:
            raise CrawlerError(f"browser-use returned an empty result for {self.source_slug}")
        return str(result)

    def _decode_json_payload(self, raw_output: str) -> dict[str, Any] | list[Any]:
        """Decode JSON from a raw agent response, including fenced snippets."""

        cleaned = clean_text(raw_output)
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if not match:
            raise CrawlerError(f"Browser-use output for {self.source_slug} was not JSON")
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise CrawlerError(f"Browser-use output for {self.source_slug} was not valid JSON") from exc

    def _normalize_authors(self, raw_authors: Any) -> list[str]:
        """Normalize author/speaker values from agent output."""

        if isinstance(raw_authors, list):
            return [clean_text(str(author)) for author in raw_authors if clean_text(str(author))]
        return split_authors(clean_text(str(raw_authors or "")))

    def _normalize_date(self, value: Any) -> str | None:
        """Normalize a date-like value to YYYY-MM-DD when possible."""

        text = clean_text(str(value or ""))
        if not text or text.lower() == "null":
            return None
        match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        return match.group(0) if match else None

    def _merge_tags(self, raw_tags: Any, conference: str) -> list[str]:
        """Merge configured source tags, source markers, conference label, and agent tags."""

        tags: list[str] = []
        candidates: list[Any] = [*self.source_config.tags, self.source_config.slug, conference]
        if isinstance(raw_tags, list):
            candidates.extend(raw_tags)
        elif raw_tags:
            candidates.append(raw_tags)

        for candidate in candidates:
            tag = self._normalize_tag(str(candidate))
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    def _normalize_tag(self, value: str) -> str:
        """Normalize one tag label."""

        return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")

    def _normalize_openai_base_url(self, value: str | None) -> str | None:
        """Convert a Responses API URL into the OpenAI-compatible API root when possible."""

        if not value:
            return None
        cleaned = value.rstrip("/")
        if cleaned.endswith("/responses"):
            cleaned = cleaned[: -len("/responses")]
        return cleaned

    def _is_responses_only_url(self, value: str | None) -> bool:
        """Return whether the configured URL points directly at the Responses API."""

        return bool(value and value.rstrip("/").endswith("/responses"))

    def _browser_use_model(self, base_url: str | None) -> str:
        """Return the browser-use chat model, with a DashScope-safe default."""

        configured = os.getenv("BROWSER_USE_MODEL")
        if configured:
            return configured
        if base_url and "dashscope.aliyuncs.com" in base_url:
            return "qwen-vl-max"
        return os.getenv("OPENAI_MODEL_STANDARD") or os.getenv("OPENAI_MODEL_FAST") or "gpt-5"

    def _browser_use_api_key(self) -> str | None:
        """Return the API key used by browser-use, separated from the main LLM path when configured."""

        browser_use_key = os.getenv("BROWSER_USE_API_KEY")
        if browser_use_key:
            return browser_use_key

        browser_use_base_url = os.getenv("BROWSER_USE_BASE_URL")
        openai_base_url = os.getenv("OPENAI_BASE_URL")
        if browser_use_base_url and not self._same_host(browser_use_base_url, openai_base_url):
            return None
        return os.getenv("OPENAI_API_KEY")

    def _same_host(self, left: str | None, right: str | None) -> bool:
        """Return whether two base URLs point at the same host."""

        if not left or not right:
            return False
        return urlparse(left).netloc.lower() == urlparse(right).netloc.lower()
