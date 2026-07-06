"""Tests for academic personalization and quality filtering."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.personalization.academic_quality import CSRankingsQualityIndex
from src.pipelines.academic_filter import AcademicFilterConfig, AcademicFilterPipeline
from src.reporting.relevance_filter import should_display_artifact
from src.repositories.artifact_repository import ArtifactRepository


def test_csrankings_quality_matches_candidate_author(tmp_path: Path) -> None:
    """CSRankings quality index should mark papers from known faculty."""

    csv_path = tmp_path / "csrankings.csv"
    csv_path.write_text(
        "name,affiliation,homepage,scholarid\nAlice Example,Example University,https://example.edu,abc123\n",
        encoding="utf-8",
    )
    artifact = Artifact(
        title="Security Paper",
        authors=["Alice Example", "Bob Student"],
        source_type=SourceType.PAPERS,
        source_tier="t2-arxiv",
        source_name="arXiv",
        source_url="https://arxiv.org/abs/2607.00002",
    )

    result = CSRankingsQualityIndex.from_csv_path(csv_path).score_artifact(artifact)

    assert result["academic_quality_evaluated"] is True
    assert result["academic_quality_score"] == 0.85
    assert result["academic_quality_signals"]["matched_faculty"][0]["affiliation"] == "Example University"


class AcademicFilterPipelineTestCase(unittest.TestCase):
    """Integration tests for academic filter evidence persistence."""

    def setUp(self) -> None:
        """Create isolated DB and fixture files."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.engine = create_database_engine(f"sqlite+pysqlite:///{self.workspace / 'test.db'}")
        create_all_tables(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self.zotero_json = self.workspace / "zotero.json"
        self.zotero_json.write_text(
            json.dumps(
                [
                    {
                        "id": "z1",
                        "title": "Prompt Injection Defenses for Tool-Using LLM Agents",
                        "author": [{"given": "Alice", "family": "Example"}],
                        "abstract": "Prompt injection attacks and defenses for agentic systems.",
                        "keyword": "prompt-injection,llm-security",
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.csrankings_csv = self.workspace / "csrankings.csv"
        self.csrankings_csv.write_text(
            "name,affiliation,homepage,scholarid\nAlice Example,Example University,https://example.edu,abc123\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        """Dispose DB resources."""

        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_pipeline_writes_zotero_and_quality_breakdown(self) -> None:
        """Pipeline should persist Zotero matches and academic quality signals."""

        session = self.session_factory()
        try:
            artifact = ArtifactRepository(session).save(
                Artifact(
                    title="Prompt Injection Vulnerabilities in Large Language Models",
                    authors=["Alice Example"],
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00001",
                    abstract="We evaluate prompt injection attacks against LLM agents.",
                    tags=["prompt-injection", "llm-security"],
                    status=ArtifactStatus.ACTIVE,
                )
            )
        finally:
            session.close()

        updated = AcademicFilterPipeline(
            session_factory=self.session_factory,
            zotero_json_path=self.zotero_json,
            csrankings_csv_path=self.csrankings_csv,
            csrankings_url=None,
            config=AcademicFilterConfig(zotero_min_similarity=0.18, arxiv_min_quality=0.5),
        ).process(None)

        self.assertEqual(len(updated), 1)
        breakdown = updated[0].score_breakdown
        self.assertTrue(breakdown["zotero_relevance_evaluated"])
        self.assertGreaterEqual(breakdown["zotero_similarity"], 0.18)
        self.assertEqual(breakdown["zotero_matches"][0]["title"], "Prompt Injection Defenses for Tool-Using LLM Agents")
        self.assertEqual(breakdown["academic_quality_score"], 0.85)
        self.assertFalse(should_display_artifact(updated[0]))

    def test_low_zotero_similarity_hides_evaluated_academic_item(self) -> None:
        """Evaluated papers below the Zotero threshold should not be displayed."""

        artifact = Artifact(
            title="Battery Material Synthesis",
            authors=["Unknown Author"],
            source_type=SourceType.PAPERS,
            source_tier="t2-arxiv",
            source_name="arXiv",
            source_url="https://arxiv.org/abs/2607.00003",
            score_breakdown={
                "zotero_relevance_evaluated": True,
                "zotero_similarity": 0.02,
                "zotero_min_similarity": 0.18,
                "academic_quality_evaluated": True,
                "academic_quality_score": 0.85,
            },
        )

        self.assertFalse(should_display_artifact(artifact))

    def test_unjudged_t1_conference_paper_is_hidden(self) -> None:
        """Top-tier conference papers should wait for LLM relevance judgment."""

        artifact = Artifact(
            title="Prompt Injection Study",
            authors=["Alice Example"],
            source_type=SourceType.PAPERS,
            source_tier="t1-conference",
            source_name="NDSS",
            source_url="https://www.ndss-symposium.org/ndss-paper/prompt-injection-study/",
            abstract="We evaluate prompt injection attacks against LLM agents.",
            score_breakdown={
                "zotero_relevance_evaluated": True,
                "zotero_similarity": 0.95,
                "zotero_min_similarity": 0.18,
            },
        )

        self.assertFalse(should_display_artifact(artifact))

    def test_judged_relevant_t1_conference_paper_is_displayed(self) -> None:
        """Top-tier conference papers can display after LLM relevance judgment."""

        artifact = Artifact(
            title="Prompt Injection Study",
            authors=["Alice Example"],
            source_type=SourceType.PAPERS,
            source_tier="t1-conference",
            source_name="NDSS",
            source_url="https://www.ndss-symposium.org/ndss-paper/prompt-injection-study/",
            abstract="We evaluate prompt injection attacks against LLM agents.",
            score_breakdown={
                "zotero_relevance_evaluated": True,
                "zotero_similarity": 0.95,
                "academic_relevance_judged": True,
                "academic_relevance_relevant": True,
                "academic_relevance_score": 0.9,
                "academic_relevance_min_score": 0.6,
            },
        )

        self.assertTrue(should_display_artifact(artifact))

    def test_low_arxiv_quality_hides_evaluated_arxiv_item(self) -> None:
        """Evaluated arXiv papers below quality threshold should not be displayed."""

        artifact = Artifact(
            title="Prompt Injection Study",
            authors=["Unknown Author"],
            source_type=SourceType.PAPERS,
            source_tier="t2-arxiv",
            source_name="arXiv",
            source_url="https://arxiv.org/abs/2607.00004",
            score_breakdown={
                "zotero_relevance_evaluated": True,
                "zotero_similarity": 0.3,
                "zotero_min_similarity": 0.18,
                "academic_quality_evaluated": True,
                "academic_quality_score": 0.4,
                "academic_quality_min_for_arxiv": 0.5,
            },
        )

        self.assertFalse(should_display_artifact(artifact))

    def test_malformed_industry_conference_artifact_is_hidden(self) -> None:
        """Historical conference pages without topic content should not be displayed."""

        artifact = Artifact(
            title="Welcome to BSidesSF 2020",
            authors=[],
            source_type=SourceType.BLOGS,
            source_tier="t3-research-blog",
            source_name="BSidesSF",
            source_url="https://bsidessf.org/news/2020/02/welcome-to-bsidessf",
            tags=["industry-conference", "security-conference", "talks"],
        )

        self.assertFalse(should_display_artifact(artifact))

    def test_unprocessed_industry_conference_artifact_is_hidden(self) -> None:
        """Raw conference items should wait for summary or LLM relevance before display."""

        artifact = Artifact(
            title="BSidesSF 2026 - More Role Models in AppSec: How to Get It Right",
            authors=[],
            source_type=SourceType.BLOGS,
            source_tier="t3-research-blog",
            source_name="BSidesSF",
            source_url="https://bsidessf.org/schedule/raw-topic",
            published_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
            abstract="Drawing on interviews with security leaders, this talk discusses AppSec role models.",
            tags=["industry-conference", "security-conference", "talks"],
        )

        self.assertFalse(should_display_artifact(artifact))

    def test_summarized_industry_conference_artifact_is_displayed(self) -> None:
        """Conference items with AI summaries may be displayed before relevance scoring."""

        artifact = Artifact(
            title="Not My Vibe: When AI Coding Agents Go Off the Rails",
            authors=[],
            source_type=SourceType.BLOGS,
            source_tier="t3-research-blog",
            source_name="BSidesSF",
            source_url="https://www.youtube.com/watch?v=ES2oO6Md9g4",
            published_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
            abstract="A talk about AI coding agent failures.",
            summary_l3="这场演讲总结 AI coding agent 在真实开发流程中可能引入的安全和工程风险。",
            tags=["industry-conference", "security-conference", "talks"],
        )

        self.assertTrue(should_display_artifact(artifact))

    def test_removed_rsac_source_artifact_is_hidden(self) -> None:
        """RSAC artifacts should stay out of consumption lanes after source removal."""

        artifact = Artifact(
            title="Advancing Cyber Defense in the Era of AI Driven Threats",
            authors=["Brad Sarsfield"],
            source_type=SourceType.BLOGS,
            source_tier="t3-research-blog",
            source_name="RSA Conference",
            source_url="https://path.rsaconference.com/flow/rsac/us26/FullAgenda/page/catalog",
            published_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
            abstract="A business-perspective session about resilient, intelligence-driven defenses.",
            tags=[
                "industry-conference",
                "security-conference",
                "official-rainfocus-agenda",
                "RSAC 2026",
                "Track Session",
                "Business Perspectives",
                "General",
            ],
        )

        self.assertFalse(should_display_artifact(artifact))
