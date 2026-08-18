"""Issue #243-C — legacy F0–F7 investigation-era taxonomy lane (offline only).

The historical #240 audit classifier (F0–F7) is **investigation tooling**, not the primary
semantic contract evaluator. Corrected categories from ``semantic_proposal_eval_v1`` remain
primary for #243 evaluation. Legacy F-codes are nested/secondary and observational-only.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Final

from semantic_eval_boundary_signals import (
    EXEC_DEPART,
    EXEC_RETURN,
    ROUND_TRIP,
    dorm_studio_boundary_signals,
)

OFF_FOCAL_CUES = re.compile(
    r"\b(kitchen|kitchenette|off.?focal|offstage|step(?:s|ped)?\s+(?:out|away|off)|"
    r"withdraw|leave\s+the\s+(?:room|exchange|focal)|excursion|reentry|re-enter)\b",
    re.I,
)
REENTRY_CUES = re.compile(r"\b(re-?enter|return(?:s|ed|ing)?\s+to|come\s+back)\b", re.I)
from semantic_eval_profiles import observational_eval_envelope

LEGACY_TAXONOMY_LANE: Final[str] = "issue240_investigation_classifier_v1"
LEGACY_TAXONOMY_PHASE: Final[str] = "243-C"

LEGACY_F_CODES: Final[frozenset[str]] = frozenset({"F0", "F1", "F2", "F3", "F4", "F7"})

LEGACY_F_CODE_LABELS: Final[dict[str, str]] = {
    "F0": "Honest aligned success with proposals",
    "F1": "Schema/syntax failure",
    "F2": "Semantic omission",
    "F3": "Performative structure / empty array cosplay",
    "F4": "Prose/structure contradiction",
    "F7": "Ambient / honest no_covered_change",
}

LEGACY_TAXONOMY_STATUSES: Final[frozenset[str]] = frozenset(
    {"historical", "superseded", "compatible", "ambiguous"}
)

_ACTOR_TARGETED_MODE = "actor_targeted_overlay"
_ONLY_ACTOR = re.compile(r"\b([A-Za-z][A-Za-z _]*?)\s+ONLY\b", re.I)


def legacy_lane_disclaimer() -> dict[str, Any]:
    return observational_eval_envelope(
        legacy_taxonomy_lane=LEGACY_TAXONOMY_LANE,
        legacy_taxonomy_purpose=(
            "historical investigation-era classifier — not primary contract-alignment truth"
        ),
        legacy_not_runtime_truth=True,
        corrected_category_primary_for_issue_243=True,
    )


def _overlay_meta(data: dict[str, Any]) -> dict[str, Any]:
    md = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return {
        "overlay_schedule_mode": data.get("overlay_schedule_mode") or md.get("overlay_schedule_mode"),
        "overlay_target_actor": data.get("overlay_target_actor") or md.get("overlay_target_actor"),
        "overlay_applied": data.get("overlay_applied", md.get("overlay_applied")),
        "overlay_skipped_reason": data.get("overlay_skipped_reason")
        or md.get("overlay_skipped_reason"),
    }


def _overlay_demands_proposals(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "")
    t = trig.lower()
    return "semantic_proposals" in t and (
        "required:" in t
        or "required " in t
        or "must include" in t
        or "must emit" in t
        or "same required" in t
    )


def _expected_overlay_actor(data: dict[str, Any]) -> str | None:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        target = str(meta.get("overlay_target_actor") or "").strip()
        return target or None
    trig = str(data.get("effective_user_trigger") or "")
    m = _ONLY_ACTOR.search(trig)
    if not m:
        return None
    return str(m.group(1) or "").strip()


def _overlay_opportunity(data: dict[str, Any]) -> bool:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        return bool(meta.get("overlay_target_actor"))
    return _overlay_demands_proposals(data)


def _overlay_applied(data: dict[str, Any]) -> bool:
    meta = _overlay_meta(data)
    if meta.get("overlay_applied") is True:
        return True
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        return meta.get("overlay_applied") is True
    return _overlay_demands_proposals(data) and _actor_aligned(data) is True


def _actor_aligned(data: dict[str, Any]) -> bool | None:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        if not meta.get("overlay_target_actor"):
            return None
        if meta.get("overlay_applied") is not True:
            return False
        expected = str(meta.get("overlay_target_actor") or "")
        bot = str(data.get("bot_name") or "").strip()
        if not bot:
            return False
        exp_norm = expected.replace("_", " ").casefold()
        bot_norm = bot.replace("_", " ").casefold()
        return exp_norm in bot_norm or bot_norm in exp_norm
    if not _overlay_demands_proposals(data):
        return None
    expected = _expected_overlay_actor(data)
    if not expected:
        return None
    bot = str(data.get("bot_name") or "").strip()
    if not bot:
        return False
    exp_norm = expected.replace("_", " ").casefold()
    bot_norm = bot.replace("_", " ").casefold()
    return exp_norm in bot_norm or bot_norm in exp_norm


def _beats_text(data: dict[str, Any]) -> str:
    bt = str(data.get("beats_text") or "").strip()
    if bt:
        return bt
    po = data.get("parsed_output") or {}
    parts: list[str] = []
    for b in po.get("beats") or []:
        if isinstance(b, dict):
            parts.append(str(b.get("action") or ""))
            parts.append(str(b.get("dialogue") or ""))
    return " ".join(parts)


def _semantic_evaluation(po: dict[str, Any]) -> dict[str, Any] | None:
    ev = po.get("semantic_evaluation")
    return ev if isinstance(ev, dict) else None


def _proposals(data: dict[str, Any]) -> list[dict[str, Any]]:
    po = data.get("parsed_output") or {}
    sp = po.get("semantic_proposals")
    if isinstance(sp, list) and sp:
        return [p for p in sp if isinstance(p, dict)]
    ev = _semantic_evaluation(po)
    if isinstance(ev, dict) and ev.get("decision") == "covered_change":
        props = ev.get("proposals")
        if isinstance(props, list):
            return [p for p in props if isinstance(p, dict)]
    emitted = data.get("proposals_emitted")
    if isinstance(emitted, list) and emitted:
        out: list[dict[str, Any]] = []
        for item in emitted:
            s = str(item)
            if "/" in s:
                kind, op = s.split("/", 1)
                out.append({"kind": kind, "operation": op})
            else:
                out.append({"kind": s})
        return out
    return []


def _trigger_expects_off_focal(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "").lower()
    return "off_focal" in trig or "kitchen" in trig or "kitchenette" in trig


def _trigger_expects_reentry(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "").lower()
    return "reentry" in trig or "re-enter" in trig


def _honest_f0(data: dict[str, Any]) -> bool:
    props = _proposals(data)
    if not props:
        return False
    beats = _beats_text(data)
    trig = str(data.get("effective_user_trigger") or "").lower()
    bot = str(data.get("bot_name") or "")
    for p in props:
        kind = str(p.get("kind") or "")
        char = str(p.get("character") or "")
        if kind == "off_focal":
            if bot and char and char.lower() != bot.lower():
                return False
            if _trigger_expects_off_focal(data):
                if not (OFF_FOCAL_CUES.search(beats) or OFF_FOCAL_CUES.search(trig)):
                    return False
        if kind == "reentry":
            if bot and char and char.lower() != bot.lower():
                return False
            if _trigger_expects_reentry(data):
                if not (REENTRY_CUES.search(beats) or REENTRY_CUES.search(trig)):
                    return False
    return True


def classify_legacy_turn(data: dict[str, Any]) -> tuple[str, list[str]]:
    """Historical #240 investigation classifier — not primary #243 evaluator output."""
    tags: list[str] = []
    po = data.get("parsed_output")
    if not isinstance(po, dict):
        if data.get("beats") or data.get("beats_text"):
            po = {
                "beats": data.get("beats") or [],
                "semantic_evaluation": data.get("semantic_evaluation") or {},
            }
            data = dict(data)
            data["parsed_output"] = po
        else:
            return "F1", ["schema_syntax"]

    overlay = _overlay_applied(data)
    props = _proposals(data)
    raw = str(data.get("raw_response") or "")
    raw_has_key = "semantic_proposals" in raw
    ev = _semantic_evaluation(po)
    decision = str(ev.get("decision") or "").strip() if isinstance(ev, dict) else ""
    if not decision and data.get("semantic_decision"):
        decision = str(data.get("semantic_decision") or "").strip()

    if overlay:
        if decision == "no_covered_change":
            beats = _beats_text(data)
            if OFF_FOCAL_CUES.search(beats) or REENTRY_CUES.search(beats):
                return "F7", tags + ["honest_no_covered_change", "prose_implies_covered"]
            return "F7", tags + ["honest_no_covered_change"]
        if decision == "covered_change":
            if props:
                if _honest_f0(data):
                    return "F0", tags + ["semantic_evaluation"]
                return "F4", tags + ["prose_structure_contradiction", "semantic_evaluation"]
            return "F2", tags + ["covered_change_without_proposals"]
        if props:
            if _honest_f0(data):
                return "F0", tags
            return "F4", tags + ["prose_structure_contradiction"]
        if raw_has_key and '"semantic_proposals": []' in raw:
            return "F3", tags + ["performative_structure", "empty_array_cosplay"]
        if "semantic_proposals" in po and po.get("semantic_proposals") == []:
            return "F3", tags + ["performative_structure"]
        return "F2", tags + ["semantic_omission"]

    if props:
        if _honest_f0(data):
            return "F0", tags
        return "F4", tags

    beats = _beats_text(data)
    if OFF_FOCAL_CUES.search(beats) or REENTRY_CUES.search(beats):
        return "F2", tags + ["semantic_omission", "prose_implies_covered"]

    return "F7", tags


def corpus_case_to_legacy_audit_dict(case: dict[str, Any]) -> dict[str, Any]:
    """Shape a frozen corpus row for legacy replay classification."""
    beats = case.get("beats") or []
    return {
        "beats_text": case.get("beats_text") or "",
        "beats": beats,
        "parsed_output": {
            "beats": beats,
            "semantic_evaluation": case.get("semantic_evaluation") or {},
            "semantic_proposals": case.get("semantic_proposals"),
        },
        "semantic_decision": case.get("semantic_decision"),
        "proposals_emitted": case.get("proposals_emitted") or [],
        "raw_response": case.get("raw_response") or "",
        "bot_name": case.get("actor") or case.get("bot_name") or "",
        "effective_user_trigger": case.get("trigger_context") or case.get("effective_user_trigger") or "",
        "overlay_applied": case.get("overlay_applied"),
        "metadata": {
            "overlay_applied": case.get("overlay_applied"),
            "overlay_schedule_mode": case.get("overlay_schedule_mode"),
            "overlay_target_actor": case.get("overlay_target_actor"),
        },
    }


def extract_stored_legacy_f_code(case: dict[str, Any]) -> tuple[str | None, list[str]]:
    primary = case.get("classifier_primary")
    if primary is None:
        return None, []
    code = str(primary).strip().upper()
    if code not in LEGACY_F_CODES:
        return None, []
    secondary_raw = case.get("classifier_secondary") or []
    secondary = [str(x).strip() for x in secondary_raw if str(x).strip()] if isinstance(secondary_raw, list) else []
    return code, secondary


def resolve_legacy_f_code(
    case: dict[str, Any],
    *,
    replay: bool = False,
) -> tuple[str, list[str], str]:
    """Return ``(f_code, secondary_tags, source)`` where source is ``stored`` or ``replayed``."""
    stored, sec = extract_stored_legacy_f_code(case)
    if stored and not replay:
        return stored, sec, "stored"
    audit = corpus_case_to_legacy_audit_dict(case)
    replayed, replay_sec = classify_legacy_turn(audit)
    if stored and replay and stored != replayed:
        return stored, sec, "stored_replay_mismatch"
    if replay or not stored:
        return replayed, replay_sec, "replayed"
    return stored, sec, "stored"


def _generic_boundary_signals(beats: str) -> dict[str, bool]:
    depart = bool(EXEC_DEPART.search(beats))
    ret = bool(EXEC_RETURN.search(beats))
    round_trip = bool(ROUND_TRIP.search(beats))
    return {
        "exec_depart": depart,
        "exec_return": ret,
        "in_room_only": False,
        "info_boundary_only": False,
        "round_trip_same_turn": round_trip and depart and ret,
        "participation_choreography": False,
        "participation_choreography_safe": False,
        "participation_choreography_boundary_adjacent": False,
    }


def boundary_signals_for_legacy(
    *,
    beats_text: str,
    profile_id: str,
    case_boundary_signals: dict[str, bool] | None = None,
) -> dict[str, bool]:
    if case_boundary_signals:
        return {str(k): bool(v) for k, v in case_boundary_signals.items()}
    if profile_id == "dorm_studio_single_space":
        return dorm_studio_boundary_signals(beats_text)
    return _generic_boundary_signals(beats_text)


def map_legacy_f_code_to_corrected(
    f_code: str,
    secondary: list[str],
    *,
    semantic_decision: str,
    boundary_signals: dict[str, bool],
    overlay_applied: bool,
    has_proposals: bool,
    profile_id: str,
) -> tuple[str | None, list[str], bool]:
    """Cautious legacy→corrected mapping. Returns ``(category, limitations, misflag_hint)``."""
    limitations: list[str] = []
    misflag = False
    sec = set(secondary)
    decision = str(semantic_decision or "").strip()

    if f_code == "F0":
        if decision == "covered_change" and has_proposals:
            return "success", limitations, False
        limitations.append("F0 without covered_change+proposals cannot be mapped safely")
        return None, limitations, False

    if f_code == "F1":
        limitations.append("F1 schema/syntax lane is outside semantic alignment evaluation scope")
        return "evaluator_defect", limitations, False

    if f_code == "F2":
        if decision == "covered_change" and not has_proposals:
            return "true_semantic_miss", limitations, False
        if boundary_signals.get("round_trip_same_turn") and decision == "no_covered_change":
            return "contract_limited", limitations, False
        if profile_id == "dorm_studio_single_space" and (
            boundary_signals.get("in_room_only") or boundary_signals.get("info_boundary_only")
        ):
            return "success", limitations + ["legacy F2 overfired on in-room/info boundary prose"], True
        if "prose_implies_covered" in sec and decision == "no_covered_change":
            if overlay_applied and not boundary_signals.get("exec_depart"):
                limitations.append("overlay pressure alone must not force true_semantic_miss")
                return "ambiguous_threshold", limitations, False
            if profile_id != "dorm_studio_single_space":
                limitations.append("generic profile: prose_implies_covered mapping remains threshold-sensitive")
                return "ambiguous_threshold", limitations, False
            return "ambiguous_threshold", limitations, False
        limitations.append("F2 semantic omission without durable net-state evidence — mapping ambiguous")
        return None, limitations, False

    if f_code == "F3":
        limitations.append("F3 performative structure requires beat-level review; mapping cautious")
        if decision == "covered_change":
            return "evaluator_defect", limitations, False
        return "ambiguous_threshold", limitations, False

    if f_code == "F4":
        if profile_id == "dorm_studio_single_space" and (
            boundary_signals.get("in_room_only") or boundary_signals.get("info_boundary_only")
        ) and decision == "no_covered_change":
            return "success", limitations + ["legacy F4 overfired on in-room/info boundary prose"], True
        limitations.append("F4 prose/structure contradiction mapping requires beat review")
        return "evaluator_defect", limitations, False

    if f_code == "F7":
        if boundary_signals.get("round_trip_same_turn") and decision == "no_covered_change":
            return "contract_limited", limitations, False
        if profile_id == "dorm_studio_single_space" and (
            boundary_signals.get("in_room_only") or boundary_signals.get("info_boundary_only")
        ) and decision == "no_covered_change":
            return "success", limitations + ["legacy F7 treated in-room/info no_covered_change as miss pressure"], True
        if decision == "no_covered_change" and not boundary_signals.get("exec_depart"):
            if "prose_implies_covered" in sec:
                limitations.append("F7 with prose_implies_covered secondary — threshold may vary")
                return "ambiguous_threshold", limitations, False
            return "success", limitations, False
        if (
            boundary_signals.get("exec_depart")
            and not boundary_signals.get("exec_return")
            and decision == "no_covered_change"
        ):
            limitations.append("overlay pressure alone must not force true_semantic_miss via legacy lane")
            return "ambiguous_threshold", limitations, False
        limitations.append("F7 ambient/honest mapping uncertain without full audit context")
        return None, limitations, False

    limitations.append(f"unknown legacy F-code {f_code!r}")
    return None, limitations, False


def derive_legacy_taxonomy_status(
    *,
    f_code: str,
    corrected_category: str,
    mapped_category: str | None,
    legacy_classifier_misflag: bool,
    mapping_limitations: list[str],
    mapping_source: str,
) -> str:
    if mapping_source == "stored_replay_mismatch":
        return "ambiguous"
    if legacy_classifier_misflag:
        return "superseded"
    if mapped_category is None or any("ambiguous" in x.lower() or "cannot" in x.lower() for x in mapping_limitations):
        return "ambiguous"
    if mapped_category == corrected_category:
        return "compatible"
    if mapped_category != corrected_category:
        return "ambiguous"
    return "historical"


def attach_legacy_lane(
    judgment: dict[str, Any],
    *,
    case: dict[str, Any],
    beats_text: str,
    profile_id: str,
    overlay_applied: bool,
    has_proposals: bool,
    boundary_signals: dict[str, bool] | None = None,
    legacy_replay: bool = False,
) -> dict[str, Any]:
    """Nest legacy F-code metadata under ``legacy_lane``; keep corrected_category primary."""
    f_code, secondary, source = resolve_legacy_f_code(case, replay=legacy_replay)
    signals = boundary_signals_for_legacy(
        beats_text=beats_text,
        profile_id=profile_id,
        case_boundary_signals=boundary_signals or judgment.get("boundary_signals"),
    )
    mapped, map_limits, misflag_hint = map_legacy_f_code_to_corrected(
        f_code,
        secondary,
        semantic_decision=str(judgment.get("semantic_decision") or case.get("semantic_decision") or ""),
        boundary_signals=signals,
        overlay_applied=overlay_applied,
        has_proposals=has_proposals,
        profile_id=profile_id,
    )
    misflag = bool(judgment.get("legacy_classifier_misflag")) or misflag_hint
    status = derive_legacy_taxonomy_status(
        f_code=f_code,
        corrected_category=str(judgment.get("corrected_category") or ""),
        mapped_category=mapped,
        legacy_classifier_misflag=misflag,
        mapping_limitations=map_limits,
        mapping_source=source,
    )
    legacy_lane = legacy_lane_disclaimer()
    legacy_lane.update(
        {
            "legacy_f_code": f_code,
            "legacy_f_code_label": LEGACY_F_CODE_LABELS.get(f_code, f_code),
            "legacy_secondary_tags": list(secondary),
            "legacy_taxonomy_status": status,
            "legacy_mapped_corrected_category": mapped,
            "legacy_resolution_source": source,
            "legacy_mapping_limitations": list(map_limits),
            "operator_guidance": _operator_guidance(status, f_code, misflag),
        }
    )
    out = dict(judgment)
    out["legacy_classifier_misflag"] = misflag
    out["legacy_lane"] = legacy_lane
    lim = list(out.get("limitations") or [])
    lim.append("legacy_f_codes: investigation-era taxonomy — not primary contract-alignment truth")
    if status == "ambiguous" and map_limits:
        for ml in map_limits:
            tagged = f"legacy_mapping_ambiguous: {ml}"
            if tagged not in lim:
                lim.append(tagged)
    out["limitations"] = lim
    return out


def _operator_guidance(status: str, f_code: str, misflag: bool) -> str:
    if status == "superseded" or misflag:
        return (
            f"Legacy {f_code} reflected investigation-era false-positive pressure; "
            "corrected_category is primary for #243 evaluation."
        )
    if status == "compatible":
        return f"Legacy {f_code} aligns with corrected_category under cautious mapping."
    if status == "ambiguous":
        return (
            f"Legacy {f_code} cannot be mapped to corrected_category safely; "
            "do not treat legacy code as runtime failure."
        )
    return (
        f"Legacy {f_code} recorded from historical investigation tooling; "
        "runtime escalation requires committed state / semantic proposal decision corroboration."
    )


def legacy_f_code_counts_from_corpus(
    corpus: dict[str, Any],
    *,
    replay: bool = False,
) -> dict[str, Any]:
    """Explicit legacy lane replay — preserves historical F-code counts when stored or replayed."""
    counts: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    for case in corpus.get("cases") or []:
        if not isinstance(case, dict):
            continue
        f_code, _, source = resolve_legacy_f_code(case, replay=replay)
        counts[f_code] += 1
        sources[source] += 1
        if source == "stored_replay_mismatch":
            stored, _, _ = extract_stored_legacy_f_code(case)
            replayed, _, _ = resolve_legacy_f_code(case, replay=True)
            mismatches.append(
                {
                    "case_id": case.get("case_id"),
                    "stored": stored,
                    "replayed": replayed,
                }
            )
    envelope = legacy_lane_disclaimer()
    envelope.update(
        {
            "schema_version": "issue243_legacy_replay_summary_v1",
            "issue": 243,
            "phase": LEGACY_TAXONOMY_PHASE,
            "legacy_f_code_counts": dict(counts),
            "legacy_resolution_sources": dict(sources),
            "case_count": sum(counts.values()),
            "replay_mode": replay,
            "stored_replay_mismatches": mismatches,
        }
    )
    return envelope
