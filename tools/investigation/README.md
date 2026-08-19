# Holy Grail investigation tooling

Active **non-production** scripts for offline validation, audit analysis, and issue investigation.

## Layout

| Path | Role |
|------|------|
| `tools/investigation/*.py` | Investigation CLIs and helpers |
| `tools/maintenance/*.py` | Read-only inventory / hygiene utilities |
| `data/` | Canonical product data (`HG_DATA_DIR`) |
| `governance/archive/validation-runs/` | Immutable historical validation evidence |

## Path helper

Import shared paths from `_repo_paths.py`:

```python
from _repo_paths import DATA_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
```

Run scripts from the repository root or from this directory:

```sh
python tools/investigation/compare_participation_calibration_ab.py --help
```

## V1 runtime dependency note

Scripts that import deleted `rp_app` modules (headless LLM simulation, corpus regression extractors, etc.) remain **archived investigation source**. They require the V1 Python runtime removed in M12.4 unless those modules are restored from `governance/archive/v1-runtime/`. Archive-reading comparators (`compare_*`, `aggregate_*`) work without `rp_app`.

## Outputs

- **Do not** write new mutable validation output into `governance/archive/validation-runs/`.
- Prefer `data/` subtrees or local gitignored paths for new investigation artifacts.

See `governance/rp-app/v2-repository-retirement-m13-6.md`.
