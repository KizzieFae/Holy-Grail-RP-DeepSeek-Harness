"""Issue #194 — narrator environmental cognition deliberation profile tests."""

from __future__ import annotations

import unittest

from domain_api.narrator_environment_deliberation_profile import (
    DELIBERATION_PROFILE_CONSTRAINED,
    DELIBERATION_PROFILE_DEEP,
    classify_cognition_result_deliberation_profile,
    classify_environment_cognition_deliberation_profile,
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

    def test_single_b2_need_is_constrained_result(self) -> None:
        profile = classify_cognition_result_deliberation_profile(
            {
                "information_needs": [{"need_id": "env_need_1"}],
                "resolutions": [{"category": "B2", "need_id": "env_need_1"}],
            }
        )
        self.assertEqual(profile, DELIBERATION_PROFILE_CONSTRAINED)

    def test_conflicts_force_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["environmental_current_view"]["conflicts"] = [{"property_key": "x"}]
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)

    def test_continuity_turn_gt_1_forces_deep_envelope(self) -> None:
        context = _narrow_opening_context()
        context["continuity_turn_index"] = 4
        result = classify_environment_cognition_deliberation_profile(context)
        self.assertEqual(result["profile"], DELIBERATION_PROFILE_DEEP)


if __name__ == "__main__":
    unittest.main()
