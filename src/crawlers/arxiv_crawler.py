"""arXiv paper crawler using the Atom API."""

from __future__ import annotations

import logging
import math
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from src.crawlers.base import PaperCrawler, clean_text
from src.exceptions import CrawlerError

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# arXiv policy: max 1 request per 3 seconds
REQUEST_INTERVAL_SECONDS = 3
MAX_RESULTS_PER_PAGE = 100

DEFAULT_CATEGORIES = ["cs.CR", "cs.SE", "cs.PL"]


class ArxivCrawler(PaperCrawler):
    """Fetch recent papers from arXiv using the Atom API."""

    source_name = "arXiv"
    source_slug = "arxiv"

    def __init__(
        self,
        *,
        categories: list[str] | None = None,
        max_results: int = 2000,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """Initialize with target categories and result limit."""

        super().__init__(timeout=timeout, max_retries=max_retries)
        self.categories = categories or DEFAULT_CATEGORIES
        self.max_results = max_results

    def fetch_papers(self, years: list[int]) -> list[dict[str, Any]]:
        """Fetch papers from arXiv for the given categories.

        The years parameter is used to filter results by publication year.
        arXiv API doesn't support date range filtering directly in the query,
        so we filter post-fetch.
        """

        target_years = set(self.normalize_years(years)) if years else set()
        if not self.categories:
            return []

        if len(self.categories) == 1:
            return self._fetch_query(f"cat:{self.categories[0]}", target_years, self.max_results)

        per_category_limit = max(1, math.ceil(self.max_results / len(self.categories)))
        all_papers: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for index, category in enumerate(self.categories):
            if index > 0:
                time.sleep(REQUEST_INTERVAL_SECONDS)

            category_papers = self._fetch_query(f"cat:{category}", target_years, per_category_limit)
            for paper in category_papers:
                key = self._dedupe_key(paper)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_papers.append(paper)
                if len(all_papers) >= self.max_results:
                    logger.info("Fetched %s papers from arXiv (%s)", len(all_papers), ", ".join(self.categories))
                    return all_papers

        logger.info("Fetched %s papers from arXiv (%s)", len(all_papers), ", ".join(self.categories))
        return all_papers

    def _fetch_query(
        self,
        query: str,
        target_years: set[int],
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Fetch one arXiv search query in paginated batches."""

        all_papers: list[dict[str, Any]] = []
        start = 0

        while start < max_results:
            batch_size = min(MAX_RESULTS_PER_PAGE, max_results - start)
            params = {
                "search_query": query,
                "start": str(start),
                "max_results": str(batch_size),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            url = f"{ARXIV_API_URL}?{urlencode(params)}"
            logger.info("Fetching arXiv batch: query=%s, start=%s, max_results=%s", query, start, batch_size)

            try:
                response_text = self.fetch_url(url)
            except CrawlerError:
                logger.error("Failed to fetch arXiv batch for query=%s at start=%s", query, start)
                break

            papers = self._parse_atom_response(response_text, target_years)
            if not papers:
                break

            all_papers.extend(papers)
            start += batch_size

            # Respect arXiv rate limit
            if start < max_results:
                time.sleep(REQUEST_INTERVAL_SECONDS)

        return all_papers

    def _dedupe_key(self, paper: dict[str, Any]) -> str:
        """Return a stable best-effort key for duplicate papers across categories."""

        for field_name in ("arxiv_id", "url", "title"):
            value = paper.get(field_name)
            if value:
                return str(value).strip().lower()
        return repr(sorted(paper.items()))

    def _parse_atom_response(
        self,
        xml_text: str,
        target_years: set[int],
    ) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML response into paper dicts."""

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Failed to parse arXiv XML response: %s", exc)
            return []

        papers: list[dict[str, Any]] = []

        for entry in root.findall(f"{ATOM_NS}entry"):
            paper = self._parse_entry(entry)
            if paper is None:
                continue

            # Year filter
            if target_years:
                paper_year = paper.get("year")
                if paper_year and paper_year not in target_years:
                    continue

            papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> dict[str, Any] | None:
        """Parse one Atom entry element into a paper dict."""

        # arXiv ID
        id_elem = entry.find(f"{ATOM_NS}id")
        if id_elem is None or not id_elem.text:
            return None
        arxiv_url = id_elem.text.strip()
        arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_url else arxiv_url.rsplit("/", 1)[-1]
        # Strip version number (e.g., "2301.12345v2" -> "2301.12345")
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.rsplit("v", 1)[0]

        # Title
        title_elem = entry.find(f"{ATOM_NS}title")
        title = clean_text(title_elem.text) if title_elem is not None and title_elem.text else ""
        if not title:
            return None

        # Authors
        authors = []
        for author_elem in entry.findall(f"{ATOM_NS}author"):
            name_elem = author_elem.find(f"{ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append(clean_text(name_elem.text))

        # Abstract
        summary_elem = entry.find(f"{ATOM_NS}summary")
        abstract = clean_text(summary_elem.text) if summary_elem is not None and summary_elem.text else ""

        # Published date
        published_elem = entry.find(f"{ATOM_NS}published")
        published_at = None
        year = None
        if published_elem is not None and published_elem.text:
            try:
                published_dt = datetime.fromisoformat(published_elem.text.replace("Z", "+00:00"))
                published_at = published_dt.isoformat()
                year = published_dt.year
            except ValueError:
                pass

        # Categories
        categories = []
        for cat_elem in entry.findall(f"{ARXIV_NS}primary_category"):
            term = cat_elem.get("term", "")
            if term:
                categories.append(term)
        for cat_elem in entry.findall(f"{ATOM_NS}category"):
            term = cat_elem.get("term", "")
            if term and term not in categories:
                categories.append(term)

        # PDF link
        pdf_url = None
        for link_elem in entry.findall(f"{ATOM_NS}link"):
            if link_elem.get("title") == "pdf":
                pdf_url = link_elem.get("href")
                break

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": year,
            "published_at": published_at,
            "url": arxiv_url,
            "paper_url": pdf_url or arxiv_url,
            "arxiv_id": arxiv_id,
            "categories": categories,
            "source": "arXiv",
        }
