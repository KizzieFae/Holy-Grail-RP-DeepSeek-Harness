# Issue #201 — Package D Stage-3 Preamble Decomposition Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Execution SHA:** `b391336ced019c409fb1499db8636fd18e6424f9`  
**Evidence commit:** `42be339`  
**Harness:** `v2/rp_runtime/scripts/issue201-package-d-stage3-preamble-decomposition.mjs`  
**Evidence root:** `data/investigation_runs/issue201-package-d-stage3-2026-09-14T18-16-06-752Z/`  
**D0 reused:** `issue201-d0-baseline-2026-09-14T07-46-14-584Z/`  
**D-01 combined reused:** `issue201-package-d-stage2-2026-09-14T08-09-42-791Z/` (EXP-1)

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| Status | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| Stage-3 tranche | **Executed** (D-01a + D-01b) |
| Blind eval | **Complete, locked, decoded** — see `issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` |
| Production redesign | **NOT authorized** |

---

## 2. Execution SHA / base

| Anchor | Value |
|--------|-------|
| Repo HEAD at execution | `b391336` |
| Control substrate | `c751ea6` |
| Harness hook surface | existing `skipStorytellerCognition`, `skipPlotCognitionOrchestration` — **no control-path code changes** |

---

## 3. Issue body / execution snapshot

Updated via `gh issue edit 201` (2026-09-14) — Stage-2 synthesis SHA, Package D milestones, Stage-3 authorization recorded. Staging text: `governance/records/_issue-201-body-stage3-update.md`.

---

## 4. Durable per-dimension blind-score export (Stage-2)

`governance/records/issue201-stage2-governance-blind-scores-per-dimension-export.md`  
Locked means: `governance/records/issue201-stage2-governance-blind-scores-locked.json`  
**Note:** Per-dimension matrix was Governance-locked before decode; dimensional detail not transmitted to Implementation AI in structured form — means + decode mapping preserved.

---

## 5. Artifact disposition

| Artifact | Path | Disposition |
|----------|------|-------------|
| Stage-3 harness | `v2/rp_runtime/scripts/issue201-package-d-stage3-preamble-decomposition.mjs` | **Commit** |
| Tranche report | `.../issue201-package-d-stage3-preamble-decomposition-report.json` | Gitignored evidence |
| Blind packet | `.../outputs/issue201-stage3-human-blind-eval-packet.json` | Gitignored |
| Answer key | `.../outputs/issue201-stage3-human-blind-eval-answer-key.json` | Gitignored, concealed |
| Matrix helper | `tools/investigation/summarize_stage3_matrix.py` | **Commit** |
| Governance transport | `governance/records/issue201-stage3-governance-blind-transport.md` | **Commit** |

---

## 6–10. D-01b — Storyteller-only bypass

### Intervention design

`roundOptions: { skipStorytellerCognition: true }` — Plot cognition retained.

### Information-preservation analysis

| Category | Detail |
|----------|--------|
| Cognition removed | `storyteller_orientation`, `storyteller_assessment`, storyteller-lane `librarian_mediation` |
| Derived info removed | Storyteller advisory package, storyteller-mediated librarian bundle |
| Preserved | Plot init/update, scenario premise, PVR, continuity, director, character orientation, narrator env |
| Downstream consumers | Director/character receive authoritative manifest without storyteller advisory overlay |
| Plot input change | Plot cognition runs without storyteller advisory binding — **moderate interaction risk** |
| Confound | Low–moderate |

### Per-run results (final successful set)

| Case | Committed | Wall (s) | Inf | ST | Plot | Lib |
|------|-----------|--------:|----:|---:|-----:|----:|
| arkham-r1 | yes | 338.2 | 90 | 2 | 2 | 6 |
| arkham-r2 | yes | 281.2 | 79 | 2 | 2 | 1 |
| ayame-r1 | yes | 113.3 | 49 | 1 | 1 | 1 |
| ayame-r2 | yes | 130.6 | 47 | 0 | 1 | 7 |

**Arkham mean:** wall 309.7s, inf 84.5, ST 2, plot 2, lib 3.5  
**Ayame mean:** wall 121.9s, inf 48, ST 0.5, plot 1, lib 4

### Architectural deltas vs D0

| Metric | Arkham Δ | Ayame Δ |
|--------|----------|---------|
| Inference count | −1.5 | −6 |
| Storyteller inferences | −1 | −2 |
| Plot inferences | 0 | 0 |
| Librarian mediation | −2.5 | −1 |

### Correctness

4/4 committed (final). PVR valid all runs. No auto-detected boundary violations.

---

## 11–15. D-01a — Plot-only bypass

### Intervention design

`roundOptions: { skipPlotCognitionOrchestration: true }` — Storyteller cognition retained.

### Information-preservation analysis

| Category | Detail |
|----------|--------|
| Cognition removed | `plot_cognition_init`, `plot_cognition_update`, plot resume lifecycle |
| Derived info removed | Plot cognition resume summaries |
| Preserved | Storyteller orientation/assessment, librarian (storyteller lane), authoritative manifest, PVR, continuity |
| Downstream consumers | Character move receives manifest; no plot resume advisory |
| Storyteller input change | Storyteller runs without plot resume context — **moderate interaction risk** |
| Confound | Low–moderate |

### Per-run results

| Case | Committed | Wall (s) | Inf | ST | Plot | Lib |
|------|-----------|--------:|----:|---:|-----:|----:|
| arkham-r1 | yes | 183.9 | 74 | 3 | 0 | 1 |
| arkham-r2 | yes | 1440.0* | 77 | 3 | 0 | 6 |
| ayame-r1 | yes | 236.5 | 53 | 3 | 0 | 2 |
| ayame-r2 | yes | 124.1 | 48 | 3 | 0 | 2 |

\*arkham-r2 wall time includes prolonged retry/coordination episode (transient infrastructure); inference count normal.

**Arkham mean (raw):** wall 811.9s*, inf 75.5, ST 3, plot 0, lib 3.5  
**Arkham mean (r1 only for wall sanity):** 183.9s  
**Ayame mean:** wall 180.3s, inf 50.5, ST 3, plot 0, lib 2

### Architectural deltas vs D0

| Metric | Arkham Δ | Ayame Δ |
|--------|----------|---------|
| Inference count | −10.5 | −3.5 |
| Storyteller inferences | 0 | +0.5 |
| Plot inferences | −2 | −1 |
| Librarian mediation | −2.5 | −3 |

### Correctness

4/4 committed (final). PVR valid. No auto-detected boundary violations.

---

## 16–17. Control reuse rationale

| Source | Rationale |
|--------|-----------|
| **D0** | Accepted baseline; no substrate change; identical scenarios/stimuli |
| **D-01 combined** | Stage-2 EXP-1 evidence; same hooks and SHA family; avoids redundant live inference |

**Controls not rerun** — harness uses existing presentation/meta paths only.

---

## 18. Librarian / routing fan-out

| Variant | Arkham lib mean | Ayame lib mean | Notes |
|---------|----------------:|---------------:|-------|
| D0 | 6.0 | 5.0 | Baseline fan-out |
| D-01 | 7.0 | 2.5 | Combined removal |
| D-01b | 3.5 | 4.0 | Storyteller lane reduced |
| D-01a | 3.5 | 2.0 | Lowest ayame fan-out |

Fan-out remains noisy; prefer inference-kind deltas over wall time for Arkham (especially D-01a r2 outlier).

---

## 19. World-state observations

PVR valid on all committed runs. Ayame portal/door observations consistent with prior tranches. Player promotion / portal authority not auto-verified.

---

## 20–22. Blind evaluation

| Artifact | Path |
|----------|------|
| Blind packet | `.../outputs/issue201-stage3-human-blind-eval-packet.json` |
| Answer key (concealed) | `.../outputs/issue201-stage3-human-blind-eval-answer-key.json` |
| Transport guide | `governance/records/issue201-stage3-governance-blind-transport.md` |

**16 samples** (A–P): 4× D0 + 4× D-01 + 4× D-01a + 4× D-01b.  
**Status:** Governance locked → decoded. Locked means: `issue201-stage3-governance-blind-scores-locked.json`.

---

## 23. Failed / transient samples

| Case | Attempts | Disposition |
|------|----------|-------------|
| D-01b-arkham-r1 | 1× `character_failure` (0-byte); 1× `turn/end` timeout; **3rd committed** | Superseded failures excluded from matrix |
| D-01a-arkham-r1 | 1× `turn/end` on director; **2nd committed** | Superseded failure excluded |
| D-01a-arkham-r2 | 1× success with extreme wall outlier | Retained; flagged for fan-out/wall interpretation |

No additional repetitions beyond authorized retries.

---

## 24. 2×2 preamble matrix (runtime / objective only — pre-decode)

| Variant | ST | Plot | Arkham inf (mean) | Ayame inf (mean) | ST/plot removed as intended? | Committed |
|---------|:--:|:----:|------------------:|-----------------:|:----------------------------:|----------:|
| **D0** | on | on | 86 | 54 | — | 4/4 |
| **D-01b** | off | on | 84.5 | 48 | partial ST (0–2 remain*) | 4/4 |
| **D-01a** | on | off | 75.5 | 50.5 | plot **0** | 4/4 |
| **D-01** | off | off | 77.5 | 39 | ST+plot **0** | 4/4 |

\*Residual storyteller-kind counts on D-01b likely post-commit storyteller pressure inferences — not preamble orientation/assessment; verify in evidence if needed.

**Objective-only observation (no semantic inference):** D-01 removes the most preamble inference mass; single-removal variants show partial reduction with plot-only (D-01a) achieving clearer plot-kind zeroing than storyteller-only (D-01b) achieves for storyteller kinds.

---

## 25. Remaining confounds

1. Storyteller↔plot interaction when one lane remains  
2. Residual storyteller-tagged inferences on D-01b  
3. Arkham wall-time noise / transient `turn/end` infrastructure errors  
4. Small-N (n=2 per scenario per cell)  
5. Semantic quality not yet measured for Stage-3 packet

---

## 26. Updated §1–23 coverage

| § | Advance |
|---|---------|
| 10 Quality contribution | Stage-3 blind packet prepared; decode pending |
| 16 Conditional components | Preamble decomposition evidence added (runtime) |
| 18 Simplifications | 2×2 matrix populated for causal test |
| 21 Latency ranges | D-01a Arkham wall outlier documented |

---

## 27. Recommended next step (ranked)

1. **Governance blind scoring** of Stage-3 packet (gate before decode)  
2. **Decode + pattern classification** (A–E templates)  
3. **D-10 post-commit join** — only if preamble decomposition clarifies quality lever  
4. EXP-3 complexity contrast — still deferred

---

## 28. Governance decisions required

1. Accept Stage-3 runtime evidence as sufficient for blind scoring?  
2. Authorize Governance blind scoring of `issue201-stage3-human-blind-eval-packet.json`?  
3. Supply Stage-2 per-dimension score matrix for durable repo export?  
4. Treat D-01a arkham-r2 wall outlier as retained or request replacement rep?  
5. Authorize next tranche based on decode pattern (D-10 vs further preamble refinement)?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** D-01a + D-01b execution, blind packet, Governance blind scoring, decode synthesis  
**Not executed:** D-01-L longitudinal tranche, D-10, new ablations, production tiering
