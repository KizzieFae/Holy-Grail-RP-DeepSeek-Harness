# Issue #201 LH-0 — Apparatus Implementation Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** Phase 5 — long-horizon supplement / LH-0 apparatus implementation  
**Activation commit:** `741e1ce`  
**Implementation commit:** `4c1e7f7` (**This record**)  
**Canonical state:** `consensus_reached` (unchanged)  
**Assigned / effective workflow weight:** `full` / `full`  
**LH-0 micro-run execution:** NOT authorized / NOT performed  
**LH-1A:** NOT authorized  

---

## Authorization scope

Governance authorized **LH-0 mechanical seam-verification apparatus implementation** and **deterministic validation only**.

**Performed:**

- Lifecycle state schema (§10 codes + transport L0–L4)
- Obligation ledger with `DEFERRED_VALID` contract enforcement
- Seam failure taxonomy + K6-class detection (no remediation)
- LH-A/B/C/D arm configuration contracts
- Consumption lifecycle enforcer (fail-closed config validation)
- Controlled micro-fixture manifest
- Synthetic obligation simulation for deterministic proof
- Negative-control seam attribution
- Narrative archaeology + cost attribution export compatibility
- Harness runner `--validate-apparatus`
- Node test suite (25 tests, all pass)

**Not performed:** LH-0 live micro-runs; RP quality conclusions; LH-1A; production A4→A2 migration; K6 remediation.

---

## Implementation artifacts

| Component | Path |
|-----------|------|
| Lifecycle state codes | `v2/rp_runtime/scripts/lib/issue201-lifecycle-states.mjs` |
| Lifecycle tracer + enforcer | `v2/rp_runtime/scripts/lib/issue201-lifecycle-tracer.mjs` |
| Obligation ledger | `v2/rp_runtime/scripts/lib/issue201-obligation-ledger.mjs` |
| Seam classifier + K6 probe | `v2/rp_runtime/scripts/lib/issue201-seam-classifier.mjs` |
| LH-0 arm configs | `v2/rp_runtime/scripts/lib/issue201-lh0-arms.mjs` |
| Fixture loader | `v2/rp_runtime/scripts/lib/issue201-lh0-fixtures.mjs` |
| Apparatus lib | `v2/rp_runtime/scripts/lib/issue201-lh0-lib.mjs` |
| Harness runner | `v2/rp_runtime/scripts/issue201-lh0-seam-verification.mjs` |
| Micro-fixture manifest | `governance/records/issue201-lh0-fixtures/lh0_fixture_manifest.json` |
| Apparatus tests | `v2/rp_runtime/tests/issue201-lh0-apparatus.test.mjs` |
| Harness-only orchestrator hook | `v2/rp_runtime/src/lib/a2-beat-orchestration.mjs` (configurable projection + LH-0 enforcer audit) |

---

## Apparatus architecture

```
Synthetic obligation manifest (lh0_fixture_manifest.json)
  → ObligationLedger (stable obligation_id, DEFERRED_VALID contract)
  → LifecycleTracer (L0–L4 events + §10 terminal states)
  → SeamClassifier (producer/persistence/retrieval/entitlement/projection/consumption/…)
  → ArchaeologyRecord + CostAttribution export
```

**Arm contracts (LH-B/C/D):** `persistent_cognition_enabled=true`, `projection_lifecycle_enabled=true`, `consumption_lifecycle_enforcer=true`, `skip_character_knowledge_cognition=false`. Rejects G3-D class gap at config validation.

**LH-D fairness:** deterministic eligibility first; narrative-priority guidance only; rejects `unconditional_director_override` and trivial Director routing through persistent model.

---

## Deterministic validation results

**Command:**

```bash
node v2/rp_runtime/scripts/issue201-lh0-seam-verification.mjs --validate-apparatus
node --test v2/rp_runtime/tests/issue201-lh0-apparatus.test.mjs
```

| Check | Result |
|-------|--------|
| 25/25 node tests | **PASS** |
| `readiness_for_lh0_micro_execution` | **true** (apparatus wiring only) |
| G3-D gap detectable | **PASS** (simulated L1 without L2) |
| Negative controls (4 layers) | **PASS** |
| LH-B/C/D happy-path L4 simulation | **PASS** |
| K6-class detection | **PASS** (probe only) |
| G3-A orchestration regression | **PASS** |

**Evidence root (local, gitignored):** `data/investigation_runs/issue201-lh0-apparatus-2026-09-15T21-09-40-401Z/`

---

## Production isolation

- `a2-beat-orchestration.mjs` remains harness-only (not production bootstrap).
- Changes: optional `projectionLifecycleEnabled`, `skipCharacterKnowledgeCognition`, `lh0ConsumptionEnforcer` from beat options (defaults preserve G3 behavior).
- No K6 remediation; no projection budget changes.

---

## Known limitations

1. Live persistent cognition adapters (Plot/Storyteller/consolidated LLM calls) are **configuration contracts** — synthetic simulation proves lifecycle accounting; live wiring validated at micro-run authorization.
2. Stages requiring live Primary RP decision influence use simulated `decision_influenced` / `observable_consequence` events with explicit evidence payloads.
3. K6 detection is instrumentation-only; defective production seam not repaired.

---

## Deviations from refined design

None on methodology. Implementation uses synthetic simulation for deterministic proof where live LLM execution is explicitly out of scope for this authorization.

---

## Proposed LH-0 execution protocol (not authorized)

See `issue201-lh0-execution-protocol.json` emitted by harness. Summary:

- 6-turn micro-sequences per persistent arm (B, C, D) + LH-A control traces
- Pass: L2+, consumer receipt, L3 or valid `DEFERRED_VALID`, seam attribution on failure
- Explicit prohibition: no RP-quality conclusions from LH-0

---

## Governance next decision

**Authorize LH-0 live micro-run execution** — separate explicit action after reviewing this implementation record.

---

**STOP.** Apparatus implementation complete. No live LH-0 runs.
