"""Deterministic progression enforcement: qualify structural deltas after process_turn.

Reads continuity turn metadata and issue snapshots only. Does not mutate continuity.
Presence deltas (Q3) are derived from continuity turn_meta['consequences'] (same source
orchestration later mirrors into presence_changes), not from orchestration_state.
"""

from __future__ import annotations

from typing import Any

from beat_shift_state import is_pending_beat_shift_active
from progression_advisory import sync_progression_advisory_for_prompts

ALLOWED_SCENE_STATE_UPDATE_KEYS = frozenset(
    {
        "sleeping_surface_assignment",
        "housing_call_outcome",
        "suppressant_formulation_outcome",
        "location_entry_outcome",
    }
)

_PRESENCE_CONSEQUENCE_MARKERS = frozenset({"exit", "arrival"})


def collect_issue_signatures(continuity_manager: Any) -> dict[str, tuple[str, frozenset[str]]]:
    """Stable issue snapshot for material-change detection (pre–process_turn)."""
    out: dict[str, tuple[str, frozenset[str]]] = {}
    issues = getattr(continuity_manager, "issues", None) or {}
    for issue in issues.values():
        sid = str(getattr(issue, "issue_id", "") or "")
        if not sid:
            continue
        status = getattr(issue, "status", "")
        st = str(getattr(status, "value", status) or "")
        raw_parts = getattr(issue, "participants", []) or []
        parts = frozenset(str(p).strip() for p in raw_parts if str(p).strip())
        out[sid] = (st, parts)
    return out


def _normalized_consequence_list(turn_meta: dict[str, Any]) -> list[str]:
    raw = turn_meta.get("consequences", [])
    if not isinstance(raw, list):
        return []
    return [str(c).strip() for c in raw if str(c or "").strip()]


def _q2_issue_material_change(
    *,
    continuity_manager: Any,
    turn_index: int,
    issues_before: dict[str, tuple[str, frozenset[str]]],
) -> bool:
    for issue in (getattr(continuity_manager, "issues", None) or {}).values():
        last_ti = int(getattr(issue, "last_turn_index", 0) or 0)
        if last_ti != turn_index:
            continue
        sid = str(getattr(issue, "issue_id", "") or "")
        if not sid:
            continue
        status = getattr(issue, "status", "")
        st = str(getattr(status, "value", status) or "")
        raw_parts = getattr(issue, "participants", []) or []
        parts = frozenset(str(p).strip() for p in raw_parts if str(p).strip())
        before = issues_before.get(sid)
        if before is None:
            return True
        b_st, b_parts = before
        if b_st != st or b_parts != parts:
            return True
    return False


def _q3_presence_delta_from_continuity_turn_meta(turn_meta: dict[str, Any]) -> bool:
    """True if continuity classified exit/arrival this turn (authoritative for Q3)."""
    for c in _normalized_consequence_list(turn_meta):
        if c.lower() in _PRESENCE_CONSEQUENCE_MARKERS:
            return True
    return False


def _q4_bounded_scene_state_updates(move: dict[str, Any]) -> bool:
    raw = move.get("scene_state_updates")
    if not isinstance(raw, dict):
        return False
    for key in raw.keys():
        k = str(key or "").strip()
        if k in ALLOWED_SCENE_STATE_UPDATE_KEYS:
            return True
    return False


def _q1_consequences_qualify(
    *,
    continuity_manager: Any,
    turn_index: int,
    turn_meta: dict[str, Any],
    q2: bool,
    q3: bool,
    q4: bool,
) -> bool:
    cons = _normalized_consequence_list(turn_meta)
    if not cons:
        return False
    if q2 or q3 or q4:
        return True
    if len(cons) != 1:
        return True
    sole = cons[0]
    meta_by_index = getattr(continuity_manager, "turn_metadata_by_index", {}) or {}
    prev_meta = meta_by_index.get(turn_index - 1)
    if not isinstance(prev_meta, dict):
        return True
    prev_cons = _normalized_consequence_list(prev_meta)
    if len(prev_cons) != 1:
        return True
    return prev_cons[0] != sole


def qualifies_as_progression_delta(
    *,
    continuity_manager: Any,
    turn_index: int,
    turn_meta: dict[str, Any],
    issues_before: dict[str, tuple[str, frozenset[str]]],
    move: dict[str, Any],
) -> bool:
    """Return True if this turn satisfies the v1 progression contract (Q1–Q4)."""
    q2 = _q2_issue_material_change(
        continuity_manager=continuity_manager,
        turn_index=turn_index,
        issues_before=issues_before,
    )
    q3 = _q3_presence_delta_from_continuity_turn_meta(turn_meta)
    q4 = _q4_bounded_scene_state_updates(move)
    q1 = _q1_consequences_qualify(
        continuity_manager=continuity_manager,
        turn_index=turn_index,
        turn_meta=turn_meta,
        q2=q2,
        q3=q3,
        q4=q4,
    )
    return bool(q1 or q2 or q3 or q4)


def progression_enforcement_gate_active(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
) -> bool:
    """v1: require delta when beat-shift pending OR progression_pressure is high."""
    if is_pending_beat_shift_active(orchestration_state):
        return True
    advisory = sync_progression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
    )
    return str(advisory.get("progression_pressure") or "") == "high"
