# Issue #200 — Supplemental Semantic Validation

**Date:** 2026-09-14  
**Issue:** [#200](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/200)  
**Phase:** `validated` (supplemental live semantic validation complete)  
**Assigned / effective weight:** `standard` / `full`

## Candidate provenance

| Field | Value |
|---|---|
| Base SHA | `bf1ac61f85262afa5ac9f64232627b328aec7477` |
| Candidate SHA | `7e5b56698134591c928ea8de149cbb3493725a45` |
| Working tree | Clean at live run |
| Commit message | Issue #200: pressure freshness and inverse R16 contract |

## Live semantic validation

- **Path:** production `runSemanticEvaluation` + DeepSeek `deepseek-v4-flash` (`reasoningEffort: low`)
- **Harness:** `v2/rp_runtime/scripts/issue200-inverse-r16-live-validation.mjs`
- **Report:** `governance/records/issue-200-live-validation-2026-09-14.json`
- **Outcome:** `validation_pass: true` (4/4 cases matched)

| Case | Expected | Result | Evidence ID |
|---|---|---|---|
| A objective regression | `reject_hard` / R16 | **pass** | `2c2080ac-3fef-458e-9798-ba8ad41a8c2e` |
| B ignorance command | `pass` | **pass** | `85f79d0c-c6bd-4bc4-b63b-7cba8c651a6a` |
| C deliberate deception | `pass` | **pass** | `b3d63289-7ced-4d7e-b933-0d0ff014a617` |
| D distinct requirement | `pass` | **pass** | `6dac8d0e-0f77-46c0-b279-412c790be7ec` |

## Deterministic regression (candidate SHA)

47 passed — `test_issue_200_scene_pressure_freshness`, #193, #155, B2 pressure, semantic-eval API.

## F06 sanity (deterministic, candidate SHA)

- Stale `semantic_unmet_condition` withheld after newer Player contribution — **pass**
- Perception remains speech-only / no wipe knowledge injection — **pass**
- Ignorance command not auto-rejected by structural tests — **pass**

## Portal desync

Recorded for #201 only; not remediated.

## Integration

**Not authorized in this cycle.** Ready for Governance integration review.
