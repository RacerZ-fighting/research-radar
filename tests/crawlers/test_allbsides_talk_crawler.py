"""Tests for the AllBSides talk crawler."""

from __future__ import annotations

from src.config.sources import SourceConfig
from src.crawlers.allbsides_talk_crawler import AllBsidesTalkCrawler
from src.models.enums import SourceType


class _JsonResponse:
    """Minimal JSON response stub."""

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_allbsides_talk_crawler_maps_talk_recordings(monkeypatch) -> None:
    """AllBSides talks should produce conference-topic raw items."""

    crawler = AllBsidesTalkCrawler(_source_config())
    payload = [
        {
            "id": 161068,
            "video_id": "LZnBhQBJ7KU",
            "url": "https://www.youtube.com/watch?v=LZnBhQBJ7KU",
            "raw_title": "BSidesSF 2026 - Opening Remarks (Sunday) (Reed Loden)",
            "curated_title": "Opening Remarks (Sunday)",
            "raw_description": "Opening Remarks (Sunday)\n\nReed Loden\n\nWelcome to Day Two.",
            "curated_description": "Reed Loden welcomes participants to Day Two of BSidesSF 2026.",
            "published_at": "2026-05-12T01:39:17Z",
            "event_name": "BSidesSF",
            "event_year": 2026,
            "speakers": [{"name": "Reed Loden"}],
            "tags": [{"name": "Community", "slug": "community"}, {"name": "Talk", "slug": "talk"}],
        }
    ]
    requested_urls: list[str] = []

    def fake_fetch_response(url: str) -> _JsonResponse:
        requested_urls.append(url)
        return _JsonResponse(payload)

    monkeypatch.setattr(crawler, "fetch_response", fake_fetch_response)

    talks = crawler.fetch_articles(limit=5)

    assert requested_urls == ["https://api.allbsides.com/v1/talks?organizer=bsidessf&year=2026&limit=5"]
    assert talks == [
        {
            "title": "Opening Remarks (Sunday)",
            "authors": ["Reed Loden"],
            "published_at": "2026-05-12T01:39:17Z",
            "source_url": "https://api.allbsides.com/v1/talks?organizer=bsidessf&year=2026",
            "article_url": "https://www.youtube.com/watch?v=LZnBhQBJ7KU",
            "excerpt": "Reed Loden welcomes participants to Day Two of BSidesSF 2026.",
            "conference": "BSidesSF 2026",
            "tags": [
                "industry-conference",
                "security-conference",
                "talks",
                "allbsides",
                "bsidessf",
                "bsidessf-2026",
                "community",
                "talk",
            ],
            "source_type": "blogs",
            "source_slug": "bsidessf",
        }
    ]


def test_allbsides_talk_crawler_cleans_recording_title_wrappers() -> None:
    """Raw YouTube recording titles should not leak conference and speaker wrappers."""

    crawler = AllBsidesTalkCrawler(_source_config())
    item = crawler._talk_to_item(
        {
            "raw_title": "BSidesSF 2026 - More Role Models in AppSec: How to Get It Right (Alexandra Charikova)",
            "raw_description": "AppSec lessons.",
            "published_at": "2026-05-12T01:38:49Z",
            "event_name": "BSidesSF",
            "event_year": 2026,
            "speakers": [{"name": "Alexandra Charikova"}],
            "tags": [],
            "url": "https://www.youtube.com/watch?v=4T_bDqeC96M",
        }
    )

    assert item is not None
    assert item["title"] == "More Role Models in AppSec: How to Get It Right"


def _source_config() -> SourceConfig:
    """Return a BSidesSF AllBSides source config."""

    return SourceConfig(
        slug="bsidessf",
        name="BSidesSF",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="crawler",
        enabled=True,
        crawler="allbsides",
        aliases=("bsides sf",),
        urls={
            "homepage": "https://bsidessf.org/",
            "fallback_api": "https://api.allbsides.com/v1/talks?organizer=bsidessf&year=2026",
        },
        filters={},
        params={"organizer_slug": "bsidessf", "event_year": 2026, "event_slug": "bsidessf-2026"},
        tags=("industry-conference", "security-conference", "talks"),
    )
