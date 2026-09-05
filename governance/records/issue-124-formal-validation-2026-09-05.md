# Issue #124 — Formal Validation Record

**Date:** 2026-09-05  
**Behavioral validation anchor:** `0d2b3124e769f9a150fe1d6637e3413120c59be2` (Greptile 5/5)  
**Record tip at validation:** `e053c49c924e38f7cc42c217f7cd4393a9c43fc6` (governance record only)  
**PR:** #127 — OPEN, not merged

## Deterministic validation

| Command | Result |
|---------|--------|
| `pytest v2/domain/tests/test_issue_124_semantic_normalization.py v2/domain/tests/test_player_decomposition_normalize_kernel.py v2/domain/tests/test_issue_120_generalized_internal.py v2/domain/tests/test_issue_121_uniform_projection.py v2/domain/tests/test_issue_91_player_perceptual.py v2/domain/tests/test_player_decomposition_context.py -q` | **43 passed** |
| `python -m pytest v2/domain/tests/ -q` | **996 passed** |
| `node --test tests/player-decomposition-phase.test.mjs tests/player-visibility-triage-phase.test.mjs tests/issue120-live-validation-projection.test.mjs` | **18 passed** |

## Live semantic validation (uncapped tokens, max 2 attempts)

Script: `v2/rp_runtime/scripts/issue124-live-validation.mjs`  
Fixture: `v2/rp_runtime/tests/fixtures/issue124-live-validation-report.json`

| Case | Attempts | Normalization | Units | Search nodes | Retry |
|------|----------|---------------|-------|--------------|-------|
| ordinary_public | 1 | accept | 2 | 3 | no |
| mixed_asymmetric (#88) | 1 | accept | 4 | 5 | no |
| complex_dense_seiza_japan | 1 | accept | 5 | 6 | no |

All cases: `validation_status: valid` on canonical PVR via `recordUserTurn`; no budget exhaustion; no semantic retries.

## Token observations (vs #112 combined semantic+mechanical)

| Case | #112 total tokens (approx) | #124 output tokens | #124 input tokens | #124 reasoning tokens |
|------|---------------------------|-------------------|-------------------|----------------------|
| ordinary_public | 12,597 | 3,258 | 525 | 3,160 |
| mixed_asymmetric | 29,750 | 1,913 | 581 | 1,650 |
| complex_dense | 22,372 | 4,011 | 625 | 3,660 |

Measured reduction in completion/reasoning tokens reflects removal of mechanical PVR JSON from LLM output; input tokens higher due to SIR contract manifest vs prior runs — compare as directional evidence only.

## Greptile

`0d2b312` — SUCCESS, 5/5, 0 new comments.
