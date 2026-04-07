"""Unit tests for hybrid tension pacing policy (no continuity integration)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from tension_pacing_policy import (
    apply_consequence_up_saturation_gate,
    consequence_tension_recommendation,
    director_pacing_is_neutral,
    parse_director_directional_pacing,
    resolve_hybrid_pacing,
)


def test_parse_escalate_soften_case_insensitive() -> None:
    assert parse_director_directional_pacing({"tension_shift": "escalate"}) == "escalate"
    assert parse_director_directional_pacing({"tension_shift": "Escalate"}) == "escalate"
    assert parse_director_directional_pacing({"tension_shift": "  soften  "}) == "soften"


def test_parse_neutral_absent_empty_hold_steady_unknown() -> None:
    assert parse_director_directional_pacing({}) is None
    assert parse_director_directional_pacing({"tension_shift": ""}) is None
    assert parse_director_directional_pacing({"tension_shift": "   "}) is None
    assert parse_director_directional_pacing({"tension_shift": "hold"}) is None
    assert parse_director_directional_pacing({"tension_shift": "steady"}) is None
    assert parse_director_directional_pacing({"tension_shift": "unsettle"}) is None
    assert parse_director_directional_pacing({"tension_shift": "bogus"}) is None


def test_parse_malformed_director_neutral() -> None:
    assert parse_director_directional_pacing(None) is None
    assert parse_director_directional_pacing({"tension_shift": None}) is None
    assert parse_director_directional_pacing({"tension_shift": 123}) is None
    assert parse_director_directional_pacing({"tension_shift": ["escalate"]}) is None


def test_director_pacing_is_neutral() -> None:
    assert director_pacing_is_neutral({"tension_shift": "steady"})
    assert not director_pacing_is_neutral({"tension_shift": "escalate"})


def test_consequence_pure_up() -> None:
    assert (
        consequence_tension_recommendation({"tags": ["refusal", "repositioning"]}) == "up"
    )


def test_consequence_pure_down() -> None:
    assert consequence_tension_recommendation({"tags": ["agreement", "commitment"]}) == "down"


def test_consequence_mixed_up_down_hold() -> None:
    assert (
        consequence_tension_recommendation({"tags": ["refusal", "agreement"]}) == "hold"
    )


def test_consequence_only_non_voting_hold() -> None:
    assert (
        consequence_tension_recommendation(
            {"tags": ["revelation", "repositioning", "decision_made"]}
        )
        == "hold"
    )


def test_consequence_escalation_alone_up() -> None:
    assert consequence_tension_recommendation({"tags": ["escalation"]}) == "up"


def test_consequence_deescalation_alone_down() -> None:
    assert consequence_tension_recommendation({"tags": ["deescalation"]}) == "down"


def test_consequence_revelation_plus_refusal_up() -> None:
    assert consequence_tension_recommendation({"tags": ["revelation", "refusal"]}) == "up"


def test_concealment_alone_hold() -> None:
    assert consequence_tension_recommendation({"tags": ["concealment"]}) == "hold"


def test_consequence_tags_order_independent() -> None:
    a = consequence_tension_recommendation({"tags": ["access_granted", "refusal"]})
    b = consequence_tension_recommendation({"tags": ["refusal", "access_granted"]})
    assert a == "hold" and b == "hold"


def test_consequence_non_list_tags_hold() -> None:
    assert consequence_tension_recommendation({"tags": None}) == "hold"
    assert consequence_tension_recommendation({}) == "hold"


def test_resolve_director_override_direction() -> None:
    tc: dict = {"tags": []}
    assert resolve_hybrid_pacing(
        director_decision={"tension_shift": "escalate"},
        turn_consequences=tc,
    ) == ("director", "up", False)
    assert resolve_hybrid_pacing(
        director_decision={"tension_shift": "soften"},
        turn_consequences=tc,
    ) == ("director", "down", False)


def test_resolve_neutral_empty_tags_hold() -> None:
    assert resolve_hybrid_pacing(
        director_decision={"tension_shift": "steady"},
        turn_consequences={"tags": []},
    ) == ("none", "hold", True)


def test_resolve_neutral_consequence_up_from_tags() -> None:
    assert resolve_hybrid_pacing(
        director_decision={"tension_shift": ""},
        turn_consequences={"tags": ["territorial_claim"]},
    ) == ("consequence", "up", True)


def test_resolve_neutral_consequence_down_when_stub_patched() -> None:
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        assert resolve_hybrid_pacing(
            director_decision={"tension_shift": ""},
            turn_consequences={"tags": ["x"]},
        ) == ("consequence", "down", True)


def test_resolve_neutral_consequence_up_when_stub_patched() -> None:
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="up",
    ):
        assert resolve_hybrid_pacing(
            director_decision={},
            turn_consequences={},
        ) == ("consequence", "up", True)


def test_director_non_neutral_ignores_patched_consequence() -> None:
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        assert resolve_hybrid_pacing(
            director_decision={"tension_shift": "escalate"},
            turn_consequences={},
        ) == ("director", "up", False)


def test_saturation_gate_suppresses_consequence_up_at_extreme() -> None:
    src, direction, suppressed = apply_consequence_up_saturation_gate(
        pacing_source="consequence",
        pacing_direction="up",
        current_tension_level="extreme",
    )
    assert (src, direction, suppressed) == ("none", "hold", True)


def test_saturation_gate_extreme_case_insensitive() -> None:
    src, direction, suppressed = apply_consequence_up_saturation_gate(
        pacing_source="consequence",
        pacing_direction="up",
        current_tension_level="  Extreme ",
    )
    assert suppressed is True
    assert (src, direction) == ("none", "hold")


def test_saturation_gate_passes_consequence_up_below_extreme() -> None:
    src, direction, suppressed = apply_consequence_up_saturation_gate(
        pacing_source="consequence",
        pacing_direction="up",
        current_tension_level="high",
    )
    assert suppressed is False
    assert (src, direction) == ("consequence", "up")


def test_saturation_gate_passes_consequence_down_at_extreme() -> None:
    src, direction, suppressed = apply_consequence_up_saturation_gate(
        pacing_source="consequence",
        pacing_direction="down",
        current_tension_level="extreme",
    )
    assert suppressed is False
    assert (src, direction) == ("consequence", "down")


def test_saturation_gate_passes_director_up_at_extreme() -> None:
    src, direction, suppressed = apply_consequence_up_saturation_gate(
        pacing_source="director",
        pacing_direction="up",
        current_tension_level="extreme",
    )
    assert suppressed is False
    assert (src, direction) == ("director", "up")
