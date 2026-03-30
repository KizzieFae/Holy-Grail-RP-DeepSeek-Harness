"""Deterministic audit-side verification for progression pressure behavior.

This module verifies progression classification and debt behavior from structured
audit artifacts. It intentionally does not rely on the runtime classifier.
"""

from __future__ import annotations

from typing import Any, Literal

TurnClass = Literal[
    "material_progression",
    "partial_progression",
    "non_progression",
    "explicit_stagnation",
]

_MAX_DEBT = 10
_RELEVANT_ISSUE_STATUSES = frozenset({"active", "escalating", "stalled"})
_TRACKED_ISSUE_STATUSES = frozenset({"active", "escalating", "stalled", "dormant"})
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


def build_progression_analysis(turns: list[dict[str, Any]]) -> dict[str, Any]:
    ordered_turns = sorted(
        [dict(turn) for turn in turns if isinstance(turn, dict)],
        key=lambda item: (
            int(item.get("round", 0) or 0),
            int(item.get("turn", 0) or 0),
        ),
    )
    expected_scene_debt = 0
    expected_issue_debt: dict[str, int] = {}
    previous_turn: dict[str, Any] | None = None
    previous_issue_map: dict[str, dict[str, Any]] = {}
    previous_scene_core: dict[str, Any] = {}
    previous_observed_issue_debt: dict[str, int] = {}
    previous_observed_scene_debt = 0
    previous_observed_scene_tier = "stable"
    previous_observed_dominant_issue_ids: list[str] = []
    plateau_streak = 0
    out_turns: list[dict[str, Any]] = []

    total_mismatches = 0
    reset_errors = 0
    fragmentation_events = 0
    false_progression_events = 0
    plateau_counts = {
        "plateau_correctly_pressured": 0,
        "plateau_under_pressured": 0,
        "plateau_incorrectly_reset": 0,
    }

    for turn in ordered_turns:
        current_turn_index = _turn_index(turn)
        observed = _observed_progression(turn)
        before_issue_map = previous_issue_map
        after_issue_map = _issue_map_after(turn)
        scene_core_after = _scene_core_after(turn)
        resolved_deltas = _resolved_outcome_deltas(turn)

        identity_events = _audit_issue_identity_continuity(
            before_issues=before_issue_map,
            after_issues=after_issue_map,
            expected_issue_debt=expected_issue_debt,
            observed_issue_debt=observed.get("issue_progression_debt", {}),
        )
        fragmentation_events += sum(
            1
            for event in identity_events
            if event.get("classification") == "fragmentation"
        )

        issue_analysis = _classify_issue_turns(
            before_issues=before_issue_map,
            after_issues=after_issue_map,
            resolved_deltas=resolved_deltas,
            current_turn_index=current_turn_index,
            turn=turn,
            observed_issue_turn_classes=observed.get("issue_turn_classes", {}),
            expected_issue_debt=expected_issue_debt,
            observed_issue_debt=observed.get("issue_progression_debt", {}),
        )

        dominant_before = (
            list(previous_observed_dominant_issue_ids)
            or _highest_observed_issue_ids(previous_observed_issue_debt)
            or _dominant_issue_ids(
                debt_map=expected_issue_debt,
                issue_map=before_issue_map,
            )
        )
        scene_expected = _classify_scene_turn(
            before_issues=before_issue_map,
            after_issues=after_issue_map,
            before_scene_core=previous_scene_core,
            after_scene_core=scene_core_after,
            issue_analysis=issue_analysis,
            resolved_deltas=resolved_deltas,
            dominant_before=dominant_before,
            turn=turn,
        )

        scene_expected_before = expected_scene_debt
        expected_scene_debt = _apply_debt_delta(expected_scene_debt, scene_expected["turn_class"])
        expected_scene_tier = _scene_tier(expected_scene_debt)
        scene_observed_after = int(observed.get("scene_progression_debt", 0) or 0)
        scene_observed_tier = str(observed.get("scene_instability_tier", "") or "stable")
        scene_match = scene_observed_after == expected_scene_debt

        if not scene_match:
            total_mismatches += 1

        issue_entries: list[dict[str, Any]] = []
        for issue_id in sorted(issue_analysis):
            info = issue_analysis[issue_id]
            before_value = int(expected_issue_debt.get(issue_id, 0) or 0)
            expected_after = _apply_debt_delta(before_value, str(info.get("expected_turn_class", "")))
            expected_issue_debt[issue_id] = expected_after
            observed_after = int(
                (observed.get("issue_progression_debt", {}) or {}).get(issue_id, 0) or 0
            )
            match = observed_after == expected_after
            if not match:
                total_mismatches += 1
            issue_entries.append(
                {
                    **info,
                    "expected_debt_before": before_value,
                    "expected_debt_after": expected_after,
                    "expected_tier_after": _issue_tier(expected_after),
                    "observed_debt_after": observed_after,
                    "observed_tier_after": str(
                        (observed.get("issue_instability_tiers", {}) or {}).get(
                            issue_id, "stable"
                        )
                        or "stable"
                    ),
                    "debt_match": match,
                }
            )

        scene_observed_class = str(observed.get("scene_turn_class", "") or "")
        flags: list[str] = []
        if scene_observed_class == "material_progression" and scene_expected["turn_class"] != "material_progression":
            flags.append("false_progression_credit")
            false_progression_events += 1

        reset_validation = _reset_validation(
            expected_scene_class=scene_expected["turn_class"],
            observed_scene_debt_after=scene_observed_after,
            reset_justification=scene_expected["reset_justification"],
        )
        if reset_validation["classification"] in {"invalid_reset", "missed_reset"}:
            reset_errors += 1
            flags.append(reset_validation["classification"])

        if scene_expected["turn_class"] != "material_progression":
            plateau_streak += 1
        else:
            plateau_streak = 0
        plateau_assessment = _plateau_assessment(
            plateau_streak=plateau_streak,
            previous_observed_scene_debt=previous_observed_scene_debt,
            observed_scene_debt=scene_observed_after,
            previous_observed_scene_tier=previous_observed_scene_tier,
            observed_scene_tier=scene_observed_tier,
            reset_validation=reset_validation["classification"],
        )
        if plateau_assessment != "not_applicable":
            plateau_counts[plateau_assessment] = plateau_counts.get(plateau_assessment, 0) + 1

        pressure_targeting = _pressure_targeting(
            highest_debt_issue_ids=_highest_observed_issue_ids(previous_observed_issue_debt),
            issue_entries=issue_entries,
        )
        if pressure_targeting != "correct_targeting":
            flags.append(pressure_targeting)

        turn_entry = {
            "round": int(turn.get("round", 0) or 0),
            "turn": int(turn.get("turn", 0) or 0),
            "character": str(turn.get("character", "") or ""),
            "scene_classification": {
                "expected": scene_expected["turn_class"],
                "observed": scene_observed_class,
                "classification_match": scene_observed_class == scene_expected["turn_class"],
                "expected_debt_before": scene_expected_before,
                "expected_debt_after": expected_scene_debt,
                "expected_tier_after": expected_scene_tier,
                "observed_debt_after": scene_observed_after,
                "observed_tier_after": scene_observed_tier,
                "debt_match": scene_match,
            },
            "issue_classifications": issue_entries,
            "expected_debt_changes": {
                "scene": _debt_delta_label(scene_expected_before, expected_scene_debt),
                "issues": {
                    item["issue_id"]: _debt_delta_label(
                        item["expected_debt_before"], item["expected_debt_after"]
                    )
                    for item in issue_entries
                },
            },
            "observed_debt_changes": {
                "scene": _debt_delta_label(previous_observed_scene_debt, scene_observed_after),
                "issues": {
                    item["issue_id"]: _debt_delta_label(
                        int(previous_observed_issue_debt.get(item["issue_id"], 0) or 0),
                        item["observed_debt_after"],
                    )
                    for item in issue_entries
                },
            },
            "reset_validation": reset_validation,
            "plateau_assessment": plateau_assessment,
            "pressure_targeting": pressure_targeting,
            "issue_identity_events": identity_events,
            "notable_flags": flags,
            "reset_justification": scene_expected["reset_justification"],
        }
        out_turns.append(turn_entry)

        previous_turn = turn
        previous_issue_map = after_issue_map
        previous_scene_core = scene_core_after
        previous_observed_issue_debt = {
            str(k): int(v or 0)
            for k, v in (observed.get("issue_progression_debt", {}) or {}).items()
            if str(k).strip()
        }
        previous_observed_scene_debt = scene_observed_after
        previous_observed_scene_tier = scene_observed_tier
        previous_observed_dominant_issue_ids = [
            str(item) for item in observed.get("dominant_issue_ids", []) if str(item).strip()
        ]

    return {
        "turns": out_turns,
        "summary": {
            "total_turns_analyzed": len(out_turns),
            "total_mismatches": total_mismatches,
            "reset_errors": reset_errors,
            "fragmentation_events": fragmentation_events,
            "false_progression_events": false_progression_events,
            "plateau_behavior_assessment": plateau_counts,
        },
    }


def _observed_progression(turn: dict[str, Any]) -> dict[str, Any]:
    raw = turn.get("progression_pressure_observed", {})
    if not isinstance(raw, dict):
        return {}
    last_turn = raw.get("last_turn", {})
    issue_turn_classes = {}
    if isinstance(last_turn, dict):
        rtc = last_turn.get("issue_turn_classes", {})
        if isinstance(rtc, dict):
            issue_turn_classes = {
                str(issue_id): str((info or {}).get("turn_class", "") or "")
                for issue_id, info in rtc.items()
                if isinstance(info, dict)
            }
    return {
        "scene_progression_debt": int(raw.get("scene_progression_debt", 0) or 0),
        "scene_instability_tier": str(raw.get("scene_instability_tier", "stable") or "stable"),
        "issue_progression_debt": {
            str(k): int(v or 0)
            for k, v in (raw.get("issue_progression_debt", {}) or {}).items()
            if str(k).strip()
        },
        "issue_instability_tiers": {
            str(k): str(v or "stable")
            for k, v in (raw.get("issue_instability_tiers", {}) or {}).items()
            if str(k).strip()
        },
        "dominant_issue_ids": [
            str(item) for item in raw.get("dominant_issue_ids", []) if str(item).strip()
        ],
        "scene_turn_class": str((last_turn or {}).get("scene_turn_class", "") or ""),
        "issue_turn_classes": issue_turn_classes,
    }


def _turn_index(turn: dict[str, Any]) -> int:
    observed = turn.get("progression_pressure_observed", {})
    if isinstance(observed, dict):
        last_turn = observed.get("last_turn", {})
        if isinstance(last_turn, dict):
            try:
                return int(last_turn.get("turn_index", 0) or 0)
            except (TypeError, ValueError):
                return 0
    issues_after = turn.get("issues_after", [])
    if isinstance(issues_after, list):
        return max(
            (
                int(item.get("last_turn_index", 0) or 0)
                for item in issues_after
                if isinstance(item, dict)
            ),
            default=0,
        )
    return 0


def _issue_map_after(turn: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in turn.get("issues_after", []) or []:
        if not isinstance(item, dict):
            continue
        issue_id = str(item.get("issue_id", "") or "").strip()
        if not issue_id:
            continue
        snap = dict(item)
        snap["fingerprint"] = _issue_fingerprint(snap)
        out[issue_id] = snap
    return out


def _scene_core_after(turn: dict[str, Any]) -> dict[str, Any]:
    raw = turn.get("scene_core_after", {})
    if isinstance(raw, dict) and raw:
        return {
            "scene_phase": str(raw.get("scene_phase", "") or ""),
            "location": str(raw.get("location", "") or ""),
            "present_characters": sorted(
                str(item)
                for item in raw.get("present_characters", [])
                if str(item or "").strip()
            ),
            "offstage_characters": sorted(
                str(item)
                for item in raw.get("offstage_characters", [])
                if str(item or "").strip()
            ),
        }
    return {
        "scene_phase": str(turn.get("scene_phase", "") or ""),
        "location": "",
        "present_characters": sorted(
            str(item)
            for item in turn.get("present_characters_after", [])
            if str(item or "").strip()
        ),
        "offstage_characters": [],
    }


def _issue_fingerprint(issue: dict[str, Any]) -> str:
    participants = ",".join(
        sorted(str(item) for item in issue.get("participants", []) if str(item).strip())
    )
    pressure = str(issue.get("pressure_kind", "") or "").strip().lower()
    blocked = str(issue.get("blocked_what", "") or "").strip().lower()
    return f"{pressure}|{blocked}|{participants}"


def _resolved_outcome_deltas(turn: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    debug = turn.get("resolved_outcome_debug", {})
    if not isinstance(debug, dict):
        return out
    for key, payload in debug.items():
        if not isinstance(payload, dict):
            continue
        decision = str(payload.get("decision", "") or "").strip().lower()
        if decision not in {"promoted", "superseded", "revoked"}:
            continue
        issue_id = str(payload.get("issue_id", "") or "").strip()
        out.append(
            {
                "legacy_key": str(key or ""),
                "decision": decision,
                "issue_id": issue_id or None,
            }
        )
    return out


def _audit_issue_identity_continuity(
    *,
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
    expected_issue_debt: dict[str, int],
    observed_issue_debt: dict[str, int],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    disappeared = set(before_issues) - set(after_issues)
    appeared = set(after_issues) - set(before_issues)
    available_old: dict[str, str] = {}
    for old_id in disappeared:
        available_old[str(before_issues[old_id].get("fingerprint", "") or "")] = old_id
    for new_id in sorted(appeared):
        new_snap = after_issues.get(new_id, {})
        status = str(new_snap.get("status", "") or "").strip().lower()
        if status not in _TRACKED_ISSUE_STATUSES:
            continue
        fingerprint = str(new_snap.get("fingerprint", "") or "")
        old_id = available_old.get(fingerprint)
        if not old_id:
            continue
        old_debt = int(expected_issue_debt.get(old_id, 0) or 0)
        observed_new = int(observed_issue_debt.get(new_id, 0) or 0)
        if observed_new == old_debt:
            classification = "correct_continuity"
        else:
            classification = "fragmentation"
        expected_issue_debt[new_id] = old_debt
        events.append(
            {
                "from_issue_id": old_id,
                "to_issue_id": new_id,
                "classification": classification,
                "reason": "exact_structured_fingerprint_match",
            }
        )
    return events


def _classify_issue_turns(
    *,
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
    resolved_deltas: list[dict[str, Any]],
    current_turn_index: int,
    turn: dict[str, Any],
    observed_issue_turn_classes: dict[str, str],
    expected_issue_debt: dict[str, int],
    observed_issue_debt: dict[str, int],
) -> dict[str, dict[str, Any]]:
    updated_issue_ids = {
        str(item.get("issue_id", "") or "").strip()
        for item in turn.get("issue_updates", []) or []
        if isinstance(item, dict) and str(item.get("issue_id", "") or "").strip()
    }
    relevant_ids = set()
    for issue_id, snap in before_issues.items():
        if _is_relevant_status(str(snap.get("status", "") or "")):
            relevant_ids.add(issue_id)
    for issue_id, snap in after_issues.items():
        status = str(snap.get("status", "") or "")
        if _is_relevant_status(status):
            relevant_ids.add(issue_id)
        if issue_id in updated_issue_ids:
            relevant_ids.add(issue_id)
    for delta in resolved_deltas:
        if delta.get("issue_id"):
            relevant_ids.add(str(delta["issue_id"]))
    relevant_ids.update(observed_issue_debt.keys())
    relevant_ids.update(expected_issue_debt.keys())

    out: dict[str, dict[str, Any]] = {}
    resolved_issue_ids = {
        str(delta.get("issue_id"))
        for delta in resolved_deltas
        if delta.get("issue_id")
    }
    for issue_id in sorted(relevant_ids):
        before_snap = before_issues.get(issue_id)
        after_snap = after_issues.get(issue_id)
        status_after = str((after_snap or before_snap or {}).get("status", "") or "").strip().lower()
        updated_this_turn = issue_id in updated_issue_ids
        if issue_id in resolved_issue_ids or status_after == "resolved":
            expected_class: TurnClass = "material_progression"
        elif status_after == "stalled":
            expected_class = "explicit_stagnation"
        elif _issue_structurally_changed(before_snap, after_snap) or updated_this_turn:
            expected_class = "partial_progression"
        else:
            expected_class = "non_progression"
        out[issue_id] = {
            "issue_id": issue_id,
            "expected_turn_class": expected_class,
            "observed_turn_class": str(observed_issue_turn_classes.get(issue_id, "") or ""),
            "classification_match": str(observed_issue_turn_classes.get(issue_id, "") or "") == expected_class,
            "status_before": str((before_snap or {}).get("status", "") or ""),
            "status_after": status_after,
            "participants": (after_snap or before_snap or {}).get("participants", []) or [],
            "required_next_step": str(
                (after_snap or before_snap or {}).get("required_next_step", "") or ""
            ),
        }
    return out


def _classify_scene_turn(
    *,
    before_issues: dict[str, dict[str, Any]],
    after_issues: dict[str, dict[str, Any]],
    before_scene_core: dict[str, Any],
    after_scene_core: dict[str, Any],
    issue_analysis: dict[str, dict[str, Any]],
    resolved_deltas: list[dict[str, Any]],
    dominant_before: list[str],
    turn: dict[str, Any],
) -> dict[str, Any]:
    active_before = {
        issue_id
        for issue_id, snap in before_issues.items()
        if _is_actionable_status(str(snap.get("status", "") or ""))
    }
    active_after = {
        issue_id
        for issue_id, snap in after_issues.items()
        if _is_actionable_status(str(snap.get("status", "") or ""))
    }
    material_issue_ids = {
        issue_id
        for issue_id, info in issue_analysis.items()
        if str(info.get("expected_turn_class", "") or "") == "material_progression"
    }
    partial_issue_ids = {
        issue_id
        for issue_id, info in issue_analysis.items()
        if str(info.get("expected_turn_class", "") or "") == "partial_progression"
    }
    explicit_issue_ids = {
        issue_id
        for issue_id, info in issue_analysis.items()
        if str(info.get("expected_turn_class", "") or "") == "explicit_stagnation"
    }
    reset_focus = set(dominant_before) if dominant_before else active_before | active_after
    core_scene_state_changed = bool(before_scene_core) and before_scene_core != after_scene_core
    material_touches_pressure = bool(material_issue_ids.intersection(reset_focus))
    material_multi_issue = len(material_issue_ids) >= 2
    consequence = _classify_consequence_delta(turn)
    scene_reset = bool(material_touches_pressure or material_multi_issue or core_scene_state_changed)
    if scene_reset:
        turn_class: TurnClass = "material_progression"
    elif material_issue_ids or consequence["turn_class"] == "material_progression":
        turn_class = "partial_progression"
    elif partial_issue_ids.intersection(active_before | active_after | set(dominant_before)) or consequence["turn_class"] == "partial_progression":
        turn_class = "partial_progression"
    elif explicit_issue_ids.intersection(active_before | active_after | set(dominant_before)) or explicit_issue_ids:
        turn_class = "explicit_stagnation"
    else:
        turn_class = "non_progression"
    return {
        "turn_class": turn_class,
        "reset_justification": {
            "scene_reset_expected": scene_reset,
            "material_issue_ids": sorted(material_issue_ids),
            "dominant_issue_ids_before": list(dominant_before),
            "reset_focus_issue_ids": sorted(reset_focus),
            "core_scene_state_changed": core_scene_state_changed,
            "resolved_outcome_issue_ids": sorted(
                str(item.get("issue_id"))
                for item in resolved_deltas
                if item.get("issue_id")
            ),
        },
    }


def _classify_consequence_delta(turn: dict[str, Any]) -> dict[str, Any]:
    tags = {
        str(item).strip().lower()
        for item in turn.get("continuity_tags", []) or []
        if str(item or "").strip()
    }
    state_changes = [
        str(item) for item in turn.get("state_changes", []) if str(item or "").strip()
    ]
    actionable = [
        str(item)
        for item in turn.get("actionable_implications", [])
        if str(item or "").strip()
    ]
    consequences = [
        str(item)
        for item in turn.get("continuity_consequences", [])
        if str(item or "").strip()
    ]
    if not tags and not state_changes and not actionable and not consequences:
        return {"turn_class": "non_progression"}
    if tags.intersection(_MATERIAL_CONSEQUENCE_TAGS):
        return {"turn_class": "material_progression"}
    return {"turn_class": "partial_progression"}


def _issue_structurally_changed(
    before_snap: dict[str, Any] | None, after_snap: dict[str, Any] | None
) -> bool:
    if before_snap is None and after_snap is not None:
        return False
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


def _apply_debt_delta(before: int, turn_class: str) -> int:
    before = max(0, min(_MAX_DEBT, int(before or 0)))
    if turn_class == "material_progression":
        return 0
    if turn_class == "explicit_stagnation":
        return min(_MAX_DEBT, before + 2)
    if turn_class == "non_progression":
        return min(_MAX_DEBT, before + 1)
    return before


def _scene_tier(debt: int) -> str:
    if debt <= 1:
        return "stable"
    if debt <= 3:
        return "unstable"
    if debt <= 6:
        return "escalating"
    return "forcing"


def _issue_tier(debt: int) -> str:
    if debt <= 1:
        return "stable"
    if debt <= 3:
        return "unstable"
    if debt <= 5:
        return "escalating"
    return "forcing"


def _is_actionable_status(status: str) -> bool:
    return str(status or "").strip().lower() in {"active", "escalating"}


def _is_relevant_status(status: str) -> bool:
    return str(status or "").strip().lower() in _RELEVANT_ISSUE_STATUSES


def _dominant_issue_ids(
    *, debt_map: dict[str, int], issue_map: dict[str, dict[str, Any]]
) -> list[str]:
    candidates = [
        (int(debt_map.get(issue_id, 0) or 0), issue_id)
        for issue_id, snap in issue_map.items()
        if _is_relevant_status(str(snap.get("status", "") or ""))
    ]
    if not candidates:
        return []
    max_debt = max(item[0] for item in candidates)
    if max_debt <= 0:
        return []
    return sorted(issue_id for debt, issue_id in candidates if debt == max_debt)


def _reset_validation(
    *,
    expected_scene_class: str,
    observed_scene_debt_after: int,
    reset_justification: dict[str, Any],
) -> dict[str, Any]:
    if expected_scene_class == "material_progression":
        if int(observed_scene_debt_after or 0) == 0:
            return {
                "classification": "valid_reset",
                "justification": reset_justification,
            }
        return {
            "classification": "missed_reset",
            "justification": reset_justification,
        }
    if int(observed_scene_debt_after or 0) == 0:
        return {
            "classification": "invalid_reset",
            "justification": reset_justification,
        }
    return {
        "classification": "no_reset_expected",
        "justification": reset_justification,
    }


def _plateau_assessment(
    *,
    plateau_streak: int,
    previous_observed_scene_debt: int,
    observed_scene_debt: int,
    previous_observed_scene_tier: str,
    observed_scene_tier: str,
    reset_validation: str,
) -> str:
    if plateau_streak < 2:
        return "not_applicable"
    if reset_validation == "invalid_reset":
        return "plateau_incorrectly_reset"
    if observed_scene_debt > previous_observed_scene_debt or _tier_rank(observed_scene_tier) > _tier_rank(previous_observed_scene_tier):
        return "plateau_correctly_pressured"
    return "plateau_under_pressured"


def _tier_rank(tier: str) -> int:
    clean = str(tier or "").strip().lower()
    if clean == "forcing":
        return 3
    if clean == "escalating":
        return 2
    if clean == "unstable":
        return 1
    return 0


def _highest_observed_issue_ids(observed_issue_debt: dict[str, int]) -> list[str]:
    if not observed_issue_debt:
        return []
    max_debt = max(int(value or 0) for value in observed_issue_debt.values())
    if max_debt <= 0:
        return []
    return sorted(
        issue_id
        for issue_id, value in observed_issue_debt.items()
        if int(value or 0) == max_debt
    )


def _pressure_targeting(
    *, highest_debt_issue_ids: list[str], issue_entries: list[dict[str, Any]]
) -> str:
    if not highest_debt_issue_ids:
        return "unclear_targeting"
    focused_high = {
        item["issue_id"]
        for item in issue_entries
        if item["issue_id"] in highest_debt_issue_ids
        and item["expected_turn_class"] in {"material_progression", "partial_progression"}
    }
    if focused_high:
        return "correct_targeting"
    focused_other = {
        item["issue_id"]
        for item in issue_entries
        if item["issue_id"] not in highest_debt_issue_ids
        and item["expected_turn_class"] in {"material_progression", "partial_progression"}
    }
    if focused_other:
        return "drift"
    return "unclear_targeting"


def _debt_delta_label(before: int, after: int) -> str:
    if int(after or 0) == 0 and int(before or 0) > 0:
        return "reset"
    diff = int(after or 0) - int(before or 0)
    if diff > 0:
        return f"+{diff}"
    if diff < 0:
        return str(diff)
    return "0"
