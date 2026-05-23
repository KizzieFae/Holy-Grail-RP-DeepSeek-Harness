"""Issue #243-A — frozen corpus load, baseline format, and diff mechanics (offline only).

Compares **calibration labels** already present in frozen #240 corpora against committed
regression baselines. Does **not** run semantic scoring engines or touch runtime paths.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from semantic_eval_profiles import (
    SemanticEvalProfileRegistry,
    load_profile_registry,
    observational_eval_envelope,
    resolve_evaluation_profile,
)

ISSUE243_REGRESSION_BASELINE_SCHEMA: Final[str] = "issue243_regression_baseline_v1"
ISSUE243_REGRESSION_REPORT_SCHEMA: Final[str] = "issue243_regression_report_v1"
ISSUE243_EVAL_BASELINE_SCHEMA: Final[str] = "issue243_eval_baseline_v1"
ISSUE243_EVAL_REPORT_SCHEMA: Final[str] = "issue243_eval_regression_report_v1"

KNOWN_CORPUS_SCHEMAS: Final[frozenset[str]] = frozenset(
    {
        "issue240_adjudication_corpus_v1",
        "issue240_final_viability_corpus_v1",
    }
)

_DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_BASELINES_DIR = _DATA_ROOT / "evaluation" / "issue243_regression_baselines"
_DEFAULT_ISSUE240_DIR = _DATA_ROOT / "issue240"

DEFAULT_FROZEN_CORPORA: Final[tuple[tuple[str, Path], ...]] = (
    ("willow_v1", _DEFAULT_ISSUE240_DIR / "adjudication_corpus_willow_v1.json"),
    (
        "final_viability_v1",
        _DEFAULT_ISSUE240_DIR / "adjudication_corpus_final_viability_v1.json",
    ),
)


@dataclass(frozen=True)
class CorpusCalibrationRow:
    case_id: str
    scenario_id: str
    calibration_label: str
    profile_id: str
    profile_resolution: str


def default_baselines_dir() -> Path:
    return _DEFAULT_BASELINES_DIR


def load_frozen_corpus(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"corpus must be a JSON object: {path}")
    schema = str(raw.get("schema_version") or "").strip()
    if schema not in KNOWN_CORPUS_SCHEMAS:
        raise ValueError(
            f"unsupported corpus schema {schema!r} in {path} "
            f"(known: {sorted(KNOWN_CORPUS_SCHEMAS)})"
        )
    cases = raw.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"corpus cases must be an array: {path}")
    return raw


def extract_calibration_label(case: dict[str, Any]) -> str:
    for key in ("corrected_category", "pre_triage_label", "calibration_label"):
        val = case.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    raise ValueError(f"case {case.get('case_id')!r} has no calibration label field")


def extract_corpus_calibration_rows(
    corpus: dict[str, Any],
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
) -> list[CorpusCalibrationRow]:
    reg = registry or load_profile_registry()
    manifests = manifest_profiles or {}
    rows: list[CorpusCalibrationRow] = []
    for case in corpus.get("cases") or []:
        if not isinstance(case, dict):
            raise ValueError("each corpus case must be an object")
        case_id = str(case.get("case_id") or "").strip()
        scenario_id = str(case.get("scenario_id") or "").strip()
        if not case_id:
            raise ValueError("corpus case missing case_id")
        if not scenario_id:
            raise ValueError(f"corpus case {case_id!r} missing scenario_id")
        label = extract_calibration_label(case)
        manifest_profile = manifests.get(scenario_id)
        profile_id, resolution = resolve_evaluation_profile(
            scenario_id,
            manifest_profile=manifest_profile,
            registry=reg,
        )
        rows.append(
            CorpusCalibrationRow(
                case_id=case_id,
                scenario_id=scenario_id,
                calibration_label=label,
                profile_id=profile_id,
                profile_resolution=resolution,
            )
        )
    return rows


def build_baseline_from_corpus(
    corpus_name: str,
    corpus_path: Path,
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
    note: str = "calibration scaffolding from frozen #240 corpus labels — not canonical truth scoring",
) -> dict[str, Any]:
    corpus = load_frozen_corpus(corpus_path)
    rows = extract_corpus_calibration_rows(
        corpus,
        registry=registry,
        manifest_profiles=manifest_profiles,
    )
    case_rows = [
        {
            "case_id": r.case_id,
            "scenario_id": r.scenario_id,
            "calibration_label": r.calibration_label,
            "profile_id": r.profile_id,
            "profile_resolution": r.profile_resolution,
        }
        for r in rows
    ]
    category_counts = dict(Counter(r.calibration_label for r in rows))
    profile_counts = dict(Counter(r.profile_id for r in rows))
    envelope = observational_eval_envelope(
        schema_version=ISSUE243_REGRESSION_BASELINE_SCHEMA,
        issue=243,
        phase="243-A",
        corpus_name=corpus_name,
        corpus_path=str(corpus_path.as_posix()),
        corpus_schema_version=str(corpus.get("schema_version") or ""),
        generated_from=note,
    )
    envelope["case_rows"] = case_rows
    envelope["category_counts"] = category_counts
    envelope["profile_counts"] = profile_counts
    envelope["case_count"] = len(case_rows)
    return envelope


def load_regression_baseline(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"baseline must be a JSON object: {path}")
    schema = str(raw.get("schema_version") or "").strip()
    if schema != ISSUE243_REGRESSION_BASELINE_SCHEMA:
        raise ValueError(
            f"unsupported baseline schema {schema!r} in {path} "
            f"(expected {ISSUE243_REGRESSION_BASELINE_SCHEMA!r})"
        )
    return raw


def diff_baselines(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> dict[str, Any]:
    """Structural diff for regression reports. Does not interpret semantic correctness."""
    mismatches: list[dict[str, Any]] = []

    exp_counts = expected.get("category_counts") or {}
    act_counts = actual.get("category_counts") or {}
    if exp_counts != act_counts:
        mismatches.append(
            {
                "field": "category_counts",
                "expected": exp_counts,
                "actual": act_counts,
            }
        )

    exp_profile_counts = expected.get("profile_counts") or {}
    act_profile_counts = actual.get("profile_counts") or {}
    if exp_profile_counts != act_profile_counts:
        mismatches.append(
            {
                "field": "profile_counts",
                "expected": exp_profile_counts,
                "actual": act_profile_counts,
            }
        )

    exp_rows = {
        str(r.get("case_id")): r
        for r in (expected.get("case_rows") or [])
        if isinstance(r, dict) and r.get("case_id")
    }
    act_rows = {
        str(r.get("case_id")): r
        for r in (actual.get("case_rows") or [])
        if isinstance(r, dict) and r.get("case_id")
    }

    if set(exp_rows.keys()) != set(act_rows.keys()):
        mismatches.append(
            {
                "field": "case_ids",
                "expected_only": sorted(set(exp_rows) - set(act_rows)),
                "actual_only": sorted(set(act_rows) - set(exp_rows)),
            }
        )

    for case_id in sorted(set(exp_rows.keys()) & set(act_rows.keys())):
        exp_row = exp_rows[case_id]
        act_row = act_rows[case_id]
        for key in ("calibration_label", "profile_id", "profile_resolution", "scenario_id"):
            if exp_row.get(key) != act_row.get(key):
                mismatches.append(
                    {
                        "field": f"case_rows.{case_id}.{key}",
                        "expected": exp_row.get(key),
                        "actual": act_row.get(key),
                    }
                )

    passed = not mismatches
    report = observational_eval_envelope(
        schema_version=ISSUE243_REGRESSION_REPORT_SCHEMA,
        issue=243,
        phase="243-A",
        passed=passed,
        mismatch_count=len(mismatches),
        mismatches=mismatches,
        expected_corpus=expected.get("corpus_name"),
        actual_corpus=actual.get("corpus_name"),
    )
    return report


def run_corpus_regression(
    corpus_name: str,
    corpus_path: Path,
    baseline_path: Path,
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    expected = load_regression_baseline(baseline_path)
    actual = build_baseline_from_corpus(
        corpus_name,
        corpus_path,
        registry=registry,
        manifest_profiles=manifest_profiles,
    )
    report = diff_baselines(expected, actual)
    report["corpus_name"] = corpus_name
    report["corpus_path"] = str(corpus_path.as_posix())
    report["baseline_path"] = str(baseline_path.as_posix())
    return report


def build_eval_baseline_from_corpus(
    corpus_name: str,
    corpus_path: Path,
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    from semantic_proposal_eval_v1 import evaluate_corpus

    corpus = load_frozen_corpus(corpus_path)
    report = evaluate_corpus(corpus, registry=registry, manifest_profiles=manifest_profiles)
    case_rows = [
        {
            "case_id": j.get("case_id"),
            "scenario_id": j.get("scenario_id"),
            "profile_id": j.get("profile_id"),
            "corrected_category": j.get("corrected_category"),
            "semantic_decision": j.get("semantic_decision"),
        }
        for j in report.get("judgments") or []
        if isinstance(j, dict)
    ]
    envelope = observational_eval_envelope(
        schema_version=ISSUE243_EVAL_BASELINE_SCHEMA,
        issue=243,
        phase="243-B",
        corpus_name=corpus_name,
        corpus_path=str(corpus_path.as_posix()),
        corpus_schema_version=str(corpus.get("schema_version") or ""),
        eval_version=report.get("eval_version"),
        generated_from="semantic_proposal_eval_v1 profile-scoped scoring — calibration-guided, not canonical truth",
    )
    envelope["case_rows"] = case_rows
    envelope["corrected_category_counts"] = report.get("corrected_category_counts") or {}
    envelope["case_count"] = len(case_rows)
    return envelope


def load_eval_baseline(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"eval baseline must be a JSON object: {path}")
    schema = str(raw.get("schema_version") or "").strip()
    if schema != ISSUE243_EVAL_BASELINE_SCHEMA:
        raise ValueError(
            f"unsupported eval baseline schema {schema!r} in {path} "
            f"(expected {ISSUE243_EVAL_BASELINE_SCHEMA!r})"
        )
    return raw


def diff_eval_baselines(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    if (expected.get("corrected_category_counts") or {}) != (actual.get("corrected_category_counts") or {}):
        mismatches.append(
            {
                "field": "corrected_category_counts",
                "expected": expected.get("corrected_category_counts"),
                "actual": actual.get("corrected_category_counts"),
            }
        )
    exp_rows = {
        str(r.get("case_id")): r
        for r in (expected.get("case_rows") or [])
        if isinstance(r, dict) and r.get("case_id")
    }
    act_rows = {
        str(r.get("case_id")): r
        for r in (actual.get("case_rows") or [])
        if isinstance(r, dict) and r.get("case_id")
    }
    if set(exp_rows.keys()) != set(act_rows.keys()):
        mismatches.append(
            {
                "field": "case_ids",
                "expected_only": sorted(set(exp_rows) - set(act_rows)),
                "actual_only": sorted(set(act_rows) - set(exp_rows)),
            }
        )
    for case_id in sorted(set(exp_rows.keys()) & set(act_rows.keys())):
        for key in ("corrected_category", "profile_id", "semantic_decision", "scenario_id"):
            if exp_rows[case_id].get(key) != act_rows[case_id].get(key):
                mismatches.append(
                    {
                        "field": f"case_rows.{case_id}.{key}",
                        "expected": exp_rows[case_id].get(key),
                        "actual": act_rows[case_id].get(key),
                    }
                )
    passed = not mismatches
    return observational_eval_envelope(
        schema_version=ISSUE243_EVAL_REPORT_SCHEMA,
        issue=243,
        phase="243-B",
        passed=passed,
        mismatch_count=len(mismatches),
        mismatches=mismatches,
        expected_corpus=expected.get("corpus_name"),
        actual_corpus=actual.get("corpus_name"),
    )


def run_eval_regression(
    corpus_name: str,
    corpus_path: Path,
    baseline_path: Path,
    *,
    registry: SemanticEvalProfileRegistry | None = None,
    manifest_profiles: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    expected = load_eval_baseline(baseline_path)
    actual = build_eval_baseline_from_corpus(
        corpus_name,
        corpus_path,
        registry=registry,
        manifest_profiles=manifest_profiles,
    )
    report = diff_eval_baselines(expected, actual)
    report["corpus_name"] = corpus_name
    report["corpus_path"] = str(corpus_path.as_posix())
    report["baseline_path"] = str(baseline_path.as_posix())
    return report


def summarize_eval_report(
    corpus_name: str,
    corpus_path: Path,
    *,
    legacy_replay: bool = False,
) -> dict[str, Any]:
    from semantic_eval_legacy_f_codes import legacy_f_code_counts_from_corpus
    from semantic_proposal_eval_v1 import (
        FINAL_VIABILITY_HUMAN_ADJUDICATION,
        evaluate_corpus,
        model_alignment_success,
    )

    corpus = load_frozen_corpus(corpus_path)
    report = evaluate_corpus(corpus, legacy_replay=legacy_replay)
    judgments = report.get("judgments") or []
    legacy_replay_summary = legacy_f_code_counts_from_corpus(corpus, replay=legacy_replay)
    human_checks: list[dict[str, Any]] = []
    if corpus_name == "final_viability_v1":
        for j in judgments:
            cid = str(j.get("case_id") or "")
            expected_human = FINAL_VIABILITY_HUMAN_ADJUDICATION.get(cid)
            if expected_human:
                human_checks.append(
                    {
                        "case_id": cid,
                        "human_adjudication": expected_human,
                        "semantic_decision": j.get("semantic_decision"),
                        "corrected_category": j.get("corrected_category"),
                        "legacy_f_code": (j.get("legacy_lane") or {}).get("legacy_f_code"),
                        "legacy_taxonomy_status": (j.get("legacy_lane") or {}).get(
                            "legacy_taxonomy_status"
                        ),
                        "aligned": j.get("semantic_decision") == expected_human
                        and model_alignment_success(j),
                    }
                )
    pseudo_room_success = sum(
        1
        for j in judgments
        if j.get("profile_id") == "dorm_studio_single_space"
        and j.get("corrected_category") == "success"
        and j.get("legacy_classifier_misflag")
    )
    legacy_status_counts = Counter(
        (j.get("legacy_lane") or {}).get("legacy_taxonomy_status")
        for j in judgments
        if (j.get("legacy_lane") or {}).get("legacy_taxonomy_status")
    )
    return {
        "corpus_name": corpus_name,
        "phase": "243-C",
        "corrected_category_counts": report.get("corrected_category_counts"),
        "legacy_f_code_counts_eval": report.get("legacy_f_code_counts"),
        "legacy_f_code_counts_replay": legacy_replay_summary.get("legacy_f_code_counts"),
        "legacy_taxonomy_status_counts": dict(legacy_status_counts),
        "human_alignment_checks": human_checks,
        "human_alignment_pass_rate": (
            sum(1 for h in human_checks if h.get("aligned")) / len(human_checks)
            if human_checks
            else None
        ),
        "dorm_legacy_misflag_success_count": pseudo_room_success,
        "ambiguous_threshold_count": (report.get("corrected_category_counts") or {}).get(
            "ambiguous_threshold", 0
        ),
        "legacy_lane_primary_note": (
            "corrected_category is primary for #243; legacy F-codes are nested under legacy_lane"
        ),
    }


def summarize_legacy_replay(corpus_name: str, corpus_path: Path, *, replay: bool = False) -> dict[str, Any]:
    from semantic_eval_legacy_f_codes import legacy_f_code_counts_from_corpus

    corpus = load_frozen_corpus(corpus_path)
    summary = legacy_f_code_counts_from_corpus(corpus, replay=replay)
    summary["corpus_name"] = corpus_name
    summary["corpus_path"] = str(corpus_path.as_posix())
    return summary
