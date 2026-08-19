# Holy Grail investigation tooling

Offline utilities that operate on **current** repository paths (`data/`, audit JSON under `data/rp_audits/`).

## Layout

| Path | Role |
|------|------|
| `compare_*.py` | Aggregate baseline vs treatment JSON from investigation runs |
| `aggregate_*.py` | Roll up architecture-quality experiment outputs |
| `audit_episodic_issue_mismatch_scan.py` | Read-only scan of character audit `*_full.json` files |
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
```

## Notes

- V1 headless LLM simulation scripts were removed in M14.3. Future scenario validation will use the V2 production path.
- Do not write investigation output to the repository root. Use `data/investigation_runs/` or another gitignored path under `data/`.
