"""Crawl-related CLI commands."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import click

from src.cli.main import handle_command_errors
from src.config.sources import enabled_source_configs, resolve_source_slug
from src.crawlers.registry import BLOG_CRAWLER_REGISTRY, PAPER_CRAWLER_REGISTRY
from src.exceptions import CrawlerError
from src.models.enums import SourceType
from src.timezone import app_today

logger = logging.getLogger(__name__)
DAILY_PAPER_SOURCE_SLUGS = {"arxiv"}


@click.command("crawl")
@click.option("--source", type=str, default=None, help="Specific source slug to crawl.")
@click.option("--years", type=str, default=None, help='Comma-separated years, e.g. "2025,2026".')
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True, writable=True),
    default=Path("data/raw"),
    show_default=True,
    help="Output directory for raw JSON files.",
)
@handle_command_errors
def crawl_command(source: str | None, years: str | None, output_dir: Path) -> None:
    """Run one or more crawlers and persist raw JSON."""

    target_output_dir = output_dir.resolve()
    target_output_dir.mkdir(parents=True, exist_ok=True)
    year_list = _parse_years(years)

    if source is None:
        _crawl_all_sources(year_list, target_output_dir)
        return

    normalized_source = _resolve_source_slug(source)
    if normalized_source in PAPER_CRAWLER_REGISTRY:
        crawler = PAPER_CRAWLER_REGISTRY[normalized_source]()
        items = crawler.fetch_papers(year_list)
        output_path = crawler.save_raw(items, target_output_dir / "papers", metadata={"years": year_list})
        click.echo(f"Crawled {normalized_source}: {len(items)} items -> {output_path}")
        return

    if normalized_source in BLOG_CRAWLER_REGISTRY:
        crawler = BLOG_CRAWLER_REGISTRY[normalized_source]()
        items = crawler.fetch_articles(limit=20)
        output_path = crawler.save_raw(items, target_output_dir / "blogs", metadata={"limit": 20})
        click.echo(f"Crawled {normalized_source}: {len(items)} items -> {output_path}")
        return

    raise click.ClickException(f"Unknown source: {source}")


def _parse_years(raw_years: str | None) -> list[int]:
    """Parse a comma-separated year list or default to the current year."""

    if raw_years is None:
        return [app_today().year]

    values = [item.strip() for item in raw_years.split(",") if item.strip()]
    if not values:
        return [app_today().year]

    try:
        return list(dict.fromkeys(int(value) for value in values))
    except ValueError as exc:
        raise click.ClickException(f"Invalid year list: {raw_years}") from exc


def _resolve_source_slug(raw_source: str) -> str:
    """Resolve one source slug while tolerating underscore/hyphen variants."""

    candidate = resolve_source_slug(raw_source)
    if candidate in PAPER_CRAWLER_REGISTRY or candidate in BLOG_CRAWLER_REGISTRY:
        return candidate

    hyphenated = candidate.replace("_", "-")
    if hyphenated in PAPER_CRAWLER_REGISTRY or hyphenated in BLOG_CRAWLER_REGISTRY:
        return hyphenated

    underscored = candidate.replace("-", "_")
    if underscored in PAPER_CRAWLER_REGISTRY or underscored in BLOG_CRAWLER_REGISTRY:
        return underscored

    return candidate


def _crawl_all_sources(years: list[int], output_dir: Path) -> None:
    """Run all registered crawlers."""

    for name, crawler_cls in PAPER_CRAWLER_REGISTRY.items():
        crawler = crawler_cls()
        try:
            items = crawler.fetch_papers(years)
            output_path = crawler.save_raw(items, output_dir / "papers", metadata={"years": years})
        except CrawlerError as exc:
            logger.warning("Skipping failed crawler %s: %s", name, exc)
            click.echo(f"Skipped {name}: {exc}", err=True)
            continue
        else:
            logger.info("Crawled %s -> %s", name, output_path)
            click.echo(f"Crawled {name}: {len(items)} items -> {output_path}")

    for name, crawler_cls in BLOG_CRAWLER_REGISTRY.items():
        crawler = crawler_cls()
        try:
            items = crawler.fetch_articles(limit=20)
            output_path = crawler.save_raw(items, output_dir / "blogs", metadata={"limit": 20})
        except CrawlerError as exc:
            logger.warning("Skipping failed crawler %s: %s", name, exc)
            click.echo(f"Skipped {name}: {exc}", err=True)
            continue
        else:
            logger.info("Crawled %s -> %s", name, output_path)
            click.echo(f"Crawled {name}: {len(items)} items -> {output_path}")


def _crawl_daily_sources(
    years: list[int],
    output_dir: Path,
    *,
    progress: Callable[[str, int, str], None] | None = None,
    fail_fast: bool = False,
) -> None:
    """Run daily crawler sources, excluding heavyweight conference paper crawlers."""

    daily_paper_items = [
        (name, crawler_cls)
        for name, crawler_cls in PAPER_CRAWLER_REGISTRY.items()
        if name in DAILY_PAPER_SOURCE_SLUGS
    ]
    daily_blog_slugs = _daily_blog_source_slugs()
    daily_blog_items = [
        (name, crawler_cls)
        for name, crawler_cls in BLOG_CRAWLER_REGISTRY.items()
        if name in daily_blog_slugs
    ]
    total_sources = max(1, len(daily_paper_items) + len(daily_blog_items))
    source_index = 0

    for name, crawler_cls in daily_paper_items:
        if name not in DAILY_PAPER_SOURCE_SLUGS:
            continue
        source_index += 1
        _emit_crawl_progress(progress, name, source_index, total_sources)
        crawler = crawler_cls()
        if fail_fast:
            _configure_crawler_fail_fast(crawler)
        try:
            items = crawler.fetch_papers(years)
            output_path = crawler.save_raw(items, output_dir / "papers", metadata={"years": years, "scope": "daily"})
        except CrawlerError as exc:
            logger.warning("Skipping failed crawler %s: %s", name, exc)
            click.echo(f"Skipped {name}: {exc}", err=True)
            continue
        else:
            logger.info("Crawled %s -> %s", name, output_path)
            click.echo(f"Crawled {name}: {len(items)} items -> {output_path}")

    for name, crawler_cls in daily_blog_items:
        source_index += 1
        _emit_crawl_progress(progress, name, source_index, total_sources)
        crawler = crawler_cls()
        if fail_fast:
            _configure_crawler_fail_fast(crawler)
        try:
            items = crawler.fetch_articles(limit=20)
            output_path = crawler.save_raw(items, output_dir / "blogs", metadata={"limit": 20, "scope": "daily"})
        except CrawlerError as exc:
            logger.warning("Skipping failed crawler %s: %s", name, exc)
            click.echo(f"Skipped {name}: {exc}", err=True)
            continue
        else:
            logger.info("Crawled %s -> %s", name, output_path)
            click.echo(f"Crawled {name}: {len(items)} items -> {output_path}")


def _daily_blog_source_slugs() -> set[str]:
    """Return blog-like sources suitable for daily refresh."""

    excluded_tags = {"industry-conference", "daily-disabled", "unstable-daily"}
    return {
        config.slug
        for config in enabled_source_configs(source_type=SourceType.BLOGS)
        if not ({tag.lower() for tag in config.tags} & excluded_tags)
    }


def _configure_crawler_fail_fast(crawler: object) -> None:
    """Reduce per-source wait time for interactive dashboard refresh."""

    if not hasattr(crawler, "_build_session"):
        return
    setattr(crawler, "timeout", min(int(getattr(crawler, "timeout", 10) or 10), 5))
    setattr(crawler, "max_retries", 0)
    setattr(crawler, "session", crawler._build_session())


def _emit_crawl_progress(
    progress: Callable[[str, int, str], None] | None,
    source_name: str,
    source_index: int,
    total_sources: int,
) -> None:
    """Emit source-level crawl progress for Dashboard."""

    if progress is None:
        return
    percent = 10 + int((source_index - 1) / total_sources * 16)
    progress("Crawling sources", percent, f"Crawling {source_name} ({source_index}/{total_sources}).")
