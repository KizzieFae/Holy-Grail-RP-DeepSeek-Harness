#!/usr/bin/env python3
"""Run #246 prior-suite re-analysis validation against #227 manual adjudication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE

_PY = REPO_ROOT
sys.path.insert(0, str(LEGACY_RP_APP))

from issue246_prior_suite_validation import (  # noqa: E402
    default_reference_path,
    run_prior_suite_validation,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Issue #246 prior-suite validation")
    ap.add_argument("--reference", type=Path, default=default_reference_path())
    ap.add_argument("--jsonl-root", type=Path, default=VALIDATION_RUNS_ARCHIVE)
    ap.add_argument("--out", type=Path, default=VALIDATION_RUNS_ARCHIVE / "participation_adjudication" / "prior_suite_validation_report.json")
    ap.add_argument("--markdown-out", type=Path, default=VALIDATION_RUNS_ARCHIVE / "participation_adjudication" / "prior_suite_validation_report.md")
    ap.add_argument(
        "--policy-only",
        action="store_true",
        help="Run without manual corpus replay (heuristic policy only)",
    )
    args = ap.parse_args()

    report = run_prior_suite_validation(
        reference_path=args.reference,
        jsonl_root=args.jsonl_root,
        mode="mock",
        use_manual_as_corpus=not args.policy_only,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Prior-suite re-analysis validation (#246 vs #227 manual)",
        "",
        f"- **Passed:** {report['passed']}",
        f"- **Agreement rate:** {report['agreement_rate']} ({report['agreement_count']}/{report['total_cases_analyzed']})",
        f"- **Mode:** mock, corpus_replay={not args.policy_only}",
        "",
        "## Summary metrics",
        "",
        json.dumps(report.get("summary_metrics") or {}, indent=2),
        "",
        "## Priority cases 11 / 12 / 15",
        "",
        json.dumps(report.get("priority_cases_11_12_15") or {}, indent=2),
        "",
        "## Mismatches",
        "",
    ]
    mismatches = [c for c in report.get("comparisons") or [] if not c.get("agreement")]
    if not mismatches:
        lines.append("None.")
    else:
        for m in mismatches:
            lines.append(
                f"- **Case {m['case_id']}** ({m['suspicion_id']}): "
                f"manual={m['manual_expected_outcome']} new={m.get('new_adjudication_outcome')} "
                f"disposition={m['mismatch_disposition']} — {m['mismatch_reason']}"
            )
    lines.extend(["", "## Full comparison", "", "| Case | Rubric | Manual | New | Agree | Disposition |", "|------|--------|--------|-----|-------|-------------|"])
    for c in report.get("comparisons") or []:
        lines.append(
            f"| {c['case_id']} | {c['deterministic_rubric']} | {c['manual_expected_outcome']} | "
            f"{c.get('new_adjudication_outcome') or '—'} | {c['agreement']} | {c['mismatch_disposition']} |"
        )
    args.markdown_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{'PASS' if report['passed'] else 'FAIL'}: agreement={report['agreement_count']}/{report['total_cases_analyzed']}")
    print(json.dumps(report.get("summary_metrics") or {}, indent=2))
    print(f"wrote {args.out}")
    print(f"wrote {args.markdown_out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
