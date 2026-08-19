## Consensus reached — Waves 0–3 (#242)

**Execution-stage transition:** `investigating` → `consensus_reached`

### Wave decisions

| Wave | Decision |
|------|----------|
| **Wave 0** | **APPROVED** — overlay schedule vocabulary + classifier alignment |
| **Wave 1** | **APPROVED** — opening / semantic-block deduplication |
| **Wave 3** | **APPROVED** — participation frame tightening |
| **Wave 2** | **CONDITIONALLY APPROVED** — threshold bridge merge (3-char) |
| **Wave 4+** | **DEFERRED** |

### Wave 2 conditional approval language (exact)

> **Wave 2 is approved contingent on:** (a) acceptance of `bridge.v6` removal from `v1_next7_3char_plus` fingerprint, (b) manifest profile update in same PR, (c) E1 + R2a live validation pass, (d) manual emotional spot-check PASS.

### Frozen baseline anchors

| Field | Value |
|-------|-------|
| **Baseline SHA** | `5b3fc7c251d7ecd850c78827a55c2a68b035c6b3` |
| **Instrumentation SHA** | `c1b7b2117301aa0bad00cf8fd61eb704fc0b918d` |
| **Baseline sessions** | `session_861`–`875` |
| **Baseline artifacts** | `autogen_rp/python/validation_runs/issue242_baseline/5b3fc7c251d7/` |

### Implementation order

`Wave 0` → `Wave 1` → `Wave 3` → `Wave 2`

(Wave 4+ deferred unless separately approved.)

### Rollback doctrine

- One git revert per wave if hard gates fail.
- **Hard FAIL:** any `semantic_evaluation` omission on v1_next7; overlay omission > 0%; profile_match < 1.0; ordering violations; cert overlay F0 below baseline; manual spot-check FAIL.
- **WARN (no auto-rollback):** classifier F2 noise; conservative emotional F0; token savings below estimate.

### Topology / fingerprint preservation doctrine

- Trigger-adjacent semantic self-report locality preserved across all waves.
- Wave 0: **no fingerprint change** (harness + overlay vocabulary only).
- Wave 2: **intentional** `bridge.v6` removal on 3-char lanes only, with manifest profile amendment in same PR.

### Authorization boundary

- **Wave 0** implementation authorized upon this consensus record.
- **Waves 1–3** approved at consensus but **not yet authorized for implementation** until Wave 0 evidence is recorded and next wave authorization is issued.
