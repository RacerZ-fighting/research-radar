"""Central source metadata configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from src.models.enums import SourceType

DEFAULT_SOURCE_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "sources.json"


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """One configured external source."""

    slug: str
    name: str
    source_type: SourceType
    tier: str
    track: str
    adapter: str
    enabled: bool
    crawler: str | None
    aliases: tuple[str, ...]
    urls: dict[str, str]
    filters: dict[str, Any]
    tags: tuple[str, ...]
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceConfig":
        """Build a SourceConfig from a JSON object."""

        return cls(
            slug=str(raw["slug"]).strip(),
            name=str(raw["name"]).strip(),
            source_type=SourceType(str(raw["source_type"]).strip()),
            tier=str(raw["tier"]).strip(),
            track=str(raw["track"]).strip(),
            adapter=str(raw["adapter"]).strip(),
            enabled=bool(raw.get("enabled", True)),
            crawler=str(raw["crawler"]).strip() if raw.get("crawler") else None,
            aliases=tuple(str(alias).strip() for alias in raw.get("aliases", []) if str(alias).strip()),
            urls={str(key): str(value) for key, value in dict(raw.get("urls", {})).items()},
            filters=dict(raw.get("filters", {})),
            params=dict(raw.get("params", {})),
            tags=tuple(str(tag).strip() for tag in raw.get("tags", []) if str(tag).strip()),
        )


def load_source_configs(config_path: Path | None = None) -> list[SourceConfig]:
    """Load all source configurations from the central JSON file."""

    path = config_path or DEFAULT_SOURCE_CONFIG_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_sources = payload.get("sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError(f"Source config must contain a list at 'sources': {path}")
    return [SourceConfig.from_dict(raw) for raw in raw_sources if isinstance(raw, dict)]


def source_configs_by_slug(config_path: Path | None = None) -> dict[str, SourceConfig]:
    """Return source configs keyed by slug."""

    return {config.slug: config for config in load_source_configs(config_path)}


def enabled_source_configs(
    *,
    source_type: SourceType | None = None,
    adapters: set[str] | None = None,
    config_path: Path | None = None,
) -> list[SourceConfig]:
    """Return enabled sources, optionally filtered by type and adapter."""

    configs = [config for config in load_source_configs(config_path) if config.enabled]
    if source_type is not None:
        configs = [config for config in configs if config.source_type == source_type]
    if adapters is not None:
        configs = [config for config in configs if config.adapter in adapters]
    return configs


def enabled_crawler_configs(
    *,
    source_type: SourceType | None = None,
    config_path: Path | None = None,
) -> list[SourceConfig]:
    """Return enabled sources backed by in-process crawler classes."""

    return [
        config
        for config in enabled_source_configs(source_type=source_type, adapters={"crawler"}, config_path=config_path)
        if config.crawler
    ]


def resolve_source_slug(raw_source: str, config_path: Path | None = None) -> str:
    """Resolve user input or aliases to a canonical source slug."""

    candidate = _normalize_key(raw_source)
    for config in load_source_configs(config_path):
        keys = [config.slug, config.name, config.crawler or "", *config.aliases]
        normalized_keys = {_normalize_key(key) for key in keys if key}
        if candidate in normalized_keys:
            return config.slug
    return raw_source.strip().lower()


def infer_source_tier(source_name: str, source_type: SourceType, config_path: Path | None = None) -> str:
    """Infer a source tier from central source metadata."""

    source_key = _normalize_key(source_name)
    for config in load_source_configs(config_path):
        if config.source_type != source_type:
            continue
        keys = [config.slug, config.name, config.crawler or "", *config.aliases]
        for key in keys:
            normalized = _normalize_key(key)
            if normalized and (normalized == source_key or normalized in source_key):
                return config.tier

    if source_type == SourceType.PAPERS:
        return "paper"
    if source_type == SourceType.BLOGS:
        return "blog"
    return "unknown"


def _normalize_key(value: str) -> str:
    """Normalize source names and slugs for loose matching."""

    return " ".join(value.strip().lower().replace("_", "-").split())
