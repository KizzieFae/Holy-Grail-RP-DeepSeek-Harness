"""Deterministic progression enforcement: qualify structural deltas after process_turn.

Reads continuity turn metadata and issue snapshots only. Does not mutate continuity.
Presence deltas (Q3) are derived from continuity turn_meta['consequences'] (same source
orchestration later mirrors into presence_changes), not from orchestration_state.
"""

from __future__ import annotations

from typing import Any

from progression_advisory import (
    STALL_BEAT_SHIFT_THRESHOLD,
    compute_stall_score,
)

ALLOWED_SCENE_STATE_UPDATE_KEYS = frozenset(
    {
        "sleeping_surface_assignment",
        "housing_call_outcome",
        "suppressant_formulation_outcome",
        "location_entry_outcome",
    }
)

_PRESENCE_CONSEQUENCE_MARKERS = frozenset({"exit", "arrival"})

# Single enforcement threshold (must match beat-shift / advisory high band).
ENFORCEMENT_THRESHOLD = STALL_BEAT_SHIFT_THRESHOLD


def _active_issue_dicts_for_stall(continuity_manager: Any | None) -> list[dict[str, Any]]:
    if continuity_manager is None:
        return []
    ctx = continuity_manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=4,
        summary_limit=3,
    )
    out: list[dict[str, Any]] = []
    for iss in ctx.get("active_issues") or []:
        if hasattr(iss, "to_dict"):
            out.append(iss.to_dict())
    return out


def progression_delta_required(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    current_actor: str | None = None,
    current_move: dict[str, Any] | None = None,
) -> bool:
    """Sole hard predicate: require Q1–Q4 progression delta when True.

    Strictly ``stall_score >= ENFORCEMENT_THRESHOLD`` — no OR branches.
    """
    scene_state = orchestration_state.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    moves = orchestration_state.get("recent_structured_moves")
    if not isinstance(moves, list):
        moves = []
    snaps = orchestration_state.get("beat_shift_scene_snapshots")
    if not isinstance(snaps, list):
        snaps = []
    issues = _active_issue_dicts_for_stall(continuity_manager)
    stall_score, _ = compute_stall_score(
        scene_state=scene_state,
        recent_structured_moves=moves,
        active_issues=issues,
        beat_shift_snapshots=snaps,
        current_actor=current_actor,
        current_move=current_move,
    )
    return bool(stall_score >= ENFORCEMENT_THRESHOLD)

# Issue snapshot for Q2: status, participants, status_reason, last_change (normalized strings).
IssueSignature = tuple[str, frozenset[str], str, str]


def _norm_issue_text(val: Any) -> str:
    return str(val or "").strip()


def collect_issue_signatures(continuity_manager: Any) -> dict[str, IssueSignature]:
    """Stable issue snapshot for material-change detection (pre–process_turn)."""
    out: dict[str, IssueSignature] = {}
    issues = getattr(continuity_manager, "issues", None) or {}
    for issue in issues.values():
        sid = str(getattr(issue, "issue_id", "") or "")
        if not sid:
            continue
        status = getattr(issue, "status", "")
        st = str(getattr(status, "value", status) or "")
        raw_parts = getattr(issue, "participants", []) or []
        parts = frozenset(str(p).strip() for p in raw_parts if str(p).strip())
        sr = _norm_issue_text(getattr(issue, "status_reason", ""))
        lc = _norm_issue_text(getattr(issue, "last_change", ""))
        out[sid] = (st, parts, sr, lc)
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
    issues_before: dict[str, IssueSignature],
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
        sr = _norm_issue_text(getattr(issue, "status_reason", ""))
        lc = _norm_issue_text(getattr(issue, "last_change", ""))
        before = issues_before.get(sid)
        if before is None:
            return True
        b_st, b_parts, b_sr, b_lc = before
        if (
            b_st != st
            or b_parts != parts
            or b_sr != sr
            or b_lc != lc
        ):
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
    issues_before: dict[str, IssueSignature],
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
    """Compatibility alias: same as ``progression_delta_required`` without parsed move."""
    return progression_delta_required(
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
        current_actor=None,
        current_move=None,
    )
