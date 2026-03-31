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
    list_scenario_ids,
    load_scenario,
    scenario_prepare_kwargs,
    scenarios_dir,
    validate_optional_scenario_fields,
)


def test_scenarios_dir_exists() -> None:
    assert scenarios_dir().is_dir()


def test_all_scenario_manifests_load() -> None:
    ids = list_scenario_ids()
    assert len(ids) >= 7
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


def test_parse_scene_phase() -> None:
    assert _parse_scene_phase("rising") == ScenePhase.RISING
    assert _parse_scene_phase("OPENING") == ScenePhase.OPENING
    with pytest.raises(ValueError):
        _parse_scene_phase("not_a_phase")
