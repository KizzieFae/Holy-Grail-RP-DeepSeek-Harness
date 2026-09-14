# Issue #201 — Package D Stage 1 Experimental Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` (Package D Stage 1 — **blocked** on live execution)  
**Assigned / effective weight:** `full` / `full`  
**Investigation SHA:** `43db105401769750980bdc214666424fa11985cb`  
**Harness:** `v2/rp_runtime/scripts/issue201-package-d-stage1.mjs`

---

## 1. Activation / current-state verification

| Field | Value |
|-------|-------|
| `Current status:` | `investigating` |
| Project | In Progress / Investigating / P1 |
| Packages A–C | Accepted (prior record) |
| Package D | **Authorized**; Stage 1 execution **blocked** (see §5) |
| Production redesign | NOT performed |
| Consensus | NOT transitioned |

---

## 2. Baseline repository / runtime anchor

| Anchor | Value |
|--------|-------|
| HEAD | `43db105401769750980bdc214666424fa11985cb` |
| Post-#199 merge | `d40d8c6f95e6aca75ba4ea88cca9a0665be06557` |
| Post-#200 merge | `4b322f2bea2b5879a2569c77b162ee982244e5a8` |
| Inference catalog | `v2/rp_runtime/src/application/llm-call-catalog.mjs` |
| Node manifest policy | `v2/rp_runtime/src/lib/manifest-projection-policy.mjs` |
| Python manifest policy | `v2/domain_api/manifest_projection_policy.py` |
| API key | Present (`DEEPSEEK_API_KEY` set) |

---

## 3. Primary stress benchmark confirmation

**Selected:** `arkham_asylum_mess_hall_arena`

| Criterion | Evidence |
|-----------|----------|
| 3+ characters | `harley_quinn`, `poison_ivy`, `magpie` (local `data/characters/`) |
| Separate agendas | Template premise: pecking order, predation, staff sightlines |
| Private knowledge | Character cards + role slots; retrieval pilot S2 cast |
| Perceptual boundaries | Multi-public mess hall; low privacy |
| Multiple narrative concerns | Parallel opener vectors (dyadic + impulse disruption) |
| Environmental persistence | Institutional cafeteria setting |
| Knowledge leakage risk | Public scene + distinct character knowledge |
| Character drift risk | High-volatility DC cast |
| Progression | Conflict escalation vectors in premise/openers |

**Harness opener:** `mess_hall_magpie` (impulse-vector public pressure).  
**Player stimulus:** Magpie observes guard's watch; provocative murmur toward Harley.

**Repository suitability:** **Confirmed** for stress benchmark intent per `governance/records/operational-retrieval-pilot.md` S2 and template metadata.

---

## 4. Controlled benchmark selection

**Selected:** `ayame_household_entry_evaluation`

| Rationale | Detail |
|-----------|--------|
| Causal isolation | Dyadic entry protocol; bounded turn semantics |
| Post-#199/#200 corpus | Same scenario as remediated F06 defects (#199 grounding, #200 consumption) |
| Existing harness | `issue194-live-validation.mjs` pattern |
| Player stimulus | F06 knock line (controlled, documented) |

**Repository suitability:** **Confirmed** — template in `data/scene_templates/`; characters `ayame`, `kizzie` present locally.

---

## 5. Fresh post-#199/#200 baseline results — **BLOCKED**

### Execution attempt

Harness invoked: `node scripts/issue201-package-d-stage1.mjs`  
**D0 arkham baseline (production `submitUserTurn`) failed** after ~246s wall.

### Failure (authoritative)

```
model-context package rejected: ... disallowed source_kind 'authoritative_perceptual_inventory'
for inference_kind 'character_orientation'
```

**Root cause (code parity defect, not architectural hypothesis):**

| Layer | `authoritative_perceptual_inventory` in `_CHARACTER_LANES` / `CHARACTER_LANES`? |
|-------|----------------------------------------------------------------------------------|
| Python `manifest_projection_policy.py` | **Yes** (line 133) |
| Node `manifest-projection-policy.mjs` | **No** (missing from `CHARACTER_LANES`, lines 37–55) |

#199 added `project_perceptual_inventory_contribution()` to `character_upstream_context.py`, which feeds **character_orientation** manifests. Host projects inventory; DSH bridge rejects before inference.

**Impact:** All live rounds requiring Character orientation fail on current `main`. Fresh Package D baselines and ablations **cannot proceed** without a minimal Node policy parity fix (or equivalent investigation-only bridge alignment).

**D0 ayame baseline:** Not attempted after arkham failure (same defect expected).

**Historical F06 timings:** Not used as Package D causal control (per Governance directive).

### Partial forensic value

Failure occurred **after** round preamble (Storyteller/plot path exercised) and Director phase — confirms pipeline reaches Character prep on arkham stress setup. No durable `data/investigation_runs/` report committed (run aborted before write).

---

## 6. Blind quality-evaluation procedure

**Artifact:** `issue201_blind_eval_packet_v1` (implemented in harness)

| Step | Procedure |
|------|-----------|
| 1 | Collect `presentation_text` per case (control + variants) |
| 2 | Assign random blind labels (A, B, C, …) — architecture identity stripped |
| 3 | Emit `issue201-blind-eval-packet.json` (evaluator-facing) |
| 4 | Emit `issue201-blind-eval-answer-key.json` (restricted mapping) |
| 5 | Evaluator scores 11 semantic dimensions (1–5) **without** architecture labels |
| 6 | Separately score objective contractual checklist |
| 7 | Unmask only after scoring complete |

**Semantic dimensions (non-deterministic):** fidelity, distinctiveness, initiative, responsiveness, progression, coherence, prose quality, repetitiveness, stiffness, exposition, emotional continuity.

**Status:** Procedure **ready**; **no live samples scored** (baseline blocked).

---

## 7. Ranked D-01–D-10 experiments (expected information gain)

| Rank | ID | Rationale |
|------|-----|-----------|
| 1 | **D-01** | Highest uncertainty on preamble advisory stack; tests coordination tax vs dramatic value |
| 2 | **D-06** | Isolates Director semantic QA marginal safety |
| 3 | **D-01-partial** | Storyteller-only skip vs full preamble — tiering signal |
| 4 | **D-04** | Env cognition cost/value (needs hook or tiering variant) |
| 5 | **D-03** | Character orientation (no production skip flag) |
| 6 | **D-10** | `skipLibrarianProposalGeneration` — post-commit join cost |
| 7 | **D-05** | Librarian S2a @character bypass |
| 8 | **D-07** | Character semantic eval off (high risk; late tranche) |
| 9 | **D-09** | PVR tiering vs full decomposition |
| 10 | **D-08** | Compact topology (largest blast radius; after component isolations) |

---

## 8. First bounded tranche rationale

**Planned tranche (3 experiments on arkham_stress, after D0 baselines):**

| Exp | Maps to | Class | Round options |
|-----|---------|-------|---------------|
| EXP-1 | D-01 | Low-marginal cognition | `skipStorytellerCognition` + `skipPlotCognitionOrchestration` |
| EXP-2 | D-06 | Checker | `directorSemanticQaEnabled: false` |
| EXP-3 | D-01-partial | Tiering/consolidation | `skipStorytellerCognition` only |

**Not executed** due to §5 blocker. Same PVR path for variants; production `submitUserTurn` for D0 controls.

---

## 9–15. Experimental results

**Not available.** No successful variant runs. No blind semantic scores. No latency/token comparison beyond partial failed arkham attempt duration (~246s to failure).

---

## 16–17. Marginal value / weakened components

**Premature for causal claims.** Blocker itself weakens confidence that #199 integration is production-live-ready on Node bridge — **implementation parity**, not architectural assessment conclusion.

---

## 18. Surprising / contradictory findings

1. **#199 merged and validated** but Node `CHARACTER_LANES` allowlist not updated — live Character orientation fails. Suggests validation corpus did not include full DSH manifest bridge path on live arkham/multi-character sessions.
2. Investigation harness correctly surfaced defect before any ablation interpretation.

---

## 19. Implications for A0–A4 (no winner)

| Hypothesis | Stage 1 implication |
|------------|----------------------|
| A4 (current) | Cannot characterize live quality/latency on fresh `main` until parity fix |
| A1/A2 | Blocker is integration defect, not evidence for monolith |
| A3 | Tranche still planned post-fix |
| A0 | N/A |

---

## 20. Recommended next Package D experiments

1. **Governance authorize minimal parity fix:** add `authoritative_perceptual_inventory` to Node `CHARACTER_LANES` in `manifest-projection-policy.mjs` (align `#134` / Python policy). Scope: investigation enablement only; not architectural redesign.
2. Re-run harness: D0 arkham + D0 ayame baselines.
3. Execute EXP-1..3 tranche on arkham.
4. Add EXP-4: `skipLibrarianProposalGeneration` (tranche 2).
5. Add D-04 env cognition tiering once investigation hook or deliberation-profile control validated.

---

## 21. World-state promotion gap classification (#200 deferred)

| Finding (#200 closure) | Classification | Evidence |
|------------------------|----------------|----------|
| Player actions not promoted to Continuity/world state | **Missing architectural responsibility** (outcome needed; mechanism absent) | #200 explicitly deferred generalized promotion; inverse R16 + pressure freshness are partial guards |
| Narrative door-open vs closed-portal desync | **Responsibility assigned to wrong layer** / fragmented world authority | #200 closure table; not remediated under #200 |
| Portal desync | **Insufficient evidence** for root cause class without fresh replay | Requires live session forensics post-fix |
| Pressure freshness / inverse R16 | **Implementation defects (remediated)** | #200 closed |

**Not an ordinary single-module bug alone** — architectural seam question remains inside #201 assessment scope. **No remediation authorized** during #201.

---

## 22. Durable evidence / record locations

| Artifact | Path | Status |
|----------|------|--------|
| Stage 1 report (this file) | `governance/records/issue-201-package-d-stage1-2026-09-14.md` | written |
| Investigation harness | `v2/rp_runtime/scripts/issue201-package-d-stage1.mjs` | written (uncommitted) |
| Packages A–C record | `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` | prior |
| Live run JSON | — | **not produced** (aborted) |
| Blind eval packet | — | **not produced** |

---

## 23. Artifact disposition

| Artifact | Disposition |
|----------|-------------|
| `issue201-package-d-stage1.mjs` | **Retain** — authorized investigation harness; re-run after parity fix |
| Partial temp evidence | **None persisted** |
| This governance record | **Retain** — Stage 1 outcome including blocker |

---

## 24. Questions for Governance

1. **Authorize minimal Node manifest parity fix** (`authoritative_perceptual_inventory` in `CHARACTER_LANES`) to unblock Package D live execution? (Investigation enablement, not #201 architectural remediation.)
2. Should parity fix be a **separate tracked Issue** or an explicit #201 investigation exception?
3. Re-run full Stage 1 (D0 + tranche) or D0-only verification after fix?
4. Approve tranche 2 (`skipLibrarianProposalGeneration`, narrator QA off) after Stage 1 completes?
5. Require arkham baseline **2 repetitions** for stochastic stability given LLM variance?

---

## Session boundary

**Stage:** `investigating` — Package D Stage 1 **blocked** on live baseline.  
**Completed:** Benchmark confirmation; harness authoring; blind-eval procedure; experiment ranking; tranche plan; blocker diagnosis; world-state gap classification.  
**Not completed:** Fresh baselines; ablation tranche; blind scoring.  
**Next:** Governance decision on parity fix authorization, then re-run harness.
