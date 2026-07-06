"""LLM-backed academic relevance judgment from Zotero evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session, sessionmaker

from src.db.session import SessionLocal
from src.exceptions import PipelineError
from src.llm import LLMClient, ModelTier
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.pipelines.base import BasePipeline
from src.repositories.artifact_repository import ArtifactRepository

logger = logging.getLogger(__name__)

ACADEMIC_RELEVANCE_JUDGE_VERSION = "v1-zotero-llm-judge"
DEFAULT_MIN_RELEVANCE = 0.6
DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_PROMPT_TEMPLATE = """你正在为安全科研情报系统判断一篇候选论文是否真的和用户已有 Zotero 文献库相关。

只返回 JSON：
{"relevant": true, "relevance_score": 0.0, "reason": "中文一句话说明", "matched_zotero_titles": []}

{{artifact_context}}
"""


@dataclass(slots=True, frozen=True)
class AcademicRelevanceJudgment:
    """Structured relevance judgment returned by the LLM."""

    relevant: bool
    relevance_score: float
    reason: str
    matched_zotero_titles: list[str]


class AcademicJudgePipeline(BasePipeline):
    """Judge personal academic relevance using candidate paper and Zotero matches."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        llm_client: LLMClient | Any | None = None,
        prompt_template_path: Path | None = None,
        judge_version: str = ACADEMIC_RELEVANCE_JUDGE_VERSION,
        min_relevance: float = DEFAULT_MIN_RELEVANCE,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        request_delay_seconds: float = 0.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialize the judge pipeline."""

        self.session_factory = session_factory or SessionLocal
        self.llm_client = llm_client or LLMClient()
        self.prompt_template_path = prompt_template_path or Path("prompts/academic_relevance_judge.md")
        self.judge_version = judge_version
        self.min_relevance = min(max(min_relevance, 0.0), 1.0)
        self.max_attempts = max(1, max_attempts)
        self.request_delay_seconds = max(0.0, request_delay_seconds)
        self.sleep_fn = sleep_fn

    def process(self, input_data: Any) -> list[Artifact]:
        """Judge selected active academic artifacts and persist results."""

        if not self.validate_input(input_data):
            raise PipelineError("Invalid input for academic judge pipeline")

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            artifacts = self._resolve_targets(repository, input_data)
            template = self._load_prompt_template()
            updated: list[Artifact] = []
            targets = [artifact for artifact in artifacts if self._needs_judgment(artifact)]
            for index, artifact in enumerate(targets):
                if index > 0 and self.request_delay_seconds > 0:
                    self.sleep_fn(self.request_delay_seconds)
                prompt = self._build_prompt(template, artifact)
                judgment = self._judge_with_retries(artifact, prompt)
                if judgment is None:
                    continue
                breakdown = dict(artifact.score_breakdown or {})
                breakdown["academic_relevance_judge_version"] = self.judge_version
                breakdown["academic_relevance_judged"] = True
                breakdown["academic_relevance_min_score"] = self.min_relevance
                breakdown["academic_relevance_relevant"] = judgment.relevant
                breakdown["academic_relevance_score"] = judgment.relevance_score
                breakdown["academic_relevance_reason"] = judgment.reason
                breakdown["academic_relevance_matched_zotero_titles"] = judgment.matched_zotero_titles
                artifact.score_breakdown = breakdown
                updated.append(repository.save(artifact))
            return updated
        finally:
            session.close()

    def _judge_with_retries(self, artifact: Artifact, prompt: str) -> AcademicRelevanceJudgment | None:
        """Return one judgment, retrying transient provider failures."""

        cache_key = self._build_cache_key(artifact)
        for attempt in range(1, self.max_attempts + 1):
            try:
                response_text = self.llm_client.generate(
                    prompt,
                    model_tier=ModelTier.FAST,
                    max_tokens=360,
                    temperature=0.0,
                    cache_key=cache_key,
                )
                return self._parse_response(response_text)
            except Exception as exc:  # pragma: no cover - defensive external boundary
                logger.warning(
                    "Failed to judge artifact %s (%s), attempt %s/%s: %s",
                    artifact.id,
                    artifact.title,
                    attempt,
                    self.max_attempts,
                    exc,
                )
                if attempt < self.max_attempts:
                    self.sleep_fn(1.0 * attempt)
        return None

    def validate_input(self, data: Any) -> bool:
        """Return whether the input selection is supported."""

        if data is None:
            return True
        if isinstance(data, int):
            return True
        if isinstance(data, Artifact):
            return True
        return isinstance(data, list) and all(isinstance(item, (int, Artifact)) for item in data)

    def validate_output(self, data: Any) -> bool:
        """Return whether output is a list of artifacts."""

        return isinstance(data, list) and all(isinstance(item, Artifact) for item in data)

    def _resolve_targets(self, repository: ArtifactRepository, input_data: Any) -> list[Artifact]:
        """Resolve input into active paper artifacts."""

        if input_data is None:
            artifacts = repository.list_by_status(ArtifactStatus.ACTIVE)
        elif isinstance(input_data, Artifact):
            artifacts = [input_data]
        elif isinstance(input_data, int):
            artifact = repository.get_by_id(input_data)
            artifacts = [artifact] if artifact is not None else []
        else:
            artifacts = []
            for item in input_data:
                artifact = item if isinstance(item, Artifact) else repository.get_by_id(item)
                if artifact is not None:
                    artifacts.append(artifact)
        return [
            artifact
            for artifact in artifacts
            if artifact.status == ArtifactStatus.ACTIVE and artifact.source_type == SourceType.PAPERS
        ]

    def _needs_judgment(self, artifact: Artifact) -> bool:
        """Return whether current judge evidence should be generated."""

        breakdown = artifact.score_breakdown or {}
        if breakdown.get("academic_relevance_judge_version") == self.judge_version:
            return False
        return isinstance(breakdown.get("zotero_matches"), list) and bool(breakdown.get("zotero_matches"))

    def _load_prompt_template(self) -> str:
        """Load prompt template from disk or fall back to the embedded template."""

        if self.prompt_template_path.exists():
            template = self.prompt_template_path.read_text(encoding="utf-8").strip()
            if template:
                return template
        return DEFAULT_PROMPT_TEMPLATE.strip()

    def _build_prompt(self, template: str, artifact: Artifact) -> str:
        """Render one artifact and its evidence into the prompt template."""

        context = self._build_artifact_context(artifact)
        if "{{artifact_context}}" in template:
            return template.replace("{{artifact_context}}", context)
        return f"{template}\n\n{context}"

    def _build_artifact_context(self, artifact: Artifact) -> str:
        """Build concise prompt context for relevance judgment."""

        breakdown = dict(artifact.score_breakdown or {})
        zotero_matches = breakdown.get("zotero_matches") if isinstance(breakdown.get("zotero_matches"), list) else []
        signals = breakdown.get("academic_quality_signals") if isinstance(breakdown.get("academic_quality_signals"), dict) else {}
        matched_faculty = signals.get("matched_faculty", []) if isinstance(signals, dict) else []
        lines = [
            "Candidate paper:",
            f"- Title: {artifact.title}",
            f"- Authors: {', '.join(artifact.authors or []) or 'Unknown'}",
            f"- Source: {artifact.source_name or 'Unknown'} ({artifact.source_tier or 'unknown'})",
            f"- Existing tags: {', '.join(artifact.tags or []) or 'None'}",
            f"- Summary: {(artifact.summary_l3 or artifact.summary_l1 or artifact.abstract or '').strip() or 'N/A'}",
            "",
            "Zotero retrieval evidence:",
            f"- Top token cosine similarity: {breakdown.get('zotero_similarity', 'N/A')}",
        ]
        for index, match in enumerate(zotero_matches[:5], start=1):
            if not isinstance(match, dict):
                continue
            topics = match.get("topics") if isinstance(match.get("topics"), list) else []
            authors = match.get("authors") if isinstance(match.get("authors"), list) else []
            lines.extend(
                [
                    f"{index}. Title: {match.get('title', 'Unknown')}",
                    f"   Score: {match.get('score', 'N/A')}",
                    f"   Authors: {', '.join(str(author) for author in authors[:4]) or 'Unknown'}",
                    f"   Venue/year: {match.get('venue', '')} {match.get('year', '')}".strip(),
                    f"   Topics: {', '.join(str(topic) for topic in topics) or 'None'}",
                ]
            )
        if matched_faculty:
            lines.append("")
            lines.append("Quality evidence, not relevance evidence:")
            for faculty in matched_faculty[:3]:
                if not isinstance(faculty, dict):
                    continue
                lines.append(f"- {faculty.get('name', 'Unknown')} ({faculty.get('affiliation', 'unknown affiliation')})")
        return "\n".join(lines)

    def _build_cache_key(self, artifact: Artifact) -> str:
        """Return a cache key that changes when judgment evidence changes."""

        breakdown = dict(artifact.score_breakdown or {})
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "title": artifact.title,
                    "abstract": artifact.abstract,
                    "summary_l3": artifact.summary_l3,
                    "tags": artifact.tags,
                    "zotero_similarity": breakdown.get("zotero_similarity"),
                    "zotero_matches": breakdown.get("zotero_matches"),
                    "academic_quality_signals": breakdown.get("academic_quality_signals"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        return f"academic_judge_{self.judge_version}_{artifact.canonical_id}_{fingerprint}"

    def _parse_response(self, response_text: str) -> AcademicRelevanceJudgment:
        """Parse and normalize one LLM judgment response."""

        payload = self._load_json_payload(response_text)
        relevance_score = _clamp_float(payload.get("relevance_score"), 0.0, 1.0)
        relevant = bool(payload.get("relevant")) and relevance_score >= self.min_relevance
        reason = " ".join(str(payload.get("reason") or "").split()).strip()
        if len(reason) > 220:
            reason = reason[:217].rstrip() + "..."
        matched_titles = _normalize_titles(payload.get("matched_zotero_titles"))
        return AcademicRelevanceJudgment(
            relevant=relevant,
            relevance_score=relevance_score,
            reason=reason or "LLM 未提供理由。",
            matched_zotero_titles=matched_titles,
        )

    def _load_json_payload(self, response_text: str) -> dict[str, Any]:
        """Load a JSON payload, accepting optional markdown code fences."""

        candidate = response_text.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise PipelineError(f"LLM academic judge response is not valid JSON: {response_text}") from exc
        if not isinstance(payload, dict):
            raise PipelineError("LLM academic judge response must be a JSON object")
        return payload


def _clamp_float(raw_value: Any, minimum: float, maximum: float) -> float:
    """Return a float clamped to a range."""

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return minimum
    return min(max(value, minimum), maximum)


def _normalize_titles(value: Any) -> list[str]:
    """Return up to three clean Zotero titles."""

    if not isinstance(value, list):
        return []
    titles: list[str] = []
    seen: set[str] = set()
    for item in value:
        title = " ".join(str(item).split()).strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title[:160])
        if len(titles) >= 3:
            break
    return titles
