"""Zotero corpus loading and lightweight similarity search."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import requests

from src.models.artifact import Artifact

DEFAULT_ZOTERO_API_BASE_URL = "https://api.zotero.org"
ZOTERO_API_VERSION = "3"
DEFAULT_ZOTERO_LIMIT = 100
DEFAULT_ZOTERO_MAX_ITEMS = 2000

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+\-.]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "using",
    "based",
    "study",
    "paper",
    "approach",
    "towards",
    "toward",
    "large",
    "language",
    "model",
    "models",
}


@dataclass(slots=True, frozen=True)
class ZoteroItem:
    """Normalized Zotero item used for local retrieval."""

    key: str
    title: str
    authors: tuple[str, ...]
    abstract: str
    venue: str
    year: int | None
    tags: tuple[str, ...]
    url: str | None = None

    def text(self) -> str:
        """Return searchable text for this Zotero item."""

        return " ".join(
            part
            for part in [
                self.title,
                self.abstract,
                self.venue,
                " ".join(self.tags),
                " ".join(self.authors),
            ]
            if part
        )


class ZoteroCorpus:
    """Collection of normalized Zotero items from CSL JSON or Zotero API."""

    def __init__(self, items: list[ZoteroItem]) -> None:
        """Initialize with normalized items."""

        self.items = [item for item in items if item.title.strip()]

    @classmethod
    def from_csl_json(cls, path: Path) -> "ZoteroCorpus":
        """Load Zotero Better CSL JSON export."""

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Zotero CSL JSON must be a list: {path}")
        return cls([_item_from_csl(raw, index) for index, raw in enumerate(payload) if isinstance(raw, dict)])

    @classmethod
    def from_api(
        cls,
        *,
        library_kind: str,
        library_id: str,
        api_key: str | None = None,
        base_url: str = DEFAULT_ZOTERO_API_BASE_URL,
        collection_key: str | None = None,
        max_items: int = DEFAULT_ZOTERO_MAX_ITEMS,
        timeout: int = 30,
    ) -> "ZoteroCorpus":
        """Fetch Zotero items from Web API or local API."""

        client = ZoteroAPIClient(
            library_kind=library_kind,
            library_id=library_id,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        return cls(client.fetch_items(collection_key=collection_key, max_items=max_items))


class ZoteroAPIClient:
    """Small read-only Zotero API client."""

    def __init__(
        self,
        *,
        library_kind: str,
        library_id: str,
        api_key: str | None = None,
        base_url: str = DEFAULT_ZOTERO_API_BASE_URL,
        timeout: int = 30,
    ) -> None:
        """Initialize API client."""

        if library_kind not in {"users", "groups"}:
            raise ValueError("library_kind must be 'users' or 'groups'")
        self.library_kind = library_kind
        self.library_id = library_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_items(self, *, collection_key: str | None = None, max_items: int = DEFAULT_ZOTERO_MAX_ITEMS) -> list[ZoteroItem]:
        """Fetch top-level Zotero items and normalize them."""

        endpoint = f"{self.base_url}/{self.library_kind}/{self.library_id}"
        if collection_key:
            endpoint = f"{endpoint}/collections/{collection_key}/items/top"
        else:
            endpoint = f"{endpoint}/items/top"

        items: list[ZoteroItem] = []
        start = 0
        while len(items) < max_items:
            limit = min(DEFAULT_ZOTERO_LIMIT, max_items - len(items))
            response = requests.get(
                endpoint,
                params={"format": "json", "include": "data", "limit": limit, "start": start},
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                break
            for raw in payload:
                if isinstance(raw, dict):
                    items.append(_item_from_api(raw))
            if len(payload) < limit:
                break
            start += limit
        return items

    def _headers(self) -> dict[str, str]:
        """Return Zotero API headers."""

        headers = {"Zotero-API-Version": ZOTERO_API_VERSION}
        if self.api_key:
            headers["Zotero-API-Key"] = self.api_key
        return headers


class ZoteroMatcher:
    """Token-cosine retrieval over a Zotero corpus."""

    def __init__(self, corpus: ZoteroCorpus) -> None:
        """Precompute item vectors."""

        self.corpus = corpus
        self._vectors = [_vectorize(item.text()) for item in corpus.items]
        self._norms = [_norm(vector) for vector in self._vectors]

    def match(self, artifact: Artifact, *, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top-k Zotero matches for one artifact."""

        query = _vectorize(_artifact_text(artifact))
        query_norm = _norm(query)
        if not query or query_norm == 0:
            return []

        scored: list[tuple[float, ZoteroItem]] = []
        for item, vector, norm in zip(self.corpus.items, self._vectors, self._norms):
            if norm == 0:
                continue
            score = _cosine(query, query_norm, vector, norm)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "title": item.title,
                "score": round(score, 4),
                "authors": list(item.authors[:4]),
                "venue": item.venue,
                "year": item.year,
                "topics": list(item.tags[:3]),
                "url": item.url,
            }
            for score, item in scored[:top_k]
        ]


def build_zotero_corpus_from_env() -> ZoteroCorpus:
    """Build a Zotero corpus from env-configured CSL JSON or API credentials."""

    csl_path = os.getenv("ZOTERO_CSL_JSON")
    if csl_path:
        return ZoteroCorpus.from_csl_json(Path(csl_path).expanduser())

    user_id = os.getenv("ZOTERO_USER_ID")
    group_id = os.getenv("ZOTERO_GROUP_ID")
    api_key = os.getenv("ZOTERO_API_KEY")
    base_url = os.getenv("ZOTERO_API_BASE_URL", DEFAULT_ZOTERO_API_BASE_URL)
    collection_key = os.getenv("ZOTERO_COLLECTION_KEY")
    max_items = _int_from_env("ZOTERO_MAX_ITEMS", DEFAULT_ZOTERO_MAX_ITEMS)

    if user_id:
        return ZoteroCorpus.from_api(
            library_kind="users",
            library_id=user_id,
            api_key=api_key,
            base_url=base_url,
            collection_key=collection_key,
            max_items=max_items,
        )
    if group_id:
        return ZoteroCorpus.from_api(
            library_kind="groups",
            library_id=group_id,
            api_key=api_key,
            base_url=base_url,
            collection_key=collection_key,
            max_items=max_items,
        )

    raise ValueError("Configure ZOTERO_CSL_JSON, ZOTERO_USER_ID, or ZOTERO_GROUP_ID before running academic-filter")


def _int_from_env(name: str, default: int) -> int:
    """Return a positive integer from an environment variable."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _item_from_csl(raw: dict[str, Any], index: int) -> ZoteroItem:
    """Normalize one Better CSL JSON item."""

    authors = tuple(_creator_name(author) for author in raw.get("author", []) if isinstance(author, dict))
    tags = _split_tags(raw.get("keyword"))
    issued = raw.get("issued") if isinstance(raw.get("issued"), dict) else {}
    year = _year_from_date_parts(issued.get("date-parts"))
    return ZoteroItem(
        key=str(raw.get("id") or raw.get("DOI") or index),
        title=str(raw.get("title") or "").strip(),
        authors=tuple(author for author in authors if author),
        abstract=str(raw.get("abstract") or raw.get("note") or "").strip(),
        venue=str(raw.get("container-title") or raw.get("event-title") or raw.get("publisher") or "").strip(),
        year=year,
        tags=tags,
        url=str(raw.get("URL") or raw.get("url") or raw.get("DOI") or "").strip() or None,
    )


def _item_from_api(raw: dict[str, Any]) -> ZoteroItem:
    """Normalize one Zotero API v3 item."""

    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    creators = data.get("creators", []) if isinstance(data.get("creators"), list) else []
    tags_payload = data.get("tags", []) if isinstance(data.get("tags"), list) else []
    tags = tuple(
        str(tag.get("tag")).strip()
        for tag in tags_payload
        if isinstance(tag, dict) and str(tag.get("tag") or "").strip()
    )
    return ZoteroItem(
        key=str(raw.get("key") or data.get("key") or data.get("DOI") or ""),
        title=str(data.get("title") or "").strip(),
        authors=tuple(_api_creator_name(creator) for creator in creators if isinstance(creator, dict)),
        abstract=str(data.get("abstractNote") or data.get("abstract") or "").strip(),
        venue=str(
            data.get("publicationTitle")
            or data.get("conferenceName")
            or data.get("proceedingsTitle")
            or data.get("publisher")
            or ""
        ).strip(),
        year=_year_from_text(str(data.get("date") or "")),
        tags=tags,
        url=str(data.get("url") or data.get("DOI") or "").strip() or None,
    )


def _creator_name(raw: dict[str, Any]) -> str:
    """Return one CSL creator name."""

    if raw.get("literal"):
        return str(raw["literal"]).strip()
    return " ".join(str(raw.get(key) or "").strip() for key in ["given", "family"]).strip()


def _api_creator_name(raw: dict[str, Any]) -> str:
    """Return one Zotero API creator name."""

    if raw.get("name"):
        return str(raw["name"]).strip()
    return " ".join(str(raw.get(key) or "").strip() for key in ["firstName", "lastName"]).strip()


def _split_tags(raw: Any) -> tuple[str, ...]:
    """Normalize CSL keyword field."""

    if isinstance(raw, list):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    if isinstance(raw, str):
        return tuple(part.strip() for part in re.split(r"[,;]", raw) if part.strip())
    return ()


def _year_from_date_parts(raw: Any) -> int | None:
    """Extract a year from CSL date-parts."""

    if isinstance(raw, list) and raw and isinstance(raw[0], list) and raw[0]:
        try:
            return int(raw[0][0])
        except (TypeError, ValueError):
            return None
    return None


def _year_from_text(value: str) -> int | None:
    """Extract a year from a Zotero date string."""

    match = re.search(r"(19|20)\d{2}", value)
    return int(match.group(0)) if match else None


def _artifact_text(artifact: Artifact) -> str:
    """Return searchable text for one artifact."""

    return " ".join(
        part
        for part in [
            artifact.title,
            artifact.abstract,
            artifact.summary_l1,
            artifact.summary_l2,
            artifact.summary_l3,
            " ".join(artifact.tags or []),
            " ".join(artifact.authors or []),
        ]
        if part
    )


def _tokenize(value: str) -> list[str]:
    """Tokenize text for similarity search."""

    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(value)
        if token.lower() not in STOPWORDS and len(token) <= 40
    ]


def _vectorize(value: str) -> Counter[str]:
    """Build a log-scaled term vector."""

    counts = Counter(_tokenize(value))
    return Counter({token: 1.0 + math.log(count) for token, count in counts.items()})


def _norm(vector: Counter[str]) -> float:
    """Return vector L2 norm."""

    return math.sqrt(sum(weight * weight for weight in vector.values()))


def _cosine(left: Counter[str], left_norm: float, right: Counter[str], right_norm: float) -> float:
    """Return cosine similarity between sparse vectors."""

    if len(left) > len(right):
        left, right = right, left
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    return dot / (left_norm * right_norm)
