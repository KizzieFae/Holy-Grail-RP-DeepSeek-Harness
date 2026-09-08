"""Issue #155 — viewer perceptual entitlement remediation and revalidation."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from domain_api.character_conversation_projection import project_character_conversation_for_manifest
from domain_api.contract import (
    ContextPrepareRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.kernel import DomainKernel
from domain_api.memory_write_policy import apply_user_turn_memory
from domain_api.session_repository import SessionRepository
from domain_api.session_state import LiveSession
from domain_api.setup_catalog import list_template_openers_catalog
from domain_api.viewer_player_perception import assemble_viewer_player_perception
from domain.tests.perceptual_test_helpers import (
    ayame_threshold_context,
    co_present_zone_context,
)
from perceptual_scene_context import PerceptualSceneContextV1
from perceptual_visibility_contract import METADATA_KEY, PLAYER_SOURCE_KIND
from perceptual_visibility_projection import (
    assemble_perceptual_history_entry_for_viewer,
    build_perceptual_visibility_audit_metadata,
)
from player_entitlement_authority import merge_entitlement_snapshot_into_metadata
from player_perceptual_service import validate_player_perceptual_decomposition
from player_decomposition_fixtures import build_player_decomposition_for_content
from player_source_accounting import normalize_source_for_indexing, normalized_source_sha256
from player_uniform_projection import build_uniform_projection_decomposition
from player_visibility_triage_corpus import build_issue_121_checker_corpus
from scene_template import SceneTemplateManager

CAST = ["Ayame", "Kizzie", "Harley", "Celina"]
PRESENT = list(CAST)

VISUAL_ONLY_TURN = (
    "Kizzie checks the address on the gatepost, looks around the quiet street, "
    "and hesitates at the front door."
)

MIXED_TURN = (
    "Kizzie looks at the house number, nervously smooths her skirt, knocks three times, "
    'then calls through the door, "Ayame? It\'s Kizzie. I\'m here for the interview."'
)

ORIGINAL_VISUAL_TURN = (
    "Kizzie looked up at the numbers to see if she had the right address and then "
    "looked around, hesitating to knock on the door."
)


def _build_uniform_player_entry(content: str) -> dict:
    decomposition = build_uniform_projection_decomposition(
        content,
        checker_audit={
            "uniform_projection_safe": True,
            "reason": "test",
            "inference_id": "player-visibility-triage-test",
        },
    )
    record, audit = validate_player_perceptual_decomposition(
        content=content,
        speaker="Kizzie",
        decomposition=decomposition,
    )
    assert audit["accepted"]
    metadata = merge_entitlement_snapshot_into_metadata(
        {METADATA_KEY: record.to_dict()},
        session_cast=CAST,
        role_assignments={},
    )
    return {
        "entry_id": "issue-155-entry",
        "sequence_index": 1,
        "kind": "user",
        "content": content,
        "actor_id": "Kizzie",
        "metadata": metadata,
    }


def _build_mixed_pvr_decomposition() -> dict[str, Any]:
    unit_specs = [
        ("u_visual_1", "observable_event", "Kizzie looks at the house number", "visual"),
        ("u_visual_2", "observable_event", "nervously smooths her skirt", "visual"),
        ("u_knock", "observable_event", "knocks three times", "auditory"),
        (
            "u_speech",
            "speech",
            'calls through the door, "Ayame? It\'s Kizzie. I\'m here for the interview."',
            "auditory",
        ),
    ]
    normalized = normalize_source_for_indexing(MIXED_TURN)
    units: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    cursor = 0
    segment_counter = 0
    for index, (unit_id, kind, text, channel) in enumerate(unit_specs):
        piece = normalize_source_for_indexing(text)
        start = normalized.find(piece, cursor)
        if start < 0:
            raise ValueError(f"unit text not found in source: {text}")
        if start > cursor:
            segment_counter += 1
            segments.append(
                {
                    "segment_id": f"g{segment_counter}",
                    "char_start": cursor,
                    "char_end": start,
                    "disposition": "non_projects",
                    "unit_ids": [],
                }
            )
        end = start + len(piece)
        segment_counter += 1
        segment_id = f"s{index + 1}"
        units.append(
            {
                "unit_id": unit_id,
                "kind": kind,
                "text": piece,
                "perception_channel": channel,
                "recipients": {"scope": "present", "characters": [], "roles": []},
                "source_provenance": {"segment_ids": [segment_id], "order_index": index},
                "source": "player_decomposition",
            }
        )
        segments.append(
            {
                "segment_id": segment_id,
                "char_start": start,
                "char_end": end,
                "disposition": "projects",
                "unit_ids": [unit_id],
            }
        )
        cursor = end
    if cursor < len(normalized):
        segment_counter += 1
        segments.append(
            {
                "segment_id": f"g{segment_counter}",
                "char_start": cursor,
                "char_end": len(normalized),
                "disposition": "non_projects",
                "unit_ids": [],
            }
        )
    return {
        "perceptual_visibility": {"units": units},
        "source_accounting": {
            "source_length": len(normalized),
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": "nfc_crlf",
            "segments": segments,
        },
        "generation": {"inference_id": "test-player-decomposition"},
    }


def _assemble(
    entry: dict,
    *,
    viewer: str,
    scene_context: PerceptualSceneContextV1 | None,
    player_character: str = "Kizzie",
) -> str | None:
    result = assemble_perceptual_history_entry_for_viewer(
        entry,
        viewer_character=viewer,
        present_characters=PRESENT,
        source_kind=PLAYER_SOURCE_KIND,
        perceptual_scene_context=scene_context,
        player_character=player_character,
    )
    return result.content


class Issue155RemediationTests(unittest.TestCase):
    def test_no_context_present_scope_withholds_legacy_leak(self) -> None:
        entry = _build_uniform_player_entry('The player waves. "Hello," they say.')
        projected = _assemble(entry, viewer="Ayame", scene_context=None)
        self.assertIsNone(projected)

    def test_co_present_context_permits_open_room_projection(self) -> None:
        content = 'The player waves. "Hello," they say.'
        entry = _build_uniform_player_entry(content)
        context = co_present_zone_context(CAST)
        projected = _assemble(entry, viewer="Ayame", scene_context=context)
        self.assertEqual(projected, content)

    def test_visual_only_exterior_withheld_from_ayame(self) -> None:
        entry = _build_uniform_player_entry(VISUAL_ONLY_TURN)
        context = ayame_threshold_context()
        self.assertIsNone(_assemble(entry, viewer="Ayame", scene_context=context))

    def test_uniform_mixed_bundle_requires_decomposition(self) -> None:
        entry = _build_uniform_player_entry(MIXED_TURN)
        context = ayame_threshold_context()
        projected = _assemble(entry, viewer="Ayame", scene_context=context)
        self.assertIsNone(projected)
        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=PRESENT,
            source_kind=PLAYER_SOURCE_KIND,
            perceptual_scene_context=context,
            player_character="Kizzie",
        )
        audit = build_perceptual_visibility_audit_metadata(assembly)
        decisions = audit["perceptual_visibility_projection"].get("unit_entitlement_decisions") or []
        self.assertTrue(
            any(d.get("reason_code") == "mixed_modality_requires_decomposition" for d in decisions)
        )

    def test_semantic_pvr_mixed_units_partial_projection(self) -> None:
        decomposition = _build_mixed_pvr_decomposition()
        record, audit = validate_player_perceptual_decomposition(
            content=MIXED_TURN,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "mixed-pvr",
            "sequence_index": 1,
            "kind": "user",
            "content": MIXED_TURN,
            "actor_id": "Kizzie",
            "metadata": merge_entitlement_snapshot_into_metadata(
                {METADATA_KEY: record.to_dict()},
                session_cast=CAST,
                role_assignments={},
            ),
        }
        context = ayame_threshold_context()
        projected = _assemble(entry, viewer="Ayame", scene_context=context)
        self.assertIsNotNone(projected)
        assert projected is not None
        self.assertIn("knocks three times", projected)
        self.assertIn("Ayame?", projected)
        self.assertNotIn("smooths her skirt", projected)

    def test_quoted_speech_with_commas_not_fragmented(self) -> None:
        from player_decomposition_fixtures import build_player_decomposition_for_content

        quote = '"Hello, Ayame, then we begin," Kizzie calls through the door.'
        decomposition = build_player_decomposition_for_content(
            quote,
            kind="speech",
            scope="present",
        )
        decomposition["perceptual_visibility"]["units"][0]["perception_channel"] = "auditory"
        record, audit = validate_player_perceptual_decomposition(
            content=quote,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "quote-entry",
            "sequence_index": 1,
            "kind": "user",
            "content": quote,
            "metadata": merge_entitlement_snapshot_into_metadata(
                {METADATA_KEY: record.to_dict()},
                session_cast=CAST,
            ),
        }
        projected = _assemble(entry, viewer="Ayame", scene_context=ayame_threshold_context())
        self.assertIn("Hello, Ayame, then we begin", projected or "")

    def test_visual_hesitation_does_not_become_auditory(self) -> None:
        entry = _build_uniform_player_entry("Kizzie hesitates outside the closed door.")
        projected = _assemble(entry, viewer="Ayame", scene_context=ayame_threshold_context())
        self.assertIsNone(projected)

    def test_open_portal_restores_visual_entitlement(self) -> None:
        entry = _build_uniform_player_entry("Kizzie looks at the house number and waves.")
        context = ayame_threshold_context(door_state="open")
        projected = _assemble(entry, viewer="Ayame", scene_context=context)
        self.assertEqual(projected, entry["content"])

    def test_unknown_zones_do_not_assume_ordinary_door(self) -> None:
        entry = _build_uniform_player_entry('Kizzie knocks and calls, "Hello?"')
        context = PerceptualSceneContextV1(character_zones={"Kizzie": "exterior"}, portals={})
        self.assertIsNone(_assemble(entry, viewer="Ayame", scene_context=context))

    def test_issue_121_false_simple_corpus_present(self) -> None:
        corpus_ids = {
            "neg_exterior_threshold_visual_155",
            "neg_exterior_address_check_155",
            "neg_mixed_visual_knock_speech_155",
        }
        cases = [c for c in build_issue_121_checker_corpus() if c.case_id in corpus_ids]
        self.assertEqual(len(cases), 3)


class Issue155AyameProductionPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_session(self) -> tuple[str, str, str]:
        openers = list_template_openers_catalog("ayame_household_entry_evaluation")
        info = self.kernel.create_session(
            characters=["ayame", "kizzie"],
            scene_template_id="ayame_household_entry_evaluation",
            role_assignments={"ayame": "host", "kizzie": "applicant"},
            player_character_file_id="kizzie",
            opening={"mode": "template", "opener_id": openers[0]["opener_id"]},
        )
        fixture = self.repo.require(info.hg_session_id)
        host = fixture.setup_snapshot["names_by_file"]["ayame"]
        applicant = fixture.setup_snapshot["names_by_file"]["kizzie"]
        scene_context = fixture.manager.scene_state.perceptual_scene_context
        self.assertIsInstance(scene_context, dict)
        self.assertIn(host, scene_context.get("character_zones", {}))
        self.assertIn(applicant, scene_context.get("character_zones", {}))
        return info.hg_session_id, host, applicant

    def _manifest_for(self, session_id: str, character_id: str):
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        return self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id=f"inf-{character_id}",
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )

    def test_template_seeds_perceptual_scene_context(self) -> None:
        template = SceneTemplateManager().load_template("ayame_household_entry_evaluation")
        self.assertIn("character_zones_by_role", template.perceptual_scene_context)

    def test_production_visual_only_turn_withheld_from_ayame(self) -> None:
        session_id, host, applicant = self._create_session()
        decomposition = build_uniform_projection_decomposition(
            ORIGINAL_VISUAL_TURN,
            checker_audit={
                "uniform_projection_safe": True,
                "reason": "test",
                "inference_id": "player-visibility-triage-test",
            },
        )
        self.kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=session_id,
                content=ORIGINAL_VISUAL_TURN,
                speaker=applicant,
                player_decomposition=decomposition,
            )
        )
        fixture = self.repo.require(session_id)
        self.assertEqual(fixture.rp_history[-1]["content"], ORIGINAL_VISUAL_TURN)
        transcript, trigger, _ = project_character_conversation_for_manifest(
            fixture,
            character_id=host,
        )
        self.assertIsNone(trigger)
        joined = f"{transcript or ''}"
        self.assertNotIn("hesitat", joined.lower())
        self.assertNotIn("looked up at the numbers", joined.lower())

    def test_production_mixed_pvr_partial_for_ayame(self) -> None:
        session_id, host, applicant = self._create_session()
        decomposition = _build_mixed_pvr_decomposition()
        self.kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=session_id,
                content=MIXED_TURN,
                speaker=applicant,
                player_decomposition=decomposition,
            )
        )
        fixture = self.repo.require(session_id)
        transcript, trigger, _ = project_character_conversation_for_manifest(
            fixture,
            character_id=host,
        )
        self.assertIsNotNone(trigger)
        joined = f"{transcript or ''}{trigger or ''}"
        self.assertIn("knocks three times", joined)
        self.assertIn("Ayame?", joined)
        self.assertNotIn("smooths her skirt", joined)


class Issue155HarnessParityTests(unittest.TestCase):
    def test_project_player_entry_cli_accepts_scene_context(self) -> None:
        import subprocess

        entry = _build_uniform_player_entry(VISUAL_ONLY_TURN)
        context = ayame_threshold_context().to_dict()
        script = (
            Path(__file__).resolve().parents[2]
            / "rp_runtime"
            / "scripts"
            / "lib"
            / "project-player-entry-for-viewer.py"
        )
        payload = {
            "entry": entry,
            "viewer_character": "Ayame",
            "present_characters": PRESENT,
            "perceptual_scene_context": context,
            "player_character": "Kizzie",
        }
        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        assembly = json.loads(result.stdout)
        self.assertIsNone(assembly.get("content"))


if __name__ == "__main__":
    unittest.main()
