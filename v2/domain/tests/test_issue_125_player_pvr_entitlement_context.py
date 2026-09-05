"""Issue #125 — PlayerPvrEntitlementContextV1 assembly and forensic chain tests."""

from __future__ import annotations

import json
import unittest

from domain_api.contract import PlayerDecompositionContextPrepareRequest
from domain_api.kernel import DomainKernel
from domain_api.player_decomposition_context import prepare_player_decomposition_context
from domain_api.player_pvr_entitlement_context import (
    PLAYER_PVR_ENTITLEMENT_CONTEXT_SOURCE_KIND,
    assemble_player_pvr_entitlement_context_v1,
)
from perceptual_visibility_contract import METADATA_KEY
from perceptual_visibility_projection import assemble_perceptual_history_entry_for_viewer
from player_decomposition_fixtures import (
    ISSUE_88_PRIVATE_METHOD_TOKEN,
    build_issue_88_mixed_turn_fixture,
)
from player_entitlement_authority import merge_entitlement_snapshot_into_metadata
from player_perceptual_service import validate_player_perceptual_decomposition
from player_semantic_normalization import normalize_player_semantic_decomposition


def _entitlement_contribution(manifest):
    return next(
        item
        for item in manifest.contributions
        if item.source_kind == PLAYER_PVR_ENTITLEMENT_CONTEXT_SOURCE_KIND
    )


class Issue125EntitlementContextAssemblyTests(unittest.TestCase):
    def _fixture_with_scene(
        self,
        *,
        cast: list[str],
        present: list[str] | None = None,
        offstage: list[str] | None = None,
        role_assignments: dict[str, str] | None = None,
    ):
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=cast)
        fixture = kernel.store.require(created.hg_scene_id)
        assert fixture.manager.scene_state is not None
        if present is not None:
            fixture.manager.scene_state.present_characters = list(present)
        if offstage is not None:
            fixture.manager.scene_state.offstage_characters = list(offstage)
        if role_assignments is not None:
            fixture.manager.scene_state.role_assignments = dict(role_assignments)
        return fixture

    def test_exact_v1_context_assembly_from_authoritative_sources(self) -> None:
        fixture = self._fixture_with_scene(
            cast=["Harley", "Celina", "Ayame"],
            present=["Harley", "Ayame"],
            offstage=["Celina"],
            role_assignments={"Harley": "guest", "Celina": "staff", "Ayame": "witness"},
        )
        context = assemble_player_pvr_entitlement_context_v1(fixture)
        self.assertEqual(
            context,
            {
                "schema_version": 1,
                "session_cast": ["Harley", "Celina", "Ayame"],
                "present_characters": ["Harley", "Ayame"],
                "offstage_characters": ["Celina"],
                "role_assignments": {
                    "Harley": "guest",
                    "Celina": "staff",
                    "Ayame": "witness",
                },
            },
        )

    def test_empty_present_characters_preserved_without_cast_fallback(self) -> None:
        fixture = self._fixture_with_scene(cast=["Alice", "Bob"])
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.present_characters = []
        context = assemble_player_pvr_entitlement_context_v1(fixture)
        self.assertEqual(context["present_characters"], [])
        self.assertEqual(context["session_cast"], ["Alice", "Bob"])

    def test_no_cast_synthesis_from_presence_categories(self) -> None:
        fixture = self._fixture_with_scene(
            cast=["Alice", "Bob", "Carol"],
            present=["Alice"],
            offstage=["Bob"],
        )
        context = assemble_player_pvr_entitlement_context_v1(fixture)
        self.assertEqual(context["session_cast"], ["Alice", "Bob", "Carol"])
        self.assertEqual(context["present_characters"], ["Alice"])
        self.assertEqual(context["offstage_characters"], ["Bob"])

    def test_manifest_includes_authoritative_entitlement_contribution(self) -> None:
        fixture = self._fixture_with_scene(cast=["Ayame", "Kizzie"])
        manifest = prepare_player_decomposition_context(
            fixture,
            PlayerDecompositionContextPrepareRequest(
                hg_session_id=fixture.hg_scene_id,
                inference_id="issue-125-manifest",
                hg_round_id="hg-round-125",
                attempt_index=0,
            ),
        )
        self.assertEqual(len(manifest.contributions), 2)
        entitlement = _entitlement_contribution(manifest)
        instruction = next(
            item for item in manifest.contributions if item.source_kind == "inference_instruction"
        )
        self.assertLess(entitlement.priority, instruction.priority)
        self.assertEqual(entitlement.authority_class, "authoritative")
        self.assertIn("PlayerPvrEntitlementContextV1", entitlement.content)
        self.assertIn('"session_cast"', entitlement.content)
        self.assertEqual(
            entitlement.provenance["context"],
            assemble_player_pvr_entitlement_context_v1(fixture),
        )
        self.assertIn("do not manufacture named private entitlement", instruction.content)
        self.assertNotIn("location_label", entitlement.content)
        self.assertNotIn("character_presence_status", entitlement.content)

    def test_role_private_instruction_uses_authoritative_role_assignments(self) -> None:
        fixture = self._fixture_with_scene(
            cast=["Alice", "Bob"],
            role_assignments={"Alice": "staff", "Bob": "guest"},
        )
        manifest = prepare_player_decomposition_context(
            fixture,
            PlayerDecompositionContextPrepareRequest(
                hg_session_id=fixture.hg_scene_id,
                inference_id="issue-125-role-private",
            ),
        )
        instruction = next(
            item for item in manifest.contributions if item.source_kind == "inference_instruction"
        )
        self.assertIn("role_private", instruction.content)
        entitlement = _entitlement_contribution(manifest)
        self.assertIn('"staff"', entitlement.content)


class Issue125ForensicReconstructionTests(unittest.TestCase):
    def test_issue_88_asymmetric_projection_chain_from_authoritative_context(self) -> None:
        """Re-baselined #88 diagnostic: authority + semantic scope, not presence oracle."""
        content, decomposition = build_issue_88_mixed_turn_fixture()
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Harley", "Celina", "Ayame"])
        fixture = kernel.store.require(created.hg_scene_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.present_characters = ["Harley", "Celina", "Ayame"]
        fixture.manager.scene_state.offstage_characters = []

        manifest = kernel.prepare_player_decomposition_context(
            PlayerDecompositionContextPrepareRequest(
                hg_session_id=fixture.hg_scene_id,
                inference_id="issue-125-forensic-88",
                hg_round_id="hg-round-forensic-88",
            )
        )
        entitlement = _entitlement_contribution(manifest)
        authoritative_context = entitlement.provenance["context"]
        self.assertEqual(
            authoritative_context["present_characters"],
            ["Harley", "Celina", "Ayame"],
        )

        semantic_units = decomposition["perceptual_visibility"]["units"]
        sir = {
            "units": [
                {
                    "kind": unit["kind"],
                    "text": unit["text"],
                    "recipients": unit["recipients"],
                }
                for unit in semantic_units
            ]
        }
        normalize_result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Traveler",
            semantic_decomposition=sir,
            generation={"inference_id": manifest.inference_id},
        )
        self.assertTrue(normalize_result["accepted"])
        normalized = normalize_result["player_decomposition"]
        assert normalized is not None

        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Traveler",
            decomposition=normalized,
        )
        self.assertTrue(audit["accepted"])
        private_unit = next(
            unit for unit in record.units if ISSUE_88_PRIVATE_METHOD_TOKEN in unit.text
        )
        private_unit_id = private_unit.unit_id
        entry = {
            "entry_id": "issue-125-forensic-88",
            "content": content,
            "metadata": merge_entitlement_snapshot_into_metadata(
                {METADATA_KEY: record.to_dict()},
                session_cast=list(fixture.cast),
                role_assignments=dict(fixture.manager.scene_state.role_assignments),
            ),
        }

        harley = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Harley",
            present_characters=authoritative_context["present_characters"],
            source_kind="player",
        )
        celina = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Celina",
            present_characters=authoritative_context["present_characters"],
            source_kind="player",
        )

        self.assertIn(private_unit_id, harley.excluded_unit_ids)
        self.assertIn(private_unit_id, celina.included_unit_ids)
        self.assertNotIn(ISSUE_88_PRIVATE_METHOD_TOKEN, harley.content or "")
        self.assertIn(ISSUE_88_PRIVATE_METHOD_TOKEN, celina.content or "")

        forensic_record = {
            "authoritative_source_state": {
                "session_cast": list(fixture.cast),
                "scene_state": {
                    "present_characters": list(fixture.manager.scene_state.present_characters),
                    "offstage_characters": list(fixture.manager.scene_state.offstage_characters),
                    "role_assignments": dict(fixture.manager.scene_state.role_assignments),
                },
            },
            "supplied_v1_context": authoritative_context,
            "manifest_contribution_id": entitlement.contribution_id,
            "player_source": content,
            "raw_semantic_decomposition": sir,
            "normalized_decomposition": normalized,
            "canonical_pvr": record.to_dict(),
            "viewer_projections": {
                "Harley": {
                    "included_unit_ids": harley.included_unit_ids,
                    "excluded_unit_ids": harley.excluded_unit_ids,
                    "content": harley.content,
                },
                "Celina": {
                    "included_unit_ids": celina.included_unit_ids,
                    "excluded_unit_ids": celina.excluded_unit_ids,
                    "content": celina.content,
                },
            },
            "entitlement_rationale": (
                "Private unit names Celina in semantic decomposition supported by player prose; "
                "Harley exclusion follows recipient scope, not invented spatial geometry. "
                "present_characters membership alone does not establish Celina private entitlement."
            ),
        }
        serialized = json.dumps(forensic_record, sort_keys=True)
        self.assertIn("issue-125-forensic-88", serialized)
        self.assertIn(entitlement.contribution_id, serialized)


if __name__ == "__main__":
    unittest.main()
