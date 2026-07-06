"""Tests for the official Black Hat schedule crawler."""

from __future__ import annotations

import pytest

from src.config.sources import SourceConfig
from src.crawlers.blackhat_schedule_crawler import BlackHatScheduleCrawler
from src.exceptions import CrawlerError
from src.models.enums import SourceType


def test_blackhat_schedule_crawler_parses_official_schedule_html() -> None:
    """Black Hat schedule pages should produce conference-topic raw items."""

    crawler = BlackHatScheduleCrawler(_source_config())
    html = """
    <html>
      <body>
        <div>All times are Singapore Time (GMT/UTC +8h)</div>
        <div>ALL SESSIONS</div>
        <h3>THURSDAY | 8:00AM</h3>
        <a href="/asia-26/briefings/schedule/index.html#coffee">Briefings Coffee &amp; Tea Break</a>
        <div>Track:</div>
        <div>Location: Orchid Main Ballroom</div>
        <h3>THURSDAY | 9:15AM</h3>
        <a href="session/privacy-captain.html">Keynote: Privacy is the Captain. Security is the Practice.</a>
        <div>Speaker: Violet Blue</div>
        <div>Track: Keynote</div>
        <div>Format: 60-Minute Keynote</div>
        <div>Location: Roselle Junior Ballroom 4610/4710</div>
        <h3>THURSDAY | 10:20AM</h3>
        <a href="session/airsnitch.html">AirSnitch: Breaking Client Isolation in Wi-Fi Networks</a>
        <div>
          Speaker: Mathy Vanhoef, Speaker: Zhiyun Qian,
          Contributor: Xin'an Zhou, Contributor: Juefei Pu
        </div>
        <div>Track: Network Security, Wireless</div>
        <div>Format: 40-Minute Briefings</div>
        <div>Location: Roselle Junior Ballroom 4711</div>
        <h3>THURSDAY | 11:15AM</h3>
        <a href="session/overflow.html">Keynote Overflow Room</a>
      </body>
    </html>
    """

    articles = crawler.parse_schedule_html(html, limit=10)

    assert [item["title"] for item in articles] == [
        "Keynote: Privacy is the Captain. Security is the Practice.",
        "AirSnitch: Breaking Client Isolation in Wi-Fi Networks",
    ]
    airsnitch = articles[1]
    assert airsnitch["authors"] == ["Mathy Vanhoef", "Zhiyun Qian", "Xin'an Zhou", "Juefei Pu"]
    assert airsnitch["published_at"] == "2026-04-23"
    assert airsnitch["article_url"] == "https://blackhat.com/asia-26/briefings/schedule/session/airsnitch.html"
    assert airsnitch["conference"] == "Black Hat Asia 2026"
    assert airsnitch["source_slug"] == "blackhat-asia"
    assert "official-schedule" in airsnitch["tags"]
    assert "Network Security" in airsnitch["tags"]
    assert "Wireless" in airsnitch["tags"]
    assert "Thursday 10:20AM" in airsnitch["excerpt"]


def test_blackhat_schedule_crawler_parses_official_sessions_json() -> None:
    """Official sessions.json should produce full talk-level raw items."""

    crawler = BlackHatScheduleCrawler(_source_config())
    payload = {
        "sections": [
            {"label": "Thursday | 8:00am", "date": "Thursday", "sessions": [{"session_id": 52456}]},
            {"label": "Thursday | 10:20am", "date": "Thursday", "sessions": [{"session_id": 51283}]},
            {"label": "Thursday | 11:00am", "date": "Thursday", "sessions": [{"session_id": 25000}]},
        ],
        "sessions": {
            "52456": {
                "id": 52456,
                "title": "Briefings Coffee &amp; Tea Break",
                "iso_start_date": "2026-04-23T08:00:00+08:00",
            },
            "25000": {
                "id": 25000,
                "title": "Briefings Refreshment Break",
                "iso_start_date": "2026-04-23T11:00:00+08:00",
            },
            "51283": {
                "id": 51283,
                "title": "AirSnitch: Breaking Client Isolation in Wi-Fi Networks",
                "track_1": "Network Security",
                "track_2": "Cryptography",
                "format": "Briefings",
                "duration": "40-Minute",
                "room": "Roselle Junior Ballroom 4610/4710",
                "iso_start_date": "2026-04-23T10:20:00+08:00",
                "time_display": "Thursday, April 23 | 10:20am-11:00am",
                "description": "<p>Bypasses Wi-Fi client isolation in WPA2/3 networks.</p>",
                "speakers": [
                    {"person_id": 34415, "role": "Speaker"},
                    {"person_id": 52697, "role": "Speaker"},
                    {"person_id": 45170, "role": "Contributor"},
                ],
            },
        },
        "speakers": {
            "34415": {"first_name": "Mathy", "last_name": "Vanhoef"},
            "52697": {"first_name": "Zhiyun", "last_name": "Qian"},
            "45170": {"first_name": "Xin'an", "last_name": "Zhou"},
        },
    }

    articles = crawler.parse_schedule_payload(payload, limit=10)

    assert len(articles) == 1
    item = articles[0]
    assert item["title"] == "AirSnitch: Breaking Client Isolation in Wi-Fi Networks"
    assert item["authors"] == ["Mathy Vanhoef", "Zhiyun Qian", "Xin'an Zhou"]
    assert item["published_at"] == "2026-04-23"
    assert item["article_url"] == "https://blackhat.com/asia-26/briefings/schedule/index.html#session/51283"
    assert "Bypasses Wi-Fi client isolation" in item["excerpt"]
    assert "Network Security" in item["tags"]
    assert "Cryptography" in item["tags"]
    assert "40-Minute Briefings" in item["tags"]


def test_blackhat_schedule_crawler_extracts_sessions_json_url() -> None:
    """The official schedule shell should point to sessions.json."""

    crawler = BlackHatScheduleCrawler(_source_config())

    assert crawler._data_url_from_html("<script>var dataUrl = 'sessions.json';</script>") == "sessions.json"


def test_blackhat_schedule_crawler_uses_configured_max_results() -> None:
    """Schedule crawls should not be capped by the generic blog limit."""

    crawler = BlackHatScheduleCrawler(_source_config())

    assert crawler._effective_limit(20) == 80


def test_blackhat_schedule_crawler_fails_fast_on_cloudflare() -> None:
    """Cloudflare challenge pages should produce a clear operator action."""

    crawler = BlackHatScheduleCrawler(_source_config())

    with pytest.raises(CrawlerError, match="BLACKHAT_COOKIE"):
        crawler._raise_if_blocked("<title>Just a moment...</title>Please enable JavaScript and cookies")


def test_blackhat_schedule_crawler_uses_impersonation_on_http_403(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP access blocks should retry through the browser-like fallback."""

    crawler = BlackHatScheduleCrawler(_source_config())
    attempted: list[tuple[str, int]] = []

    class _Response:
        status_code = 403
        text = "Forbidden"

        def raise_for_status(self) -> None:
            raise AssertionError("raise_for_status should not be reached for 403")

    monkeypatch.setattr(crawler.session, "get", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(
        crawler,
        "_fetch_with_browser_impersonation",
        lambda url, status: attempted.append((url, status)) or "ok",
    )

    assert crawler._fetch_schedule_html() == "ok"
    assert attempted == [("https://blackhat.com/asia-26/briefings/schedule/index.html", 403)]


def test_blackhat_schedule_crawler_fetch_applies_scoped_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """A manually supplied scoped cookie should be attached to the official request."""

    crawler = BlackHatScheduleCrawler(_source_config())
    monkeypatch.setenv("BLACKHAT_COOKIE", "cf_clearance=test-token")

    crawler._apply_cookie()

    assert crawler.session.headers["Cookie"] == "cf_clearance=test-token"


def _source_config() -> SourceConfig:
    """Return a Black Hat Asia official schedule source config."""

    return SourceConfig(
        slug="blackhat-asia",
        name="Black Hat Asia",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="crawler",
        enabled=True,
        crawler="blackhat-schedule",
        aliases=("blackhat asia",),
        urls={
            "homepage": "https://www.blackhat.com/asia-26/",
            "schedule": "https://blackhat.com/asia-26/briefings/schedule/index.html",
        },
        filters={},
        params={
            "event_label": "Black Hat Asia 2026",
            "target_urls": ["https://blackhat.com/asia-26/briefings/schedule/index.html"],
            "schedule_dates": {"THURSDAY": "2026-04-23", "FRIDAY": "2026-04-24"},
            "cookie_env": "BLACKHAT_COOKIE",
            "max_results": 80,
        },
        tags=("industry-conference", "security-conference", "talks"),
    )
