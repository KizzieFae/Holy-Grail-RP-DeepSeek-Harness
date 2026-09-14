# Issue #197 — Implementation Characterization Provenance Remediation

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Disposition:** **Outcome A — provenance reconstructable; observations preserved**

## Problem

`governance/records/issue-197-implementation-characterization-2026-09-14.json` recorded `git_sha: 65512d5` while the implementation candidate is `adac09c`.

## Reconstructed execution state

| Field | Value |
|-------|-------|
| **Execution timestamp** | `2026-09-14T02:57:46.840Z` |
| **Execution HEAD** | `65512d556b8c6ea3439e47e250824059611a6c12` (`65512d5`) |
| **Implementation committed** | **No** — `adac09c` was created after characterization |
| **Working tree at execution** | **Dirty** — full #197 implementation present but uncommitted |
| **Runtime surface** | `runPlayerVisibilityTriagePhase` + `runPlayerUniformEligibilityVerification` via `issue197-implementation-characterization.mjs` |
| **SHA population mechanism** | `git rev-parse HEAD` only (no dirty-tree capture at original run) |

## Forensic proof the implementation tree executed

1. **Verifier artifact absent at HEAD:** `player-uniform-eligibility-verification.mjs` does not exist in `65512d5` (`git show 65512d5:...` fatal).
2. **Verifier output present in observations:** affirmative scenarios record `checker_result.verification` with inference ids ending in `-uniform-eligibility-verification` and dispositions `clear` — impossible without the implementation code.
3. **Transcript ordering:** characterization JSON written before the `adac09c` implementation commit in the same Implementation-AI session.
4. **Content identity:** `git diff 65512d5..adac09c` for routing/orchestration files matches the behavior observed (affirmative-only verifier invocation, audit fields, fail-safe gate).

## Resolution

- **Did not rerun** the six-scenario live characterization (Outcome A).
- **Preserved** original timings and route observations unchanged.
- **Supplemented** the durable JSON with an explicit `provenance` addendum linking execution HEAD, dirty working-tree state, and resulting implementation commit `adac09c`.
- **Added** `resolveGitProvenance()` helper for future candidate-tied evidence scripts.

## Candidate lineage after remediation

| Commit | Role |
|--------|------|
| `65512d5` | Investigation / consensus-challenge evidence |
| `adac09c` | Implementation candidate (semantic content executed pre-commit) |
| *(remediation commit)* | Provenance-only evidence correction |
