"""Academic quality signals from CSRankings-style faculty data."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import re
from pathlib import Path
from typing import Any

import requests

from src.models.artifact import Artifact

DEFAULT_CSRANKINGS_URL = "https://raw.githubusercontent.com/emeryberger/CSRankings/gh-pages/csrankings.csv"
DEFAULT_CSRANKINGS_TIMEOUT_SECONDS = 15
NO_QUALITY_SIGNAL_SCORE = 0.4
FACULTY_MATCH_SCORE = 0.85


@dataclass(slots=True, frozen=True)
class FacultyRecord:
    """One CSRankings faculty entry."""

    name: str
    affiliation: str
    homepage: str | None = None
    scholar_id: str | None = None


class CSRankingsQualityIndex:
    """Lookup index for CSRankings faculty and institutions."""

    def __init__(self, records: list[FacultyRecord]) -> None:
        """Initialize lookup maps."""

        self.records = records
        self._by_name = {_normalize_name(record.name): record for record in records if record.name}
        self._institutions = {_normalize_text(record.affiliation) for record in records if record.affiliation}

    @classmethod
    def from_csv_path(cls, path: Path) -> "CSRankingsQualityIndex":
        """Load records from a local CSRankings CSV file."""

        return cls(_parse_csv(path.read_text(encoding="utf-8")))

    @classmethod
    def from_url(
        cls,
        url: str = DEFAULT_CSRANKINGS_URL,
        *,
        timeout: int = DEFAULT_CSRANKINGS_TIMEOUT_SECONDS,
    ) -> "CSRankingsQualityIndex":
        """Load records from a remote CSRankings CSV URL."""

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return cls(_parse_csv(response.text))

    @classmethod
    def empty(cls) -> "CSRankingsQualityIndex":
        """Return an empty quality index."""

        return cls([])

    def score_artifact(self, artifact: Artifact) -> dict[str, Any]:
        """Return quality score and evidence for one artifact."""

        matched_faculty: list[dict[str, str | None]] = []
        for author in artifact.authors or []:
            record = self._by_name.get(_normalize_name(author))
            if record is None:
                continue
            matched_faculty.append(
                {
                    "name": record.name,
                    "affiliation": record.affiliation,
                    "homepage": record.homepage,
                    "scholar_id": record.scholar_id,
                }
            )

        if matched_faculty:
            return {
                "academic_quality_score": FACULTY_MATCH_SCORE,
                "academic_quality_evaluated": True,
                "academic_quality_source": "csrankings",
                "academic_quality_signals": {
                    "matched_faculty": matched_faculty,
                    "reason": "candidate author appears in CSRankings faculty data",
                },
            }

        return {
            "academic_quality_score": NO_QUALITY_SIGNAL_SCORE,
            "academic_quality_evaluated": bool(self.records),
            "academic_quality_source": "csrankings" if self.records else "none",
            "academic_quality_signals": {
                "matched_faculty": [],
                "reason": "no candidate author matched CSRankings faculty data" if self.records else "quality index unavailable",
            },
        }


def load_quality_index(
    *,
    csv_path: Path | None = None,
    url: str | None = DEFAULT_CSRANKINGS_URL,
    timeout: int = DEFAULT_CSRANKINGS_TIMEOUT_SECONDS,
) -> CSRankingsQualityIndex:
    """Load CSRankings quality index, degrading to empty on remote failure."""

    if csv_path is not None:
        return CSRankingsQualityIndex.from_csv_path(csv_path)
    if url:
        try:
            return CSRankingsQualityIndex.from_url(url, timeout=timeout)
        except requests.RequestException:
            return CSRankingsQualityIndex.empty()
    return CSRankingsQualityIndex.empty()


def _parse_csv(text: str) -> list[FacultyRecord]:
    """Parse CSRankings CSV with a tolerant header mapping."""

    reader = csv.DictReader(io.StringIO(text))
    records: list[FacultyRecord] = []
    for row in reader:
        normalized = {_normalize_header(key): value for key, value in row.items() if key is not None}
        name = (normalized.get("name") or normalized.get("faculty") or "").strip()
        affiliation = (normalized.get("affiliation") or normalized.get("institution") or "").strip()
        if not name:
            continue
        records.append(
            FacultyRecord(
                name=name,
                affiliation=affiliation,
                homepage=(normalized.get("homepage") or normalized.get("home_page") or "").strip() or None,
                scholar_id=(normalized.get("scholarid") or normalized.get("scholar_id") or "").strip() or None,
            )
        )
    return records


def _normalize_header(value: str) -> str:
    """Normalize CSV header names."""

    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalize_name(value: str) -> str:
    """Normalize personal names for exact matching."""

    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z\s-]", " ", value).lower()).strip()


def _normalize_text(value: str) -> str:
    """Normalize text for set membership."""

    return re.sub(r"\s+", " ", value.lower()).strip()
