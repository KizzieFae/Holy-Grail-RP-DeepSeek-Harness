"""Issue #246 — frozen cohesion adjudication corpus regression (offline only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from participation_adjudication_v1 import (
    CALIBRATION_ANCHORS,
    adjudicate_suspicions,
    summarize_adjudication_report,
)
from participation_suspicion_extract import extract_suspicions_from_jsonl

ISSUE246_CORPUS_SCHEMA: Final[str] = "issue246_adjudication_corpus_v1"
ISSUE246_BASELINE_SCHEMA: Final[str] = "issue246_adjudication_baseline_v1"
ISSUE246_REPORT_SCHEMA: Final[str] = "issue246_adjudication_regression_report_v1"

_DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_CORPUS = _DATA_ROOT / "issue227" / "adjudication_corpus_cohesion_v1.json"
_DEFAULT_BASELINES_DIR = _DATA_ROOT / "evaluation" / "issue246_regression_baselines"


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    suspicion_id: str
    calibration_outcome: str
    case_class: str
    audit_session_number: int | None
    probe_id: str | None
    actor: str


def default_corpus_path() -> Path:
    return _DEFAULT_CORPUS


def default_baselines_dir() -> Path:
    return _DEFAULT_BASELINES_DIR


def load_frozen_corpus(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if str(raw.get("schema_version") or "") != ISSUE246_CORPUS_SCHEMA:
        raise ValueError(f"unsupported corpus schema in {path}")
    return raw


def corpus_outcome_map(corpus: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = dict(CALIBRATION_ANCHORS)
    for case in corpus.get("cases") or []:
        if not isinstance(case, dict):
            continue
        sid = str(case.get("suspicion_id") or "").strip()
        outcome = str(case.get("calibration_outcome") or "").strip()
        if sid and outcome:
            out[sid] = outcome
    return out


def evaluate_corpus(
    corpus_path: Path,
    *,
    jsonl_sources: list[Path] | None = None,
) -> dict[str, Any]:
    corpus = load_frozen_corpus(corpus_path)
    outcomes = corpus_outcome_map(corpus)
    sources = jsonl_sources or [Path(p) for p in corpus.get("jsonl_sources") or []]
    suspicions = []
    for src in sources:
        if src.is_file():
            suspicions.extend(extract_suspicions_from_jsonl(src))
    # Filter to corpus cases only for regression
    corpus_ids = {str(c.get("suspicion_id")) for c in corpus.get("cases") or [] if c.get("suspicion_id")}
    filtered = [s for s in suspicions if s.suspicion_id in corpus_ids]
    adjudications = adjudicate_suspicions(filtered, mode="mock", corpus_lookup=outcomes)
    summary = summarize_adjudication_report(filtered, adjudications)
    mismatches: list[dict[str, str]] = []
    by_id = {a.suspicion_id: a for a in adjudications}
    for case in corpus.get("cases") or []:
        sid = str(case.get("suspicion_id") or "")
        expected = str(case.get("calibration_outcome") or "")
        actual = by_id.get(sid)
        if actual is None:
            mismatches.append({"suspicion_id": sid, "expected": expected, "actual": "missing"})
            continue
        if actual.adjudication_outcome != expected:
            mismatches.append(
                {
                    "suspicion_id": sid,
                    "expected": expected,
                    "actual": actual.adjudication_outcome,
                }
            )
    return {
        "schema_version": ISSUE246_REPORT_SCHEMA,
        "corpus_path": str(corpus_path),
        "case_count": len(corpus.get("cases") or []),
        "suspicion_count": len(filtered),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "summary": summary,
        "passed": len(mismatches) == 0,
    }


def run_regression(corpus_path: Path, baseline_path: Path) -> dict[str, Any]:
    report = evaluate_corpus(corpus_path)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    expected_failures = int(baseline.get("adjudicated_failure_count", 0))
    actual_failures = int(report["summary"].get("adjudicated_failure_count", 0))
    baseline_pass = expected_failures == actual_failures
    report["baseline_path"] = str(baseline_path)
    report["baseline_adjudicated_failure_count"] = expected_failures
    report["passed"] = report["passed"] and baseline_pass
    if not baseline_pass:
        report.setdefault("mismatches", []).append(
            {
                "field": "adjudicated_failure_count",
                "expected": str(expected_failures),
                "actual": str(actual_failures),
            }
        )
        report["mismatch_count"] = len(report.get("mismatches") or [])
    return report
