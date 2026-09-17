# Issue #201 — LH-1B Live Execution-Path Qualification Record

**Date:** 2026-09-16  
**Phase:** 5 — long-horizon persistent-narrative-cognition supplement  
**Subphase:** LH-1B final execution-path qualification (mock/synthetic only)  
**Issue:** #201 (`consensus_reached`, P1, full/full)  
**Prior apparatus SHA:** `ec4c82c`  
**Live S1–S6:** NOT authorized  
**#201 → `implemented`:** NOT authorized  

## Frozen hashes (unchanged)

| Artifact | SHA-256 |
|----------|---------|
| Fixture | `96b8ef4fa90ab27f0956b4da8edba1a090b5efd22df28825d4e1a05ea9918a64` |
| Player policy | `362207fa89fa89b87765c5aa78ca5d554c7ae67264eda99463feb09d36514fa3` |
| Causal design | `78bc5ff240f08d8658df9645e4b862366c0a02d8ff3fa96cf18044d436484c58` |

## Runner implementation

- **Authoritative path:** `HolyGrailApplicationClient` → `runPlayerPvrAndRecord` → `runA2BeatRound` (`issue201-lh1b-live-lib.mjs`)
- **Campaign entry (Governance-gated):** `node v2/rp_runtime/scripts/issue201-lh1b-seam-verification.mjs --execute-campaign` with `liveAuthorized: true` and successful `--preflight`
- **Turn ordering:** `LH1B_TURN_ORDERING` in `issue201-lh1b-live-lib.mjs` (LH-0 projection before Director when persistent)

## Qualification (no live LLM)

```
node --test v2/rp_runtime/tests/issue201-lh1b-apparatus.test.mjs   # 5/5
node --test v2/rp_runtime/tests/issue201-lh1b-runner.test.mjs      # includes 35-proof runner qual
node v2/rp_runtime/scripts/issue201-lh1b-seam-verification.mjs --qualify-runner
```

- Apparatus: 38/38 gates, 14/14 synthetic proofs (via validation suite)
- Runner mock qualification: **35/35 proofs PASS** (`runLh1bRunnerMockQualification`)
- Character negative control: `forceMockInferenceProfiles` on violating T17 mock only (no live model for negative injection)

## Arm isolation fix (wiring, not frozen design)

- `issue201-lh0-post-commit-adapters.mjs`: LH-B post-commit no longer seeds `director_turn` fixture obligations (prevents LH-D trajectory leak on S2/S4)

## Live failure / retry policy

- `issue201-lh1b-failure-policy.mjs` — fail-closed campaign; no sequence restart without Governance; partial sequences forensic-only

## Cost envelope correction

- Prior ~29 inferences/turn conflated round-internal budgets with execution-evidence attempts
- LH-1A: 782 events / 176 player turns ≈ **4.44 events/turn**
- LH-1B S1–S6 projected: **437** total inference events (~2.50 wall-hours at LH-1A ayame rates); see `buildLh1bCostEnvelope()`

## Repository

- `main` ahead of `origin/main` by 61 commits at apparatus baseline; local history intentional; reproducibility risk until push — see qualification report
