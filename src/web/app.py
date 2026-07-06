"""FastAPI application for the local Research Radar console."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
import logging
import math
import os
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, quote

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.cli.main import AppContext
from src.cli.process import _run_daily_refresh
from src.config.sources import DEFAULT_SOURCE_CONFIG_PATH, SourceConfig
from src.db.session import ENGINE, SessionLocal, create_all_tables
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.pipelines.enrichment import EnrichmentPipeline
from src.pipelines.normalization import NormalizationPipeline
from src.reporting.daily import DailyReportGenerator
from src.reporting.relevance_filter import should_display_artifact
from src.scoring.engine import ScoringEngine
from src.timezone import app_today, local_date
from src.llm import LLMClient
from src.web.presentation import artifact_chips, artifact_source_label, artifact_summary
from src.web.source_admin import (
    build_blog_crawler,
    list_source_configs,
    test_source_fetch,
    toggle_source,
    upsert_source_from_form,
)

WEB_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
templates.env.globals["artifact_chips"] = artifact_chips
templates.env.globals["artifact_source_label"] = artifact_source_label
templates.env.globals["artifact_summary"] = artifact_summary
ORG_SOURCE_SLUGS = {"openai-blog", "anthropic-news"}
CONFERENCE_SOURCE_MARKERS = ("black hat", "blackhat", "def con", "defcon", "bsides")
ARTIFACTS_PAGE_SIZE = 20
DASHBOARD_RANGE_MODES = {"today", "7d", "custom"}


@dataclass
class RefreshStatus:
    """In-memory dashboard refresh status."""

    state: str = "idle"
    step: str = "Idle"
    progress: int = 0
    message: str = "No refresh is running."
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class DashboardDateRange:
    """Dashboard date range selector state."""

    mode: str
    start: date
    end: date
    selected_date: date
    label: str

    @property
    def date_value(self) -> str:
        return self.selected_date.isoformat()

    @property
    def start_value(self) -> str:
        return self.start.isoformat()

    @property
    def end_value(self) -> str:
        return self.end.isoformat()


class RefreshStatusStore:
    """Thread-safe status store for one local web process."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._status = RefreshStatus()

    def start(self, message: str) -> bool:
        with self._lock:
            if self._status.state == "running":
                return False
            self._status = RefreshStatus(
                state="running",
                step="Queued",
                progress=1,
                message=message,
                started_at=_utc_now_iso(),
            )
            return True

    def update(self, step: str, progress: int, message: str) -> None:
        with self._lock:
            self._status.step = step
            self._status.progress = max(0, min(99, progress))
            self._status.message = message

    def finish(self, message: str) -> None:
        with self._lock:
            self._status.state = "complete"
            self._status.step = "Complete"
            self._status.progress = 100
            self._status.message = message
            self._status.finished_at = _utc_now_iso()
            self._status.error = None

    def fail(self, message: str) -> None:
        with self._lock:
            self._status.state = "failed"
            self._status.step = "Failed"
            self._status.progress = 100
            self._status.message = message
            self._status.finished_at = _utc_now_iso()
            self._status.error = message

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self._status)


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
    source_config_path: Path | None = None,
) -> FastAPI:
    """Create the local web console app."""

    resolved_session_factory = session_factory or SessionLocal
    engine = resolved_session_factory.kw.get("bind") if hasattr(resolved_session_factory, "kw") else None
    engine = engine or ENGINE
    create_all_tables(engine)
    app = FastAPI(title="Research Radar Console")
    app.state.session_factory = resolved_session_factory
    app.state.engine = engine
    app.state.source_config_path = source_config_path or DEFAULT_SOURCE_CONFIG_PATH
    app.state.refresh_status = RefreshStatusStore()
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=303)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(
        request: Request,
        selected_date: str | None = Query(default=None, alias="date"),
        selected_range: str | None = Query(default=None, alias="range"),
        q: str = "",
        notice: str | None = None,
        error: str | None = None,
    ) -> HTMLResponse:
        session = _session(request)
        try:
            dashboard_range = _parse_dashboard_range(selected_range, selected_date)
            search_query = _normalize_search_query(q)
            artifacts = _dashboard_candidate_artifacts(session)
            display_artifacts = [artifact for artifact in artifacts if should_display_artifact(artifact)]
            if search_query:
                display_artifacts = [
                    artifact for artifact in display_artifacts if _artifact_matches_search(artifact, search_query)
                ]
            sources = _sources(request)
            context = _base_context(request, notice=notice, error=error)
            context.update(
                {
                    "active_nav": "dashboard",
                    "metrics": _dashboard_metrics(session, display_artifacts, sources),
                    "academic_items": _dashboard_academic_items(display_artifacts, dashboard_range=dashboard_range),
                    "industry_sections": _industry_sections(
                        display_artifacts,
                        sources,
                        dashboard_range=dashboard_range,
                    ),
                    "dashboard_date": dashboard_range.date_value,
                    "dashboard_range": dashboard_range,
                    "search_query": search_query,
                    "search_query_param": quote(search_query),
                }
            )
            return templates.TemplateResponse(request, "dashboard.html", context)
        finally:
            session.close()

    @app.post("/dashboard/refresh-today")
    async def refresh_today(request: Request, background_tasks: BackgroundTasks) -> RedirectResponse:
        status_store: RefreshStatusStore = request.app.state.refresh_status
        started = status_store.start("Daily refresh queued.")
        if started:
            background_tasks.add_task(
                _run_dashboard_daily_refresh,
                request.app.state.session_factory,
                request.app.state.engine,
                status_store,
            )
            notice = "Started lightweight daily refresh for today. Progress is shown below."
        else:
            notice = "Daily refresh is already running. Progress is shown below."
        return _redirect(
            f"/dashboard?date={app_today().isoformat()}",
            notice=notice,
        )

    @app.get("/dashboard/refresh-status")
    async def refresh_status(request: Request) -> dict[str, Any]:
        status_store: RefreshStatusStore = request.app.state.refresh_status
        return status_store.snapshot()

    @app.get("/sources", response_class=HTMLResponse)
    async def sources(request: Request, notice: str | None = None, error: str | None = None) -> HTMLResponse:
        context = _base_context(request, notice=notice, error=error)
        context.update({"active_nav": "sources", "sources": _sources(request)})
        return templates.TemplateResponse(request, "sources.html", context)

    @app.post("/sources")
    async def create_source(request: Request) -> RedirectResponse:
        try:
            form = await _form_dict(request)
            source = upsert_source_from_form(form, _source_config_path(request))
        except Exception as exc:
            return _redirect("/sources", error=f"Could not save source: {exc}")
        return _redirect("/sources", notice=f"Saved source {source.slug}. It is disabled until you enable it.")

    @app.post("/sources/{slug}/toggle")
    async def toggle_source_route(request: Request, slug: str) -> RedirectResponse:
        try:
            source = toggle_source(slug, _source_config_path(request))
        except Exception as exc:
            return _redirect("/sources", error=f"Could not toggle source: {exc}")
        state = "enabled" if source.enabled else "disabled"
        return _redirect("/sources", notice=f"{source.name} is now {state}.")

    @app.post("/sources/{slug}/test")
    async def test_source_route(request: Request, slug: str) -> HTMLResponse:
        result = test_source_fetch(slug, _source_config_path(request), limit=3)
        context = _base_context(request)
        context.update({"active_nav": "sources", "sources": _sources(request), "test_slug": slug, "test_result": result})
        return templates.TemplateResponse(request, "sources.html", context)

    @app.get("/artifacts", response_class=HTMLResponse)
    async def artifacts(request: Request, track: str = "all", page: int = 1, q: str = "") -> HTMLResponse:
        session = _session(request)
        try:
            track = track if track in {"all", "academic", "industry"} else "all"
            page = max(1, page)
            search_query = _normalize_search_query(q)
            items, pagination = _paginated_artifacts(
                session,
                track=track,
                page=page,
                page_size=ARTIFACTS_PAGE_SIZE,
                search_query=search_query,
            )
            context = _base_context(request)
            context.update(
                {
                    "active_nav": "artifacts",
                    "track": track,
                    "search_query": search_query,
                    "search_query_param": quote(search_query),
                    "artifacts": items,
                    "pagination": pagination,
                }
            )
            return templates.TemplateResponse(request, "artifacts.html", context)
        finally:
            session.close()

    @app.get("/runs", response_class=HTMLResponse)
    async def runs(request: Request, notice: str | None = None, error: str | None = None) -> HTMLResponse:
        context = _base_context(request, notice=notice, error=error)
        context.update({"active_nav": "runs", "sources": _sources(request), "today": app_today().isoformat()})
        return templates.TemplateResponse(request, "runs.html", context)

    @app.post("/runs/crawl-source")
    async def crawl_source(request: Request) -> RedirectResponse:
        form = await _form_dict(request)
        slug = form.get("slug", "")
        try:
            sources_by_slug = {source.slug: source for source in _sources(request)}
            source = sources_by_slug[slug]
            crawler = build_blog_crawler(source)
            items = crawler.fetch_articles(limit=5)
            output_path = crawler.save_raw(items, Path("data/raw/blogs"), metadata={"limit": 5, "source": "web-console"})
        except Exception as exc:
            return _redirect("/runs", error=f"Could not crawl {slug}: {exc}")
        return _redirect("/runs", notice=f"Crawled {slug}: {len(items)} items saved to {output_path.name}.")

    @app.post("/runs/normalize")
    async def normalize_run(request: Request) -> RedirectResponse:
        try:
            artifacts = NormalizationPipeline(
                session_factory=_session_factory(request), engine=request.app.state.engine
            ).process(Path("data/raw"))
        except Exception as exc:
            return _redirect("/runs", error=f"Normalize failed: {exc}")
        return _redirect("/runs", notice=f"Normalized {len(artifacts)} artifact entries.")

    @app.post("/runs/enrich-one")
    async def enrich_one(request: Request) -> RedirectResponse:
        form = await _form_dict(request)
        try:
            artifact_id = int(form.get("artifact_id", "0"))
            delay = float(form.get("request_delay", "0") or 0)
            client = LLMClient(provider="openai", timeout=90, max_retries=1, backoff_base_seconds=5)
            enriched = EnrichmentPipeline(
                session_factory=_session_factory(request),
                llm_client=client,
                max_workers=1,
                request_delay_seconds=delay,
            ).process(artifact_id)
        except Exception as exc:
            return _redirect("/runs", error=f"Enrich failed: {exc}")
        return _redirect("/runs", notice=f"Enriched {len(enriched)} artifact.")

    @app.post("/runs/score")
    async def score_run(request: Request) -> RedirectResponse:
        try:
            artifacts = ScoringEngine(session_factory=_session_factory(request)).score_all()
        except Exception as exc:
            return _redirect("/runs", error=f"Score failed: {exc}")
        return _redirect("/runs", notice=f"Scored {len(artifacts)} artifacts.")

    @app.post("/runs/report-daily")
    async def report_daily(request: Request) -> RedirectResponse:
        form = await _form_dict(request)
        target_date = date.fromisoformat(form.get("target_date") or app_today().isoformat())
        try:
            report_path = DailyReportGenerator(session_factory=_session_factory(request)).generate(target_date)
        except Exception as exc:
            return _redirect("/runs", error=f"Report failed: {exc}")
        return _redirect("/runs", notice=f"Generated daily report: {report_path}.")

    return app


def _base_context(request: Request, *, notice: str | None = None, error: str | None = None) -> dict[str, Any]:
    """Build shared template context."""

    return {"request": request, "notice": notice, "error": error}


def _session_factory(request: Request) -> sessionmaker[Session]:
    """Return the configured session factory."""

    return request.app.state.session_factory


def _session(request: Request) -> Session:
    """Create a DB session for one request."""

    return _session_factory(request)()


def _source_config_path(request: Request) -> Path:
    """Return the active source config path."""

    return request.app.state.source_config_path


def _sources(request: Request) -> list[SourceConfig]:
    """Load source configs for templates."""

    return list_source_configs(_source_config_path(request))


def _recent_artifacts(session: Session, *, limit: int) -> list[Artifact]:
    """Load recent active artifacts."""

    display_timestamp = func.coalesce(Artifact.published_at, Artifact.created_at)
    display_statement = (
        select(Artifact)
        .where(Artifact.status == ArtifactStatus.ACTIVE)
        .order_by(display_timestamp.desc(), Artifact.id.desc())
        .limit(limit)
    )
    created_statement = (
        select(Artifact)
        .where(Artifact.status == ArtifactStatus.ACTIVE)
        .order_by(Artifact.created_at.desc(), Artifact.id.desc())
        .limit(limit)
    )

    artifacts_by_id: dict[int, Artifact] = {}
    for artifact in [
        *session.scalars(display_statement),
        *session.scalars(created_statement),
    ]:
        if artifact.id is not None:
            artifacts_by_id.setdefault(artifact.id, artifact)
    return sorted(
        artifacts_by_id.values(),
        key=lambda artifact: (
            _artifact_sort_timestamp(artifact),
            _datetime_timestamp(artifact.created_at),
            artifact.id or 0,
        ),
        reverse=True,
    )


def _dashboard_candidate_artifacts(session: Session) -> list[Artifact]:
    """Load dashboard candidates without letting raw paper corpus crowd out analyzed papers."""

    artifacts_by_id: dict[int, Artifact] = {}
    for artifact in [
        *_recent_artifacts(session, limit=160),
        *_recent_paper_artifacts(session, limit=2000),
    ]:
        if artifact.id is not None:
            artifacts_by_id.setdefault(artifact.id, artifact)
    return sorted(
        artifacts_by_id.values(),
        key=lambda artifact: (
            _artifact_sort_timestamp(artifact),
            _datetime_timestamp(artifact.created_at),
            artifact.id or 0,
        ),
        reverse=True,
    )


def _recent_paper_artifacts(session: Session, *, limit: int) -> list[Artifact]:
    """Load a wider paper candidate pool for post-filtered academic display."""

    display_timestamp = func.coalesce(Artifact.published_at, Artifact.created_at)
    statement = (
        select(Artifact)
        .where(Artifact.status == ArtifactStatus.ACTIVE)
        .where(Artifact.source_type == SourceType.PAPERS)
        .order_by(display_timestamp.desc(), Artifact.created_at.desc(), Artifact.id.desc())
        .limit(limit)
    )
    return list(session.scalars(statement))


def _paginated_artifacts(
    session: Session,
    *,
    track: str,
    page: int,
    page_size: int,
    search_query: str = "",
) -> tuple[list[Artifact], dict[str, Any]]:
    """Load one time-ordered artifact page from SQLite."""

    normalized_track = track if track in {"all", "academic", "industry"} else "all"
    base_statement = select(Artifact).where(Artifact.status == ArtifactStatus.ACTIVE)
    if normalized_track == "academic":
        base_statement = base_statement.where(Artifact.source_type == SourceType.PAPERS)
    elif normalized_track == "industry":
        base_statement = base_statement.where(Artifact.source_type != SourceType.PAPERS)

    candidates = list(
        session.scalars(
            base_statement.order_by(
                Artifact.published_at.desc().nullslast(),
                Artifact.created_at.desc(),
                Artifact.id.desc(),
            )
        )
    )
    display_items = [artifact for artifact in candidates if should_display_artifact(artifact)]
    if search_query:
        display_items = [artifact for artifact in display_items if _artifact_matches_search(artifact, search_query)]
    total_items = len(display_items)
    total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 1
    current_page = min(max(1, page), total_pages)
    offset = (current_page - 1) * page_size
    page_items = display_items[offset : offset + page_size]
    first_item = offset + 1 if page_items else 0
    last_item = offset + len(page_items)

    return page_items, {
        "page": current_page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "first_item": first_item,
        "last_item": last_item,
        "has_previous": current_page > 1,
        "has_next": current_page < total_pages,
        "previous_page": max(1, current_page - 1),
        "next_page": min(total_pages, current_page + 1),
        "query_suffix": f"&q={quote(search_query)}" if search_query else "",
    }


def _normalize_search_query(value: str) -> str:
    """Normalize one artifact search query for stable matching."""

    return " ".join(str(value or "").strip().split())


def _artifact_matches_search(artifact: Artifact, search_query: str) -> bool:
    """Return whether one displayable artifact matches all search terms."""

    terms = [term.casefold() for term in search_query.split() if term.strip()]
    if not terms:
        return True

    score_breakdown: dict[str, Any] = dict(artifact.score_breakdown or {})
    focus_labels = score_breakdown.get("academic_focus_labels")
    focus_text = " ".join(str(label) for label in focus_labels) if isinstance(focus_labels, list) else ""
    haystack = " ".join(
        str(value or "")
        for value in [
            artifact.title,
            artifact.source_name,
            artifact.source_tier,
            artifact.abstract,
            artifact.summary_l1,
            artifact.summary_l2,
            artifact.summary_l3,
            " ".join(str(tag) for tag in artifact.tags or []),
            focus_text,
        ]
    ).casefold()
    return all(term in haystack for term in terms)


def _dashboard_metrics(session: Session, artifacts: list[Artifact], sources: list[SourceConfig]) -> dict[str, int]:
    """Return dashboard counters."""

    total = int(session.scalar(select(func.count(Artifact.id)).where(Artifact.status == ArtifactStatus.ACTIVE)) or 0)
    summarized = int(
        session.scalar(
            select(func.count(Artifact.id))
            .where(Artifact.status == ArtifactStatus.ACTIVE)
            .where(Artifact.summary_l1.is_not(None))
            .where(Artifact.summary_l1 != "")
        )
        or 0
    )
    return {
        "total_artifacts": total,
        "recent_items": len(artifacts),
        "summarized": summarized,
        "enabled_sources": len([source for source in sources if source.enabled]),
        "disabled_sources": len([source for source in sources if not source.enabled]),
        "academic_recent": len([item for item in artifacts if item.source_type == SourceType.PAPERS]),
        "industry_recent": len([item for item in artifacts if item.source_type != SourceType.PAPERS]),
    }


def _dashboard_academic_items(artifacts: list[Artifact], *, dashboard_range: DashboardDateRange) -> list[Artifact]:
    """Return dashboard papers, date-filtering arXiv while keeping conference papers recent."""

    items: list[Artifact] = []
    for artifact in artifacts:
        if artifact.source_type != SourceType.PAPERS:
            continue
        if _is_arxiv_artifact(artifact) and not _artifact_matches_range(artifact, dashboard_range):
            continue
        items.append(artifact)
    return _diverse_academic_items(items, limit=8)


def _industry_sections(
    artifacts: list[Artifact],
    sources: list[SourceConfig],
    *,
    dashboard_range: DashboardDateRange,
) -> list[dict[str, Any]]:
    """Group recent industry artifacts into readable dashboard lanes."""

    grouped: dict[str, list[Artifact]] = {
        "conference": [],
        "blog": [],
        "organization": [],
    }
    for artifact in artifacts:
        if artifact.source_type == SourceType.PAPERS:
            continue
        category = _industry_category(artifact, sources)
        if category != "conference" and not _artifact_matches_range(artifact, dashboard_range):
            continue
        grouped[category].append(artifact)

    return [
        {
            "key": "conference",
            "eyebrow": "Industry conferences",
            "title": "Conference topics",
            "items": _diverse_conference_items(grouped["conference"], limit=8),
            "empty": "No recent conference topics. Crawl Black Hat, DEF CON or BSidesSF sources to populate this lane.",
        },
        {
            "key": "blog",
            "eyebrow": "Research blogs",
            "title": "Blog articles",
            "items": grouped["blog"][:8],
            "empty": f"No research blog articles for {dashboard_range.label}. Change the range or crawl curated blog sources.",
        },
        {
            "key": "organization",
            "eyebrow": "Organizations",
            "title": "Organization updates",
            "items": grouped["organization"][:6],
            "empty": f"No OpenAI, Anthropic or organization updates for {dashboard_range.label}.",
        },
    ]


def _sort_by_score(artifacts: list[Artifact]) -> list[Artifact]:
    """Return artifacts ordered by score, then recency."""

    return sorted(
        artifacts,
        key=lambda artifact: (
            artifact.final_score or 0.0,
            _artifact_sort_timestamp(artifact),
            artifact.id or 0,
        ),
        reverse=True,
    )


def _diverse_conference_items(artifacts: list[Artifact], *, limit: int) -> list[Artifact]:
    """Return top conference items while keeping multiple sources visible."""

    sorted_artifacts = _sort_by_score(artifacts)
    selected: list[Artifact] = []
    selected_ids: set[int] = set()
    seen_sources: set[str] = set()

    for artifact in sorted_artifacts:
        source_key = _source_key(artifact.source_name or "")
        if not source_key or source_key in seen_sources:
            continue
        selected.append(artifact)
        selected_ids.add(artifact.id)
        seen_sources.add(source_key)
        if len(selected) >= limit:
            return selected

    for artifact in sorted_artifacts:
        if artifact.id in selected_ids:
            continue
        selected.append(artifact)
        if len(selected) >= limit:
            break
    return selected


def _diverse_academic_items(artifacts: list[Artifact], *, limit: int) -> list[Artifact]:
    """Return top academic items while keeping conference/preprint sources visible."""

    sorted_artifacts = _sort_by_score(artifacts)
    selected: list[Artifact] = []
    selected_ids: set[int] = set()
    source_counts: dict[str, int] = {}

    for artifact in sorted_artifacts:
        source_key = _source_key(artifact.source_name or "")
        if not source_key or source_key in source_counts:
            continue
        selected.append(artifact)
        if artifact.id is not None:
            selected_ids.add(artifact.id)
        source_counts[source_key] = 1
        if len(selected) >= limit:
            return selected

    for artifact in sorted_artifacts:
        if artifact.id in selected_ids:
            continue
        source_key = _source_key(artifact.source_name or "")
        if source_key and source_counts.get(source_key, 0) >= 2:
            continue
        selected.append(artifact)
        if artifact.id is not None:
            selected_ids.add(artifact.id)
        if source_key:
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
        if len(selected) >= limit:
            return selected

    for artifact in sorted_artifacts:
        if artifact.id in selected_ids:
            continue
        selected.append(artifact)
        if len(selected) >= limit:
            break
    return selected


def _artifact_sort_timestamp(artifact: Artifact) -> float:
    """Return a comparable timestamp for artifact ordering."""

    timestamp = artifact.published_at or artifact.created_at
    return _datetime_timestamp(timestamp)


def _datetime_timestamp(timestamp: datetime | None) -> float:
    """Return a comparable timestamp for a possibly naive datetime."""

    if timestamp is None:
        return 0.0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.timestamp()


def _industry_category(artifact: Artifact, sources: list[SourceConfig]) -> str:
    """Return the dashboard category for one industry artifact."""

    source = _source_for_artifact(artifact, sources)
    if source is not None:
        tags = {tag.lower() for tag in source.tags}
        if "industry-conference" in tags:
            return "conference"
        if source.slug in ORG_SOURCE_SLUGS:
            return "organization"
        if "research-blog" in tags:
            return "blog"

    source_name = _source_key(artifact.source_name or "")
    if any(marker in source_name for marker in CONFERENCE_SOURCE_MARKERS):
        return "conference"
    if "openai" in source_name or "anthropic" in source_name:
        return "organization"
    return "blog"


def _source_for_artifact(artifact: Artifact, sources: list[SourceConfig]) -> SourceConfig | None:
    """Best-effort match an artifact source name to central source config."""

    source_name = _source_key(artifact.source_name or "")
    if not source_name:
        return None
    for source in sources:
        candidates = [source.slug, source.name, source.crawler or "", *source.aliases]
        for candidate in candidates:
            candidate_key = _source_key(candidate)
            if candidate_key and (candidate_key == source_name or candidate_key in source_name):
                return source
    return None


def _source_key(value: str) -> str:
    """Normalize source labels for loose dashboard matching."""

    return " ".join(value.strip().lower().replace("_", "-").split())


def _is_arxiv_artifact(artifact: Artifact) -> bool:
    """Return whether a paper came from arXiv."""

    source_tier = (artifact.source_tier or "").strip().lower()
    source_name = _source_key(artifact.source_name or "")
    return source_tier == "t2-arxiv" or "arxiv" in source_name


def _parse_dashboard_date(raw_value: str | None) -> date:
    """Return the dashboard date, defaulting invalid or missing values to today."""

    if not raw_value:
        return app_today()
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return app_today()


def _parse_dashboard_range(raw_mode: str | None, raw_date: str | None) -> DashboardDateRange:
    """Return a normalized dashboard range selector."""

    mode = (raw_mode or ("custom" if raw_date else "today")).strip().lower()
    if mode not in DASHBOARD_RANGE_MODES:
        mode = "today"

    today = app_today()
    selected_date = _parse_dashboard_date(raw_date)
    if mode == "7d":
        start = today - timedelta(days=6)
        return DashboardDateRange(
            mode="7d",
            start=start,
            end=today,
            selected_date=today,
            label=f"{start.isoformat()} to {today.isoformat()}",
        )
    if mode == "custom":
        return DashboardDateRange(
            mode="custom",
            start=selected_date,
            end=selected_date,
            selected_date=selected_date,
            label=selected_date.isoformat(),
        )
    return DashboardDateRange(
        mode="today",
        start=today,
        end=today,
        selected_date=today,
        label=today.isoformat(),
    )


def _artifact_matches_range(artifact: Artifact, dashboard_range: DashboardDateRange) -> bool:
    """Return whether an artifact belongs to a dashboard date range."""

    timestamp = artifact.published_at or artifact.created_at
    if timestamp is None:
        return False
    artifact_date = local_date(timestamp)
    return dashboard_range.start <= artifact_date <= dashboard_range.end


def _artifact_matches_date(artifact: Artifact, target_date: date) -> bool:
    """Return whether an artifact belongs to a dashboard calendar day."""

    timestamp = artifact.published_at or artifact.created_at
    if timestamp is None:
        return False
    return local_date(timestamp) == target_date


def _run_dashboard_daily_refresh(
    session_factory: sessionmaker[Session],
    engine: Engine,
    status_store: RefreshStatusStore,
) -> None:
    """Run the standard daily refresh from the dashboard background action."""

    try:
        report_path = _run_daily_refresh(
            AppContext(engine=engine, session_factory=session_factory, database_url="", verbose=False),
            target_date=app_today(),
            provider=os.getenv("WEB_DAILY_REFRESH_PROVIDER", "openai"),
            skip_crawl=_env_bool("WEB_DAILY_REFRESH_SKIP_CRAWL", False),
            workers=_env_int("WEB_DAILY_REFRESH_WORKERS", 1, minimum=1),
            request_delay=_env_float("WEB_DAILY_REFRESH_REQUEST_DELAY", 5.0, minimum=0.0),
            academic_personalization=_env_bool("WEB_DAILY_REFRESH_ACADEMIC_PERSONALIZATION", True),
            crawl_scope=os.getenv("WEB_DAILY_REFRESH_CRAWL_SCOPE", "daily"),
            artifact_scope="daily",
            progress=status_store.update,
        )
        status_store.finish(f"Daily refresh complete: {report_path}")
    except Exception:
        logger.exception("Dashboard daily refresh failed")
        status_store.fail("Dashboard daily refresh failed. Check the server log for details.")


def _env_bool(name: str, default: bool) -> bool:
    """Parse a small boolean environment override."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, *, minimum: float) -> float:
    """Parse a bounded float environment override."""

    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _env_int(name: str, default: int, *, minimum: int) -> int:
    """Parse a bounded integer environment override."""

    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _utc_now_iso() -> str:
    """Return a compact UTC timestamp for refresh status."""

    return datetime.now(timezone.utc).isoformat()


async def _form_dict(request: Request) -> dict[str, str]:
    """Parse urlencoded form bodies without adding a multipart dependency."""

    raw_body = await request.body()
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _redirect(path: str, *, notice: str | None = None, error: str | None = None) -> RedirectResponse:
    """Redirect with one optional flash message."""

    separator = "&" if "?" in path else "?"
    if notice:
        path = f"{path}{separator}notice={quote(notice)}"
        separator = "&"
    if error:
        path = f"{path}{separator}error={quote(error)}"
    return RedirectResponse(url=path, status_code=303)
