"""Tests for Issue #243-A corpus regression baseline mechanics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from issue243_corpus_regression import (  # noqa: E402
    ISSUE243_EVAL_BASELINE_SCHEMA,
    ISSUE243_REGRESSION_BASELINE_SCHEMA,
    build_baseline_from_corpus,
    build_eval_baseline_from_corpus,
    default_baselines_dir,
    diff_baselines,
    diff_eval_baselines,
    extract_calibration_label,
    load_frozen_corpus,
    load_regression_baseline,
    run_corpus_regression,
    run_eval_regression,
)
from semantic_eval_profiles import load_profile_registry  # noqa: E402

_DATA = Path(__file__).resolve().parent.parent / "data"
_WILLOW = _DATA / "issue240" / "adjudication_corpus_willow_v1.json"
_FINAL = _DATA / "issue240" / "adjudication_corpus_final_viability_v1.json"


def test_load_frozen_willow_corpus() -> None:
    corpus = load_frozen_corpus(_WILLOW)
    assert corpus["schema_version"] == "issue240_adjudication_corpus_v1"
    assert corpus["case_count"] == len(corpus["cases"])


def test_extract_calibration_label_prefers_corrected_category() -> None:
    assert extract_calibration_label({"corrected_category": "success", "pre_triage_label": "x"}) == "success"
    assert extract_calibration_label({"pre_triage_label": "ambiguous"}) == "ambiguous"


def test_build_baseline_from_willow_corpus() -> None:
    baseline = build_baseline_from_corpus("willow_v1", _WILLOW)
    assert baseline["schema_version"] == ISSUE243_REGRESSION_BASELINE_SCHEMA
    assert baseline["observational_only"] is True
    assert baseline["case_count"] == 14
    assert baseline["category_counts"]["ambiguous"] == 13
    assert baseline["profile_counts"]["dorm_studio_single_space"] == 14


def test_build_baseline_from_final_viability_corpus() -> None:
    baseline = build_baseline_from_corpus("final_viability_v1", _FINAL)
    assert baseline["case_count"] == 10
    assert "true semantic miss" in baseline["category_counts"]


def test_diff_baselines_passes_on_identical() -> None:
    baseline = build_baseline_from_corpus("willow_v1", _WILLOW)
    report = diff_baselines(baseline, dict(baseline))
    assert report["passed"] is True
    assert report["mismatch_count"] == 0


def test_diff_baselines_detects_label_change() -> None:
    baseline = build_baseline_from_corpus("willow_v1", _WILLOW)
    mutated = json.loads(json.dumps(baseline))
    mutated["case_rows"][0]["calibration_label"] = "mutated"
    report = diff_baselines(baseline, mutated)
    assert report["passed"] is False
    assert report["mismatch_count"] >= 1


def test_committed_baselines_match_frozen_corpora() -> None:
    reg = load_profile_registry()
    for name, corpus_path in (
        ("willow_v1", _WILLOW),
        ("final_viability_v1", _FINAL),
    ):
        baseline_path = default_baselines_dir() / f"{name}.json"
        assert baseline_path.is_file(), f"missing committed baseline {baseline_path}"
        report = run_corpus_regression(name, corpus_path, baseline_path, registry=reg)
        assert report["passed"], report.get("mismatches")


def test_eval_baseline_build_and_diff() -> None:
    actual = build_eval_baseline_from_corpus("willow_v1", _WILLOW)
    assert actual["schema_version"] == ISSUE243_EVAL_BASELINE_SCHEMA
    assert actual["observational_only"] is True
    assert actual["corrected_category_counts"]["success"] == 14
    report = diff_eval_baselines(actual, dict(actual))
    assert report["passed"] is True


def test_committed_eval_baselines_match() -> None:
    reg = load_profile_registry()
    for name, corpus_path in (
        ("willow_v1", _WILLOW),
        ("final_viability_v1", _FINAL),
    ):
        baseline_path = default_baselines_dir() / f"{name}_eval.json"
        assert baseline_path.is_file(), f"missing eval baseline {baseline_path}"
        report = run_eval_regression(name, corpus_path, baseline_path, registry=reg)
        assert report["passed"], report.get("mismatches")


def test_summarize_eval_report_distinguishes_legacy() -> None:
    from issue243_corpus_regression import summarize_eval_report

    summary = summarize_eval_report("willow_v1", _WILLOW)
    assert summary["corrected_category_counts"]["success"] == 14
    assert summary["legacy_f_code_counts_replay"]["F7"] == 14
    assert "legacy_lane_primary_note" in summary


def test_load_regression_baseline_rejects_bad_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "nope"}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported baseline schema"):
        load_regression_baseline(bad)
