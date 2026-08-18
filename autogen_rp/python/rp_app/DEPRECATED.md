# DEPRECATED — `rp_app` namespace (M12.3)

This directory is **not** the Holy Grail production runtime.

## Production (V2)

```text
Launch-Holy-Grail-V2.bat
cd v2/rp_runtime && npm run app
```

## What remains here

- **Domain shims** — forward imports to `v2/domain/modules/` (M12.2)
- **No orchestration** — `turn_runner`, `app.py`, `model_client`, UI, and AutoGen wiring moved to `legacy/v1_orchestration/`

## Legacy V1 (retirement-only)

```text
python -m legacy.v1_orchestration --check-imports
```

See `governance/rp-app/v2-v1-orchestration-fence-m12-3.md`.
