# Storyteller Tier-1 Certification Harness (#65 Phase B)

Headless deterministic certification infrastructure for the integrated Storyteller program (#48). Phase B proves **objective architecture gates**; Phase C owns bounded live inference and semantic-quality characterization.

## Purpose

- Exercise production Domain Host + DSH orchestration seams without Streamlit/UI
- Mock **inference outputs only** — Domain authority, WAFI, Layer A/B, regeneration gates, freshness barriers, and Chronicle remain real
- Emit structured per-scenario results for Governance review and later Phase-C reuse

## Location

| Component | Path |
|-----------|------|
| Harness library | `v2/rp_runtime/src/scenario-harness/` |
| Tier-1 scenarios | `tier1-scenarios.mjs` |
| Certification tests | `v2/rp_runtime/tests/storyteller-tier1-certification.test.mjs` |

## Certification policy

### Objective correctness (hard gates — Phase B)

Deterministic pass/fail: epistemic isolation, freshness, WAFI, operation kind, bounded regeneration (≤1 / ≤2 evals), fail-closed semantics, evidence/chronicle joinability where exercised, consumer delivery/withhold.

### Semantic quality (Phase C — not Phase B)

PlotGoal usefulness, Director strategic value, Character advisory naturalness, replan appropriateness — **separate report**; no substring gates; no merge-blocking numeric thresholds before baseline.

## Scenario IDs (Tier 1 Certification Core)

| ID | Proof |
|----|-------|
| T1-01 | New-scope initialization + overlay READY + Chronicle |
| T1-02 | Post-commit update / no replan |
| T1-03 | Semantic replan distinct from ordinary update |
| T1-04 | Fresh Director overlay projection vs stale withhold |
| T1-05 | Layer B pass → Character contribution |
| T1-06 | Hidden-basis / cross-Character withhold |
| T1-07 | Bounded rewrite/regeneration |
| T1-08 | Stale Overlay freshness barrier |
| T1-09 | Restart/resume pending work (Domain-owned) |
| T1-10 | Forensic reconstruction join |
| T1-11 | Evaluator degradation fail-closed |

## Result schema

Each run returns `hg_storyteller_tier1_scenario_result_v1` (`scenario-result.mjs`):

- `scenario_id`, `run_id`, `fixture_id`
- `objective_status`: `certified` | `blocked` | `not_proven`
- `objective_pass` (true only when `objective_status === 'certified'`)
- `objective_gates`
- `operation_sequence`, `inference_counts`, `regeneration_count`
- `consumer_contributions`, `withheld`
- `evidence_ids`, `chronicle_keys`, `integrity_gaps`
- `durable_evidence` (on-disk evidence IDs for forensic scenarios)
- `phase_durations_ms`
- `semantic_characterization` (reserved for Phase C; null in Phase B)

## Forensics

Reuses existing stores only:

- Execution evidence: `data/execution_evidence/<hg_session_id>/`
- Plot Cognition Chronicle: `data/plot_cognition_forensics/<scope_id>/`
- Investigator CLIs: `tools/investigation/trace_plot_cognition_forensics.py`, `list_execution_evidence.py`

No parallel audit system.

## Running

```bash
cd v2/rp_runtime
node --test tests/storyteller-tier1-certification.test.mjs
```

## Boundaries

- **In scope (Phase B):** deterministic Tier-1 infrastructure, objective gates, measurement hooks
- **Out of scope:** live-model campaigns, semantic rubric thresholds, Tier-2, Layer B parallelism, numeric tuning, `clear_pending` hardening (#65 residual)

Layer B remains **sequential** per #66; concurrency assessment is Phase D.

## Phase C handoff

Replace `createTrackingInference` mocks with bounded real-model profiles on the same harness entry points (`runTier1Scenario`, `runAllTier1Scenarios`) without replacing scenario IDs or result schema.

### Phase C Tranche 1 (live)

- Live campaign machinery: `src/scenario-harness/live-config.mjs`, `tier1-tranche1.mjs`, `certification-evaluator.mjs`, etc.
- Truth fixtures: `data/fixtures/storyteller_tier1_truth/`
- Run: `node scripts/run-tranche1.mjs` (requires `DEEPSEEK_API_KEY`)
- Pre-live tests: `tests/storyteller-tier1-live-campaign.test.mjs`
