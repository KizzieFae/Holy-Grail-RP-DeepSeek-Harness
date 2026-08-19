# Holy Grail validation evidence archive

**Status:** Immutable historical evidence (M13.5 rehome)  
**Original source:** `autogen_rp/python/validation_runs/`  
**Migration anchor:** M13.5 governance record (see `governance/rp-app/v2-repository-retirement-m13-5.md`)

## Purpose

This tree preserves Holy Grail behavioral-validation and issue-investigation **evidence** produced during the V1/V2 transition era. Contents are **not** active production data, runtime configuration, or current test fixtures.

## Current product architecture (for readers)

| Concern | Current location |
|---------|------------------|
| Production runtime | `v2/rp_runtime/`, `v2/domain_api/` |
| Domain library | `v2/domain/modules/` |
| Domain contract tests | `v2/domain/tests/` |
| Product data | `data/` (`HG_DATA_DIR`) |
| Python environment | repo-root `.venv/` |

## Historical-content policy

Files in this archive may reference paths such as `autogen_rp/python/...`, `rp_app/`, or checkout-specific absolute paths. **Those references are intentional** — they describe the architecture and commands that were true when the evidence was captured. Do not bulk-rewrite archived markdown/JSON to modern paths.

## Active test fixture split (M13.5)

`issue251/i251_doctrine_alignment.py` was extracted to a permanent domain test fixture:

`v2/domain/tests/fixtures/issue251/i251_doctrine_alignment.py`

The archive retains all other Issue #251 runners, reports, and JSON evidence.

## Investigation scripts

Non-production scripts under `autogen_rp/python/scripts/` that read archived JSONL/JSON use:

`governance/archive/validation-runs/`

via `autogen_rp/python/scripts/_archive_paths.py`.

## Mutability policy

- **Do not** add new validation output to this archive as part of normal development.
- Treat existing material as **read-only evidence** unless a governance-approved correction is required.
- New headless validation output (if any) should use current V2 conventions outside this tree.

## Layout (issue-organized)

| Subtree | Role |
|---------|------|
| `issue230_stepB/` | #230 Step B harmonization evidence |
| `issue242_*` | #242 participation/emission investigation waves |
| `issue249/` | #249 proposal-schema experiments |
| `issue251/` | #251 physical-severance doctrine investigations |
| `plan_execution/` | Post–#24 headless structured_eval snapshots |
| `cohesion_slate/` | #227 cohesion JSONL extracts |
| `participation_adjudication/` | #246 prior-suite reports |
| Root `*.md`, `*.jsonl` | Cross-issue synthesis and experiment matrices |

Executable Python runners co-located with evidence (e.g. `issue251/run_*.py`) are **historical reproduction scripts**, not production tooling.
