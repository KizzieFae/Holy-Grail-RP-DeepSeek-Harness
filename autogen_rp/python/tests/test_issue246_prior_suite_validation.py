"""Tests for Issue #246 prior-suite validation."""

from __future__ import annotations

import sys
from pathlib import Path

_RP = Path(__file__).resolve().parents[1] / "rp_app"
if str(_RP) not in sys.path:
    sys.path.insert(0, str(_RP))

from issue246_prior_suite_validation import (  # noqa: E402
    default_reference_path,
    run_prior_suite_validation,
)


def test_prior_suite_validation_passes_with_manual_replay():
    ref = default_reference_path()
    jsonl_root = Path(__file__).resolve().parents[1] / "validation_runs"
    if not ref.is_file():
        return
    report = run_prior_suite_validation(
        reference_path=ref,
        jsonl_root=jsonl_root,
        use_manual_as_corpus=True,
    )
    assert report["total_cases_analyzed"] == 25
    assert report["passed"] is True
    assert report["agreement_rate"] == 1.0
    for cid in ("11", "12", "15"):
        pc = report["priority_cases_11_12_15"][cid]
        assert pc["agreement"] is True
        assert pc["new_adjudication_outcome"] == "adjudicated_failure"
