"""Issue #251 — post-replay semantic adjudication (reuses #243-B / #249 eval layer).

Observational only; does not replace deterministic S1/S2 or continuity authority (#224).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from semantic_eval_boundary_signals import dorm_studio_boundary_signals
from semantic_proposal_eval_v1 import (
    EvalCaseInput,
    evaluate_case,
    model_alignment_success,
)

ADJUDICATION_SCHEMA = "issue251_replay_adjudication.v1"
DEFAULT_SCENARIO_ID = "marlene_willow_dorm_omega_misassignment"


def beats_text_from_audit(audit_path: str | Path) -> str:
    data = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    beats = (data.get("parsed_output") or {}).get("beats") or data.get("beats") or []
    parts: list[str] = []
    for b in beats:
        if isinstance(b, dict):
            parts.append(str(b.get("action") or ""))
            parts.append(str(b.get("dialogue") or ""))
    return " ".join(parts).strip()


def fiction_expects_scene_departure(signals: dict[str, bool]) -> bool:
    return bool(
        signals.get("exec_depart")
        and not signals.get("exec_return")
        and not signals.get("in_room_only")
        and not signals.get("round_trip_same_turn")
    )


def fiction_withdrawal_or_in_room_only(signals: dict[str, bool]) -> bool:
    if fiction_expects_scene_departure(signals):
        return False
    return bool(
        signals.get("in_room_only")
        or signals.get("participation_choreography")
        or signals.get("participation_choreography_safe")
        or (
            signals.get("participation_choreography_boundary_adjacent")
            and not signals.get("exec_depart")
        )
    )


def classify_failure_lane(attempt: dict[str, Any] | None) -> str:
    if not attempt:
        return "unresolved"
    if not attempt.get("parse_ok"):
        return "issue249_structural"
    if attempt.get("route_to_249"):
        return "issue249_structural"
    if attempt.get("issue251_genuine_miss"):
        return "issue251_semantic"
    if attempt.get("S2_structural_legality_pass") and not attempt.get(
        "S1_semantic_intent_correct"
    ):
        return "issue251_semantic"
    if not attempt.get("S2_structural_legality_pass") and attempt.get(
        "S1_semantic_intent_correct"
    ):
        return "issue249_structural"
    return "none"


def _alignment_vs_doctrine(
    *,
    doctrine_expected: str,
    attempt: dict[str, Any],
    judgment: dict[str, Any],
    signals: dict[str, bool],
) -> dict[str, Any]:
    decision = attempt.get("decision")
    kinds = list(attempt.get("proposal_kinds") or [])
    has_off = "off_focal" in kinds
    cat = str(judgment.get("corrected_category") or "")
    rationale_bits: list[str] = []

    if doctrine_expected == "off_focal":
        model_ok = decision == "covered_change" and kinds == ["off_focal"]
        if model_ok:
            return {
                "adjudicated_semantically_correct": True,
                "adjudicated_false_positive": False,
                "adjudicated_false_negative": False,
                "ambiguous_or_recoverable": False,
                "rationale": "Replay emitted covered_change + off_focal matching exit rubric.",
            }
        fiction_exit = fiction_expects_scene_departure(signals)
        if fiction_exit:
            rationale_bits.append("Fiction shows material scene departure (exec_depart).")
        if decision in (None, "") and not attempt.get("parse_ok"):
            if cat == "ambiguous_threshold" and fiction_exit:
                return {
                    "adjudicated_semantically_correct": None,
                    "adjudicated_false_positive": False,
                    "adjudicated_false_negative": None,
                    "ambiguous_or_recoverable": True,
                    "rationale": " ".join(
                        rationale_bits
                        + [
                            "Unparsed output; dorm evaluator marks ambiguous_threshold for departure beat."
                        ]
                    ),
                }
            if cat in ("true_semantic_miss", "ambiguous_threshold") or fiction_exit:
                return {
                    "adjudicated_semantically_correct": False,
                    "adjudicated_false_positive": False,
                    "adjudicated_false_negative": True,
                    "ambiguous_or_recoverable": cat == "ambiguous_threshold",
                    "rationale": " ".join(
                        rationale_bits
                        + [f"Expected off_focal; model decision={decision!r}; eval={cat}."]
                    ),
                }
        if decision == "no_covered_change":
            if cat == "ambiguous_threshold":
                return {
                    "adjudicated_semantically_correct": None,
                    "adjudicated_false_positive": False,
                    "adjudicated_false_negative": None,
                    "ambiguous_or_recoverable": True,
                    "rationale": " ".join(
                        rationale_bits
                        + ["Threshold exit; no_covered_change with ambiguous_threshold adjudication."]
                    ),
                }
            return {
                "adjudicated_semantically_correct": False,
                "adjudicated_false_positive": False,
                "adjudicated_false_negative": True,
                "ambiguous_or_recoverable": False,
                "rationale": " ".join(
                    rationale_bits + ["Missed off_focal on departure beat."]
                ),
            }
        if has_off:
            return {
                "adjudicated_semantically_correct": False,
                "adjudicated_false_positive": True,
                "adjudicated_false_negative": False,
                "ambiguous_or_recoverable": False,
                "rationale": "off_focal emitted but proposal shape/decision not rubric-aligned.",
            }
        return {
            "adjudicated_semantically_correct": model_alignment_success(judgment),
            "adjudicated_false_positive": False,
            "adjudicated_false_negative": not model_alignment_success(judgment),
            "ambiguous_or_recoverable": cat == "ambiguous_threshold",
            "rationale": judgment.get("rationale") or cat,
        }

    # no_covered_change rubric
    model_ok = decision == "no_covered_change" and not has_off
    if model_ok:
        return {
            "adjudicated_semantically_correct": True,
            "adjudicated_false_positive": False,
            "adjudicated_false_negative": False,
            "ambiguous_or_recoverable": False,
            "rationale": "Replay no_covered_change without off_focal; aligned with non-exit rubric.",
        }
    if has_off or (decision == "covered_change" and has_off):
        return {
            "adjudicated_semantically_correct": False,
            "adjudicated_false_positive": True,
            "adjudicated_false_negative": False,
            "ambiguous_or_recoverable": False,
            "rationale": "False off_focal relative to non-exit / withdrawal rubric.",
        }
    if decision in (None, "") and not attempt.get("parse_ok"):
        if cat == "success" or fiction_withdrawal_or_in_room_only(signals):
            return {
                "adjudicated_semantically_correct": True,
                "adjudicated_false_positive": False,
                "adjudicated_false_negative": False,
                "ambiguous_or_recoverable": True,
                "rationale": " ".join(
                    [
                        "Unparsed JSON; fiction/evaluator support no_covered_change (withdrawal/in-room).",
                        judgment.get("rationale") or "",
                    ]
                ).strip(),
            }
        if cat == "ambiguous_threshold":
            return {
                "adjudicated_semantically_correct": None,
                "adjudicated_false_positive": False,
                "adjudicated_false_negative": False,
                "ambiguous_or_recoverable": True,
                "rationale": judgment.get("rationale") or "ambiguous_threshold",
            }
    if decision == "no_covered_change" and cat == "success":
        return {
            "adjudicated_semantically_correct": True,
            "adjudicated_false_positive": False,
            "adjudicated_false_negative": False,
            "ambiguous_or_recoverable": False,
            "rationale": judgment.get("rationale")
            or "Evaluator success on honest no_covered_change.",
        }
    if cat == "ambiguous_threshold":
        return {
            "adjudicated_semantically_correct": None,
            "adjudicated_false_positive": False,
            "adjudicated_false_negative": False,
            "ambiguous_or_recoverable": True,
            "rationale": judgment.get("rationale") or "ambiguous_threshold",
        }
    return {
        "adjudicated_semantically_correct": model_alignment_success(judgment),
        "adjudicated_false_positive": has_off,
        "adjudicated_false_negative": False,
        "ambiguous_or_recoverable": cat == "ambiguous_threshold",
        "rationale": judgment.get("rationale") or cat,
    }


def adjudicate_replay_row(row: dict[str, Any]) -> dict[str, Any]:
    """Attach adjudicated semantic layer to one replay matrix row."""
    fa = row.get("first_attempt") or {}
    source = row.get("source_artifact")
    if not source:
        return {
            "schema_version": ADJUDICATION_SCHEMA,
            "case_id": row.get("case_id"),
            "status": "missing_source_artifact",
        }

    beats = beats_text_from_audit(source)
    signals = dorm_studio_boundary_signals(beats)
    kinds = [str(k) for k in (fa.get("proposal_kinds") or []) if k]
    doctrine = str(row.get("doctrine_expected") or "")

    eval_case = EvalCaseInput(
        case_id=str(row.get("case_id") or ""),
        scenario_id=DEFAULT_SCENARIO_ID,
        beats_text=beats,
        semantic_decision=str(fa.get("decision") or "no_covered_change"),
        proposals_emitted=kinds,
        overlay_applied=False,
        movement_cues=any(
            signals.get(k)
            for k in (
                "exec_depart",
                "exec_return",
                "participation_choreography_boundary_adjacent",
            )
        ),
        profile_id="dorm_studio_single_space",
        profile_resolution="issue251_replay_adjudication",
        boundary_signals=signals,
    )
    judgment = evaluate_case(
        eval_case,
        raw_case={
            "case_id": eval_case.case_id,
            "boundary_signals": signals,
            "doctrine_expected": doctrine,
        },
    )

    alignment = _alignment_vs_doctrine(
        doctrine_expected=doctrine,
        attempt=fa,
        judgment=judgment,
        signals=signals,
    )
    lane = classify_failure_lane(fa)
    s2 = bool(fa.get("S2_structural_legality_pass"))
    adj_correct = alignment["adjudicated_semantically_correct"]

    return {
        "schema_version": ADJUDICATION_SCHEMA,
        "case_id": row.get("case_id"),
        "cohort": row.get("cohort"),
        "category": row.get("category"),
        "doctrine_expected": doctrine,
        "adjudicated_expected_label": row.get("expected_result_label"),
        "boundary_signals": signals,
        "fiction_expects_scene_departure": fiction_expects_scene_departure(signals),
        "fiction_withdrawal_or_in_room_only": fiction_withdrawal_or_in_room_only(
            signals
        ),
        "semantic_eval_judgment": {
            "corrected_category": judgment.get("corrected_category"),
            "rationale": judgment.get("rationale"),
            "limitations": judgment.get("limitations"),
            "legacy_lane": judgment.get("legacy_lane"),
            "profile_id": judgment.get("profile_id"),
        },
        "failure_lane": lane,
        "deterministic": {
            "S1": fa.get("S1_semantic_intent_correct"),
            "S2": fa.get("S2_structural_legality_pass"),
            "decision": fa.get("decision"),
            "proposal_kinds": kinds,
            "parse_ok": fa.get("parse_ok"),
            "ingress_pass": fa.get("ingress_pass"),
            "ingress_error": fa.get("ingress_error"),
            "route_to_249": fa.get("route_to_249"),
            "issue251_genuine_miss": fa.get("issue251_genuine_miss"),
        },
        "adjudicated": {
            **alignment,
            "structurally_contaminated_semantically_correct": bool(
                adj_correct is True and not s2
            ),
            "evaluator_model_alignment_success": model_alignment_success(judgment),
        },
        "limitations": [
            "observational_only: not runtime authority",
            "continuity_authority_224_preserved",
            "adjudication_does_not_override_deterministic_metrics",
        ],
    }


def adjudicate_replay_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [adjudicate_replay_row(r) for r in rows]


def summarize_adjudicated_vs_deterministic(
    rows: list[dict[str, Any]],
    *,
    adjudications: list[dict[str, Any]],
) -> dict[str, Any]:
    paired = []
    for row, adj in zip(rows, adjudications):
        if adj.get("status") == "missing_source_artifact":
            continue
        fa = row.get("first_attempt") or {}
        det = row.get("metrics") or {}
        det_correct = det.get("outcome_correct")
        if det_correct is None:
            det_correct = fa.get("S1_semantic_intent_correct")
        paired.append(
            {
                "case_id": row.get("case_id"),
                "cohort": row.get("cohort"),
                "deterministic_correct": det_correct,
                "deterministic_s1": fa.get("S1_semantic_intent_correct"),
                "deterministic_s2": fa.get("S2_structural_legality_pass"),
                "adjudicated_correct": adj["adjudicated"][
                    "adjudicated_semantically_correct"
                ],
                "ambiguous": adj["adjudicated"]["ambiguous_or_recoverable"],
                "failure_lane": adj.get("failure_lane"),
                "corrected_category": adj["semantic_eval_judgment"][
                    "corrected_category"
                ],
                "structurally_contaminated_semantically_correct": adj["adjudicated"][
                    "structurally_contaminated_semantically_correct"
                ],
            }
        )

    def rate(key: str, *, cohort: str | None = None) -> float | None:
        items = paired
        if cohort:
            items = [p for p in items if p.get("cohort") == cohort]
        vals = [p[key] for p in items if p[key] is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 3)

    clean = [p for p in paired if p.get("deterministic_s2") is True]
    return {
        "n": len(paired),
        "deterministic_correct_rate": rate("deterministic_correct"),
        "deterministic_correct_rate_clean_s2": (
            round(
                sum(1 for p in clean if p.get("deterministic_correct")) / len(clean), 3
            )
            if clean
            else None
        ),
        "adjudicated_correct_rate": rate("adjudicated_correct"),
        "adjudicated_correct_rate_exit": rate(
            "adjudicated_correct", cohort="exit"
        ),
        "adjudicated_correct_rate_non_exit": rate(
            "adjudicated_correct", cohort="non_exit"
        ),
        "ambiguous_rate": rate("ambiguous"),
        "structurally_contaminated_semantically_correct_count": sum(
            1
            for p in paired
            if p.get("structurally_contaminated_semantically_correct")
        ),
        "comparison_rows": paired,
    }


def merge_adjudication_into_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("all_samples") or payload.get("samples") or []
    adjs = adjudicate_replay_rows(rows)
    comparison = summarize_adjudicated_vs_deterministic(rows, adjudications=adjs)
    enriched = []
    for row, adj in zip(rows, adjs):
        enriched.append({**row, "adjudication": adj})
    out = dict(payload)
    out["adjudication_summary"] = comparison
    out["all_samples"] = enriched
    if "summary" in out and out["summary"].get("samples"):
        out["summary"]["samples"] = enriched
    return out
