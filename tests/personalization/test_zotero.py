"""Tests for Zotero corpus parsing and matching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.models.artifact import Artifact
from src.models.enums import SourceType
from src.personalization.zotero import ZoteroCorpus, ZoteroMatcher, build_zotero_corpus_from_env


def test_zotero_csl_json_loads_better_csl_export(tmp_path: Path) -> None:
    """Better CSL JSON should normalize title, authors, abstract, venue, and tags."""

    path = tmp_path / "zotero.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "paper-1",
                    "title": "Prompt Injection Defenses for LLM Agents",
                    "author": [{"given": "Alice", "family": "Example"}],
                    "abstract": "We study prompt injection attacks against tool-using agents.",
                    "container-title": "USENIX Security",
                    "issued": {"date-parts": [[2025]]},
                    "keyword": "prompt-injection,llm-security",
                    "URL": "https://example.com/paper",
                }
            ]
        ),
        encoding="utf-8",
    )

    corpus = ZoteroCorpus.from_csl_json(path)

    assert len(corpus.items) == 1
    item = corpus.items[0]
    assert item.title == "Prompt Injection Defenses for LLM Agents"
    assert item.authors == ("Alice Example",)
    assert item.venue == "USENIX Security"
    assert item.year == 2025
    assert item.tags == ("prompt-injection", "llm-security")


def test_zotero_matcher_returns_related_items(tmp_path: Path) -> None:
    """Matcher should rank topically related Zotero papers above unrelated ones."""

    path = tmp_path / "zotero.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "related",
                    "title": "Prompt Injection Defenses for Tool-Using LLM Agents",
                    "abstract": "Prompt injection attacks and defenses for agentic systems.",
                    "keyword": "prompt-injection,llm-security,agent-security,tool-use,defense",
                },
                {
                    "id": "unrelated",
                    "title": "Quantum Materials for Batteries",
                    "abstract": "A chemistry study of battery materials.",
                },
            ]
        ),
        encoding="utf-8",
    )
    artifact = Artifact(
        title="An Empirical Evaluation of Prompt Injection Vulnerabilities in Large Language Models",
        authors=["Bob Researcher"],
        source_type=SourceType.PAPERS,
        source_tier="t2-arxiv",
        source_name="arXiv",
        source_url="https://arxiv.org/abs/2607.00001",
        abstract="This paper evaluates multilingual prompt injection attacks against LLMs.",
        tags=["prompt-injection", "llm-security"],
    )

    matches = ZoteroMatcher(ZoteroCorpus.from_csl_json(path)).match(artifact, top_k=2)

    assert matches[0]["title"] == "Prompt Injection Defenses for Tool-Using LLM Agents"
    assert matches[0]["topics"] == ["prompt-injection", "llm-security", "agent-security"]
    assert all(match["title"] != "Quantum Materials for Batteries" for match in matches)


def test_zotero_api_max_items_env_controls_fetch_size(monkeypatch) -> None:
    """ZOTERO_MAX_ITEMS should allow Zotero API corpora larger than 500 items."""

    calls: list[dict[str, int]] = []

    class StubResponse:
        def __init__(self, payload: list[dict[str, object]]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return self._payload

    def fake_get(url, *, params, headers, timeout):  # noqa: ANN001
        start = int(params["start"])
        limit = int(params["limit"])
        calls.append({"start": start, "limit": limit})
        remaining = max(0, 600 - start)
        count = min(limit, remaining)
        payload = [
            {
                "key": f"item-{start + index}",
                "data": {
                    "title": f"Paper {start + index}",
                    "creators": [],
                    "tags": [],
                },
            }
            for index in range(count)
        ]
        return StubResponse(payload)

    monkeypatch.setenv("ZOTERO_USER_ID", "123")
    monkeypatch.setenv("ZOTERO_API_KEY", "secret")
    monkeypatch.setenv("ZOTERO_MAX_ITEMS", "600")
    monkeypatch.delenv("ZOTERO_CSL_JSON", raising=False)
    monkeypatch.delenv("ZOTERO_GROUP_ID", raising=False)

    with patch("src.personalization.zotero.requests.get", side_effect=fake_get):
        corpus = build_zotero_corpus_from_env()

    assert len(corpus.items) == 600
    assert calls[-1] == {"start": 500, "limit": 100}
