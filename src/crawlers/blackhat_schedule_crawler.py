"""Official Black Hat schedule crawler."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config.sources import SourceConfig
from src.crawlers.base import BlogCrawler, clean_text, split_authors
from src.exceptions import CrawlerError
from src.models.enums import SourceType


class BlackHatScheduleCrawler(BlogCrawler):
    """Parse official Black Hat briefing schedule pages."""

    _TIME_HEADER_RE = re.compile(r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s*\|\s*(.+)$")
    _METADATA_RE = re.compile(
        r"(Speaker|Speakers|Contributor|Track|Format|Location):\s*(.*?)(?=(?:,\s*)?"
        r"(?:Speaker|Speakers|Contributor|Track|Format|Location):|$)",
        flags=re.IGNORECASE,
    )
    _SKIP_TITLE_RE = re.compile(
        r"(coffee|tea break|refreshment break|lunch|reception|overflow room|registration|expo hall|business hall opens)",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize from centralized source metadata."""

        if source_config.source_type != SourceType.BLOGS:
            raise ValueError("BlackHatScheduleCrawler only supports blog-like sources")
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.source_config = source_config
        self.source_name = source_config.name
        self.source_slug = source_config.slug
        self.event_label = clean_text(str(source_config.params.get("event_label") or source_config.name))
        self.schedule_url = self._schedule_url()
        self.schedule_dates = self._schedule_dates()
        self.cookie_env = clean_text(str(source_config.params.get("cookie_env") or "BLACKHAT_COOKIE"))

    def fetch_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch and parse the official schedule page."""

        self._apply_cookie()
        html = self._fetch_schedule_html()
        self._raise_if_blocked(html)
        data_url = self._data_url_from_html(html) or "sessions.json"
        payload = self._fetch_schedule_payload(self.to_absolute_url(self.schedule_url, data_url) or data_url)
        articles = self.parse_schedule_payload(payload, limit=self._effective_limit(limit))
        if not articles:
            if "No sessions found" in html:
                raise CrawlerError(
                    f"{self.source_name} official schedule returned no sessions. "
                    f"If your browser can see sessions, export a scoped cookie to {self.cookie_env}."
                )
            raise CrawlerError(f"{self.source_name} official schedule did not contain parseable sessions")
        return articles

    def _fetch_schedule_html(self) -> str:
        """Fetch schedule HTML while translating access blocks into operator guidance."""

        return self._fetch_official_text(self.schedule_url)

    def _fetch_schedule_payload(self, url: str) -> dict[str, Any]:
        """Fetch the official schedule JSON payload."""

        text = self._fetch_official_text(url)
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise CrawlerError(f"{self.source_name} official schedule JSON was not valid") from exc
        if not isinstance(payload, dict):
            raise CrawlerError(f"{self.source_name} official schedule JSON had an unexpected shape")
        return payload

    def _fetch_official_text(self, url: str) -> str:
        """Fetch official Black Hat content with an optional browser-like fallback."""

        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise CrawlerError(f"Failed to fetch {self.source_name} from {url}") from exc
        if response.status_code in {401, 403}:
            return self._fetch_with_browser_impersonation(url, response.status_code)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CrawlerError(f"Failed to fetch {self.source_name} from {url}") from exc
        return response.text

    def _fetch_with_browser_impersonation(self, url: str, original_status: int) -> str:
        """Retry with curl_cffi Chrome impersonation for Cloudflare-cleared sessions."""

        try:
            from curl_cffi import requests as curl_requests
        except ImportError as exc:
            raise CrawlerError(
                f"{self.source_name} official schedule returned HTTP {original_status}. "
                f"Install curl_cffi and export only blackhat.com cookies to {self.cookie_env}."
            ) from exc

        headers = dict(self.session.headers)
        impersonate = clean_text(str(self.source_config.params.get("impersonate") or "chrome136"))
        try:
            response = curl_requests.get(url, headers=headers, timeout=self.timeout, impersonate=impersonate)
        except Exception as exc:  # curl_cffi raises its own request exceptions.
            raise CrawlerError(f"Failed to fetch {self.source_name} from {url}") from exc
        if response.status_code in {401, 403}:
            raise CrawlerError(
                f"{self.source_name} official schedule returned HTTP {response.status_code}. "
                f"If your browser can view it, export only blackhat.com cookies to {self.cookie_env}."
            )
        if response.status_code >= 400:
            raise CrawlerError(f"Failed to fetch {self.source_name} from {url}")
        return response.text

    def _data_url_from_html(self, html: str) -> str | None:
        """Extract the official schedule data URL from the schedule shell."""

        match = re.search(r"var\s+dataUrl\s*=\s*['\"]([^'\"]+)['\"]", html)
        if not match:
            return None
        return clean_text(match.group(1))

    def parse_schedule_payload(self, payload: dict[str, Any], *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse official Black Hat sessions JSON into raw conference items."""

        sessions = payload.get("sessions")
        speakers = payload.get("speakers")
        if not isinstance(sessions, dict):
            return []
        if not isinstance(speakers, dict):
            speakers = {}

        ordered_session_ids = self._ordered_session_ids(payload)
        if not ordered_session_ids:
            ordered_session_ids = list(sessions.keys())

        articles: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for session_id in ordered_session_ids:
            if len(articles) >= limit:
                break
            session = sessions.get(str(session_id)) or sessions.get(session_id)
            if not isinstance(session, dict):
                continue
            item = self._build_item_from_session(session, speakers)
            if item is None:
                continue
            dedupe_key = str(session.get("id") or item["title"])
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            articles.append(item)
        return articles

    def _ordered_session_ids(self, payload: dict[str, Any]) -> list[str]:
        """Return schedule session ids in official display order."""

        ordered: list[str] = []
        sections = payload.get("sections")
        if not isinstance(sections, list):
            return ordered
        for section in sections:
            if not isinstance(section, dict):
                continue
            for ref in section.get("sessions") or []:
                if not isinstance(ref, dict):
                    continue
                session_id = ref.get("session_id") or ref.get("id")
                if session_id is not None:
                    ordered.append(str(session_id))
        return ordered

    def _build_item_from_session(
        self,
        session: dict[str, Any],
        speakers: dict[Any, Any],
    ) -> dict[str, Any] | None:
        """Build one raw item from an official schedule session."""

        title = clean_text(str(session.get("title") or ""))
        if not title or self._SKIP_TITLE_RE.search(title):
            return None
        if int(session.get("cancelled") or 0):
            return None

        track_values = [
            clean_text(str(session.get("track_1") or "")),
            clean_text(str(session.get("track_2") or "")),
        ]
        track = ", ".join(value for value in track_values if value)
        fmt = clean_text(" ".join(str(value) for value in (session.get("duration"), session.get("format")) if value))
        location = clean_text(str(session.get("room") or ""))
        authors = self._authors_from_session(session, speakers)
        published_at = self._session_date(session)
        session_id = clean_text(str(session.get("id") or ""))
        article_url = f"{self.schedule_url}#session/{session_id}" if session_id else self.schedule_url
        excerpt = self._session_excerpt(session, authors, track, fmt, location)

        return {
            "title": title,
            "authors": authors,
            "published_at": published_at,
            "source_url": self.schedule_url,
            "article_url": article_url,
            "excerpt": excerpt,
            "conference": self.event_label,
            "tags": self._merge_tags(track, fmt),
            "source_type": "blogs",
            "source_slug": self.source_slug,
        }

    def _authors_from_session(self, session: dict[str, Any], speakers: dict[Any, Any]) -> list[str]:
        """Resolve speaker references from the official schedule payload."""

        authors: list[str] = []
        for ref in session.get("speakers") or []:
            if not isinstance(ref, dict):
                continue
            person_id = ref.get("person_id")
            speaker = speakers.get(str(person_id)) or speakers.get(person_id)
            if not isinstance(speaker, dict):
                continue
            name = clean_text(f"{speaker.get('first_name') or ''} {speaker.get('last_name') or ''}")
            if name and name not in authors:
                authors.append(name)
        return authors

    def _session_date(self, session: dict[str, Any]) -> str | None:
        """Return the scheduled local date for a session."""

        iso_start = clean_text(str(session.get("iso_start_date") or ""))
        if len(iso_start) >= 10:
            return iso_start[:10]
        time_start = clean_text(str(session.get("time_start") or ""))
        if len(time_start) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", time_start):
            return time_start[:10]
        return clean_text(str(session.get("published_date") or "")) or None

    def _session_excerpt(
        self,
        session: dict[str, Any],
        authors: list[str],
        track: str,
        fmt: str,
        location: str,
    ) -> str:
        """Build an excerpt with schedule metadata plus the official abstract."""

        description = clean_text(BeautifulSoup(str(session.get("description") or ""), "html.parser").get_text(" "))
        parts = [self.event_label]
        time_display = clean_text(str(session.get("time_display") or ""))
        if time_display:
            parts.append(time_display)
        if authors:
            parts.append(f"Speakers: {', '.join(authors)}")
        if track:
            parts.append(f"Track: {track}")
        if fmt:
            parts.append(f"Format: {fmt}")
        if location:
            parts.append(f"Location: {location}")
        if description:
            parts.append(description)
        return ". ".join(parts) + "."

    def parse_schedule_html(self, html: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Parse a Black Hat schedule HTML document into raw conference items."""

        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("script, style, noscript"):
            node.decompose()

        link_map = self._build_link_map(soup)
        lines = self._text_lines(soup)
        articles: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        current_day: str | None = None
        current_time: str | None = None
        current_title: str | None = None
        metadata_lines: list[str] = []

        def flush_current() -> None:
            nonlocal current_title, metadata_lines
            if not current_title:
                return
            item = self._build_item(
                title=current_title,
                metadata_lines=metadata_lines,
                day=current_day,
                time_label=current_time,
                link_map=link_map,
            )
            current_title = None
            metadata_lines = []
            if item is None:
                return
            dedupe_key = item["title"].lower()
            if dedupe_key in seen_titles:
                return
            seen_titles.add(dedupe_key)
            articles.append(item)

        for line in lines:
            time_match = self._TIME_HEADER_RE.match(line)
            if time_match:
                flush_current()
                current_day = time_match.group(1).upper()
                current_time = clean_text(time_match.group(2))
                if len(articles) >= limit:
                    break
                continue

            if current_day is None:
                continue
            if self._is_non_session_line(line):
                continue
            if self._is_metadata_line(line):
                metadata_lines.append(line)
                continue

            flush_current()
            if len(articles) >= limit:
                break
            current_title = line

        if len(articles) < limit:
            flush_current()
        return articles[:limit]

    def _build_item(
        self,
        *,
        title: str,
        metadata_lines: list[str],
        day: str | None,
        time_label: str | None,
        link_map: dict[str, str],
    ) -> dict[str, Any] | None:
        """Build one raw item from parsed schedule state."""

        clean_title = clean_text(title)
        if not clean_title or self._SKIP_TITLE_RE.search(clean_title):
            return None

        metadata = self._parse_metadata(metadata_lines)
        track = metadata.get("track")
        fmt = metadata.get("format")
        location = metadata.get("location")
        article_url = link_map.get(clean_title.lower()) or f"{self.schedule_url}#{self._slugify(clean_title)}"
        tags = self._merge_tags(track, fmt)

        excerpt_parts = [self.event_label]
        if time_label:
            excerpt_parts.append(f"{day.title() if day else 'Session'} {time_label}")
        if track:
            excerpt_parts.append(f"Track: {track}")
        if fmt:
            excerpt_parts.append(f"Format: {fmt}")
        if location:
            excerpt_parts.append(f"Location: {location}")

        return {
            "title": clean_title,
            "authors": metadata.get("authors", []),
            "published_at": self.schedule_dates.get(day or ""),
            "source_url": self.schedule_url,
            "article_url": article_url,
            "excerpt": ". ".join(excerpt_parts) + ".",
            "conference": self.event_label,
            "tags": tags,
            "source_type": "blogs",
            "source_slug": self.source_slug,
        }

    def _parse_metadata(self, lines: list[str]) -> dict[str, Any]:
        """Parse speaker, track, format, and location fields from text lines."""

        joined = clean_text(" ".join(lines))
        metadata: dict[str, Any] = {"authors": []}
        author_values: list[str] = []
        for match in self._METADATA_RE.finditer(joined):
            key = match.group(1).lower()
            value = clean_text(match.group(2).strip(" ,"))
            if not value:
                continue
            if key in {"speaker", "speakers", "contributor"}:
                author_values.append(value)
            elif key == "track":
                metadata["track"] = value
            elif key == "format":
                metadata["format"] = value
            elif key == "location":
                metadata["location"] = value

        authors: list[str] = []
        for raw_author in author_values:
            for author in split_authors(raw_author):
                if author and author not in authors:
                    authors.append(author)
        metadata["authors"] = authors
        return metadata

    def _build_link_map(self, soup: BeautifulSoup) -> dict[str, str]:
        """Build a mapping from visible link text to absolute URLs."""

        links: dict[str, str] = {}
        for node in soup.find_all("a"):
            text = clean_text(node.get_text(" ", strip=True))
            href = clean_text(node.get("href"))
            if not text or not href:
                continue
            absolute = self.to_absolute_url(self.schedule_url, href)
            if absolute:
                links[text.lower()] = absolute
        return links

    def _text_lines(self, soup: BeautifulSoup) -> list[str]:
        """Return normalized visible text lines."""

        return [line for line in (clean_text(part) for part in soup.get_text("\n").splitlines()) if line]

    def _is_metadata_line(self, line: str) -> bool:
        """Return whether a line contains schedule metadata."""

        return bool(re.match(r"^(Speaker|Speakers|Contributor|Track|Format|Location):", line, flags=re.IGNORECASE))

    def _is_non_session_line(self, line: str) -> bool:
        """Filter navigation, facet, and footer text from schedule pages."""

        normalized = line.strip().lower()
        if normalized in {
            "all",
            "all sessions",
            "speakers",
            "format(s)",
            "track(s)",
            "select all |clear",
            "discover more from informa",
        }:
            return True
        if normalized.startswith("all times are "):
            return True
        return False

    def _raise_if_blocked(self, html: str) -> None:
        """Raise a clear error for Cloudflare and bot-check pages."""

        lowered = html.lower()
        if (
            "attention required! | cloudflare" in lowered
            or "sorry, you have been blocked" in lowered
            or "just a moment..." in lowered
            or "enable javascript and cookies" in lowered
        ):
            raise CrawlerError(
                f"{self.source_name} official schedule is blocked by Cloudflare. "
                f"If your browser can view it, export only blackhat.com cookies to {self.cookie_env}."
            )

    def _apply_cookie(self) -> None:
        """Apply an optional manually supplied Black Hat cookie."""

        cookie = clean_text(os.getenv(self.cookie_env)) or clean_text(os.getenv("BLACKHAT_COOKIE"))
        if cookie:
            self.session.headers.update({"Cookie": cookie})

    def _schedule_url(self) -> str:
        """Return the configured official schedule URL."""

        target_urls = self.source_config.params.get("target_urls")
        if isinstance(target_urls, list) and target_urls:
            return clean_text(str(target_urls[0]))
        return clean_text(self.source_config.urls.get("schedule"))

    def _schedule_dates(self) -> dict[str, str]:
        """Return day labels mapped to ISO dates."""

        raw_dates = self.source_config.params.get("schedule_dates")
        if not isinstance(raw_dates, dict):
            return {}
        return {clean_text(str(key)).upper(): clean_text(str(value)) for key, value in raw_dates.items()}

    def _merge_tags(self, track: str | None, fmt: str | None) -> list[str]:
        """Merge source tags with official provenance and schedule metadata."""

        tags: list[str] = []
        candidates = [*self.source_config.tags, "official-schedule", self.event_label]
        for value in (track, fmt):
            if value:
                candidates.extend(part.strip() for part in re.split(r"[,/]", value) if part.strip())

        for candidate in candidates:
            tag = clean_text(str(candidate))
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    def _effective_limit(self, requested_limit: int) -> int:
        """Prefer configured schedule cap over the generic blog CLI cap."""

        try:
            configured_limit = int(self.source_config.params.get("max_results"))
        except (TypeError, ValueError):
            configured_limit = requested_limit
        return max(requested_limit, configured_limit)

    def _slugify(self, value: str) -> str:
        """Build a simple fragment fallback."""

        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
