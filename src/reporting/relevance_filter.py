"""Shared display filtering for low-relevance artifacts."""

from __future__ import annotations

from typing import Any

from src.models.artifact import Artifact
from src.models.enums import SourceType

MIN_DISPLAY_LLM_RELEVANCE = 0.4
MIN_DISPLAY_ZOTERO_SIMILARITY = 0.18
MIN_DISPLAY_ARXIV_QUALITY = 0.5
REMOVED_INDUSTRY_SOURCE_MARKERS = ("rsa conference", "rsac")


def get_llm_relevance_score(artifact: Artifact) -> float | None:
    """Return the persisted LLM relevance score when available."""

    score_breakdown: dict[str, Any] = dict(artifact.score_breakdown or {})
    raw_score = score_breakdown.get("llm_relevance_score")
    if raw_score is None:
        return None
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return None


def should_display_artifact(artifact: Artifact, *, min_score: float = MIN_DISPLAY_LLM_RELEVANCE) -> bool:
    """Return whether an artifact should be shown in daily consumption surfaces."""

    llm_score = get_llm_relevance_score(artifact)
    if llm_score is not None and llm_score < min_score:
        return False
    if not _passes_industry_conference_filter(artifact):
        return False
    if not _passes_academic_personal_filter(artifact):
        return False
    return True


def _passes_industry_conference_filter(artifact: Artifact) -> bool:
    """Hide malformed or low-signal industry conference entries."""

    if artifact.source_type != SourceType.BLOGS:
        return True

    source_name = str(artifact.source_name or "").strip().lower()
    if any(marker in source_name for marker in REMOVED_INDUSTRY_SOURCE_MARKERS):
        return False
    if not _is_industry_conference_artifact(artifact):
        return True

    text_fields = [artifact.abstract, artifact.summary_l1, artifact.summary_l2, artifact.summary_l3]
    has_content = any(str(value or "").strip() for value in text_fields)
    if not artifact.published_at and not has_content:
        return False
    has_summary = any(str(value or "").strip() for value in [artifact.summary_l1, artifact.summary_l2, artifact.summary_l3])
    if get_llm_relevance_score(artifact) is None and not has_summary:
        return False

    return True


def _is_industry_conference_artifact(artifact: Artifact) -> bool:
    """Return whether an artifact belongs to the industry conference lane."""

    tags = _normalized_tags(artifact)
    if "industry-conference" in tags:
        return True
    source_name = str(artifact.source_name or "").strip().lower()
    return any(marker in source_name for marker in ("black hat", "blackhat", "def con", "defcon", "bsides"))


def _normalized_tags(artifact: Artifact) -> set[str]:
    """Return lower-case string tags."""

    return {str(tag).strip().lower() for tag in artifact.tags or [] if str(tag).strip()}


def _passes_academic_personal_filter(artifact: Artifact) -> bool:
    """Return whether academic personalization evidence allows display."""

    if artifact.source_type != SourceType.PAPERS:
        return True

    score_breakdown: dict[str, Any] = dict(artifact.score_breakdown or {})

    has_llm_judgment = bool(score_breakdown.get("academic_relevance_judged"))
    source_tier = (artifact.source_tier or "").lower()
    if not has_llm_judgment and source_tier == "t1-conference":
        return False

    if not has_llm_judgment and score_breakdown.get("zotero_relevance_evaluated"):
        return False

    if has_llm_judgment:
        threshold = _float_value(score_breakdown.get("academic_relevance_min_score"), 0.6)
        score = _float_value(score_breakdown.get("academic_relevance_score"), 0.0)
        if not score_breakdown.get("academic_relevance_relevant") or score < threshold:
            return False

    if source_tier == "t2-arxiv" and score_breakdown.get("academic_quality_evaluated"):
        threshold = _float_value(score_breakdown.get("academic_quality_min_for_arxiv"), MIN_DISPLAY_ARXIV_QUALITY)
        quality = _float_value(score_breakdown.get("academic_quality_score"), 0.0)
        if quality < threshold:
            return False

    return True


def _float_value(raw_value: Any, default: float) -> float:
    """Return a float with fallback."""

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default
