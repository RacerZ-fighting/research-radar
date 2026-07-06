"""Daily markdown report generation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.reporting.base import BaseReportGenerator
from src.reporting.relevance_filter import should_display_artifact
from src.reporting.renderer import format_date, truncate
from src.timezone import local_date

RECENT_SIGNAL_DAYS = 7
BLOG_RECOMMENDATION_LIMIT = 5
DAILY_SECTION_LIMIT = 8
SUMMARY_MAX_LENGTH = 900
ORG_SOURCE_MARKERS = ("openai", "anthropic")
CONFERENCE_SOURCE_MARKERS = ("black hat", "blackhat", "def con", "defcon", "bsides")


class DailyReportGenerator(BaseReportGenerator):
    """Generate a daily markdown report."""

    def generate(self, target_date: date) -> Path:
        """Generate and write the daily report for one UTC day."""

        day_start, day_end = self._day_range(target_date)
        recent_window_start = day_start - timedelta(days=RECENT_SIGNAL_DAYS - 1)
        read_artifact_ids = self._load_read_artifact_ids()
        recent_scored_artifacts = self._load_scored_artifacts(recent_window_start, day_end)
        display_artifacts = [
            artifact
            for artifact in recent_scored_artifacts
            if artifact.id not in read_artifact_ids and should_display_artifact(artifact)
        ]
        blog_recommendations = [
            artifact
            for artifact in display_artifacts
            if artifact.source_type == SourceType.BLOGS
            and self._matches_day(artifact, target_date)
            and not self._is_organization_update(artifact)
            and not self._is_industry_conference(artifact)
        ][:BLOG_RECOMMENDATION_LIMIT]
        organization_updates = [
            artifact
            for artifact in display_artifacts
            if artifact.source_type == SourceType.BLOGS
            and self._matches_day(artifact, target_date)
            and self._is_organization_update(artifact)
        ][:DAILY_SECTION_LIMIT]
        arxiv_papers = [
            artifact
            for artifact in display_artifacts
            if artifact.source_type == SourceType.PAPERS
            and self._is_arxiv_paper(artifact)
            and self._matches_day(artifact, target_date)
        ][:DAILY_SECTION_LIMIT]
        conference_topics = [
            artifact
            for artifact in display_artifacts
            if artifact.source_type == SourceType.BLOGS and self._is_industry_conference(artifact)
        ][:DAILY_SECTION_LIMIT]
        metadata = self._load_daily_metadata(day_start, day_end)

        context = {
            "target_date": target_date,
            "generated_at": self._current_time(),
            "blog_recommendations": blog_recommendations,
            "organization_updates": organization_updates,
            "arxiv_papers": arxiv_papers,
            "conference_topics": conference_topics,
            "paper_count": metadata["paper_count"],
            "paper_sources": metadata["paper_sources"],
            "daily_blog_count": metadata["daily_blog_count"],
            "database_total": metadata["database_total"],
        }

        return self._write_report("daily", f"{target_date.isoformat()}.md", self.render(context))

    def render(self, context: dict) -> str:
        """Render the daily report into markdown."""

        target_date = context["target_date"]
        generated_at = context["generated_at"]
        blog_recommendations: list[Artifact] = context["blog_recommendations"]
        organization_updates: list[Artifact] = context["organization_updates"]
        arxiv_papers: list[Artifact] = context["arxiv_papers"]
        conference_topics: list[Artifact] = context["conference_topics"]
        paper_count: int = context["paper_count"]
        paper_sources: list[str] = context["paper_sources"]
        daily_blog_count: int = context["daily_blog_count"]
        database_total: int = context["database_total"]

        lines = [
            "# Research Radar - 日报",
            f"**日期**: {target_date.isoformat()}",
            f"**生成时间**: {generated_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            f"## 今日博客推荐（{len(blog_recommendations)} 篇）",
        ]

        lines.extend(self._render_artifact_list(blog_recommendations, empty_text="暂无符合条件的博客推荐。"))

        lines.extend(
            [
                "",
                "---",
                "",
                f"## 今日组织更新（{len(organization_updates)} 篇）",
            ]
        )
        lines.extend(self._render_artifact_list(organization_updates, empty_text="暂无 OpenAI / Anthropic 等组织更新。"))

        lines.extend(
            [
                "",
                "---",
                "",
                f"## 今日 arXiv（{len(arxiv_papers)} 篇）",
            ]
        )
        lines.extend(self._render_artifact_list(arxiv_papers, empty_text="暂无符合条件的 arXiv 论文。"))

        lines.extend(
            [
                "",
                "---",
                "",
                f"## 近期工业会议 topic（{len(conference_topics)} 条）",
            ]
        )
        lines.extend(self._render_artifact_list(conference_topics, empty_text="暂无近期工业会议 topic。"))

        lines.extend(
            [
                "",
                "---",
                "",
                "## 漏洞速报",
                "",
                "暂无漏洞数据源",
                "",
                "---",
                "",
                "## 论文动态",
                "",
                self._render_paper_activity(paper_count, paper_sources),
                "",
                "---",
                "",
                "## 统计",
                f"- 今日新增博客数: {daily_blog_count}",
                f"- 今日 arXiv 展示数: {len(arxiv_papers)}",
                f"- 数据库总量: {database_total}",
            ]
        )
        return "\n".join(lines)

    def _load_daily_metadata(self, start: datetime, end: datetime) -> dict[str, object]:
        """Load non-recommendation daily counters and paper source names."""

        session = self.session_factory()
        try:
            base_filters = (
                Artifact.created_at >= start,
                Artifact.created_at < end,
                Artifact.status == ArtifactStatus.ACTIVE,
            )
            paper_count = int(
                session.scalar(
                    select(func.count(Artifact.id)).where(
                        *base_filters,
                        Artifact.source_type == SourceType.PAPERS,
                    )
                )
                or 0
            )
            daily_blog_count = int(
                session.scalar(
                    select(func.count(Artifact.id)).where(
                        *base_filters,
                        Artifact.source_type == SourceType.BLOGS,
                    )
                )
                or 0
            )
            database_total = int(
                session.scalar(
                    select(func.count(Artifact.id)).where(Artifact.status == ArtifactStatus.ACTIVE)
                )
                or 0
            )
            source_statement = (
                select(Artifact.source_name)
                .where(
                    *base_filters,
                    Artifact.source_type == SourceType.PAPERS,
                )
                .distinct()
                .order_by(Artifact.source_name.asc())
            )
            paper_sources = [source_name for source_name in session.scalars(source_statement) if source_name]
            return {
                "paper_count": paper_count,
                "paper_sources": paper_sources,
                "daily_blog_count": daily_blog_count,
                "database_total": database_total,
            }
        finally:
            session.close()

    def _render_paper_activity(self, paper_count: int, paper_sources: list[str]) -> str:
        """Render the paper activity callout block."""

        if paper_count <= 0:
            return "> 今日无论文更新。"
        visible_sources = paper_sources[:3]
        source_text = "、".join(visible_sources) if visible_sources else "未知来源"
        if len(paper_sources) > len(visible_sources):
            source_text = f"{source_text} 等"
        return f"> 今日新增 {paper_count} 篇论文（来源：{source_text}）。详见周报。"

    def _render_artifact_list(self, artifacts: list[Artifact], *, empty_text: str) -> list[str]:
        """Render a numbered artifact list section."""

        if not artifacts:
            return ["", empty_text]

        lines: list[str] = []
        for rank, artifact in enumerate(artifacts, start=1):
            lines.extend(
                [
                    "",
                    f"### {rank}. {artifact.title}",
                    f"- **来源**: {artifact.source_name or 'Unknown'}",
                    f"- **发布**: {format_date(artifact.published_at, artifact.year)}",
                    f"- **相关度**: {(artifact.relevance_score or 0.0):.2f}",
                    f"- **URL**: {artifact.paper_url or artifact.source_url}",
                    f"- **内容总结**: {self._render_summary(artifact)}",
                    f"- **关键词**: {self._render_keywords(artifact)}",
                ]
            )
        return lines

    def _render_summary(self, artifact: Artifact) -> str:
        """Return the preferred summary text for one daily artifact."""

        summary = artifact.summary_l3 or artifact.summary_l1 or artifact.abstract
        if not summary:
            return "暂无摘要。"
        return truncate(summary.strip(), SUMMARY_MAX_LENGTH)

    def _render_keywords(self, artifact: Artifact) -> str:
        """Return display-ready keyword tags for a blog recommendation."""

        tags = [str(tag).strip() for tag in artifact.tags or [] if str(tag).strip()]
        if not tags:
            return "暂无关键词。"
        return "、".join(tags)

    def _matches_day(self, artifact: Artifact, target_date: date) -> bool:
        """Return whether the artifact belongs to the target report day."""

        timestamp = artifact.published_at or artifact.created_at
        return local_date(timestamp) == target_date

    def _is_arxiv_paper(self, artifact: Artifact) -> bool:
        """Return whether one paper is an arXiv item."""

        return (artifact.source_tier or "").lower() == "t2-arxiv" or "arxiv" in self._source_key(artifact)

    def _is_organization_update(self, artifact: Artifact) -> bool:
        """Return whether one blog item is an organization update."""

        source_key = self._source_key(artifact)
        return any(marker in source_key for marker in ORG_SOURCE_MARKERS)

    def _is_industry_conference(self, artifact: Artifact) -> bool:
        """Return whether one blog item is an industry conference topic."""

        source_key = self._source_key(artifact)
        tag_keys = {str(tag).strip().lower() for tag in artifact.tags or []}
        return "industry-conference" in tag_keys or any(marker in source_key for marker in CONFERENCE_SOURCE_MARKERS)

    def _source_key(self, artifact: Artifact) -> str:
        """Normalize artifact source labels for category checks."""

        return " ".join((artifact.source_name or "").strip().lower().replace("_", "-").split())
