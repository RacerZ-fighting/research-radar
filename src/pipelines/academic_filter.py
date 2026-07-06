"""Academic personalization pipeline based on Zotero and CSRankings evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from src.db.session import SessionLocal
from src.exceptions import PipelineError
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.personalization.academic_quality import DEFAULT_CSRANKINGS_URL, CSRankingsQualityIndex, load_quality_index
from src.personalization.zotero import ZoteroCorpus, ZoteroMatcher, build_zotero_corpus_from_env
from src.pipelines.base import BasePipeline
from src.repositories.artifact_repository import ArtifactRepository

ACADEMIC_FILTER_VERSION = "v4-zotero-maxitems2000-topics3"
DEFAULT_TOP_K = 5


@dataclass(slots=True)
class AcademicFilterConfig:
    """Runtime options for academic filtering."""

    top_k: int = DEFAULT_TOP_K
    zotero_min_similarity: float = 0.18
    arxiv_min_quality: float = 0.5


class AcademicFilterPipeline(BasePipeline):
    """Persist Zotero personal relevance and CSRankings quality evidence."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        zotero_corpus: ZoteroCorpus | None = None,
        zotero_json_path: Path | None = None,
        quality_index: CSRankingsQualityIndex | None = None,
        csrankings_csv_path: Path | None = None,
        csrankings_url: str | None = DEFAULT_CSRANKINGS_URL,
        config: AcademicFilterConfig | None = None,
    ) -> None:
        """Initialize the pipeline."""

        self.session_factory = session_factory or SessionLocal
        self.zotero_corpus = zotero_corpus or self._load_zotero_corpus(zotero_json_path)
        self.quality_index = quality_index or load_quality_index(csv_path=csrankings_csv_path, url=csrankings_url)
        self.config = config or AcademicFilterConfig()

    def process(self, input_data: Any) -> list[Artifact]:
        """Evaluate target academic artifacts and persist evidence."""

        if not self.validate_input(input_data):
            raise PipelineError("Invalid input for academic filter pipeline")

        matcher = ZoteroMatcher(self.zotero_corpus)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            artifacts = self._resolve_targets(repository, input_data)
            updated: list[Artifact] = []
            for artifact in artifacts:
                if not self._needs_academic_filter(artifact):
                    continue
                matches = matcher.match(artifact, top_k=self.config.top_k)
                zotero_similarity = float(matches[0]["score"]) if matches else 0.0
                quality = self.quality_index.score_artifact(artifact)

                breakdown = dict(artifact.score_breakdown or {})
                breakdown.update(
                    {
                        "zotero_relevance_evaluated": True,
                        "zotero_relevance_version": ACADEMIC_FILTER_VERSION,
                        "zotero_similarity": round(zotero_similarity, 4),
                        "zotero_matches": matches,
                        "zotero_min_similarity": self.config.zotero_min_similarity,
                        "academic_quality_version": ACADEMIC_FILTER_VERSION,
                        "academic_quality_min_for_arxiv": self.config.arxiv_min_quality,
                    }
                )
                breakdown.update(quality)
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
        """Resolve pipeline input into active academic artifacts."""

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
                if isinstance(item, Artifact):
                    artifacts.append(item)
                else:
                    artifact = repository.get_by_id(item)
                    if artifact is not None:
                        artifacts.append(artifact)

        return [
            artifact
            for artifact in artifacts
            if artifact.status == ArtifactStatus.ACTIVE and artifact.source_type == SourceType.PAPERS
        ]

    def _needs_academic_filter(self, artifact: Artifact) -> bool:
        """Return whether the artifact needs current academic filter evidence."""

        breakdown = artifact.score_breakdown or {}
        return breakdown.get("zotero_relevance_version") != ACADEMIC_FILTER_VERSION

    def _load_zotero_corpus(self, zotero_json_path: Path | None) -> ZoteroCorpus:
        """Load Zotero corpus from explicit path or environment."""

        if zotero_json_path is not None:
            return ZoteroCorpus.from_csl_json(zotero_json_path)
        return build_zotero_corpus_from_env()
