# Holy Grail maintenance tooling

Read-only inventory and hygiene utilities for local `rp_audits` and related artifacts.

| Script | Purpose |
|--------|---------|
| `hg_data_migration_check.py` | **Optional one-time operator check** — compares a local legacy data tree vs canonical `data/` (`--check` / `--migrate`). Not part of normal startup or product architecture. |
| `issue86_inventory_pass.py` | Deterministic `rp_audits` inventory JSON |
| `issue88_tranche1_prepare.py` | Registry snapshot + allow-list prep |
| `issue88_tranche2_duplicate_plan.py` | Duplicate equivalence / keep-delete plan |

Outputs are written under this directory (gitignored `issue86_*.json`, `issue88_*.json` patterns in root `.gitignore`).

Run from repository root:

```sh
python tools/maintenance/issue86_inventory_pass.py
```
