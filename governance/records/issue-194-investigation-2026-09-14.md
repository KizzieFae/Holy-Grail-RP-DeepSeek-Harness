# Issue #194 — First-Turn Inference Efficiency Investigation (Session F06)

**Date:** 2026-09-14  
**Issue:** [#194](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/194)  
**Phase:** `investigating`  
**Assigned / effective weight:** `standard` / `full`  
**Bootstrap profile:** Full  
**Investigation anchor:** `768fa5d738500bfe8b52325490a4c1121ca87e59`  
**Primary session:** `hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40`  
**Scenario:** `ayame_household_entry_evaluation`

## Activation

| Item | Value |
|------|-------|
| Operation | `006fa8a9-65a5-424b-995d-d58f1547a8e9` |
| Round | `hg-round-4e1765c6-b3a6-4d2b-b8e6-b748ac96e53a` |
| Commit | `hg-commit-72544ec1-d599-441b-a93a-b3e760bdcd4a` |
| Player post | `hg-hist-ed794be4-be74-4dbb-b33d-bb29c73b22b1` |
| Reconstruction | `tools/investigation/reconstruct_round_latency.py --attribution` |

## Executive summary

A knock-only first Player turn required **~224s** player-visible latency. Cost is **multi-contributor and partially coupled** — no single stage is sole cause. Three high-value investigation targets emerge:

1. **Player decomposition/PVR (~41.5s inference, 0 usable PVR)** — two semantic attempts, terminal `invalid_excluded` (`sir_substantive_omission` / substantive-not-fully-covered), no demonstrated downstream prose benefit.
2. **Narrator environmental cognition (~55.7s, ~11.5k reasoning tokens)** — narrow `house_number` B2 need; disproportionate reasoning vs output (`visible house number by the entrance`).
3. **Opening-turn preamble stack (~52s serial)** — storyteller orientation/assessment, librarian mediation, plot cognition init on a simple first turn.

Post-commit narrator lane (**~78s actual wall**) binds after commit; env cognition dominates that lane.

**Root-cause model:** structural critical-path accumulation across **several independent contributors**, with **retry waste** and **complexity-insensitive cognition** as amplifying mechanisms — not a single defect.

## Critical path (authoritative wall)

| Segment | Wall (ms) | Notes |
|---------|----------:|-------|
| Pre-round (segmentation + triage + decomposition + persist) | ~47,000 | Blocks round start; decomposition ~41.5s |
| `round_preamble_serial` | 52,101 | Storyteller + librarian + assessment + plot init |
| `director_phase` | 3,291 | |
| `character_prep_phase` | 33,661 | Orientation ~17.6s |
| Character move + semantic eval | ~5,500 | |
| `post_commit_lane_narrator` | 78,156 | **Binding post-commit tail**; env cog ~55.7s inside |
| `domain_record_presentation` | 4,587 | |
| **Player-visible operation** | **224,289** | proven |

`post_commit_section` attributed sum **156,330 ms** is lane+join double-count per #173 — **not** elapsed wall.

## Decision-value table (material inference stages)

| Stage | Wall | Tokens (rt/tot) | Consumed? | Decision/state | Visible | Class | Hypothesis |
|-------|-----:|-----------------|-----------|----------------|---------|-------|------------|
| opening_segmentation | 2.4s | — / 685 | yes | opening canon | indirect | supporting | correct as-is |
| player_visibility_triage | 0.7s | — / 605 | yes | routes decomposition | no | supporting | correct as-is |
| player_decomposition ×2 | 41.5s | 8555 / 19366 | **no usable PVR** | `invalid_excluded` | degradation only | **fallback/retry waste** | complexity gate or earlier exit |
| storyteller_orientation | 2.8s | 185 / 983 | yes | preamble context | indirect | supporting | correct as-is |
| librarian_mediation (pre) | 23.3s | 1913 / 11311 | partial | story mediation | indirect | **worthwhile refinement** | defer/slim on T1 simple |
| storyteller_assessment | 15.2s | 2163 / 8700 | yes | assessment state | indirect | supporting | defer on simple T1? |
| plot_cognition_init | 10.5s | 1467 / 6099 | yes | plot lane bootstrap | indirect | supporting | defer on simple T1? |
| director_decision | 1.9s | 87 / 1144 | yes | Ayame selected | yes | decision-producing | correct as-is |
| director_semantic_qa | 1.2s | — / 1395 | yes | pass gate | no | validation | correct as-is |
| character_orientation | 17.6s | 3132 / 7698 | yes | move context | indirect | supporting | review T1 necessity |
| plot epistemic eval ×4 | ~5.5s | — / 2688 | advisory | plot lane | no | observational | low priority |
| character_move | 4.3s | 244 / 2408 | yes | committed move | yes | decision-producing | #193 scope |
| character_semantic_eval | 1.3s | — / 5156 | yes | pass (pre-R16) | no | validation | #193 scope |
| narrator_environment_cognition | 55.7s | 11454 / 24841 | yes | B2 `house_number` proposal | partial (`brass` in presentation) | **disproportionate grounding** | complexity-tiered cognition |
| librarian_mediation (post) | 7.1s | 243 / 5283 | yes | env mediation | indirect | supporting | correct as-is |
| narrator_presentation | 9.0s | 1533 / 8294 | yes | presentation text | yes | decision-producing | correct as-is |
| narrator_semantic_qa | 1.1s | — / 6566 | yes | pass | no | validation | correct as-is |
| storyteller_post_commit_issue_pressure | 4.7s | 325 / 4673 | yes | post-commit advisory | no | observational | low priority |

**Cumulative observed inference wall (LLM attempts only):** ~206s (sum of per-attempt walls; overlaps exist across parallel lanes).

## PVR / decomposition analysis

| Attempt | Evidence | Wall | Reasoning | Outcome |
|---------|----------|-----:|----------:|---------|
| 0 | `aed90531-…` | 13,330 ms | 2,657 | Retry: `sir_substantive_omission` |
| 1 | `3c8389b1-…` | 28,225 ms | 5,898 | Terminal: `invalid_excluded`, notes: *substantive source not fully covered* |

**Terminal PVR record:** `pvr-player-fail-5475c4bf-…` — `units: []`, `validation_status: invalid_excluded`, generation from retry-1 evidence.

**Downstream consumption:** No usable per-character perceptual units. Director retained full `user_turn_source` (orchestration contract). Character transcript used degradation/unavailable projection path — **no demonstrated Player-visible prose benefit** from decomposition spend.

**Causal inefficiency (hypothesis):** bounded retry policy + strict substantive-coverage checker + model reasoning over-splitting/under-covering on a 17-word knock line → **~41.5s spend with zero PVR value**. Mechanism may combine retry policy, prompt/evaluator behavior, and normalization — **not yet isolated to one owner**.

## Environmental cognition analysis

**Evidence:** `318b7a1a-4ea3-4972-b75e-1c119e5d17f3` — 55,728 ms wall, 11,454 reasoning tokens.

**Need declared:** house number / exterior identifier for Player glance-and-check action.

**Output:** B2 `house_number` = `visible house number by the entrance`; `response_sufficient: false` (Host validation required).

**Value produced:** modest generic grounding; presentation later added `"brass"` specificity (separate fidelity concern, #193 informational).

**Disproportion:** ~11.5k reasoning tokens and ~56s wall for a single narrow B2 proposal on a trivial opening action. Model reasoning trace shows extensive deliberation over scope/category rules — **deep cognition triggered for a shallow need**.

## Comparative characterization

| Case | Source | Complexity | Decomposition | Env cognition | Notes |
|------|--------|------------|---------------|---------------|-------|
| **F06 simple opening** | live session F06 | low (knock) | 2 attempts, 41.5s, invalid PVR | 55.7s / 11.5k rt | baseline |
| **9065f006 complex** | audit fixture + `e2e-session-quality-audit-9065f006.md` | high (18 turns) | 36/36 attempts failed (malformed JSON); ~112k tokens | present, timing not indexed on live copy | decomposition valuable when working, but failure mode differs |
| **Stress / over-optimization guard** | F06 PVR invalid + 9065f006 total decomposition failure | — | shows system pays heavy decomposition cost even when output unusable | env cog cost weakly scales with need in F06 | supports **complexity-sensitive gating** hypothesis |

**Conclusion:** Expensive mechanisms do **not** reliably scale effort with decision complexity on F06; 9065f006 shows decomposition can matter on complex turns when successful.

## Historical lineage constraints

| Issue | Relevance to #194 |
|-------|-------------------|
| #124 | `sir_substantive_omission` contract; retry discipline — do not remove without evidence |
| #151 | Env cognition sufficiency — correctness gate, not efficiency owner |
| #152 | Natural-completion characterization — token data is diagnostic, not optimization target |
| #158 / #173 | Timing substrate; wall vs attributed-sum semantics |
| #131 | Projection dedup did not eliminate F06 env-cog cost |
| #176 | Layer B serial topology deliberately retained — parallelization proposals must respect |
| #193 | Closed; orthogonal turn-quality scope |

## Findings (classification separate from disposition)

| ID | Observation | Class | Disposition rec. |
|----|-------------|-------|------------------|
| F194-1 | ~41.5s decomposition → `invalid_excluded` PVR on 17-word knock | worthwhile refinement | investigate PVR path; no removal without consensus |
| F194-2 | Env cog ~56s / 11.5k rt for generic house-number B2 | worthwhile refinement | complexity-tiered cognition hypothesis |
| F194-3 | ~52s opening preamble on first simple turn | architectural debt | conditional/deferred preamble hypothesis |
| F194-4 | ~224s multi-stage accumulation | architectural debt | targeted interventions, not global shallowing |
| F194-5 | Pre-commit librarian mediation ~23s on T1 | worthwhile refinement | scope/defer hypothesis |
| F194-6 | Director/character move stack modest (~12s) | correct as-is | no change |
| F194-7 | Post-commit narrator lane binds at ~78s | architectural debt | env cog dominates; presentation modest |

## Proposed interventions (hypotheses — NOT authorized)

### P1 — Complexity-aware decomposition/PVR path (high confidence)

- **Inefficiency:** 41.5s retry waste, zero PVR value on simple uniform turn.
- **Owner:** orchestration + player decomposition/PVR (`player-decomposition-phase`, normalization).
- **Intervention:** classify simple/uniform player turns before second semantic attempt; fast-path or checker-tuned acceptance when coverage is materially complete.
- **Unchanged:** valid PVR on complex turns; #124 SIR contracts on substantive turns.
- **Benefit:** ~20–40s on F06-class turns.
- **Risk:** under-projection on subtle mixed turns.
- **Validation:** F06 replay + 9065f006 complex turn + mixed-turn fixture.

### P2 — Tiered environmental cognition by need complexity (high confidence)

- **Inefficiency:** 55.7s / 11.5k rt for narrow B2.
- **Owner:** narrator env cognition assembly + orchestration trigger policy.
- **Intervention:** shallow path when need is single explicit Player-referenced identifier and baseline+occurrence nearly sufficient; preserve deep path for ambiguous/multi-need cases.
- **Unchanged:** #151 sufficiency/fail-closed semantics.
- **Benefit:** potentially ~30–50s on F06-class narrow needs.
- **Risk:** under-grounding if classifier wrong.
- **Validation:** F06 + complex env scenario + cannot_safely_resolve cases.

### P3 — Conditional opening-turn preamble (medium confidence)

- **Inefficiency:** ~52s serial preamble before director on knock-only turn.
- **Owner:** round orchestration / storyteller preamble scheduling.
- **Intervention:** defer non-critical storyteller assessment/plot init on low-complexity first turns.
- **Unchanged:** #176 serial dependencies where proven.
- **Benefit:** ~20–50s if safely deferrable.
- **Risk:** missing continuity/plot context on scenarios that need it.
- **Validation:** scenario matrix with/without deferred preamble.

### P4 — Pre-commit librarian mediation slimming (medium confidence, coupled)

- **Inefficiency:** 23.3s pre-commit mediation on T1.
- **Owner:** librarian mediation phase.
- **Benefit:** ~10–20s if inputs thin.
- **Coupling:** may interact with P3.

**Smallest high-confidence set:** **P1 + P2** (independent owners, largest F06 deltas).

## Explicit non-changes

- No global reasoning/token caps (#152 natural-completion policy).
- No removal of env cognition or decomposition outright.
- No Director/Narrator semantic QA removal.
- No #193 R16 reopening.
- No timeout budget tuning as primary fix.
- No `post_commit_section` metric reinterpretation work as remediation.

## Validation design (for future implementation)

1. F06 replay with #173 wall attribution before/after.
2. Token/natural-completion record per changed inference kind (#152).
3. Complex-turn guard: 9065f006-class or richer ayame scenario turn.
4. PVR correctness: valid mixed/complex turns still produce usable PVR.
5. RP-quality regression vs #193 criteria where overlapping.
6. No arbitrary latency SLA — report decision-value preservation.

## Governance questions

1. **Uniform/simple-turn fast path:** Is Governance willing to skip or shorten full semantic decomposition when triage marks a turn uniform/low-complexity (#121 alignment)?
2. **Env cognition depth tiers:** Should narrow Player-referenced identifiers use a shallow cognition profile while preserving deep cognition for multi-need/ambiguous cases?
3. **Opening preamble deferral:** Which storyteller/plot cognition stages are mandatory on turn 1 vs deferrable without continuity risk?
