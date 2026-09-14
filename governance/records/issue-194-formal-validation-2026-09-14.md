# Issue #194 — Formal Validation Record

**Date:** 2026-09-14  
**Issue:** [#194](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/194)  
**Implementation candidate:** `5e1b726f712e60d1e600a5846c1734eb017066a5`  
**Validation PR:** [#196](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/196)  
**Disposition:** **NOT VALIDATED — blockers remain**

## Activation

| Item | Value |
|------|-------|
| Base (`origin/main`) | `9548847` |
| Implementation candidate | `5e1b726` |
| Validation branch / PR head | `issue-194-formal-validation` @ `5e1b726` (evidence commits pending) |
| Drift | None material on `origin/main` outside #194 lineage |
| Working tree | Clean after evidence capture |
| Issue state | `implemented` / In Progress / Implemented / P2 (unchanged) |

## Package A — Deterministic regression

**Python (105 passed):**

```bash
python -m pytest \
  v2/domain/tests/test_issue_194_pvr_coverage_fidelity.py \
  v2/domain/tests/test_issue_194_environment_deliberation_profile.py \
  v2/domain/tests/test_issue_124_semantic_normalization.py \
  v2/domain/tests/test_issue_121_uniform_projection.py \
  v2/domain/tests/test_issue_151_environment_cognition_status.py \
  v2/domain/tests/test_issue_131_narrator_context_packaging.py \
  v2/domain/tests/test_issue_89_environment_sufficiency.py \
  v2/domain/tests/test_issue_49_narrator_environment.py -q
```

**Node (8 passed):**

```bash
cd v2/rp_runtime
node --test tests/issue-194-env-cognition-profile-safety.test.mjs \
             tests/issue-194-player-decomposition-retry.test.mjs \
             tests/issue151-environment-cognition-substrate.test.mjs
```

All required routing matrix rows covered deterministically, including mediation-path and bounded escalation substrate test.

## Package B — Live F06 end-to-end

**Session:** `hg-session-969a153e-12a0-40dc-90c3-e7797dc21fe8`  
**Operation:** `9d9c4b2f-bb5e-4967-ac75-1865ca2d6acf`  
**Round:** `hg-round-dba2fede-1df2-4070-bfae-2c1e4d1ec748`  
**Commit:** `hg-commit-89aa62ae-01a1-4f26-aa13-b2dc5b058bcb`  
**Evidence:** `governance/records/issue-194-live-validation-2026-09-14.json`

### F06 PVR (live)

| Metric | Historical F06 | Live validation |
|--------|----------------|-----------------|
| Triage route | semantic decomposition required | **`uniform_projection_safe: true`** |
| Decomposition attempts | 2 | **0** (triage bypass) |
| Decomposition wall | ~41.5s | **0s** |
| PVR outcome | invalid/excluded | **valid** (`uniform_projection`) |

**Blocker:** Live full-turn did **not** reproduce the historical F06 **semantic decomposition** path. I1 punctuation-absorption mechanism is proven deterministically, not on this live routing.

### F06 environmental cognition (live)

| Metric | Historical F06 | Live validation |
|--------|----------------|-----------------|
| Cognition calls (round) | 1 | **3** (2 commits; first pair probe+escalation) |
| Combined probe+deep wall (1st commit) | ~55.7s (single deep) | **21,223ms** (3,729 + 17,494) |
| Reasoning tokens (env cog total) | ~11,454 | **3,343** |
| Escalation | n/a | **`deep-escalation` observed** |

**Blocker:** Constrained probe did not yield a compliant single-B2 result; bounded escalation fired. Safety mechanism works, but live F06 does **not** satisfy acceptance criterion “compliant narrow result avoids escalation.”

### End-to-end timing (#173)

| Metric | Historical ~ | Live |
|--------|-------------|------|
| Player-visible latency | 224,289ms | **208,646ms** |
| Round internal serial | 167,500ms | **189,825ms** |
| Character turn (1st) | 89,100ms pre-commit | **30,405ms** character prep phase |
| Post-commit parallel (actual) | ~78,200ms | **~44,990ms** (1st commit span) |

`post_commit_section` attributed sum (49,225ms) is **not** elapsed wall.

## Package C — Escalation safety

Proven via `issue-194-env-cognition-profile-safety.test.mjs` (production substrate): constrained probe → structural deep classification → re-prepare override → single deep re-inference before KAR.

## Package D — Complex decomposition guard

Live `complex_dense_seiza_japan`: **5 units**, kinds `observable_event`/`internal`/`speech`, **1 attempt**, accepted. Equivalent to #112/#124 authoritative corpus.

## Package E — Complex environmental cognition

Deterministic prepare-time deep routing proven for conflicts, carryover B2, multi-location, stable sub-referents, continuity_turn_index>1 (Package A tests).

## Package G — RP quality

Presentation produced; Ayame active and responsive; house-number grounding coherent in narrator/character prose; no #194-caused authorship regression observed. Unrelated historical fidelity items out of scope.

## Package H — Quota attestation

No #194 max-token cap introduced. Constrained profile uses `reasoningEffort: off` / `thinking: disabled` only. Role profiles uncapped (`reasoningEffort: low`, no `maxTokens` on narrator profile).

## Blockers (prevent validated transition)

1. **I1 live F06 semantic path not exercised** — triage routed `uniform_projection`; cannot claim live F06 decomposition improvement on the historical mixed-semantics route.
2. **I2 live F06 narrow path not satisfied** — constrained probe escalated to deep; acceptance requires compliant narrow B2 without escalation on F06-shaped envelope.

## Recommended follow-up (within #194 or Governance-directed)

- Run bounded live semantic-decomposition slice with triage forced to semantic path and F06 attempt-0 replay envelope.
- Run bounded live env-cognition slice on F06-shaped prepare envelope with compliant single-B2 mock/characterization fixture to confirm constrained-no-escalation happy path under production substrate.

## Chain of custody

#193 and historical Issues unchanged. Issue remains `implemented`.
