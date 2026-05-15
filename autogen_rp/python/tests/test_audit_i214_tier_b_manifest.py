"""GitHub #214 Tier B — scenario manifest contract (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_simulation_scenarios import load_scenario  # noqa: E402
from tier_b_session_schedule import parse_tier_b_session_mutation_schedule  # noqa: E402


def test_audit_i214_is_tier_b_continuity_grounded() -> None:
    raw = load_scenario("audit_i214_offstage_continuity_tier_b")
    assert raw.get("audit_validation_tier") == "tier_b_continuity_grounded"
    assert raw.get("audit_program_issue") == "214"
    assert raw.get("startup_trigger_mode") == "overlay"
    sched = raw.get("tier_b_session_mutation_schedule")
    assert isinstance(sched, list) and len(sched) >= 2
    gate = raw.get("tier_b_continuity_gate")
    assert isinstance(gate, dict)
    assert gate.get("excursion_id") == "i214_tier_b_exc"
    assert gate.get("excursion_participant_card_id") == "hannah"


def test_tier_b_schedule_parses_to_mutation_requests() -> None:
    raw = load_scenario("audit_i214_offstage_continuity_tier_b")
    by_turn = parse_tier_b_session_mutation_schedule(
        raw,
        card_to_agent={"hannah": "Hannah_Lovelace"},
    )
    assert set(by_turn.keys()) == {1, 6}
    assert len(by_turn[1]) == 1
    assert by_turn[1][0].payload.get("participant_character_ids") == ["Hannah_Lovelace"]
