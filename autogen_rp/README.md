# Holy Grail — transitional `autogen_rp` container

**Status:** Retirement in progress (M13.x). **Do not add new project material here.**

## Where active material moved (M13.6)

| Former location | Current location |
|-----------------|------------------|
| Investigation scripts | [`tools/investigation/`](../tools/investigation/README.md) |
| Maintenance utilities | [`tools/maintenance/`](../tools/maintenance/README.md) |
| Technical documentation | [`docs/`](../docs/) |
| Validation evidence | [`governance/archive/validation-runs/`](../governance/archive/validation-runs/README.md) |
| Historical planning / audits | [`governance/archive/`](../governance/archive/) |

## Production architecture

```text
v2/          — production runtime, domain API, tests
data/        — HG_DATA_DIR product data
.venv/       — canonical Python environment (repo root)
```

See [`governance/rp-app/v2-repository-retirement-m13-6.md`](../governance/rp-app/v2-repository-retirement-m13-6.md).

## Remaining tracked content

This container retains **gitignore rules** and **local residue paths** until the final bounded retirement slice (M13.7+). No active tooling or current documentation should remain here after M13.6.
