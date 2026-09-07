# Issue #136 Tier-2 Semantic Campaign Specification

**Status:** Authorized validation tooling (Governance-approved 2026-09-06)  
**Issue:** [#136](https://github.com/) — LLM inference assessment  
**Implementation SHA (production inference):** `f3852196395505b8077ab817a736c7e7eddef099`

## Purpose

Forensic Tier-2 semantic validation of the deployed #136 Character grounding invariant:

> Ground this turn's beats and motivation in the authoritative Character and scene context already supplied; action, inaction, and change should follow from that context.

This campaign does **not** ablate or override production prompts. Controlled fixtures use scripted Director/Narrator where required; Character, Storyteller, semantic QA, plot cognition, and commit paths remain production-like.

## Fixture matrix

| Fixture ID | File | Repetitions | Structure |
|------------|------|-------------|-----------|
| `136-T2-A-STABILITY` | `136-t2-a-stability.json` | 3 | 1 live Mara turn |
| `136-T2-B-POS-CHANGE` | `136-t2-b-pos-change.json` | 2 | 2 turns; Jon seed + live Mara |
| `136-T2-C-NEG-CHANGE` | `136-t2-c-neg-change.json` | 2 | 2 turns; Jon seed + live Mara |
| `136-T2-D-INACTION` | `136-t2-d-inaction.json` | 3 | 1 live Mara turn |
| `136-T2-E-ENTITLEMENT` | `136-t2-e-entitlement.json` | 2 | 3 live turns Alice→Bob→Alice |
| `136-T2-F-ACTION-REQUIRED` | `136-t2-f-action-required.json` | 3 | 1 live Mara turn |

Truth records define **supported**, **ambiguous**, and **unsupported** envelopes for adjudication. Examples are not mandatory model behavior.

## Artifact layout

```text
data/fixtures/issue136_tier2_fidelity/
  truth/*.json
  cards/*.json
  README.md

v2/rp_runtime/scripts/run-issue136-tier2-campaign.mjs
v2/rp_runtime/src/scenario-harness/issue136-tier2-campaign.mjs
v2/rp_runtime/src/scenario-harness/issue136-fixture-truth.mjs
v2/rp_runtime/tests/issue136-tier2-fixture-truth.test.mjs
v2/rp_runtime/tests/issue136-tier2-campaign-smoke.test.mjs
```

## Safety guard

`deriveIssue136SafetyGuard()` computes a runaway-protection ceiling from:

- 16 campaign runs (15 controlled repetitions + 1 sentinel)
- 19 live Character turns
- Storyteller, Character, QA retry allowance, plot cognition, and sentinel margin

Not a semantic pass threshold. Record actual usage from execution evidence where available.

## Execution gates

1. Deterministic tooling tests pass (mock path).
2. Production #136 inference files unchanged since `f385219`.
3. Tooling committed; Greptile SUCCESS on tooling-bearing PR head with zero valid findings.
4. Live campaign + sentinel only after Greptile gate.

## Adjudication

Harness emits forensic records with deterministic entitlement-leak detection only. All other semantic dimensions default to `ambiguous` for Governance adjudication. No percentage thresholds or majority vote.

## Post-campaign

Documentation/evidence updates only. Do not mutate fixtures, cards, runner, or production runtime based on results without Governance re-authorization.
