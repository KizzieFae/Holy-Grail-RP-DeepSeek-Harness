"""Heuristic per-turn character decision audits (v1). Pure, non-mutating builders.

Computed post-validation, pre-continuity, pre-narrator. Advisory only; no LLM.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_SCHEMA_VERSION = 2
_EXCERPT = 240
_OPENING_CAP = 300
_DELTA_CAP = 500
_RECENT_MOVES_TAIL = 6
_MAX_ISSUES_DIGEST = 12
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "by",
        "with",
        "her",
        "his",
        "their",
        "she",
        "he",
        "they",
        "it",
        "was",
        "were",
        "is",
        "are",
    }
)


def _excerpt(s: str, cap: int = _EXCERPT) -> str:
    t = str(s or "")
    if len(t) <= cap:
        return t
    return t[:cap] + "…"


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def _meaningful_tokens(text: str) -> list[str]:
    return [w for w in _tokenize_words(text) if w not in _STOPWORDS and len(w) > 1]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def _trim_scene_state_pre(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    phase = raw.get("phase")
    if phase is None:
        phase = raw.get("scene_phase")
    rd = str(raw.get("recent_delta", "") or "")
    od = str(raw.get("opening_description", "") or "")
    out: dict[str, Any] = {
        "location": raw.get("location"),
        "phase": phase,
        "current_tension_level": str(raw.get("current_tension_level", "") or ""),
        "present_characters": list(raw.get("present_characters") or []),
        "active_issue_ids": list(raw.get("active_issue_ids") or []),
        "recent_delta": _excerpt(rd, _DELTA_CAP),
        "opening_description": _excerpt(od, _OPENING_CAP),
        "scene_template_id": raw.get("scene_template_id"),
    }
    return out


def _project_issues_before_json(
    signatures: Mapping[str, Any] | None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not signatures:
        return {"issues": issues, "schema_note": "projected_from_collect_issue_signatures_pre_process_turn"}
    for sid, sig in list(signatures.items())[:_MAX_ISSUES_DIGEST]:
        if not isinstance(sig, tuple) or len(sig) != 4:
            continue
        st, parts, sr, lc = sig
        frozen = parts if isinstance(parts, frozenset) else frozenset()
        issues.append(
            {
                "issue_id": str(sid),
                "status": str(st),
                "participants": sorted(str(p) for p in frozen),
                "status_reason_excerpt": _excerpt(str(sr)),
                "last_change_excerpt": _excerpt(str(lc)),
            }
        )
    return {"issues": issues, "schema_note": "projected_from_collect_issue_signatures_pre_process_turn"}


def _active_issues_digest_from_cm(cm_exec: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    issues = getattr(cm_exec, "issues", None) or {}
    if not isinstance(issues, dict):
        return out
    for iss in list(issues.values())[:_MAX_ISSUES_DIGEST]:
        iid = str(getattr(iss, "issue_id", "") or "")
        if not iid:
            continue
        desc = str(getattr(iss, "description", "") or "")
        rns = str(getattr(iss, "required_next_step", "") or "")
        status = getattr(iss, "status", "")
        st = str(getattr(status, "value", status) or "")
        out.append(
            {
                "issue_id": iid,
                "description_excerpt": _excerpt(desc),
                "required_next_step_excerpt": _excerpt(rns),
                "status": st,
            }
        )
    return out


def _active_issues_digest_from_orchestration(
    orch_issues: list[Any] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(orch_issues, list):
        return out
    for iss in orch_issues[:_MAX_ISSUES_DIGEST]:
        if not isinstance(iss, dict):
            continue
        iid = str(iss.get("issue_id", "") or "")
        if not iid:
            continue
        out.append(
            {
                "issue_id": iid,
                "description_excerpt": _excerpt(str(iss.get("description", "") or "")),
                "required_next_step_excerpt": _excerpt(
                    str(iss.get("required_next_step", "") or "")
                ),
                "status": str(iss.get("status", "") or ""),
            }
        )
    return out


def _recent_moves_tail(
    orchestration_state: Mapping[str, Any],
    *,
    k: int = _RECENT_MOVES_TAIL,
) -> list[dict[str, Any]]:
    raw = orchestration_state.get("recent_structured_moves")
    if not isinstance(raw, list):
        return []
    tail = raw[-k:] if len(raw) > k else raw
    slim: list[dict[str, Any]] = []
    for m in tail:
        if not isinstance(m, dict):
            continue
        slim.append(
            {
                "speaker": str(m.get("speaker", "") or ""),
                "action_excerpt": _excerpt(str(m.get("action", "") or "")),
                "dialogue_excerpt": _excerpt(str(m.get("dialogue", "") or "")),
            }
        )
    return slim


def _ca3_issue_engagement(
    move: Mapping[str, Any],
    active_digest: list[dict[str, Any]],
) -> dict[str, Any]:
    iu = move.get("issue_updates")
    mu = len(iu) if isinstance(iu, list) else 0
    active_n = len(active_digest)
    if active_n == 0:
        return {
            "method": "heuristic_v1",
            "active_issue_count": 0,
            "move_issue_update_count": mu,
            "classification": "not_applicable",
            "limitations": "No active issue text in scope.",
        }
    if mu > 0:
        return {
            "method": "heuristic_v1",
            "active_issue_count": active_n,
            "move_issue_update_count": mu,
            "classification": "engaged",
            "limitations": "Presence of issue_updates fields only; depth not scored.",
        }
    blob = " ".join(
        str(d.get("description_excerpt", ""))
        + " "
        + str(d.get("required_next_step_excerpt", ""))
        for d in active_digest
    )
    mot = move.get("motivation")
    goal = str(mot.get("goal", "")) if isinstance(mot, dict) else ""
    move_blob = f"{move.get('action', '')} {move.get('dialogue', '')} {goal}"
    tb = set(_meaningful_tokens(blob))
    mb = set(_meaningful_tokens(move_blob))
    inter = len(tb & mb)
    if inter >= 2:
        cls = "unclear"
    else:
        cls = "possibly_passive"
    return {
        "method": "heuristic_v1",
        "active_issue_count": active_n,
        "move_issue_update_count": mu,
        "classification": cls,
        "limitations": "Lexical overlap with issue excerpts only; intentional omission not distinguished.",
    }


def _ca4_repetition(
    move: Mapping[str, Any],
    next_actor: str,
    orchestration_state: Mapping[str, Any],
) -> dict[str, Any]:
    moves = orchestration_state.get("recent_structured_moves")
    if not isinstance(moves, list):
        moves = []
    prior = [
        m
        for m in moves
        if isinstance(m, dict) and str(m.get("speaker", "") or "") == next_actor
    ]
    k = min(3, len(prior))
    if k == 0:
        return {
            "method": "heuristic_v1",
            "prior_turns_compared": 0,
            "similarity_metric": None,
            "band": "low",
            "limitations": "No prior structured moves for this speaker.",
        }
    cur = set(
        _meaningful_tokens(
            str(move.get("action", "")) + " " + str(move.get("dialogue", ""))
        )
    )
    best = 0.0
    for m in prior[-k:]:
        prev = set(
            _meaningful_tokens(
                str(m.get("action", "")) + " " + str(m.get("dialogue", ""))
            )
        )
        best = max(best, _jaccard(cur, prev))
    band = "low"
    if best >= 0.55:
        band = "high"
    elif best >= 0.3:
        band = "moderate"
    return {
        "method": "heuristic_v1",
        "prior_turns_compared": k,
        "similarity_metric": round(best, 4),
        "band": band,
        "limitations": "Soft signal only; validator duplicate gate is authoritative.",
    }


def _ca5_plausibility(
    move: Mapping[str, Any],
    char_names: list[str],
    scene_state_pre: Mapping[str, Any] | None,
) -> dict[str, Any]:
    limitations = (
        "Name matching vs present_characters is imperfect (display vs internal ids, "
        "punctuation). Results are informational only and must never be treated as a "
        "correctness signal."
    )
    flags: list[str] = []
    present = []
    if scene_state_pre and isinstance(scene_state_pre.get("present_characters"), list):
        present = [str(p).strip().lower() for p in scene_state_pre["present_characters"] if p]
    present_set = set(present)
    prose = (str(move.get("action", "")) + " " + str(move.get("dialogue", ""))).lower()
    for name in char_names:
        raw = str(name or "").strip()
        if not raw:
            continue
        nl = raw.lower()
        nu = nl.replace("_", " ")
        if nl in present_set or nu in present_set:
            continue
        if len(nl) >= 3 and (nl in prose or nu in prose):
            flags.append(f"possible_reference_to_cast_not_in_present_characters:{raw}")
    return {"method": "heuristic_v1", "flags": flags, "limitations": limitations}


def _classify_tension_shift(ts: str) -> str:
    t = str(ts or "").strip().lower()
    if not t:
        return "not_applicable"
    if "de-escal" in t or "deescal" in t or "calm" in t or "ease" in t or "defus" in t:
        return "de_escalate"
    if "escal" in t or "spike" in t or "heighten" in t:
        return "escalate"
    if "resolv" in t or "closer" in t:
        return "neutral"
    return "unclear"


def _ca6_pressure_director(decision: Mapping[str, Any]) -> dict[str, Any]:
    ts = str(decision.get("tension_shift", "") or "")
    env = str(decision.get("environment_event", "") or "").strip()
    fields: list[str] = []
    if ts.strip():
        fields.append("tension_shift")
    if env:
        fields.append("environment_event")
    if not fields:
        return {
            "method": "heuristic_v1",
            "fields_present": [],
            "classification": "not_applicable",
            "limitations": "No director tension or environment fields.",
        }
    cls = _classify_tension_shift(ts)
    if env and cls == "not_applicable":
        cls = "neutral"
    return {
        "method": "heuristic_v1",
        "fields_present": fields,
        "classification": cls,
        "limitations": "Director cue only; does not assert in-fiction outcome.",
    }


def _ca7_pressure_move(move: Mapping[str, Any]) -> dict[str, Any]:
    fields: list[str] = []
    if str(move.get("tension_shift", "") or "").strip():
        fields.append("tension_shift")
    if isinstance(move.get("consequences"), list) and move.get("consequences"):
        fields.append("consequences")
    if isinstance(move.get("issue_updates"), list) and move.get("issue_updates"):
        fields.append("issue_updates")
    if not fields:
        return {
            "method": "heuristic_v1",
            "fields_present": [],
            "classification": "none",
            "limitations": "No model-emitted pressure fields on move.",
        }
    cls = "unclear"
    if "tension_shift" in fields:
        cls = _classify_tension_shift(str(move.get("tension_shift", "")))
    if "consequences" in fields:
        cons = " ".join(str(c).lower() for c in (move.get("consequences") or []) if c)
        if any(x in cons for x in ("resolv", "agree", "de-escal", "calm")):
            cls = "resolve"
        elif any(x in cons for x in ("escal", "threat", "violence", "challenge")):
            cls = "escalate"
    if "issue_updates" in fields and cls in ("none", "unclear", "not_applicable"):
        cls = "unclear"
    return {
        "method": "heuristic_v1",
        "fields_present": fields,
        "classification": cls,
        "limitations": "Move-emitted fields only; separate from director pressure_director.",
    }


def build_character_audit_v1(
    *,
    move: Mapping[str, Any],
    decision: Mapping[str, Any],
    next_actor: str,
    char_names: list[str],
    trigger_text: str,
    attempt_index: int,
    orchestration_state: Mapping[str, Any],
    continuity_scope: str,
    scene_state_pre_source_dict: Mapping[str, Any] | None,
    issues_before_signatures: Mapping[str, Any] | None,
    cm_exec: Any | None,
) -> dict[str, Any]:
    """Build advisory character decision audit (v1). Does not mutate inputs."""
    scene_trim = _trim_scene_state_pre(scene_state_pre_source_dict)
    issues_before_json = _project_issues_before_json(issues_before_signatures)
    if continuity_scope == "continuity_enabled" and cm_exec is not None:
        active_digest = _active_issues_digest_from_cm(cm_exec)
    else:
        orch_iss = orchestration_state.get("continuity_active_issues")
        active_digest = _active_issues_digest_from_orchestration(
            orch_iss if isinstance(orch_iss, list) else []
        )
    moves_tail = _recent_moves_tail(orchestration_state)
    reason = str(decision.get("reason", "") or "")

    observed: dict[str, Any] = {
        "next_actor": next_actor,
        "attempt_index": attempt_index,
        "continuity_scope": continuity_scope,
        "trigger_text_excerpt": _excerpt(trigger_text),
        "director_decision": {
            "next_actor": str(decision.get("next_actor", "") or ""),
            "tension_shift": str(decision.get("tension_shift", "") or ""),
            "environment_event": str(decision.get("environment_event", "") or ""),
            "reason_excerpt": _excerpt(reason),
        },
        "move_excerpt": {
            "action": _excerpt(str(move.get("action", "") or "")),
            "dialogue": _excerpt(str(move.get("dialogue", "") or "")),
            "motivation": dict(move.get("motivation") or {})
            if isinstance(move.get("motivation"), dict)
            else {},
        },
        "scene_state_pre": scene_trim,
        "scene_state_pre_source": (
            "continuity_scene_state.to_dict_allowlist"
            if continuity_scope == "continuity_enabled"
            else "orchestration_state.scene_state_allowlist"
        ),
        "issues_before": issues_before_json,
        "active_issues_digest": active_digest,
        "recent_structured_moves_tail": moves_tail,
        "chat_history_tail_note": "chat_history_not_used_in_v1_dimensions",
    }

    derived: dict[str, Any] = {
        "issue_engagement": _ca3_issue_engagement(move, active_digest),
        "repetition_vs_prior_self": _ca4_repetition(move, next_actor, orchestration_state),
        "scene_plausibility_flags": _ca5_plausibility(move, char_names, scene_trim),
        "pressure_director": _ca6_pressure_director(decision),
        "pressure_move": _ca7_pressure_move(move),
    }

    return {
        "schema_version": _SCHEMA_VERSION,
        "layer": "character_decision",
        "scope_note": "per_turn_pre_continuity_v1_advisory",
        "methods_note": "deterministic_heuristics_no_llm",
        "observed": observed,
        "derived": derived,
        "provenance": {
            "pipeline": "execute_character_turn",
            "placement": (
                "pre_process_turn_when_continuity_else_pre_metadata_no_continuity"
            ),
        },
    }
