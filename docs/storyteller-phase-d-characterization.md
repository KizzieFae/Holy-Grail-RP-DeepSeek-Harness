# Storyteller Phase D — Tier-2 Characterization (#65)

Phase D extends Tier-1 structural certification with bounded live **semantic-quality** and **performance** characterization. It does not change production behavior.

## Objectives

- Measure replan judgment stability across distinct invalidation classes
- Characterize update quality without replan
- Confirm lifecycle/freshness behavior under multi-commit sequences
- Capture Director projection usefulness
- Aggregate latency, token, and call distributions
- Assess whether sequential architecture creates material performance problems

## Fixtures

Truth fixtures: `data/fixtures/storyteller_tier2_truth/`

| ID | Class |
|----|-------|
| T2-R1 | Treaty/reconciliation destruction |
| T2-R2 | Target permanently sealed |
| T2-R3 | Strategic premise disproven |
| T2-R4 | Viable-plan control (no replan expected) |
| T2-U1 | New pressure (update, not replan) |
| T2-U2 | Resolved pressure |
| T2-L1 | Multi-commit pending lifecycle |
| T2-D1 | Director overlay projection |

Historical Phase-C C3 (`no_change` on treaty breach) is tracked separately and does not count toward new Phase-D sample size.

## Running

Deterministic gates:

```bash
cd v2/rp_runtime
node --test tests/storyteller-tier2-characterization.test.mjs
```

Live campaign (requires `DEEPSEEK_API_KEY`, max **40** calls):

```bash
cd v2/rp_runtime
node scripts/run-phase-d.mjs
```

Report (local, gitignored): `v2/rp_runtime/tmp/phase-d-report.json` — default harness output; optional CLI path override. Durable validation conclusions (PASS/FAIL, SHA, campaign path, key metrics) belong on the governing GitHub Issue.

## Posture

- Structural correctness remains hard-gated (authority, evidence, budgets)
- Semantic disagreement is characterized, not auto-failed
- No production tuning, prompt changes, or concurrency in Phase D
