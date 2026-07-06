"""DEF CON conference talk crawler."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.crawlers.base import BlogCrawler, clean_text
from src.exceptions import CrawlerError
from src.timezone import app_today

logger = logging.getLogger(__name__)


class DefconTalkCrawler(BlogCrawler):
    """Fetch DEF CON speaker/talk pages as industry conference topics."""

    source_name = "DEF CON"
    source_slug = "defcon"

    def __init__(
        self,
        *,
        conference_number: int | None = None,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize the crawler for the latest public DEF CON speaker page."""

        super().__init__(timeout=timeout, max_retries=max_retries)
        self._explicit_conference_number = conference_number
        self.conference_number = conference_number or self._current_conference_number()
        self.speakers_url = self._speakers_url(self.conference_number)

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch DEF CON talks from the public speaker page."""

        errors: list[str] = []
        for conference_number in self._candidate_conference_numbers():
            self.conference_number = conference_number
            self.speakers_url = self._speakers_url(conference_number)
            try:
                html = self.fetch_url(self.speakers_url)
            except CrawlerError as exc:
                errors.append(f"DEF CON {conference_number}: {exc}")
                if self._explicit_conference_number is not None:
                    raise
                logger.info("DEF CON %s speakers page unavailable; trying fallback", conference_number)
                continue

            talks = self.parse_speakers_page(html, limit=limit)
            if talks:
                return talks

            errors.append(f"DEF CON {conference_number}: no talk nodes found")
            if self._explicit_conference_number is not None:
                break
            logger.info("DEF CON %s speakers page had no talk nodes; trying fallback", conference_number)

        detail = "; ".join(errors) if errors else "no candidate pages were configured"
        raise CrawlerError(f"Failed to fetch DEF CON talks: {detail}")

    def parse_speakers_page(self, html: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse a DEF CON speakers page into raw blog-like talk items."""

        soup = BeautifulSoup(html, "html.parser")
        talks: list[dict[str, Any]] = []
        for node in soup.select("article.talk"):
            talk = self._talk_node_to_item(node)
            if talk is None:
                continue
            talks.append(talk)
            if len(talks) >= limit:
                break
        return talks

    def _talk_node_to_item(self, node: Tag) -> dict[str, Any] | None:
        """Convert one DEF CON talk node into a raw item."""

        title = clean_text(self._text(node, ".talk-title"))
        if not title:
            return None

        speaker_text = clean_text(self._text(node, ".speaker"))
        speaker_title = clean_text(self._text(node, ".speaker-title"))
        speakers = self._speaker_names(speaker_text, speaker_title)
        schedule_text = clean_text(self._text(node, ".time-room"))
        abstract = clean_text(self._text(node, ".abstract"))
        if not abstract:
            abstract = clean_text(self._text(node, ".speaker-bio"))
        article_url = self._talk_url(node)

        tags = [
            "industry-conference",
            "security-conference",
            "talks",
            "defcon",
            f"defcon-{self.conference_number}",
        ]
        track = self._extract_track(schedule_text)
        if track:
            tags.append(track.lower().replace(" ", "-"))

        return {
            "title": title,
            "authors": speakers,
            "published_at": None,
            "source_url": self.speakers_url,
            "article_url": article_url,
            "excerpt": abstract,
            "conference": f"DEF CON {self.conference_number}",
            "track": track,
            "scheduled_at": schedule_text,
            "tags": tags,
            "source_type": "blogs",
        }

    def _talk_url(self, node: Tag) -> str:
        """Return a stable URL for one talk node."""

        node_id = clean_text(str(node.get("id") or ""))
        if node_id:
            return f"{self.speakers_url}#{node_id}"
        title = clean_text(self._text(node, ".talk-title")).lower()
        slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-")
        return f"{self.speakers_url}#{slug}"

    def _speaker_names(self, speaker_text: str, speaker_title: str) -> list[str]:
        """Return speaker names without affiliation text."""

        cleaned = speaker_text
        if speaker_title and cleaned.endswith(speaker_title):
            cleaned = cleaned[: -len(speaker_title)]
        names = [name for name in re.split(r"\s{2,}|,\s+|\sand\s", clean_text(cleaned)) if clean_text(name)]
        return [clean_text(name) for name in names]

    def _extract_track(self, schedule_text: str) -> str | None:
        """Extract a track label from schedule text."""

        match = re.search(r"\bTrack\s+\d+\b", schedule_text, flags=re.IGNORECASE)
        if not match:
            return None
        return clean_text(match.group(0)).title()

    def _text(self, node: Tag, selector: str) -> str:
        """Return text for a child selector."""

        child = node.select_one(selector)
        if child is None:
            return ""
        return child.get_text(" ", strip=True)

    def _candidate_conference_numbers(self) -> list[int]:
        """Return DEF CON numbers to try in order."""

        if self._explicit_conference_number is not None:
            return [self._explicit_conference_number]

        current = self._current_conference_number()
        fallback = max(1, current - 1)
        return [current] if current == fallback else [current, fallback]

    def _current_conference_number(self) -> int:
        """Return the DEF CON number for the current calendar year."""

        year = app_today().year
        # DEF CON 33 corresponds to 2025, so 2026 maps to DEF CON 34.
        return max(1, year - 1992)

    def _speakers_url(self, conference_number: int) -> str:
        """Return the public speaker page URL for one DEF CON number."""

        return f"https://defcon.org/html/defcon-{conference_number}/dc-{conference_number}-speakers.html"
