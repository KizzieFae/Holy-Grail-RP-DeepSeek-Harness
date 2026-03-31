"""Load fixed progression-layer simulation scenarios (JSON under ``data/progression_simulation_scenarios``)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SCENARIOS_DIR = Path(__file__).resolve().parent / "data" / "progression_simulation_scenarios"

_EXPECTED_PRESSURE_PROFILES = frozenset({"low", "medium", "high"})

_REQUIRED_KEYS = frozenset(
    {
        "id",
        "title",
        "intent",
        "character_card_ids",
        "opening_description",
        "location",
        "trigger_text",
        "max_turns",
        "seed_escalating_issue",
        "beat_shift_active",
        "initial_tension",
        "initial_phase",
    }
)


def validate_optional_scenario_fields(raw: dict[str, Any], scenario_id: str) -> None:
    """Reject invalid values for optional manifest fields."""
    if "expected_pressure_profile" in raw and raw["expected_pressure_profile"] is not None:
        v = str(raw["expected_pressure_profile"]).strip().lower()
        if v not in _EXPECTED_PRESSURE_PROFILES:
            raise ValueError(
                f"Scenario {scenario_id!r}: expected_pressure_profile must be one of "
                f"{sorted(_EXPECTED_PRESSURE_PROFILES)}, got {raw['expected_pressure_profile']!r}"
            )


def scenarios_dir() -> Path:
    return _SCENARIOS_DIR


def list_scenario_ids() -> list[str]:
    if not _SCENARIOS_DIR.is_dir():
        return []
    out: list[str] = []
    for p in sorted(_SCENARIOS_DIR.glob("*.json")):
        out.append(p.stem)
    return out


def load_scenario(scenario_id: str) -> dict[str, Any]:
    """Load scenario by id (filename without ``.json``)."""
    path = _SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No scenario file: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Scenario {scenario_id!r} must be a JSON object")
    missing = _REQUIRED_KEYS - raw.keys()
    if missing:
        raise ValueError(f"Scenario {scenario_id!r} missing keys: {sorted(missing)}")
    if raw["id"] != scenario_id:
        raise ValueError(
            f"Scenario file {scenario_id!r} has mismatched id field {raw['id']!r}"
        )
    validate_optional_scenario_fields(raw, scenario_id)
    return raw


def audit_owner_slug(scenario_id: str) -> str:
    """Safe owner string for audit filenames (alphanumeric + underscore)."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", scenario_id).strip("_").lower()
    return s or "headless_sim"


def scenario_prepare_kwargs(raw: dict[str, Any]) -> dict[str, Any]:
    """Kwargs for ``prepare_headless_session`` from scenario dict."""
    return {
        "character_card_ids": list(raw["character_card_ids"]),
        "opening_description": str(raw["opening_description"]),
        "location": str(raw["location"]),
        "seed_escalating_issue": bool(raw["seed_escalating_issue"]),
        "beat_shift_active": bool(raw["beat_shift_active"]),
        "initial_tension": str(raw["initial_tension"]),
        "initial_phase": str(raw["initial_phase"]),
        "seed_issue": raw.get("seed_issue"),
        "scenario_id": str(raw["id"]),
        "scenario_title": str(raw["title"]),
        "scenario_intent": str(raw["intent"]),
        "expected_pressure_profile": (
            str(raw["expected_pressure_profile"]).strip().lower()
            if raw.get("expected_pressure_profile") is not None
            and str(raw.get("expected_pressure_profile") or "").strip()
            else None
        ),
    }
