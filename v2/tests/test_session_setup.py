"""M9 session setup from authored character cards and scene templates."""

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
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.paths import characters_data_dir  # noqa: E402

from v2.domain_api.contract import ContextPrepareRequest, RoundStartRequest
from v2.domain_api.kernel import DomainKernel
from v2.domain_api.session_repository import SessionRepository
from domain_api.knowledge_test_helpers import retrieve_authored_text
from v2.domain_api.setup_catalog import list_characters_catalog, list_scene_templates_catalog


class SessionSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_catalog_excludes_private_card_fields(self) -> None:
        characters = list_characters_catalog()
        self.assertTrue(characters)
        first = characters[0]
        self.assertIn("character_id", first)
        self.assertIn("display_name", first)
        self.assertNotIn("system_prompt", first)
        self.assertNotIn("lore_facts", first)

        templates = list_scene_templates_catalog()
        self.assertTrue(templates)
        self.assertIn("template_id", templates[0])
        self.assertIn("premise", templates[0])

    def test_create_session_from_real_cards_and_template(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "minimal"},
        )
        self.assertIn("Kizzie", info.present_characters)
        self.assertIn("Willow Reeves", info.present_characters)
        self.assertIsNotNone(info.setup_provenance)
        assert info.setup_provenance is not None
        self.assertEqual(
            sorted(info.setup_provenance["character_ids"]),
            ["kizzie", "willow"],
        )
        self.assertEqual(
            info.setup_provenance["scene_template_id"],
            "celina_apartment_recovery_watch",
        )

        session = self.repo.require(info.hg_session_id)
        self.assertTrue(session.setup_snapshot.get("character_cards"))
        kizzie_card = session.setup_snapshot["character_cards"]["kizzie"]
        self.assertIn("system_prompt", kizzie_card)

        scene_state = session.manager.scene_state
        assert scene_state is not None
        roles = scene_state.role_assignments
        self.assertEqual(roles.get("Kizzie"), "recovering_demi_human")
        self.assertEqual(roles.get("Willow Reeves"), "protector")

    def test_snapshot_survives_card_edit_after_create(self) -> None:
        chars_dir = characters_data_dir()
        fixture_dir = Path(self._tmpdir) / "chars"
        fixture_dir.mkdir()
        fixture_path = fixture_dir / "kizzie.json"
        shutil.copy(chars_dir / "kizzie.json", fixture_path)

        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "custom", "text": "Opening snapshot test."},
            characters_dir=fixture_dir,
        )
        session_id = info.hg_session_id
        original_description = self.repo.require(session_id).character_states[
            "Kizzie"
        ].description

        mutated = json.loads(fixture_path.read_text(encoding="utf-8"))
        mutated["name"] = "Mutated Kizzie"
        mutated["description"] = "Changed after session create."
        fixture_path.write_text(json.dumps(mutated), encoding="utf-8")

        self.repo.clear_cache()
        reopened = self.repo.open_session(session_id)
        self.assertEqual(reopened.cast[0], "Kizzie")
        self.assertEqual(reopened.character_states["Kizzie"].description, original_description)
        self.assertEqual(
            reopened.setup_snapshot["character_cards"]["kizzie"]["name"],
            "Kizzie",
        )

    def test_context_projection_isolates_private_material(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        round_info = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=info.hg_scene_id)
        )
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=info.hg_scene_id,
                hg_round_id=round_info.hg_round_id,
                inference_id="inf-kizzie",
                character_id="Kizzie",
                role="recovering_demi_human",
                turn_index=0,
                attempt_index=0,
            )
        )
        kinds = {item.source_kind for item in manifest.contributions}
        self.assertIn("character_identity", kinds)
        self.assertIn("scene_state", kinds)
        fixture = self.repo.require(info.hg_session_id)
        char_text, scene_text = retrieve_authored_text(
            self.repo.knowledge_service, fixture, character_id="Kizzie"
        )
        self.assertTrue(char_text)
        joined = "\n".join(char_text + scene_text + [c.content for c in manifest.contributions])
        self.assertIn("one-tailed Kitsune", joined)
        self.assertNotIn("system_prompt", joined.lower())
        willow_char, _ = retrieve_authored_text(
            self.repo.knowledge_service, fixture, character_id="Willow Reeves"
        )
        self.assertFalse(any("one-tailed kitsune" in text.lower() for text in willow_char))
        self.assertTrue(scene_text)


if __name__ == "__main__":
    unittest.main()
