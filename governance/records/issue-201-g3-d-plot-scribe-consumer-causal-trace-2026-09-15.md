# Issue #201 G3-D — Plot/Scribe Consumer Causal Trace Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Decode record SHA:** `0980194`  
**Investigation:** Read-only causal trace (no mutation, no live runs, no instrumentation repair)  
**Status:** Complete — pending Governance verdict

Machine-readable: `issue-201-g3-d-plot-scribe-consumer-causal-trace-2026-09-15.json`  
Evidence root: `data/investigation_runs/issue201-g3d-f3-2026-09-15T06-44-23-918Z`

---

## 1. Governance adjudication carried forward

> Plot/Scribe has not earned retention as a required component of A2. Current evidence favors remove/consolidate, pending one bounded causal investigation.

Blind evidence unchanged (Plot OFF 4.75 > Plot ON 4.65; SEQ-G 5.00 Plot OFF; +23 LLM calls; no prior proven consumer).

---

## 2. Governing causal question

**Did existing Plot/Scribe advisory outputs reach later Primary-RP cognition in G3-D, and if so, did they change consequential decisions?**

**Answer: No.** Plot advisory was generated and mostly persisted to overlay sidecars, but **zero L2+ transport** to Character, Director, or Narrator cognition in the executed A2 G3-D topology.

**Leading hypothesis: B — Generated but not consumed.**

---

## 3. Declared vs observed consumer contract

| Consumer | Declared (production) | Observed (G3-D F3 A2) |
|----------|---------------------|------------------------|
| Character | `plot_cognition_finalized_projection` via projection lifecycle | **Not observed** — `projectionLifecycleEnabled: false`; packaging fail-closed without finalized projection |
| Director | `director_overlay_contributions` / `project_director_overlay` | **Not observed** — obligation-driven actor selection; no overlay packaging |
| Narrator | Not a Plot consumer | N/A |
| Next-turn overlay | Sidecar `_plot_cognition_overlay/{scope}.json` | **L1 persisted** — but not read into cognition inputs |

A2 beat explicitly sets `skipCharacterKnowledgeCognition: true` and `projectionLifecycleEnabled: false` (`a2-beat-orchestration.mjs`). `storyteller_round_packaging.py` character path: without `finalized_projection`, candidates exist but contributions are **not emitted** (fail-closed `pass`).

---

## 4. Forensic extractor gap (corrected)

Prior decode reported `overlay_found: false` for all turns. **Re-investigation shows:**

- Overlay sidecar files **do exist** on disk (resolvable via `plot_post_commit.contractLineage.primary.raw` → `plot_cognition_scope_id`).
- Harness `extractPlotForensics` failed because **session JSON lacked `plot_cognition_scope_id`**, so scope was null at forensic read time.
- `cross_turn_plot_consumption` showed `updated_no_persisted_keys` due to empty before/after forensics — **extractor gap**, not proof of absent runtime persistence.

**L1 persistence is evidenced; L2 projection is not.**

---

## 5. T1 init failure interpretation (SEQ-E, SEQ-H)

| Field | Value |
|-------|-------|
| Surface code | `forensic_persistence_failed` |
| Surface message | `proposal failed objective validation` |
| T1 accepted | `false` |
| T2 recovery | `initialization/committed` |
| Overlay after recovery | **Yes** |

**Interpretation:** First init **proposal failed objective validation** inside WAFI-wrapped finalize; overlay **not established on T1**. T2 retry committed successfully. This is **not** proof of post-commit persistence failure after accepted commit. Label `forensic_persistence_failed` is a WAFI wrapper code surfacing validation rejection message.

---

## 6. Twelve-inference L0–L4 table

| Sequence | Turn | Lifecycle | Key advisory | L | Consumer observed | Duplicate? | Consequential? |
|----------|------|-----------|--------------|---|-------------------|------------|----------------|
| SEQ-A | 1 | initialization | Arkham goals/pressures (watch, Harley/Ivy, surveillance) | **L1** | none | compressed duplicate | no |
| SEQ-A | 3 | semantic_update | overlay revision post-T3 | **L1** | none | synthesized | no |
| SEQ-A | 4 | semantic_update | overlay revision post-T4 | **L1** | none | synthesized | no |
| SEQ-B | 1 | initialization | Ayame household-entry pressures | **L1** | none | compressed duplicate | no |
| SEQ-B | 3 | semantic_update | overlay revision | **L1** | none | synthesized | no |
| SEQ-B | 4 | semantic_update | overlay revision | **L1** | none | synthesized | no |
| SEQ-E | 1 | initialization | magpie-fixation-crosses-harley; guard observation | **L0** | none | not persisted | no |
| SEQ-E | 2 | initialization | shared watch-attention (hg-pressure-global-003) | **L1** | none | duplicate of transcript | no |
| SEQ-E | 4 | semantic_update | overlay revision | **L1** | none | synthesized | no |
| SEQ-H | 1 | initialization | Ayame entry-evaluation pressures | **L0** | none | not persisted | no |
| SEQ-H | 2 | initialization | household-entry pressures (recovery) | **L1** | none | compressed duplicate | no |
| SEQ-H | 4 | semantic_update | overlay revision | **L1** | none | synthesized | no |

### Transport counts

| Level | Count |
|-------|-------|
| L0 (generated only) | **2** |
| L1 (persisted) | **10** |
| L2 (projected) | **0** |
| L3 (decision-relevant) | **0** |
| L4 (consequential) | **0** |

### Duplicate-information counts

| Class | Count |
|-------|-------|
| Exact duplicate | 0 |
| Compressed duplicate | 4 |
| Synthesized interpretation | 5 |
| Genuinely new narrative inference | 0 |
| Not persisted (L0) | 2 |

---

## 7. Sequence-specific findings

### SEQ-A (Plot ON 4.90)

Watch thread, Ivy restraint, Harley testing, Magpie refusal — all **present in committed transcript** without Plot projection. Paired Plot-OFF SEQ-D (identical branch) scores 4.80. **No L2+ Plot contribution evidenced.**

### SEQ-B (Plot ON 4.40 — weakest)

Plot advised household/boundary framing already available through interview transcript and Continuity. Paired Plot-OFF SEQ-G scores 5.00. No evidence Plot encouraged repetition; thematic house-agency in prose is **not** attributable to Plot consumption.

### SEQ-E (Plot ON 4.60 — social-knowledge miss)

- **Failed T1 proposal** contained `hg-pressure-magpie-fixation-crosses-harley` (discarded).
- **Recovered T2 overlay** contains `hg-pressure-global-003`: shared watch attention among inmates.
- Ivy T4 "Nobody else in this room did" contradicts Harley T1/T3 transcript — **Character cognition miss**.
- Plot held correct social-attention information in **persisted overlay** but **did not project** to Ivy cognition (`projectionLifecycleEnabled: false`). Plot had **opportunity** to help only if consumed; it was not.

### SEQ-H (Plot ON 4.70)

Reliability → boundaries → failure → terms progression available from transcript. Tied Plot-OFF SEQ-C (4.70). No Plot-unique longitudinal function.

---

## 8. Plot-OFF comparison

| Plot-OFF | Score | Finding |
|----------|-------|---------|
| SEQ-G | 5.00 | Exceptional unresolved-thread persistence **without Plot** |
| SEQ-D | 4.80 | Strong Harley/Ivy continuity on paired Arkham branch |
| SEQ-C | 4.70 | Tied Plot-ON SEQ-H |
| SEQ-F | 4.50 | Retention-with-looping without Plot |

**No longitudinal function demonstrated in Plot-ON that Plot-OFF lacked.**

---

## 9. Topology assessment

| Stage | Assessment |
|-------|------------|
| Generation | 12 plot LLM inferences executed |
| Persistence | 10/12 committed to sidecar; 2 T1 validation failures recovered T2 |
| Reconciliation | Domain bookkeeping; no plot inference |
| Projection | **Disabled** in executed A2 G3-D path |
| Consumption | **Fail-closed** without projection lifecycle |

**Complexity not justified:** init → reconciliation → semantic_update → overlay sidecar → (blocked) projection → character contributions. Advisory state is written but **never enters Primary-RP cognition inputs** in the topology that was actually executed.

---

## 10. Prospective causal classification evidence

| Hypothesis | Evidence |
|------------|----------|
| Consumed but low-value | **Not supported** (zero L2+) |
| **Generated but not consumed** | **Strongly supported** |
| Consumed and consequential | **Not supported** |
| Causally unresolved | **Not supported** — execution evidence sufficient |

---

## 11. G3-E readiness

This causal trace **resolves Plot sufficiently** for Governance to proceed to massive-knowledge validation (G3-E) **without** carrying an ambiguous Plot-retention decision. Plot remove/consolidate is now causally grounded, not only correlatively grounded.

**G3-E not executed by this record.**

---

## 12. Governance decisions required next

1. **Render G3-D Plot/Scribe architecture verdict** (remove/consolidate vs retain-with-redesign) using blind + causal trace evidence.
2. **Authorize or decline G3-E** massive-knowledge validation as separate action.
3. **If retaining Plot function at all:** require topology change so projection lifecycle reaches Character cognition (current A2 path cannot consume Plot).
4. **Maintain** Issue #201 `consensus_reached` until next phase directive.
