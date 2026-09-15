# Issue #201 G3-D F3 — Blind Decode & Longitudinal Plot/Scribe Evidence Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Execution record SHA:** `eea4822`  
**Blind-lock SHA:** `f5bfdd6`  
**Status:** Decoded — pending Governance G3-D adjudication

Machine-readable: `issue-201-g3-d-f3-blind-decode-longitudinal-plot-scribe-evidence-2026-09-15.json`  
Blind lock: `issue-201-g3-d-f3-blind-score-lock-2026-09-15.json`  
Evidence root: `data/investigation_runs/issue201-g3d-f3-2026-09-15T06-44-23-918Z`

---

## 1. Answer-key access proof

Answer key accessed **only after** blind-lock commit `f5bfdd6` succeeded.

Path: `.../outputs/issue201-g3d-f3-blind-sequence-answer-key.json`

---

## 2. Decoded SEQ-A–H mapping

| Label | Sequence ID | Plot | Scenario | Rep | Mean | Usefulness |
|-------|-------------|------|----------|-----|------|------------|
| SEQ-A | `G3D-F3-a2_plot_on-arkham_stress-seq2-a1` | ON | Arkham | 2 | 4.90 | 5 |
| SEQ-B | `G3D-F3-a2_plot_on-ayame_controlled-seq1-a1` | ON | Ayame | 1 | 4.40 | 4 |
| SEQ-C | `G3D-F3-a2_plot_off-ayame_controlled-seq2-a1` | OFF | Ayame | 2 | 4.70 | 5 |
| SEQ-D | `G3D-F3-a2_plot_off-arkham_stress-seq2-a2` | OFF | Arkham | 2 | 4.80 | 5 |
| SEQ-E | `G3D-F3-a2_plot_on-arkham_stress-seq1-a1` | ON | Arkham | 1 | 4.60 | 4 |
| SEQ-F | `G3D-F3-a2_plot_off-arkham_stress-seq1-a1` | OFF | Arkham | 1 | 4.50 | 4 |
| SEQ-G | `G3D-F3-a2_plot_off-ayame_controlled-seq1-a1` | OFF | Ayame | 1 | **5.00** | 5 |
| SEQ-H | `G3D-F3-a2_plot_on-ayame_controlled-seq2-a1` | ON | Ayame | 2 | 4.70 | 5 |

Blind ordering preserved: **G 5.00 > A 4.90 > D 4.80 > C/H 4.70 > E 4.60 > F 4.50 > B 4.40**

---

## 3. Plot-ON vs Plot-OFF longitudinal means

| Metric | Plot ON | Plot OFF | Δ (ON − OFF) |
|--------|---------|----------|--------------|
| Overall longitudinal mean | **4.65** | **4.75** | **−0.10** |
| Overall RP usefulness | 4.50 | 4.75 | −0.25 |

**Plot OFF exceeds Plot ON at population level.** This is correlation, not causal proof.

---

## 4. Scenario-stratified means (do not collapse)

| Scenario | Plot ON | Plot OFF | Δ |
|----------|---------|----------|---|
| Arkham | 4.75 | 4.65 | +0.10 |
| Ayame | 4.55 | 4.85 | −0.30 |

### Paired repetition comparison

| Scenario | Rep | Plot ON | Plot OFF | Δ | Notes |
|----------|-----|---------|----------|---|-------|
| Arkham | 2 | SEQ-A 4.90 | SEQ-D 4.80 | +0.10 | **Identical player branch trajectory** |
| Arkham | 1 | SEQ-E 4.60 | SEQ-F 4.50 | +0.10 | T2 branch diverged (Ivy direct vs Harley dominant) |
| Ayame | 1 | SEQ-B 4.40 | SEQ-G 5.00 | **−0.60** | Largest gap; Plot OFF strongest overall |
| Ayame | 2 | SEQ-H 4.70 | SEQ-C 4.70 | 0.00 | Tied |

---

## 5. Per-dimension means

| Dimension | Plot ON | Plot OFF | Δ |
|-----------|---------|----------|---|
| Unresolved-thread retention | 4.50 | 4.75 | −0.25 |
| Escalation/progression | 4.75 | 4.75 | 0.00 |
| Character-agenda continuity | 4.75 | 5.00 | −0.25 |
| Delayed-consequence handling | 4.50 | 4.75 | −0.25 |
| Momentum | 4.75 | 4.75 | 0.00 |
| Initiative | 4.50 | 4.75 | −0.25 |
| Loop avoidance | 4.75 | 4.25 | **+0.50** |
| No premature resolution | 5.00 | 5.00 | 0.00 |
| Plot/narrative drift | 4.25 | 4.50 | −0.25 |
| Continuity | 4.75 | 5.00 | −0.25 |

Plot ON shows marginal loop-avoidance advantage only; all other dimensions favor Plot OFF or tie.

---

## 6. Locked observation attribution

### SEQ-G — exceptional unresolved-thread persistence (**Plot OFF**)

- **Arm:** `a2_plot_off` / `ayame_controlled` rep 1
- **Mechanism:** Primary RP + Continuity + transcript + Ayame Character cognition (single actor)
- **Finding:** Strongest blind sequence (5.00) **without Plot**. Turn-1 housing question remains an active obligation through four evasions; Turn 4 converts Kizzie's boundary demand into an explicit Ayame boundary requiring the unanswered question.
- **Plot role:** Absent. **Definitive evidence** that significant unresolved-thread persistence does not require Plot advisory.

### SEQ-A — strong Arkham accumulation (**Plot ON**)

- **Arm:** `a2_plot_on` / `arkham_stress` rep 2; lifecycle init ok → reconciliation → semantic_update
- **Finding:** Strongest Arkham blind sequence under Plot ON.
- **Confound:** Paired rep-2 Plot-OFF run SEQ-D (identical player branch) scores 4.80 vs 4.90 — negligible delta.
- **Plot role:** Correlation only; **cannot claim Plot caused accumulation** without consumer proof.

### SEQ-D — relationship continuity + spatial ambiguity (**Plot OFF**)

- **Arm:** `a2_plot_off` / `arkham_stress` rep 2 attempt 2
- **Finding:** Excellent Harley/Ivy longitudinal relationship without Plot.
- **Spatial:** Turn 4 low-volume "Come here" while Magpie remains at another table — **Narrator spatial-claim completeness debt** (carried from G3-C Sample D), not a new defect class. Validator: `spatial_claims_consistent_or_unknown`.

### SEQ-E — social-knowledge contradiction (**Plot ON**)

- **Arm:** `a2_plot_on` / `arkham_stress` rep 1; T1 init `forensic_persistence_failed`
- **Evidence:** Harley T1/T3 explicitly notices watch/Magpie fixation. Ivy T4: "Nobody else in this room did."
- **Classification:** **Character cognition miss** — generating Ivy cognition contradicts committed transcript social knowledge available to cognition.
- **Plot role:** Not implicated. Init failure recovered by T2 but did not prevent blemish.

### SEQ-F — looping despite retention (**Plot OFF**)

- **Arm:** `a2_plot_off` / `arkham_stress` rep 1
- **Finding:** Strong memory (watch, guard, linen cart) but repeated spectacle/taunt and Ivy "shine half-life" refrain.
- **Plot role:** Absent. Retention ≠ progression. Does **not** prove Plot would prevent loops.

### SEQ-B — weaker accumulation (**Plot ON**)

- **Arm:** `a2_plot_on` / `ayame_controlled` rep 1; weakest blind score (4.40)
- **Finding:** Competent interview arc with thematic variation; mild house-agency language.
- **Confound:** Paired Plot-OFF rep-1 SEQ-G scores 5.00 — Plot did not rescue weaker arc.

---

## 7. Plot initialization failures

| Blind | Sequence | T1 code | Recovery | Mean |
|-------|----------|---------|----------|------|
| SEQ-E | `...-arkham_stress-seq1-a1` | `forensic_persistence_failed` | T2 init ok → T3 reconciliation → T4 semantic_update | 4.60 |
| SEQ-H | `...-ayame_controlled-seq2-a1` | `forensic_persistence_failed` | T2 init ok → T3 reconciliation → T4 semantic_update | 4.70 |

- Failures did **not** produce worst-in-population scores.
- Recovery restored later lifecycle operations.
- **Confounds Plot value** at topology level (persistence machinery unreliable) even when semantic lifecycle continues.
- Separates **Plot function hypothesis** (longitudinal advisory value) from **current topology quality** (init persistence failures).

---

## 8. Cross-turn consumption & forensic gap

| Question | Answer |
|----------|--------|
| Overlay pressure keys surfaced by harness extractor? | **No** |
| Plot inferences executed (runtime)? | **Yes — 12** |
| Proven next-turn consumer? | **0** |
| Forensic gap type | Extractor/overlay-path gap (not disproving runtime execution) |
| Blind differences causally associated with Plot? | **Not proven** |

> A Plot-ON semantic victory without proven consumption is arm-level correlation, not proof that Plot caused the victory.

**Recommendation:** Bounded **read-only** causal trace before final Plot-retention adjudication. **Do not repair instrumentation during decode** (per authorization).

---

## 9. Plot decision-value classification (12 inferences)

| Class | Count |
|-------|-------|
| Consequential | 0 |
| Transported but unused | 0 |
| Duplicate of Continuity | 0 |
| Stale/superseded | 0 |
| Harmful/misleading | 0 |
| **Causality unknown (forensic gap)** | **12** |

Rich advisory prose must not be counted as consequential without demonstrated consumer/effect.

---

## 10. Information-bureaucracy adjudication

| Question | Assessment |
|----------|------------|
| Creates unique future-useful information? | **Not proven** |
| Mostly restates Continuity? | Suspected; not proven |
| Changes Character/Director/Narrator decisions? | **Not proven** |
| Improves progression (blind)? | **No** at population mean |
| Reduces loops (blind)? | Marginal (+0.50 loop-avoidance dimension only) |
| Overdetermines/repeats? | SEQ-B house-agency mild concern; not proven harmful |

---

## 11. What disappears when Plot is absent?

Plot-OFF sequences maintained longitudinal continuity through:

- **Continuity** state and committed events
- **Transcript/context** summaries in cognition substrate
- **Character cognition** (single- and multi-actor)
- **Director** actor selection (obligation-driven Harley/Ivy alternation)
- **Narrator** presentation

**No longitudinal capability measurably worsened at population blind mean when Plot was absent.** SEQ-G proves unresolved-thread persistence; SEQ-D proves interpersonal accumulation on paired Arkham branch.

---

## 12. Efficiency (committed sequences, 4 per arm)

| Metric | Plot ON | Plot OFF | Δ |
|--------|---------|----------|---|
| Primary-RP sync LLM | 53 | 42 | +11 |
| Plot inferences | 12 | 0 | +12 |
| Total LLM calls | 65 | 42 | +23 |
| Input tokens | 180,233 | 146,913 | +33,320 |
| Output tokens | 94,535 | 59,462 | +35,073 |
| Reasoning tokens | 61,374 | 39,297 | +22,077 |
| **Critical-path wall (ms)** | 466,318 | 448,391 | +17,927 |
| Plot post-commit wall (ms) | 155,567 | 0 | +155,567 |
| Operation wall (ms) | 1,072,741 | 1,057,679 | +15,062 |

Plot is outside player-visible critical path, but adds **12 LLM calls**, **~155s post-commit wall**, and **~33k input tokens** per 4-sequence arm with no proven blind benefit.

---

## 13. Confounds

1. N=1 sequence per arm per scenario repetition
2. Arkham rep-1 arms diverged at T2 player-policy branch
3. 2/4 Plot-ON T1 init persistence failures
4. Ayame rep-1 largest gap partly driven by T3 branch divergence (evaluative vs rules-stated)
5. Forensic extractor gap blocks consumer proof
6. Arkham Plot-OFF rep-2 required replacement attempt (seq2-a2)

---

## 14. Prospective G3-D classification evidence (not verdict)

| Band | Evidence strength |
|------|-------------------|
| Retain function / topology supported | **Not supported** — no causal consumption; aggregate blind favors OFF |
| Retain function / topology redesign | **Leading band** — lifecycle runs but persistence failures + consumer gap |
| Plot value unresolved | **Strongly supported** — correlation only; G/D disprove Plot necessity |
| Remove/consolidate Plot | **Partial** — OFF matches/exceeds ON; not definitive at N=4 |
| Plot harmful | **Not supported** — no proven loop/drift harm from Plot |

---

## 15. G3-E readiness (assessment only — not authorized)

- **G3-E execution:** Not authorized by this record.
- **Massive-retrieval validation** may proceed as an **orthogonal** Governance action.
- **Final Plot-retention verdict** should await bounded read-only consumer trace if Governance requires causal proof.
- Forensic gap alone should not block G3-E if Governance treats massive-retrieval as separate from Plot adjudication.

---

## 16. Governance decisions required next

1. **Adjudicate G3-D F3** blind decode and longitudinal Plot/Scribe evidence (this record).
2. **Authorize or decline** bounded read-only Plot consumer causal trace before final Plot-retention decision.
3. **Separate decisions:** Plot *function value* vs current *topology/persistence implementation quality*.
4. **G3-E authorization** — separate explicit action if massive-retrieval validation should proceed.
5. **Maintain** Issue #201 `consensus_reached` until Governance issues next phase directive.

G3-E and production changes remain **not authorized**.
