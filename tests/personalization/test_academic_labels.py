"""Tests for AI academic focus label generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.pipelines.academic_labels import AcademicLabelPipeline
from src.repositories.artifact_repository import ArtifactRepository


class StubLabelClient:
    """Deterministic LLM stub for academic focus labels."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, prompt: str, **kwargs) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        return json.dumps(
            {
                "labels": ["prompt injection 防护", "LLM agent 工具调用"],
                "reason": "论文和 Zotero 证据都指向 LLM agent 的提示注入风险。",
            },
            ensure_ascii=False,
        )


class AcademicLabelPipelineTestCase(unittest.TestCase):
    """Integration tests for academic focus labels."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.engine = create_database_engine(f"sqlite+pysqlite:///{self.workspace / 'test.db'}")
        create_all_tables(self.engine)
        self.session_factory = create_session_factory(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_pipeline_writes_focus_labels(self) -> None:
        """Pipeline should persist concise focus labels into score_breakdown."""

        session = self.session_factory()
        try:
            artifact = ArtifactRepository(session).save(
                Artifact(
                    title="Prompt Injection Vulnerabilities in LLM Agents",
                    authors=["Alice Example"],
                    source_type=SourceType.PAPERS,
                    source_tier="t2-arxiv",
                    source_name="arXiv",
                    source_url="https://arxiv.org/abs/2607.00001",
                    abstract="We evaluate prompt injection attacks against tool-using LLM agents.",
                    tags=["llm-security"],
                    score_breakdown={
                        "zotero_similarity": 0.32,
                        "zotero_matches": [
                            {
                                "title": "Prompt Injection Defenses for Tool-Using LLM Agents",
                                "topics": ["prompt-injection", "agent-security"],
                            }
                        ],
                    },
                    status=ArtifactStatus.ACTIVE,
                )
            )
        finally:
            session.close()

        stub = StubLabelClient()
        updated = AcademicLabelPipeline(session_factory=self.session_factory, llm_client=stub).process(artifact.id)

        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0].score_breakdown["academic_focus_labels"], ["prompt injection 防护", "LLM agent 工具调用"])
        self.assertIn("academic_focus_", stub.calls[0]["cache_key"])
