"""Tests for the enrichment pipeline."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from sqlalchemy.orm import Session

from src.db.session import create_all_tables, create_database_engine, create_session_factory
from src.exceptions import LLMError
from src.llm.base import ModelTier
from src.models.artifact import Artifact
from src.models.enums import ArtifactStatus, SourceType
from src.models.profile import Profile
from src.pipelines.enrichment import EnrichmentPipeline
from src.repositories.artifact_repository import ArtifactRepository


class StubLLMClient:
    """Tiny LLM stub with queued responses."""

    def __init__(self, responses: list[object]) -> None:
        """Store deterministic LLM outcomes."""

        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []
        self.lock = threading.Lock()

    def generate(
        self,
        prompt: str,
        model_tier: ModelTier = ModelTier.STANDARD,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        cache_key: str | None = None,
    ) -> str:
        """Return the next queued response or raise the next queued error."""

        with self.lock:
            self.calls.append(
                {
                    "prompt": prompt,
                    "model_tier": model_tier,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "cache_key": cache_key,
                }
            )
            if not self.responses:
                raise AssertionError("No queued response in StubLLMClient")
            response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return str(response)


class EnrichmentPipelineTestCase(unittest.TestCase):
    """Integration-style tests for artifact enrichment."""

    def setUp(self) -> None:
        """Create an isolated database and pipeline dependencies."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        database_path = self.workspace / "test.db"
        database_url = f"sqlite+pysqlite:///{database_path}"
        self.engine = create_database_engine(database_url)
        create_all_tables(self.engine)
        self.session_factory = create_session_factory(self.engine)

    def tearDown(self) -> None:
        """Dispose test resources."""

        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_process_enriches_active_artifacts_with_summary_and_tags(self) -> None:
        """Unenriched active artifacts should receive summary_l1 and tags."""

        llm_client = StubLLMClient(
            [
                '{"summary_l1": "这篇文章概述了浏览器隔离机制中的安全问题，并说明相关攻击面为什么值得持续关注。", '
                '"summary_l3": "文章围绕浏览器隔离机制展开，讨论攻击者如何利用边界不清或实现缺陷影响安全保证。它强调系统组件、攻击面和防护策略之间的关系，适合作为后续判断浏览器安全研究价值的基础材料。", '
                '"tags": ["browser-security", "side-channel"]}'
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact = self._save_artifact(title="Interesting Paper", abstract="Deep browser isolation work.")
        self._save_profile(interests=["browser security"], preferred_topics=["sandboxing"])

        enriched = pipeline.process(None)

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].summary_l1, "这篇文章概述了浏览器隔离机制中的安全问题，并说明相关攻击面为什么值得持续关注。")
        self.assertIn("浏览器隔离机制", enriched[0].summary_l3)
        self.assertEqual(enriched[0].tags, ["browser-security", "side-channel"])
        self.assertEqual(len(llm_client.calls), 1)
        self.assertEqual(llm_client.calls[0]["model_tier"], ModelTier.FAST)
        self.assertEqual(llm_client.calls[0]["max_tokens"], 900)
        self.assertTrue(str(llm_client.calls[0]["cache_key"]).startswith("enrichment_v2-cn-detailed_"))
        self.assertIn("browser security", str(llm_client.calls[0]["prompt"]))

    def test_process_skips_artifacts_that_are_already_enriched(self) -> None:
        """Artifacts with summary and tags should not be sent to the LLM again."""

        llm_client = StubLLMClient(['{"summary_l1": "unused", "tags": ["unused"]}'])
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        self._save_artifact(
            title="Already Enriched",
            summary_l1="Existing summary.",
            summary_l3="Existing detailed summary.",
            tags=["existing-tag"],
        )

        enriched = pipeline.process(None)

        self.assertEqual(enriched, [])
        self.assertEqual(llm_client.calls, [])

    def test_process_reenriches_artifacts_missing_detailed_summary(self) -> None:
        """Artifacts with only old L1 enrichment should receive summary_l3."""

        llm_client = StubLLMClient(
            [
                '{"summary_l1": "旧条目现在会补充中文概览，方便在日报中快速判断是否值得阅读。", '
                '"summary_l3": "这条内容原本只有较短摘要和标签，因此新版本会重新调用 LLM 补齐详细总结。详细总结会说明文章讨论的问题、涉及的系统或方法，以及它对每日情报消费的意义。", '
                '"tags": ["summary-upgrade", "daily-review"]}',
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact = self._save_artifact(
            title="Old Enriched Artifact",
            summary_l1="Old short summary.",
            summary_l3=None,
            tags=["existing-tag"],
        )

        enriched = pipeline.process([artifact.id])

        self.assertEqual(len(enriched), 1)
        self.assertIn("补齐详细总结", enriched[0].summary_l3)
        self.assertEqual(enriched[0].tags, ["existing-tag", "summary-upgrade", "daily-review"])

    def test_cache_key_changes_when_source_text_changes(self) -> None:
        """Enrichment cache keys should not reuse summaries after crawler text improves."""

        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=StubLLMClient([]),
            prompt_template_path=self.workspace / "prompt.md",
        )
        before = self._save_artifact(title="Changing Article", abstract=None)
        after = self._save_artifact(title="Changing Article Copy", abstract="Now the crawler has article body text.")
        after.canonical_id = before.canonical_id

        before_key = pipeline._build_cache_key(before)
        after_key = pipeline._build_cache_key(after)

        self.assertNotEqual(before_key, after_key)
        self.assertTrue(before_key.startswith("enrichment_v2-cn-detailed_"))

    def test_process_continues_when_one_artifact_enrichment_fails(self) -> None:
        """One failed artifact should not prevent the rest from being enriched."""

        llm_client = StubLLMClient(
            [
                LLMError("temporary failure"),
                '{"summary_l1": "Second artifact summary.", "tags": ["network-security"]}',
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        first = self._save_artifact(title="First Artifact")
        second = self._save_artifact(title="Second Artifact")

        enriched = pipeline.process(None)

        self.assertEqual([artifact.title for artifact in enriched], ["First Artifact"])

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            persisted_first = repository.get_by_id(first.id)
            persisted_second = repository.get_by_id(second.id)
            self.assertEqual(persisted_first.summary_l1, "Second artifact summary.")
            self.assertEqual(persisted_first.tags, ["network-security"])
            self.assertIsNone(persisted_second.summary_l1)
        finally:
            session.close()

    def test_process_can_target_specific_artifact_ids(self) -> None:
        """Targeted enrichment should only process the selected artifact ids."""

        llm_client = StubLLMClient(
            [
                '{"summary_l1": "Targeted summary.", "tags": ["program-analysis"]}',
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        targeted = self._save_artifact(title="Targeted Artifact")
        untouched = self._save_artifact(title="Untouched Artifact")

        enriched = pipeline.process([targeted.id])

        self.assertEqual([artifact.id for artifact in enriched], [targeted.id])

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            self.assertEqual(repository.get_by_id(targeted.id).summary_l1, "Targeted summary.")
            self.assertIsNone(repository.get_by_id(untouched.id).summary_l1)
        finally:
            session.close()

    def test_process_salvages_summary_with_unescaped_quotes(self) -> None:
        """Malformed JSON with bare quotes inside summary_l1 should still be recovered."""

        llm_client = StubLLMClient(
            [
                """```json
{
  "summary_l1": "VETEOS is a static analysis tool for EOSIO contracts that detects "Groundhog Day" vulnerabilities.",
  "tags": ["eosio-smart-contracts", "static-analysis", "blockchain-security"]
}
```"""
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact = self._save_artifact(title="VETEOS")

        enriched = pipeline.process([artifact.id])

        self.assertEqual(len(enriched), 1)
        self.assertEqual(
            enriched[0].summary_l1,
            'VETEOS is a static analysis tool for EOSIO contracts that detects "Groundhog Day" vulnerabilities.',
        )
        self.assertEqual(
            enriched[0].summary_l3,
            'VETEOS is a static analysis tool for EOSIO contracts that detects "Groundhog Day" vulnerabilities.',
        )
        self.assertEqual(
            enriched[0].tags,
            ["eosio-smart-contracts", "static-analysis", "blockchain-security"],
        )

    def test_parallel_processing(self) -> None:
        """Parallel enrichment should process multiple artifacts successfully."""

        llm_client = StubLLMClient(
            ['{"summary_l1": "Parallel summary.", "tags": ["parallel-test", "web-security", "analysis"]}'] * 4
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
            max_workers=2,
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact_ids = [self._save_artifact(title=f"Artifact {index}").id for index in range(4)]

        enriched = pipeline.process(artifact_ids)

        self.assertEqual(len(enriched), 4)
        self.assertEqual(len(llm_client.calls), 4)

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            summaries = [repository.get_by_id(artifact_id).summary_l1 for artifact_id in artifact_ids]
            self.assertEqual(summaries.count("Parallel summary."), 4)
        finally:
            session.close()

    def test_parallel_failure_isolation(self) -> None:
        """One parallel worker failure should not block the rest."""

        llm_client = StubLLMClient(
            [
                LLMError("temporary failure"),
                '{"summary_l1": "Recovered summary.", "tags": ["parallel-test", "recovery", "analysis"]}',
                '{"summary_l1": "Recovered summary.", "tags": ["parallel-test", "recovery", "analysis"]}',
                '{"summary_l1": "Recovered summary.", "tags": ["parallel-test", "recovery", "analysis"]}',
            ]
        )
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
            max_workers=2,
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact_ids = [self._save_artifact(title=f"Failure Artifact {index}").id for index in range(4)]

        enriched = pipeline.process(artifact_ids)

        self.assertEqual(len(enriched), 3)
        self.assertEqual(len(llm_client.calls), 4)

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            persisted = [repository.get_by_id(artifact_id) for artifact_id in artifact_ids]
            enriched_count = sum(1 for artifact in persisted if artifact.summary_l1 == "Recovered summary.")
            missing_count = sum(1 for artifact in persisted if artifact.summary_l1 is None)
            self.assertEqual(enriched_count, 3)
            self.assertEqual(missing_count, 1)
        finally:
            session.close()

    def test_request_delay_forces_sequential_processing(self) -> None:
        """Configured request delay should serialize enrichment calls for rate-limited providers."""

        llm_client = StubLLMClient(
            [
                '{"summary_l1": "Delayed summary.", "tags": ["rate-limit", "sequential", "analysis"]}',
                '{"summary_l1": "Delayed summary.", "tags": ["rate-limit", "sequential", "analysis"]}',
                '{"summary_l1": "Delayed summary.", "tags": ["rate-limit", "sequential", "analysis"]}',
            ]
        )
        sleeps: list[float] = []
        pipeline = EnrichmentPipeline(
            session_factory=self.session_factory,
            llm_client=llm_client,
            prompt_template_path=self.workspace / "prompt.md",
            max_workers=3,
            request_delay_seconds=2.5,
            sleep_fn=sleeps.append,
        )
        (self.workspace / "prompt.md").write_text("{{artifact_context}}", encoding="utf-8")
        artifact_ids = [self._save_artifact(title=f"Delayed Artifact {index}").id for index in range(3)]

        enriched = pipeline.process(artifact_ids)

        self.assertEqual(len(enriched), 3)
        self.assertEqual(sleeps, [2.5, 2.5])
        self.assertEqual(len(llm_client.calls), 3)

    def _save_artifact(self, **kwargs) -> Artifact:
        """Persist one artifact with sensible defaults."""

        session: Session = self.session_factory()
        try:
            repository = ArtifactRepository(session)
            return repository.save(
                Artifact(
                    title=kwargs.pop("title", "Test Artifact"),
                    authors=kwargs.pop("authors", ["Alice Example"]),
                    year=kwargs.pop("year", 2026),
                    source_type=kwargs.pop("source_type", SourceType.PAPERS),
                    source_tier=kwargs.pop("source_tier", "top-tier"),
                    source_name=kwargs.pop("source_name", "NDSS"),
                    source_url=kwargs.pop("source_url", "https://example.com/artifact"),
                    abstract=kwargs.pop("abstract", "A useful abstract."),
                    status=kwargs.pop("status", ArtifactStatus.ACTIVE),
                    summary_l1=kwargs.pop("summary_l1", None),
                    tags=kwargs.pop("tags", []),
                    **kwargs,
                )
            )
        finally:
            session.close()

    def _save_profile(self, **kwargs) -> Profile:
        """Persist one active profile for prompt-context tests."""

        session: Session = self.session_factory()
        try:
            profile = Profile(
                profile_version=kwargs.pop("profile_version", "v1"),
                interests=kwargs.pop("interests", []),
                preferences=kwargs.pop("preferences", {}),
                preferred_topics=kwargs.pop("preferred_topics", []),
                is_active=kwargs.pop("is_active", True),
                **kwargs,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile
        finally:
            session.close()
