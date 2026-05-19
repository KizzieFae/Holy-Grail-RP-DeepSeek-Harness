"""GitHub #234 — cert manifest loader validation (Execution Group 1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_simulation_scenarios import (  # noqa: E402
    effective_round1_trigger_text_headless,
    load_scenario,
    scenario_prepare_kwargs,
    validate_startup_trigger_semantics,
)

CERT_ID = "cert_i234_proposal_accept_off_focal"


def test_cert_i234_manifest_loads_and_prepares() -> None:
    raw = load_scenario(CERT_ID)
    assert raw["id"] == CERT_ID
    assert raw["character_card_ids"] == ["ayame", "celina"]
    assert "scene_template_id" not in raw
    assert 4 <= int(raw["max_turns"]) <= 6
    assert raw["startup_trigger_mode"] == "overlay"
    validate_startup_trigger_semantics(raw, CERT_ID)
    prep = scenario_prepare_kwargs(raw)
    assert prep["character_card_ids"] == ["ayame", "celina"]
    assert prep["seed_escalating_issue"] is False
    trigger = effective_round1_trigger_text_headless(
        scenario_raw=raw,
        simulation_opening_final=str(raw.get("opening_description", "")),
        adhoc_fallback_trigger=str(raw.get("trigger_text", "")),
        cli_trigger_provided=False,
        cli_trigger_value="",
    )
    assert "semantic_proposals" in trigger
    assert "off_focal" in trigger
    assert "Celina" in trigger
    assert "illegal" not in trigger.lower() or "do not use illegal" in trigger.lower()


def test_cert_i234_no_template_or_illegal_overlay_stanza() -> None:
    raw = load_scenario(CERT_ID)
    opening = str(raw.get("opening_description", ""))
    trigger = str(raw.get("trigger_text", ""))
    combined = (opening + trigger).lower()
    assert "scene_template_id" not in raw
    assert "must_remain" not in combined
    assert "illegal overlay" not in combined
    assert "scene_template_role_assignments" not in raw
