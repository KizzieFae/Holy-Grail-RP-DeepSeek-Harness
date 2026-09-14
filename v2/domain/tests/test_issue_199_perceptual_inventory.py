"""Issue #199 — perceptual inventory projection and R02b grounding contracts."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from continuity_state import PublicEvent
from domain_api.character_context import prepare_character_context
from domain_api.character_perceptual_inventory import (
    PERCEPTION_FACT_AUTHORIZED_INVENTORY_PREFIX,
    PERCEPTION_FACT_ENTITLED_PREFIX,
    build_character_perceptual_inventory_refs,
)
from domain_api.contract import ContextPrepareRequest, RoundStartRequest, UserTurnRecordRequest
from domain_api.kernel import DomainKernel
from domain_api.player_authorship_authority import (
    CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE,
    PLAYER_AUTHORSHIP_GUARDRAIL_TEXT,
)
from domain_api.semantic_evaluation_context import build_authority_references
from domain.tests.perceptual_test_helpers import ayame_threshold_context, co_present_zone_context
from player_decomposition_fixtures import build_player_decomposition_for_content
from player_uniform_projection import build_uniform_projection_decomposition

CAST = ["Ayame", "Kizzie"]


def _current_round(fixture):
    return fixture.rounds[-1]


def _record_uniform_player_turn(kernel: DomainKernel, fixture, content: str, speaker: str = "Kizzie") -> None:
    decomposition = build_uniform_projection_decomposition(
        content,
        checker_audit={
            "uniform_projection_safe": True,
            "reason": "test",
            "inference_id": "player-visibility-triage-test",
        },
    )
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=fixture.hg_session_id,
            content=content,
            speaker=speaker,
            player_decomposition=decomposition,
        )
    )


def _record_observable_player_turn(
    kernel: DomainKernel,
    fixture,
    content: str,
    *,
    speaker: str = "Kizzie",
    channel: str = "visual",
) -> None:
    decomposition = build_player_decomposition_for_content(
        content,
        kind="observable_event",
        scope="present",
    )
    decomposition["perceptual_visibility"]["units"][0]["perception_channel"] = channel
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=fixture.hg_session_id,
            content=content,
            speaker=speaker,
            player_decomposition=decomposition,
        )
    )


def _record_speech_only_turn(kernel: DomainKernel, fixture, content: str, speaker: str = "Kizzie") -> None:
    decomposition = build_player_decomposition_for_content(
        content,
        kind="speech",
        scope="present",
    )
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=fixture.hg_session_id,
            content=content,
            speaker=speaker,
            player_decomposition=decomposition,
        )
    )


class Issue199PerceptualInventoryTests(unittest.TestCase):
    def test_guardrail_text_rejects_subjective_without_substrate(self) -> None:
        self.assertIn("Subjective phrasing alone does not cure", PLAYER_AUTHORSHIP_GUARDRAIL_TEXT)
        self.assertIn("does NOT authorize fabrication", PLAYER_AUTHORSHIP_GUARDRAIL_TEXT)

    def test_matrix_a_knowledge_without_evidence_empty_inventory(self) -> None:
        """Matrix A — knowledge may inform reasoning; no sensory substrate at barrier."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Scene")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = ayame_threshold_context()
        opening = (
            "Kizzie glanced up, double-checking the house number and then steeled herself before knocking."
        )
        _record_uniform_player_turn(kernel, fixture, opening)
        fixture = kernel.store.require(fixture.hg_session_id)
        rnd = _current_round(fixture)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=rnd.hg_round_id,
        )
        master = refs[0]
        self.assertTrue(master["ref_id"].startswith(PERCEPTION_FACT_AUTHORIZED_INVENTORY_PREFIX))
        self.assertIn("No authorized perceptual evidence of Player physical display", master["text"])
        player_sensory = [
            r for r in refs[1:] if (r.get("provenance") or {}).get("targets_player")
        ]
        self.assertEqual(player_sensory, [])

    def test_matrix_b_current_turn_trembling_in_inventory(self) -> None:
        """Matrix B — entitled current-turn observable is in inventory."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        content = "Kizzie stood trembling, her hands shaking visibly."
        _record_observable_player_turn(kernel, fixture, content)
        fixture = kernel.store.require(fixture.hg_session_id)
        rnd = _current_round(fixture)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=rnd.hg_round_id,
        )
        entitled = [r for r in refs if r["ref_id"].startswith(PERCEPTION_FACT_ENTITLED_PREFIX)]
        self.assertTrue(entitled)
        player_sensory = [r for r in refs if (r.get("provenance") or {}).get("targets_player")]
        self.assertTrue(player_sensory)
        combined = " ".join(r["text"] for r in player_sensory).lower()
        self.assertIn("trembling", combined)

    def test_matrix_c_knowledge_plus_current_evidence(self) -> None:
        """Matrix C — trembling inventory present; knowledge is separate (no fabrication)."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        fixture.character_private_secrets["Ayame"] = "Ayame knows Kizzie was recently fired."
        _record_observable_player_turn(kernel, fixture, "Kizzie's hands trembled as she waited.")
        fixture = kernel.store.require(fixture.hg_session_id)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=_current_round(fixture).hg_round_id,
        )
        player_sensory = [r for r in refs if (r.get("provenance") or {}).get("targets_player")]
        self.assertTrue(any("trembled" in r["text"].lower() for r in player_sensory))

    def test_matrix_d_ambiguous_pause_without_bodily_invention(self) -> None:
        """Matrix D — pause may be observable; no extra bodily signs without substrate."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        _record_observable_player_turn(
            kernel,
            fixture,
            "Kizzie paused at the door before knocking.",
        )
        fixture = kernel.store.require(fixture.hg_session_id)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=_current_round(fixture).hg_round_id,
        )
        player_sensory = [r for r in refs if (r.get("provenance") or {}).get("targets_player")]
        combined = " ".join(r["text"] for r in player_sensory).lower()
        self.assertIn("paused", combined)
        self.assertNotIn("trembl", combined)
        self.assertNotIn("strain", combined)

    def test_matrix_e_prior_grounding_injury_persists(self) -> None:
        """Matrix E — settled visible medical grounding survives a later speech-only turn."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        fixture.manager.public_events = [
            PublicEvent(
                event_id="e1",
                timestamp=datetime.now(timezone.utc),
                event_type="decision",
                participants=["Kizzie"],
                summary="Visible forearm bandage established.",
                turn_index=1,
                grounding_markers=[
                    "medical_status:wound_dressing|status=visible_forearm_bandage"
                ],
            )
        ]
        _record_observable_player_turn(
            kernel,
            fixture,
            "Kizzie looked at Ayame with a fresh bandage on her forearm.",
        )
        _record_speech_only_turn(kernel, fixture, '"Hello," Kizzie said quietly.')
        fixture = kernel.store.require(fixture.hg_session_id)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=_current_round(fixture).hg_round_id,
        )
        grounding_refs = [r for r in refs if str(r.get("ref_id", "")).startswith("grounding:")]
        self.assertTrue(grounding_refs)
        self.assertTrue(any("bandage" in r["text"].lower() for r in grounding_refs))

    def test_matrix_f_subjective_without_substrate_inventory_empty(self) -> None:
        """Matrix F — subjective strain claim has no inventory substrate."""
        refs = build_character_perceptual_inventory_refs(
            _EmptyInventoryFixture(),
            character_id="Ayame",
            hg_round_id="hg-round-test",
        )
        master = refs[0]
        self.assertIn("No authorized perceptual evidence", master["text"])
        player_sensory = [
            r for r in refs[1:] if (r.get("provenance") or {}).get("targets_player")
        ]
        self.assertEqual(player_sensory, [])
        self.assertIn("R02b", PLAYER_AUTHORSHIP_GUARDRAIL_TEXT)

    def test_matrix_g_legitimate_inference_with_substrate(self) -> None:
        """Matrix G — fallible interpretation allowed when substrate exists."""
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        _record_observable_player_turn(kernel, fixture, "Kizzie's hands shook as she waited.")
        fixture = kernel.store.require(fixture.hg_session_id)
        refs = build_character_perceptual_inventory_refs(
            fixture,
            character_id="Ayame",
            hg_round_id=_current_round(fixture).hg_round_id,
        )
        master = refs[0]
        self.assertNotIn("No authorized perceptual evidence of Player physical display", master["text"])
        self.assertTrue(any("shook" in r["text"].lower() for r in refs[1:]))

    def test_character_manifest_includes_inventory_and_discipline(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        rnd = kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(CAST)
        _record_uniform_player_turn(kernel, fixture, "Kizzie knocked on the door.")
        fixture = kernel.store.require(fixture.hg_session_id)
        manifest = prepare_character_context(
            fixture,
            _current_round(fixture),
            ContextPrepareRequest(
                inference_id="inf-test",
                attempt_index=0,
                hg_scene_id=scene.hg_scene_id,
                hg_round_id=rnd.hg_round_id,
                role="host",
                character_id="Ayame",
                turn_index=0,
            ),
            memory_service=None,
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("authoritative_perceptual_inventory", kinds)
        instructions = [
            c.content for c in manifest.contributions if c.source_kind == "inference_instruction"
        ]
        self.assertTrue(any(CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE in text for text in instructions))

    def test_semantic_eval_authority_includes_inventory(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        scene = kernel.create_scene(cast=CAST, location="Room")
        kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        fixture = kernel.store.require(scene.hg_session_id)
        refs = build_authority_references(
            fixture,
            character_id="Ayame",
            hg_round_id=_current_round(fixture).hg_round_id,
        )
        ref_ids = {ref["ref_id"] for ref in refs}
        self.assertTrue(
            any(rid.startswith(PERCEPTION_FACT_AUTHORIZED_INVENTORY_PREFIX) for rid in ref_ids)
        )


class _EmptyInventoryFixture:
    manager = type("M", (), {"scene_state": type("S", (), {"present_characters": CAST})()})()
    cast = CAST
    rp_history = []
    setup_snapshot = {}

    @staticmethod
    def require(_sid):
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
