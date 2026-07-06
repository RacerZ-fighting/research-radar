"""Tests for the official RSAC agenda crawler."""

from __future__ import annotations

from typing import Any

from src.config.sources import SourceConfig
from src.crawlers.rsac_agenda_crawler import RSACAgendaCrawler
from src.models.enums import SourceType


def test_rsac_agenda_crawler_parses_section_list_payload() -> None:
    """RainFocus sectionList responses should become conference-topic raw items."""

    crawler = RSACAgendaCrawler(_rsac_source_config())
    payload = {
        "responseCode": "0",
        "totalSearchItems": 1,
        "sectionList": [
            {
                "total": 1,
                "items": [
                    _session_item(
                        title="From Prompt to Pwn: Exploiting Web Apps with LLM & OWASP Techniques",
                        code="LAB2-M01",
                    )
                ],
            }
        ],
    }

    items, total = crawler._items_from_payload(payload)
    article = crawler._build_item(items[0])

    assert total == 1
    assert article is not None
    assert article["title"] == "From Prompt to Pwn: Exploiting Web Apps with LLM & OWASP Techniques"
    assert article["authors"] == ["Alice Researcher", "Bob Operator"]
    assert article["published_at"] == "2026-03-23"
    assert article["source_url"] == "https://path.rsaconference.com/flow/rsac/us26/FullAgenda/page/catalog"
    assert "official-rainfocus-agenda" in article["tags"]
    assert "Hackers & Threats" in article["tags"]
    assert "Speakers: Alice Researcher, Bob Operator" in article["excerpt"]


def test_rsac_agenda_crawler_parses_paginated_top_level_payload() -> None:
    """RainFocus from-offset responses use top-level items instead of sectionList."""

    crawler = RSACAgendaCrawler(_rsac_source_config())
    payload = {
        "responseCode": "0",
        "total": 661,
        "from": 50,
        "items": [_session_item(title="Making Security Data Actionable", code="PART1-M03")],
    }

    items, total = crawler._items_from_payload(payload)

    assert total == 661
    assert len(items) == 1
    assert items[0]["code"] == "PART1-M03"


def test_rsac_agenda_crawler_filters_non_topic_sessions() -> None:
    """Networking and invite-only agenda entries should not enter the industry lane."""

    crawler = RSACAgendaCrawler(_rsac_source_config())

    assert crawler._build_item(_session_item(title="All Access Continental Breakfast", fmt="Networking")) is None
    assert crawler._build_item(_session_item(title="Cyber Leaders Forum - Invite Only", fmt="Invite Only")) is None
    assert (
        crawler._build_item(
            _session_item(
                title="Advancing Cyber Defense in the Era of AI Driven Threats",
                fmt="Track Session",
                tracks=["Business Perspectives", "Intersection of AI & Security"],
                classification="General",
            )
        )
        is None
    )


def test_rsac_agenda_crawler_uses_configured_limit() -> None:
    """Configured max_results should override the generic CLI blog limit."""

    crawler = RSACAgendaCrawler(_rsac_source_config())

    assert crawler._effective_limit(20) == 160


def _session_item(
    *,
    title: str,
    code: str = "SEC-M01",
    fmt: str = "Learning Lab",
    tracks: list[str] | None = None,
    classification: str = "Intermediate—Technical",
) -> dict[str, Any]:
    track_values = tracks or ["Hackers & Threats", "Intersection of AI & Security"]
    return {
        "sessionID": f"session-{code}",
        "sessionTimeID": f"time-{code}",
        "code": code,
        "title": title,
        "published": 1.0,
        "testRecord": False,
        "abstract": "<p>This session studies practical exploitation and defensive validation.</p>",
        "times": [
            {
                "date": "2026-03-23",
                "dateFormatted": "Monday, March 23",
                "startTimeFormatted": "10:50 AM",
                "endTimeFormatted": "11:40 AM",
                "room": "Moscone West",
            }
        ],
        "participants": [
            {"fullName": "Alice Researcher", "displayorder": 0.0},
            {"preferredFullName": "Bob Operator", "displayorder": 1.0},
        ],
        "attributevalues": [
            {"attribute": "Type/Format", "value": fmt},
            *[{"attribute": "Topic/Track", "value": track} for track in track_values],
            {"attribute": "Session Classification", "value": classification},
        ],
    }


def _rsac_source_config() -> SourceConfig:
    return SourceConfig(
        slug="rsac-fixture",
        name="RSA Conference",
        source_type=SourceType.BLOGS,
        tier="t3-research-blog",
        track="industry",
        adapter="crawler",
        crawler="rsac-agenda",
        enabled=False,
        aliases=("rsac", "rsa conference"),
        urls={"agenda": "https://path.rsaconference.com/flow/rsac/us26/FullAgenda/page/catalog"},
        filters={},
        tags=("industry-conference", "security-conference", "talks"),
        params={
            "event_label": "RSAC 2026",
            "agenda_url": "https://path.rsaconference.com/flow/rsac/us26/FullAgenda/page/catalog",
            "sessions_api_url": "https://events.rsaconference.com/api/sessions",
            "widget_id": "fixture-widget",
            "api_profile_id": "fixture-profile",
            "session_catalog_tab": "fixture-tab",
            "max_results": 160,
        },
    )
