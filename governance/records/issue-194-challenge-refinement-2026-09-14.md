# Issue #194 — Challenge & Refined Proposal Report

**Date:** 2026-09-14  
**Issue:** [#194](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/194)  
**Phase:** `investigating` (unchanged — **not** `consensus_reached`)  
**Assigned / effective weight:** `standard` / `full`  
**Bootstrap profile:** Full  
**Refinement anchor:** `95488474b2fec1656d6293b10dc07652244d253a`  
**Primary session:** `hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40`  
**Prior investigation record:** `governance/records/issue-194-investigation-2026-09-14.md`

---

## A. Activation

| Item | Value |
|------|-------|
| #194 state | `OPEN` / label `investigating` |
| Project | **In Progress** / **Investigating** / **P2** |
| #193 | CLOSED / Done / Done / P2 (unchanged) |
| Repository anchor | `9548847` on `main` |
| Working tree | clean at refinement start |
| Implementation authority | **none** |
| Method | read-only forensic replay + deterministic normalization replay |

---

## B. F06 decomposition causal reconstruction

**Player source (normalized, 93 chars, indices 0–92):**

`Kizzie glanced up, double-checking the house number and then steeled herself before knocking.`

**Pre-decomposition triage** (`267644f3-…`, 743 ms):

- Checker output: `uniform_projection_safe: false`, `reason: requires_semantic_decomposition`
- **Correct routing:** mixed observable action + internal cognition (`steeled herself`) is not affirmatively uniform-safe per #121 checker contract.

### Attempt 0 — `aed90531-e538-4866-8b73-e95a2298f748`

| Stage | Detail |
|-------|--------|
| **1. Source / segmentation supplied** | Full 93-char normalized source (single substantive Player post). |
| **2. Request / instructions** | Standard `player_decomposition` manifest: verbatim excerpt units; completeness rule — every substantive (non-whitespace) character must appear in exactly one unit; no overlap; whitespace between units may be omitted from excerpts. |
| **3. Model output** | 2 units: (a) `observable_event` / `present` — `"Kizzie glanced up, double-checking the house number"`; (b) `internal` / `private` — `"and then steeled herself before knocking"`. |
| **4. Normalized units** | Parsed as two SIR units; verbatim substrings found at spans **[0,51)** and **[52,92)**. |
| **5. Checker input** | `_substantive_mask` over full source: all non-whitespace indices substantive, including index **92** (`'.'`). |
| **6. `sir_substantive_omission` reason** | `substantive source not fully covered` — `partial_exists` true, no complete non-overlapping assignment covers index 92. |
| **7. Believed omitted material** | **Trailing sentence-terminal period only** (char index 92). Semantic split otherwise contiguous: [0,51)+[52,92) leaves `.` uncovered. |
| **8. Retry delta** | Retry prompt adds `ATTEMPT_2_OUTPUT_RETRY` + generic `sir_substantive_omission` guidance: *"Account for all substantive player source content…"* — **does not identify the period**. |
| **9. Wall / reasoning** | 13,330 ms; 2,657 reasoning tokens. |

### Retry 1 — `3c8389b1-49f5-4dc0-9705-5abb67768570`

| Stage | Detail |
|-------|--------|
| **3. Model output** | 3 units: `observable_event` `"Kizzie glanced up,"`; `observable_event` `"double-checking the house number"`; `internal` `"and then steeled herself before knocking"`. |
| **4. Normalized spans** | **[0,18)**, **[19,51)**, **[52,92)** — still end at index 92 (exclusive), **period still omitted**. |
| **6–7. Checker** | Same failure: index 92 uncovered. |
| **9. Terminal exclusion** | `invalid_excluded`; `validation_notes: ["substantive source not fully covered"]`; PVR `units: []`. |
| **Wall / reasoning** | 28,225 ms; 5,898 reasoning tokens. |

### Deterministic replay proof

Re-running `normalize_player_semantic_decomposition` on both attempt outputs:

- **As recorded:** both → `accepted: false`, `failure_class: sir_substantive_omission`.
- **With only trailing `.` appended to last unit text:** both → **`accepted: true`**.

The semantic entitlement split (observable prelude + internal resolve + knock-adjacent phrasing grouped internal) is **normalization-acceptable**; failure was **mechanical completeness**, not wrong mixed-unit semantics.

---

## C. PVR causal conclusion

### Should the existing correct contract have succeeded without retry?

**Yes.**

A contract-compliant decomposition existed on attempt 0: same two-unit semantic split with the last excerpt ending `…knocking.` (or equivalent non-overlapping coverage including index 92). Normalization accepts that output.

### Actual inefficiency mechanism (confidence: **high**)

| Mechanism | Role |
|-----------|------|
| **Model output contract non-compliance** | Omitted terminal `.` despite otherwise correct verbatim spans. |
| **Opaque retry guidance** | `sir_substantive_omission` retry text is generic; does not surface uncovered indices/characters. |
| **Retry ineffectiveness** | Retry 1 increased unit count and reasoning (~2.2×) but repeated the same omission. |
| **Over-reasoning amplifier** | ~8.5k combined reasoning tokens on a structurally simple 2–3 unit split. |

**Not demonstrated as primary cause:** checker false positive, segmentation disagreement, or inherent need for a uniform bypass. Triage correctly required full PVR (mixed entitlement).

**Not justified by this evidence:** a complexity-aware decomposition **fast path** for F06 — the turn is mixed observable/internal, not uniform-safe.

---

## D. Existing simple / uniform classification (#121 lineage)

| Concept | Location | Role |
|---------|----------|------|
| **`player_visibility_triage`** | #121 routing checker | Affirmative `uniform_projection_safe: true` → deterministic `uniform_projection` synthesis; `false` → full semantic decomposition. |
| **`uniform_projection` kind** | `player_uniform_projection.py` | Checker-routed single-unit present-visible synthesis; `semantic_decomposition: not_performed`. |
| **`build_uniform_projection_decomposition`** | Domain | Deterministic envelope when checker affirms uniform safety. |
| **Mandatory negative corpus** | `player_visibility_triage_corpus.py` | Seiza/Japan aside, issue-88 mixed turn, concealed action, internal cognition, directed speech → `full_pvr`. |
| **`text_has_mixed_perception_modalities`** | `player_uniform_projection.py` | Structural perception-channel signal for uniform unit assembly (not a semantic complexity classifier). |

### Can existing classification support optimization without a new semantic classifier?

**Partially — with an important F06 boundary:**

- **Uniform path:** usable only when triage affirmatively returns `uniform_projection_safe: true`. **F06 triage returned `false`** (`requires_semantic_decomposition`) because of internal cognition in the Player source. A uniform bypass would **not** preserve F06 semantics.
- **Full PVR path:** required for F06. Optimization must improve **contract compliance and retry efficiency** on the semantic path, not reroute this turn to uniform projection.
- **No second complexity classifier needed** for the decomposition finding; #121 already provides the authoritative uniform vs full route. The F06 defect is downstream of a **correct** full-PVR route.

---

## E. Complex successful-decomposition evidence

**9065f006 does not provide successful decomposition evidence** (36/36 attempts failed; malformed JSON). It cannot demonstrate successful complex-turn decomposition value.

**Authoritative positive evidence — Issue #112 repeatability** (`governance/records/issue-112-pvr-repeatability-report.json`):

| Field | Value |
|-------|-------|
| Case | `complex_dense_repeat_1` |
| Player content | ~483 chars; seiza + internal Japan aside + directed speech + hesitation + long speech |
| Attempts | **1** (no retry) |
| `validation_status` | **`valid`** |
| Units | **5** — `observable_event`, `internal`, `speech` (×2), `observable_event` |
| Material entitlement effect | Separates **present observable seating** from **private internal authorial aside** (`they were not in Japan…`) and **directed speech** — distinct perceptual routing per unit. |
| Wall | ~130.5s (live experiment; cost high but **decision-producing**) |

**Conclusion:** Successful complex decomposition value is **architecturally supported and empirically demonstrated** by #112 — **not** by 9065f006.

---

## F. Environmental-cognition comparison

### F06 — narrow/simple individual inference (`318b7a1a-…`)

| Field | Value |
|-------|-------|
| **Need(s)** | **1** — house number / exterior identifier for Player glance-and-check |
| **Input** | Sparse baseline (host descriptor only); immediate user turn; committed occurrence with porch/foyer detail |
| **Output** | Single **B2** proposal: `house_number` = `visible house number by the entrance`; `response_sufficient: false` |
| **Librarian** | **None** in cognition attempt |
| **Reasoning tokens** | **11,454** |
| **Wall time** | **55,728 ms** |
| **Downstream** | Modest grounding; Host B2 validation path |
| **Deep reasoning value** | **Low** — extensive `reasoning_text` deliberates baseline_sufficient, category rules, and scope for a single B2 minimum proposal already structurally implied by Player action |

### 9065f006 — complex individual inference (`nar-env-cog-aad723430736`, continuity turn 4)

*Session audit record; separate execution-evidence attempt with timing **not** present in fixture corpus.*

| Field | Value |
|-------|-------|
| **Need(s)** | **2** interacting needs across domains |
| | `env_001`: stable seating/furnishing grounding Player seiza on cushion |
| | `story_risk_001`: Ayame backstory hardship for emotional response to Player question |
| **Input** | Sparse baseline; **multi-turn committed progression** (foyer → parlor → tea); Player seiza/cushion action |
| **Librarian** | **2 queries**, both `match`, with composed grounding from progression + premise |
| **Resolutions** | **B2** `furnishing:cushion_present` (Host **accepted**, persisted `env-b2-b85d4e708bba4ab6`) + **C** material story fact (Host **rejected** establishment — governed path required) |
| **Sufficiency** | Per-need reconciliation; B2 insufficient until Host establishment; C explicitly `bounded_refusal` |
| **Deep reasoning value** | **High** — multi-need synthesis, retrieval reconciliation, persistence vs refusal boundaries materially affect narration and continuity |

### Timing caveat

Only **F06** currently has indexed `narrator_environment_cognition` execution-evidence with `inference_wall_clock_ms` in the available corpus. The 9065f006 complex case provides **semantic/decision-complexity** comparison; wall-time comparison for that specific cognition ID is **not available** from fixture evidence.

---

## G. Environmental tier discriminator (evidence-backed)

Observable properties distinguishing F06 trivial grounding from cognition where deep reasoning provides decision value:

| Property | F06 (shallow) | 9065 `aad723` (deep) |
|----------|---------------|----------------------|
| **`information_needs` count** | 1 | 2+ |
| **Referent domain** | Single location ref | Location **and** character backstory |
| **Librarian mediation** | Absent | Present; per-need composed grounding |
| **Resolution category mix** | B2 only | B2 **+ C** (material story fact) |
| **Host establishment chain** | Single B2 proposal | B2 accept **+** C refuse (governed establishment) |
| **Prior progression synthesis** | Opening turn; thin history | Multi-turn progression retrieval required |
| **Sufficiency reconciliation** | Single narrow gap | Per-need insufficiency with conflicting render vs persist obligations |
| **`cannot_safely_resolve` / bounded_refusal** | No | Yes (story_risk_001) |

**Tiering rule (derived from evidence, not a classifier design):** Deep cognition is justified when the cognition envelope requires **multi-need reconciliation across domains**, **Librarian-mediated grounding with insufficiency follow-through**, or **category C / governed-establishment boundaries**. A **single-need, single-B2, no-mediation, opening-turn identifier gap** does not exhibit those properties in F06.

---

## H. Corrected comparative conclusions

| Initial report claim | Correction |
|---------------------|------------|
| "9065f006 complex case demonstrates decomposition can matter when successful" | **Withdrawn.** 9065f006 shows **total decomposition failure** (0/18 usable PVR; malformed JSON; ~112k wasted tokens). It demonstrates **failure/waste**, not successful decomposition value. |
| Successful complex decomposition support | **Retained architecturally**; **demonstrated empirically** by #112 `complex_dense_repeat_1` (5 valid units, 1 attempt), not 9065f006. |
| F06 decomposition mechanism "not yet isolated" | **Now isolated:** terminal punctuation omission + generic retry + model non-compliance. Not checker defect or inherent retry necessity for semantics. |
| P1 "complexity-aware fast path" for F06 knock | **Rejected for F06:** triage correctly routed to full PVR; bypass would risk internal/observable entanglement. |

---

## I. Refined root-cause model

| ID | Causal mechanism | Confidence |
|----|------------------|------------|
| RC-1 | Decomposition retry waste from **terminal substantive punctuation omission** with **non-diagnostic retry guidance** | **High** |
| RC-2 | Decomposition **over-reasoning** on structurally simple semantic splits (secondary amplifier) | **Medium** |
| RC-3 | Environmental cognition **over-deliberation** on single-need B2-minimum opening identifier gaps | **High** |
| RC-4 | Opening-turn **multi-stage accumulation** (preamble + decomposition + env cog + post-commit narrator) | **High** (unchanged) |
| RC-5 | Director/character move stack as optimization target | **Low** (unchanged — not supported) |

---

## J. Refined intervention 1 — Decomposition substantive-coverage fidelity

| # | Spec |
|---|------|
| **1. Demonstrated inefficiency** | ~41.5s inference, 0 usable PVR, 2 attempts, terminal `invalid_excluded`. |
| **2. Causal mechanism** | Model omitted index-92 `.`; checker correctly fired `sir_substantive_omission`; retry guidance did not identify omission; retry repeated failure. |
| **3. Architectural owner** | Domain: `player_semantic_normalization.py`; DSH: `player-decomposition-phase.mjs` retry assembly. |
| **4. Intervention concept** | **(a)** Deterministic **terminal punctuation merge** in normalization when uncovered substantive tail is-only sentence-terminal punctuation and all other substantive indices are covered by non-overlapping verbatim spans; **(b)** **Diagnostic retry text** exposing uncovered substantive character span(s) (e.g. trailing `.`) instead of generic completeness message. |
| **5. Addresses cause not symptom** | Fixes contract-compliance gap and retry information deficit; preserves full semantic decomposition for mixed turns. |
| **6. Unchanged behavior** | #121 triage routing; mixed-turn unit semantics; SIR contracts on substantive content; no uniform bypass for internal/observable mixes. |
| **7. Expected latency benefit** | **~15–30s** on F06-class punctuation-only failures (eliminate retry 1). |
| **8. Expected inference/token benefit** | **~5–9k reasoning tokens** saved when retry avoided. |
| **9. Semantic capability at risk** | Low if punctuation merge is strictly limited to uncovered terminal punctuation with otherwise complete contiguous coverage; medium if retry diagnostics leak into model overfitting — monitor. |
| **10. Deterministic validation** | Unit tests: F06 attempt 0/1 payloads accept after merge; `test_issue_124_semantic_normalization.py` regression; negative cases for genuine substantive omission. |
| **11. Semantic/scenario validation** | F06 replay; #112 `complex_dense_repeat_1`; issue-88 mixed-turn fixture; seiza/Japan negative corpus. |
| **12. Complex-turn guard** | issue-88 + #112 complex dense must still require full unit coverage; no merge when internal content genuinely omitted. |
| **13. Rollback/failure criterion** | Any increase in `invalid_excluded` on mixed-turn fixtures; any perceptual projection diff on #91 acceptance tests. |

---

## K. Refined intervention 2 — Environmental cognition need-structure deliberation profile

| # | Spec |
|---|------|
| **1. Demonstrated inefficiency** | 55,728 ms wall; 11,454 reasoning tokens for 1 B2 minimum proposal. |
| **2. Causal mechanism** | Single-need, no-mediation cognition still triggers full-scope deliberation over baseline_sufficient/category rules (visible in `reasoning_text`). |
| **3. Architectural owner** | `narrator-environment-cognition-substrate.mjs` + cognition manifest/inference profile selection; Host finalize path unchanged (`narrator_environment_cognition.py`). |
| **4. Intervention concept** | **Need-structure profile routing** using existing cognition schema outputs (not a new semantic classifier): when `information_needs.length === 1`, resolutions are **B2-only**, **no librarian_queries**, and no **C / cannot_safely_resolve**, use a **constrained deliberation profile** (tighter assessment scope, reduced rule-recursion prompt surface, optional lower reasoning effort per #152 natural-completion policy — **not** a hard token cap). |
| **5. Addresses cause not symptom** | Reduces decision-free deliberation where structural envelope already constrains the answer shape; preserves deep path for multi-need/mediation/C cases. |
| **6. Unchanged behavior** | #151 sufficiency semantics; Host B2 validation; fail-closed on retrieval/mediation failure; Librarian match ≠ sufficiency. |
| **7. Expected latency benefit** | **~20–40s** on F06-class single-need B2 openings (estimate pending live replay). |
| **8. Expected inference/token benefit** | Proportional reduction in reasoning tokens via natural completion under constrained profile; measure, do not cap. |
| **9. Semantic capability at risk** | Under-grounding on opening turns where single B2 is insufficient but misclassified structurally; mitigated by `response_sufficient: false` + Host validation gate. |
| **10. Deterministic validation** | Substrate tests: profile selection keyed off need count / category flags; no change to Host authority tests. |
| **11. Semantic/scenario validation** | F06 replay; 9065 `aad723` audit replay (must remain on deep profile); #49 semantic QA tests. |
| **12. Complex-turn guard** | Any `information_needs.length > 1`, any librarian query, any C/cannot_safely_resolve → deep profile mandatory. |
| **13. Rollback/failure criterion** | Increased `cannot_safely_resolve` or Host B2 rejections on opening scenarios; narration fidelity regression on house-number + cushion/seiza scenarios. |

---

## L. Deferred opportunities (P3/P4)

| ID | Item | Disposition |
|----|------|-------------|
| P3 | Opening-preamble deferral (storyteller/librarian/plot init ~52s on T1) | Retained architectural opportunity; **not** #194 implementation scope |
| P4 | Pre-commit Librarian slimming | Retained architectural opportunity; **not** #194 implementation scope |

Rationale unchanged: strongest evidence and lowest coupling concentrate on decomposition coverage fidelity and env-cognition deliberation profile.

---

## M. Validation design

| Intervention | Efficiency proof | Intelligence preservation |
|--------------|------------------|---------------------------|
| **J — coverage fidelity** | F06 replay: 0 or 1 decomposition attempt; valid PVR; pre-round wall reduction | issue-88, #112 complex dense, seiza/Japan corpus: unchanged unit semantics and projection |
| **K — env cog profile** | F06 env cog wall + reasoning tokens down vs baseline; natural-completion report (#152) | 9065 `aad723` structural profile still deep; #151 sufficiency tests; B2/C establishment boundaries |

Shared: `#173` wall-clock attribution; no use of discarded 156s attributed sum; RP-quality spot-check against closed #193 criteria where overlapping.

---

## N. Artifacts / repository state

| Artifact | Disposition |
|----------|-------------|
| `governance/records/issue-194-challenge-refinement-2026-09-14.md` | **Durable record (this file)** |
| `governance/records/issue-194-investigation-2026-09-14.md` | Superseded for causal conclusions only; retained for initial measurements |
| Local execution evidence (`data/execution_evidence/hg-session-f06d7b72-…/`) | Read-only; not committed (gitignored) |
| Deterministic replay scripts | Ephemeral; no repo mutation |

---

## O. Issue / Project state

| Item | State |
|------|-------|
| #194 | `investigating` |
| Project | In Progress / Investigating / P2 |
| Consensus transition | **Not performed** |

---

## P. Mutation attestation

- [x] No runtime implementation (no prompt, policy, retry, reasoning, classifier, sequencing, or token-cap changes)
- [x] No historical Issue mutation
- [x] No #193 mutation
- [x] Durable governance record only

---

## Q. Consensus readiness

**Improved — Governance decision pending.**

Causal gaps from Governance challenge are **resolved**:

1. **PVR/decomposition:** Mechanism isolated to terminal punctuation omission + non-diagnostic retry; correct contract would have succeeded on attempt 0. Uniform fast path **not** justified for F06.
2. **Env cognition:** Evidence-backed discriminator properties identified; F06 vs 9065 `aad723` comparison documented with timing caveat.

The refined proposal replaces initial P1 fast-path / undifferentiated P2 tiering with **two targeted, causally grounded interventions** (coverage fidelity + need-structure deliberation profile). This is **more implementation-precise** than the initial report but still requires Governance approval before `consensus_reached`.

**Do not transition state in this cycle.**
