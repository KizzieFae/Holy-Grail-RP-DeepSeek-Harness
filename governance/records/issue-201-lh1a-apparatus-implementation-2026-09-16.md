# Issue #201 LH-1A — Apparatus Implementation & Deterministic Validation Record

**Date:** 2026-09-16  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Canonical state:** `consensus_reached` (unchanged)  
**Phase:** 5 — long-horizon supplement  
**Subphase:** **LH-1A apparatus implementation + deterministic validation** (live execution NOT authorized)  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  

**Methodology authority:** `issue-201-long-horizon-refined-experimental-design-2026-09-15.md`; `issue-201-architecture-direction-and-long-horizon-validation-design-2026-09-15.md`; `issue-201-lh1a-preparation-activation-2026-09-16.md`; `issue-201-lh0-completion-governance-acceptance-2026-09-16.md`

---

## Authorization boundary (this step)

**Authorized:**

1. Durable LH-1A experimental apparatus (fixtures, policies, rubric, orchestrator, exporters, validation tooling)
2. Deterministic validation campaign (55 gates + synthetic lifecycle proofs + LH-0 regressions)
3. Governance record and Issue progress comment

**NOT authorized:**

- Eight live LH-1A sequences
- LH-0 classifier repair or rerun
- Cognition tuning
- K6 remediation
- LH-2 freeze
- Production A4→A2 migration
- #201 `implemented` or closure

---

## Implementation candidate

Recorded at commit time of this record (see git log for `feat(#201): LH-1A apparatus`).

---

## Frozen authority artifact hashes

| Artifact | SHA-256 |
|----------|---------|
| Ayame fixture (`ayame_lh1a_fixture_v1.json`) | `208956064650058b0e60093893ba0a569e4035d181dd75ac9e5834d3a14054d4` |
| Arkham fixture (`arkham_lh1a_fixture_v1.json`) | `f9556fc504660935eddc8b1e918969fe6d5fcf32aef9416ff5bde5b6d9f50212` |
| Ayame player policy (`ayame_lh1a_policy_v1.json`) | `868384b06e85d980ad42b331bc59b0ac8e00a56a7b4ee9006c1bdd23e7075bd2` |
| Arkham player policy (`arkham_lh1a_policy_v1.json`) | `fb14d6f2a4f10adda6a1680be4c415671be939bbfb1fad18867ebadef2130a2c` |
| Blind rubric (`lh1a_blind_rubric_v1.json`) | `f533cc604b276f7798639db863c8e2264254233ab162de03b343841df840bb91` |

---

## Campaign shape (implemented)

| Dimension | Value |
|-----------|-------|
| Arms | LH-A, LH-B, LH-C, LH-D (4) |
| Scenario families | Ayame controlled-pressure; Arkham antagonistic arena (2) |
| Sequences | 8 (1 per arm/scenario) |
| Turns per sequence | 22 (within 20–24) |
| Scenes per sequence | 2 (transition at T12) |
| Checkpoints | C1=T8, C2=T16, C3=T22 |
| Obligation classes per fixture | 10 (minimum manifest) |

---

## Deterministic validation results

**Command:** `node v2/rp_runtime/scripts/issue201-lh1a-seam-verification.mjs --validate-apparatus`

| Suite | Result |
|-------|--------|
| LH-1A apparatus gates | **55/55 PASS** |
| Synthetic lifecycle proofs | **8/8 PASS** |
| LH-0 consumer-value regressions | **PASS** |
| LH-0 timing regressions | **PASS** |
| `issue201-lh1a-apparatus.test.mjs` | **6/6 PASS** |

**Readiness:** `readiness_for_governance_execution_gate: true`  
**Live execution:** `live_execution_authorized: false`

---

## Production-runtime impact

**None.** Apparatus is offline planning/validation tooling under `v2/rp_runtime/scripts/lib/issue201-lh1a-*` and governance fixtures. No Domain Host, RP runtime beat path, or UI changes. Live inference integration deferred to Governance-authorized execution gate.

---

## Artifact disposition

| Class | Disposition |
|-------|-------------|
| Fixtures, policies, rubric | **Committed** under `governance/records/issue201-lh1a-*` |
| Apparatus libraries, CLI, tests | **Committed** under `v2/rp_runtime/` |
| Validation JSON output | **Ephemeral** (stdout / optional `--output-dir`; not committed by default) |
| LH-0 investigation runs | **Preserved** under `data/investigation_runs/` (gitignored) |

---

## Methodology deviations

None identified. Implementation follows accepted refined design; orchestrator is planning-only (no live inference) per authorization boundary.

---

## Next Governance decision required

> **Authorize eight live LH-1A sequences** after full-weight consensus execution gate, using frozen hashes above and blind rubric `lh1a_blind_rubric_v1`.

---

## Implementation map

| Component | Path |
|-----------|------|
| Contract / constants | `v2/rp_runtime/scripts/lib/issue201-lh1a-contract.mjs` |
| Fixtures loader | `v2/rp_runtime/scripts/lib/issue201-lh1a-fixtures.mjs` |
| Player policy | `v2/rp_runtime/scripts/lib/issue201-lh1a-player-policy.mjs` |
| Policy turn realizations | `v2/rp_runtime/scripts/lib/issue201-lh1a-policy-turns.mjs` |
| Orchestrator | `v2/rp_runtime/scripts/lib/issue201-lh1a-orchestrator.mjs` |
| Checkpoint exporter | `v2/rp_runtime/scripts/lib/issue201-lh1a-checkpoint-exporter.mjs` |
| Blind packet | `v2/rp_runtime/scripts/lib/issue201-lh1a-blind-packet.mjs` |
| Archaeology | `v2/rp_runtime/scripts/lib/issue201-lh1a-archaeology.mjs` |
| Cost accounting | `v2/rp_runtime/scripts/lib/issue201-lh1a-cost-accounting.mjs` |
| Synthetic proofs | `v2/rp_runtime/scripts/lib/issue201-lh1a-synthetic-proofs.mjs` |
| Validation suite | `v2/rp_runtime/scripts/lib/issue201-lh1a-validation-lib.mjs` |
| Entry / CLI | `v2/rp_runtime/scripts/issue201-lh1a-seam-verification.mjs` |
| Tests | `v2/rp_runtime/tests/issue201-lh1a-apparatus.test.mjs` |
