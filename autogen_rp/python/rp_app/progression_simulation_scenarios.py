"""Load fixed progression-layer simulation scenarios (JSON under ``data/progression_simulation_scenarios``).

Each manifest must include ``startup_trigger_mode`` (Issue #83 scenario contract):

- ``parity`` — ``opening_description`` and ``trigger_text`` are the same string (strip-normalized);
  headless round-1 trigger follows the finalized opening.
- ``overlay`` — ``trigger_text`` is an explicit first-round simulation overlay and must differ
  from ``opening_description``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SCENARIOS_DIR = Path(__file__).resolve().parent / "data" / "progression_simulation_scenarios"

_EXPECTED_PRESSURE_PROFILES = frozenset({"low", "medium", "high"})
_STARTUP_TRIGGER_MODES = frozenset({"parity", "overlay"})

_REQUIRED_KEYS = frozenset(
    {
        "id",
        "title",
        "intent",
        "character_card_ids",
        "opening_description",
        "location",
        "trigger_text",
        "startup_trigger_mode",
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
    tid: str | None = None
    if "scene_template_id" in raw and raw["scene_template_id"] is not None:
        tid = str(raw["scene_template_id"]).strip()
        if not tid:
            raise ValueError(
                f"Scenario {scenario_id!r}: scene_template_id must be a non-empty string when present"
            )
    if raw.get("scene_template_role_assignments") is not None:
        ra = raw["scene_template_role_assignments"]
        if not isinstance(ra, dict):
            raise ValueError(
                f"Scenario {scenario_id!r}: scene_template_role_assignments must be an object"
            )
        cards = {str(x).strip() for x in raw.get("character_card_ids", []) if str(x).strip()}
        for key, val in ra.items():
            ck = str(key or "").strip()
            rv = str(val or "").strip()
            if not ck or not rv:
                raise ValueError(
                    f"Scenario {scenario_id!r}: scene_template_role_assignments "
                    f"has empty key or value: {key!r} -> {val!r}"
                )
            if ck not in cards:
                raise ValueError(
                    f"Scenario {scenario_id!r}: scene_template_role_assignments "
                    f"key {ck!r} is not in character_card_ids"
                )
    opt_anchor = raw.get("anchor_role_name")
    if opt_anchor is not None and str(opt_anchor).strip():
        if not tid:
            raise ValueError(
                f"Scenario {scenario_id!r}: anchor_role_name is only valid with scene_template_id"
            )

    if tid:
        from scene_template import SceneTemplateManager, validate_role_assignments

        try:
            template = SceneTemplateManager().load_template(tid)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Scenario {scenario_id!r}: cannot load scene template {tid!r}: {exc}"
            ) from exc
        if opt_anchor is not None and str(opt_anchor).strip():
            oa = str(opt_anchor).strip()
            if oa != template.anchor_role_name:
                raise ValueError(
                    f"Scenario {scenario_id!r}: anchor_role_name must match template "
                    f"{tid!r} ({template.anchor_role_name!r}), got {oa!r}"
                )
        ra = raw.get("scene_template_role_assignments")
        if not isinstance(ra, dict) or not ra:
            raise ValueError(
                f"Scenario {scenario_id!r}: scene_template_role_assignments is required "
                f"when scene_template_id is set (Issue #80)"
            )
        cards_list = [
            str(x).strip() for x in raw.get("character_card_ids", []) if str(x).strip()
        ]
        for cid in cards_list:
            if cid not in ra:
                raise ValueError(
                    f"Scenario {scenario_id!r}: scene_template_role_assignments "
                    f"missing entry for character_card_id {cid!r}"
                )
        issues = validate_role_assignments(template, cards_list, ra)
        if issues:
            raise ValueError(
                f"Scenario {scenario_id!r}: invalid template role assignments: "
                + "; ".join(issues)
            )
        anchor = template.anchor_role_name
        n_anchor = sum(
            1
            for cid in cards_list
            if str(ra.get(cid, "") or "").strip().lower() == anchor.lower()
        )
        if n_anchor != 1:
            raise ValueError(
                f"Scenario {scenario_id!r}: exactly one character must be assigned "
                f"anchor role {anchor!r} for template {tid!r} (found {n_anchor})"
            )


def validate_startup_trigger_semantics(raw: dict[str, Any], scenario_id: str) -> None:
    """Enforce explicit parity vs overlay startup contract (Issue #83).

    * ``parity`` — round-1 user line matches the scene opening text in the manifest
      (``opening_description`` == ``trigger_text``); headless uses ``simulation_opening_final`` as trigger.
    * ``overlay`` — manifest ``trigger_text`` is an explicit first-round simulation overlay
      and must differ from ``opening_description``.
    """
    mode = str(raw.get("startup_trigger_mode", "")).strip().lower()
    if mode not in _STARTUP_TRIGGER_MODES:
        raise ValueError(
            f"Scenario {scenario_id!r}: startup_trigger_mode must be 'parity' or 'overlay', "
            f"got {raw.get('startup_trigger_mode')!r}"
        )
    o = str(raw.get("opening_description") or "").strip()
    t = str(raw.get("trigger_text") or "").strip()
    if mode == "parity" and o != t:
        raise ValueError(
            f"Scenario {scenario_id!r}: startup_trigger_mode is 'parity' but "
            f"opening_description and trigger_text differ"
        )
    if mode == "overlay" and o == t:
        raise ValueError(
            f"Scenario {scenario_id!r}: startup_trigger_mode is 'overlay' but "
            f"opening_description equals trigger_text (use 'parity' when they match)"
        )


def parse_cli_scene_template_role_assignments(spec: str | None) -> dict[str, str]:
    """Parse ``card=role,card=role`` from CLI ``--scene-template-roles`` (ad-hoc template runs)."""
    if spec is None or not str(spec).strip():
        return {}
    out: dict[str, str] = {}
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(
                f"Invalid scene-template-roles segment {part!r}; use card=role,card=role"
            )
        card, role = part.split("=", 1)
        ck = card.strip()
        rk = role.strip()
        if not ck or not rk:
            raise ValueError(
                f"Invalid scene-template-roles segment {part!r}; card and role must be non-empty"
            )
        out[ck] = rk
    return out


def effective_round1_trigger_text_headless(
    *,
    scenario_raw: dict[str, Any] | None,
    simulation_opening_final: str,
    adhoc_fallback_trigger: str,
    cli_trigger_provided: bool,
    cli_trigger_value: str,
) -> str:
    """Resolve round-1 user trigger for headless when no trigger schedule is active.

    ``--trigger`` always wins. Ad-hoc runs use the finalized opening as the canonical default.
    Scenario runs consult ``startup_trigger_mode`` (validated at load time).
    """
    if cli_trigger_provided:
        return cli_trigger_value
    fin = str(simulation_opening_final or "").strip()
    if scenario_raw is None:
        return fin if fin else str(adhoc_fallback_trigger or "").strip()
    mode = str(scenario_raw.get("startup_trigger_mode") or "").strip().lower()
    if mode == "parity":
        return fin
    return str(scenario_raw.get("trigger_text") or "").strip()


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
    validate_startup_trigger_semantics(raw, scenario_id)
    return raw


def audit_owner_slug(scenario_id: str) -> str:
    """Safe owner string for audit filenames (alphanumeric + underscore)."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", scenario_id).strip("_").lower()
    return s or "headless_sim"


def scenario_prepare_kwargs(raw: dict[str, Any]) -> dict[str, Any]:
    """Kwargs for ``prepare_headless_session`` from scenario dict."""
    out: dict[str, Any] = {
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
    if raw.get("scene_template_id") is not None and str(raw.get("scene_template_id") or "").strip():
        out["scene_template_id"] = str(raw["scene_template_id"]).strip()
    if raw.get("scene_template_role_assignments") is not None and isinstance(
        raw.get("scene_template_role_assignments"), dict
    ):
        out["scene_template_role_assignments"] = {
            str(k).strip(): str(v).strip()
            for k, v in raw["scene_template_role_assignments"].items()
            if str(k or "").strip() and str(v or "").strip()
        }
    return out
