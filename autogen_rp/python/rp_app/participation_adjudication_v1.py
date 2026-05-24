"""Issue #246 — offline participation suspicion adjudication (observational only).

Builds compact adjudication bundles, runs mock/human/LLM adjudicators, and
produces reporting summaries. **Not** runtime authority; **not** on #59 allowlist.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Final

from participation_suspicion_extract import (
    ParticipationSuspicionRecord,
    make_suspicion_id,
)
from semantic_eval_profiles import observational_eval_envelope

INPUT_SCHEMA: Final[str] = "participation_adjudication_input.v1"
OUTPUT_SCHEMA: Final[str] = "participation_adjudication.v1"
PROMPT_VERSION: Final[str] = "participation_adjudication_prompt_v1"

OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "flagged",
        "adjudicated_failure",
        "adjudicated_non_failure",
        "ambiguous_or_unresolved",
        "needs_human_review",
    }
)

TERMINAL_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "adjudicated_failure",
        "adjudicated_non_failure",
        "ambiguous_or_unresolved",
        "needs_human_review",
    }
)

ADJUDICATOR_KINDS: Final[frozenset[str]] = frozenset(
    {"human", "llm", "deterministic_policy"}
)

DEFAULT_LIMITATIONS: Final[tuple[str, ...]] = (
    "observational_only: not runtime authority",
    "report_survival_not_runtime_truth",
    "confidence_is_reporting_confidence_only",
    "human_calibration_anchor: not canonical semantic truth",
)

# Phase 0 manual review anchors (#227 25-case corpus)
CALIBRATION_ANCHORS: Final[dict[str, str]] = {
    "899:7:Willow_Reeves:P03": "adjudicated_failure",  # case 11
    "899:9:Willow_Reeves:P04": "adjudicated_failure",  # case 12
    "902:7:Hannah_Lovelace:P03": "adjudicated_failure",  # case 15
    "901:9:Willow_Reeves:P04": "ambiguous_or_unresolved",  # case 13
    "902:3:Hannah_Lovelace:P01": "ambiguous_or_unresolved",  # case 14
    "907:7:Celina:P03": "ambiguous_or_unresolved",  # case 24
}

WEAKENED_SUSPICION_IDS: Final[frozenset[str]] = frozenset(
    {
        "901:9:Willow_Reeves:P04",
        "902:3:Hannah_Lovelace:P01",
        "907:7:Celina:P03",
    }
)


@dataclass
class AdjudicationInputBundle:
    schema_version: str = INPUT_SCHEMA
    suspicion_id: str = ""
    probe_instruction: str = ""
    active_scene_focus_excerpt: str = ""
    participation_arc_excerpt: str = ""
    scene_topology_excerpt: str = ""
    beats_excerpt: str = ""
    semantic_output_summary: dict[str, Any] = field(default_factory=dict)
    committed_state_delta: dict[str, Any] = field(default_factory=dict)
    false_positive_class_hints: list[str] = field(default_factory=list)
    human_seed_label: str | None = None


@dataclass
class AdjudicationRecord:
    schema_version: str = OUTPUT_SCHEMA
    suspicion_id: str = ""
    adjudication_outcome: str = "flagged"
    adjudication_confidence: str = "medium"
    adjudication_rationale: str = ""
    adjudicator_kind: str = "deterministic_policy"
    adjudicator_model: str | None = None
    adjudicator_prompt_version: str | None = None
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_LIMITATIONS))
    provenance: dict[str, Any] = field(default_factory=dict)
    human_calibration_anchor: bool = False


def _truncate(text: str, limit: int) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _false_positive_hints(rec: ParticipationSuspicionRecord) -> list[str]:
    hints: list[str] = []
    cf = rec.cohesion_flags or {}
    df = rec.deterministic_flags or {}
    if cf.get("F_tether_cue"):
        hints.append("tethered_speech_topology")
    if cf.get("F_in_room_focus") and not cf.get("F_fiction_roster_drift"):
        hints.append("in_room_relocation_not_exit")
    if cf.get("F_rebound_cue"):
        hints.append("rebound_without_departure")
    if df.get("F_context_drift"):
        hints.append("context_drift_without_offstage")
    if not hints:
        hints.append("topology_sensitive_c3")
    return hints


def build_adjudication_bundle(
    suspicion: ParticipationSuspicionRecord,
    *,
    row: dict[str, Any] | None = None,
    human_seed_label: str | None = None,
) -> AdjudicationInputBundle:
    row = row or {}
    arc = row.get("participation_arc_lines") or []
    arc_text = "\n".join(f"- {line}" for line in arc[-2:]) if arc else ""
    beats = f"{row.get('beats_action_text') or ''}\n{row.get('beats_dialogue_text') or ''}".strip()
    if not beats and row:
        beats = _truncate(str(row.get("beats_excerpt") or ""), 1200)
    topology_parts = [
        f"probe={suspicion.probe_id}",
        f"transition={suspicion.transition_type}",
        f"constraint={suspicion.scene_snapshot_before.get('target_presence_constraint')}",
        f"present={suspicion.scene_snapshot_after.get('present_characters')}",
        f"offstage={suspicion.scene_snapshot_after.get('offstage_characters')}",
    ]
    return AdjudicationInputBundle(
        suspicion_id=suspicion.suspicion_id,
        probe_instruction=_truncate(suspicion.effective_user_trigger, 400),
        active_scene_focus_excerpt=_truncate(
            str(row.get("active_focus_position") or row.get("active_scene_focus_excerpt") or ""),
            800,
        ),
        participation_arc_excerpt=_truncate(arc_text, 400),
        scene_topology_excerpt=_truncate(" · ".join(topology_parts), 600),
        beats_excerpt=_truncate(beats, 1200),
        semantic_output_summary={
            "semantic_decision": suspicion.semantic_decision,
            "proposal_count": suspicion.proposal_count,
            "spd_authority_outcome": suspicion.spd_authority_outcome,
            "deterministic_flags": suspicion.deterministic_flags,
            "cohesion_flags": suspicion.cohesion_flags,
        },
        committed_state_delta={
            "before": suspicion.scene_snapshot_before,
            "after": suspicion.scene_snapshot_after,
        },
        false_positive_class_hints=_false_positive_hints(suspicion),
        human_seed_label=human_seed_label,
    )


def _policy_outcome(
    suspicion: ParticipationSuspicionRecord,
    *,
    corpus_outcome: str | None = None,
) -> tuple[str, str, str]:
    """Return (outcome, confidence, rationale) for deterministic policy mode."""
    if corpus_outcome:
        return (
            corpus_outcome,
            "high",
            f"Frozen calibration anchor outcome={corpus_outcome}",
        )
    if suspicion.suspicion_id in WEAKENED_SUSPICION_IDS:
        return (
            "ambiguous_or_unresolved",
            "medium",
            "Weakened seed case — preserve ambiguity per #246 consensus",
        )
    hints = _false_positive_hints(suspicion)
    cf = suspicion.cohesion_flags or {}
    if cf.get("F_tether_cue") or (
        cf.get("F_in_room_focus") and not cf.get("F_fiction_roster_drift")
    ):
        return (
            "adjudicated_non_failure",
            "high",
            "Topology-sensitive participation — deterministic C3 likely false positive",
        )
    if cf.get("F_rebound_cue"):
        return (
            "ambiguous_or_unresolved",
            "medium",
            "Rebound movement without clear departure — ambiguous threshold",
        )
    return (
        "ambiguous_or_unresolved",
        "low",
        "No calibration anchor — insufficient policy signal; preserve ambiguity",
    )


def adjudicate_suspicion(
    suspicion: ParticipationSuspicionRecord,
    bundle: AdjudicationInputBundle,
    *,
    mode: str = "mock",
    corpus_lookup: dict[str, str] | None = None,
    llm_fn: Callable[[AdjudicationInputBundle], AdjudicationRecord] | None = None,
    extract_run_id: str = "",
) -> AdjudicationRecord:
    corpus = corpus_lookup or CALIBRATION_ANCHORS
    anchor_outcome = corpus.get(suspicion.suspicion_id)
    is_anchor = anchor_outcome is not None or suspicion.suspicion_id in CALIBRATION_ANCHORS

    if mode == "human":
        return AdjudicationRecord(
            suspicion_id=suspicion.suspicion_id,
            adjudication_outcome=anchor_outcome or "needs_human_review",
            adjudication_confidence="medium",
            adjudication_rationale="Human-only mode — awaiting operator adjudication",
            adjudicator_kind="human",
            human_calibration_anchor=is_anchor,
            provenance=_provenance(extract_run_id),
        )

    if mode == "llm":
        if llm_fn is None:
            raise ValueError("LLM mode requires llm_fn adapter")
        rec = llm_fn(bundle)
        rec.suspicion_id = suspicion.suspicion_id
        rec.adjudicator_kind = "llm"
        rec.human_calibration_anchor = is_anchor
        if rec.adjudication_confidence == "low":
            rec.adjudication_outcome = "needs_human_review"
        if not rec.provenance:
            rec.provenance = _provenance(extract_run_id)
        return rec

    # mock / deterministic_policy (default CI path)
    outcome, confidence, rationale = _policy_outcome(
        suspicion, corpus_outcome=anchor_outcome
    )
    return AdjudicationRecord(
        suspicion_id=suspicion.suspicion_id,
        adjudication_outcome=outcome,
        adjudication_confidence=confidence,
        adjudication_rationale=rationale,
        adjudicator_kind="deterministic_policy",
        adjudicator_prompt_version=PROMPT_VERSION,
        human_calibration_anchor=is_anchor,
        provenance=_provenance(extract_run_id),
    )


def _provenance(extract_run_id: str) -> dict[str, Any]:
    return {
        "extract_run_id": extract_run_id,
        "adjudicated_at": datetime.now(timezone.utc).isoformat(),
        "issue": "246",
    }


def adjudicate_suspicions(
    suspicions: list[ParticipationSuspicionRecord],
    *,
    row_lookup: dict[str, dict[str, Any]] | None = None,
    mode: str = "mock",
    corpus_lookup: dict[str, str] | None = None,
    llm_fn: Callable[[AdjudicationInputBundle], AdjudicationRecord] | None = None,
    extract_run_id: str = "",
) -> list[AdjudicationRecord]:
    records: list[AdjudicationRecord] = []
    lookup = row_lookup or {}
    for suspicion in suspicions:
        row = lookup.get(suspicion.suspicion_id, {})
        bundle = build_adjudication_bundle(
            suspicion,
            row=row,
            human_seed_label=(corpus_lookup or CALIBRATION_ANCHORS).get(suspicion.suspicion_id),
        )
        records.append(
            adjudicate_suspicion(
                suspicion,
                bundle,
                mode=mode,
                corpus_lookup=corpus_lookup,
                llm_fn=llm_fn,
                extract_run_id=extract_run_id,
            )
        )
    return records


def summarize_adjudication_report(
    suspicions: list[ParticipationSuspicionRecord],
    adjudications: list[AdjudicationRecord],
) -> dict[str, Any]:
    by_id = {a.suspicion_id: a for a in adjudications}
    raw = len(suspicions)
    pending = sum(1 for s in suspicions if by_id.get(s.suspicion_id, AdjudicationRecord()).adjudication_outcome == "flagged")
    outcome_counts = {k: 0 for k in TERMINAL_OUTCOMES}
    review_modes = {k: 0 for k in ADJUDICATOR_KINDS}
    for adj in adjudications:
        oc = adj.adjudication_outcome
        if oc in outcome_counts:
            outcome_counts[oc] += 1
        if adj.adjudicator_kind in review_modes and oc in TERMINAL_OUTCOMES:
            review_modes[adj.adjudicator_kind] += 1
    adjudicated_total = sum(outcome_counts.values())
    return observational_eval_envelope(
        schema_version="participation_adjudication_summary.v1",
        raw_deterministic_suspicion_count=raw,
        adjudication_pending_count=pending,
        adjudicated_total_count=adjudicated_total,
        adjudicated_failure_count=outcome_counts["adjudicated_failure"],
        adjudicated_non_failure_count=outcome_counts["adjudicated_non_failure"],
        ambiguous_or_unresolved_count=outcome_counts["ambiguous_or_unresolved"],
        needs_human_review_count=outcome_counts["needs_human_review"],
        human_reviewed_count=review_modes["human"],
        llm_reviewed_count=review_modes["llm"],
        deterministic_policy_reviewed_count=review_modes["deterministic_policy"],
        validation_failure_metric="adjudicated_failure_count",
    )


def merge_adjudication_into_cohesion_summary(
    base_summary: dict[str, Any],
    adjudication_report: dict[str, Any],
) -> dict[str, Any]:
    """Attach adjudication tallies alongside raw rubric counts."""
    merged = dict(base_summary)
    merged["adjudication_report"] = adjudication_report
    merged["validation_failure_count"] = adjudication_report.get("adjudicated_failure_count", 0)
    merged["raw_c3_suspicion_count"] = adjudication_report.get(
        "raw_deterministic_suspicion_count", 0
    )
    return merged


def write_adjudication_jsonl(records: list[AdjudicationRecord], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def load_corpus_outcomes(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for case in data.get("cases") or []:
        if not isinstance(case, dict):
            continue
        sid = str(case.get("suspicion_id") or "").strip()
        outcome = str(case.get("calibration_outcome") or "").strip()
        if sid and outcome:
            out[sid] = outcome
    return out


def row_lookup_from_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sid = make_suspicion_id(
            audit_session_number=row.get("audit_session_number"),
            turn_number=row.get("turn_number"),
            actor=str(row.get("actor") or ""),
            probe_id=row.get("probe_id"),
        )
        lookup[sid] = row
    return lookup
