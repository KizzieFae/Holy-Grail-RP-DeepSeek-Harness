"""Scenario manifest validation (no LLM)."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_state import ScenePhase  # noqa: E402
from headless_scene_simulation import (  # noqa: E402
    _parse_scene_phase,
    prepare_headless_session,
)
from progression_simulation_scenarios import (  # noqa: E402
    effective_round1_trigger_text_headless,
    list_scenario_ids,
    load_scenario,
    parse_cli_scene_template_role_assignments,
    scenario_prepare_kwargs,
    scenarios_dir,
    validate_optional_scenario_fields,
    validate_startup_trigger_semantics,
)


def test_scenarios_dir_exists() -> None:
    assert scenarios_dir().is_dir()


def test_all_scenario_manifests_load() -> None:
    ids = list_scenario_ids()
    assert len(ids) >= 8
    params = inspect.signature(prepare_headless_session).parameters
    for sid in ids:
        raw = load_scenario(sid)
        assert raw["id"] == sid
        prep = scenario_prepare_kwargs(raw)
        assert prep["character_card_ids"]
        assert isinstance(prep["seed_escalating_issue"], bool)
        assert prep["initial_tension"]
        assert prep["initial_phase"]
        for k in prep:
            assert k in params, f"Scenario {sid!r}: unknown prepare kwarg {k!r}"


def test_validate_optional_expected_pressure_profile() -> None:
    validate_optional_scenario_fields({"expected_pressure_profile": "HIGH"}, "x")
    validate_optional_scenario_fields({}, "x")
    with pytest.raises(ValueError, match="expected_pressure_profile"):
        validate_optional_scenario_fields({"expected_pressure_profile": "extreme"}, "bad")


def test_validate_optional_evaluation_ontology_profile() -> None:
    validate_optional_scenario_fields(
        {"evaluation_ontology_profile": "generic_net_state_v1"},
        "x",
    )
    with pytest.raises(ValueError, match="evaluation_ontology_profile"):
        validate_optional_scenario_fields(
            {"evaluation_ontology_profile": "not_a_real_profile"},
            "bad",
        )


def test_validate_optional_scene_template_id() -> None:
    validate_optional_scenario_fields(
        {
            "character_card_ids": ["harley_quinn", "magpie"],
            "scene_template_id": "arkham_asylum_cell_intake",
            "scene_template_role_assignments": {
                "harley_quinn": "cell_resident",
                "magpie": "new_arrival",
            },
        },
        "x",
    )
    validate_optional_scenario_fields({}, "x")
    with pytest.raises(ValueError, match="scene_template_id"):
        validate_optional_scenario_fields({"scene_template_id": ""}, "bad")
    with pytest.raises(ValueError, match="scene_template_id"):
        validate_optional_scenario_fields({"scene_template_id": "   "}, "bad")


def test_validate_optional_scene_template_role_assignments() -> None:
    base = {
        "character_card_ids": ["kizzie", "marlene"],
        "scene_template_role_assignments": {
            "kizzie": "misassigned_omega_student",
            "marlene": "alpha_roommate_marlene",
        },
    }
    validate_optional_scenario_fields(dict(base), "x")
    bad = dict(base)
    bad["scene_template_role_assignments"] = {"unknown": "alpha_roommate_marlene"}
    with pytest.raises(ValueError, match="scene_template_role_assignments"):
        validate_optional_scenario_fields(bad, "bad")
    bad2 = dict(base)
    bad2["scene_template_role_assignments"] = "not_a_dict"
    with pytest.raises(ValueError, match="scene_template_role_assignments"):
        validate_optional_scenario_fields(bad2, "bad2")


def test_scenario_prepare_kwargs_scene_template_id_only_when_set() -> None:
    base = {
        "id": "x",
        "title": "t",
        "intent": "i",
        "character_card_ids": ["a"],
        "opening_description": "o",
        "location": "l",
        "trigger_text": "tr",
        "startup_trigger_mode": "overlay",
        "max_turns": 1,
        "seed_escalating_issue": False,
        "beat_shift_active": False,
        "initial_tension": "low",
        "initial_phase": "opening",
    }
    assert "scene_template_id" not in scenario_prepare_kwargs(dict(base))
    with_tpl = dict(base)
    with_tpl["scene_template_id"] = "  tpl  "
    prep = scenario_prepare_kwargs(with_tpl)
    assert prep["scene_template_id"] == "tpl"


def test_parse_scene_phase() -> None:
    assert _parse_scene_phase("rising") == ScenePhase.RISING
    assert _parse_scene_phase("OPENING") == ScenePhase.OPENING
    with pytest.raises(ValueError):
        _parse_scene_phase("not_a_phase")


def test_validate_startup_trigger_parity_ok() -> None:
    validate_startup_trigger_semantics(
        {
            "opening_description": " same line ",
            "trigger_text": "same line",
            "startup_trigger_mode": "parity",
        },
        "t",
    )


def test_validate_startup_trigger_parity_mismatch_fails() -> None:
    with pytest.raises(ValueError, match="parity"):
        validate_startup_trigger_semantics(
            {
                "opening_description": "a",
                "trigger_text": "b",
                "startup_trigger_mode": "parity",
            },
            "t",
        )


def test_validate_startup_trigger_overlay_ok() -> None:
    validate_startup_trigger_semantics(
        {
            "opening_description": "a",
            "trigger_text": "b",
            "startup_trigger_mode": "overlay",
        },
        "t",
    )


def test_validate_startup_trigger_overlay_same_text_fails() -> None:
    with pytest.raises(ValueError, match="overlay"):
        validate_startup_trigger_semantics(
            {
                "opening_description": "x",
                "trigger_text": "x",
                "startup_trigger_mode": "overlay",
            },
            "t",
        )


def test_parse_cli_scene_template_role_assignments() -> None:
    m = parse_cli_scene_template_role_assignments("a=1,b=2")
    assert m == {"a": "1", "b": "2"}
    assert parse_cli_scene_template_role_assignments("") == {}
    with pytest.raises(ValueError):
        parse_cli_scene_template_role_assignments("nope")


def test_effective_round1_trigger_parity_uses_opening_final() -> None:
    raw = load_scenario("parity_opening_trigger_smoke")
    t = effective_round1_trigger_text_headless(
        scenario_raw=raw,
        simulation_opening_final="resolved opening from session",
        adhoc_fallback_trigger="fallback",
        cli_trigger_provided=False,
        cli_trigger_value="",
    )
    assert t == "resolved opening from session"


def test_effective_round1_trigger_overlay_uses_manifest() -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    t = effective_round1_trigger_text_headless(
        scenario_raw=raw,
        simulation_opening_final="different resolved",
        adhoc_fallback_trigger="fallback",
        cli_trigger_provided=False,
        cli_trigger_value="",
    )
    assert t == str(raw["trigger_text"])


def test_effective_round1_cli_override_wins() -> None:
    raw = load_scenario("parity_opening_trigger_smoke")
    t = effective_round1_trigger_text_headless(
        scenario_raw=raw,
        simulation_opening_final="x",
        adhoc_fallback_trigger="y",
        cli_trigger_provided=True,
        cli_trigger_value="from cli",
    )
    assert t == "from cli"


def test_effective_round1_adhoc_uses_opening_final() -> None:
    t = effective_round1_trigger_text_headless(
        scenario_raw=None,
        simulation_opening_final="adhoc opening final",
        adhoc_fallback_trigger="standoff",
        cli_trigger_provided=False,
        cli_trigger_value="",
    )
    assert t == "adhoc opening final"
