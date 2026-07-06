"""Tests for the daily report generator."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.models.enums import FeedbackTargetType, FeedbackType, SourceType
from src.models.feedback import FeedbackEvent
from src.repositories.artifact_repository import ArtifactRepository
from src.repositories.feedback_repository import FeedbackRepository
from src.reporting.daily import DailyReportGenerator
from tests.reporting.helpers import make_artifact


class DailyReportGeneratorTestCase(unittest.TestCase):
    """Integration tests for daily report generation."""

    def setUp(self) -> None:
        """Create an isolated database and output directory."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        database_path = self.workspace / "test.db"
        database_url = f"sqlite+pysqlite:///{database_path}"
        self.engine = create_database_engine(database_url)
        create_all_tables(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self.output_dir = self.workspace / "reports"
        self.generator = DailyReportGenerator(
            session_factory=self.session_factory,
            output_dir=self.output_dir,
            now_fn=lambda: datetime(2026, 3, 10, 18, 0, tzinfo=timezone.utc),
        )
        self.target_date = date(2026, 3, 10)

    def tearDown(self) -> None:
        """Dispose resources created for the test."""

        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_daily_empty_sections_render(self) -> None:
        """Empty days should still render the new report sections."""

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("## 今日博客推荐（0 篇）", content)
        self.assertIn("暂无符合条件的博客推荐。", content)
        self.assertIn("## 漏洞速报", content)
        self.assertIn("暂无漏洞数据源", content)
        self.assertIn("> 今日无论文更新。", content)
        self.assertIn("- 今日新增博客数: 0", content)
        self.assertIn("- 数据库总量: 0", content)

    def test_daily_recommends_recent_unread_blogs_only(self) -> None:
        """Daily reports should recommend recent unread blogs and exclude papers."""

        recent_blog = make_artifact(
            title="Recent Blog",
            source_type=SourceType.BLOGS,
            source_name="PortSwigger Research",
            final_score=0.93,
            relevance_score=0.88,
            created_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        )
        earlier_blog = make_artifact(
            title="Earlier Blog",
            source_type=SourceType.BLOGS,
            source_name="Project Zero",
            final_score=0.84,
            relevance_score=0.79,
            created_at=datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc),
        )
        read_blog = make_artifact(
            title="Read Blog",
            source_type=SourceType.BLOGS,
            source_name="Cloudflare Security Blog",
            final_score=0.99,
            relevance_score=0.92,
            created_at=datetime(2026, 3, 9, 12, 0, tzinfo=timezone.utc),
        )
        stale_blog = make_artifact(
            title="Stale Blog",
            source_type=SourceType.BLOGS,
            source_name="PortSwigger Research",
            final_score=0.97,
            relevance_score=0.90,
            created_at=datetime(2026, 3, 7, 23, 59, tzinfo=timezone.utc),
        )
        paper = make_artifact(
            title="Fresh Paper",
            source_type=SourceType.PAPERS,
            source_name="IEEE S&P",
            final_score=0.98,
            relevance_score=0.95,
            created_at=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        )

        self._save_artifacts(recent_blog, earlier_blog, read_blog, stale_blog, paper)
        self._mark_as_read(read_blog)

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")
        blog_section = content.split("## 漏洞速报", maxsplit=1)[0]

        self.assertIn("## 今日博客推荐（1 篇）", content)
        self.assertIn("Recent Blog", blog_section)
        self.assertNotIn("Earlier Blog", blog_section)
        self.assertNotIn("Read Blog", content)
        self.assertNotIn("Stale Blog", content)
        self.assertNotIn("Fresh Paper", content)

    def test_daily_uses_published_date_for_delayed_blog_fetches(self) -> None:
        """Daily reports should include late-fetched blogs on their publication day."""

        delayed_blog = make_artifact(
            title="Delayed Anthropic Blog",
            source_type=SourceType.BLOGS,
            source_name="Anthropic News",
            final_score=0.91,
            relevance_score=0.83,
            published_at=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 3, 11, 2, 0, tzinfo=timezone.utc),
            summary_l3="这是一条延迟抓取但属于目标日期的中文摘要。",
        )

        self._save_artifacts(delayed_blog)

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("Delayed Anthropic Blog", content)
        self.assertIn("这是一条延迟抓取但属于目标日期的中文摘要。", content)

    def test_daily_hides_analyzed_low_relevance_blogs(self) -> None:
        """Daily reports should hide artifacts once LLM relevance marks them as low relevance."""

        self._save_artifacts(
            make_artifact(
                title="Relevant Security Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                final_score=0.80,
                relevance_score=0.60,
                score_breakdown={"llm_relevance_score": 0.6, "llm_relevance_version": "v4"},
            ),
            make_artifact(
                title="Generic AI Product News",
                source_type=SourceType.BLOGS,
                source_name="OpenAI Blog",
                final_score=0.90,
                relevance_score=0.20,
                score_breakdown={"llm_relevance_score": 0.2, "llm_relevance_version": "v4"},
            ),
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("Relevant Security Blog", content)
        self.assertNotIn("Generic AI Product News", content)

    def test_daily_splits_org_arxiv_and_conference_sections(self) -> None:
        """Daily report should mirror dashboard date semantics for org, arXiv, and conference lanes."""

        previous_day = datetime(2026, 3, 9, 11, 0, tzinfo=timezone.utc)
        self._save_artifacts(
            make_artifact(
                title="OpenAI Security Update",
                source_type=SourceType.BLOGS,
                source_name="OpenAI Blog",
                final_score=0.88,
                relevance_score=0.80,
            ),
            make_artifact(
                title="Previous Anthropic Update",
                source_type=SourceType.BLOGS,
                source_name="Anthropic News",
                final_score=0.87,
                relevance_score=0.79,
                created_at=previous_day,
            ),
            make_artifact(
                title="Daily arXiv Paper",
                source_type=SourceType.PAPERS,
                source_name="arXiv",
                source_tier="t2-arxiv",
                final_score=0.86,
                relevance_score=0.78,
            ),
            make_artifact(
                title="Previous arXiv Paper",
                source_type=SourceType.PAPERS,
                source_name="arXiv",
                source_tier="t2-arxiv",
                final_score=0.85,
                relevance_score=0.77,
                created_at=previous_day,
            ),
            make_artifact(
                title="Older DEF CON Topic",
                source_type=SourceType.BLOGS,
                source_name="DEF CON",
                final_score=0.84,
                relevance_score=0.76,
                created_at=previous_day,
                summary_l3="这是一条已经完成中文摘要的 DEF CON 议题。",
                tags=["industry-conference"],
            ),
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")
        org_section = content.split("## 今日组织更新", maxsplit=1)[1].split("## 今日 arXiv", maxsplit=1)[0]
        arxiv_section = content.split("## 今日 arXiv", maxsplit=1)[1].split("## 近期工业会议 topic", maxsplit=1)[0]
        conference_section = content.split("## 近期工业会议 topic", maxsplit=1)[1].split("## 漏洞速报", maxsplit=1)[0]

        self.assertIn("OpenAI Security Update", org_section)
        self.assertNotIn("Previous Anthropic Update", org_section)
        self.assertIn("Daily arXiv Paper", arxiv_section)
        self.assertNotIn("Previous arXiv Paper", arxiv_section)
        self.assertIn("Older DEF CON Topic", conference_section)

    def test_daily_uses_configured_local_day_for_arxiv(self) -> None:
        """UTC evening arXiv papers should belong to the next Asia/Shanghai daily report."""

        self._save_artifacts(
            make_artifact(
                title="Local Day arXiv Paper",
                source_type=SourceType.PAPERS,
                source_name="arXiv",
                source_tier="t2-arxiv",
                final_score=0.86,
                relevance_score=0.78,
                created_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
                published_at=datetime(2026, 7, 1, 17, 46, tzinfo=timezone.utc),
            )
        )

        content = self.generator.generate(date(2026, 7, 2)).read_text(encoding="utf-8")

        arxiv_section = content.split("## 今日 arXiv", maxsplit=1)[1].split("## 近期工业会议 topic", maxsplit=1)[0]
        self.assertIn("Local Day arXiv Paper", arxiv_section)

    def test_daily_prefers_detailed_summary_over_l1_and_raw_abstract(self) -> None:
        """Blog summaries should prefer AI-generated summary_l3 over shorter fallbacks."""

        self._save_artifacts(
            make_artifact(
                title="AI Summary Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                abstract="Raw crawler excerpt.",
                summary_l1="Short AI generated summary.",
                summary_l3="更完整的中文内容总结，说明这篇文章的核心问题、主要发现、涉及的系统以及为什么值得关注。",
                relevance_score=0.81,
            )
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("- **内容总结**: 更完整的中文内容总结，说明这篇文章的核心问题、主要发现、涉及的系统以及为什么值得关注。", content)
        self.assertNotIn("Short AI generated summary.", content)
        self.assertNotIn("Raw crawler excerpt.", content)
        self.assertNotIn("暂无摘要。", content)

    def test_daily_falls_back_to_summary_l1_when_detailed_summary_missing(self) -> None:
        """Existing short summaries should still render when summary_l3 has not been generated."""

        self._save_artifacts(
            make_artifact(
                title="L1 Summary Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                abstract="Raw crawler excerpt.",
                summary_l1="AI generated summary.",
                summary_l3=None,
                relevance_score=0.81,
            )
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("- **内容总结**: AI generated summary.", content)
        self.assertNotIn("Raw crawler excerpt.", content)

    def test_daily_falls_back_to_abstract_when_summary_l1_missing(self) -> None:
        """Raw excerpts should still be used when AI enrichment has not run."""

        self._save_artifacts(
            make_artifact(
                title="Raw Summary Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                abstract="Raw crawler excerpt.",
                summary_l1=None,
                relevance_score=0.81,
            )
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("- **内容总结**: Raw crawler excerpt.", content)
        self.assertNotIn("暂无摘要。", content)

    def test_daily_renders_keywords_for_blog_recommendations(self) -> None:
        """Daily recommendations should expose AI-generated tags as keywords."""

        self._save_artifacts(
            make_artifact(
                title="Tagged Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                tags=["web-security", "agent-security", "vulnerability-research"],
                relevance_score=0.81,
            )
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("- **关键词**: web-security、agent-security、vulnerability-research", content)

    def test_daily_renders_keyword_placeholder_when_tags_missing(self) -> None:
        """Daily recommendations should make missing keywords explicit."""

        self._save_artifacts(
            make_artifact(
                title="Untagged Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                tags=[],
                relevance_score=0.81,
            )
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("- **关键词**: 暂无关键词。", content)

    def test_daily_limits_blog_recommendations_to_five(self) -> None:
        """Daily blog recommendations should cap the visible list at five."""

        self._save_artifacts(
            *[
                make_artifact(
                    title=f"Blog {index}",
                    source_type=SourceType.BLOGS,
                    source_name="PortSwigger Research",
                    final_score=0.99 - (index * 0.01),
                    relevance_score=0.90,
                    created_at=datetime(2026, 3, 10, 10, index, tzinfo=timezone.utc),
                )
                for index in range(7)
            ]
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("## 今日博客推荐（5 篇）", content)
        self.assertIn("Blog 0", content)
        self.assertIn("Blog 4", content)
        self.assertNotIn("Blog 5", content)
        self.assertNotIn("Blog 6", content)

    def test_daily_stats_count_unscored_blogs(self) -> None:
        """Daily stats should count new blogs even when they are not yet scored."""

        self._save_artifacts(
            make_artifact(
                title="Scored Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                final_score=0.88,
                relevance_score=0.75,
            ),
            make_artifact(
                title="Unscored Blog",
                source_type=SourceType.BLOGS,
                source_name="Project Zero",
                final_score=None,
                relevance_score=None,
            ),
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("## 今日博客推荐（1 篇）", content)
        self.assertIn("Scored Blog", content)
        self.assertNotIn("Unscored Blog", content)
        self.assertIn("- 今日新增博客数: 2", content)

    def test_daily_paper_activity_summarizes_new_papers(self) -> None:
        """Paper activity should summarize same-day paper arrivals without listing titles."""

        self._save_artifacts(
            make_artifact(
                title="Daily Paper A",
                source_type=SourceType.PAPERS,
                source_name="IEEE S&P",
                created_at=datetime(2026, 3, 10, 7, 0, tzinfo=timezone.utc),
            ),
            make_artifact(
                title="Daily Paper B",
                source_type=SourceType.PAPERS,
                source_name="USENIX Security",
                created_at=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
            ),
            make_artifact(
                title="Previous Day Paper",
                source_type=SourceType.PAPERS,
                source_name="NDSS",
                created_at=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
            ),
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")
        paper_activity = content.split("## 论文动态", maxsplit=1)[1]

        self.assertIn("> 今日新增 2 篇论文（来源：IEEE S&P、USENIX Security）。详见周报。", content)
        self.assertNotIn("Daily Paper A", paper_activity)
        self.assertNotIn("Daily Paper B", paper_activity)

    def test_daily_paper_activity_truncates_long_source_lists(self) -> None:
        """Paper activity should abbreviate long source lists after three names."""

        self._save_artifacts(
            make_artifact(title="Paper A", source_type=SourceType.PAPERS, source_name="IEEE S&P"),
            make_artifact(title="Paper B", source_type=SourceType.PAPERS, source_name="USENIX Security"),
            make_artifact(title="Paper C", source_type=SourceType.PAPERS, source_name="NDSS"),
            make_artifact(title="Paper D", source_type=SourceType.PAPERS, source_name="ACSAC"),
        )

        content = self.generator.generate(self.target_date).read_text(encoding="utf-8")

        self.assertIn("> 今日新增 4 篇论文（来源：ACSAC、IEEE S&P、NDSS 等）。详见周报。", content)

    def test_daily_file_written_and_idempotent(self) -> None:
        """Daily reports should be written to the expected path and stay stable."""

        self._save_artifacts(
            make_artifact(
                title="Stable Blog",
                source_type=SourceType.BLOGS,
                source_name="PortSwigger Research",
                final_score=0.82,
                relevance_score=0.73,
            )
        )

        first_path = self.generator.generate(self.target_date)
        first_content = first_path.read_text(encoding="utf-8")
        second_path = self.generator.generate(self.target_date)
        second_content = second_path.read_text(encoding="utf-8")

        self.assertEqual(first_path, (self.output_dir / "daily" / "2026-03-10.md").resolve())
        self.assertTrue(first_path.exists())
        self.assertEqual(first_path, second_path)
        self.assertEqual(first_content, second_content)

    def _save_artifacts(self, *artifacts) -> None:
        """Persist artifacts for report-generation tests."""

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for artifact in artifacts:
                repository.save(artifact)
        finally:
            session.close()

    def _mark_as_read(self, artifact) -> None:
        """Persist a read feedback event for an artifact."""

        session: Session = self.session_factory()
        try:
            FeedbackRepository(session).save(
                FeedbackEvent(
                    target_type=FeedbackTargetType.ARTIFACT,
                    target_id=str(artifact.id),
                    feedback_type=FeedbackType.READ,
                    content={"type": "read"},
                )
            )
        finally:
            session.close()
