"""Official RSAC agenda crawler backed by RainFocus widget APIs."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text
from src.exceptions import CrawlerError
from src.models.enums import SourceType


class RSACAgendaCrawler(BlogCrawler):
    """Fetch RSAC agenda sessions from the official RainFocus widget API."""

    _SKIP_TITLE_RE = re.compile(
        r"(breakfast|reception|meet\s*&\s*greet|cybrew|café|cafe|expo|booth|lunch|party)",
        flags=re.IGNORECASE,
    )
    _SKIP_FORMATS = {"networking", "invite only"}

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 20,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type != SourceType.BLOGS:
            raise ValueError("RSACAgendaCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.event_label = clean_text(str(source_config.params.get("event_label") or source_config.name))
        self.agenda_url = clean_text(
            str(source_config.params.get("agenda_url") or source_config.urls.get("agenda") or source_config.urls.get("usa"))
        )
        self.sessions_api_url = clean_text(
            str(source_config.params.get("sessions_api_url") or "https://events.rsaconference.com/api/sessions")
        )
        self.widget_id = clean_text(str(source_config.params.get("widget_id") or ""))
        self.api_profile_id = clean_text(str(source_config.params.get("api_profile_id") or ""))
        self.session_catalog_tab = clean_text(str(source_config.params.get("session_catalog_tab") or ""))
        self.browser_timezone = clean_text(str(source_config.params.get("browser_timezone") or "Asia/Shanghai"))

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch and parse RSAC agenda sessions."""

        self._require_api_config()
        effective_limit = self._effective_limit(limit)
        page_size = self._page_size()
        offset = 0
        articles: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        total: int | None = None

        while len(articles) < effective_limit:
            payload = self._fetch_sessions_page(offset=offset)
            items, page_total = self._items_from_payload(payload)
            if total is None:
                total = page_total
            if not items:
                break

            for item in items:
                article = self._build_item(item)
                if article is None:
                    continue
                dedupe_key = clean_text(str(item.get("sessionID") or item.get("sessionTimeID") or article["title"]))
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                articles.append(article)
                if len(articles) >= effective_limit:
                    break

            offset += page_size
            if total is not None and offset >= total:
                break

        if not articles:
            raise CrawlerError(f"{self.source_name} official agenda returned no parseable sessions")
        return articles

    def _fetch_sessions_page(self, *, offset: int) -> dict[str, Any]:
        """Fetch one official RainFocus sessions page."""

        data: dict[str, str] = {
            "tab.sessioncatalogdisplay": self.session_catalog_tab,
            "type": "session",
            "browserTimezone": self.browser_timezone,
            "catalogDisplay": "list",
        }
        if offset:
            data["from"] = str(offset)
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://path.rsaconference.com",
            "Referer": "https://path.rsaconference.com/",
            "rfWidgetId": self.widget_id,
            "rfApiProfileId": self.api_profile_id,
        }
        try:
            response = self.session.post(self.sessions_api_url, headers=headers, data=data, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except ValueError as exc:
            raise CrawlerError(f"{self.source_name} official agenda JSON was not valid") from exc
        except Exception as exc:
            raise CrawlerError(f"Failed to fetch {self.source_name} agenda from RainFocus") from exc

        if not isinstance(payload, dict):
            raise CrawlerError(f"{self.source_name} official agenda JSON had an unexpected shape")
        if clean_text(str(payload.get("responseCode") or "")) not in {"", "0"}:
            raise CrawlerError(
                f"{self.source_name} official agenda returned responseCode={payload.get('responseCode')}"
            )
        return payload

    def _items_from_payload(self, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
        """Return session items and total count from either RainFocus response shape."""

        raw_items = payload.get("items")
        total = self._safe_int(payload.get("total") or payload.get("totalSearchItems"))
        if isinstance(raw_items, list):
            return [item for item in raw_items if isinstance(item, dict)], total

        section_items: list[dict[str, Any]] = []
        sections = payload.get("sectionList")
        if not isinstance(sections, list):
            return [], total
        for section in sections:
            if not isinstance(section, dict):
                continue
            if total is None:
                total = self._safe_int(section.get("total"))
            items = section.get("items")
            if isinstance(items, list):
                section_items.extend(item for item in items if isinstance(item, dict))
        return section_items, total

    def _build_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Convert one RSAC session into the raw blog-like item shape."""

        title = clean_text(str(item.get("title") or ""))
        if not title or self._SKIP_TITLE_RE.search(title):
            return None
        if self._safe_int(item.get("published")) == 0 or item.get("testRecord") is True:
            return None

        attributes = self._attribute_values(item)
        formats = attributes.get("Type/Format", [])
        if any(value.strip().lower() in self._SKIP_FORMATS for value in formats):
            return None

        tracks = attributes.get("Topic/Track", [])
        classifications = attributes.get("Session Classification", [])
        if self._is_low_signal_session(tracks, classifications):
            return None

        authors = self._authors(item)
        published_at = self._published_date(item)
        session_id = clean_text(str(item.get("sessionID") or item.get("sessionTimeID") or ""))
        article_url = f"{self.agenda_url}#session/{session_id}" if session_id else self.agenda_url

        excerpt = self._excerpt(item, authors, formats, tracks, classifications)

        return {
            "title": title,
            "authors": authors,
            "published_at": published_at,
            "source_url": self.agenda_url,
            "article_url": article_url,
            "excerpt": excerpt,
            "conference": self.event_label,
            "tags": self._merge_tags(formats, tracks, classifications),
            "source_type": "blogs",
            "source_slug": self.source_slug,
        }

    def _is_low_signal_session(self, tracks: list[str], classifications: list[str]) -> bool:
        """Return whether an agenda session is too broad for the topic lane."""

        normalized_tracks = {value.strip().lower() for value in tracks}
        normalized_classifications = {value.strip().lower() for value in classifications}
        return "business perspectives" in normalized_tracks and "general" in normalized_classifications

    def _attribute_values(self, item: dict[str, Any]) -> dict[str, list[str]]:
        """Group RainFocus attribute values by display name."""

        grouped: dict[str, list[str]] = {}
        raw_values = item.get("attributevalues")
        if not isinstance(raw_values, list):
            return grouped
        for raw_value in raw_values:
            if not isinstance(raw_value, dict):
                continue
            key = clean_text(str(raw_value.get("attribute") or raw_value.get("attributeDisplayName") or ""))
            value = clean_text(str(raw_value.get("value") or raw_value.get("attributeValueDisplayName") or ""))
            if key and value and value not in grouped.setdefault(key, []):
                grouped[key].append(value)
        return grouped

    def _authors(self, item: dict[str, Any]) -> list[str]:
        """Return unique speaker names in agenda order."""

        authors: list[str] = []
        participants = item.get("participants")
        if not isinstance(participants, list):
            return authors
        for participant in participants:
            if not isinstance(participant, dict):
                continue
            name = clean_text(
                str(
                    participant.get("preferredFullName")
                    or participant.get("fullName")
                    or participant.get("globalFullName")
                    or ""
                )
            )
            if name and name not in authors:
                authors.append(name)
        return authors

    def _published_date(self, item: dict[str, Any]) -> str | None:
        """Return the local scheduled date for one session."""

        times = item.get("times")
        if isinstance(times, list) and times:
            first_time = times[0]
            if isinstance(first_time, dict):
                date = clean_text(str(first_time.get("date") or first_time.get("endDate") or ""))
                if re.match(r"\d{4}-\d{2}-\d{2}", date):
                    return date
        utc_start = clean_text(str(item.get("utcStartTime") or ""))
        if re.match(r"\d{4}/\d{2}/\d{2}", utc_start):
            return utc_start[:10].replace("/", "-")
        return None

    def _excerpt(
        self,
        item: dict[str, Any],
        authors: list[str],
        formats: list[str],
        tracks: list[str],
        classifications: list[str],
    ) -> str:
        """Build a compact excerpt with agenda metadata plus abstract."""

        parts = [self.event_label]
        code = clean_text(str(item.get("code") or item.get("abbreviation") or ""))
        if code:
            parts.append(f"Code: {code}")
        time_label = self._time_label(item)
        if time_label:
            parts.append(time_label)
        if authors:
            parts.append(f"Speakers: {', '.join(authors)}")
        if formats:
            parts.append(f"Format: {', '.join(formats)}")
        if tracks:
            parts.append(f"Track: {', '.join(tracks)}")
        if classifications:
            parts.append(f"Classification: {', '.join(classifications)}")
        abstract = clean_text(BeautifulSoup(str(item.get("abstract") or ""), "html.parser").get_text(" "))
        if abstract:
            parts.append(abstract)
        return ". ".join(parts) + "."

    def _time_label(self, item: dict[str, Any]) -> str:
        """Return a human-readable scheduled time and room label."""

        times = item.get("times")
        if not isinstance(times, list) or not times:
            return ""
        first_time = times[0]
        if not isinstance(first_time, dict):
            return ""
        date = clean_text(str(first_time.get("dateFormatted") or first_time.get("date") or ""))
        start = clean_text(str(first_time.get("startTimeFormatted") or first_time.get("startTime") or ""))
        end = clean_text(str(first_time.get("endTimeFormatted") or first_time.get("endTime") or ""))
        room = clean_text(str(first_time.get("room") or ""))
        pieces = [piece for piece in (date, f"{start}-{end}" if start and end else start, room) if piece]
        return "Time: " + ", ".join(pieces) if pieces else ""

    def _merge_tags(self, formats: list[str], tracks: list[str], classifications: list[str]) -> list[str]:
        """Merge source tags with agenda provenance and selected attributes."""

        tags: list[str] = []
        candidates = [
            *self.source_config.tags,
            "official-rainfocus-agenda",
            self.event_label,
            *formats,
            *tracks,
            *classifications,
        ]
        for candidate in candidates:
            tag = clean_text(str(candidate))
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    def _require_api_config(self) -> None:
        """Raise a clear error if the RainFocus widget credentials are missing."""

        missing = [
            name
            for name, value in {
                "widget_id": self.widget_id,
                "api_profile_id": self.api_profile_id,
                "session_catalog_tab": self.session_catalog_tab,
            }.items()
            if not value
        ]
        if missing:
            raise CrawlerError(f"{self.source_name} official agenda missing config params: {', '.join(missing)}")

    def _effective_limit(self, requested_limit: int) -> int:
        """Prefer configured agenda cap over the generic blog CLI cap."""

        try:
            configured_limit = int(self.source_config.params.get("max_results"))
        except (TypeError, ValueError):
            configured_limit = requested_limit
        return max(requested_limit, configured_limit)

    def _page_size(self) -> int:
        """Return RainFocus page size."""

        try:
            page_size = int(self.source_config.params.get("page_size") or 50)
        except (TypeError, ValueError):
            page_size = 50
        return max(1, page_size)

    def _safe_int(self, value: Any) -> int | None:
        """Convert RainFocus numeric values when possible."""

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
