# Issue #201 — Package D Stage-2 Refinement Synthesis & Next-Tranche Proposal

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Control substrate SHA:** `c751ea666f0cae6524698005aa5859721c2e9738`  
**Prior records:** D0 baseline, Stage-1 blocker, Stage-2 tranche 1, Stage-2 refinement, nomenclature map  
**Locked scores:** `governance/records/issue201-stage2-governance-blind-scores-locked.json`

---

## 1. Exact current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| Package D D0 | **Accepted** |
| Stage-2 tranche 1 | **Executed** (EXP-1, EXP-2, EXP-3) |
| Stage-2 refinement | **Complete** (forensic, replacement, blind transport, nomenclature, topology) |
| Blind semantic eval | **Complete, locked, decoded** (Governance AI; user pass declined) |
| New ablation | **NOT authorized** |
| Production redesign | **NOT authorized** |
| Packages E–G | **NOT authorized** |

---

## 2. Durable evidence / commit state

| SHA | Purpose |
|-----|---------|
| `f272158` | Primary evidence durability (harnesses, governance records, EXP-3 hook, forensic tools) |
| `0d861e3` | Refinement report SHA finalize |
| `1268a7e` | Stage-2 synthesis, locked blind scores, answer-key verification helper |

**Gitignored evidence (cited, retained locally):**

| Root | Role |
|------|------|
| `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/` | D0 control runs |
| `data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/` | Stage-2 variant runs, blind packet, answer key |

**Reproducibility:** `v2/rp_runtime/scripts/issue201-package-d-{d0-baseline,stage2-tranche1}.mjs` on SHA `c751ea6`+ with evidence roots above.

---

## 3. Locked blind scores (Governance AI)

**Authority:** `issue201-stage2-governance-blind-scores-locked.json`  
**Evaluator:** Governance AI independent blind pass (locked before answer-key reveal).  
**Project user:** declined additional human scoring pass.

### Sample means (locked — do not alter)

| Sample | Mean | Decoded group |
|--------|-----:|---------------|
| A | 4.73 | EXP-2 Arkham r1 |
| B | 3.73 | EXP-1 Ayame r1 |
| C | 4.36 | EXP-3 Arkham r2 |
| D | 4.45 | D0 Ayame r2 |
| E | 4.27 | EXP-3 Ayame r2 |
| F | 4.27 | EXP-2 Ayame r2 |
| G | 4.36 | EXP-1 Arkham r1 |
| H | 4.45 | D0 Arkham r2 |
| I | 4.64 | D0 Arkham r1 |
| J | 4.64 | EXP-2 Ayame r1 |
| K | 4.36 | D0 Ayame r1 |
| L | 4.09 | EXP-1 Arkham r2 |
| M | 4.73 | EXP-2 Arkham r2 (replacement) |
| N | 4.09 | EXP-3 Arkham r1 |
| O | 4.45 | EXP-1 Ayame r2 |
| P | 4.64 | EXP-3 Ayame r1 |

Per-dimension detail remains Governance-held locked artifact (11 rubric dimensions); Implementation AI records means and derived aggregates only.

---

## 4. Decoded group means

| Architecture | Arkham | Ayame | Overall |
|--------------|-------:|------:|--------:|
| **D0** full A4 | 4.545 | 4.405 | **4.475** |
| **EXP-1** preamble bypass (D-01) | 4.225 | 4.090 | **4.158** |
| **EXP-2** Director QA bypass (D-06) | 4.730 | 4.455 | **4.593** |
| **EXP-3** orientation bypass (D-03) | 4.225 | 4.455 | **4.340** |

**Approximate deltas vs D0 overall (small-N causal signals, not population estimates):**

| Variant | Δ overall |
|---------|----------:|
| EXP-1 | **−0.32** |
| EXP-2 | **+0.12** |
| EXP-3 | **−0.14** |

---

## 5. EXP-1 updated classification

**Prior evidence:** 4/4 committed; ~9–15 inferences removed; low information-preservation confound; architectural work clearly reduced.

**Blind semantic:** Arkham ~4.55→~4.23; Ayame ~4.41→~4.09; both scenarios declined in same direction.

**Updated provisional classification:** **Retain function; architecture unresolved. Strong decomposition/consolidation candidate.**

**Interpretation:** Combined Storyteller + Plot preamble contributes useful RP value in this sample, but does **not** establish that both components or current topology are required. Next causal question: which part of the combined preamble provides observed benefit.

**NOT authorized:** production tiering/removal.

---

## 6. EXP-2 updated classification

**Forensic:** Original failed Arkham r2 (`hg-session-a92735ee-...`) classified **likely unrelated/transient**; superseded for comparison.

**Operational:** Refreshed QA-disabled set **4/4 committed**.

**Blind semantic:** Arkham A/M both 4.73; Ayame J/F 4.64/4.27; overall ~4.59 vs D0 ~4.48.

**Updated provisional classification:** **Strong combine/remove candidate; no demonstrated marginal value so far.**

**Bounded interpretation:**

- Does **not** prove Director semantic QA can never catch a valuable defect.
- Current evidence has **failed to demonstrate** marginal safety or RP-quality value sufficient to justify synchronous cost.
- Removal did not produce detectable semantic degradation in this sample; refreshed runs committed successfully.

**NOT authorized:** production removal during #201 assessment.

---

## 7. EXP-3 updated classification

**Prior evidence:** Orientation inference count → 0; 4/4 committed; librarian fan-out/wall time not cleanly reduced.

**Blind semantic (scenario-dependent):** Arkham ~4.55→~4.23; Ayame ~4.41→~4.46.

**Updated provisional classification:** **Conditional retain / complexity-tier candidate.**

**Working hypothesis:** Separate Character orientation cognition may add value on multi-character/high-interaction stress turns while being redundant on simple controlled turns. **Hypothesis only** — not final causal conclusion.

**Preserve distinction:** (1) orientation LLM cognition; (2) orientation-support Librarian mediation; (3) manifest/context assembly; (4) downstream Character Move information; (5) residual coordination topology.

**NOT authorized:** compact path implementation.

---

## 8. EXP-2 forensic / replacement conclusion

| Item | Conclusion |
|------|------------|
| Failed session | `hg-session-a92735ee-709d-4d00-a79a-7b41f0ee8652` |
| Divergence | Character semantic eval hard-rejects on Harley (R14/R16/R02b); budget exhausted |
| Causal class | **Likely unrelated/transient contamination** |
| Replacement | Full EXP-2 refresh; Arkham r2 → session `hg-session-7bd917bc-...` (sample **M**) |
| In blind comparison | Failed run **excluded**; sample M authoritative |

### Final refreshed EXP-2 architectural accounting

| Metric | Arkham (replacement) | Ayame | Notes |
|--------|---------------------|-------|-------|
| Committed | 4/4 | 4/4 | All variants |
| `director_semantic_qa` | **0** | **0** | Removed by design |
| Inference count | ~85–93 | ~46–47 | No clear savings vs D0 |
| Librarian mediation | 6–9 | 2 | Fan-out noise |
| Blind overall mean | 4.730 | 4.455 | Small-N signal only |

---

## 9. EXP-3 topology decomposition

| Component | D0 | EXP-3 (`skipCharacterKnowledgeCognition`) |
|-----------|-----|-------------------------------------------|
| **1. Orientation LLM inference** | 1–2× `character_orientation` | **0** — removed |
| **2. Librarian mediation (orientation path)** | 1–10× KAR-driven | **Reduced variably** (2–13×); other lanes remain |
| **3. Manifest/context assembly** | orientation + character context prep | **Retained** — `prepareCharacterContext` for Move |
| **4. Character Move inputs** | manifest + orientation `librarian_bundle` | manifest only (`librarian_bundle` null) |
| **5. Routing/coordination** | full character prep subgraph | **Retained** — projection lifecycle, semantic eval, director loop |

### Work actually removed

- Orientation LLM call(s) and finalize acceptance when skipped
- Orientation-derived KAR and orientation-mediated librarian bundle

### Orientation-topology work that remained

- Character projection lifecycle
- `prepareCharacterContext` assembly
- Character move + semantic eval retries
- Director/narrator stacks
- Non-orientation librarian mediation (storyteller, narrator env, etc.)

**If orientation LLM eliminated with authoritative inputs supplied directly to Character Move:** above residual synchronous work would remain unless topology redesigned.

---

## 10. Canonical D-series mapping

See `governance/records/issue201-experiment-nomenclature-d01-d10.md`.

| Tranche EXP | D-ID | `roundOptions` | Executed |
|-------------|------|----------------|----------|
| EXP-1 | **D-01** | `skipStorytellerCognition` + `skipPlotCognitionOrchestration` | Yes |
| EXP-2 | **D-06** | `directorSemanticQaEnabled: false` | Yes |
| EXP-3 | **D-03** | `skipCharacterKnowledgeCognition` | Yes |

**Not executed:** D-02 (plot-only subset), D-04–D-05, D-07–D-10.

---

## 11. Nomenclature corrections

1. Stage-1 EXP-3 label (Storyteller-only) — **historical only**; Stage-2 EXP-3 = D-03 orientation bypass.
2. D0 record §26 — updated to D-03 orientation label.
3. D-10 = post-commit join / `skipLibrarianProposalGeneration` — same experiment as Packages A–C D-10; not a rename conflict.

---

## 12. World-state observational findings

| Observation | Status |
|-------------|--------|
| PVR validation | **valid** on committed D0 + variant runs |
| Knowledge/perception boundary violations | **None auto-detected** in harness |
| Player promotion / portal authority | **Not auto-verified** (observe-only) |
| Ayame portal/door in presentation | Observed in committed Ayame samples |
| Arkham multi-actor stress | Director routing + semantic eval exercised |

No material change requiring new blocker filing in this refinement step.

---

## 13. Updated Package-D architectural hypotheses

### Working hypothesis (not redesign consensus)

> Holy Grail may contain valuable specialized cognition but invoke too much of it unconditionally. The emerging target may be a **compact core with specialized cognition triggered by decision complexity/information need** rather than either a one-LLM monolith or the current always-on A4 topology.

### Per-experiment signals (small-N)

| Experiment | Architectural signal | Quality signal |
|------------|---------------------|----------------|
| EXP-1 | Clear inference reduction | Negative blind delta |
| EXP-2 | QA stage removable synchronously | Neutral-to-positive blind delta |
| EXP-3 | Orientation LLM removable | Scenario-dependent blind delta |

---

## 14. Implications for A0–A4

| Topology | Updated implication |
|----------|---------------------|
| **A4 (current)** | Unconditional preamble and orientation layers show **measurable cost**; preamble shows **measurable quality contribution** in blind sample |
| **A3 compact** | EXP-3 does **not** justify unconditional orientation removal; **tiering hypothesis** strengthened for stress vs controlled turns |
| **A2/A1** | EXP-2 supports **re-evaluating checker stack** — QA may be combinable/removable without detected quality loss in sample |
| **A0** | Still **insufficient evidence** to collapse to single-call; boundary machinery still required |

---

## 15. Remaining evidence gaps

1. **Preamble decomposition** — which of Storyteller vs Plot vs interaction drives EXP-1 quality delta?
2. **Director QA edge cases** — rare failure modes not captured in small-N blind sample
3. **Orientation tiering** — fair complexity-contrast (stress vs controlled) with bundle-preservation variant if authorized
4. **Post-commit join (D-10)** — cost/value not yet isolated
5. **Statistical power** — all Stage-2 blind signals are n=2 per scenario per variant
6. **Per-dimension attribution** — Governance-held detail not yet mapped to component hypotheses in durable record
7. **World-state promotion** — still observe-only

---

## 16. Proposed next causal variants (NOT executed)

**Primary objective:** Decompose EXP-1 quality signal — Storyteller vs Plot vs interaction.

| Proposed ID | Variant | `roundOptions` (conceptual) | vs D0 | vs EXP-1 |
|-------------|---------|----------------------------|-------|----------|
| **EXP-4a / D-01a** | Storyteller retained; Plot preamble bypassed | `skipPlotCognitionOrchestration: true` only | Partial preamble removal | Isolates Plot |
| **EXP-4b / D-01b** | Plot retained; Storyteller bypassed | `skipStorytellerCognition: true` only | Partial preamble removal | Isolates Storyteller |
| **EXP-1 / D-01** | Combined preamble bypass | both skip flags | *(executed)* | Baseline combined |
| **D0** | Full A4 control | none | *(executed)* | — |

**Optional later (not recommended as co-primary in same tranche):**

| ID | Variant | Rationale to defer |
|----|---------|-------------------|
| EXP-3 complexity contrast | Orientation on stress-only re-test | Wait until preamble decomposition clarifies largest quality lever |
| D-10 post-commit join | `skipLibrarianProposalGeneration` | Lower priority than EXP-1 decomposition given blind signal |

---

## 17. Information-preservation design (proposed variants)

| Variant | Cognition removed | Must preserve (no starvation) |
|---------|-------------------|------------------------------|
| **D-01a Plot-only skip** | `plot_cognition_init`, `plot_cognition_update`, plot-mediated librarian resume | Scenario premise, character cards, continuity, PVR, Storyteller advisory (if retained), director/character/narrator authoritative inputs |
| **D-01b Storyteller-only skip** | `storyteller_orientation`, `storyteller_assessment`, storyteller-mediated librarian | Plot cognition state/resume (if retained), authoritative manifest, PVR, director decision context |
| **D-01 combined** | Both stacks | Authoritative scenario + manifest + continuity + PVR (established EXP-1 confound: low) |

**Rule:** Ablations remove cognition only; legitimate downstream authoritative inputs must still reach Character Move and Narrator.

---

## 18. Expected information gain (proposed variants)

| Variant | Information gain |
|---------|------------------|
| **D-01a Plot-only** | Isolates whether Plot cognition drives EXP-1 Arkham/Ayame quality decline |
| **D-01b Storyteller-only** | Isolates whether Storyteller advisory drives decline; tests if Plot alone sustains quality |
| **Re-run D-01 + D0** | Confirms EXP-1 signal reproducibility in decomposition tranche |
| **EXP-3 contrast (deferred)** | Tests complexity-tier hypothesis for orientation |

---

## 19. Recommended execution order

1. **D0** controls (2× Arkham + 2× Ayame) — same harness substrate; confirm parity
2. **D-01b** Storyteller-only skip (higher priority — Storyteller is larger inference stack per tranche accounting)
3. **D-01a** Plot-only skip
4. **Optional:** re-include **D-01 combined** only if Governance wants same-tranche replication of EXP-1
5. **Blind eval** on new tranche outputs before decode
6. **Defer EXP-3 complexity contrast** until preamble decomposition results reviewed

---

## 20. Recommended repetition strategy

| Scenario | Reps | Rationale |
|----------|------|-----------|
| Arkham stress | **2** | Match Stage-2; maintain small-N discipline |
| Ayame controlled | **2** | Match Stage-2 |
| Per new variant | **4 runs total** (2+2) | 16 blind samples if all variants + D0 in one tranche |
| EXP-2 | **0** | Sufficient for current gate; no third Arkham rep unless Governance requests edge-case hunt |

**Blind protocol:** Same rubric; Governance or designated evaluator; lock before decode.

---

## 21. Updated §1–23 assessment coverage

| § | Deliverable | Status after Stage-2 synthesis |
|---|-------------|-------------------------------|
| 1 | Architecture map | **Advanced** — node inventory + D ablation anchors |
| 2 | Critical-path map | **Advanced** — latency per tranche case |
| 3 | Inference inventory | **Satisfied** |
| 4 | Component value ledger | **Advanced** — provisional classifications EXP-1/2/3 |
| 5 | Checker/correction ledger | **Advanced** — EXP-2 Director QA signal |
| 6 | Information-handoff map | **Advanced** — EXP-3 topology decomposition |
| 7 | Historical rationale | **Satisfied** |
| 8 | Latency contribution | **Advanced** — D0 + tranche wall/inference |
| 9 | Correctness contribution | **Advanced** — commit rates, PVR valid |
| 10 | **Quality contribution** | **Advanced** — first causal blind attribution (small-N) |
| 11 | Failure modes | **Advanced** — EXP-2 forensic |
| 12 | Duplication/redundancy | **Partial** — preamble/orientation overlap flagged |
| 13 | Creative-freedom | **Gap** |
| 14 | Decision-value ranking | **Advanced** |
| 15 | Clearly justified | **Premature** |
| 16 | Conditional components | **Advanced** — EXP-1 retain, EXP-2 combine/remove candidate, EXP-3 tier candidate |
| 17 | Insufficient justification | **Advanced** — EXP-2 QA synchronous cost |
| 18 | Candidate simplifications | **Advanced** — preamble decomposition proposed |
| 19 | A0–A4 comparison | **Advanced** — §14 above |
| 20 | Risk/tradeoff | **Partial** — awaits more tranches |
| 21 | Expected latency ranges | **Partial** |
| 22 | Validation strategy | **Advanced** — blind eval protocol proven |
| 23 | Remediation program | **Not authorized** |

---

## 22. Artifact disposition / commit SHAs

| Artifact | Disposition |
|----------|-------------|
| Investigation harnesses | Committed `f272158` |
| Governance records (A–C, D0, Stage-1/2) | Committed `f272158` / `0d861e3` |
| This synthesis + locked scores | **This commit** |
| `tools/investigation/verify_blind_eval_key.py` | Committed (integrity helper) |
| `tools/investigation/regen_stage2_scoring_sheet.py` | Committed `f272158` |
| Gitignored run outputs | Retained locally; paths in records |
| Staging utilities | Deleted (`_backfill_meta.py`) |

---

## 23. Governance decisions required

1. **Authorize next causal tranche** — preamble decomposition (D-01a + D-01b) as primary objective?
2. **Accept updated classifications** — EXP-1 retain/decompose; EXP-2 combine/remove candidate; EXP-3 tier candidate?
3. **Replicate D-01 combined** in next tranche or treat Stage-2 EXP-1 as sufficient?
4. **Defer EXP-3 complexity contrast** until after preamble decomposition?
5. **Authorize D-10** post-commit join as subsequent tranche after preamble results?
6. **Update #201 Issue body** with Stage-2 synthesis SHA and blind decode summary?
7. **Record Governance per-dimension scores** in durable repo artifact (if Governance chooses to export)?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** Blind decode recorded; Stage-2 refinement synthesis; next-tranche proposal prepared  
**Not executed:** New ablations, production tiering, Packages E–G synthesis
