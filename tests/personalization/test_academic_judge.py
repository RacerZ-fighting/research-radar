"""Tests for Zotero-backed LLM academic relevance judgment."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.pipelines.academic_judge import AcademicJudgePipeline
from src.reporting.relevance_filter import should_display_artifact
from src.repositories.artifact_repository import ArtifactRepository


class StubJudgeClient:
    """Deterministic LLM stub for academic relevance judgment."""

    def __init__(self, *, relevant: bool, score: float) -> None:
        self.relevant = relevant
        self.score = score
        self.calls: list[dict[str, object]] = []

    def generate(self, prompt: str, **kwargs) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        return json.dumps(
            {
                "relevant": self.relevant,
                "relevance_score": self.score,
                "reason": "候选论文与 Zotero 证据都聚焦 LLM agent 的提示注入风险。",
                "matched_zotero_titles": ["Prompt Injection Defenses for Tool-Using LLM Agents"],
            },
            ensure_ascii=False,
        )


class AcademicJudgePipelineTestCase(unittest.TestCase):
    """Integration tests for academic relevance judgment."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.engine = create_database_engine(f"sqlite+pysqlite:///{self.workspace / 'test.db'}")
        create_all_tables(self.engine)
        self.session_factory = create_session_factory(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_pipeline_writes_relevant_judgment(self) -> None:
        """Pipeline should persist strict LLM relevance judgment into score_breakdown."""

        artifact = self._save_artifact()
        stub = StubJudgeClient(relevant=True, score=0.82)

        updated = AcademicJudgePipeline(session_factory=self.session_factory, llm_client=stub).process(artifact.id)

        self.assertEqual(len(updated), 1)
        breakdown = updated[0].score_breakdown
        self.assertTrue(breakdown["academic_relevance_judged"])
        self.assertTrue(breakdown["academic_relevance_relevant"])
        self.assertEqual(breakdown["academic_relevance_score"], 0.82)
        self.assertIn("academic_judge_", stub.calls[0]["cache_key"])
        self.assertIn("Prompt Injection Defenses", stub.calls[0]["prompt"])
        self.assertTrue(should_display_artifact(updated[0]))

    def test_display_filter_hides_judged_irrelevant_paper(self) -> None:
        """Judged papers should use LLM relevance instead of the raw Zotero threshold."""

        artifact = self._save_artifact()
        stub = StubJudgeClient(relevant=False, score=0.2)

        updated = AcademicJudgePipeline(session_factory=self.session_factory, llm_client=stub).process(artifact.id)

        self.assertFalse(updated[0].score_breakdown["academic_relevance_relevant"])
        self.assertFalse(should_display_artifact(updated[0]))

    def _save_artifact(self) -> Artifact:
        """Save one active paper with Zotero evidence."""

        session = self.session_factory()
        try:
            return ArtifactRepository(session).save(
                Artifact(
                    title="Prompt Injection Vulnerabilities in LLM Agents",
                    authors=["Alice Example"],
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00001",
                    abstract="We evaluate prompt injection attacks against tool-using LLM agents.",
                    summary_l3="论文评估工具调用型 LLM agent 面临的提示注入攻击。",
                    tags=["llm-security"],
                    score_breakdown={
                        "zotero_relevance_evaluated": True,
                        "zotero_similarity": 0.12,
                        "zotero_min_similarity": 0.18,
                        "zotero_matches": [
                            {
                                "title": "Prompt Injection Defenses for Tool-Using LLM Agents",
                                "score": 0.12,
                                "topics": ["prompt-injection", "agent-security"],
                            }
                        ],
                        "academic_quality_evaluated": True,
                        "academic_quality_score": 0.85,
                        "academic_quality_min_for_arxiv": 0.5,
                    },
                    status=ArtifactStatus.ACTIVE,
                )
            )
        finally:
            session.close()
