# Issue #197 — Investigation Record

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Git SHA:** `79cdb5a`  
**Disposition:** Investigation complete; **READY FOR GOVERNANCE REVIEW** (no implementation)

## Cleanup (Phase 0)

Nine local untracked post-#194 artifacts deleted as superseded/ephemeral:

| Path | Disposition | Rationale |
|------|-----------|-----------|
| `governance/records/issue-193-causality-baseline-9548847.json` | **Deleted** | Incidental #194 causality probe; conclusions in merged `issue-194-formal-validation-2026-09-14.md` |
| `governance/records/issue-193-causality-baseline-9548847.stdout.txt` | **Deleted** | Stdout companion; superseded |
| `governance/records/issue-193-causality-baseline-9548847-rerun.json` | **Deleted** | Rerun companion; superseded |
| `governance/records/issue-193-causality-baseline-9548847-rerun.stdout.txt` | **Deleted** | Stdout companion; superseded |
| `governance/records/issue-193-causality-candidate-5e1b726.json` | **Deleted** | Incidental #194 causality probe; superseded |
| `governance/records/issue-193-causality-candidate-5e1b726.stdout.txt` | **Deleted** | Stdout companion; superseded |
| `governance/records/issue-193-causality-candidate-5e1b726-rerun.json` | **Deleted** | Rerun companion; superseded |
| `governance/records/issue-193-causality-candidate-5e1b726-rerun.stdout.txt` | **Deleted** | Stdout companion; superseded |
| `governance/records/issue-194-formal-validation-completion-2026-09-14.md` | **Deleted** | Local draft superseded by #194 closure comment |

No unique audit evidence required retention beyond merged records and Issue comments.

## Root cause (summary)

**Proposal failure + acceptance/enforcement failure.**

1. **Proposal:** Live triage model (`deepseek-v4-flash`, reasoning off) returns `uniform_projection_safe: true` for F06 mixed text because implicit internal-state verbs (`steeled herself`) embedded in observable action are not recognized as private cognition.
2. **Acceptance:** DSH routing treats any parsed `uniform_projection_safe === true` as authoritative (`isAffirmativeUniformProjectionSafe`); no secondary semantic rubric checker.
3. **Enforcement gap:** #121 `mandatory_negative` corpus is **test/validation contract only** — not consulted at runtime. Domain post-submit validation checks uniform **shape/provenance**, not triage semantic correctness.

## Bounded live reproduction (`issue-197-investigation-2026-09-14.json`)

| Scenario | Expected | Observed | Result |
|----------|----------|----------|--------|
| F06 mixed (×3) | `full_pvr` | 3/3 `uniform_projection` | **false_simple** |
| Positive simple action | `uniform_projection` | `uniform_projection` | correct |
| `neg_internal_cognition` | `full_pvr` | `full_pvr` | correct |
| F06 variant (no internal) | `uniform_projection` | 2/2 `uniform_projection` | correct |
| `neg_concealed_action` | `full_pvr` | `full_pvr` | correct |

F06 false-simple is **reproducible 3/3** on current `main`. Variant without `steeled herself` routes correctly, isolating the internal-state span as the failure trigger.

## Proposed remediation architecture (no implementation)

See Issue #197 investigation comment and Governance review. Preferred direction: add runtime fail-safe enforcement at orchestration boundary when semantic triage affirms uniform-safe — without destroying legitimate uniform fast path — consistent with `contextual intelligence proposes meaning; deterministic authority decides legality`.
