"""#58 Plot Cognition Overlay contract tests."""

from __future__ import annotations

import sys
import unittest
from dataclasses import fields
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    GLOBAL_PLOT_FRAME_SCHEMA,
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
    CognitionApplicability,
    CreationProvenance,
    GlobalPlotFrame,
    GoalLineage,
    PlotGoal,
    UnresolvedNarrativePressure,
    global_plot_frame_from_dict,
    global_plot_frame_to_dict,
    new_frame_id,
    new_goal_id,
    new_pressure_id,
    plot_goal_from_dict,
    plot_goal_json_round_trip,
    plot_goal_to_dict,
    unresolved_narrative_pressure_from_dict,
    unresolved_narrative_pressure_to_dict,
    validate_applicability,
    validate_global_plot_frame,
    validate_plot_goal,
    validate_unresolved_narrative_pressure,
)
from domain_api.storyteller_contract import StorytellerAdvisoryPackage  # noqa: E402


def _ref(stable_ref: str) -> StableReference:
    return StableReference(ref_kind="public_event", stable_ref=stable_ref)


def _provenance(
    source: str,
    *,
    note: str | None = None,
    refs: tuple[StableReference, ...] = (),
) -> CreationProvenance:
    return CreationProvenance(source=source, provenance_note=note, provenance_refs=refs)  # type: ignore[arg-type]


def _goal(
    *,
    applicability: CognitionApplicability,
    intended_direction: str = "Steer toward confrontation over the vault.",
    horizon: str = "SHORT",
    provenance: CreationProvenance | None = None,
    goal_id: str = "goal-1",
) -> PlotGoal:
    return PlotGoal(
        schema=PLOT_GOAL_SCHEMA,
        goal_id=goal_id,
        intended_direction=intended_direction,
        basis_note="Alice distrusts Bob.",
        basis_refs=(_ref("event-alice-distrust"),),
        applicability=applicability,
        planning_horizon=horizon,  # type: ignore[arg-type]
        creation_provenance=provenance or _provenance("storyteller"),
        lineage=GoalLineage(),
        activity_state="active",
    )


class PlotCognitionOverlayContractTests(unittest.TestCase):
    def test_valid_character_applicability(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        )
        ok, violations = validate_applicability(applicability)
        self.assertTrue(ok, violations)
        goal = _goal(applicability=applicability)
        self.assertTrue(validate_plot_goal(goal)[0])

    def test_invalid_character_applicability_rejected(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice", "Bob"),
        )
        ok, violations = validate_applicability(applicability)
        self.assertFalse(ok)
        self.assertIn("character_applicability_requires_one_involved_character", violations)

    def test_valid_relational_applicability(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="relational",
            primary_character_id="Alice",
            involved_character_ids=("Alice", "Bob"),
        )
        ok, violations = validate_applicability(applicability)
        self.assertTrue(ok, violations)

    def test_relational_primary_required_and_involved(self) -> None:
        missing_primary = CognitionApplicability(
            applicability_kind="relational",
            primary_character_id=None,
            involved_character_ids=("Alice", "Bob"),
        )
        ok, violations = validate_applicability(missing_primary)
        self.assertFalse(ok)
        self.assertIn("relational_applicability_requires_primary_character_id", violations)

        not_involved = CognitionApplicability(
            applicability_kind="relational",
            primary_character_id="Charlie",
            involved_character_ids=("Alice", "Bob"),
        )
        ok, violations = validate_applicability(not_involved)
        self.assertFalse(ok)
        self.assertIn("relational_applicability_primary_must_be_involved", violations)

    def test_valid_global_applicability(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="global",
            primary_character_id=None,
            involved_character_ids=(),
        )
        ok, violations = validate_applicability(applicability)
        self.assertTrue(ok, violations)
        goal = _goal(applicability=applicability)
        self.assertTrue(validate_plot_goal(goal)[0])

    def test_invalid_global_character_membership_rejected(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="global",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        )
        ok, violations = validate_applicability(applicability)
        self.assertFalse(ok)
        self.assertIn("global_applicability_requires_empty_involved_character_ids", violations)

    def test_multiple_goals_may_share_horizon(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        )
        first = _goal(applicability=applicability, goal_id="goal-a", horizon="SHORT")
        second = _goal(
            applicability=applicability,
            goal_id="goal-b",
            horizon="SHORT",
            intended_direction="Protect Bob from exposure.",
        )
        self.assertTrue(validate_plot_goal(first)[0])
        self.assertTrue(validate_plot_goal(second)[0])

    def test_intended_direction_required(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        )
        goal = _goal(applicability=applicability, intended_direction="   ")
        ok, violations = validate_plot_goal(goal)
        self.assertFalse(ok)
        self.assertIn("intended_direction_required", violations)

    def test_pressure_text_and_rationale_required(self) -> None:
        pressure = UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id="pressure-1",
            pressure_text=" ",
            dramatic_rationale=" ",
            basis_note=None,
            basis_refs=(),
            continuity_issue_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            creation_provenance=_provenance("storyteller"),
            activity_state="active",
        )
        ok, violations = validate_unresolved_narrative_pressure(pressure)
        self.assertFalse(ok)
        self.assertIn("pressure_text_required", violations)
        self.assertIn("dramatic_rationale_required", violations)

    def test_pressure_may_have_zero_basis_refs(self) -> None:
        pressure = UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id="pressure-2",
            pressure_text="Trust fracture could erupt at any moment.",
            dramatic_rationale="The scene is primed for emotional payoff.",
            basis_note="Inferred from recent hostile exchanges.",
            basis_refs=(),
            continuity_issue_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="relational",
                primary_character_id="Alice",
                involved_character_ids=("Alice", "Bob"),
            ),
            creation_provenance=_provenance("storyteller"),
            activity_state="active",
        )
        self.assertTrue(validate_unresolved_narrative_pressure(pressure)[0])

    def test_pressure_may_reference_continuity_issues_without_embedding_authority(self) -> None:
        pressure = UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id="pressure-3",
            pressure_text="Vault standoff may turn violent.",
            dramatic_rationale="Blocked access raises stakes.",
            basis_note=None,
            basis_refs=(_ref("event-vault-blocked"),),
            continuity_issue_refs=("issue-vault-1",),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            creation_provenance=_provenance("storyteller"),
            activity_state="active",
        )
        ok, violations = validate_unresolved_narrative_pressure(pressure)
        self.assertTrue(ok, violations)
        payload = unresolved_narrative_pressure_to_dict(pressure)
        self.assertEqual(payload["continuity_issue_refs"], ["issue-vault-1"])
        self.assertNotIn("issue_status", payload)

    def test_provenance_authored_material(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            provenance=_provenance(
                "authored_material",
                note="Character card seed",
                refs=(_ref("character-card-alice"),),
            ),
        )
        self.assertTrue(validate_plot_goal(goal)[0])
        self.assertEqual(goal.creation_provenance.source, "authored_material")

    def test_provenance_storyteller_origin(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            provenance=_provenance("storyteller"),
        )
        self.assertEqual(goal.creation_provenance.source, "storyteller")

    def test_provenance_character_committed_origin(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            provenance=_provenance(
                "character_committed",
                refs=(_ref("commit-move-42"),),
            ),
        )
        self.assertEqual(goal.creation_provenance.source, "character_committed")

    def test_provenance_player_committed_origin(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            provenance=_provenance(
                "player_committed",
                refs=(_ref("user-turn-7"),),
            ),
        )
        self.assertEqual(goal.creation_provenance.source, "player_committed")

    def test_provenance_refs_support_multiple_contributors(self) -> None:
        provenance = _provenance(
            "character_committed",
            note="Alice confession shaped trajectory; player prompt initiated turn.",
            refs=(_ref("commit-move-42"), _ref("user-turn-7")),
        )
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            provenance=provenance,
        )
        self.assertEqual(len(goal.creation_provenance.provenance_refs), 2)

    def test_lifecycle_states_represented(self) -> None:
        applicability = CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        )
        for state in ("active", "inactive", "retired"):
            goal = _goal(applicability=applicability, goal_id=f"goal-{state}")
            goal = PlotGoal(
                schema=goal.schema,
                goal_id=goal.goal_id,
                intended_direction=goal.intended_direction,
                basis_note=goal.basis_note,
                basis_refs=goal.basis_refs,
                applicability=goal.applicability,
                planning_horizon=goal.planning_horizon,
                creation_provenance=goal.creation_provenance,
                lineage=goal.lineage,
                activity_state=state,  # type: ignore[arg-type]
            )
            self.assertTrue(validate_plot_goal(goal)[0])

    def test_global_plot_frame_requires_direction_sense(self) -> None:
        frame = GlobalPlotFrame(
            schema=GLOBAL_PLOT_FRAME_SCHEMA,
            frame_id="frame-1",
            direction_sense=" ",
            pacing_note=None,
            cross_character_note=None,
            opportunity_note=None,
            basis_refs=(),
            activity_state="active",
            superseded_by_frame_id=None,
            creation_provenance=_provenance("storyteller"),
        )
        ok, violations = validate_global_plot_frame(frame)
        self.assertFalse(ok)
        self.assertIn("direction_sense_required", violations)

    def test_global_plot_frame_optional_notes_independent(self) -> None:
        frame = GlobalPlotFrame(
            schema=GLOBAL_PLOT_FRAME_SCHEMA,
            frame_id=new_frame_id(),
            direction_sense="Ensemble arc bends toward fracture.",
            pacing_note="Stagnation around the vault.",
            cross_character_note=None,
            opportunity_note="Bob may learn about the key.",
            basis_refs=(),
            activity_state="active",
            superseded_by_frame_id=None,
            creation_provenance=_provenance("storyteller"),
        )
        self.assertTrue(validate_global_plot_frame(frame)[0])
        restored = global_plot_frame_from_dict(global_plot_frame_to_dict(frame))
        self.assertIsNone(restored.cross_character_note)
        self.assertEqual(restored.pacing_note, "Stagnation around the vault.")

    def test_no_numeric_boundedness_or_rank_contract_fields(self) -> None:
        overlay_field_names = {
            field.name
            for cls in (PlotGoal, UnresolvedNarrativePressure, GlobalPlotFrame)
            for field in fields(cls)
        }
        self.assertNotIn("rank_hint", overlay_field_names)
        self.assertNotIn("rank", overlay_field_names)
        self.assertNotIn("max_active", overlay_field_names)
        self.assertNotIn("grounding_kind", overlay_field_names)

    def test_contract_independent_of_model_a_types(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            goal_id=new_goal_id(),
        )
        self.assertNotIsInstance(goal, StorytellerAdvisoryPackage)
        self.assertEqual(goal.schema, PLOT_GOAL_SCHEMA)

    def test_plot_goal_serialization_round_trip(self) -> None:
        goal = _goal(
            applicability=CognitionApplicability(
                applicability_kind="relational",
                primary_character_id="Alice",
                involved_character_ids=("Alice", "Bob"),
            ),
            goal_id=new_goal_id(),
            provenance=_provenance(
                "storyteller",
                refs=(_ref("event-1"),),
            ),
        )
        restored = plot_goal_json_round_trip(goal)
        self.assertEqual(plot_goal_to_dict(goal), plot_goal_to_dict(restored))
        self.assertTrue(validate_plot_goal(restored)[0])

    def test_pressure_serialization_round_trip(self) -> None:
        pressure = UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id=new_pressure_id(),
            pressure_text="Mutual distrust is building.",
            dramatic_rationale="Scene energy is unresolved.",
            basis_note=None,
            basis_refs=(),
            continuity_issue_refs=("issue-1",),
            applicability=CognitionApplicability(
                applicability_kind="relational",
                primary_character_id="Alice",
                involved_character_ids=("Alice", "Bob"),
            ),
            creation_provenance=_provenance("storyteller"),
            activity_state="inactive",
            related_goal_ids=("goal-1",),
        )
        restored = unresolved_narrative_pressure_from_dict(
            unresolved_narrative_pressure_to_dict(pressure)
        )
        self.assertEqual(
            unresolved_narrative_pressure_to_dict(pressure),
            unresolved_narrative_pressure_to_dict(restored),
        )


if __name__ == "__main__":
    unittest.main()
