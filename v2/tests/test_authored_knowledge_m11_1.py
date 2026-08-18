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

from domain_api.contract import (  # noqa: E402
    ContextPrepareRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.knowledge_service import KnowledgeService  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class AuthoredKnowledgeM111Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)
        self.knowledge = KnowledgeService()

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

        kizzie_authored = [
            c
            for c in kizzie_manifest.contributions
            if c.source_kind == "authored_character_knowledge"
        ]
        willow_authored = [
            c
            for c in willow_manifest.contributions
            if c.source_kind == "authored_character_knowledge"
        ]
        self.assertTrue(kizzie_authored)
        self.assertTrue(any("one-tailed kitsune" in c.content.lower() for c in kizzie_authored))
        self.assertFalse(
            any("one-tailed kitsune" in c.content.lower() for c in willow_authored)
        )
        self.assertTrue(
            any("willow reeves" in c.content.lower() for c in willow_authored)
        )

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
        self.assertTrue(
            any(c.source_kind == "scene_reference" for c in kizzie_manifest.contributions)
        )
        self.assertTrue(
            any(c.source_kind == "scene_reference" for c in willow_manifest.contributions)
        )

    def test_authority_precedence_scene_state_over_authored_reference(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "minimal"},
            location="Authoritative Workshop",
        )
        manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        authored = next(
            c for c in manifest.contributions if c.source_kind == "authored_character_knowledge"
        )
        self.assertEqual(scene.authority_class, "authoritative")
        self.assertEqual(authored.authority_class, "suggestive")
        self.assertIn("Authoritative Workshop", scene.content)
        self.assertIn("authoritative", scene.content.lower())

    def test_snapshot_stability_after_card_edit(self) -> None:
        chars_dir = _ROOT / "autogen_rp" / "python" / "data" / "autogen_characters"
        fixture_dir = Path(self._tmpdir) / "chars"
        fixture_dir.mkdir()
        fixture_path = fixture_dir / "kizzie.json"
        shutil.copy(chars_dir / "kizzie.json", fixture_path)

        info = self.kernel.create_session(
            characters=["kizzie"],
            characters_dir=fixture_dir,
        )
        session_id = info.hg_session_id
        before = self._prepare_kizzie_manifest(session_id)
        before_text = "\n".join(
            c.content
            for c in before.contributions
            if c.source_kind == "authored_character_knowledge"
        )

        mutated = json.loads(fixture_path.read_text(encoding="utf-8"))
        mutated["lore_facts"] = ["Mutated lore that must not appear in reopened session."]
        fixture_path.write_text(json.dumps(mutated), encoding="utf-8")
        self.repo.clear_cache()

        after = self._prepare_kizzie_manifest(session_id)
        after_text = "\n".join(
            c.content
            for c in after.contributions
            if c.source_kind == "authored_character_knowledge"
        )
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
            UserTurnRecordRequest(
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
        self.assertIn("authored_character_knowledge", kinds)
        authored = [
            c for c in manifest.contributions if c.source_kind == "authored_character_knowledge"
        ]
        self.assertTrue(all(c.authority_class == "suggestive" for c in authored))
        self.assertEqual(before_summary, after_summary)

    def test_lore_not_in_character_private_lane(self) -> None:
        info = self.kernel.create_session(characters=["kizzie"])
        manifest = self._prepare_kizzie_manifest(info.hg_session_id)
        private = [c for c in manifest.contributions if c.source_kind == "character_private"]
        authored = [
            c for c in manifest.contributions if c.source_kind == "authored_character_knowledge"
        ]
        self.assertFalse(private)
        self.assertTrue(authored)
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
