# Issue #201 — LH-1B Live Causal Campaign Record

**Date:** 2026-09-17  
**Qualified runner:** `dd11d10cc3f4a420691fb33f3533bd75dcb39a4f`  
**Live execution SHA:** `215a5b6c5bf2682e7386f8a573ae82b7ac90b5f1` (authorization-only CLI: `--live-authorized`)  
**Evidence root:** `data/investigation_runs/issue201-lh1b-live-campaign-2026-09-17/`  
**Campaign outcome:** S1–S6 complete (108/108 player turns committed); `campaign_failed: false`

## Remote durability

- Pre-live `origin/main`: `c751ea6` (strict ancestor)
- Published: `dd11d10` then `215a5b6` fast-forward push
- Post-publication `origin/main`: `215a5b6`

## Frozen hashes (verified at preflight)

Unchanged from preregistered values (fixture, policy, causal design).

## Causal headline (preregistered forks)

| Comparison | Character forks T15–T18 | Director T15 |
|------------|----------------------|--------------|
| S1/S3 LH-A | No R2–R4 (no persistence path) | N/A / no receipt |
| S2/S4 LH-B | R3–R4 **yes**; R5 **no** (`stimulus_sufficient` / transcript) | No director trajectory receipt (LH-B) |
| S5 LH-D | R3–R4 **yes**; R5 **no** (lean substrate) | R0–R2 **yes**; R3–R4 **no** (Director decision did not match trajectory markers) |
| S6 LH-A control | No persistence | No director guidance (control) |

**No preregistered fork reached R5 marginal persistence value** in this campaign.

## Cost (observed)

- Inference events (turn `inference_count` sum): **349** (planning ~437)
- Wall time (turn `operation_wall_ms` sum): **~2.28 h** (~8.22M ms)
- Per sequence events: S1 40, S2 76, S3 38, S4 77, S5 77, S6 41
- Token fields not populated on execution-evidence attempts in this run (rollup tooling gap; forensic attempts under evidence root)

## Issue state

#201 remains OPEN / `consensus_reached` / P1 — not `implemented`.
