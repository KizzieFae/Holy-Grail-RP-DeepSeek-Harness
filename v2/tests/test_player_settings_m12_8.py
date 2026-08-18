"""M12.8 player identity and production settings tests."""

from __future__ import annotations

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

from v2.domain_api.contract import EligibleActorsRequest, RoundStartRequest
from v2.domain_api.kernel import DomainKernel
from v2.domain_api.session_repository import SessionRepository


class PlayerSettingsM128Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_player_character_excluded_from_eligibility(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            player_character_file_id="kizzie",
            user_persona_id="Kelly",
        )
        session = self.repo.require(info.hg_session_id)
        player_name = session.setup_snapshot["names_by_file"]["kizzie"]
        ai_name = session.setup_snapshot["names_by_file"]["willow"]

        round_info = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=info.hg_session_id)
        )
        eligibility = self.kernel.eligible_actors(
            EligibleActorsRequest(
                hg_scene_id=info.hg_session_id,
                hg_round_id=round_info.hg_round_id,
            )
        )
        self.assertNotIn(player_name, eligibility.eligible_actors)
        self.assertIn(ai_name, eligibility.eligible_actors)
        player_entry = next(
            entry for entry in eligibility.actors if entry.character_id == player_name
        )
        self.assertEqual(player_entry.exclusion_reason, "player_controlled")

    def test_player_identity_persists_on_reopen(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            player_character_file_id="kizzie",
            user_persona_id="Operator",
        )
        session_id = info.hg_session_id
        self.assertEqual(info.setup_provenance["user_persona_id"], "Operator")
        self.assertEqual(info.setup_provenance["player_character_file_id"], "kizzie")

        self.repo.clear_cache()
        reopened = self.repo.open_session(session_id)
        self.assertEqual(reopened.setup_snapshot["user_persona_id"], "Operator")
        self.assertEqual(reopened.setup_snapshot["player_character_file_id"], "kizzie")
        self.assertEqual(
            reopened.setup_snapshot["control_modes"][
                reopened.setup_snapshot["names_by_file"]["kizzie"]
            ],
            "player",
        )

    def test_player_character_must_be_in_cast(self) -> None:
        with self.assertRaises(ValueError):
            self.kernel.create_session(
                characters=["kizzie"],
                player_character_file_id="willow",
            )

    def test_player_control_mode_recorded_when_playing_cast_member(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            player_character_file_id="willow",
        )
        session = self.repo.require(info.hg_session_id)
        willow_name = session.setup_snapshot["names_by_file"]["willow"]
        self.assertEqual(session.setup_snapshot["player_character_file_id"], "willow")
        self.assertEqual(session.setup_snapshot["control_modes"][willow_name], "player")
        self.assertEqual(session.setup_snapshot["control_modes"][
            session.setup_snapshot["names_by_file"]["kizzie"]
        ], "ai")


if __name__ == "__main__":
    unittest.main()
