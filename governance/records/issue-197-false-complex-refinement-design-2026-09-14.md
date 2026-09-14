# Issue #197 — False-Complex Refinement Design (Predeclared)

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Phase:** Validation refinement under `validated` / Validating / P1  
**Baseline candidate:** `5ba6808` (code `3ed4a2d`)

## Predeclared repeat design

| Parameter | Value |
|-----------|-------|
| **Positive cases** | All 5 `uniform_safe_positive` corpus cases |
| **Positive repeat count** | **3** per case (15 total positive runs) |
| **Negative controls** | F06 exact, F06 paraphrase, explicit internal cognition, concealed action, directed speech |
| **Negative repeat count** | **1** per control (post-remediation safety check) |
| **Cast** | `Ayame`, `Kizzie`, `Harley`, `Celina` (matches corpus certification) |
| **Inference path** | Live production semantic path (end-to-end triage + verifier) |

## Interpretation thresholds

- **Rare stochastic veto:** case-level final-uniform rate ≥ 2/3 across repeats.
- **Frequent/systematic veto:** case-level final-uniform rate ≤ 1/3 across repeats, or aggregate positive uniform rate ≤ 40%.
- **Safety gate:** any mandatory-negative false-simple ⇒ block integration regardless of positive yield.

## Execution order

1. Document original corpus false-complex evidence (raw verifier outputs).
2. Run pre-remediation positive repeat (baseline at `5ba6808`).
3. Refine verifier semantic rubric if evidence supports systematic over-disqualification.
4. Rerun deterministic tests, post-remediation positive repeat, and negative controls on new candidate.
