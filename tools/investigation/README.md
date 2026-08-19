# Holy Grail investigation tooling

Active **non-production** scripts for offline validation, audit analysis, and issue investigation.

## Layout

| Path | Role |
|------|------|
| `tools/investigation/*.py` | Investigation CLIs and helpers |
| `tools/maintenance/*.py` | Read-only inventory / hygiene utilities |
| `data/` | Canonical product data (`HG_DATA_DIR`) |
| `data/investigation_runs/` | Local gitignored investigation output (default for comparators) |

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

Scripts that import deleted `rp_app` modules (headless LLM simulation, corpus regression extractors, etc.) are **broken until restored or rewritten** (M14.3). Archive-reading comparators (`compare_*`, `aggregate_*`) work without `rp_app`.

## Outputs

- **Do not** write investigation output to the repository root.
- Prefer `data/investigation_runs/` or other local gitignored paths under `data/`.

See `governance/rp-app/fresh-start-residue-investigation-m14.md`.
