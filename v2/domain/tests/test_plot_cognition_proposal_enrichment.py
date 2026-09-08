"""Tests for Storyteller proposal deterministic enrichment (#68 Part C)."""

from __future__ import annotations

import unittest

from domain_api.plot_cognition_initialization_contract import (
    INITIALIZATION_PROPOSAL_SCHEMA,
    PlotCognitionInitializationProposal,
    validate_initialization_proposal_objective,
)
from domain_api.plot_cognition_overlay_contract import (
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
    plot_goal_from_dict,
    validate_plot_goal,
)
from domain_api.plot_cognition_proposal_enrichment import (
    canonicalize_applicability_dict,
    enrich_initialization_proposal,
    enrich_replan_proposal,
    enrich_storyteller_proposed_goal,
    enrich_storyteller_proposed_pressure,
    enrich_update_proposal,
)
from domain_api.plot_cognition_update_contract import (
    REPLAN_PROPOSAL_SCHEMA,
    UPDATE_PROPOSAL_SCHEMA,
    PlotCognitionReplanProposal,
    PlotCognitionUpdateProposal,
    validate_replan_proposal_objective,
    validate_update_proposal_objective,
)


def _thin_goal(*, goal_id: str = "g-thin", direction: str = "Explore quietly.") -> dict:
    return {
        "goal_id": goal_id,
        "intended_direction": direction,
        "planning_horizon": "MEDIUM",
        "applicability": {
            "applicability_kind": "character",
            "primary_character_id": "Alice",
            "involved_character_ids": ["Alice"],
        },
    }


def _thin_pressure(*, pressure_id: str = "p-thin") -> dict:
    return {
        "pressure_id": pressure_id,
        "pressure_text": "The key remains missing.",
        "dramatic_rationale": "Sustains tension.",
        "applicability": {
            "applicability_kind": "global",
            "primary_character_id": None,
            "involved_character_ids": [],
        },
    }


class PlotCognitionProposalEnrichmentTests(unittest.TestCase):
    def test_goal_missing_metadata_receives_storyteller_defaults(self) -> None:
        enriched = enrich_storyteller_proposed_goal(_thin_goal())
        self.assertEqual(enriched["schema"], PLOT_GOAL_SCHEMA)
        self.assertEqual(enriched["creation_provenance"], {"source": "storyteller"})
        self.assertEqual(enriched["activity_state"], "active")

    def test_pressure_missing_metadata_receives_storyteller_defaults(self) -> None:
        enriched = enrich_storyteller_proposed_pressure(_thin_pressure())
        self.assertEqual(enriched["schema"], UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA)
        self.assertEqual(enriched["creation_provenance"], {"source": "storyteller"})
        self.assertEqual(enriched["activity_state"], "active")

    def test_preserves_explicit_authored_material_provenance(self) -> None:
        raw = {
            **_thin_goal(),
            "creation_provenance": {
                "source": "authored_material",
                "provenance_refs": [
                    {"ref_kind": "storyteller_plot_direction", "stable_ref": "dir:1"},
                ],
            },
        }
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["creation_provenance"]["source"], "authored_material")

    def test_preserves_explicit_activity_state(self) -> None:
        raw = {**_thin_goal(), "activity_state": "inactive"}
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["activity_state"], "inactive")

    def test_invalid_explicit_provenance_not_replaced(self) -> None:
        raw = {**_thin_goal(), "creation_provenance": {"source": "not_a_real_source"}}
        enriched = enrich_storyteller_proposed_goal(raw)
        goal = plot_goal_from_dict(enriched)
        ok, violations = validate_plot_goal(goal)
        self.assertFalse(ok)
        self.assertIn("creation_provenance_source_invalid", violations)

    def test_semantic_fields_preserved(self) -> None:
        raw = _thin_goal(direction="Hold the line.")
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["goal_id"], "g-thin")
        self.assertEqual(enriched["intended_direction"], "Hold the line.")
        self.assertEqual(enriched["planning_horizon"], "MEDIUM")
        self.assertEqual(enriched["applicability"]["applicability_kind"], "character")

    def test_thin_semantic_proposal_passes_objective_validation_after_enrichment(self) -> None:
        proposal = PlotCognitionInitializationProposal(
            schema=INITIALIZATION_PROPOSAL_SCHEMA,
            proposal_id="p-init",
            source_snapshot_id="snap",
            source_snapshot_fingerprint="fp",
            plot_cognition_scope_id="scope",
            adoption_rationale="Adopt initial cognition.",
            goals=(_thin_goal(),),
            pressures=(_thin_pressure(),),
            global_frame=None,
        )
        enriched = enrich_initialization_proposal(proposal)
        result = validate_initialization_proposal_objective(
            enriched,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(result.ok, result.violations)

    def test_missing_dramatic_rationale_still_fails_after_enrichment(self) -> None:
        thin = {
            "pressure_id": "p-missing",
            "pressure_text": "Pressure without rationale.",
            "applicability": {
                "applicability_kind": "global",
                "primary_character_id": None,
                "involved_character_ids": [],
            },
        }
        enriched = enrich_storyteller_proposed_pressure(thin)
        proposal = PlotCognitionUpdateProposal(
            schema=UPDATE_PROPOSAL_SCHEMA,
            proposal_id="p-update",
            source_snapshot_id="snap",
            source_snapshot_fingerprint="fp",
            plot_cognition_scope_id="scope",
            prior_store_revision=1,
            assimilation_rationale="Adjust pressures.",
            goals=(),
            pressures=(enriched,),
            global_frame=None,
        )
        enriched_proposal = enrich_update_proposal(proposal)
        result = validate_update_proposal_objective(
            enriched_proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("dramatic_rationale_required" in item for item in result.violations))

    def test_replan_proposal_enrichment_shared_path(self) -> None:
        proposal = PlotCognitionReplanProposal(
            schema=REPLAN_PROPOSAL_SCHEMA,
            proposal_id="rp1",
            source_snapshot_id="snap",
            source_snapshot_fingerprint="fp",
            plot_cognition_scope_id="scope",
            prior_store_revision=1,
            replan_rationale="Replan warranted.",
            trigger_summary="Authority shifted.",
            goals=(_thin_goal(goal_id="g-replan"),),
            pressures=(),
            global_frame=None,
        )
        enriched = enrich_replan_proposal(proposal)
        result = validate_replan_proposal_objective(
            enriched,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(result.ok, result.violations)

    def test_character_goal_with_extra_participants_canonicalizes_to_primary_only(self) -> None:
        raw = {
            **_thin_goal(goal_id="g-ayame"),
            "applicability": {
                "applicability_kind": "character",
                "primary_character_id": "Ayame",
                "involved_character_ids": ["Ayame", "Kizzie"],
            },
        }
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["applicability"]["applicability_kind"], "character")
        self.assertEqual(enriched["applicability"]["involved_character_ids"], ["Ayame"])

    def test_character_goal_with_empty_involved_canonicalizes_to_primary(self) -> None:
        raw = {
            **_thin_goal(goal_id="g-alice"),
            "applicability": {
                "applicability_kind": "character",
                "primary_character_id": "Alice",
                "involved_character_ids": [],
            },
        }
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["applicability"]["involved_character_ids"], ["Alice"])

    def test_character_goal_with_wrong_sole_involved_canonicalizes_to_primary(self) -> None:
        raw = {
            **_thin_goal(goal_id="g-ayame2"),
            "applicability": {
                "applicability_kind": "character",
                "primary_character_id": "Ayame",
                "involved_character_ids": ["Kizzie"],
            },
        }
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["applicability"]["involved_character_ids"], ["Ayame"])
        self.assertEqual(enriched["applicability"]["applicability_kind"], "character")

    def test_relational_missing_primary_in_involved_adds_primary(self) -> None:
        raw = {
            **_thin_pressure(pressure_id="p-rel"),
            "applicability": {
                "applicability_kind": "relational",
                "primary_character_id": "Ayame",
                "involved_character_ids": ["Kizzie"],
            },
        }
        enriched = enrich_storyteller_proposed_pressure(raw)
        self.assertEqual(enriched["applicability"]["applicability_kind"], "relational")
        self.assertEqual(enriched["applicability"]["involved_character_ids"], ["Ayame", "Kizzie"])

    def test_relational_with_one_character_still_fails_objective_validation(self) -> None:
        raw = {
            **_thin_pressure(pressure_id="p-rel-one"),
            "applicability": {
                "applicability_kind": "relational",
                "primary_character_id": "Alice",
                "involved_character_ids": ["Alice"],
            },
        }
        enriched = enrich_storyteller_proposed_pressure(raw)
        proposal = PlotCognitionUpdateProposal(
            schema=UPDATE_PROPOSAL_SCHEMA,
            proposal_id="p-rel-fail",
            source_snapshot_id="snap",
            source_snapshot_fingerprint="fp",
            plot_cognition_scope_id="scope",
            prior_store_revision=1,
            assimilation_rationale="Test relational failure.",
            goals=(),
            pressures=(enriched,),
            global_frame=None,
        )
        result = validate_update_proposal_objective(
            enrich_update_proposal(proposal),
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any("relational_applicability_requires_two_or_more_characters" in item for item in result.violations)
        )

    def test_global_applicability_canonicalizes_to_empty_scope(self) -> None:
        canonical = canonicalize_applicability_dict(
            {
                "applicability_kind": "global",
                "primary_character_id": "Alice",
                "involved_character_ids": ["Alice"],
            }
        )
        self.assertIsNone(canonical["primary_character_id"])
        self.assertEqual(canonical["involved_character_ids"], [])

    def test_valid_applicability_unchanged(self) -> None:
        raw = _thin_goal()
        enriched = enrich_storyteller_proposed_goal(raw)
        self.assertEqual(enriched["applicability"], raw["applicability"])


if __name__ == "__main__":
    unittest.main()
