"""Issue #199 supplemental — uniform-projection authority trace (deterministic)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from domain.tests.perceptual_test_helpers import ayame_threshold_context, co_present_zone_context
from domain_api.character_conversation_projection import project_character_conversation_for_manifest
from domain_api.character_perceptual_inventory import build_character_perceptual_inventory_refs
from domain_api.contract import RoundStartRequest, UserTurnRecordRequest
from domain_api.kernel import DomainKernel
from domain_api.semantic_evaluation_context import build_authority_references
from player_decomposition_fixtures import build_player_decomposition_for_content
from player_uniform_projection import build_uniform_projection_decomposition

CAST = ["Ayame", "Kizzie"]
TRIAGE_CHECKER = {
    "uniform_projection_safe": True,
    "reason": "test",
    "inference_id": "player-visibility-triage-test",
}


class Issue199UniformProjectionTraceTests(unittest.TestCase):
    def _session(self, *, context):
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Scene")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = context
        return kernel, fixture

    def test_auditory_uniform_co_present_in_trigger_not_sensory_inventory(self) -> None:
        kernel, fixture = self._session(context=co_present_zone_context(CAST))
        content = 'Kizzie knocks and calls, "Ayame? It\'s Kizzie."'
        decomposition = build_uniform_projection_decomposition(content, checker_audit=TRIAGE_CHECKER)
        kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=fixture.hg_session_id,
                content=content,
                speaker="Kizzie",
                player_decomposition=decomposition,
            )
        )
        fixture = kernel.store.require(fixture.hg_session_id)
        rnd = fixture.rounds[-1]
        _, trigger, _ = project_character_conversation_for_manifest(fixture, character_id="Ayame")
        refs = build_character_perceptual_inventory_refs(
            fixture, character_id="Ayame", hg_round_id=rnd.hg_round_id
        )
        master = refs[0]["text"]
        self.assertIn("knocks", (trigger or "").lower())
        self.assertIn("No authorized perceptual evidence of Player physical display", master)
        auth_ref_ids = {r["ref_id"] for r in build_authority_references(fixture, character_id="Ayame", hg_round_id=rnd.hg_round_id)}
        self.assertTrue(any(rid.startswith("player_fact:user_post:") for rid in auth_ref_ids))

    def test_non_perceptual_uniform_bodily_withheld_from_trigger_and_inventory(self) -> None:
        kernel, fixture = self._session(context=co_present_zone_context(CAST))
        content = "Kizzie stood trembling, her hands shaking visibly."
        decomposition = build_uniform_projection_decomposition(content, checker_audit=TRIAGE_CHECKER)
        kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=fixture.hg_session_id,
                content=content,
                speaker="Kizzie",
                player_decomposition=decomposition,
            )
        )
        fixture = kernel.store.require(fixture.hg_session_id)
        rnd = fixture.rounds[-1]
        _, trigger, _ = project_character_conversation_for_manifest(fixture, character_id="Ayame")
        refs = build_character_perceptual_inventory_refs(
            fixture, character_id="Ayame", hg_round_id=rnd.hg_round_id
        )
        self.assertIsNone(trigger)
        self.assertIn("No authorized perceptual evidence of Player physical display", refs[0]["text"])

    def test_full_pvr_observable_bodily_in_inventory_and_trigger(self) -> None:
        kernel, fixture = self._session(context=co_present_zone_context(CAST))
        content = "Kizzie's hands trembled as she waited."
        decomposition = build_player_decomposition_for_content(
            content, kind="observable_event", scope="present"
        )
        decomposition["perceptual_visibility"]["units"][0]["perception_channel"] = "visual"
        kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=fixture.hg_session_id,
                content=content,
                speaker="Kizzie",
                player_decomposition=decomposition,
            )
        )
        fixture = kernel.store.require(fixture.hg_session_id)
        rnd = fixture.rounds[-1]
        _, trigger, _ = project_character_conversation_for_manifest(fixture, character_id="Ayame")
        refs = build_character_perceptual_inventory_refs(
            fixture, character_id="Ayame", hg_round_id=rnd.hg_round_id
        )
        self.assertIn("trembled", (trigger or "").lower())
        self.assertNotIn("No authorized perceptual evidence of Player physical display", refs[0]["text"])


if __name__ == "__main__":
    unittest.main()
