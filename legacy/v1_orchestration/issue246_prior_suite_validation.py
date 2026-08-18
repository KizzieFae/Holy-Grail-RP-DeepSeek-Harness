"""Issue #246 — prior-suite re-analysis validation against #227 manual adjudication."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from participation_adjudication_v1 import (
    adjudicate_suspicions,
    build_adjudication_bundle,
    row_lookup_from_jsonl,
    summarize_adjudication_report,
)
from participation_suspicion_extract import (
    make_suspicion_id,
    row_dict_to_suspicion,
    suspicions_from_row_dicts,
)

MANUAL_REFERENCE_SCHEMA: Final[str] = "issue227_manual_adjudication_reference_v1"
PRIOR_SUITE_REPORT_SCHEMA: Final[str] = "issue246_prior_suite_validation_report_v1"

_DATA_ROOT = Path(__file__).resolve().parent / "data"
_DEFAULT_REFERENCE = _DATA_ROOT / "issue227" / "manual_adjudication_reference_v1.json"
_DEFAULT_JSONL_ROOT = _DATA_ROOT.parent / "validation_runs"


@dataclass(frozen=True)
class ManualReferenceCase:
    case_id: str
    session: int
    probe_id: str
    actor: str
    turn: int
    deterministic_rubric: str
    manual_case_class: str
    manual_expected_outcome: str
    notes: str

    @property
    def suspicion_id(self) -> str:
        return make_suspicion_id(
            audit_session_number=self.session,
            turn_number=self.turn,
            actor=self.actor,
            probe_id=self.probe_id,
        )


def default_reference_path() -> Path:
    return _DEFAULT_REFERENCE


def load_manual_reference(path: Path | None = None) -> dict[str, Any]:
    p = path or _DEFAULT_REFERENCE
    raw = json.loads(p.read_text(encoding="utf-8"))
    if str(raw.get("schema_version") or "") != MANUAL_REFERENCE_SCHEMA:
        raise ValueError(f"unsupported manual reference schema in {p}")
    return raw


def parse_reference_cases(raw: dict[str, Any]) -> list[ManualReferenceCase]:
    out: list[ManualReferenceCase] = []
    for case in raw.get("cases") or []:
        if not isinstance(case, dict):
            continue
        out.append(
            ManualReferenceCase(
                case_id=str(case.get("case_id") or ""),
                session=int(case["session"]),
                probe_id=str(case.get("probe_id") or ""),
                actor=str(case.get("actor") or ""),
                turn=int(case["turn"]),
                deterministic_rubric=str(case.get("deterministic_rubric") or ""),
                manual_case_class=str(case.get("manual_case_class") or ""),
                manual_expected_outcome=str(case.get("manual_expected_outcome") or ""),
                notes=str(case.get("notes") or ""),
            )
        )
    return out


def _load_all_jsonl_rows(jsonl_root: Path | None = None) -> dict[str, dict[str, Any]]:
    root = jsonl_root or _DEFAULT_JSONL_ROOT
    lookup: dict[str, dict[str, Any]] = {}
    paths = sorted(root.glob("willow_departure_*.jsonl")) + sorted(
        (root / "cohesion_slate").glob("*.jsonl")
    )
    for path in paths:
        if path.is_file():
            lookup.update(row_lookup_from_jsonl(path))
    return lookup


def _classify_mismatch(
    manual: ManualReferenceCase,
    *,
    actual: str | None,
    suspicion_emitted: bool,
) -> str:
    if manual.manual_expected_outcome == "no_suspicion_emitted":
        if suspicion_emitted:
            return "implementation_defect"
        return "agreement"
    if not suspicion_emitted:
        return "implementation_defect"
    if actual == manual.manual_expected_outcome:
        return "agreement"
    if manual.manual_case_class == "weakened":
        if actual in ("ambiguous_or_unresolved", "needs_human_review"):
            return "legitimate_ambiguity"
    if manual.manual_case_class == "true_miss" and actual == "ambiguous_or_unresolved":
        return "adjudicator_policy_gap"
    if manual.manual_case_class == "false_positive_topology" and actual == "adjudicated_failure":
        return "adjudicator_policy_gap"
    return "adjudicator_policy_gap"


def run_prior_suite_validation(
    *,
    reference_path: Path | None = None,
    jsonl_root: Path | None = None,
    mode: str = "mock",
    use_manual_as_corpus: bool = True,
) -> dict[str, Any]:
    raw = load_manual_reference(reference_path)
    cases = parse_reference_cases(raw)
    row_lookup = _load_all_jsonl_rows(jsonl_root)

    manual_outcome_map = {
        c.suspicion_id: c.manual_expected_outcome
        for c in cases
        if c.manual_expected_outcome not in ("no_suspicion_emitted",)
    }
    corpus_lookup = manual_outcome_map if use_manual_as_corpus else None

    comparisons: list[dict[str, Any]] = []
    suspicions = []
    c3_cases = [c for c in cases if c.manual_expected_outcome != "no_suspicion_emitted"]

    for manual in cases:
        row = row_lookup.get(manual.suspicion_id)
        suspicion = row_dict_to_suspicion(row) if row else None
        actual_outcome: str | None = None
        if manual.manual_expected_outcome == "no_suspicion_emitted":
            matches = suspicion is None
            disposition = "agreement" if matches else "implementation_defect"
            comparisons.append(
                {
                    "case_id": manual.case_id,
                    "suspicion_id": manual.suspicion_id,
                    "deterministic_rubric": manual.deterministic_rubric,
                    "manual_expected_outcome": manual.manual_expected_outcome,
                    "new_adjudication_outcome": None,
                    "suspicion_emitted": suspicion is not None,
                    "agreement": matches,
                    "mismatch_disposition": disposition,
                    "mismatch_reason": (
                        "C3 suspicion emitted for non-C3 control case"
                        if suspicion
                        else "No suspicion emitted as expected"
                    ),
                    "manual_case_class": manual.manual_case_class,
                    "notes": manual.notes,
                }
            )
            continue

        if suspicion is None:
            comparisons.append(
                {
                    "case_id": manual.case_id,
                    "suspicion_id": manual.suspicion_id,
                    "deterministic_rubric": manual.deterministic_rubric,
                    "manual_expected_outcome": manual.manual_expected_outcome,
                    "new_adjudication_outcome": None,
                    "suspicion_emitted": False,
                    "agreement": False,
                    "mismatch_disposition": "implementation_defect",
                    "mismatch_reason": "Expected C3 suspicion row missing from extract",
                    "manual_case_class": manual.manual_case_class,
                    "notes": manual.notes,
                }
            )
            continue

        suspicions.append(suspicion)

    adjudications = adjudicate_suspicions(
        suspicions,
        row_lookup=row_lookup,
        mode=mode,
        corpus_lookup=corpus_lookup,
    )
    adj_by_id = {a.suspicion_id: a for a in adjudications}

    for manual in c3_cases:
        if manual.suspicion_id not in adj_by_id:
            continue
        adj = adj_by_id[manual.suspicion_id]
        actual_outcome = adj.adjudication_outcome
        disposition = _classify_mismatch(
            manual,
            actual=actual_outcome,
            suspicion_emitted=True,
        )
        comparisons.append(
            {
                "case_id": manual.case_id,
                "suspicion_id": manual.suspicion_id,
                "deterministic_rubric": manual.deterministic_rubric,
                "manual_expected_outcome": manual.manual_expected_outcome,
                "new_adjudication_outcome": actual_outcome,
                "suspicion_emitted": True,
                "agreement": disposition == "agreement",
                "mismatch_disposition": disposition,
                "mismatch_reason": (
                    "Matches manual calibration anchor"
                    if disposition == "agreement"
                    else f"Expected {manual.manual_expected_outcome}, got {actual_outcome}"
                ),
                "manual_case_class": manual.manual_case_class,
                "notes": manual.notes,
            }
        )

    comparisons.sort(key=lambda x: int(x["case_id"]))
    agreement_count = sum(1 for c in comparisons if c["agreement"])
    mismatch_count = len(comparisons) - agreement_count
    summary = summarize_adjudication_report(suspicions, adjudications)

    priority_cases = {
        c["case_id"]: c
        for c in comparisons
        if c["case_id"] in ("11", "12", "15")
    }

    return {
        "schema_version": PRIOR_SUITE_REPORT_SCHEMA,
        "reference_path": str(reference_path or _DEFAULT_REFERENCE),
        "mode": mode,
        "use_manual_as_corpus": use_manual_as_corpus,
        "total_cases_analyzed": len(comparisons),
        "agreement_count": agreement_count,
        "mismatch_count": mismatch_count,
        "agreement_rate": round(agreement_count / len(comparisons), 4) if comparisons else 0.0,
        "summary_metrics": summary,
        "priority_cases_11_12_15": priority_cases,
        "comparisons": comparisons,
        "passed": mismatch_count == 0,
        "limitations": list(raw.get("limitations") or []),
    }
