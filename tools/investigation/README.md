# Holy Grail investigation tooling

Offline utilities that operate on **current** repository paths (`data/`, audit JSON under `data/rp_audits/`).

## Layout

| Path | Role |
|------|------|
| `compare_*.py` | Aggregate baseline vs treatment JSON from investigation runs |
| `aggregate_*.py` | Roll up architecture-quality experiment outputs |
| `audit_episodic_issue_mismatch_scan.py` | Read-only scan of character audit `*_full.json` files |
| `list_execution_evidence.py` | List V2 execution evidence for a session (`data/execution_evidence/`) |
| `list_audit_tags.py` | List V2 human audit tags for a session (`data/audit_tags/`) |
| `trace_turn_forensics.py` | Unified read-only turn/commit forensic navigator (`hg_turn_investigator_v1`, #101). Commit view excludes EE explicitly tied to another commit; round view preserves multi-commit sequence and per-commit Plot Cognition handoffs. |
| `_turn_forensics.py` | Shared turn/commit correlation library (not invoked directly) |
| `trace_ni_forensics.py` | Read-only NI forensic investigator over `hg_ni_forensics_v1` (#46 Package B) |
| `_ni_forensics.py` | Shared NI traversal/reconstruction library (not invoked directly) |
| `trace_plot_cognition_forensics.py` | Read-only Plot Cognition chronicle investigator (#64) |
| `_plot_cognition_forensics.py` | Shared Plot Cognition forensics helpers (not invoked directly) |
| `_issue240_*.py` | Offline Issue #240 audit analysis helpers (read audit trees only) |
| `data/investigation_runs/` | Default local output for comparators (gitignored) |

## Path helper

```python
from _repo_paths import DATA_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
```

Run from repository root:

```sh
python tools/investigation/compare_participation_calibration_ab.py --help
python tools/investigation/audit_episodic_issue_mismatch_scan.py --help
python tools/investigation/list_execution_evidence.py <hg_session_id>
python tools/investigation/list_audit_tags.py <hg_session_id>
python tools/investigation/trace_turn_forensics.py <hg_session_id> commit <domain_commit_id> [--json]
python tools/investigation/trace_turn_forensics.py <hg_session_id> round <hg_round_id> [--json]
python tools/investigation/trace_ni_forensics.py <hg_session_id> session
python tools/investigation/trace_ni_forensics.py <hg_session_id> tag <tag_id> [--resolve]
python tools/investigation/trace_ni_forensics.py <hg_session_id> lineage --source-id <id> [--json]
```

## Notes

- Scenario validation uses domain manifest tests and integration tests; see [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md).
- Write investigation output to `data/investigation_runs/` or another gitignored path under `data/`.
