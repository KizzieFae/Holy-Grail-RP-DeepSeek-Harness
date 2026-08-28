"""M12.7 retrieval-index capability migration tests."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.paths import characters_data_dir, holy_grail_data_dir  # noqa: E402

from domain_api.authored_knowledge import AuthoredKnowledgeRecord
from domain_api.compiled_index_provider import CompiledIndexRetrievalProvider
from domain_api.contract import ContextPrepareRequest, RoundStartRequest
from domain_api.kernel import DomainKernel
from domain_api.knowledge_service import KnowledgeService
from domain_api.retrieval_selection import (
    RetrievalQueryContext,
    merge_authored_record_sets,
    select_retrieval_records,
)
from domain_api.session_repository import SessionRepository
from domain_api.knowledge_test_helpers import retrieve_authored_text


class RetrievalIndexM127Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)
        self.knowledge = self.repo.knowledge_service

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _prepare_manifest(self, session_id: str, character_id: str):
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        return self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id=f"inf-{character_id}",
                character_id=character_id,
                role="character",
                turn_index=0,
                attempt_index=0,
            )
        )

    def test_template_role_slots_reach_scene_reference_lane(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        fixture = self.repo.require(info.hg_session_id)
        _char_text, scene_text = retrieve_authored_text(self.knowledge, fixture, character_id="Kizzie")
        joined = "\n".join(scene_text)
        self.assertTrue(scene_text)
        self.assertIn("role=protector", joined)
        self.assertIn("role=recovering_demi_human", joined)
        self.assertIn("apartment", joined.lower())

    def test_compiled_index_supplements_without_duplicating_snapshot_lore(self) -> None:
        pilot_index = (
            holy_grail_data_dir()
            / "retrieval"
            / "compiled"
            / "operational_pilot_v3.json"
        )
        provider = CompiledIndexRetrievalProvider(pilot_index)
        self.assertTrue(provider.is_configured())
        chunks = provider.query(
            RetrievalQueryContext(
                character_file_id="harley_quinn",
                character_display_name="Harley Quinn",
                session_template_id="arkham_asylum_cell_intake",
                character_index_keys=("Harley_Quinn", "harley_quinn", "Harley Quinn"),
            )
        )
        self.assertTrue(chunks)
        template_chunks = [
            c for c in chunks if c.provenance.get("knowledge_lane") == "scene_reference"
        ]
        self.assertTrue(any("role=cell_resident" in c.content for c in template_chunks))

        service = KnowledgeService(
            retrieval_provider=provider,
        )
        info = self.kernel.create_session(characters=["kizzie"])
        fixture = self.repo.require(info.hg_session_id)
        snapshot_records = service.compile_snapshot_records(fixture)
        merged, dedupe = merge_authored_record_sets(snapshot_records, chunks)
        self.assertEqual(dedupe, 0)
        self.assertGreater(len(merged), len(snapshot_records))

    def test_multi_character_isolation_with_compiled_index(self) -> None:
        pilot_index = (
            holy_grail_data_dir()
            / "retrieval"
            / "compiled"
            / "operational_pilot_v3.json"
        )
        self.repo.knowledge_service = KnowledgeService(
            scope_repo=self.repo.knowledge_service.scope_repo,
            retrieval_provider=CompiledIndexRetrievalProvider(pilot_index),
        )
        self.knowledge = self.repo.knowledge_service

        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        fixture = self.repo.require(info.hg_session_id)
        kizzie_char, _ = retrieve_authored_text(self.knowledge, fixture, character_id="Kizzie")
        willow_char, _ = retrieve_authored_text(self.knowledge, fixture, character_id="Willow Reeves")
        kizzie_authored = "\n".join(kizzie_char)
        willow_authored = "\n".join(willow_char)
        self.assertIn("one-tailed kitsune", kizzie_authored.lower())
        self.assertNotIn("one-tailed kitsune", willow_authored.lower())
        self.assertIn("willow reeves", willow_authored.lower())
        self.assertNotIn("willow reeves", kizzie_authored.lower())

    def test_snapshot_stability_after_source_edit(self) -> None:
        chars_dir = characters_data_dir()
        fixture_dir = Path(self._tmpdir) / "chars"
        fixture_dir.mkdir()
        fixture_path = fixture_dir / "kizzie.json"
        shutil.copy(chars_dir / "kizzie.json", fixture_path)

        info = self.kernel.create_session(
            characters=["kizzie"],
            characters_dir=fixture_dir,
        )
        before = self.knowledge.retrieve_authored(
            self.repo.require(info.hg_session_id), character_id="Kizzie"
        )
        before_ids = {r.knowledge_id for batch in before for r in batch}

        mutated = json.loads(fixture_path.read_text(encoding="utf-8"))
        mutated["lore_facts"] = ["Mutated lore must not appear after reopen."]
        mutated["scene_template"] = {"premise": "Mutated premise"}
        fixture_path.write_text(json.dumps(mutated), encoding="utf-8")
        self.repo.clear_cache()

        after = self.knowledge.retrieve_authored(
            self.repo.open_session(info.hg_session_id), character_id="Kizzie"
        )
        after_ids = {r.knowledge_id for batch in after for r in batch}
        self.assertEqual(before_ids, after_ids)

    def test_global_caps_are_enforced(self) -> None:
        records = [
            AuthoredKnowledgeRecord(
                knowledge_id=f"id-{index}",
                knowledge_kind="lore_reference",
                content=f"Lore item {index}",
                authority_class="suggestive",
                visibility="character_scoped",
                subject_character_file_id="kizzie",
                source_kind="character_card",
                source_asset_id="kizzie",
                provenance={
                    "knowledge_lane": "authored_character_knowledge",
                    "source_index": index,
                },
            )
            for index in range(12)
        ]
        character_records, scene_records = select_retrieval_records(
            records,
            character_file_id="kizzie",
            session_template_id=None,
        )
        self.assertLessEqual(len(character_records), 4)
        self.assertEqual(len(scene_records), 0)

    def test_retrieval_diagnostics_exposed_in_manifest_provenance(self) -> None:
        info = self.kernel.create_session(characters=["kizzie"])
        fixture = self.repo.require(info.hg_session_id)
        self.knowledge.retrieve_authored(fixture, character_id="Kizzie")
        diagnostics = self.knowledge.last_retrieval_diagnostics("Kizzie")
        self.assertIsInstance(diagnostics, dict)
        self.assertIn("selected_ids", diagnostics)
        self.assertGreater(diagnostics.get("selected_character_count", 0), 0)

    def test_missing_index_path_does_not_break_session(self) -> None:
        service = KnowledgeService(
            retrieval_provider=CompiledIndexRetrievalProvider("/nonexistent/index.json"),
        )
        info = self.kernel.create_session(characters=["kizzie"])
        fixture = self.repo.require(info.hg_session_id)
        character_records, scene_records = service.retrieve_authored(
            fixture, character_id="Kizzie"
        )
        self.assertTrue(character_records)


if __name__ == "__main__":
    unittest.main()
