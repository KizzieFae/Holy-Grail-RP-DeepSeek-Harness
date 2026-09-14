# Issue #199 — Supplemental Validation Record

**Date:** 2026-09-14  
**Candidate SHA:** `3a818aebc373a96a55432d220244d39574627a19` (base `09f39295`)  
**Live evidence:** `issue-199-supplemental-semantic-validation-2026-09-14.json`

## Uniform-projection classification

**A — Representational only**

Deterministic trace: `v2/domain/tests/test_issue_199_uniform_projection_trace.py`

## Live semantic validation

| Check | Result |
|-------|--------|
| Unsupported strain (F06 opening, threshold) | **reject_hard** R02b (+ R14) |
| Legitimate trembling interpretation (co-present) | **pass** |

Model: `deepseek-v4-flash` (semantic evaluator, reasoningEffort `low`).

## Character generation (secondary)

Deterministic manifest inspection via existing tests confirms `authoritative_perceptual_inventory` + `CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE` on F06-like empty-inventory fixtures. No live Character-generation campaign run (bounded scope).
