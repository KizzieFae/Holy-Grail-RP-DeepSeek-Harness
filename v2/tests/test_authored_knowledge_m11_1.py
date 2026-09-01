"""M11.1 authored KnowledgeService and ContextAssembly integration tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.paths import characters_data_dir  # noqa: E402
from domain_api.contract import (  # noqa: E402
    ContextPrepareRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.knowledge_test_helpers import retrieve_authored_text  # noqa: E402


class AuthoredKnowledgeM111Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)
        self.knowledge = self.repo.knowledge_service

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _prepare_kizzie_manifest(self, session_id: str):
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        return self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-kizzie",
                character_id="Kizzie",
                role="recovering_demi_human",
                turn_index=0,
                attempt_index=0,
            )
        )

    def _authored_for(self, session_id: str, character_id: str) -> tuple[list[str], list[str]]:
        fixture = self.repo.require(session_id)
        return retrieve_authored_text(self.knowledge, fixture, character_id=character_id)

    def test_authored_lore_reaches_intended_character_only(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        kizzie_manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        willow_round = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=info.hg_session_id)
        ).hg_round_id
        willow_manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=info.hg_session_id,
                hg_round_id=willow_round,
                inference_id="inf-willow",
                character_id="Willow Reeves",
                role="protector",
                turn_index=0,
                attempt_index=0,
            )
        )

        kizzie_char, kizzie_scene = self._authored_for(info.hg_session_id, "Kizzie")
        willow_char, _willow_scene = self._authored_for(info.hg_session_id, "Willow Reeves")
        kizzie_authored = kizzie_char + kizzie_scene
        willow_authored = willow_char
        self.assertTrue(kizzie_authored)
        self.assertTrue(any("one-tailed kitsune" in c.lower() for c in kizzie_authored))
        self.assertFalse(any("one-tailed kitsune" in c.lower() for c in willow_authored))
        self.assertTrue(any("willow reeves" in c.lower() for c in willow_authored))

    def test_scene_reference_reaches_both_characters(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        kizzie_manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        willow_round = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=info.hg_session_id)
        ).hg_round_id
        willow_manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=info.hg_session_id,
                hg_round_id=willow_round,
                inference_id="inf-willow",
                character_id="Willow Reeves",
                role="protector",
                turn_index=0,
                attempt_index=0,
            )
        )
        kizzie_char, kizzie_scene = self._authored_for(info.hg_session_id, "Kizzie")
        willow_char, willow_scene = self._authored_for(info.hg_session_id, "Willow Reeves")
        self.assertTrue(kizzie_scene or kizzie_char)
        self.assertTrue(willow_scene or willow_char)

    def test_authority_precedence_scene_state_over_authored_reference(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "minimal"},
            location="Authoritative Workshop",
        )
        manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        fixture = self.repo.require(info.hg_session_id)
        character_records, _scene_records = self.knowledge.retrieve_authored(
            fixture, character_id="Kizzie"
        )
        self.assertTrue(character_records)
        self.assertEqual(scene.authority_class, "authoritative")
        self.assertEqual(character_records[0].authority_class, "suggestive")
        self.assertIn("Authoritative Workshop", scene.content)
        self.assertIn("authoritative", scene.content.lower())

    def test_snapshot_stability_after_card_edit(self) -> None:
        chars_dir = characters_data_dir()
        fixture_dir = Path(self._tmpdir) / "chars"
        fixture_dir.mkdir()
        fixture_path = fixture_dir / "kizzie.json"
        shutil.copy(chars_dir / "kizzie.json", fixture_path)

        info = self.kernel.create_session(
            characters=["kizzie"],
            characters_dir=fixture_dir,
        )
        session_id = info.hg_session_id
        before_char, _ = self._authored_for(session_id, "Kizzie")
        before_text = "\n".join(before_char)

        mutated = json.loads(fixture_path.read_text(encoding="utf-8"))
        mutated["lore_facts"] = ["Mutated lore that must not appear in reopened session."]
        fixture_path.write_text(json.dumps(mutated), encoding="utf-8")
        self.repo.clear_cache()

        after_char, _ = self._authored_for(session_id, "Kizzie")
        after_text = "\n".join(after_char)
        self.assertEqual(before_text, after_text)
        self.assertIn("one-tailed Kitsune", after_text)
        self.assertNotIn("Mutated lore", after_text)

    def test_memory_and_knowledge_lanes_remain_separate(self) -> None:
        info = self.kernel.create_session(characters=["kizzie"])
        session_id = info.hg_session_id
        fixture = self.repo.require(session_id)
        before_summary = list(
            fixture.character_states["Kizzie"].character_memory_summary
        )
        self.kernel.record_user_turn(
            UserTurnRecordRequest.from_content(
                hg_session_id=session_id,
                content="Kizzie, remember this conversation.",
                speaker="Traveler",
            )
        )
        manifest = self._prepare_kizzie_manifest(session_id)
        after_fixture = self.repo.require(session_id)
        after_summary = list(
            after_fixture.character_states["Kizzie"].character_memory_summary
        )
        kinds = {c.source_kind for c in manifest.contributions}
        char_text, _ = self._authored_for(session_id, "Kizzie")
        self.assertTrue(char_text)
        self.assertNotIn("authored_character_knowledge", kinds)
        self.assertEqual(before_summary, after_summary)

    def test_lore_not_in_character_private_lane(self) -> None:
        info = self.kernel.create_session(characters=["kizzie"])
        manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        private = [c for c in manifest.contributions if c.source_kind == "character_private"]
        char_text, _ = self._authored_for(info.hg_session_id, "Kizzie")
        self.assertFalse(private)
        self.assertTrue(char_text)
        joined_private = "\n".join(c.content for c in private)
        self.assertNotIn("Kitsune", joined_private)

    def test_authored_record_caps(self) -> None:
        fixture = self.repo.require(
            self.kernel.create_session(characters=["kizzie"]).hg_session_id
        )
        card = dict(fixture.setup_snapshot["character_cards"]["kizzie"])
        card["lore_facts"] = [f"Lore line {index}" for index in range(10)]
        fixture.setup_snapshot["character_cards"]["kizzie"] = card
        self.repo.persist(fixture)
        character_records, scene_records = self.knowledge.retrieve_authored(
            fixture, character_id="Kizzie"
        )
        self.assertEqual(len(character_records), 4)
        self.assertLessEqual(len(scene_records), 3)


if __name__ == "__main__":
    unittest.main()
