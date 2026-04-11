"""Tests for investigation recall contract validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_simulation_scenarios import load_scenario
from response_validation_content import validate_bot_response
from response_validation_investigation_recall import (
    validate_investigation_recall_contract,
)


def test_negotiation_recall_fail_and_pass() -> None:
    raw = load_scenario("investigate_i29_negotiation_harley_kizzie_ayame")
    bad = {
        "dialogue": "only ISSUE29_NEGOT_TERMS_V1 here",
        "action": "",
    }
    ok, msg = validate_investigation_recall_contract(
        move=bad,
        orchestration_turn_number=20,
        scenario_raw=raw,
        effective_user_trigger="",
        character_system_prompt="",
    )
    assert ok is False
    assert msg.startswith("[INVESTIGATION_ANCHOR]")

    good = {
        "dialogue": "ISSUE29_NEGOT_TERMS_V1 and ISSUE29_ROLE_ANCHOR_AY noted.",
        "action": "",
    }
    ok2, msg2 = validate_investigation_recall_contract(
        move=good,
        orchestration_turn_number=20,
        scenario_raw=raw,
        effective_user_trigger="",
        character_system_prompt="",
    )
    assert ok2 is True
    assert msg2 == ""

    ok3, _ = validate_investigation_recall_contract(
        move=bad,
        orchestration_turn_number=19,
        scenario_raw=raw,
    )
    assert ok3 is True


def test_validate_bot_response_skips_without_scenario_id() -> None:
    ok, msg = validate_bot_response(
        "ISSUE29_NEGOT_TERMS_V1 ISSUE29_ROLE_ANCHOR_AY",
        "Kizzie",
        "Player",
        [],
        None,
        {
            "dialogue": "ISSUE29_NEGOT_TERMS_V1 ISSUE29_ROLE_ANCHOR_AY",
            "action": "",
        },
        None,
        {},
        None,
        None,
        simulation_scenario_id=None,
        orchestration_turn_number=20,
    )
    assert ok is True


def test_validate_bot_response_enforces_with_scenario_id() -> None:
    ok, msg = validate_bot_response(
        "no tokens",
        "Kizzie",
        "Player",
        [],
        None,
        {"dialogue": "plain", "action": ""},
        None,
        {},
        None,
        None,
        simulation_scenario_id="investigate_i29_negotiation_harley_kizzie_ayame",
        orchestration_turn_number=20,
    )
    assert ok is False
    assert "[INVESTIGATION_ANCHOR]" in msg
