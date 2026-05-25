"""Issue #242 — topology manifest extraction tests."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from prompt_topology_issue240 import build_character_turn_prompt_for_runtime
from prompt_topology_manifest import extract_topology_manifest
from test_prompt_builders import _minimal_character_prompt_kwargs


@pytest.fixture(autouse=True)
def _clear_issue240_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_ISSUE240_PROMPT_TOPOLOGY", raising=False)


def _three_character_prompt_kwargs() -> dict:
    kwargs = _minimal_character_prompt_kwargs()
    kwargs.update(
        char_name="Willow_Reeves",
        scene_state={
            "location": "university_dorm_triple",
            "present_characters": ["Kizzie", "Marlene_Fletcher", "Willow_Reeves"],
            "offstage_characters": [],
        },
        cast=["Kizzie", "Marlene_Fletcher", "Willow_Reeves"],
        state_context="- Emotional state: controlled steadiness\n",
        trigger_text="Traveler: test trigger",
        active_issues=[{"description": "Settle dorm logistics under quiet tension."}],
    )
    return kwargs


def test_topology_manifest_v1_next7_two_char_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["scene_state"] = {"location": "corridor", "present_characters": ["Ayame", "Celina"]}
    kwargs["cast"] = ["Ayame", "Celina"]
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    manifest = extract_topology_manifest(prompt)

    assert manifest["topology_inferred"] == "v1_next7"
    assert manifest["expected_profile_id"] == "v1_next7_2char"
    assert manifest["profile_match"] is True
    assert manifest["markers"]["opening_dual_role"] is True
    assert manifest["markers"]["semantic_evaluation_required"] is True
    assert manifest["markers"]["proposal_schema_teaching_v249_a"] is True
    assert manifest["markers"]["threshold_calibration_v1_next7"] is False
    assert manifest["markers"]["participation_frame"] is False
    assert manifest["markers"]["participation_arc"] is False
    assert manifest["adjacency"]["semantic_self_report_before_private_state"] is True
    assert "semantic.block" in manifest["topology_fingerprint"]


def test_topology_manifest_v1_next7_three_char_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    manifest = extract_topology_manifest(prompt)

    assert manifest["expected_profile_id"] == "v1_next7_3char_plus"
    assert manifest["profile_match"] is True
    assert manifest["markers"]["participation_arc"] is True
    assert manifest["markers"]["active_focus_capsule"] is True
    assert manifest["markers"]["threshold_bridge_v1_next6"] is False

    offsets = manifest["ordering"]["offsets"]
    sem = offsets["semantic_self_report"]
    schema = offsets["proposal_schema"]
    arc = offsets["participation_arc"]
    focus = offsets["active_focus"]
    assert sem is not None and schema is not None and arc is not None
    assert focus is not None
    assert sem < schema < arc < focus
    assert "bridge.v6" not in manifest["topology_fingerprint"]


def test_topology_manifest_default_v1_next7_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_ISSUE240_PROMPT_TOPOLOGY", raising=False)
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    manifest = extract_topology_manifest(prompt)

    assert manifest["topology_inferred"] == "v1_next7"
    assert manifest["expected_profile_id"] == "v1_next7_2char"
    assert manifest["profile_match"] is True
    assert manifest["markers"]["semantic_evaluation_required"] is True
    assert manifest["markers"]["proposal_schema_teaching_v249_a"] is True
    assert manifest["markers"]["threshold_calibration_v1_next7"] is False
    assert manifest["markers"]["output_rules_production_semantic_proposals"] is False


def test_topology_manifest_production_legacy_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "production_legacy")
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    manifest = extract_topology_manifest(prompt)

    assert manifest["topology_inferred"] == "production"
    assert manifest["expected_profile_id"] == "production_baseline"
    assert manifest["profile_match"] is True
    assert manifest["markers"]["opening_production"] is True
    assert manifest["markers"]["semantic_evaluation_required"] is True
    assert manifest["markers"]["semantic_self_report"] is False


def test_topology_manifest_detects_suffix_layers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    prompt += "\n\nPROGRESSION ADVISORY: advance the scene.\n"
    manifest = extract_topology_manifest(prompt)
    assert manifest["markers"]["progression_advisory_suffix"] is True
