# Holy Grail legacy tree (`autogen_rp/python`)

This directory retains **historical scripts, validation evidence, and local runtime artifacts** from the AutoGen-era fork. Production V2 no longer depends on this path for data or domain tests.

## Production architecture (V2)

```text
Launch-Holy-Grail-V2.bat
  → v2/rp_runtime (supervisor + DSH)
  → v2/domain_api (Domain Host)
  → v2/domain (permanent domain semantics)
```

## Current locations (post-M13)

| Former role | Current location |
|-------------|------------------|
| Product data (templates, retrieval, fixtures, sessions) | `data/` at repository root (`HG_DATA_DIR`) |
| Neutral-domain pytest contracts | `v2/domain/tests/` |
| Domain library | `v2/domain/modules/` |

### Running domain tests

From repository root:

```sh
python -m pytest v2/domain/tests/ -q
```

Or from `v2/domain/`:

```sh
python -m pytest tests/ -q
```

Tests bootstrap `v2/domain` via `domain.bootstrap.ensure_domain_paths()` (see `v2/domain/tests/conftest.py`).

## Remaining layout here

| Path | Purpose |
|------|---------|
| `data/` | Legacy local data (migration source for M13.1); may still exist on disk |
| `scripts/` | Non-production investigation utilities |
| Validation evidence (historical) | `governance/archive/validation-runs/` |
| `.venv/` (under `autogen_rp/python/`) | **Legacy local** venv residue — not used by production (see repo-root `.venv`) |

## History

Forked from Microsoft AutoGen; progressively retired during M12–M13. See `governance/rp-app/v2-repository-retirement-m13.md`.
