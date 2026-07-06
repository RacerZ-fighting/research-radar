"""Presentation helpers for the local web console."""

from __future__ import annotations

import re
from typing import Any

from src.models.artifact import Artifact
from src.models.enums import SourceType

MAX_TOPIC_CHIPS = 5
MAX_CHIPS = 11
MAX_PAPER_SUMMARY_CHARS = 520
MAX_DEFAULT_SUMMARY_CHARS = 420


def artifact_source_label(artifact: Artifact) -> str:
    """Return the source label used on artifact cards."""

    conference = _conference_label(artifact)
    if conference:
        return conference
    return artifact.source_name or "Unknown source"


def artifact_summary(artifact: Artifact) -> str:
    """Return the summary text used on artifact cards."""

    if artifact.source_type == SourceType.PAPERS:
        for candidate in [artifact.summary_l3, artifact.summary_l1]:
            if candidate and _contains_cjk(candidate):
                return _compact_label(candidate, MAX_PAPER_SUMMARY_CHARS)
        focus_labels = (artifact.score_breakdown or {}).get("academic_focus_labels")
        if isinstance(focus_labels, list):
            labels = [str(label).strip() for label in focus_labels if str(label).strip()]
            if labels:
                return _compact_label(f"研究焦点：{'、'.join(labels[:4])}。", MAX_PAPER_SUMMARY_CHARS)
        return "暂无中文摘要，可打开原文查看。"
    summary = artifact.summary_l3 or artifact.summary_l1
    if summary:
        return _compact_label(summary, MAX_DEFAULT_SUMMARY_CHARS)
    return "暂无中文摘要，可打开原文查看。"


def artifact_chips(artifact: Artifact) -> list[dict[str, str]]:
    """Build compact UI chips for artifact topics and academic evidence."""

    chips: list[dict[str, str]] = []
    seen: set[str] = set()

    if artifact.source_type == SourceType.PAPERS:
        chips.extend(_academic_evidence_chips(artifact, seen))
    else:
        conference = _conference_label(artifact)
        if conference:
            _append_chip(chips, seen, label=conference, kind="conference")
        for tag in artifact.tags or []:
            _append_chip(chips, seen, label=str(tag), kind="topic")
            if len([chip for chip in chips if chip["kind"] == "topic"]) >= MAX_TOPIC_CHIPS:
                break

    return chips[:MAX_CHIPS]


def _conference_label(artifact: Artifact) -> str | None:
    """Return a concrete conference edition label when available."""

    external_ids = artifact.external_ids or {}
    conference = str(external_ids.get("conference") or "").strip() if isinstance(external_ids, dict) else ""
    if not conference:
        return None

    source_name = (artifact.source_name or "").strip()
    if source_name and conference.lower() == source_name.lower():
        return None
    return conference


def _academic_evidence_chips(artifact: Artifact, seen: set[str]) -> list[dict[str, str]]:
    """Return Zotero and quality evidence chips for a paper artifact."""

    score_breakdown: dict[str, Any] = dict(artifact.score_breakdown or {})
    chips: list[dict[str, str]] = []

    focus_labels = score_breakdown.get("academic_focus_labels")
    has_focus_labels = False
    if isinstance(focus_labels, list):
        for label in focus_labels[:4]:
            _append_chip(chips, seen, label=str(label), kind="focus")
        has_focus_labels = bool(chips)

    if not has_focus_labels:
        for tag in artifact.tags or []:
            if _is_generic_topic(str(tag)):
                continue
            _append_chip(chips, seen, label=str(tag), kind="topic")
            if len([chip for chip in chips if chip["kind"] == "topic"]) >= MAX_TOPIC_CHIPS:
                break

    relevance_score = _float_value(score_breakdown.get("academic_relevance_score"))
    relevance_reason = str(score_breakdown.get("academic_relevance_reason") or "").strip()
    if score_breakdown.get("academic_relevance_judged") and relevance_score is not None:
        _append_chip(
            chips,
            seen,
            label=f"相关度 {relevance_score:.2f}",
            kind="relevance",
            title=relevance_reason or f"LLM relevance score: {relevance_score:.2f}",
        )

    signals = score_breakdown.get("academic_quality_signals")
    matched_faculty = signals.get("matched_faculty", []) if isinstance(signals, dict) else []
    if isinstance(matched_faculty, list) and matched_faculty:
        first_faculty = matched_faculty[0] if isinstance(matched_faculty[0], dict) else {}
        faculty_name = str(first_faculty.get("name") or "").strip()
        affiliation = str(first_faculty.get("affiliation") or "").strip()
        if faculty_name:
            _append_chip(chips, seen, label=f"CSRankings: {_compact_label(faculty_name, 28)}", kind="quality")
        if affiliation:
            _append_chip(chips, seen, label=f"Group: {_compact_label(affiliation, 34)}", kind="quality", title=affiliation)

    return chips


def _append_chip(
    chips: list[dict[str, str]],
    seen: set[str],
    *,
    label: str,
    kind: str,
    title: str | None = None,
) -> None:
    """Append one chip if its display label has not appeared yet."""

    label = _compact_label(label, 54)
    key = label.lower()
    if not label or key in seen:
        return
    seen.add(key)
    chips.append({"label": label, "kind": kind, "title": title or label})


def _compact_label(value: str, max_chars: int) -> str:
    """Trim long chip labels without relying on CSS ellipsis."""

    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 3)].rstrip() + "..."


def _float_value(raw_value: Any) -> float | None:
    """Return a float when a value can be parsed."""

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def _is_generic_topic(label: str) -> bool:
    """Return whether a topic is too broad for a paper card chip."""

    normalized = " ".join(label.lower().replace("-", " ").split())
    generic = {
        "ai",
        "llm",
        "security",
        "computer science",
        "machine learning",
        "software engineering",
        "cryptography and security",
        "artificial intelligence",
        "computation and language",
        "computers and society",
        "statistics machine learning",
    }
    return normalized in generic or normalized.startswith("computer science ")


def _contains_cjk(value: str) -> bool:
    """Return whether text contains Chinese/Japanese/Korean characters."""

    return re.search(r"[\u3400-\u9fff]", value) is not None
