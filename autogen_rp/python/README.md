# Holy Grail domain tests (`autogen_rp/python`)

This directory holds **neutral-domain pytest suites** and **Holy Grail data assets** (character cards, scene templates, sessions, audit fixtures).

## Production architecture (V2)

Holy Grail does **not** use AutoGen for production orchestration.

```text
Launch-Holy-Grail-V2.bat
  → v2/rp_runtime (supervisor + DSH)
  → v2/domain_api (Domain Host)
  → v2/domain (permanent domain semantics)
```

## Running domain tests

From repository root:

```sh
python -m pytest autogen_rp/python/tests/ -q
```

Or from this directory:

```sh
python -m pytest tests/ -q
```

Tests bootstrap `v2/domain` via `domain.bootstrap.ensure_domain_paths()` (see `tests/conftest.py`).

## Layout

| Path | Purpose |
|------|---------|
| `data/` | Character cards, templates, sessions, audit JSON |
| `tests/` | Neutral-domain behavioral contracts |
| `scripts/` | Non-production investigation utilities |
| `validation_runs/` | Historical validation evidence (markdown + neutral helpers) |

## History

This tree was forked from Microsoft AutoGen and progressively retired during M12 (M12.4 removed V1 orchestration; M12.5 removed vendored AutoGen packages). See `governance/rp-app/v2-v1-orchestration-deletion-m12-4.md` and `governance/rp-app/v2-autogen-package-removal-m12-5.md`.
