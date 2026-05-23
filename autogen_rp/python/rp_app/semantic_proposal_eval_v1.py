"""Issue #243-B — offline semantic proposal evaluation (profile-scoped, observational only).

Deterministic evaluation over frozen corpus rows or audit-shaped dicts. **Not** runtime
authority; **not** on the #59 runtime-use allowlist.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Final

from semantic_eval_boundary_signals import (
    EXEC_DEPART,
    EXEC_RETURN,
    ROUND_TRIP,
    dorm_studio_boundary_signals,
)
from semantic_eval_legacy_f_codes import attach_legacy_lane
from semantic_eval_profiles import (
    DEFAULT_PROFILE_ID,
    SemanticEvalProfileRegistry,
    load_profile_registry,
    observational_eval_envelope,
    resolve_evaluation_profile,
)

SEMANTIC_PROPOSAL_EVAL_VERSION: Final[str] = "1"
PREDICATE_SEMANTIC_ALIGNMENT: Final[str] = "semantic_proposal.model_alignment_v1"

CORRECTED_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "success",
        "evaluator_defect",
        "contract_limited",
        "ambiguous_threshold",
        "true_semantic_miss",
    }
)

# Calibration anchor for final viability human adjudication (Issue #240 — not runtime truth)
FINAL_VIABILITY_HUMAN_ADJUDICATION: Final[dict[str, str]] = {
    "848_t3_celina_baseline": "no_covered_change",
    "853_t9_celina": "no_covered_change",
    "855_t3_ayame": "no_covered_change",
    "856_t3_celina": "no_covered_change",
    "856_t6_ayame": "no_covered_change",
    "856_t4_ayame": "no_covered_change",
    "856_t10_ayame": "no_covered_change",
    "856_t12_ayame": "no_covered_change",
    "857_t6_ayame": "no_covered_change",
    "857_t8_ayame": "no_covered_change",
}


@dataclass
class EvalCaseInput:
    case_id: str
    scenario_id: str
    beats_text: str
    semantic_decision: str
    proposals_emitted: list[str]
    overlay_applied: bool = False
    movement_cues: bool = False
    must_remain: bool = False
    human_adjudication_decision: str | None = None
    profile_id: str = DEFAULT_PROFILE_ID
    profile_resolution: str = "default"
    boundary_signals: dict[str, bool] = field(default_factory=dict)


def _beats_text_from_case(case: dict[str, Any]) -> str:
    bt = str(case.get("beats_text") or "").strip()
    if bt:
        return bt
    parts: list[str] = []
    for b in case.get("beats") or []:
        if isinstance(b, dict):
            parts.append(str(b.get("action") or ""))
            parts.append(str(b.get("dialogue") or ""))
    return " ".join(parts).strip()


def _semantic_decision_from_case(case: dict[str, Any]) -> str:
    if case.get("semantic_decision"):
        return str(case["semantic_decision"]).strip()
    ev = case.get("semantic_evaluation")
    if isinstance(ev, dict) and ev.get("decision"):
        return str(ev["decision"]).strip()
    return ""


def _proposals_from_case(case: dict[str, Any]) -> list[str]:
    props = case.get("proposals_emitted")
    if isinstance(props, list):
        return [str(p) for p in props]
    ev = case.get("semantic_evaluation")
    if isinstance(ev, dict):
        inner = ev.get("proposals")
        if isinstance(inner, list) and inner:
            out: list[str] = []
            for p in inner:
                if isinstance(p, dict):
                    kind = str(p.get("kind") or "")
                    op = str(p.get("operation") or "")
                    out.append(f"{kind}/{op}".strip("/"))
            return out
    return []


def corpus_case_to_eval_input(
    case: dict[str, Any],
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
) -> EvalCaseInput:
    reg = registry or load_profile_registry()
    scenario_id = str(case.get("scenario_id") or "").strip()
    profile_id, resolution = resolve_evaluation_profile(
        scenario_id,
        manifest_profile=(manifest_profiles or {}).get(scenario_id),
        registry=reg,
    )
    case_id = str(case.get("case_id") or "").strip()
    human = case.get("human_adjudication_decision")
    if human is None and case_id in FINAL_VIABILITY_HUMAN_ADJUDICATION:
        human = FINAL_VIABILITY_HUMAN_ADJUDICATION[case_id]
    must_remain = "willow" in scenario_id.lower() or "must_remain" in scenario_id.lower()
    signals: dict[str, bool] = {}
    if case.get("boundary_signals") and isinstance(case["boundary_signals"], dict):
        signals = {str(k): bool(v) for k, v in case["boundary_signals"].items()}
    return EvalCaseInput(
        case_id=case_id,
        scenario_id=scenario_id,
        beats_text=_beats_text_from_case(case),
        semantic_decision=_semantic_decision_from_case(case),
        proposals_emitted=_proposals_from_case(case),
        overlay_applied=bool(case.get("overlay_applied")),
        movement_cues=bool(case.get("movement_cues")),
        must_remain=must_remain,
        human_adjudication_decision=str(human).strip() if human else None,
        profile_id=profile_id,
        profile_resolution=resolution,
        boundary_signals=signals,
    )


def _judgment(
    *,
    case: EvalCaseInput,
    category: str,
    rationale: str,
    limitations: list[str],
    boundary_signals: dict[str, bool] | None = None,
    legacy_classifier_misflag: bool = False,
) -> dict[str, Any]:
    if category not in CORRECTED_CATEGORIES:
        raise ValueError(f"invalid corrected_category: {category!r}")
    lim = list(limitations)
    profile = load_profile_registry().get_profile(case.profile_id)
    for pl in profile.limitations:
        if pl not in lim:
            lim.append(pl)
    if profile.placeholder:
        lim.append("profile_placeholder: scoring rules may be incomplete")
    return observational_eval_envelope(
        predicate_id=PREDICATE_SEMANTIC_ALIGNMENT,
        eval_version=SEMANTIC_PROPOSAL_EVAL_VERSION,
        profile_id=case.profile_id,
        profile_resolution=case.profile_resolution,
        case_id=case.case_id,
        scenario_id=case.scenario_id,
        semantic_decision=case.semantic_decision,
        corrected_category=category,
        rationale=rationale,
        limitations=lim,
        boundary_signals=boundary_signals or {},
        legacy_classifier_misflag=legacy_classifier_misflag,
        overlay_applied=case.overlay_applied,
    )


def _evaluate_generic_net_state(case: EvalCaseInput, signals: dict[str, bool]) -> dict[str, Any]:
    decision = case.semantic_decision
    props = case.proposals_emitted
    limitations = [
        "generic_net_state_v1: no dorm/studio ontology heuristics applied",
    ]

    if case.human_adjudication_decision and decision == case.human_adjudication_decision:
        return _judgment(
            case=case,
            category="success",
            rationale="Model semantic_decision matches frozen human adjudication calibration anchor.",
            limitations=limitations
            + ["human_adjudication_calibration_anchor: not runtime authority"],
            boundary_signals=signals,
        )

    if decision == "covered_change" and not props:
        return _judgment(
            case=case,
            category="true_semantic_miss",
            rationale="covered_change without proposals.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if signals.get("round_trip_same_turn") and decision == "no_covered_change":
        return _judgment(
            case=case,
            category="contract_limited",
            rationale="Same-turn round-trip; net state unchanged; open+close illegal.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if (
        signals.get("exec_depart")
        and not signals.get("exec_return")
        and decision == "no_covered_change"
    ):
        if case.overlay_applied:
            return _judgment(
                case=case,
                category="ambiguous_threshold",
                rationale="Executed departure cues with overlay; threshold judgment may vary.",
                limitations=limitations + ["overlay_pressure_may_conflict_with_net_state_legality"],
                boundary_signals=signals,
            )
        return _judgment(
            case=case,
            category="ambiguous_threshold",
            rationale="Executed departure cues without overlay; threshold judgment may vary.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if decision == "covered_change" and props:
        return _judgment(
            case=case,
            category="success",
            rationale="Honest covered_change with proposals.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if decision == "no_covered_change":
        return _judgment(
            case=case,
            category="success",
            rationale="no_covered_change; generic profile finds no net-state violation.",
            limitations=limitations,
            boundary_signals=signals,
        )

    return _judgment(
        case=case,
        category="ambiguous_threshold",
        rationale="Insufficient or non-standard semantic decision for generic evaluation.",
        limitations=limitations,
        boundary_signals=signals,
    )


def _evaluate_dorm_studio(case: EvalCaseInput, signals: dict[str, bool]) -> dict[str, Any]:
    decision = case.semantic_decision
    limitations = [
        "dorm_studio_single_space: calibrated for single-space dorm/studio topology only",
        "does_not_infer_profile_from_prose; scenario binding required",
    ]

    if (
        case.human_adjudication_decision
        and decision == case.human_adjudication_decision
    ):
        return _judgment(
            case=case,
            category="success",
            rationale="Model semantic_decision matches frozen human adjudication calibration anchor.",
            limitations=limitations
            + ["human_adjudication_calibration_anchor: not runtime authority"],
            boundary_signals=signals,
        )

    if decision == "covered_change" and not case.proposals_emitted:
        return _judgment(
            case=case,
            category="true_semantic_miss",
            rationale="covered_change without proposals.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if signals.get("round_trip_same_turn") and decision == "no_covered_change":
        return _judgment(
            case=case,
            category="contract_limited",
            rationale="Same-turn round-trip; net state unchanged; open+close illegal.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if (signals.get("in_room_only") or signals.get("info_boundary_only")) and decision == "no_covered_change":
        return _judgment(
            case=case,
            category="success",
            rationale="In-room repositioning or informational boundary mention; no durable net-state transition.",
            limitations=limitations,
            boundary_signals=signals,
            legacy_classifier_misflag=True,
        )

    if signals.get("participation_choreography_boundary_adjacent") and decision == "no_covered_change":
        lim = limitations + [
            "participation_choreography_boundary_adjacent: doorway/corridor movement — threshold preserved",
        ]
        if case.overlay_applied:
            lim.append("overlay_pressure_may_conflict_with_net_state_legality")
        return _judgment(
            case=case,
            category="ambiguous_threshold",
            rationale="Boundary-adjacent participation movement; threshold may vary under departure or overlay cues.",
            limitations=lim,
            boundary_signals=signals,
        )

    if (
        signals.get("participation_choreography")
        and decision == "no_covered_change"
        and not signals.get("exec_depart")
    ):
        return _judgment(
            case=case,
            category="success",
            rationale="In-focal participation choreography; conservative no_covered_change coherent.",
            limitations=limitations
            + ["participation_choreography_safe: not durable excursion/off_focal commit"],
            boundary_signals=signals,
        )

    if (
        signals.get("exec_depart")
        and not signals.get("exec_return")
        and not signals.get("in_room_only")
        and not signals.get("info_boundary_only")
        and not signals.get("round_trip_same_turn")
        and decision == "no_covered_change"
    ):
        lim = list(limitations)
        if case.overlay_applied:
            lim.append("overlay_pressure_may_conflict_with_net_state_legality")
        return _judgment(
            case=case,
            category="ambiguous_threshold",
            rationale="Executed departure cues without dorm-safe in-room/info/round-trip signal; threshold may vary.",
            limitations=lim,
            boundary_signals=signals,
        )

    if (
        case.overlay_applied
        and case.movement_cues
        and not any(
            signals.get(k)
            for k in (
                "exec_depart",
                "exec_return",
                "round_trip_same_turn",
                "in_room_only",
                "info_boundary_only",
                "participation_choreography",
                "participation_choreography_boundary_adjacent",
            )
        )
        and decision == "no_covered_change"
    ):
        return _judgment(
            case=case,
            category="ambiguous_threshold",
            rationale="Gradual participation movement cues with overlay; threshold disagreement may remain.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if decision == "no_covered_change":
        return _judgment(
            case=case,
            category="success",
            rationale="Honest no_covered_change under dorm/studio ontology.",
            limitations=limitations,
            boundary_signals=signals,
        )

    if decision == "covered_change" and case.proposals_emitted:
        return _judgment(
            case=case,
            category="success",
            rationale="Honest covered_change with proposals.",
            limitations=limitations,
            boundary_signals=signals,
        )

    return _judgment(
        case=case,
        category="ambiguous_threshold",
        rationale="Dorm/studio profile could not classify decisively.",
        limitations=limitations,
        boundary_signals=signals,
    )


def _evaluate_multi_room_stub(case: EvalCaseInput, signals: dict[str, bool]) -> dict[str, Any]:
    return _judgment(
        case=case,
        category="ambiguous_threshold",
        rationale="multi_room_excursion_v1 is a stub profile; no mature scoring rules.",
        limitations=[
            "multi_room_excursion_v1: placeholder only — do not treat as pass/fail verdict",
            "future work must validate against Tier B / excursion scenarios before maturity",
        ],
        boundary_signals=signals,
    )


def _generic_boundary_signals(beats: str) -> dict[str, bool]:
    """Net-state-only signals for generic profile (depart/return/round-trip only)."""
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


def evaluate_case(
    case: EvalCaseInput,
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    raw_case: dict[str, Any] | None = None,
    legacy_replay: bool = False,
) -> dict[str, Any]:
    reg = registry or load_profile_registry()
    _ = reg.get_profile(case.profile_id)
    beats = case.beats_text
    if case.profile_id == "multi_room_excursion_v1":
        judgment = _evaluate_multi_room_stub(case, _generic_boundary_signals(beats))
    elif case.profile_id == "dorm_studio_single_space":
        judgment = _evaluate_dorm_studio(case, dorm_studio_boundary_signals(beats))
    else:
        judgment = _evaluate_generic_net_state(case, _generic_boundary_signals(beats))
    source = raw_case if isinstance(raw_case, dict) else {
        "case_id": case.case_id,
        "scenario_id": case.scenario_id,
        "beats_text": case.beats_text,
        "semantic_decision": case.semantic_decision,
        "proposals_emitted": case.proposals_emitted,
        "overlay_applied": case.overlay_applied,
        "boundary_signals": case.boundary_signals,
    }
    return attach_legacy_lane(
        judgment,
        case=source,
        beats_text=beats,
        profile_id=case.profile_id,
        overlay_applied=case.overlay_applied,
        has_proposals=bool(case.proposals_emitted),
        boundary_signals=judgment.get("boundary_signals"),
        legacy_replay=legacy_replay,
    )


def evaluate_corpus(
    corpus: dict[str, Any],
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
    legacy_replay: bool = False,
) -> dict[str, Any]:
    reg = registry or load_profile_registry()
    judgments: list[dict[str, Any]] = []
    for raw_case in corpus.get("cases") or []:
        if not isinstance(raw_case, dict):
            continue
        inp = corpus_case_to_eval_input(raw_case, registry=reg, manifest_profiles=manifest_profiles)
        judgments.append(
            evaluate_case(inp, registry=reg, raw_case=raw_case, legacy_replay=legacy_replay)
        )
    cats = Counter(j["corrected_category"] for j in judgments)
    legacy_counts = Counter(
        (j.get("legacy_lane") or {}).get("legacy_f_code")
        for j in judgments
        if (j.get("legacy_lane") or {}).get("legacy_f_code")
    )
    envelope = observational_eval_envelope(
        schema_version="semantic_proposal_eval_report_v1",
        issue=243,
        phase="243-C",
        eval_version=SEMANTIC_PROPOSAL_EVAL_VERSION,
        corpus_schema_version=str(corpus.get("schema_version") or ""),
        case_count=len(judgments),
        corrected_category_counts=dict(cats),
        legacy_f_code_counts=dict(legacy_counts),
        legacy_lane_note=(
            "legacy_f_codes are investigation-era taxonomy nested under legacy_lane — "
            "corrected_category is primary"
        ),
        judgments=judgments,
    )
    return envelope


def model_alignment_success(judgment: dict[str, Any]) -> bool:
    return judgment.get("corrected_category") == "success"
