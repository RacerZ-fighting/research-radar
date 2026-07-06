"""Tests for the DEF CON talk crawler."""

from __future__ import annotations

import pytest

from src.crawlers.defcon_talk_crawler import DefconTalkCrawler
from src.exceptions import CrawlerError


def test_defcon_talk_crawler_parses_speaker_page_talks() -> None:
    """DEF CON speaker pages should produce talk-level industry items."""

    crawler = DefconTalkCrawler(conference_number=33)
    html = """
    <article class="talk" id="content_123">
      <h3 class="talk-title">Remote code execution via MIDI messages</h3>
      <p class="time-room">
        Friday at 10:00 in LVCC - Track 2
        <br>
        45 minutes | Demo, Exploit
      </p>
      <h4 class="speaker">
        Anna portasynthinca3 Antonenko
        <span class="speaker-title">Independent Researcher</span>
      </h4>
      <p class="abstract">
        This talk reverse engineers a MIDI implementation and shows how crafted messages trigger remote code execution.
      </p>
    </article>
    """

    talks = crawler.parse_speakers_page(html)

    assert len(talks) == 1
    assert talks[0]["title"] == "Remote code execution via MIDI messages"
    assert talks[0]["authors"] == ["Anna portasynthinca3 Antonenko"]
    assert talks[0]["conference"] == "DEF CON 33"
    assert talks[0]["track"] == "Track 2"
    assert talks[0]["scheduled_at"] == "Friday at 10:00 in LVCC - Track 2 45 minutes | Demo, Exploit"
    assert "crafted messages trigger remote code execution" in talks[0]["excerpt"]
    assert talks[0]["article_url"] == "https://defcon.org/html/defcon-33/dc-33-speakers.html#content_123"
    assert talks[0]["tags"] == [
        "industry-conference",
        "security-conference",
        "talks",
        "defcon",
        "defcon-33",
        "track-2",
    ]


def test_defcon_talk_crawler_falls_back_when_current_year_page_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default crawl should try the current DEF CON page, then the latest available fallback."""

    crawler = DefconTalkCrawler()
    html = """
    <article class="talk" id="content_456">
      <h3 class="talk-title">Supply chain compromise from abandoned buckets</h3>
      <p class="abstract">This talk studies real-world supply chain compromise paths.</p>
    </article>
    """
    attempted_urls: list[str] = []

    monkeypatch.setattr(crawler, "_candidate_conference_numbers", lambda: [34, 33])

    def fake_fetch_url(url: str) -> str:
        attempted_urls.append(url)
        if "defcon-34" in url:
            raise CrawlerError("404")
        return html

    monkeypatch.setattr(crawler, "fetch_url", fake_fetch_url)

    talks = crawler.fetch_articles(limit=5)

    assert attempted_urls == [
        "https://defcon.org/html/defcon-34/dc-34-speakers.html",
        "https://defcon.org/html/defcon-33/dc-33-speakers.html",
    ]
    assert crawler.conference_number == 33
    assert talks[0]["conference"] == "DEF CON 33"
    assert "defcon-33" in talks[0]["tags"]
