"""Normalization, enrichment, analysis, clustering, scoring, and full-run CLI commands."""

from __future__ import annotations

from datetime import date, datetime, time as datetime_time, timedelta
from pathlib import Path
import time
from typing import Any, Callable

import click

from src.cli.crawl import _crawl_all_sources, _crawl_daily_sources
from src.cli.main import AppContext, handle_command_errors, parse_date_option, pass_app_context
from src.llm import LLMClient
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.personalization.academic_quality import DEFAULT_CSRANKINGS_URL
from src.pipelines.academic_filter import AcademicFilterConfig, AcademicFilterPipeline
from src.pipelines.academic_judge import AcademicJudgePipeline
from src.pipelines.academic_labels import AcademicLabelPipeline
from src.pipelines.clustering import ClusteringPipeline
from src.pipelines.deep_analysis import DeepAnalysisPipeline
from src.pipelines.enrichment import EnrichmentPipeline
from src.pipelines.gap_detection import GapDetectionPipeline
from src.pipelines.llm_relevance import LLMRelevancePipeline
from src.pipelines.normalization import NormalizationPipeline, _LEGACY_TIER_MAP
from src.pipelines.signal_extraction import SignalExtractionPipeline
from src.pipelines.direction_synthesis import DirectionSynthesisPipeline
from src.pipelines.trend_analysis import TrendAnalysisPipeline
from src.reporting.daily import DailyReportGenerator
from src.reporting.landscape import LandscapeReportGenerator
from src.reporting.relevance_filter import should_display_artifact
from src.reporting.weekly import WeeklyReportGenerator
from src.repositories.artifact_repository import ArtifactRepository
from src.scoring.engine import ScoringEngine
from src.timezone import app_today, local_date


def build_llm_client(provider: str) -> LLMClient:
    """Build an LLM client for one provider name."""

    return LLMClient(provider=provider)


@click.command("normalize")
@click.option(
    "--input-dir",
    type=click.Path(path_type=Path),
    default=Path("data/raw"),
    show_default=True,
    help="Input raw JSON directory or file.",
)
@click.option("--recursive/--no-recursive", default=True, show_default=True, help="Scan subdirectories recursively.")
@pass_app_context
@handle_command_errors
def normalize_command(app: AppContext, input_dir: Path, recursive: bool) -> None:
    """Process raw JSON files into normalized artifacts."""

    target = _resolve_normalization_input(input_dir, recursive)
    pipeline = NormalizationPipeline(session_factory=app.session_factory, engine=app.engine)
    artifacts = pipeline.process(target)
    click.echo(f"Normalized {len(artifacts)} artifact entries")


@click.command("enrich")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider to use for enrichment.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option("--workers", type=click.IntRange(1), default=8, show_default=True, help="Number of LLM worker threads.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=0.0,
    show_default=True,
    help="Seconds to wait between LLM requests; values >0 force sequential enrichment.",
)
@pass_app_context
@handle_command_errors
def enrich_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    workers: int,
    request_delay: float,
) -> None:
    """Generate LLM summaries and tags."""

    llm_client = build_llm_client(provider)
    pipeline = EnrichmentPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        request_delay_seconds=request_delay,
    )
    enriched = pipeline.process(artifact_id)
    click.echo(f"Enriched {len(enriched)} artifacts")


@click.command("score")
@pass_app_context
@handle_command_errors
def score_command(app: AppContext) -> None:
    """Score persisted artifacts."""

    artifacts = ScoringEngine(session_factory=app.session_factory).score_all()
    click.echo(f"Scored {len(artifacts)} artifacts")


@click.command("llm-relevance")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="gemini",
    show_default=True,
    help="LLM provider to use for relevance scoring.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option("--workers", type=click.IntRange(1), default=8, show_default=True, help="Number of LLM worker threads.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=0.0,
    show_default=True,
    help="Seconds to wait between LLM requests; values >0 force sequential relevance scoring.",
)
@pass_app_context
@handle_command_errors
def llm_relevance_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    workers: int,
    request_delay: float,
) -> None:
    """Pre-compute LLM relevance scores for persisted artifacts."""

    llm_client = build_llm_client(provider)
    artifacts = LLMRelevancePipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        request_delay_seconds=request_delay,
    ).process(artifact_id)
    click.echo(f"LLM relevance scored {len(artifacts)} artifacts")


@click.command("academic-filter")
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option(
    "--zotero-json",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    envvar="ZOTERO_CSL_JSON",
    help="Better CSL JSON export from Zotero. Falls back to Zotero API env vars.",
)
@click.option(
    "--csrankings-csv",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    envvar="CSRANKINGS_CSV",
    help="Local CSRankings CSV file. If omitted, the configured URL is used.",
)
@click.option(
    "--csrankings-url",
    type=str,
    default=DEFAULT_CSRANKINGS_URL,
    show_default=True,
    envvar="CSRANKINGS_URL",
    help="CSRankings CSV URL. Use an empty value to disable remote fetch.",
)
@click.option("--top-k", type=click.IntRange(1), default=5, show_default=True, help="Number of Zotero matches to keep.")
@click.option(
    "--min-similarity",
    type=click.FloatRange(0.0, 1.0),
    default=0.18,
    show_default=True,
    help="Minimum Zotero similarity required for academic display.",
)
@click.option(
    "--min-arxiv-quality",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    show_default=True,
    help="Minimum CSRankings quality score required for evaluated arXiv display.",
)
@pass_app_context
@handle_command_errors
def academic_filter_command(
    app: AppContext,
    artifact_id: int | None,
    zotero_json: Path | None,
    csrankings_csv: Path | None,
    csrankings_url: str,
    top_k: int,
    min_similarity: float,
    min_arxiv_quality: float,
) -> None:
    """Precompute academic relevance and quality evidence from Zotero and CSRankings."""

    pipeline = AcademicFilterPipeline(
        session_factory=app.session_factory,
        zotero_json_path=zotero_json,
        csrankings_csv_path=csrankings_csv,
        csrankings_url=csrankings_url or None,
        config=AcademicFilterConfig(
            top_k=top_k,
            zotero_min_similarity=min_similarity,
            arxiv_min_quality=min_arxiv_quality,
        ),
    )
    artifacts = pipeline.process(artifact_id)
    click.echo(f"Academic filter evaluated {len(artifacts)} artifacts")


@click.command("academic-labels")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider to use for concise academic focus labels.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=0.0,
    show_default=True,
    help="Seconds to wait between LLM requests.",
)
@click.option(
    "--only-displayable/--all-academic",
    default=True,
    show_default=True,
    help="Only label academic artifacts that currently pass display filters.",
)
@pass_app_context
@handle_command_errors
def academic_labels_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    request_delay: float,
    only_displayable: bool,
) -> None:
    """Generate concise AI focus labels for academic paper cards."""

    target: int | list[int] | None = artifact_id
    if artifact_id is None and only_displayable:
        session = app.session_factory()
        try:
            repository = ArtifactRepository(session)
            target = [
                artifact.id
                for artifact in repository.list_by_status(ArtifactStatus.ACTIVE)
                if artifact.source_type == SourceType.PAPERS and should_display_artifact(artifact)
            ]
        finally:
            session.close()

    llm_client = build_llm_client(provider)
    artifacts = AcademicLabelPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        request_delay_seconds=request_delay,
    ).process(target)
    click.echo(f"Academic focus labeled {len(artifacts)} artifacts")


@click.command("academic-judge")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider to use for Zotero-backed relevance judgment.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=0.0,
    show_default=True,
    help="Seconds to wait between LLM requests.",
)
@click.option(
    "--min-relevance",
    type=click.FloatRange(0.0, 1.0),
    default=0.6,
    show_default=True,
    help="Minimum LLM relevance score required for academic display.",
)
@pass_app_context
@handle_command_errors
def academic_judge_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    request_delay: float,
    min_relevance: float,
) -> None:
    """Judge academic relevance from candidate paper and top-k Zotero evidence."""

    llm_client = build_llm_client(provider)
    artifacts = AcademicJudgePipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        min_relevance=min_relevance,
        request_delay_seconds=request_delay,
    ).process(artifact_id)
    click.echo(f"Academic relevance judged {len(artifacts)} artifacts")


@click.command("deep-analyze")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM provider to use for deep analysis.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific artifact by DB id.")
@click.option("--workers", type=click.IntRange(1), default=4, show_default=True, help="Number of LLM worker threads.")
@click.option("--min-relevance", type=float, default=0.6, show_default=True, help="Minimum relevance threshold.")
@pass_app_context
@handle_command_errors
def deep_analyze_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    workers: int,
    min_relevance: float,
) -> None:
    """Generate structured L2 deep analysis for relevant papers."""

    llm_client = build_llm_client(provider)
    artifacts = DeepAnalysisPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        min_relevance=min_relevance,
    ).process(artifact_id)
    click.echo(f"Deep analyzed {len(artifacts)} artifacts")


@click.command("cluster")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM provider to use for clustering.",
)
@click.option("--full/--incremental", "full_mode", default=True, show_default=True, help="Run full or incremental clustering.")
@click.option("--min-relevance", type=float, default=0.6, show_default=True, help="Minimum relevance threshold.")
@pass_app_context
@handle_command_errors
def cluster_command(app: AppContext, provider: str, full_mode: bool, min_relevance: float) -> None:
    """Group high-relevance papers into research themes."""

    llm_client = build_llm_client(provider)
    themes = ClusteringPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        min_relevance=min_relevance,
    ).process(None if full_mode else "incremental")
    click.echo(f"Clustered {len(themes)} themes")


@click.command("run")
@click.option("--skip-crawl", is_flag=True, help="Skip the crawl step.")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider for enrichment.",
)
@click.option(
    "--report-type",
    type=click.Choice(["daily", "weekly", "landscape"], case_sensitive=False),
    default="daily",
    show_default=True,
    help="Report type to generate.",
)
@click.option("--date", "target_date_raw", type=str, default=None, help="Target date in YYYY-MM-DD format.")
@click.option("--workers", type=click.IntRange(1), default=8, show_default=True, help="Number of LLM worker threads.")
@click.option("--full", "full_mode", is_flag=True, help="Run full intelligence analysis chain (weekly).")
@pass_app_context
@handle_command_errors
def run_command(
    app: AppContext,
    skip_crawl: bool,
    provider: str,
    report_type: str,
    target_date_raw: str | None,
    workers: int,
    full_mode: bool,
) -> None:
    """Run normalize → enrich → score → report sequentially. --full adds intelligence analysis."""

    target_date = parse_date_option(target_date_raw)
    raw_input_dir = Path("data/raw")

    if not skip_crawl:
        raw_input_dir.mkdir(parents=True, exist_ok=True)
        _crawl_all_sources([app_today().year], raw_input_dir.resolve())

    if _has_raw_json(raw_input_dir):
        normalization_target = _resolve_normalization_input(raw_input_dir, recursive=True)
        normalized = NormalizationPipeline(session_factory=app.session_factory, engine=app.engine).process(normalization_target)
    else:
        normalized = []
    click.echo(f"Normalized {len(normalized)} artifact entries")

    llm_client = build_llm_client(provider)
    enriched = EnrichmentPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
    ).process(None)
    click.echo(f"Enriched {len(enriched)} artifacts")

    llm_relevance = LLMRelevancePipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
    ).process(None)
    click.echo(f"LLM relevance scored {len(llm_relevance)} artifacts")

    scored = ScoringEngine(session_factory=app.session_factory).score_all()
    click.echo(f"Scored {len(scored)} artifacts")

    if full_mode:
        # Academic track: L2 deep analysis + clustering
        deep = DeepAnalysisPipeline(
            session_factory=app.session_factory,
            llm_client=llm_client,
            max_workers=min(workers, 4),
        ).process(None)
        click.echo(f"Deep analyzed {len(deep)} artifacts")

        # Industry track: signal extraction
        signals = SignalExtractionPipeline(
            session_factory=app.session_factory,
            llm_client=llm_client,
            max_workers=min(workers, 4),
        ).process(None)
        click.echo(f"Extracted signals from {len(signals)} blog posts")

        themes = ClusteringPipeline(
            session_factory=app.session_factory,
            llm_client=llm_client,
        ).process(None)
        click.echo(f"Clustered {len(themes)} themes")

        # Trend analysis
        trend_themes = TrendAnalysisPipeline(
            session_factory=app.session_factory,
            llm_client=llm_client,
        ).process(None)
        click.echo(f"Trend analysis updated {len(trend_themes)} themes")

        # Cross-reference: gap detection + direction synthesis
        gaps = GapDetectionPipeline(
            session_factory=app.session_factory,
        ).process()
        click.echo(f"Detected {len(gaps)} research gaps")

        directions = DirectionSynthesisPipeline(
            session_factory=app.session_factory,
            llm_client=llm_client,
        ).process()
        click.echo(f"Synthesized {len(directions)} candidate directions")

        # Generate landscape report
        effective_report_type = "landscape"
    else:
        effective_report_type = report_type

    report_path = _generate_report(app, effective_report_type, target_date)
    click.echo(f"Generated {effective_report_type} report: {report_path}")


@click.command("daily-refresh")
@click.option("--skip-crawl", is_flag=True, help="Skip the crawl step.")
@click.option(
    "--crawl-scope",
    type=click.Choice(["daily", "all"], case_sensitive=False),
    default="daily",
    show_default=True,
    help="Sources to crawl when crawl is not skipped. daily crawls arXiv and blog/webpage feeds; all also runs heavyweight conference paper crawlers.",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider for daily enrichment and relevance.",
)
@click.option("--date", "target_date_raw", type=str, default=None, help="Target date in YYYY-MM-DD format.")
@click.option("--workers", type=click.IntRange(1), default=1, show_default=True, help="Number of LLM worker threads.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=5.0,
    show_default=True,
    help="Seconds to wait between LLM requests.",
)
@click.option(
    "--academic-personalization/--skip-academic-personalization",
    default=True,
    show_default=True,
    help="Run Zotero/CSRankings filter, LLM judge, and focus labels after scoring.",
)
@pass_app_context
@handle_command_errors
def daily_refresh_command(
    app: AppContext,
    skip_crawl: bool,
    crawl_scope: str,
    provider: str,
    target_date_raw: str | None,
    workers: int,
    request_delay: float,
    academic_personalization: bool,
) -> None:
    """Refresh the daily dashboard/report pipeline once for the target day."""

    target_date = parse_date_option(target_date_raw)
    _run_daily_refresh(
        app,
        target_date=target_date,
        provider=provider,
        skip_crawl=skip_crawl,
        crawl_scope=crawl_scope,
        workers=workers,
        request_delay=request_delay,
        academic_personalization=academic_personalization,
    )


@click.command("schedule-daily")
@click.option(
    "--time",
    "run_time",
    default="00:10",
    show_default=True,
    help="Local HH:MM time to run the daily refresh.",
)
@click.option("--run-now", is_flag=True, help="Run one refresh immediately before waiting for the next day.")
@click.option("--once", is_flag=True, help="Exit after one scheduled or immediate refresh.")
@click.option("--skip-crawl", is_flag=True, help="Skip the crawl step in each refresh.")
@click.option(
    "--crawl-scope",
    type=click.Choice(["daily", "all"], case_sensitive=False),
    default="daily",
    show_default=True,
    help="Sources to crawl when crawl is not skipped.",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="LLM provider for daily enrichment and relevance.",
)
@click.option("--workers", type=click.IntRange(1), default=1, show_default=True, help="Number of LLM worker threads.")
@click.option(
    "--request-delay",
    type=click.FloatRange(0.0),
    default=5.0,
    show_default=True,
    help="Seconds to wait between LLM requests.",
)
@click.option(
    "--academic-personalization/--skip-academic-personalization",
    default=True,
    show_default=True,
    help="Run Zotero/CSRankings filter, LLM judge, and focus labels after scoring.",
)
@pass_app_context
@handle_command_errors
def schedule_daily_command(
    app: AppContext,
    run_time: str,
    run_now: bool,
    once: bool,
    skip_crawl: bool,
    crawl_scope: str,
    provider: str,
    workers: int,
    request_delay: float,
    academic_personalization: bool,
) -> None:
    """Run the daily refresh automatically once per local day."""

    scheduled_time = _parse_schedule_time(run_time)
    if run_now:
        _run_daily_refresh(
            app,
            target_date=app_today(),
            provider=provider,
            skip_crawl=skip_crawl,
            crawl_scope=crawl_scope,
            workers=workers,
            request_delay=request_delay,
            academic_personalization=academic_personalization,
        )
        if once:
            return

    while True:
        now = datetime.now().astimezone()
        next_run = _next_scheduled_run(now, scheduled_time)
        wait_seconds = max(0.0, (next_run - now).total_seconds())
        click.echo(f"Next daily refresh at {next_run.strftime('%Y-%m-%d %H:%M %Z')}")
        if wait_seconds:
            time.sleep(wait_seconds)
        _run_daily_refresh(
            app,
            target_date=app_today(),
            provider=provider,
            skip_crawl=skip_crawl,
            crawl_scope=crawl_scope,
            workers=workers,
            request_delay=request_delay,
            academic_personalization=academic_personalization,
        )
        if once:
            return


def _run_daily_refresh(
    app: AppContext,
    *,
    target_date: date,
    provider: str,
    skip_crawl: bool,
    workers: int,
    request_delay: float,
    academic_personalization: bool,
    crawl_scope: str = "daily",
    artifact_scope: str = "daily",
    progress: Callable[[str, int, str], None] | None = None,
) -> Path:
    """Run the daily refresh chain and return the generated report path."""

    raw_input_dir = Path("data/raw")
    raw_input_dir.mkdir(parents=True, exist_ok=True)

    _emit_progress(progress, "Starting", 3, "Preparing daily refresh.")
    if not skip_crawl:
        _emit_progress(progress, "Crawling sources", 10, f"Crawling {crawl_scope} source set.")
        if crawl_scope.lower() == "all":
            _crawl_all_sources([app_today().year], raw_input_dir.resolve())
        else:
            _crawl_daily_sources(
                [app_today().year],
                raw_input_dir.resolve(),
                progress=progress,
                fail_fast=progress is not None,
            )

    _emit_progress(progress, "Normalizing", 28, "Normalizing raw JSON into artifacts.")
    if _has_raw_json(raw_input_dir):
        normalization_target = _resolve_normalization_input(raw_input_dir, recursive=True)
        normalized = NormalizationPipeline(session_factory=app.session_factory, engine=app.engine).process(normalization_target)
    else:
        normalized = []
    click.echo(f"Normalized {len(normalized)} artifact entries")

    target_ids = _daily_refresh_target_ids(
        app.session_factory,
        target_date=target_date,
        normalized=normalized,
        artifact_scope=artifact_scope,
    )
    if artifact_scope == "daily":
        click.echo(f"Selected {len(target_ids)} daily artifact entries for LLM processing")

    _emit_progress(progress, "Enriching", 45, "Generating Chinese summaries and tags.")
    llm_client = build_llm_client(provider)
    enriched = EnrichmentPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        request_delay_seconds=request_delay,
    ).process(target_ids if artifact_scope == "daily" else None)
    click.echo(f"Enriched {len(enriched)} artifacts")

    _emit_progress(progress, "Scoring relevance", 62, "Running LLM relevance filter.")
    relevance = LLMRelevancePipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        request_delay_seconds=request_delay,
    ).process(target_ids if artifact_scope == "daily" else None)
    click.echo(f"LLM relevance scored {len(relevance)} artifacts")

    _emit_progress(progress, "Scoring", 74, "Computing final scores.")
    scored = ScoringEngine(session_factory=app.session_factory).score_all()
    click.echo(f"Scored {len(scored)} artifacts")

    if academic_personalization:
        _emit_progress(progress, "Personalizing papers", 84, "Applying Zotero and academic quality signals.")
        _run_academic_personalization(
            app,
            llm_client=llm_client,
            request_delay=request_delay,
            artifact_ids=target_ids if artifact_scope == "daily" else None,
        )

    _emit_progress(progress, "Writing report", 94, "Generating the daily report.")
    report_path = DailyReportGenerator(session_factory=app.session_factory).generate(target_date)
    click.echo(f"Generated daily report: {report_path}")
    _emit_progress(progress, "Complete", 100, f"Generated daily report: {report_path}")
    return report_path


def _emit_progress(progress: Callable[[str, int, str], None] | None, step: str, percent: int, message: str) -> None:
    """Emit optional daily refresh progress without affecting CLI behavior."""

    if progress is not None:
        progress(step, percent, message)


def _daily_refresh_target_ids(
    session_factory: Any,
    *,
    target_date: date,
    normalized: list[Any],
    artifact_scope: str,
) -> list[int]:
    """Select artifacts that belong to one daily refresh cycle."""

    if artifact_scope != "daily":
        return []

    normalized_ids = {artifact.id for artifact in normalized if getattr(artifact, "id", None) is not None}
    session = session_factory()
    try:
        artifacts = session.query(Artifact).filter(Artifact.status == ArtifactStatus.ACTIVE).all()
        selected: list[int] = []
        for artifact in artifacts:
            if not _is_daily_refresh_artifact(artifact):
                continue
            is_new_or_updated = artifact.id in normalized_ids
            matches_target_date = _artifact_matches_date(artifact, target_date)
            if not is_new_or_updated and not matches_target_date:
                continue
            selected.append(artifact.id)
        return sorted(set(selected))
    finally:
        session.close()


def _is_daily_refresh_artifact(artifact: Artifact) -> bool:
    """Return whether an artifact belongs to daily crawl/analysis scope."""

    if artifact.source_type != SourceType.PAPERS:
        return True
    source_tier = (artifact.source_tier or "").strip().lower()
    source_name = (artifact.source_name or "").strip().lower()
    return source_tier == "t2-arxiv" or "arxiv" in source_name


def _artifact_matches_date(artifact: Artifact, target_date: date) -> bool:
    """Return whether an artifact belongs to a target daily date."""

    timestamp = artifact.published_at or artifact.created_at
    if timestamp is None:
        return False
    return local_date(timestamp) == target_date


def _run_academic_personalization(
    app: AppContext,
    *,
    llm_client: LLMClient,
    request_delay: float,
    artifact_ids: list[int] | None = None,
) -> None:
    """Run academic personalization best-effort so automation still produces a daily report."""

    try:
        filtered = AcademicFilterPipeline(session_factory=app.session_factory).process(artifact_ids)
    except Exception as exc:  # pragma: no cover - defensive external/source boundary
        click.echo(f"Skipped academic personalization: {exc}", err=True)
        return
    click.echo(f"Academic filter evaluated {len(filtered)} artifacts")

    judged = AcademicJudgePipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        request_delay_seconds=request_delay,
    ).process(artifact_ids)
    click.echo(f"Academic relevance judged {len(judged)} artifacts")

    labeled = AcademicLabelPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        request_delay_seconds=request_delay,
    ).process(artifact_ids)
    click.echo(f"Academic focus labeled {len(labeled)} artifacts")


def _parse_schedule_time(raw_value: str) -> datetime_time:
    """Parse HH:MM schedule time."""

    try:
        hour_text, minute_text = raw_value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
        return datetime_time(hour=hour, minute=minute)
    except ValueError as exc:
        raise click.ClickException(f"Invalid --time value: {raw_value}. Expected HH:MM.") from exc


def _next_scheduled_run(now: datetime, scheduled_time: datetime_time) -> datetime:
    """Return the next local datetime matching the scheduled time."""

    candidate = now.replace(
        hour=scheduled_time.hour,
        minute=scheduled_time.minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _has_raw_json(path: Path) -> bool:
    """Return whether a raw input directory contains any JSON file."""

    return path.exists() and any(item.is_file() for item in path.rglob("*.json"))


def _resolve_normalization_input(input_dir: Path, recursive: bool) -> Path | list[Path]:
    """Resolve CLI normalize input into a pipeline-compatible target."""

    target = input_dir.resolve()
    if not target.exists():
        raise click.ClickException(f"Input path does not exist: {input_dir}")
    if target.is_file():
        return target
    if recursive:
        return target
    files = sorted(target.glob("*.json"))
    if not files:
        raise click.ClickException(f"No JSON files found in: {input_dir}")
    return files


def _generate_report(app: AppContext, report_type: str, target_date: date) -> Path:
    """Generate one report and return its output path."""

    normalized_report_type = report_type.lower()
    if normalized_report_type == "daily":
        return DailyReportGenerator(session_factory=app.session_factory).generate(target_date)
    if normalized_report_type == "weekly":
        return WeeklyReportGenerator(session_factory=app.session_factory).generate(target_date)
    if normalized_report_type == "landscape":
        return LandscapeReportGenerator(session_factory=app.session_factory).generate(target_date)
    raise click.ClickException(f"Unsupported report type: {report_type}")


@click.command("extract-signals")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM provider to use for signal extraction.",
)
@click.option("--artifact-id", type=int, default=None, help="Target a specific blog artifact by DB id.")
@click.option("--workers", type=click.IntRange(1), default=4, show_default=True, help="Number of LLM worker threads.")
@click.option("--min-relevance", type=float, default=0.3, show_default=True, help="Minimum relevance threshold for blogs.")
@pass_app_context
@handle_command_errors
def extract_signals_command(
    app: AppContext,
    provider: str,
    artifact_id: int | None,
    workers: int,
    min_relevance: float,
) -> None:
    """Extract demand signals from blog posts (industry track)."""

    llm_client = build_llm_client(provider)
    artifacts = SignalExtractionPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        max_workers=workers,
        min_relevance=min_relevance,
    ).process(artifact_id)
    click.echo(f"Extracted signals from {len(artifacts)} blog posts")


@click.command("detect-gaps")
@click.option("--top-n", type=click.IntRange(1), default=10, show_default=True, help="Maximum number of gaps to detect.")
@pass_app_context
@handle_command_errors
def detect_gaps_command(app: AppContext, top_n: int) -> None:
    """Detect research gaps between academic coverage and industry demand."""

    gaps = GapDetectionPipeline(
        session_factory=app.session_factory,
        top_n=top_n,
    ).process()
    click.echo(f"Detected {len(gaps)} research gaps")
    for gap in gaps[:5]:
        click.echo(f"  [{gap.gap_score:.2f}] {gap.topic} (demand={gap.demand_frequency}, coverage={gap.academic_coverage:.1%})")


@click.command("trend")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM provider for qualitative trend analysis.",
)
@click.option("--theme-id", type=str, default=None, help="Target a specific theme by UUID.")
@click.option("--no-qualitative", is_flag=True, help="Skip LLM qualitative analysis, only compute statistics.")
@pass_app_context
@handle_command_errors
def trend_command(app: AppContext, provider: str, theme_id: str | None, no_qualitative: bool) -> None:
    """Compute trend statistics and qualitative analysis for research themes."""

    llm_client = build_llm_client(provider)
    themes = TrendAnalysisPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
        qualitative=not no_qualitative,
    ).process(theme_id)
    click.echo(f"Trend analysis updated {len(themes)} themes")
    for t in themes[:10]:
        click.echo(f"  [{t.trend_direction or '?'}] {t.name} ({t.artifact_count} papers)")


@click.command("synthesize")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "gemini"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM provider to use for direction synthesis.",
)
@pass_app_context
@handle_command_errors
def synthesize_command(app: AppContext, provider: str) -> None:
    """Synthesize candidate research directions from detected gaps."""

    llm_client = build_llm_client(provider)
    directions = DirectionSynthesisPipeline(
        session_factory=app.session_factory,
        llm_client=llm_client,
    ).process()
    click.echo(f"Synthesized {len(directions)} candidate directions")
    for d in directions:
        score_str = f"{d.composite_direction_score:.2f}" if d.composite_direction_score else "N/A"
        click.echo(f"  [{score_str}] {d.title}")


@click.command("migrate-tiers")
@pass_app_context
@handle_command_errors
def migrate_tiers_command(app: AppContext) -> None:
    """One-time migration of legacy source_tier values to v2 SourceTier enum values."""

    from src.models.artifact import Artifact
    from src.models.enums import ArtifactStatus
    from src.repositories.artifact_repository import ArtifactRepository

    session = app.session_factory()
    try:
        repository = ArtifactRepository(session)
        artifacts = repository.list_by_status(ArtifactStatus.ACTIVE)
        migrated = 0
        for artifact in artifacts:
            old_tier = (artifact.source_tier or "").lower().strip()
            new_tier = _LEGACY_TIER_MAP.get(old_tier)
            if new_tier and artifact.source_tier != new_tier:
                artifact.source_tier = new_tier
                repository.save(artifact)
                migrated += 1
        click.echo(f"Migrated {migrated} artifacts to new tier values")
    finally:
        session.close()
