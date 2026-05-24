"""Tests for Issue #246 corpus regression."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RP = Path(__file__).resolve().parents[1] / "rp_app"
if str(_RP) not in sys.path:
    sys.path.insert(0, str(_RP))

from issue246_corpus_regression import evaluate_corpus, run_regression  # noqa: E402


def test_corpus_regression_passes_when_present():
    corpus = Path(__file__).resolve().parents[1] / "data" / "issue227" / "adjudication_corpus_cohesion_v1.json"
    baseline = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "evaluation"
        / "issue246_regression_baselines"
        / "cohesion_v1.json"
    )
    if not corpus.is_file() or not baseline.is_file():
        return
    report = run_regression(corpus, baseline)
    assert report["passed"] is True
    assert report["mismatch_count"] == 0
    assert report["summary"]["adjudicated_failure_count"] == 3
