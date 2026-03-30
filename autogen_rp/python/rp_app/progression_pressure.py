"""Deterministic progression pressure state derived from continuity outputs.

This module tracks scene- and issue-level progression debt using only structured
signals that already exist in continuity-owned state. It does not write
continuity truth; it stores derived pressure memory on orchestration state.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger("rp_app.progression_pressure")

TurnClass = Literal[
    "material_progression",
    "partial_progression",
    "non_progression",
    "explicit_stagnation",
]
Tier = Literal["stable", "unstable", "escalating", "forcing"]

_STATE_KEY = "progression_pressure"
_MAX_DEBT = 10
_SCENE_MATERIAL_RESET_STATUSES = frozenset({"active", "escalating", "stalled"})
_RELEVANT_ISSUE_STATUSES = frozenset({"active", "escalating", "stalled"})
_TRACKED_ISSUE_STATUSES = frozenset({"active", "escalating", "stalled", "dormant"})
_SCENE_CORE_FIELDS = (
    "scene_phase",
    "location",
    "present_characters",
    "offstage_characters",
)
_MATERIAL_CONSEQUENCE_TAGS = frozenset(
    {
        "access_granted",
        "access_denied",
        "arrival",
        "decision_made",
        "dependency_advanced",
        "exit",
        "medical_state_set",
        "physical_state_set",
        "plan_committed",
        "revelation",
    }
)


def default_progression_pressure_state() -> dict[str, Any]:
    return {
        "scene_progression_debt": 0,
        "scene_instability_tier": "stable",
        "issue_progression_debt": {},
        "issue_instability_tiers": {},
        "dominant_issue_ids": [],
        "issue_identity_aliases": {},
        "issue_identity_notes": [],
        "tracked_issue_fingerprints": {},
        "last_turn": {},
    }


def ensure_progression_pressure_state(orchestration_state: dict[str, Any]) -> dict[str, Any]:
    raw = orchestration_state.get(_STATE_KEY)
    if not isinstance(raw, dict):
        raw = default_progression_pressure_state()
        orchestration_state[_STATE_KEY] = raw
    raw.setdefault("scene_progression_debt", 0)
    raw.setdefault("scene_instability_tier", "stable")
    raw.setdefault("issue_progression_debt", {})
    raw.setdefault("issue_instability_tiers", {})
    raw.setdefault("dominant_issue_ids", [])
    raw.setdefault("issue_identity_aliases", {})
    raw.setdefault("issue_identity_notes", [])
    raw.setdefault("tracked_issue_fingerprints", {})
    raw.setdefault("last_turn", {})
    return raw


def get_cached_progression_pressure(orchestration_state: dict[str, Any]) -> dict[str, Any] | None:
    raw = orchestration_state.get(_STATE_KEY)
    return raw if isinstance(raw, dict) else None


def capture_progression_truth_snapshot(continuity_manager: Any | None) -> dict[str, Any]:
    if continuity_manager is None:
        return {
            "issues": {},
            "scene_core": {},
            "resolved_outcomes": {},
            "active_issue_ids": [],
            "tracked_issue_ids": [],
        }

    issues: dict[str, dict[str, Any]] = {}
    for issue in getattr(continuity_manager, "issues", {}).values():
        snap = _snapshot_issue(issue)
        issue_id = str(snap.get("issue_id", "") or "")
        if issue_id:
            issues[issue_id] = snap

    scene_core = _snapshot_scene_core(getattr(continuity_manager, "scene_state", None))
    outcomes: dict[str, dict[str, Any]] = {}
    for outcome in getattr(continuity_manager, "resolved_outcomes", []) or []:
        snap = _snapshot_outcome(outcome)
        outcome_id = str(snap.get("outcome_id", "") or "")
        if outcome_id:
            outcomes[outcome_id] = snap

    return {
        "issues": issues,
        "scene_core": scene_core,
        "resolved_outcomes": outcomes,
        "active_issue_ids": [
            issue_id
            for issue_id, snap in issues.items()
            if _is_actionable_status(str(snap.get("status", "") or ""))
        ],
        "tracked_issue_ids": [
            issue_id
            for issue_id, snap in issues.items()
            if _is_tracked_issue_status(str(snap.get("status", "") or ""))
        ],
    }


def update_progression_pressure_state(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any | None,
    before_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    state = ensure_progression_pressure_state(orchestration_state)
    before = before_snapshot if isinstance(before_snapshot, dict) else {}
    after = capture_progression_truth_snapshot(continuity_manager)
    turn_index = int(getattr(continuity_manager, "turn_counter", 0) or 0)
    turn_meta = {}
    metadata_by_index = getattr(continuity_manager, "turn_metadata_by_index", {})
    if isinstance(metadata_by_index, dict):
        candidate_meta = metadata_by_index.get(turn_index, {})
        if isinstance(candidate_meta, dict):
            turn_meta = candidate_meta

    resolved_deltas = _collect_resolved_outcome_deltas(
        before_outcomes=before.get("resolved_outcomes", {}),
        after_outcomes=after.get("resolved_outcomes", {}),
        turn_index=turn_index,
    )
    alias_notes = _preserve_issue_identity_continuity(
        state=state,
        before_issues=before.get("issues", {}),
        after_issues=after.get("issues", {}),
    )
    issue_classes = _classify_issues(
        state=state,
        before_issues=before.get("issues", {}),
        after_issues=after.get("issues", {}),
        resolved_deltas=resolved_deltas,
        turn_index=turn_index,
    )
    dominant_before = _dominant_issue_ids(
        debt_map=state.get("issue_progression_debt", {}),
        issue_ids=before.get("tracked_issue_ids", []),
        issues=before.get("issues", {}),
    )
    scene_class, scene_debug = _classify_scene_turn(
        state=state,
        before_issues=before.get("issues", {}),
        after_issues=after.get("issues", {}),
        before_active_issue_ids=before.get("active_issue_ids", []),
        after_active_issue_ids=after.get("active_issue_ids", []),
        before_scene_core=before.get("scene_core", {}),
        after_scene_core=after.get("scene_core", {}),
        issue_classes=issue_classes,
        resolved_deltas=resolved_deltas,
        turn_meta=turn_meta,
        dominant_before=dominant_before,
    )

    scene_before = int(state.get("scene_progression_debt", 0) or 0)
    scene_after = _apply_debt_delta(scene_before, scene_class)
    state["scene_progression_debt"] = scene_after
    state["scene_instability_tier"] = tier_for_scene_debt(scene_after)

    issue_debt = state.setdefault("issue_progression_debt", {})
    issue_tiers = state.setdefault("issue_instability_tiers", {})
    for issue_id, info in issue_classes.items():
        before_value = int(issue_debt.get(issue_id, 0) or 0)
        after_value = _apply_debt_delta(before_value, str(info.get("turn_class", "")))
        issue_debt[issue_id] = after_value
        issue_tiers[issue_id] = tier_for_issue_debt(after_value)
        info["debt_before"] = before_value
        info["debt_after"] = after_value
        info["tier_after"] = issue_tiers[issue_id]

    tracked_issue_ids = [
        issue_id
        for issue_id, snap in after.get("issues", {}).items()
        if _is_tracked_issue_status(str(snap.get("status", "") or ""))
    ]
    state["dominant_issue_ids"] = _dominant_issue_ids(
        debt_map=issue_debt,
        issue_ids=tracked_issue_ids,
        issues=after.get("issues", {}),
    )
    notes = list(state.get("issue_identity_notes", []) or [])
    if alias_notes:
        notes.extend(alias_notes)
    state["issue_identity_notes"] = notes[-12:]
    tracked_fingerprints = state.setdefault("tracked_issue_fingerprints", {})
    for issue_id, snap in after.get("issues", {}).items():
        status = str(snap.get("status", "") or "")
        if _is_tracked_issue_status(status):
            tracked_fingerprints[issue_id] = str(snap.get("fingerprint", "") or "")

    consequence_delta = _classify_consequence_delta(turn_meta=turn_meta)
    state["last_turn"] = {
        "turn_index": turn_index,
        "scene_turn_class": scene_class,
        "scene_debt_before": scene_before,
        "scene_debt_after": scene_after,
        "scene_tier_after": state["scene_instability_tier"],
        "scene_debug": scene_debug,
        "resolved_outcome_deltas": resolved_deltas,
        "issue_turn_classes": issue_classes,
        "consequence_delta": consequence_delta,
        "dominant_issue_ids_before": dominant_before,
        "dominant_issue_ids_after": list(state.get("dominant_issue_ids", [])),
        "issue_identity_notes": alias_notes,
    }
    logger.info(
        "[progression_pressure] turn=%s scene_class=%s scene_debt=%s->%s tier=%s dominant=%s",
        turn_index,
        scene_class,
        scene_before,
        scene_after,
        state["scene_instability_tier"],
        state.get("dominant_issue_ids", []),
    )
    return state


def tier_for_scene_debt(debt: int) -> Tier:
    debt = int(debt or 0)
    if debt <= 1:
        return "stable"
    if debt <= 3:
        return "unstable"
    if debt <= 6:
        return "escalating"
    return "forcing"


def tier_for_issue_debt(debt: int) -> Tier:
    debt = int(debt or 0)
    if debt <= 1:
        return "stable"
    if debt <= 3:
        return "unstable"
    if debt <= 5:
        return "escalating"
    return "forcing"


def build_director_progression_pressure_payload(
    *,
    orchestration_state: dict[str, Any],
    active_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    state = get_cached_progression_pressure(orchestration_state) or {}
    issue_debt = state.get("issue_progression_debt", {})
    issue_tiers = state.get("issue_instability_tiers", {})
    pressured_issues: list[dict[str, Any]] = []
    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        issue_id = str(issue.get("issue_id", "") or "").strip()
        if not issue_id:
            continue
        pressured_issues.append(
            {
                "issue_id": issue_id,
                "status": str(issue.get("status", "") or ""),
                "description": str(issue.get("description", "") or ""),
                "progression_debt": int(issue_debt.get(issue_id, 0) or 0),
                "instability_tier": str(issue_tiers.get(issue_id, "stable") or "stable"),
                "required_next_step": str(issue.get("required_next_step", "") or ""),
            }
        )
    pressured_issues.sort(
        key=lambda item: (
            -int(item.get("progression_debt", 0) or 0),
            str(item.get("issue_id", "") or ""),
        )
    )
    return {
        "scene_progression_debt": int(state.get("scene_progression_debt", 0) or 0),
        "scene_instability_tier": str(
            state.get("scene_instability_tier", "stable") or "stable"
        ),
        "dominant_issue_ids": [
            str(item)
            for item in state.get("dominant_issue_ids", [])
            if str(item or "").strip()
        ],
        "active_issue_pressure": pressured_issues[:4],
        "last_turn": {
            "scene_turn_class": (
                state.get("last_turn", {}) or {}
            ).get("scene_turn_class", ""),
            "turn_index": (state.get("last_turn", {}) or {}).get("turn_index"),
        },
    }


def build_director_progression_pressure_prefix(orchestration_state: dict[str, Any]) -> str:
    state = get_cached_progression_pressure(orchestration_state) or {}
    tier = str(state.get("scene_instability_tier", "stable") or "stable")
    if tier not in {"escalating", "forcing"}:
        return ""
    debt = int(state.get("scene_progression_debt", 0) or 0)
    dominant = [
        str(item)
        for item in state.get("dominant_issue_ids", [])
        if str(item or "").strip()
    ]
    dominant_line = (
        f"- Dominant unresolved pressure ids: {', '.join(dominant)}\n" if dominant else ""
    )
    forcing_line = (
        "- The next beat should produce observable structured change: a resolution, escalation, consequence, or binding decision.\n"
        if tier == "forcing"
        else "- Do not preserve the current equilibrium through reaction alone when a more pressure-bearing move is available.\n"
    )
    return (
        "PROGRESSION PRESSURE (STRUCTURED):\n"
        f"- Scene instability tier: {tier} (debt {debt}).\n"
        f"{dominant_line}"
        f"{forcing_line}\n"
    )


def build_character_progression_pressure_suffix(
    *,
    orchestration_state: dict[str, Any],
    char_name: str,
    active_issues: list[dict[str, Any]],
) -> str:
    state = get_cached_progression_pressure(orchestration_state) or {}
    scene_tier = str(state.get("scene_instability_tier", "stable") or "stable")
    issue_tiers = state.get("issue_instability_tiers", {})
    issue_debt = state.get("issue_progression_debt", {})
    relevant: list[tuple[str, int, str, str]] = []
    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        participants = issue.get("participants", [])
        if not isinstance(participants, list) or char_name not in participants:
            continue
        issue_id = str(issue.get("issue_id", "") or "").strip()
        if not issue_id:
            continue
        relevant.append(
            (
                issue_id,
                int(issue_debt.get(issue_id, 0) or 0),
                str(issue_tiers.get(issue_id, "stable") or "stable"),
                str(issue.get("required_next_step", "") or ""),
            )
        )
    relevant.sort(key=lambda item: (-item[1], item[0]))
    strongest_issue_tier = relevant[0][2] if relevant else "stable"
    if scene_tier in {"stable", "unstable"} and strongest_issue_tier in {"stable", "unstable"}:
        return ""
    lines = [
        "",
        "PROGRESSION PRESSURE (STRUCTURED):",
        f"- Scene instability tier: {scene_tier} (debt {int(state.get('scene_progression_debt', 0) or 0)}).",
    ]
    if relevant:
        issue_id, debt, tier, next_step = relevant[0]
        lines.append(f"- Your highest-pressure issue: {issue_id} ({tier}, debt {debt}).")
        if next_step:
            lines.append(f"- Required next step remains: {next_step}")
    if scene_tier == "forcing" or strongest_issue_tier == "forcing":
        lines.append(
            "- This beat should produce observable structured change, not only continued equilibrium."
        )
    else:
        lines.append(
            "- If you can affect the active pressure, prefer a move that changes a tracked state, consequence, or obligation."
        )
    return "\n".join(lines)


def _snapshot_issue(issue: Any) -> dict[str, Any]:
    status = getattr(issue, "status", "")
    status_value = str(getattr(status, "value", status) or "").strip().lower()
    participants = [
        str(item) for item in getattr(issue, "participants", []) if str(item).strip()
    ]
    out = {
        "issue_id": str(getattr(issue, "issue_id", "") or ""),
        "status": status_value,
        "participants": participants,
        "pressure_kind": str(getattr(issue, "pressure_kind", "") or ""),
        "blocked_what": str(getattr(issue, "blocked_what", "") or ""),
        "required_next_step": str(getattr(issue, "required_next_step", "") or ""),
        "last_change": str(getattr(issue, "last_change", "") or ""),
        "description": str(getattr(issue, "description", "") or ""),
        "last_turn_index": int(getattr(issue, "last_turn_index", 0) or 0),
    }
    out["fingerprint"] = _issue_fingerprint(out)
    return out


def _snapshot_outcome(outcome: Any) -> dict[str, Any]:
    value = dict(getattr(outcome, "value", {}) or {})
    return {
        "outcome_id": str(getattr(outcome, "outcome_id", "") or ""),
        "status": str(getattr(outcome, "status", "") or ""),
        "category": str(getattr(outcome, "category", "") or ""),
        "key": str(getattr(outcome, "key", "") or ""),
        "subject_id": str(getattr(outcome, "subject_id", "") or ""),
        "value": value,
        "source_issue_id": getattr(outcome, "source_issue_id", None),
        "supersedes_outcome_id": getattr(outcome, "supersedes_outcome_id", None),
        "created_turn_index": int(getattr(outcome, "created_turn_index", 0) or 0),
        "revoked_turn_index": int(getattr(outcome, "revoked_turn_index", 0) or 0),
    }


def _snapshot_scene_core(scene_state: Any) -> dict[str, Any]:
    if scene_state is None:
        return {}
    if hasattr(scene_state, "to_dict"):
        scene_dict = scene_state.to_dict()
    elif isinstance(scene_state, dict):
        scene_dict = scene_state
    else:
        scene_dict = {}
    return {
        "scene_phase": str(scene_dict.get("phase", scene_dict.get("scene_phase", "")) or ""),
        "location": str(scene_dict.get("location", "") or ""),
        "present_characters": sorted(
            str(item)
            for item in scene_dict.get("present_characters", [])
            if str(item or "").strip()
        ),
        "offstage_characters": sorted(
            str(item)
            for item in scene_dict.get("offstage_characters", [])
            if str(item or "").strip()
        ),
    }


def _issue_fingerprint(issue: dict[str, Any]) -> str:
    participants = ",".join(sorted(str(item) for item in issue.get("participants", [])))
    pressure = str(issue.get("pressure_kind", "") or "").strip().lower()
    blocked = str(issue.get("blocked_what", "") or "").strip().lower()
    return f"{pressure}|{blocked}|{participants}"


def _collect_resolved_outcome_deltas(
    *,
    before_outcomes: dict[str, dict[str, Any]],
    after_outcomes: dict[str, dict[str, Any]],
    turn_index: int,
) -> list[dict[str, Any]]:
    _ = before_outcomes
    deltas: list[dict[str, Any]] = []
    for outcome in after_outcomes.values():
        created_turn = int(outcome.get("created_turn_index", 0) or 0)
        revoked_turn = int(outcome.get("revoked_turn_index", 0) or 0)
        status = str(outcome.get("status", "") or "")
        if created_turn == turn_index and status == "active":
            deltas.append(
                {
                    "kind": (
                        "superseded"
                        if outcome.get("supersedes_outcome_id")
                        else "promoted"
                    ),
                    "outcome_id": str(outcome.get("outcome_id", "") or ""),
                    "category": str(outcome.get("category", "") or ""),
                    "key": str(outcome.get("key", "") or ""),
                    "subject_id": str(outcome.get("subject_id", "") or ""),
                    "source_issue_id": (
                        str(outcome.get("source_issue_id"))
                        if outcome.get("source_issue_id") is not None
                        and str(outcome.get("source_issue_id")).strip()
                        else None
                    ),
                }
            )
        elif revoked_turn == turn_index and status == "revoked":
            deltas.append(
                {
                    "kind": "revoked",
                    "outcome_id": str(outcome.get("outcome_id", "") or ""),
                    "category": str(outcome.get("category", "") or ""),
                    "key": str(outcome.get("key", "") or ""),
                    "subject_id": str(outcome.get("subject_id", "") or ""),
                    "source_issue_id": (
                        str(outcome.get("source_issue_id"))
                        if outcome.get("source_issue_id") is not None
                        and str(outcome.get("source_issue_id")).strip()
                        else None
                    ),
                }
            )
    return deltas


def _preserve_issue_identity_continuity(
    *,
    state: dict[str, Any],
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
) -> list[str]:
    debt_map = state.setdefault("issue_progression_debt", {})
    tier_map = state.setdefault("issue_instability_tiers", {})
    aliases = state.setdefault("issue_identity_aliases", {})
    fingerprints = state.setdefault("tracked_issue_fingerprints", {})
    notes: list[str] = []
    before_ids = set(before_issues.keys())
    after_ids = set(after_issues.keys())
    disappeared = before_ids - after_ids
    appeared = after_ids - before_ids
    available_old: dict[str, str] = {}
    for old_id in disappeared:
        fingerprint = str(before_issues.get(old_id, {}).get("fingerprint", "") or "")
        if not fingerprint:
            continue
        if old_id in aliases.values():
            continue
        available_old[fingerprint] = old_id

    for new_id in appeared:
        snap = after_issues.get(new_id, {})
        status = str(snap.get("status", "") or "")
        if not _is_tracked_issue_status(status):
            continue
        fingerprint = str(snap.get("fingerprint", "") or "")
        old_id = available_old.get(fingerprint)
        if not old_id or old_id == new_id:
            continue
        if new_id not in debt_map and old_id in debt_map:
            debt_map[new_id] = int(debt_map.get(old_id, 0) or 0)
        if new_id not in tier_map and old_id in tier_map:
            tier_map[new_id] = str(tier_map.get(old_id, "stable") or "stable")
        aliases[new_id] = old_id
        fingerprints[new_id] = fingerprint
        note = (
            f"Possible issue identity continuation: transferred progression debt "
            f"from {old_id} to {new_id} using exact structured fingerprint."
        )
        notes.append(note)
        logger.warning("[progression_pressure] %s", note)
    return notes


def _classify_issues(
    *,
    state: dict[str, Any],
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
    resolved_deltas: list[dict[str, Any]],
    turn_index: int,
) -> dict[str, dict[str, Any]]:
    resolved_issue_ids = {
        str(item.get("source_issue_id"))
        for item in resolved_deltas
        if item.get("source_issue_id")
    }
    relevant_issue_ids = set()
    for issue_id, snap in before_issues.items():
        if _is_relevant_issue_status(str(snap.get("status", "") or "")):
            relevant_issue_ids.add(issue_id)
    for issue_id, snap in after_issues.items():
        status = str(snap.get("status", "") or "")
        if _is_relevant_issue_status(status):
            relevant_issue_ids.add(issue_id)
        if int(snap.get("last_turn_index", 0) or 0) == turn_index:
            relevant_issue_ids.add(issue_id)
    relevant_issue_ids.update(resolved_issue_ids)

    out: dict[str, dict[str, Any]] = {}
    for issue_id in sorted(relevant_issue_ids):
        before_snap = before_issues.get(issue_id)
        after_snap = after_issues.get(issue_id)
        status_after = str(
            (after_snap or before_snap or {}).get("status", "") or ""
        ).strip().lower()
        updated_this_turn = bool(after_snap) and int(
            after_snap.get("last_turn_index", 0) or 0
        ) == turn_index
        materially_resolved = issue_id in resolved_issue_ids or status_after == "resolved"
        if materially_resolved:
            turn_class: TurnClass = "material_progression"
        elif status_after == "stalled":
            turn_class = "explicit_stagnation"
        elif _issue_structurally_changed(before_snap, after_snap) or updated_this_turn:
            turn_class = "partial_progression"
        else:
            turn_class = "non_progression"
        out[issue_id] = {
            "issue_id": issue_id,
            "turn_class": turn_class,
            "status_before": str((before_snap or {}).get("status", "") or ""),
            "status_after": status_after,
            "updated_this_turn": updated_this_turn,
            "participants": (
                (after_snap or before_snap or {}).get("participants", []) or []
            ),
            "pressure_kind": str(
                (after_snap or before_snap or {}).get("pressure_kind", "") or ""
            ),
            "description": str(
                (after_snap or before_snap or {}).get("description", "") or ""
            ),
            "required_next_step": str(
                (after_snap or before_snap or {}).get("required_next_step", "") or ""
            ),
        }
    return out


def _classify_scene_turn(
    *,
    state: dict[str, Any],
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
    before_active_issue_ids: list[str],
    after_active_issue_ids: list[str],
    before_scene_core: dict[str, Any],
    after_scene_core: dict[str, Any],
    issue_classes: dict[str, dict[str, Any]],
    resolved_deltas: list[dict[str, Any]],
    turn_meta: dict[str, Any],
    dominant_before: list[str],
) -> tuple[TurnClass, dict[str, Any]]:
    active_or_dominant = set(before_active_issue_ids) | set(after_active_issue_ids) | set(
        dominant_before
    )
    reset_focus_issue_ids = (
        set(dominant_before)
        if dominant_before
        else set(before_active_issue_ids) | set(after_active_issue_ids)
    )
    core_scene_state_changed = any(
        before_scene_core.get(field) != after_scene_core.get(field)
        for field in _SCENE_CORE_FIELDS
    )
    material_issue_ids = {
        issue_id
        for issue_id, info in issue_classes.items()
        if str(info.get("turn_class", "") or "") == "material_progression"
    }
    partial_issue_ids = {
        issue_id
        for issue_id, info in issue_classes.items()
        if str(info.get("turn_class", "") or "") == "partial_progression"
    }
    explicit_issue_ids = {
        issue_id
        for issue_id, info in issue_classes.items()
        if str(info.get("turn_class", "") or "") == "explicit_stagnation"
    }
    consequence_info = _classify_consequence_delta(turn_meta=turn_meta)
    consequence_class = str(consequence_info.get("turn_class", "") or "")
    consequence_material = consequence_class == "material_progression"
    consequence_partial = consequence_class == "partial_progression"
    material_touches_pressure = bool(material_issue_ids.intersection(reset_focus_issue_ids))
    material_multi_issue = len(material_issue_ids) >= 2
    scene_reset = bool(
        material_touches_pressure or material_multi_issue or core_scene_state_changed
    )
    focus_issue_ids = active_or_dominant
    focus_partial = bool(partial_issue_ids.intersection(focus_issue_ids))
    focus_explicit = bool(explicit_issue_ids.intersection(focus_issue_ids))

    if scene_reset:
        turn_class: TurnClass = "material_progression"
    elif material_issue_ids or consequence_material:
        turn_class = "partial_progression"
    elif focus_partial or consequence_partial:
        turn_class = "partial_progression"
    elif focus_explicit or explicit_issue_ids:
        turn_class = "explicit_stagnation"
    else:
        turn_class = "non_progression"

    return turn_class, {
        "scene_reset": scene_reset,
        "core_scene_state_changed": core_scene_state_changed,
        "material_issue_ids": sorted(material_issue_ids),
        "partial_issue_ids": sorted(partial_issue_ids),
        "explicit_issue_ids": sorted(explicit_issue_ids),
        "dominant_issue_ids_before": list(dominant_before),
        "active_or_dominant_issue_ids": sorted(active_or_dominant),
        "reset_focus_issue_ids": sorted(reset_focus_issue_ids),
        "resolved_outcome_issue_ids": sorted(
            str(item.get("source_issue_id"))
            for item in resolved_deltas
            if item.get("source_issue_id")
        ),
        "consequence_turn_class": consequence_class,
        "consequence_tags": list(consequence_info.get("tags", [])),
    }


def _classify_consequence_delta(*, turn_meta: dict[str, Any]) -> dict[str, Any]:
    tags = sorted(
        {
            str(item).strip().lower()
            for item in turn_meta.get("tags", [])
            if str(item or "").strip()
        }
    )
    state_changes = [
        str(item) for item in turn_meta.get("state_changes", []) if str(item or "").strip()
    ]
    actionable_implications = [
        str(item)
        for item in turn_meta.get("actionable_implications", [])
        if str(item or "").strip()
    ]
    if not tags and not state_changes and not actionable_implications:
        return {
            "turn_class": "non_progression",
            "tags": [],
            "state_changes": [],
            "actionable_implications": [],
        }
    tag_set = set(tags)
    turn_class: TurnClass = (
        "material_progression"
        if bool(tag_set.intersection(_MATERIAL_CONSEQUENCE_TAGS))
        else "partial_progression"
    )
    return {
        "turn_class": turn_class,
        "tags": tags,
        "state_changes": state_changes,
        "actionable_implications": actionable_implications,
    }


def _issue_structurally_changed(
    before_snap: dict[str, Any] | None, after_snap: dict[str, Any] | None
) -> bool:
    if before_snap is None and after_snap is not None:
        return True
    if before_snap is None or after_snap is None:
        return False
    for key in (
        "status",
        "pressure_kind",
        "blocked_what",
        "required_next_step",
        "last_change",
        "description",
    ):
        if str(before_snap.get(key, "") or "") != str(after_snap.get(key, "") or ""):
            return True
    before_participants = sorted(
        str(item) for item in before_snap.get("participants", []) if str(item).strip()
    )
    after_participants = sorted(
        str(item) for item in after_snap.get("participants", []) if str(item).strip()
    )
    return before_participants != after_participants


def _dominant_issue_ids(
    *,
    debt_map: dict[str, Any],
    issue_ids: list[str],
    issues: dict[str, dict[str, Any]],
) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for issue_id in issue_ids:
        snap = issues.get(issue_id, {})
        status = str(snap.get("status", "") or "")
        if not _is_relevant_issue_status(status):
            continue
        debt = int(debt_map.get(issue_id, 0) or 0)
        candidates.append((debt, issue_id))
    if not candidates:
        return []
    max_debt = max(item[0] for item in candidates)
    if max_debt <= 0:
        return []
    return sorted(issue_id for debt, issue_id in candidates if debt == max_debt)


def _apply_debt_delta(before: int, turn_class: str) -> int:
    before = max(0, min(_MAX_DEBT, int(before or 0)))
    if turn_class == "material_progression":
        return 0
    if turn_class == "explicit_stagnation":
        return min(_MAX_DEBT, before + 2)
    if turn_class == "non_progression":
        return min(_MAX_DEBT, before + 1)
    return before


def _is_actionable_status(status: str) -> bool:
    return str(status or "").strip().lower() in {"active", "escalating"}


def _is_relevant_issue_status(status: str) -> bool:
    return str(status or "").strip().lower() in _RELEVANT_ISSUE_STATUSES


def _is_tracked_issue_status(status: str) -> bool:
    return str(status or "").strip().lower() in _TRACKED_ISSUE_STATUSES
