"""Issue #194 — narrator environmental cognition deliberation profile tests."""

from __future__ import annotations

import unittest

from domain_api.narrator_environment_deliberation_profile import (
    DELIBERATION_PROFILE_CONSTRAINED,
    DELIBERATION_PROFILE_DEEP,
    classify_cognition_result_deliberation_profile,
    classify_environment_cognition_deliberation_profile,
    resolve_environment_cognition_deliberation_profile,
    should_escalate_constrained_cognition_to_deep,
)


def _narrow_opening_context() -> dict:
    return {
        "environmental_packet": {
            "location_refs": ["location:scene"],
            "effective_descriptors": [{"property_key": "the_host", "value": "evaluating"}],
            "recent_environmental_changes": [],
            "carryover_b2_refs": [],
            "stable_sub_referents": [],
        },
        "environmental_current_view": {
            "location_ref": "location:scene",
            "conflicts": [],
        },
        "continuity_turn_index": 1,
    }


class Issue194EnvironmentDeliberationProfileTests(unittest.TestCase):
    def test_f06_shaped_envelope_is_constrained(self) -> None:
        result = classify_environment_cognition_deliberation_profile(_narrow_opening_context())
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_CONSTRAINED)

    def test_profile_override_forces_deep(self) -> None:
        result = resolve_environment_cognition_deliberation_profile(
            _narrow_opening_context(),
            profile_override=DELIBERATION_PROFILE_DEEP,
        )
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)
        self.assertIn("profile_override", result["signals"])

    def test_multi_need_result_requires_deep(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "a"}, {"need_id": "b"}],
                "resolutions": [{"category": "B2"}, {"category": "B2"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_DEEP)

    def test_category_c_requires_deep(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "a"}],
                "resolutions": [{"category": "C"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_DEEP)

    def test_cannot_safely_resolve_requires_deep(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "a"}],
                "resolutions": [{"category": "cannot_safely_resolve"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_DEEP)

    def test_mediation_outcome_requires_deep(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "a"}],
                "resolutions": [{"category": "B2", "mediation_outcome": "match"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_DEEP)

    def test_single_b2_need_is_constrained_result(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "env_need_1"}],
                "resolutions": [{"category": "B2", "need_id": "env_need_1"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_CONSTRAINED)

    def test_pre_mediation_placeholder_outcome_does_not_force_deep(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "n1"}],
                "resolutions": [{
                    "category": "B2",
                    "need_id": "n1",
                    "property_key": "house_number",
                    "mediation_outcome": "no_librarian_match",
                }],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_CONSTRAINED)

    def test_should_escalate_constrained_probe_to_deep(self) -> None:
        self.assertTrue(
            should_escalate_constrained_cognition_to_deep(
                DELIBERATION_PROFILE_CONSTRAINED,
                {
                    "information_needs": [{"need_id": "a"}, {"need_id": "b"}],
                    "resolutions": [],
                },
            )
        )
        self.assertFalse(
            should_escalate_constrained_cognition_to_deep(
                DELIBERATION_PROFILE_CONSTRAINED,
                {
                    "information_needs": [{"need_id": "env_need_1"}],
                    "resolutions": [{"category": "B2", "need_id": "env_need_1"}],
                },
            )
        )

    def test_conflicts_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_current_view"]["conflicts"] = [{"property_key": "x"}]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_recent_environmental_changes_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_packet"]["recent_environmental_changes"] = ["change-1"]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_carryover_b2_refs_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_packet"]["carryover_b2_refs"] = ["story-record-1"]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_multiple_location_refs_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_packet"]["location_refs"] = ["location:a", "location:b"]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_stable_sub_referents_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_packet"]["stable_sub_referents"] = ["character:Ayame"]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_continuity_turn_gt_1_forces_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["continuity_turn_index"] = 4
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_unknown_cognition_result_defaults_deep(self) -> None:
        self.assertEqual(
            classify_cognition_result_deliberation_profile(None),
            DELIBERATION_PROFILE_DEEP,
        )


if __name__ == "__main__":
    unittest.main()
