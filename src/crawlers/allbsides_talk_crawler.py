"""AllBSides talk crawler for BSides conference recordings."""

from __future__ import annotations

import re
from typing import Any

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text
from src.exceptions import CrawlerError


class AllBsidesTalkCrawler(BlogCrawler):
    """Fetch talk-level conference items from the public AllBSides API."""

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type.value != "blogs":
            raise ValueError("AllBsidesTalkCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        params = source_config.params
        self.organizer_slug = str(params.get("organizer_slug") or source_config.slug).strip()
        self.event_year = int(params.get("event_year") or 0)
        self.event_slug = str(params.get("event_slug") or "").strip()
        self.api_url = self._api_url(limit=int(params.get("max_results") or 20))

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch and normalize AllBSides talks."""

        response = self.fetch_response(self._api_url(limit=limit))
        try:
            payload = response.json()
        except ValueError as exc:
            raise CrawlerError(f"Invalid AllBSides JSON for {self.source_slug}") from exc
        if not isinstance(payload, list):
            raise CrawlerError(f"Unexpected AllBSides payload for {self.source_slug}")

        talks: list[dict[str, Any]] = []
        for raw_talk in payload:
            if not isinstance(raw_talk, dict):
                continue
            talk = self._talk_to_item(raw_talk)
            if talk is None:
                continue
            talks.append(talk)
            if len(talks) >= limit:
                break
        return talks

    def _api_url(self, *, limit: int) -> str:
        """Return the AllBSides API URL."""

        if self.organizer_slug and self.event_year:
            return (
                "https://api.allbsides.com/v1/talks"
                f"?organizer={self.organizer_slug}&year={self.event_year}&limit={limit}"
            )
        if self.event_slug:
            return f"https://api.allbsides.com/v1/talks/by-event/{self.event_slug}?sort=newest&limit={limit}"
        raise ValueError(f"AllBSides source requires organizer_slug+event_year or event_slug: {self.source_config.slug}")

    def _talk_to_item(self, raw_talk: dict[str, Any]) -> dict[str, Any] | None:
        """Convert one AllBSides talk into the raw blog-like item shape."""

        title = self._title(raw_talk)
        if not title:
            return None

        event_year = int(raw_talk.get("event_year") or self.event_year or 0)
        event_name = clean_text(raw_talk.get("event_name") or self.source_config.name)
        conference = f"{event_name} {event_year}".strip() if event_year else event_name
        authors = self._speaker_names(raw_talk.get("speakers"))
        tags = self._tags(raw_talk, event_year=event_year)
        article_url = clean_text(raw_talk.get("url")) or self._allbsides_talk_url(raw_talk)
        excerpt = clean_text(raw_talk.get("curated_description") or raw_talk.get("raw_description"))

        return {
            "title": title,
            "authors": authors,
            "published_at": clean_text(raw_talk.get("published_at")) or None,
            "source_url": self.source_config.urls.get("fallback_api") or self.api_url,
            "article_url": article_url,
            "excerpt": excerpt,
            "conference": conference,
            "tags": tags,
            "source_type": "blogs",
            "source_slug": self.source_config.slug,
        }

    def _speaker_names(self, raw_speakers: Any) -> list[str]:
        """Return speaker names from AllBSides speaker objects."""

        if not isinstance(raw_speakers, list):
            return []
        names: list[str] = []
        for speaker in raw_speakers:
            if not isinstance(speaker, dict):
                continue
            name = clean_text(speaker.get("name"))
            if name and name not in names:
                names.append(name)
        return names

    def _title(self, raw_talk: dict[str, Any]) -> str:
        """Return a display title without common recording wrappers."""

        curated_title = clean_text(raw_talk.get("curated_title"))
        if curated_title:
            return curated_title

        title = clean_text(raw_talk.get("raw_title"))
        event_name = clean_text(raw_talk.get("event_name") or self.source_config.name)
        event_year = int(raw_talk.get("event_year") or self.event_year or 0)
        if event_name and event_year:
            title = re.sub(rf"^{re.escape(event_name)}\s+{event_year}\s*-\s*", "", title, flags=re.IGNORECASE)

        speakers = self._speaker_names(raw_talk.get("speakers"))
        for speaker in speakers:
            title = re.sub(rf"\s*\({re.escape(speaker)}\)\s*$", "", title)
        return clean_text(title)

    def _tags(self, raw_talk: dict[str, Any], *, event_year: int) -> list[str]:
        """Build stable tags for one talk."""

        tags = list(self.source_config.tags)
        for tag in ["allbsides", self.source_config.slug]:
            if tag not in tags:
                tags.append(tag)
        if event_year:
            edition_tag = f"{self.source_config.slug}-{event_year}"
            if edition_tag not in tags:
                tags.append(edition_tag)

        raw_tags = raw_talk.get("tags")
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if not isinstance(tag, dict):
                    continue
                slug = clean_text(tag.get("slug") or tag.get("name")).lower().replace(" ", "-")
                if slug and slug not in tags:
                    tags.append(slug)
        return tags

    def _allbsides_talk_url(self, raw_talk: dict[str, Any]) -> str:
        """Return an AllBSides talk URL when no video URL is available."""

        video_id = clean_text(raw_talk.get("video_id"))
        if video_id:
            return f"https://allbsides.com/talk/{video_id}.html"
        talk_id = clean_text(raw_talk.get("id"))
        return f"https://allbsides.com/talk/{talk_id}.html" if talk_id else self.source_config.urls.get("homepage", "")
