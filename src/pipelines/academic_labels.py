"""LLM-backed academic focus label generation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
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

ACADEMIC_FOCUS_LABEL_VERSION = "v1-ai-focus-labels"
DEFAULT_PROMPT_TEMPLATE = """你正在为安全科研情报系统给一篇论文生成可扫读的研究焦点标签。

只返回 JSON：
{"labels": ["标签1", "标签2"], "reason": "一句话理由"}

要求：
- labels 返回 2-4 个中文或中英混合短标签。
- 标签必须聚焦具体研究问题、对象、方法或约束。
- 不要返回 Computer Science、Security、Machine Learning、LLM、AI 等过泛标签。

{{artifact_context}}
"""


@dataclass(slots=True, frozen=True)
class AcademicFocusPayload:
    """Structured focus labels returned by the LLM."""

    labels: list[str]
    reason: str


class AcademicLabelPipeline(BasePipeline):
    """Generate concise academic focus labels and persist them in score_breakdown."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        llm_client: LLMClient | Any | None = None,
        prompt_template_path: Path | None = None,
        label_version: str = ACADEMIC_FOCUS_LABEL_VERSION,
        request_delay_seconds: float = 0.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialize the label pipeline."""

        self.session_factory = session_factory or SessionLocal
        self.llm_client = llm_client or LLMClient()
        self.prompt_template_path = prompt_template_path or Path("prompts/academic_focus_labels.md")
        self.label_version = label_version
        self.request_delay_seconds = max(0.0, request_delay_seconds)
        self.sleep_fn = sleep_fn

    def process(self, input_data: Any) -> list[Artifact]:
        """Generate focus labels for selected active academic artifacts."""

        if not self.validate_input(input_data):
            raise PipelineError("Invalid input for academic label pipeline")

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            artifacts = self._resolve_targets(repository, input_data)
            template = self._load_prompt_template()
            updated: list[Artifact] = []
            targets = [artifact for artifact in artifacts if self._needs_labels(artifact)]
            for index, artifact in enumerate(targets):
                if index > 0 and self.request_delay_seconds > 0:
                    self.sleep_fn(self.request_delay_seconds)
                prompt = self._build_prompt(template, artifact)
                response_text = self.llm_client.generate(
                    prompt,
                    model_tier=ModelTier.FAST,
                    max_tokens=260,
                    temperature=0.1,
                    cache_key=self._build_cache_key(artifact),
                )
                payload = self._parse_response(response_text)
                breakdown = dict(artifact.score_breakdown or {})
                breakdown["academic_focus_label_version"] = self.label_version
                breakdown["academic_focus_labels"] = payload.labels
                breakdown["academic_focus_reason"] = payload.reason
                artifact.score_breakdown = breakdown
                updated.append(repository.save(artifact))
            return updated
        finally:
            session.close()

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

    def _needs_labels(self, artifact: Artifact) -> bool:
        """Return whether current label evidence should be generated."""

        breakdown = artifact.score_breakdown or {}
        return breakdown.get("academic_focus_label_version") != self.label_version

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
        """Build concise prompt context for label generation."""

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
            f"- Abstract: {(artifact.abstract or artifact.summary_l3 or artifact.summary_l1 or '').strip() or 'N/A'}",
            "",
            "Zotero relevance evidence:",
            f"- Top similarity: {breakdown.get('zotero_similarity', 'N/A')}",
        ]
        for match in zotero_matches[:3]:
            if not isinstance(match, dict):
                continue
            topics = match.get("topics") if isinstance(match.get("topics"), list) else []
            lines.append(
                "- Related Zotero paper: "
                f"{match.get('title', 'Unknown')} "
                f"(topics: {', '.join(str(topic) for topic in topics) or 'None'})"
            )
        if matched_faculty:
            lines.append("")
            lines.append("Quality evidence:")
            for faculty in matched_faculty[:3]:
                if not isinstance(faculty, dict):
                    continue
                lines.append(
                    "- CSRankings faculty: "
                    f"{faculty.get('name', 'Unknown')} "
                    f"({faculty.get('affiliation', 'unknown affiliation')})"
                )
        return "\n".join(lines)

    def _build_cache_key(self, artifact: Artifact) -> str:
        """Return a cache key that changes when visible label evidence changes."""

        breakdown = dict(artifact.score_breakdown or {})
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "title": artifact.title,
                    "abstract": artifact.abstract,
                    "summary_l3": artifact.summary_l3,
                    "tags": artifact.tags,
                    "zotero_matches": breakdown.get("zotero_matches"),
                    "academic_quality_signals": breakdown.get("academic_quality_signals"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        return f"academic_focus_{self.label_version}_{artifact.canonical_id}_{fingerprint}"

    def _parse_response(self, response_text: str) -> AcademicFocusPayload:
        """Parse and normalize one LLM label response."""

        payload = self._load_json_payload(response_text)
        labels = self._normalize_labels(payload.get("labels"))
        reason = " ".join(str(payload.get("reason") or "").split()).strip()
        if not labels:
            raise PipelineError("LLM academic label response missing labels")
        if len(reason) > 180:
            reason = reason[:177].rstrip() + "..."
        return AcademicFocusPayload(labels=labels, reason=reason)

    def _load_json_payload(self, response_text: str) -> dict[str, Any]:
        """Load a JSON payload, accepting optional markdown code fences."""

        candidate = response_text.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
            candidate = re.sub(r"\s*```$", "", candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise PipelineError(f"LLM academic label response is not valid JSON: {response_text}") from exc
        if not isinstance(payload, dict):
            raise PipelineError("LLM academic label response must be a JSON object")
        return payload

    def _normalize_labels(self, value: Any) -> list[str]:
        """Return deduplicated, specific focus labels."""

        if not isinstance(value, list):
            return []
        labels: list[str] = []
        seen: set[str] = set()
        for item in value:
            label = " ".join(str(item).split()).strip()
            if not label or _is_generic_label(label):
                continue
            if len(label) > 36:
                label = label[:33].rstrip() + "..."
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            labels.append(label)
            if len(labels) >= 4:
                break
        return labels


def _is_generic_label(label: str) -> bool:
    """Return whether a label is too broad to be useful on paper cards."""

    normalized = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
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
    }
    return normalized in generic or normalized.startswith("computer science ")
