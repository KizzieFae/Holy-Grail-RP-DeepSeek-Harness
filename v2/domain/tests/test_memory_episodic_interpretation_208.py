"""GitHub #208: episodic interpretation ladder (director_model_reason → reason → motivation)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


from memory_layer.writes import _episodic_interpretation_from_director_decision


@pytest.mark.parametrize(
    ("director", "motivation", "expected"),
    [
        (
            {
                "director_model_reason": "Ayame_was_addressed_via_key",
                "reason": "[ORCH] diagnostics; fairness",
            },
            {},
            "Ayame_was_addressed_via_key",
        ),
        (
            {"reason": "hard_route_synthetic_reason"},
            {},
            "hard_route_synthetic_reason",
        ),
        (
            {"source": "fallback", "reason": "parse_fallback_has_no_model_reason_key"},
            {},
            "parse_fallback_has_no_model_reason_key",
        ),
        (
            {},
            {"goal": "stay calm", "tactic": "breathe"},
            "goal=stay calm; tactic=breathe",
        ),
        (
            {"reason": "", "director_model_reason": "     "},
            {"goal": "g", "tactic": ""},
            "goal=g",
        ),
        (
            {"director_model_reason": ""},
            {"goal": "only_goal", "tactic": ""},
            "goal=only_goal",
        ),
        (
            {"reason": "", "director_model_reason": ""},
            {"goal": "", "tactic": "solo_tactic"},
            "tactic=solo_tactic",
        ),
        (
            {},
            "not-a-dict",
            "",
        ),
        (
            {},
            {},
            "",
        ),
    ],
)
def test_episodic_interpretation_ladder(
    director: dict,
    motivation: object,
    expected: str,
) -> None:
    assert (
        _episodic_interpretation_from_director_decision(director, motivation) == expected
    )
