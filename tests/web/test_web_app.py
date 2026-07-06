"""Tests for the local web console."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.repositories.artifact_repository import ArtifactRepository
from src.web.app import create_app
from src.web.source_admin import SourceTestResult


class WebConsoleTestCase(unittest.TestCase):
    """Route-level tests for the FastAPI console."""

    def setUp(self) -> None:
        """Create an isolated DB and source config."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.config_path = self.workspace / "sources.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": [
                        {
                            "slug": "sample-feed",
                            "name": "Sample Feed",
                            "source_type": "blogs",
                            "tier": "t3-research-blog",
                            "track": "industry",
                            "adapter": "rss",
                            "enabled": False,
                            "aliases": [],
                            "urls": {"rss": "https://example.com/feed.xml"},
                            "tags": ["sample"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        engine = create_database_engine(f"sqlite+pysqlite:///{self.workspace / 'test.db'}")
        create_all_tables(engine)
        self.engine = engine
        self.session_factory = create_session_factory(engine)
        self.client = TestClient(
            create_app(
                session_factory=self.session_factory,
                source_config_path=self.config_path,
            )
        )

    def tearDown(self) -> None:
        """Dispose test resources."""

        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_dashboard_renders(self) -> None:
        """Dashboard should render the local console shell."""

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Research intelligence workspace", response.text)
        self.assertIn("app.css?v=20260706-dashboard-search", response.text)
        self.assertIn("Daily intelligence paper", response.text)
        self.assertIn("data-sidebar-toggle", response.text)
        self.assertIn("rr-sidebar-collapsed", response.text)
        self.assertIn("Academic", response.text)
        self.assertIn("Industry", response.text)
        self.assertIn("Refresh today", response.text)
        self.assertIn("data-refresh-status", response.text)
        self.assertIn("/dashboard/refresh-status", response.text)
        self.assertNotIn("Run pipeline", response.text)
        self.assertNotIn("Manage sources", response.text)
        self.assertNotIn("Provider status", response.text)
        self.assertNotIn("Configuration status", response.text)
        self.assertNotIn("API key", response.text)

    def test_dashboard_refresh_today_starts_daily_refresh(self) -> None:
        """Dashboard refresh action should start the standard daily refresh chain."""

        with patch("src.web.app._run_daily_refresh") as refresh:
            response = self.client.post("/dashboard/refresh-today", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertIn("/dashboard?date=", response.headers["location"])
        self.assertIn("notice=", response.headers["location"])
        refresh.assert_called_once()
        self.assertFalse(refresh.call_args.kwargs["skip_crawl"])
        self.assertEqual(refresh.call_args.kwargs["crawl_scope"], "daily")
        self.assertEqual(refresh.call_args.kwargs["artifact_scope"], "daily")
        self.assertEqual(refresh.call_args.kwargs["max_llm_items"], 30)

        notice_response = self.client.get(response.headers["location"])
        self.assertEqual(notice_response.status_code, 200)
        self.assertIn("Started lightweight daily refresh for today", notice_response.text)

        status_response = self.client.get("/dashboard/refresh-status")
        self.assertEqual(status_response.status_code, 200)
        status = status_response.json()
        self.assertEqual(status["state"], "complete")
        self.assertEqual(status["progress"], 100)

    def test_dashboard_prefers_detailed_summary(self) -> None:
        """Dashboard artifact cards should show summary_l3 when available."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="Detailed Blog",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Example Blog",
                    source_url="https://example.com/blog",
                    abstract="Raw excerpt.",
                    summary_l1="Short summary.",
                    summary_l3="中文详细内容总结，概括文章的核心问题、主要内容和为什么值得关注。",
                    tags=["web-security"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("中文详细内容总结", response.text)
        self.assertNotIn("Short summary.", response.text)

    def test_dashboard_hides_unprocessed_conference_items(self) -> None:
        """Dashboard should not show raw conference items before analysis."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="Raw Conference Session",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Black Hat USA",
                    source_url="https://www.blackhat.com/us-26/briefings/schedule/index.html",
                    abstract="Black Hat USA 2026. Time: Wednesday, August 5.",
                    tags=["industry-conference", "security-conference", "Identity"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Raw Conference Session", response.text)
        self.assertNotIn("Black Hat USA 2026. Time", response.text)

    def test_dashboard_search_filters_cards(self) -> None:
        """Dashboard search should filter cards while keeping range controls usable."""

        base_time = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for title, summary, focus in (
                ("Kernel Fuzzing Paper", "这篇论文讨论 kernel fuzzing 调度与漏洞触发。", "kernel fuzzing"),
                ("Prompt Injection Paper", "这篇论文讨论 prompt injection 攻击。", "prompt injection"),
            ):
                repository.save(
                    Artifact(
                        title=title,
                        authors=[],
                        year=2026,
                        source_type=SourceType.PAPERS,
                        source_tier="t1-conference",
                        source_name="USENIX Security",
                        source_url=f"https://example.com/{title.lower().replace(' ', '-')}",
                        published_at=base_time,
                        summary_l3=summary,
                        tags=["security"],
                        score_breakdown={
                            "academic_relevance_judged": True,
                            "academic_relevance_relevant": True,
                            "academic_relevance_score": 0.9,
                            "academic_relevance_min_score": 0.6,
                            "academic_focus_labels": [focus],
                        },
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.9,
                    )
                )
        finally:
            session.close()

        default_response = self.client.get("/dashboard?range=7d")
        search_response = self.client.get("/dashboard?range=7d&q=fuzzing")

        self.assertEqual(default_response.status_code, 200)
        self.assertIn("Kernel Fuzzing Paper", default_response.text)
        self.assertIn("Prompt Injection Paper", default_response.text)
        self.assertIn('name="q"', default_response.text)

        self.assertEqual(search_response.status_code, 200)
        self.assertIn('value="fuzzing"', search_response.text)
        self.assertIn("Kernel Fuzzing Paper", search_response.text)
        self.assertNotIn("Prompt Injection Paper", search_response.text)
        self.assertIn("/dashboard?range=today&q=fuzzing", search_response.text)
        self.assertIn("/dashboard?range=7d&q=fuzzing", search_response.text)

    def test_paper_cards_prefer_detailed_chinese_summary(self) -> None:
        """Paper cards should prefer summary_l3 when a Chinese detailed summary exists."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="Concise Paper",
                    authors=["Alice Example"],
                    year=2026,
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00001",
                    abstract="English abstract should not be shown when a Chinese summary exists.",
                    summary_l1="这篇论文聚焦于 fuzzing 调度策略，讨论如何在有限预算下选择更有效的测试目标。",
                    summary_l3="这是一段更长的中文详细总结，包含更多背景、方法、实验设置和潜在影响，应作为论文卡片的主要摘要展示。",
                    tags=["fuzzing"],
                    score_breakdown={
                        "zotero_relevance_evaluated": True,
                        "zotero_similarity": 0.3,
                        "zotero_min_similarity": 0.18,
                        "academic_relevance_judged": True,
                        "academic_relevance_relevant": True,
                        "academic_relevance_score": 0.82,
                        "academic_relevance_min_score": 0.6,
                        "academic_quality_evaluated": True,
                        "academic_quality_score": 0.85,
                    },
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
        finally:
            session.close()

        response = self.client.get("/artifacts?track=academic")

        self.assertEqual(response.status_code, 200)
        self.assertIn("这是一段更长的中文详细总结", response.text)
        self.assertNotIn("这篇论文聚焦于 fuzzing 调度策略", response.text)
        self.assertNotIn("English abstract should not be shown", response.text)

    def test_paper_cards_use_focus_labels_when_chinese_summary_missing(self) -> None:
        """Paper cards should not expose English abstracts when focus labels exist."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="English Only Paper",
                    authors=["Alice Example"],
                    year=2026,
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00002",
                    abstract="This English abstract should stay out of the card summary.",
                    tags=["fuzzing"],
                    score_breakdown={
                        "academic_focus_labels": ["fuzzing 调度策略", "状态覆盖优化"],
                        "zotero_relevance_evaluated": True,
                        "zotero_similarity": 0.3,
                        "zotero_min_similarity": 0.18,
                        "academic_relevance_judged": True,
                        "academic_relevance_relevant": True,
                        "academic_relevance_score": 0.82,
                        "academic_relevance_min_score": 0.6,
                        "academic_quality_evaluated": True,
                        "academic_quality_score": 0.85,
                    },
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
        finally:
            session.close()

        response = self.client.get("/artifacts?track=academic")

        self.assertEqual(response.status_code, 200)
        self.assertIn("研究焦点：fuzzing 调度策略、状态覆盖优化。", response.text)
        self.assertNotIn("This English abstract should stay out", response.text)

    def test_dashboard_splits_industry_sections(self) -> None:
        """Industry dashboard should split conferences, blogs, and organization updates."""

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for title, source_name in (
                ("Black Hat Topic", "Black Hat USA"),
                ("Project Zero Article", "Google Project Zero"),
                ("OpenAI Update", "OpenAI Blog"),
            ):
                repository.save(
                    Artifact(
                        title=title,
                        authors=[],
                        year=2026,
                        source_type=SourceType.BLOGS,
                        source_tier="t3-research-blog",
                        source_name=source_name,
                        source_url=f"https://example.com/{title.lower().replace(' ', '-')}",
                        abstract="Raw excerpt.",
                        summary_l3=f"{title} detailed summary.",
                        tags=["web-security"],
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.9,
                    )
                )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Industry conferences", response.text)
        self.assertIn("Research blogs", response.text)
        self.assertIn("Organizations", response.text)
        self.assertIn("Black Hat Topic", response.text)
        self.assertIn("Project Zero Article", response.text)
        self.assertIn("OpenAI Update", response.text)

    def test_dashboard_date_filter_applies_to_blogs_orgs_and_arxiv(self) -> None:
        """Dashboard date control should filter blogs, orgs, and arXiv while keeping conferences visible."""

        selected_day = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
        previous_day = selected_day - timedelta(days=1)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for title, source_name, source_type, published_at in (
                ("Today Blog Signal", "Project Zero", SourceType.BLOGS, selected_day),
                ("Yesterday Blog Signal", "Project Zero", SourceType.BLOGS, previous_day),
                ("Today OpenAI Update", "OpenAI Blog", SourceType.BLOGS, selected_day),
                ("Yesterday OpenAI Update", "OpenAI Blog", SourceType.BLOGS, previous_day),
                ("Older Black Hat Topic", "Black Hat USA", SourceType.BLOGS, previous_day),
                ("Today arXiv Paper", "arXiv", SourceType.PAPERS, selected_day),
                ("Yesterday arXiv Paper", "arXiv", SourceType.PAPERS, previous_day),
                ("Older USENIX Paper", "USENIX Security", SourceType.PAPERS, previous_day),
            ):
                is_arxiv = source_name == "arXiv"
                repository.save(
                    Artifact(
                        title=title,
                        authors=[],
                        year=2026,
                        source_type=source_type,
                        source_tier=(
                            "t3-research-blog"
                            if source_type == SourceType.BLOGS
                            else "t2-arxiv"
                            if is_arxiv
                            else "t1-conference"
                        ),
                        source_name=source_name,
                        source_url=f"https://example.com/{title.lower().replace(' ', '-')}",
                        published_at=published_at,
                        abstract="Raw excerpt.",
                        summary_l3=f"{title} detailed summary.",
                        tags=["security"],
                        score_breakdown=(
                            {
                                "academic_relevance_judged": True,
                                "academic_relevance_relevant": True,
                                "academic_relevance_score": 0.9,
                                "academic_relevance_min_score": 0.6,
                            }
                            if source_type == SourceType.PAPERS and not is_arxiv
                            else {}
                        ),
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.9,
                    )
                )
        finally:
            session.close()

        response = self.client.get("/dashboard?date=2026-07-02")

        self.assertEqual(response.status_code, 200)
        self.assertIn('value="2026-07-02"', response.text)
        self.assertIn("Custom date", response.text)
        self.assertIn(">Custom</span>", response.text)
        self.assertIn("Today Blog Signal", response.text)
        self.assertNotIn("Yesterday Blog Signal", response.text)
        self.assertIn("Today OpenAI Update", response.text)
        self.assertNotIn("Yesterday OpenAI Update", response.text)
        self.assertIn("Today arXiv Paper", response.text)
        self.assertNotIn("Yesterday arXiv Paper", response.text)
        self.assertIn("Older Black Hat Topic", response.text)
        self.assertIn("Older USENIX Paper", response.text)

    def test_dashboard_seven_day_range_filters_daily_lanes(self) -> None:
        """Dashboard 7 day mode should include recent daily items and exclude older daily items."""

        today = datetime.now(timezone.utc)
        recent_day = today - timedelta(days=2)
        older_day = today - timedelta(days=9)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for title, source_name, source_type, published_at in (
                ("Recent Blog Signal", "Project Zero", SourceType.BLOGS, recent_day),
                ("Old Blog Signal", "Project Zero", SourceType.BLOGS, older_day),
                ("Recent OpenAI Update", "OpenAI Blog", SourceType.BLOGS, recent_day),
                ("Old OpenAI Update", "OpenAI Blog", SourceType.BLOGS, older_day),
                ("Recent arXiv Paper", "arXiv", SourceType.PAPERS, recent_day),
                ("Old arXiv Paper", "arXiv", SourceType.PAPERS, older_day),
                ("Old Black Hat Topic", "Black Hat USA", SourceType.BLOGS, older_day),
                ("Old USENIX Paper", "USENIX Security", SourceType.PAPERS, older_day),
            ):
                is_arxiv = source_name == "arXiv"
                repository.save(
                    Artifact(
                        title=title,
                        authors=[],
                        year=2026,
                        source_type=source_type,
                        source_tier=(
                            "t3-research-blog"
                            if source_type == SourceType.BLOGS
                            else "t2-arxiv"
                            if is_arxiv
                            else "t1-conference"
                        ),
                        source_name=source_name,
                        source_url=f"https://example.com/{title.lower().replace(' ', '-')}",
                        published_at=published_at,
                        abstract="Raw excerpt.",
                        summary_l3=f"{title} detailed summary.",
                        tags=["security"],
                        score_breakdown=(
                            {
                                "academic_relevance_judged": True,
                                "academic_relevance_relevant": True,
                                "academic_relevance_score": 0.9,
                                "academic_relevance_min_score": 0.6,
                            }
                            if source_type == SourceType.PAPERS and not is_arxiv
                            else {}
                        ),
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.9,
                    )
                )
        finally:
            session.close()

        response = self.client.get("/dashboard?range=7d")

        self.assertEqual(response.status_code, 200)
        self.assertIn(">7 days</a>", response.text)
        self.assertIn("Recent Blog Signal", response.text)
        self.assertNotIn("Old Blog Signal", response.text)
        self.assertIn("Recent OpenAI Update", response.text)
        self.assertNotIn("Old OpenAI Update", response.text)
        self.assertIn("Recent arXiv Paper", response.text)
        self.assertNotIn("Old arXiv Paper", response.text)
        self.assertIn("Old Black Hat Topic", response.text)
        self.assertIn("Old USENIX Paper", response.text)

    def test_dashboard_date_filter_uses_configured_local_day(self) -> None:
        """UTC evening arXiv papers should appear on the next Asia/Shanghai dashboard day."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="Local Day arXiv Paper",
                    authors=[],
                    year=2026,
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.01209",
                    published_at=datetime(2026, 7, 1, 17, 46, tzinfo=timezone.utc),
                    created_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
                    abstract="A security paper published in the UTC evening.",
                    summary_l3="本地日期边界测试摘要。",
                    tags=["security"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard?date=2026-07-02")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Local Day arXiv Paper", response.text)

    def test_dashboard_hides_analyzed_low_relevance_artifacts(self) -> None:
        """Dashboard should hide artifacts marked as low relevance by LLM analysis."""

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            repository.save(
                Artifact(
                    title="Generic AI Product News",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="OpenAI Blog",
                    source_url="https://example.com/generic-ai",
                    abstract="Generic product adoption update.",
                    summary_l3="Generic product adoption update.",
                    tags=["frontier-ai"],
                    score_breakdown={"llm_relevance_score": 0.2, "llm_relevance_version": "v4"},
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
            repository.save(
                Artifact(
                    title="Security Relevant Update",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Project Zero",
                    source_url="https://example.com/security",
                    abstract="Security research update.",
                    summary_l3="Security research update.",
                    tags=["vulnerability-research"],
                    score_breakdown={"llm_relevance_score": 0.6, "llm_relevance_version": "v4"},
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Security Relevant Update", response.text)
        self.assertNotIn("Generic AI Product News", response.text)

    def test_academic_cards_render_evidence_chips(self) -> None:
        """Academic cards should surface topics, Zotero matches, and quality evidence."""

        session = self.session_factory()
        try:
            ArtifactRepository(session).save(
                Artifact(
                    title="Prompt Injection Vulnerability Paper",
                    authors=["Alice Example"],
                    year=2026,
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00001",
                    summary_l3="这篇论文总结提示注入风险。",
                    tags=["prompt-injection"],
                    score_breakdown={
                        "zotero_relevance_evaluated": True,
                        "zotero_similarity": 0.32,
                        "zotero_min_similarity": 0.18,
                        "academic_relevance_judged": True,
                        "academic_relevance_relevant": True,
                        "academic_relevance_score": 0.82,
                        "academic_relevance_min_score": 0.6,
                        "academic_relevance_reason": "候选论文与 Zotero 证据都聚焦提示注入风险。",
                        "academic_focus_labels": ["prompt injection 防护", "LLM agent 工具调用"],
                        "zotero_matches": [
                            {
                                "title": "Prompt Injection Defenses for Tool-Using LLM Agents",
                                "score": 0.32,
                                "topics": ["llm-security", "agent-security"],
                            }
                        ],
                        "academic_quality_evaluated": True,
                        "academic_quality_score": 0.85,
                        "academic_quality_min_for_arxiv": 0.5,
                        "academic_quality_signals": {
                            "matched_faculty": [
                                {
                                    "name": "Alice Example",
                                    "affiliation": "Example University Security Lab",
                                }
                            ]
                        },
                    },
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
        finally:
            session.close()

        response = self.client.get("/artifacts?track=academic")

        self.assertEqual(response.status_code, 200)
        self.assertIn("prompt injection 防护", response.text)
        self.assertIn("LLM agent 工具调用", response.text)
        self.assertIn("相关度 0.82", response.text)
        self.assertIn("候选论文与 Zotero 证据都聚焦提示注入风险。", response.text)
        self.assertNotIn("Zotero match", response.text)
        self.assertNotIn("Top Zotero cosine similarity", response.text)
        self.assertNotIn(">Zotero 0.32<", response.text)
        self.assertNotIn("Zotero: llm-security", response.text)
        self.assertIn("CSRankings: Alice Example", response.text)
        self.assertIn("Group: Example University Security Lab", response.text)

    def test_dashboard_candidate_pool_keeps_industry_visible_after_paper_batch(self) -> None:
        """Large paper batches should not crowd industry items out of the dashboard."""

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            repository.save(
                Artifact(
                    title="Earlier Industry Signal",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Project Zero",
                    source_url="https://example.com/industry",
                    summary_l3="Industry security research summary.",
                    tags=["vulnerability-research"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
            for index in range(30):
                repository.save(
                    Artifact(
                        title=f"arXiv Paper {index}",
                        authors=[],
                        year=2026,
                        source_type=SourceType.PAPERS,
                        source_tier="t2-arxiv",
                        source_name="arXiv",
                        source_url=f"https://arxiv.org/abs/2607.{index:05d}",
                        summary_l3="Academic paper summary.",
                        tags=["preprint"],
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.6,
                    )
                )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Earlier Industry Signal", response.text)

    def test_dashboard_candidate_pool_uses_created_time_when_published_time_missing(self) -> None:
        """Recent conference talks without published_at should not fall behind all dated papers."""

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            repository.save(
                Artifact(
                    title="Recent DEF CON Talk",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="DEF CON",
                    source_url="https://defcon.org/html/defcon-33/dc-33-speakers.html#content_1",
                    summary_l3="Conference talk summary.",
                    tags=["industry-conference", "security-conference"],
                    external_ids={"conference": "DEF CON 33"},
                    score_breakdown={"llm_relevance_score": 0.8, "llm_relevance_version": "v5-security-filter"},
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
            for index in range(180):
                repository.save(
                    Artifact(
                        title=f"Older Dated Paper {index}",
                        authors=[],
                        year=2026,
                        source_type=SourceType.PAPERS,
                        source_tier="t1-conference",
                        source_name="USENIX Security",
                        source_url=f"https://example.com/paper-{index}",
                        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        summary_l3="Paper summary.",
                        tags=["security"],
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.8,
                    )
                )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Recent DEF CON Talk", response.text)
        self.assertIn("DEF CON 33", response.text)

    def test_dashboard_conference_lane_keeps_multiple_sources_visible(self) -> None:
        """Conference lane should not let one source crowd out all other conferences."""

        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for index in range(8):
                repository.save(
                    Artifact(
                        title=f"High DEF CON Talk {index}",
                        authors=[],
                        year=2026,
                        source_type=SourceType.BLOGS,
                        source_tier="t3-research-blog",
                        source_name="DEF CON",
                        source_url=f"https://defcon.org/talk-{index}",
                        summary_l3="DEF CON summary.",
                        tags=["industry-conference", "security-conference"],
                        external_ids={"conference": "DEF CON 33"},
                        score_breakdown={"llm_relevance_score": 0.8, "llm_relevance_version": "v5-security-filter"},
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.95 - (index * 0.01),
                    )
                )
            repository.save(
                Artifact(
                    title="Not My Vibe: When AI Coding Agents Go Off the Rails",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="BSidesSF",
                    source_url="https://www.youtube.com/watch?v=ES2oO6Md9g4",
                    summary_l3="BSidesSF AI coding agent summary.",
                    tags=["industry-conference", "security-conference", "bsidessf-2026"],
                    external_ids={"conference": "BSidesSF 2026"},
                    score_breakdown={"llm_relevance_score": 0.6, "llm_relevance_version": "v5-security-filter"},
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.79,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("High DEF CON Talk 0", response.text)
        self.assertIn("Not My Vibe: When AI Coding Agents Go Off the Rails", response.text)
        self.assertIn("BSidesSF 2026", response.text)

    def test_dashboard_orders_items_by_published_time(self) -> None:
        """Dashboard should prefer published_at ordering over insertion ordering."""

        base_time = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            repository.save(
                Artifact(
                    title="Newer Published Item",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Project Zero",
                    source_url="https://example.com/newer-published",
                    published_at=base_time,
                    summary_l3="Newer summary.",
                    tags=["security"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
            repository.save(
                Artifact(
                    title="Older Published Item",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="Project Zero",
                    source_url="https://example.com/older-published",
                    published_at=base_time - timedelta(hours=2),
                    summary_l3="Older summary.",
                    tags=["security"],
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.8,
                )
            )
        finally:
            session.close()

        response = self.client.get("/dashboard?date=2026-07-01")

        self.assertEqual(response.status_code, 200)
        self.assertLess(response.text.index("Newer Published Item"), response.text.index("Older Published Item"))

    def test_artifacts_are_time_ordered_and_paginated(self) -> None:
        """Artifact browser should show SQLite-backed time pages in descending order."""

        base_time = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for index in range(25):
                repository.save(
                    Artifact(
                        title=f"Visible Artifact {index:02d}",
                        authors=[],
                        year=2026,
                        source_type=SourceType.BLOGS,
                        source_tier="t3-research-blog",
                        source_name="Project Zero",
                        source_url=f"https://example.com/visible-{index}",
                        published_at=base_time - timedelta(minutes=index),
                        summary_l3=f"Visible summary {index}.",
                        tags=["security"],
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.8,
                    )
                )
            repository.save(
                Artifact(
                    title="Hidden Low Relevance Artifact",
                    authors=[],
                    year=2026,
                    source_type=SourceType.BLOGS,
                    source_tier="t3-research-blog",
                    source_name="OpenAI Blog",
                    source_url="https://example.com/hidden",
                    published_at=base_time + timedelta(minutes=1),
                    summary_l3="Low relevance summary.",
                    tags=["frontier-ai"],
                    score_breakdown={"llm_relevance_score": 0.2},
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
        finally:
            session.close()

        first_page = self.client.get("/artifacts?track=industry")
        second_page = self.client.get("/artifacts?track=industry&page=2")

        self.assertEqual(first_page.status_code, 200)
        self.assertIn("Showing 1-20 of 25", first_page.text)
        self.assertIn("Page 1 / 2", first_page.text)
        self.assertIn("Visible Artifact 00", first_page.text)
        self.assertIn("Visible Artifact 19", first_page.text)
        self.assertNotIn("Visible Artifact 20", first_page.text)
        self.assertNotIn("Hidden Low Relevance Artifact", first_page.text)

        self.assertEqual(second_page.status_code, 200)
        self.assertIn("Showing 21-25 of 25", second_page.text)
        self.assertIn("Page 2 / 2", second_page.text)
        self.assertIn("Visible Artifact 20", second_page.text)
        self.assertIn("Visible Artifact 24", second_page.text)
        self.assertNotIn("Visible Artifact 19", second_page.text)

    def test_artifacts_search_filters_displayable_items(self) -> None:
        """Artifact browser search should filter displayable items and keep pagination params."""

        base_time = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            for index in range(22):
                repository.save(
                    Artifact(
                        title=f"Prompt Injection Artifact {index:02d}",
                        authors=[],
                        year=2026,
                        source_type=SourceType.PAPERS,
                        source_tier="t2-arxiv",
                        source_name="arXiv",
                        source_url=f"https://example.com/prompt-{index}",
                        published_at=base_time - timedelta(minutes=index),
                        summary_l3=f"这篇论文讨论 prompt injection 防护与工具调用边界 {index}。",
                        tags=["prompt-injection"],
                        status=ArtifactStatus.ACTIVE,
                        final_score=0.8,
                    )
                )
            repository.save(
                Artifact(
                    title="Firmware Fuzzing Artifact",
                    authors=[],
                    year=2026,
                    source_type=SourceType.PAPERS,
                    source_tier="t1-conference",
                    source_name="USENIX Security",
                    source_url="https://example.com/fuzzing",
                    published_at=base_time + timedelta(minutes=1),
                    summary_l3="这篇论文讨论 IoT 固件 fuzzing。",
                    tags=["fuzzing"],
                    score_breakdown={
                        "academic_relevance_judged": True,
                        "academic_relevance_relevant": True,
                        "academic_relevance_score": 0.9,
                        "academic_focus_labels": ["固件 fuzzing"],
                    },
                    status=ArtifactStatus.ACTIVE,
                    final_score=0.9,
                )
            )
        finally:
            session.close()

        default_response = self.client.get("/artifacts?track=academic")
        search_response = self.client.get("/artifacts?track=academic&q=fuzzing")

        self.assertEqual(default_response.status_code, 200)
        self.assertIn("Prompt Injection Artifact 00", default_response.text)
        self.assertIn("Search", default_response.text)
        self.assertIn('name="q"', default_response.text)

        self.assertEqual(search_response.status_code, 200)
        self.assertIn('value="fuzzing"', search_response.text)
        self.assertIn("Showing 1-1 of 1", search_response.text)
        self.assertIn("Firmware Fuzzing Artifact", search_response.text)
        self.assertNotIn("Prompt Injection Artifact 00", search_response.text)

        paged_search = self.client.get("/artifacts?track=academic&q=prompt")
        self.assertIn("Showing 1-20 of 22", paged_search.text)
        self.assertIn("/artifacts?track=academic&page=2&amp;q=prompt", paged_search.text)

    def test_create_source_defaults_disabled(self) -> None:
        """New web-created sources should not become enabled until tested and toggled."""

        response = self.client.post(
            "/sources",
            data={
                "slug": "new-blog",
                "name": "New Blog",
                "source_type": "blogs",
                "adapter": "webpage",
                "url_listing": "https://example.com/blog",
                "tags": "ai-security, research-blog",
                "include_url_prefixes": "https://example.com/blog/",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        created = next(source for source in payload["sources"] if source["slug"] == "new-blog")
        self.assertEqual(created["name"], "New Blog")
        self.assertFalse(created["enabled"])
        self.assertEqual(created["urls"]["listing"], "https://example.com/blog")
        self.assertEqual(created["tags"], ["ai-security", "research-blog"])

    def test_toggle_source(self) -> None:
        """The source toggle endpoint should flip enabled state."""

        response = self.client.post("/sources/sample-feed/toggle", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        source = payload["sources"][0]
        self.assertTrue(source["enabled"])

    def test_source_test_result_renders(self) -> None:
        """Source test results should show sample item titles."""

        result = SourceTestResult(
            ok=True,
            message="Fetched 1 items from Sample Feed",
            items=[{"title": "Sample result", "published_at": "2026-07-01"}],
        )
        with patch("src.web.app.test_source_fetch", return_value=result):
            response = self.client.post("/sources/sample-feed/test")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Fetched 1 items from Sample Feed", response.text)
        self.assertIn("Sample result", response.text)
