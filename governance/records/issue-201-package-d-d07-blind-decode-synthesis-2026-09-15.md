# Issue #201 — D-07 Blind Decode & Narrator-QA Intervention-Value Report

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full` / `full`  
**Status:** Primary decode complete — **architectural classification NOT rendered** (Governance adjudication)

| Anchor | SHA / path |
|--------|------------|
| D-07 execution | `921b127` |
| Locked blind scores | `f3f9d38` — `issue201-d07-governance-blind-scores-locked.json` |
| Evidence root | `data/investigation_runs/issue201-package-d-d07-2026-09-15T04-25-04-321Z/` |

---

## 1. Issue / project state and weights

| Field | Value |
|-------|-------|
| Issue | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-07 decode | **Complete** |
| D-07 Governance classification | **Pending** |
| Final #201 synthesis | **Still paused** |
| Production remediation | **NOT authorized** |

---

## 2. Blind-lock artifact path

`governance/records/issue201-d07-governance-blind-scores-locked.json`

---

## 3. Blind-lock commit SHA

**`f3f9d386b571720dea56fe2deae07c5685753ba7`** (`f3f9d38`)

---

## 4. Proof lock preceded answer-key access

| Step | Evidence |
|------|----------|
| Lock commit | `f3f9d38` — file created and committed with `scored_before_answer_key_reveal: true` |
| Answer-key read | **Only after** lock commit succeeded |
| Decode commit | This document — post-lock |

Implementation AI did not read `issue201-d07-blind-eval-answer-key.json` before `f3f9d38`.

---

## 5. Exact A–H decoded mapping

| Label | Case ID | Arm | Scenario | QA enabled |
|-------|---------|-----|----------|:----------:|
| **A** | `D07-ablated-arkham_stress-r1` | ablated | Arkham | no |
| **B** | `D07-ablated-arkham_stress-r2-a2` | ablated | Arkham | no |
| **C** | `D07-ablated-ayame_controlled-r1` | ablated | Ayame | no |
| **D** | `D07-ablated-ayame_controlled-r2` | ablated | Ayame | no |
| **E** | `D07-control-arkham_stress-r1` | control | Arkham | yes |
| **F** | `D07-control-arkham_stress-r2` | control | Arkham | yes |
| **G** | `D07-control-ayame_controlled-r1` | control | Ayame | yes |
| **H** | `D07-control-ayame_controlled-r2` | control | Ayame | yes |

---

## 6. Unchanged locked scores

Governance-assigned; not rescored. See `issue201-d07-governance-blind-scores-locked.json`.

| Label | Primary mean | Env grounding | RP usefulness |
|-------|------------:|--------------:|--------------:|
| A | 4.18 | 4 | 4 |
| B | 4.45 | 4 | 4 |
| C | 4.36 | 3 | 4 |
| D | 4.55 | 4 | 5 |
| E | 4.18 | 3 | 3 |
| F | 4.18 | 4 | 4 |
| G | 4.36 | 4 | 4 |
| H | 4.64 | 5 | 5 |

---

## 7. Overall primary control / ablated means and delta

| Arm | n | Primary mean |
|-----|--:|-------------:|
| Control | 4 | **4.34** |
| Ablated | 4 | **4.39** |
| **Δ (control − ablated)** | | **−0.05** |

**Interpretation (evidence only):** Ablated arm matched or slightly exceeded control on the primary blind endpoint. Not a population estimate; n=2 per scenario per arm.

---

## 8. Arkham means / delta

| Arm | Samples | Mean |
|-----|---------|-----:|
| Control | E, F | **4.18** |
| Ablated | A, B | **4.31** |
| **Δ** | | **−0.13** |

Ablated Arkham scored higher; strongest Arkham blind sample **B** (4.45) is **ablated**.

---

## 9. Ayame means / delta

| Arm | Samples | Mean |
|-----|---------|-----:|
| Control | G, H | **4.50** |
| Ablated | C, D | **4.46** |
| **Δ** | | **+0.05** |

Ayame slightly favors control; strongest Ayame **H** (4.64) is control (post-QA-regen final).

---

## 10. Per-dimension arm means / deltas

| Dimension | Control | Ablated | Δ (C−A) |
|-----------|--------:|--------:|--------:|
| Character fidelity | 4.25 | 4.50 | −0.25 |
| Distinctiveness | 4.75 | 4.75 | 0.00 |
| Initiative | 3.75 | 4.00 | −0.25 |
| Responsiveness | 5.00 | 4.75 | +0.25 |
| Dramatic progression | 4.00 | 4.00 | 0.00 |
| **Coherence** | 4.25 | 4.75 | **−0.50** |
| Prose quality | 4.00 | 4.00 | 0.00 |
| Repetitiveness | 4.50 | 4.75 | −0.25 |
| Stiffness | 4.75 | 4.75 | 0.00 |
| Unnecessary exposition | 4.25 | 4.00 | +0.25 |
| Emotional/narrative continuity | 4.25 | 4.00 | +0.25 |

No dimension shows a ≥0.20 control advantage. Largest arm gap is **coherence favoring ablated** (−0.50), driven substantially by Sample **E** (control, coherence 3).

---

## 11. Adjunct means / deltas

| Adjunct | Control | Ablated | Δ (C−A) |
|---------|--------:|--------:|--------:|
| Environmental grounding | 4.00 | 3.75 | +0.25 |
| Overall RP usefulness | 4.00 | 4.25 | −0.25 |

Adjuncts are **not** folded into primary mean. Environmental grounding slightly favors control; overall usefulness slightly favors ablated.

---

## 12. Objective correctness integration

**Established (execution):** 8/8 scored runs objectively **clean** (committed, valid PVR, non-empty presentation).

Blind weaknesses (coherence, grounding, invented detail) **did not produce objective harness failures** — they are semantic/subjective quality issues not caught by deterministic gates in this sample.

---

## 13. Sample E state/spatial adjudication after decode

| Field | Value |
|-------|-------|
| Label | **E** |
| Arm | **control** (QA **enabled**) |
| Case | `D07-control-arkham_stress-r1` |
| Blind issue | Magpie described as “new arrival **at the table**” vs briefing placing her **at another table** |
| Locked coherence | **3** (lowest in set) |
| QA outcome | **pass** (no intervention) |

### Adjudication questions

| Question | Answer |
|----------|--------|
| Was E control or ablated? | **Control** |
| Did Narrator QA catch it? | **No** — QA passed |
| Evidence of QA-protected outcome? | **No** — defect present **with** QA on |
| Objectively/deterministically detectable? | **Plausibly yes** — scenario briefing + spatial role assignment could be checked against presentation claims (perceptual/scenario-authority contract) |
| Justifies separate always-on semantic QA? | **Not established** — QA **failed** to catch the blind's clearest coherence defect; argues for **stronger deterministic scenario/spatial validation** at least as much as retaining LLM QA |

**Protected-outcome note:** The blind-identified defect proves **spatial/state discipline matters**; it does **not** prove the current always-on QA topology catches it.

---

## 14. New D-07 QA intervention analysis (control ayame-r2 → Sample H)

### Trace

```text
pre-QA candidate (attempt 0)
  → soft_regen (player-authorship soft overreach, env repetition, framing distortion)
  → narrator regen
  → final presentation (attempt 1 pass) = blind Sample H
```

### Findings

| # | Assessment |
|---|------------|
| 1. What QA objected to | House-number visibility assertion not supported at Player vantage; redundant env restatement; mild framing distortion |
| 2. Objectively valid? | **Partially** — authorship/perception overreach is a real contract concern; repetition is softer |
| 3. Required semantic judgment? | **Partially** — rubric cites authority refs; could be rule-assisted |
| 4. Did regen fix it? | **Yes** — removed house-number clause; tightened threshold prose |
| 5. Was final actually better? | **Blind: yes** — H scored 4.64 (highest Ayame) |
| 6. Degradation introduced? | **No** evidence |
| 7. Deterministic alternative? | **Plausible** — player-authorship / perceptual-inventory checks; fidelity validation already runs pre-QA |

### Counterfactual context

- Ablated ayame-r2 (**D**, no QA) scored **4.55** — strong without intervention.
- QA improved control r2 over its **own** rejected attempt 0, but ablated arm achieved comparable quality without QA cost.

---

## 15. D-10 archive QA intervention analysis

**Governance baseline:** 64 presentations; 9 non-pass (3 hard_regen, 5 soft_regen, 1 authorship_fail_closed, 1 residual_accept).

**D-07 re-parse (partial corpus, 33 events):** 6 non-pass; confirms interventions occur under control topology.

**Blind relevance:** Longitudinal D-10 blind decode showed post-commit ST ablation **neutral-to-positive**; archive QA activity did not prevent ablated quality collapse in that experiment. D-07 extends the pattern to **Narrator QA**: interventions exist but **do not correlate** with control arm blind advantage in this tranche.

---

## 16. Consequential-benefit assessment

| Metric | D-07 new runs | Assessment |
|--------|---------------|------------|
| QA invocations (control) | 7 | — |
| Non-pass interventions | 1 | 14% of control QA events |
| Consequential blind benefit | 1 case (H vs its pre-QA candidate) | **Localized** |
| Control vs ablated blind mean | −0.05 Δ | **No net control advantage** |
| QA failed to catch blind defect | Sample E (control) | **Counter-evidence** |

**Key architectural metric:** QA changed a consequential output for the better **once** in 7 control presentations, while the ablated arm produced **B** (best Arkham) and **D** (strong Ayame) without QA.

---

## 17. Deterministic vs semantic protection assessment

| Protection need | Evidence |
|-----------------|----------|
| Spatial/scenario consistency (E) | Blind-critical; **QA missed**; **deterministic scenario check** candidate |
| Player-authorship overreach (ayame-r2 attempt 0) | QA caught (soft); **deterministic authorship rules** may suffice |
| Overall blind quality | **Comparable** without always-on QA |
| Always-on separate LLM checker | **Not demonstrated** as necessary for net quality in this sample |

Governance refinement applies: catching a defect proves **function/value of protection**; it does **not** automatically prove **always-on separate QA LLM** is the correct topology.

---

## 18. Cost / accounting context

| Arm | Narrator QA calls | Op wall (4 runs) | QA wall (control only) |
|-----|------------------:|-----------------:|-----------------------:|
| Control | 7 | 754,634 ms | ~11.8 s summed |
| Ablated | **0** | 824,651 ms | 0 |

Wall-time not causal (high variance). QA token cost non-trivial but small vs total inference. **7 eliminated QA calls** per 4-run control arm equivalent.

---

## 19. Prospective classification evidence (NOT verdict)

Evidence mapped to accepted categories — **Governance must adjudicate**.

### Separate always-on QA justified

**Evidence against (primary):**

- Overall blind Δ −0.05 (ablated ≥ control)
- Arkham ablated +0.13
- Clearest blind coherence defect on **control** with QA pass (E)
- Single consequential intervention vs 7 QA calls

**Does not meet threshold** on current evidence.

### Function necessary, topology unresolved

**Evidence for:**

- One demonstrated soft-authorship catch + successful regen (H)
- D-10 archive: non-pass events exist
- Semantic judgment partially involved

**Evidence against full always-on topology:**

- Ablated D ≈ post-QA H without QA
- E defect uncaught by QA
- Deterministic/conditional alternatives plausible

**Strongest fit** if Governance finds protection function real but topology unproven.

### Remove / consolidate

**Evidence for:**

- Mirror of D-06 Director QA pattern (no blind degradation; ablated slightly better)
- Rare consequential benefit (1/7 new; low rate in single-turn sample)
- Objective cleanliness matched
- Protection may relocate to deterministic validation / conditional repair

**Strongest fit** if Governance weights net blind + missed-defect evidence over single Ayame regen.

### Inconclusive

**Not supported** — execution clean, decode coherent, no material confound beyond small-N (noted).

---

## 20. Confounds / uncertainty

| Confound | Note |
|----------|------|
| Small-N | n=2 per scenario per arm |
| Single-turn | Low QA intervention rate; D-10 supplements longitudinal |
| Sample H = post-QA final | Cannot blind-score pre-QA candidate |
| Replacement run | `r2-a2` ablated Arkham only |
| E defect uncaught | May reflect QA rubric gap, not QA absence value |

---

## 21. Updated 26-kind coverage implication

| Kind | Prior | Post-D-07 |
|------|-------|-----------|
| `narrator_semantic_qa` | UNCOVERED — synthesis-critical | **COVERED — remove/consolidate candidate** (causal challenge complete; mirror D-06) |
| `narrator_environment_cognition` | UNCOVERED — tiering (D-04R) | **Unchanged** — function necessary / mechanism unresolved |

**Synthesis-critical live gap for Narrator QA:** **closed** pending Governance classification acceptance.

---

## 22. Synthesis-critical live experiments remaining

| Experiment | Status |
|------------|--------|
| D-07 Narrator QA | **Complete** |
| Env cognition live ablation | **Not authorized** / optional |
| Other 26-kind gaps | Low decision value per coverage audit |

**No mandatory live experiment remains** before #201 synthesis if Governance accepts D-07 decode. Env cognition tiering carries as **qualified uncertainty** from D-04R.

---

## 23. Durable record / commit / Issue comment

| Artifact | Path |
|----------|------|
| Locked scores | `issue201-d07-governance-blind-scores-locked.json` (`f3f9d38`) |
| This decode | `issue-201-package-d-d07-blind-decode-synthesis-2026-09-15.md` |

---

## 24. Exact Governance decision required next

1. **Accept** D-07 blind decode as Package D synthesis input.
2. **Adjudicate** D-07 classification among:
   - remove/consolidate (symmetric with D-06 Director QA);
   - function necessary, topology unresolved;
   - separate always-on QA justified (not supported by evidence);
   - inconclusive (not recommended).
3. **Authorize or decline** final #201 synthesis (still paused).
4. **Decline** production Narrator QA / env-tiering changes until synthesis completes.
5. Keep #201 **`investigating`** until synthesis explicitly authorized.

**Do NOT begin final #201 synthesis without Governance authorization.**

---

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
