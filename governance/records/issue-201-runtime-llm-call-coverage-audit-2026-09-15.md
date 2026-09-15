# Issue #201 — Runtime LLM Call-by-Call Assessment Coverage Audit

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**Investigation type:** Read-only coverage gate (no synthesis, no live experiments, no production mutation)

**Prior anchor:** `42899dd` (D-10 causal-gap adjudication)  
**Catalog substrate SHA:** `adac09c` (`v2/rp_runtime/src/application/llm-call-catalog.mjs` at audit commit `42899dd`)

**Governance correction:** Package D synthesis authorization is **paused** pending this audit. Synthesis **not** executed in this step.

---

## 1. Activation / state / weights

| Field | Value |
|-------|-------|
| Assigned / effective weight | `full` |
| Package A–D evidence | Retained |
| D-10 + causal-gap | Complete |
| Final synthesis | **PAUSED** (was authorized; not executed) |
| This audit | Complete (read-only) |

---

## 2. Authoritative catalog source

| Item | Value |
|------|-------|
| **Authority** | `v2/rp_runtime/src/application/llm-call-catalog.mjs` (`PRIMARY_RUNTIME_CATALOG`, `HARNESS_ANNEX_CATALOG`) |
| **Schema** | `hg_llm_call_catalog_v1` |
| **Policy parity** | `v2/domain_api/manifest_projection_policy.py` (`INFERENCE_KINDS`) |
| **Substrate SHA** | `adac09caa9672e474c243e85061e8e9acd17849b` |
| **Prior #201 count** | ~25 primary kinds (Packages A–C, 2026-09-14) |
| **Current count** | **27 catalog rows** / **26 unique canonical inference kinds** (production) |

**Delta from prior inventory:** `player_uniform_eligibility_verification` (#197) is now cataloged; `librarian_mediation` has **two catalog rows** (`@character`, `@narrator`) sharing one canonical kind.

**Not in primary catalog but in manifest policy (legacy aliases):** `librarian_proposal`, `librarian_proposal_contract_correction` — superseded by post-commit semantic kinds; not separate production hot-path calls.

---

## 3. Exact production inference counts

| Bucket | Count |
|--------|------:|
| **Primary runtime catalog rows** | 27 |
| **Unique canonical inference kinds (production)** | **26** |
| Harness annex (non-production) | 2 |
| Manifest policy inference kinds (incl. test/harness) | 28 |

---

## 4. Complete call-by-call matrix

Columns abbreviated in master table; full lifecycle detail in §5–§8 inventories.

**Timing key:** `sync` = round critical path; `post-commit` = per character commit join; `init` = session bootstrap.

| # | Inference kind | Agent / subsystem | Timing | Trigger | Principal output | Direct consumer | Coverage status |
|---|----------------|-------------------|--------|---------|------------------|-----------------|-----------------|
| 1 | `director_turn` | Director | sync | Every round after participation | Director decision JSON | Orchestrator → Character/Narrator | **COVERED — retain** |
| 2 | `director_semantic_qa` | Semantic evaluator | sync | After director candidate | QA pass/reject | Director phase gate | **COVERED — remove/consolidate** |
| 3 | `character_turn` | Character | sync | Selected actor turn | Structured move | Commit / Continuity | **COVERED — retain** |
| 4 | `character_semantic_evaluation` | Semantic evaluator | sync | After character move | pass/reject_hard/soft | Commit gate (#193, #200) | **COVERED — function necessary, mechanism unresolved** |
| 5 | `character_orientation` | Character cognition | sync | Pre-move when cognition enabled | Orientation + KAR | Character move manifest | **COVERED — function necessary, mechanism unresolved** |
| 6 | `librarian_mediation` | Librarian (parent: character or narrator) | sync | KAR from orientation/ST/narrator env | LibrarianKnowledgeBundle | Mapper → manifest lanes | **COVERED — function necessary, mechanism unresolved** |
| 7 | `librarian_mediation_contract_correction` | Librarian | sync retry | Primary mediation parse fail (max 1) | Corrected bundle | Same as mediation | **UNCOVERED — low decision value** |
| 8 | `storyteller_post_commit_issue_pressure` | Storyteller | post-commit | ACTIVE/ESCALATING issues | `issue_tension_pressure` proposals | Continuity overlays → `scene_pressures` | **COVERED — remove/consolidate** |
| 9 | `storyteller_post_commit_issue_pressure_contract_correction` | Storyteller | post-commit retry | Parse fail (max 1) | Corrected proposal batch | Same as #8 | **UNCOVERED — low decision value** |
| 10 | `narrator_presentation` | Narrator | sync/post-commit lane | End of narrator phase | Presentation prose | Player UI / history | **COVERED — retain** |
| 11 | `narrator_environment_cognition` | Narrator | post-commit lane | Env obligation path active | B2/env proposals | Narrator render context | **UNCOVERED — synthesis-critical** |
| 12 | `narrator_semantic_qa` | Semantic evaluator | sync | After narrator presentation | QA pass/reject | Narrator phase gate | **UNCOVERED — synthesis-critical** |
| 13 | `opening` | Opening | init | Scene bootstrap | Opening prose | Session start | **COVERED — retain** |
| 14 | `opening_segmentation` | Opening | init | Long template opener | Segmented opener | Opening validation | **UNCOVERED — low decision value** |
| 15 | `player_visibility_triage` | Player PVR | sync (pre-round) | Every player submit | uniform vs full path | PVR routing (#121) | **COVERED — retain** |
| 16 | `player_uniform_eligibility_verification` | Player PVR | sync (conditional) | After affirmative triage | verify/reject uniform | PVR gate (#197) | **COVERED — retain** |
| 17 | `player_decomposition` | Player PVR | sync (conditional) | Non-uniform path | PVR units | Perception projection (#91, #199) | **COVERED — function necessary, mechanism unresolved** |
| 18 | `storyteller_orientation` | Storyteller | sync (preamble) | Round start (unless skipped) | Orientation state | Assessment + advisory | **COVERED — remove/consolidate** |
| 19 | `storyteller_assessment` | Storyteller | sync (preamble) | Paired with orientation | StorytellerAdvisoryPackage | Director/Character lanes | **COVERED — remove/consolidate** |
| 20 | `plot_cognition_init` | Plot / Storyteller lane | sync (preamble) | Plot work pending | Initial plot overlay | Plot resume/update | **COVERED — function necessary, mechanism unresolved** |
| 21 | `plot_cognition_init_contract_correction` | Plot | sync retry | Init parse fail | Corrected init | Same as #20 | **UNCOVERED — low decision value** |
| 22 | `plot_cognition_update` | Plot | sync/post-round | Plot resume lifecycle | Plot pressure updates | Plot overlay store | **COVERED — function necessary, mechanism unresolved** |
| 23 | `plot_cognition_update_contract_correction` | Plot | sync retry | Update parse fail | Corrected update | Same as #22 | **UNCOVERED — low decision value** |
| 24 | `plot_cognition_epistemic_eval` | Semantic evaluator | sync (plot projection) | Character advisory projection | Epistemic eval | Plot→Character advisory | **UNCOVERED — low decision value** |
| 25 | `plot_cognition_epistemic_eval_contract_correction` | Semantic evaluator | sync retry | Eval parse fail | Corrected eval | Same as #24 | **UNCOVERED — low decision value** |
| 26 | `character_advisory_generation` | Semantic evaluator | sync (plot projection) | Advisory regeneration | Character advisory text | Plot projection path | **UNCOVERED — low decision value** |

### Per-call evidence types (A–E) and #201 causal linkage

| Kind | Evidence types | #201 causal challenge |
|------|----------------|----------------------|
| `director_turn` | C, D (#136) | None |
| `director_semantic_qa` | **A** (D-06/EXP-2) | **Yes** |
| `character_turn` | C, D | None |
| `character_semantic_evaluation` | **B** (#193, #199, #200) | None |
| `character_orientation` | **A** (D-03/EXP-3), C | **Yes** |
| `librarian_mediation` | B, C, D (#194 fan-out); partial A via orientation skip | **Partial** |
| `librarian_mediation_contract_correction` | D | None |
| `storyteller_post_commit_issue_pressure` | **A** (D-10), C | **Yes** |
| `storyteller_post_commit_*_contract_correction` | D | Bundled with #8 |
| `narrator_presentation` | C, D | None |
| `narrator_environment_cognition` | C, D (#194 disproportionate cost) | None |
| `narrator_semantic_qa` | C, D (analogous to D-06) | **None** |
| `opening` / `opening_segmentation` | B/C | None |
| `player_visibility_triage` | **B** (#121) | None |
| `player_uniform_eligibility_verification` | **B** (#197) | None |
| `player_decomposition` | **B**, C (#112, #194 waste cases) | None |
| `storyteller_orientation` / `assessment` | **A** (D-01, D-01b, D-01-L), C | **Yes** |
| `plot_cognition_init` / `update` | **A** (D-01, D-01a, D-10 both arms), C | **Yes** |
| `plot_cognition_*_contract_correction` | D | Retry-only |
| `plot_cognition_epistemic_eval` | C (#194 ~5.5s) | None |
| `character_advisory_generation` | C | None |

---

## 5. Checker / double-checker inventory

| Checker call | Checks | Deterministic detectable? | LLM required? | Rejection/correction rate (#201) | Removal evidence | Always-on? |
|--------------|--------|---------------------------|---------------|----------------------------------|------------------|------------|
| `director_semantic_qa` | Director candidate suitability/contradiction | Partial (structural) | Semantic judgment on advisory refs | Low in D0 (~1.2s); **removed in EXP-2 with no blind degradation** | **D-06 causal** | Yes when enabled |
| `character_semantic_evaluation` | R02b/R11/R12/R14/R15/R16 move legality | Partial (PVR, refs) | Semantic authority alignment | **Hard rejects observed** (EXP-2 failure, #200) | **Not ablated** — #193/#200 prove failures | Yes on move path |
| `narrator_semantic_qa` | Narrator fidelity / invention | Partial (F1/F2 deterministic) | Semantic redundancy checks | Pass-heavy in #194 | **Not ablated** | Yes when enabled |
| `player_uniform_eligibility_verification` | Uniform-path adversarial check | No (semantic) | **Yes** — #197 design | Rare reject path | Not ablated | Conditional |
| `plot_cognition_epistemic_eval` | Plot→Character advisory epistemic fit | Partial | Semantic | Unknown; low wall in #194 | Not ablated | Conditional on projection |

**High-priority LLM→LLM→LLM chains (architecture-debt candidates unless evidenced):**

1. **Character:** orientation → librarian_mediation → plot resume → move → **semantic_evaluation** (5+ LLM steps before commit)
2. **Preamble:** storyteller_orientation → librarian_mediation → storyteller_assessment → plot_cognition_init (serial ~52s in #194)
3. **Narrator lane:** narrator_environment_cognition → librarian_mediation → narrator_presentation → **narrator_semantic_qa**
4. **Plot projection:** plot_cognition_update → epistemic_eval → character_advisory_generation (checker/regen chain)
5. **Post-commit:** storyteller_post_commit_issue_pressure → contract_correction (retry)

**Director QA chain:** director_turn → **director_semantic_qa** — **causally challenged; remove/consolidate supported.**

---

## 6. Retry / repair inventory

| Pattern | Kinds | Trigger | Classification |
|---------|-------|---------|----------------|
| Contract correction (max 1) | `*_contract_correction` (6 kinds) | Structural JSON parse failure | **Conditional repair** — compensates weak structured output |
| Player decomposition retry | `player_decomposition` | `sir_substantive_omission` etc. | **Normal + compensating** — #194 shows expensive failure terminal |
| Character move retry | `character_turn` (re-attempt) | Semantic eval hard reject | **Expected exception handling** — not separate kind |
| Director/Narrator QA reject | semantic QA kinds | reject_hard/soft | **Semantic gate** — may trigger phase retry |

**Assessment:** Contract-correction calls are **not** architecture candidates for removal — they are conditional. Primary cognition contract strength determines their frequency.

---

## 7. Librarian / mediation inventory

| Distinct LLM inference | Role | Trigger | Knowledge infra vs LLM interpretation |
|------------------------|------|---------|--------------------------------------|
| `librarian_mediation` (@character) | Read-side bundle | Character orientation KAR | **LLM interprets retrieval request** — infrastructure still required |
| `librarian_mediation` (@narrator) | Read-side bundle | Narrator env cognition / ST paths | Same |
| `librarian_mediation_contract_correction` | Repair | Parse failure | Repair only |
| `storyteller_post_commit_issue_pressure` | Write-side proposal | Post-commit eligible | **Separate from S2a read mediation** — D-10 challenged |

**Separation:** Retrieval/entitlement/PVR infrastructure (**retain**) ≠ per-path LLM mediation fan-out (**partially tested, topology unresolved**). D0 shows **2–13× mediation calls/run variance** — observational cost signal, not causal mediation ablation.

---

## 8. Validator inventory

| Responsibility | Implementation | Class |
|----------------|----------------|-------|
| Move structural parse | Deterministic validators | **Deterministic** |
| PVR completeness / uniform routing | triage + verification + decomposition | **Hybrid** (deterministic gates + semantic decomp) |
| Director semantic QA | `director_semantic_qa` | **Semantic LLM** — D-06 challenged |
| Character semantic eval | `character_semantic_evaluation` | **Semantic LLM** — correctness demonstrated |
| Narrator semantic QA | `narrator_semantic_qa` | **Semantic LLM** — **not challenged** |
| Narrator fidelity F1/F2 | Deterministic (Host) | **Deterministic** |
| Perceptual visibility / PVR | Deterministic projection | **Deterministic** |
| Post-commit proposal continuity | Deterministic + Host finalize | **Hybrid** (LLM proposes; rules apply) |

**Do not remove correctness outcomes** (#200 R16, #193) — question is **topology** (separate call vs folded contract).

---

## 9. Prior-Issue evidence mapping (what it proves / does NOT prove)

| Issue / record | Proves | Does NOT prove |
|----------------|--------|----------------|
| **#112 / #121 / #197** | PVR routing + uniform verification prevent leak classes; always-on full decomp rejected | Optimal decomposition cost on every turn |
| **#193 / #199 / #200** | Character semantic eval catches real authority violations | Separate eval call is optimal vs stronger move contract |
| **#194** | Multi-contributor latency; env cognition disproportionate; decomposition waste cases | Causal ablation of env cognition or narrator QA |
| **#136** | Full inventory + duplication risks; validation surrounds generation | Marginal value per call |
| **D-06 / EXP-2** | Director QA removal: no blind degradation; combine/remove candidate | Narrator QA redundancy |
| **D-03 / EXP-3** | Orientation removal: scenario-split signal; topology decomposition | Orientation unnecessary on all turns |
| **D-01 / Stage-3** | Combined preamble removal hurts; Plot marginal +0.24 descriptive | Optimal Plot topology |
| **D-01-L** | ST preamble weak; post-commit retained on both arms | Post-commit value (→ D-10) |
| **D-10** | Post-commit ST remove/consolidate candidate; mechanism functioned | Plot/ST semantic redundancy |
| **Causal-gap `42899dd`** | Overlays persist; D-10 forensic gaps | Per-call consumption |

---

## 10. Calls directly challenged by #201 (causal)

**7 unique canonical kinds** with Package D causal isolation:

1. `director_semantic_qa` (D-06)
2. `character_orientation` (D-03)
3. `storyteller_orientation` (D-01, D-01b, D-01-L)
4. `storyteller_assessment` (same)
5. `plot_cognition_init` (D-01, D-01a, D-10 control/ablated both had plot)
6. `plot_cognition_update` (same)
7. `storyteller_post_commit_issue_pressure` (D-10)

**Partial:** `librarian_mediation` (orientation-mediated reduction only in EXP-3).

**Not challenged:** 18 kinds (69% of catalog).

---

## 11. Calls justified primarily by prior correctness evidence (B)

| Kind | Basis |
|------|-------|
| `player_visibility_triage` | #121 |
| `player_uniform_eligibility_verification` | #197 |
| `player_decomposition` | #112, #91, #199 (function); gating unresolved |
| `character_semantic_evaluation` | #193, #199, #200 |
| `opening_segmentation` | Opening validation path |

---

## 12. Observational / historical-only calls (C/D dominant)

| Kind | Notes |
|------|-------|
| `director_turn` | Core; never ablated — necessary by role |
| `character_turn` | Core |
| `narrator_presentation` | Core output |
| `librarian_mediation` | Runs; fan-out varies; not fully ablated |
| `narrator_environment_cognition` | #194 cost observational |
| `narrator_semantic_qa` | Pass-heavy; analogous to removed Director QA |
| `plot_cognition_epistemic_eval` | Low cost observational |
| `character_advisory_generation` | Low frequency |
| All `*_contract_correction` | Retry-only observational |

---

## 13. Coverage status counts (mutually exclusive)

| Status | Count | % of 26 |
|--------|------:|--------:|
| **COVERED — retain** | 6 | 23% |
| **COVERED — remove/consolidate** | 4 | 15% |
| **COVERED — function necessary, mechanism unresolved** | 6 | 23% |
| **UNCOVERED — low decision value** | 8 | 31% |
| **UNCOVERED — synthesis-critical** | 2 | 8% |
| **INAPPLICABLE** (harness annex) | 2 | — |

### Overlapping evidence-type counts (non-exclusive)

| Evidence bucket | Kinds (approx.) |
|-----------------|----------------:|
| Direct causal (#201 A) | 7 (+1 partial) |
| Strong correctness (B) | 5 |
| Observational/historical (C/D) | 18 |
| No meaningful evidence (E) | 0 — all kinds have at least historical/rationale |

---

## 14. Architecture-bureaucracy heat map (ranked clusters)

| Rank | Cluster | Calls involved | Concern |
|------|---------|----------------|---------|
| 1 | **Round preamble stack** | ST orientation/assessment, librarian_mediation, plot init/update | Serial ~52s+; D-01 shows combined removal hurts but ST weak alone |
| 2 | **Character pre-commit chain** | orientation, mediation, plot resume, move, semantic_eval | Deepest per-turn LLM chain (#136) |
| 3 | **Semantic QA pair** | director_semantic_qa (**challenged**), narrator_semantic_qa (**not**) | LLM-checking-LLM; asymmetric evidence |
| 4 | **Narrator post-commit lane** | env_cognition, mediation, presentation, semantic_qa | #194 binding tail; env cognition disproportionate |
| 5 | **Plot projection checker chain** | epistemic_eval, advisory_generation | Low cost but pure interpretive stack |
| 6 | **Post-commit ST pressure** | issue_pressure + correction | **Challenged** — remove candidate |
| 7 | **PVR stack** | triage, verification, decomposition | Correctness-critical; cost/gating unresolved |

---

## 15. UNCOVERED — synthesis-critical (ranked)

### 1. `narrator_semantic_qa`

| Field | Value |
|-------|-------|
| Why synthesis-critical | Director QA (structural twin) removed without blind harm (D-06); narrator QA is the remaining always-on presentation checker — consolidation vs retain affects A2/A4 QA topology |
| Plausible dispositions | Remove/consolidate with Director QA; fold into narrator contract; retain dual QA |
| Cheapest resolution | **Mirror D-06:** `narratorSemanticQaEnabled: false` tranche (proposed D-07; not executed) |
| Repo-only sufficient? | **Partial** — strong analogy, not causal proof |
| Live ablation necessary? | **Recommended** for high-confidence consolidation claim |
| Scope if live | 4 runs (2×2 scenario), blind optional — same as EXP-2 |

### 2. `narrator_environment_cognition`

| Field | Value |
|-------|-------|
| Why synthesis-critical | #194: ~55.7s, ~11.5k reasoning tokens for narrow B2 need; binds post-commit lane — affects cost/latency architecture and tiering recommendations |
| Plausible dispositions | Tier/conditional activation; fold into presentation; retain always-on |
| Cheapest resolution | Forensic replay of D0/D-10 sessions for obligation frequency + skip hook audit (read-only); optional D-04 live |
| Repo-only sufficient? | **Partial** — cost proven; marginal value not |
| Live ablation necessary? | **Optional** — synthesis can recommend tiering with uncertainty |
| Scope if live | Scenario-matched runs with env cognition disabled |

**Not synthesis-critical (carried as uncertainty):** contract-correction kinds, plot epistemic chain, `character_advisory_generation`, `opening_segmentation` — unlikely to flip A0/A4 direction.

---

## 16. Minimum proposed evidence work (not executed)

| Priority | Work | Type | Resolves |
|----------|------|------|----------|
| **1** | **D-07:** `narratorSemanticQaEnabled: false` mirror of EXP-2 | Live ablation (4-run) | `narrator_semantic_qa` |
| **2** | Read-only D-04 forensics: env cognition obligation rate across D0/D-10 evidence | Repo-only | `narrator_environment_cognition` cost/value |
| **3** (optional) | D-04 live only if Governance requires causal env-cognition claim | Live | Tiering vs removal |

**Not proposed:** 25-call campaign; per-contract-correction ablations; full librarian mediation bypass (high blast radius).

---

## 17. Governance recommendation

### **B. Small targeted evidence gap**

**Rationale:**

- **Complete catalog coverage achieved:** all 26 production kinds classified; none omitted.
- **Strong synthesis direction already supported without per-call ablation:** preamble ST remove/consolidate (D-01-L), post-commit ST remove/consolidate (D-10), Director QA remove/consolidate (D-06), Plot retain function (Stage-3), PVR/semantic-eval correctness retain.
- **One high-leverage gap remains:** `narrator_semantic_qa` is the largest **untested symmetric** member of the semantic-QA bureaucracy cluster after Director QA removal.
- **`narrator_environment_cognition`** is synthesis-critical for **cost/tiering** claims but can be carried into synthesis as qualified uncertainty if Governance declines D-04 live.
- **69% of kinds lack direct #201 causal challenge** — full per-call ablation campaign is **not** decision-worthy per §12 threshold.

**Not C:** Material multi-call experimentation is unnecessary for first-principles architecture direction; uncovered low-decision-value kinds (8) dominate by count.

**Not A (yet):** Governance's stated concern ("not demonstrated for all calls") is **partially resolved** by this matrix, but **narrator_semantic_qa** absence leaves the QA-layer consolidation story incomplete.

---

## 18. Unresolved uncertainty

| Item | Carry into synthesis |
|------|---------------------|
| Narrator QA marginal value | Pending D-07 or explicit analogy caveat |
| Env cognition tiering | #194 cost vs benefit |
| Librarian mediation fan-out | Partial orientation evidence only |
| Character eval vs stronger move contract | Correctness vs topology |
| Per-call consumption for observational kinds | General limitation |

---

## 19. Durable record / Governance decision

| Artifact | SHA / path |
|----------|------------|
| This audit | `governance/records/issue-201-runtime-llm-call-coverage-audit-2026-09-15.md` |
| Catalog authority | `adac09c` @ `llm-call-catalog.mjs` |
| Synthesis | **NOT executed** |

### Exact Governance decisions required

1. **Accept** call-by-call coverage audit as Package D synthesis gate input.
2. **Choose:** resume synthesis with caveats (**A path**) **OR** authorize **D-07 narrator QA bypass** (minimum targeted gap) before synthesis.
3. **Decline or defer** D-04 live / full mediation ablation unless broader gap deemed material.
4. Keep #201 `investigating` until synthesis explicitly authorized.

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
