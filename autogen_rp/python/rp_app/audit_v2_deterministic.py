"""Audit V2 deterministic envelopes: dimension-scoped checks (metrics only for policy)."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from character_audits_v1 import (
    _ca4_repetition,
    _ca7_pressure_move,
)
from narrator_audits_v1 import (
    SINGLE_ACTOR_SCOPE_HEURISTIC_DEPRECATION_TRACKER_ISSUE,
    build_narrator_output_audit_v1,
    build_prose_dialogue_audit_v1,
)

from audit_v2_escalation_policy import (
    CHECK_TO_DIMENSION,
    compute_escalation_for_layer,
)
from progression_enforcement import (
    _q2_issue_material_change,
    _q4_bounded_scene_state_updates,
    _normalized_consequence_list,
)

_QUOTED_SEGMENT_RE = re.compile(r'"[^"]+"')

OPTIONAL_DETERMINISTIC_BLOCK_KEYS: frozenset[str] = frozenset(
    {
        "intra_move_summary",
        "scope_proxy_context",
        "attribution_ambiguity_hint",
        "ca7_surface",
    }
)

MASKED_PROGRESSION_CHECK_ID = "char_masked_progression_strict"
MASKED_PROGRESSION_DIMENSION_ID = CHECK_TO_DIMENSION[MASKED_PROGRESSION_CHECK_ID]


def _continuity_event_dict_for_turn(
    continuity_manager: Any, turn_index: int, next_actor: str
) -> dict[str, Any]:
    public_events = list(getattr(continuity_manager, "public_events", []) or [])
    if not public_events:
        return {}
    event = public_events[-1]
    if int(getattr(event, "turn_index", 0) or 0) != turn_index:
        return {}
    participants = [
        str(p).strip() for p in (getattr(event, "participants", []) or []) if str(p).strip()
    ]
    if next_actor not in participants:
        return {}
    return dict(event.to_dict()) if hasattr(event, "to_dict") else {}


def _continuity_state_changes_non_empty(continuity_event: Mapping[str, Any]) -> bool:
    sc = continuity_event.get("state_changes")
    if not isinstance(sc, list):
        return False
    return any(str(x or "").strip() for x in sc)


def _structured_intent_for_masked_progression(move: Mapping[str, Any]) -> bool:
    """Non-dialogue-only structured intent: motivation goal/tactic, action, or Q4 keys."""
    if _q4_bounded_scene_state_updates(dict(move)):
        return True
    mot = move.get("motivation")
    if isinstance(mot, dict):
        g = str(mot.get("goal", "") or "").strip()
        t = str(mot.get("tactic", "") or "").strip()
        if g or t:
            return True
    if str(move.get("action", "") or "").strip():
        return True
    return False


def build_masked_progression_strict_payload(
    *,
    next_actor: str,
    continuity_manager: Any | None,
    turn_index: int,
    turn_meta: Mapping[str, Any],
    issues_before: Mapping[str, Any] | None,
    move: Mapping[str, Any],
    turn_execution: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Strict-tier masked progression observability (GitHub #73).

    ``observation`` is ``fired`` | ``clear`` | ``skipped``. Escalation policy always maps
    the scored check to **pass**; this payload is for operators only.
    """
    limitations: list[str] = []
    reasons: list[str] = []
    tex = turn_execution if isinstance(turn_execution, dict) else {}
    attempt_index = int(tex.get("attempt_index", 0) or 0)

    if continuity_manager is None:
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "skipped",
            "limitations": ["continuity_manager_absent"],
            "reasons": [],
            "signals": {},
        }

    if attempt_index != 0:
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "skipped",
            "limitations": ["non_initial_attempt_index"],
            "reasons": [],
            "signals": {"attempt_index": attempt_index},
        }

    if bool(tex.get("progression_retry_triggered")):
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "skipped",
            "limitations": ["progression_retry_path"],
            "reasons": [],
            "signals": {},
        }

    cons = _normalized_consequence_list(dict(turn_meta))
    classifier_lane_empty = len(cons) == 0
    if not classifier_lane_empty:
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "clear",
            "limitations": [],
            "reasons": [],
            "signals": {"classifier_lane_empty": False, "consequence_count": len(cons)},
        }

    structured = _structured_intent_for_masked_progression(move)
    ib = dict(issues_before) if isinstance(issues_before, dict) else {}
    q2 = _q2_issue_material_change(
        continuity_manager=continuity_manager,
        turn_index=turn_index,
        issues_before=ib,
    )
    q4 = _q4_bounded_scene_state_updates(dict(move))
    ev = _continuity_event_dict_for_turn(continuity_manager, turn_index, next_actor)
    mat_state = _continuity_state_changes_non_empty(ev)
    structural_proxy = bool(q2 or q4 or mat_state)

    signals: dict[str, Any] = {
        "classifier_lane_empty": True,
        "structured_intent_present": structured,
        "q2_issue_material_change": q2,
        "q4_allowlisted_scene_state_updates": q4,
        "continuity_event_state_changes_non_empty": mat_state,
        "continuity_event_id": str(ev.get("event_id", "") or "") if ev else "",
    }

    if not structured:
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "clear",
            "limitations": [],
            "reasons": [],
            "signals": signals,
        }

    if not structural_proxy:
        return {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "clear",
            "limitations": [],
            "reasons": [],
            "signals": signals,
        }

    if q2:
        reasons.append("q2_issue_material_change")
    if q4:
        reasons.append("q4_allowlisted_scene_state_updates")
    if mat_state:
        reasons.append("continuity_event_state_changes_non_empty")

    return {
        "schema_version": 1,
        "strict_tier": True,
        "observation": "fired",
        "limitations": limitations,
        "reasons": reasons,
        "signals": signals,
        "interpretation": (
            "Classifier lane empty while continuity/progression proxies advanced "
            "(Q2 and/or Q4 and/or committed state_changes). Observational only — not a "
            "runtime defect."
        ),
    }


def count_quoted_segments(rendered_final: str) -> int:
    """P4: exact count of substrings matching /\"[^\"]+\"/ (ASCII double quotes only)."""
    return len(_QUOTED_SEGMENT_RE.findall(str(rendered_final or "")))


def narrator_other_cast_names_frozenset_from_deterministic(
    deterministic: Mapping[str, Any],
) -> frozenset[str]:
    """Extract nar_scope_proxy names from a narrator V2 deterministic envelope."""
    for c in deterministic.get("checks") or []:
        if not isinstance(c, dict) or c.get("check_id") != "nar_scope_proxy":
            continue
        pl = c.get("payload") if isinstance(c.get("payload"), dict) else {}
        raw = pl.get("other_cast_names_found") or []
        if isinstance(raw, list):
            return frozenset(str(x) for x in raw)
        return frozenset()
    return frozenset()


def build_character_audit_v2_deterministic(
    *,
    move: Mapping[str, Any],
    next_actor: str,
    orchestration_state: Mapping[str, Any],
    continuity_manager: Any | None = None,
    turn_index: int | None = None,
    turn_meta: Mapping[str, Any] | None = None,
    issues_before: Mapping[str, Any] | None = None,
    turn_execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """V2 character deterministic: repetition, declared move fields, masked progression."""
    ca4 = _ca4_repetition(move, next_actor, orchestration_state)
    ca7 = _ca7_pressure_move(move)
    ti = int(turn_index) if turn_index is not None else -1
    if continuity_manager is None or ti < 0 or not isinstance(turn_meta, dict):
        masked_payload: dict[str, Any] = {
            "schema_version": 1,
            "strict_tier": True,
            "observation": "skipped",
            "limitations": ["continuity_context_not_applicable"],
            "reasons": [],
            "signals": {},
        }
    else:
        masked_payload = build_masked_progression_strict_payload(
            next_actor=next_actor,
            continuity_manager=continuity_manager,
            turn_index=ti,
            turn_meta=turn_meta,
            issues_before=issues_before,
            move=move,
            turn_execution=turn_execution,
        )
    checks: list[dict[str, Any]] = [
        {
            "check_id": "char_ca4_repetition",
            "dimension_id": CHECK_TO_DIMENSION["char_ca4_repetition"],
            "payload": dict(ca4),
        },
        {
            "check_id": "char_ca7_declared_fields",
            "dimension_id": CHECK_TO_DIMENSION["char_ca7_declared_fields"],
            "payload": dict(ca7),
        },
        {
            "check_id": MASKED_PROGRESSION_CHECK_ID,
            "dimension_id": MASKED_PROGRESSION_DIMENSION_ID,
            "payload": masked_payload,
        },
    ]
    scored, escalation, layer_extras = compute_escalation_for_layer(
        layer="character_decision", checks=checks
    )
    out: dict[str, Any] = {
        "schema_version": 2,
        "layer": "character_decision",
        "checks": scored,
        "escalation": escalation,
    }
    out.update(layer_extras)
    ca7_surface = _build_ca7_surface_from_scored(scored)
    if ca7_surface is not None:
        out["ca7_surface"] = ca7_surface
    return out


def _build_ca7_surface_from_scored(scored: list[dict[str, Any]]) -> dict[str, Any] | None:
    """P7: surface when fields_present is non-empty; preserve payload list order."""
    for row in scored:
        if row.get("check_id") != "char_ca7_declared_fields":
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        fields = payload.get("fields_present")
        if not isinstance(fields, list) or len(fields) == 0:
            return None
        fields_ordered = list(fields)
        cls = str(payload.get("classification", "") or "")
        hr = (
            f"Declared pressure fields present: {', '.join(str(f) for f in fields_ordered)}; "
            f"classification {cls!r}; check result {row.get('result', '')!r}."
        )
        return {
            "schema_version": 1,
            "active": True,
            "fields_present": fields_ordered,
            "classification": cls,
            "check_result": str(row.get("result", "") or ""),
            "human_readable": hr[:512],
        }
    return None


def build_narrator_audit_v2_deterministic(
    *,
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    rendered_final: str,
    char_names: list[str],
    acting_display_name: str,
    previous_narrator_other_cast_names: frozenset[str] | None = None,
) -> dict[str, Any]:
    v1 = build_narrator_output_audit_v1(
        next_actor=next_actor,
        move=move,
        decision=decision,
        rendered_final=rendered_final,
        char_names=char_names,
        acting_display_name=acting_display_name,
    )
    ch = v1.get("checks") if isinstance(v1.get("checks"), dict) else {}
    action = ch.get("action_coverage_heuristic") if isinstance(ch, dict) else {}
    action = action if isinstance(action, dict) else {}
    env = ch.get("environment_event_heuristic") if isinstance(ch, dict) else {}
    env = env if isinstance(env, dict) else {}
    scope = ch.get("single_actor_scope_heuristic") if isinstance(ch, dict) else {}
    scope = scope if isinstance(scope, dict) else {}

    action_empty = not str(move.get("action", "") or "").strip()
    checks: list[dict[str, Any]] = [
        {
            "check_id": "nar_strict_action_overlap",
            "dimension_id": CHECK_TO_DIMENSION["nar_strict_action_overlap"],
            "payload": {
                "action_token_overlap_ratio": float(
                    action.get("action_token_overlap_ratio", 0.0) or 0.0
                ),
                "action_empty": action_empty,
            },
        },
        {
            "check_id": "nar_v1_action_passes_bar",
            "dimension_id": CHECK_TO_DIMENSION["nar_v1_action_passes_bar"],
            "payload": {"passes_bar": bool(action.get("passes_bar"))},
        },
        {
            "check_id": "nar_environment_cue",
            "dimension_id": CHECK_TO_DIMENSION["nar_environment_cue"],
            "payload": {
                "environment_event_present": bool(
                    env.get("environment_event_present", False)
                ),
                "token_hits_in_render": int(env.get("token_hits_in_render", 0) or 0),
            },
        },
        {
            "check_id": "nar_scope_proxy",
            "dimension_id": CHECK_TO_DIMENSION["nar_scope_proxy"],
            "payload": {
                "passes_bar": bool(scope.get("passes_bar")),
                "other_cast_names_found": list(
                    scope.get("other_cast_names_found", []) or []
                ),
                "status": scope.get("status", "deprecated"),
                "interpretation": scope.get("interpretation", "do_not_use"),
                "reason": scope.get(
                    "reason",
                    (
                        "No evidence of meaningful ownership violations in reviewed corpus; "
                        "high false-positive rate from treating other-cast name mention as failure."
                    ),
                ),
                "tracked_by_issue": scope.get(
                    "tracked_by_issue",
                    SINGLE_ACTOR_SCOPE_HEURISTIC_DEPRECATION_TRACKER_ISSUE,
                ),
            },
        },
    ]
    scored, escalation, _ = compute_escalation_for_layer(
        layer="narrator_output", checks=checks
    )
    scope_names: list[str] = []
    for row in scored:
        if row.get("check_id") == "nar_scope_proxy":
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            raw = pl.get("other_cast_names_found") or []
            if isinstance(raw, list):
                scope_names = [str(x) for x in raw]
            break
    scope_set = frozenset(scope_names)
    same_prev: bool | None
    if previous_narrator_other_cast_names is None:
        same_prev = None
    else:
        same_prev = scope_set == previous_narrator_other_cast_names
    return {
        "schema_version": 2,
        "layer": "narrator_output",
        "checks": scored,
        "escalation": escalation,
        "scope_proxy_context": {
            "schema_version": 1,
            "other_cast_names_count": len(scope_names),
            "other_cast_names_sorted": sorted(scope_names),
            "same_other_cast_set_as_previous_narrator_turn": same_prev,
        },
    }


def build_prose_audit_v2_deterministic(
    *,
    next_actor: str,
    move: dict[str, Any],
    rendered_final: str,
    prior_assistant_content: str | None,
    acting_display_name: str,
) -> dict[str, Any]:
    v1 = build_prose_dialogue_audit_v1(
        next_actor=next_actor,
        move=move,
        rendered_final=rendered_final,
        prior_assistant_content=prior_assistant_content,
        acting_display_name=acting_display_name,
    )
    ch = v1.get("checks") if isinstance(v1.get("checks"), dict) else {}
    ch = ch if isinstance(ch, dict) else {}

    def _pl(name: str) -> dict[str, Any]:
        x = ch.get(name)
        return dict(x) if isinstance(x, dict) else {}

    checks: list[dict[str, Any]] = [
        {
            "check_id": "prose_readability",
            "dimension_id": CHECK_TO_DIMENSION["prose_readability"],
            "payload": _pl("readability_proxy"),
        },
        {
            "check_id": "prose_redundancy",
            "dimension_id": CHECK_TO_DIMENSION["prose_redundancy"],
            "payload": _pl("redundancy_vs_prior"),
        },
        {
            "check_id": "prose_dialogue_integration",
            "dimension_id": CHECK_TO_DIMENSION["prose_dialogue_integration"],
            "payload": _pl("dialogue_integration_proxy"),
        },
        {
            "check_id": "prose_attribution",
            "dimension_id": CHECK_TO_DIMENSION["prose_attribution"],
            "payload": _pl("attribution_proxy"),
        },
        {
            "check_id": "prose_tone",
            "dimension_id": CHECK_TO_DIMENSION["prose_tone"],
            "payload": _pl("tone_consistency_local"),
        },
    ]
    scored, escalation, _ = compute_escalation_for_layer(
        layer="prose_dialogue", checks=checks
    )
    hint = _build_attribution_ambiguity_hint(
        scored=scored, rendered_final=rendered_final
    )
    out: dict[str, Any] = {
        "schema_version": 2,
        "layer": "prose_dialogue",
        "checks": scored,
        "escalation": escalation,
        "attribution_ambiguity_hint": hint,
    }
    return out


def _build_attribution_ambiguity_hint(
    *,
    scored: list[dict[str, Any]],
    rendered_final: str,
) -> dict[str, Any]:
    """P4: prose-only; uses scored prose checks + quoted segment count rule."""
    att_pl: dict[str, Any] = {}
    dlg_pl: dict[str, Any] = {}
    for row in scored:
        cid = row.get("check_id")
        pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if cid == "prose_attribution":
            att_pl = dict(pl)
        elif cid == "prose_dialogue_integration":
            dlg_pl = dict(pl)
    att_ok = bool(att_pl.get("passes_bar"))
    dlg_ok = bool(dlg_pl.get("passes_bar"))
    qcount = count_quoted_segments(rendered_final)
    lim = str(att_pl.get("limitations", "") or "")
    if att_ok:
        return {"schema_version": 1, "active": False}
    if dlg_ok and qcount >= 2:
        level = "possible_speaker_ambiguity"
        human_readable = (
            "Attribution heuristic failed while dialogue integration passed and "
            f"two or more double-quoted segments were found (count={qcount}); "
            "possible speaker ambiguity in render."
        )
    else:
        level = "heuristic_limitation"
        human_readable = (
            "Attribution heuristic failed; likely pronoun-only or formatting limitation "
            f"(quoted_segment_count={qcount})."
        )
        if lim:
            human_readable = f"{human_readable} ({lim})"
    return {
        "schema_version": 1,
        "active": True,
        "level": level,
        "human_readable": human_readable[:512],
        "signals": {
            "attribution_passes_bar": att_ok,
            "dialogue_integration_passes_bar": dlg_ok,
            "quoted_segment_count": qcount,
            "limitations_note": lim,
        },
    }


def assemble_audit_v2_layer_block(
    *,
    deterministic: dict[str, Any],
    llm: dict[str, Any] | None,
) -> dict[str, Any]:
    esc = deterministic.get("escalation")
    if not isinstance(esc, dict):
        esc = {"qualified": False, "reasons": [], "dimension_aggregate": {}}
    det_out: dict[str, Any] = {
        "schema_version": deterministic.get("schema_version", 1),
        "layer": deterministic.get("layer", ""),
        "checks": deterministic.get("checks", []),
    }
    for key in OPTIONAL_DETERMINISTIC_BLOCK_KEYS:
        if key in deterministic:
            det_out[key] = deterministic[key]
    return {
        "deterministic": det_out,
        "escalation": {
            "qualified": bool(esc.get("qualified", False)),
            "reasons": list(esc.get("reasons", []) or []),
            "dimension_aggregate": dict(esc.get("dimension_aggregate", {}) or {}),
        },
        "llm": llm,
    }


def format_move_for_llm_closed(move: dict[str, Any]) -> str:
    """Serialize move as JSON for closed-artifact LLM input (character layer)."""
    try:
        return json.dumps(move, ensure_ascii=False, default=str)[:12000]
    except TypeError:
        return str(move)[:12000]


ALLOWED_EXPANSION_POLICY_TEXT = (
    "Allowed narrator expansion ONLY: tone, pacing, staging detail, manner of action. "
    "Novel material facts (new objects, new actions beyond direct mechanical continuation "
    "of the declared action, new state changes, new world facts) are out of scope."
)
