# Issue #201 — Package D Stage 2: First Causal Tranche Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` (Package D — first causal tranche complete)  
**Assigned / effective weight:** `full` / `full`  
**Experimental SHA:** `c751ea666f0cae6524698005aa5859721c2e9738`  
**Harness:** `v2/rp_runtime/scripts/issue201-package-d-stage2-tranche1.mjs`  
**Evidence root:** `data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/`  
**D0 control root:** `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/`

---

## 1. Activation / state verification

| Field | Value |
|-------|-------|
| `Current status:` | `investigating` |
| Project #10 | In Progress / Investigating / **P1** |
| D0 sufficiency | **Accepted** by Governance |
| First tranche | **Authorized and executed** (EXP-1..3) |
| Production redesign | NOT performed |
| Packages E–G | NOT executed |

---

## 2. Experimental SHA / base

`git rev-parse HEAD` = `c751ea666f0cae6524698005aa5859721c2e9738` (matches D0 control substrate).

---

## 3. Durable D0 snapshot update

| Item | Value |
|------|-------|
| Control SHA | `c751ea666f0cae6524698005aa5859721c2e9738` |
| Arkham config | `arkham_asylum_mess_hall_arena`, opener `mess_hall_magpie`, Magpie watch stimulus |
| Ayame config | `ayame_household_entry_evaluation`, F06 knock stimulus |
| D0 evidence | `issue201-d0-baseline-2026-09-14T07-46-14-584Z/` |
| D0 sufficiency | Sufficient for causal ablation (see D0 record §22) |
| Mediation fan-out variance | Documented; **not** used as automatic 3rd-control trigger |
| #206 blocker | Resolved on D0 path |
| Stage 2 authorization | First tranche EXP-1..3 (EXP-3 = Character orientation bypass, not Storyteller-only) |

---

## 4. Artifact disposition

| Artifact | Disposition |
|----------|-------------|
| `governance/records/issue-201-package-d-stage2-tranche1-2026-09-14.md` | **Commit** (this record) |
| `governance/records/issue-201-package-d-d0-baseline-2026-09-14.md` | **Retained** |
| `v2/rp_runtime/scripts/issue201-package-d-stage2-tranche1.mjs` | **Commit** |
| `v2/rp_runtime/scripts/issue201-package-d-d0-baseline.mjs` | **Retained** |
| `skipCharacterKnowledgeCognition` hook | **Minimal investigation hook** in `character-phase.mjs` + orchestrator (not production redesign) |
| Stage-2 raw bundle | **Retain local** (`data/*` gitignored) |
| `_backfill_meta.py` | **Delete** after report (staging utility) |

---

## 5–11. EXP-1 — Storyteller + Plot preamble bypass

### Intervention design

`roundOptions: { skipStorytellerCognition: true, skipPlotCognitionOrchestration: true }`

### Information-preservation / confound analysis

| # | Analysis |
|---|----------|
| Cognition removed | Storyteller orientation/assessment, plot cognition init/update, associated preamble librarian mediation |
| Output removed | Storyteller advisory package, plot cognition resume summaries |
| Downstream consumers | Director, Character, Narrator (no advisory overlays) |
| Preserved | Scenario, PVR, continuity, character orientation, director, character move, narrator stack |
| Confound | **Low** — existing production skip flags; authoritative context retained |

### Per-run results

| Case | Wall (s) | Inferences | Lib. med. | Committed |
|------|----------|------------|-----------|-----------|
| arkham-r1 | 273.8 | 76 | 6 | yes |
| arkham-r2 | 315.9 | 79 | 8 | yes |
| ayame-r1 | 103.7 | 37 | 1 | yes |
| ayame-r2 | 180.2 | 41 | 4 | yes |

**D0 comparison (mean):** Arkham wall −4% / inferences −9; Ayame wall −15% / inferences −28%.

### Objective correctness

4/4 committed; PVR path unchanged; no harness-flagged perceptual violations.

### Semantic (machine — non-authoritative)

Ayame variants shorter but functional (door opens, invitation). Arkham Ivy voice retained; comparable initiative. Human blind packet required for close judgment.

### Architectural-work comparison

| Metric | Arkham Δ vs D0 | Ayame Δ vs D0 |
|--------|----------------|---------------|
| Inference count | −9 to −12 | −11 to −15 |
| Storyteller/plot kinds | **0** (removed) | **0** |
| Librarian mediation | variable (−4 to +6 vs D0 reps) | −1 to −4 |

### Provisional classification: **conditional retain / tier**

Preamble stack removes ~9–15 inferences/round with **architectural** savings clearer than wall-time savings (fan-out noise). No correctness regression in 4/4. Quality impact **inconclusive** pending human blind eval. Tiering candidate for simple/medium scenes; retain for high-coordination stress until quality evidence says otherwise.

---

## 12–18. EXP-2 — Director semantic QA bypass

### Intervention design

`roundOptions: { directorSemanticQaEnabled: false }`

### Information-preservation / confound analysis

| # | Analysis |
|---|----------|
| Cognition removed | `director_semantic_qa` only |
| Preserved | Director decision inference, structural validation, character semantic evaluation |
| Confound | **Low** for information; **moderate** for safety (QA gate removed) |

### Per-run results

| Case | Wall (s) | Inferences | Dir. QA | Committed |
|------|----------|------------|---------|-----------|
| arkham-r1 | 319.1 | 86 | 0 | yes |
| arkham-r2 | 153.8 | 38 | 0 | **no** (empty presentation) |
| ayame-r1 | 164.7 | 51 | 0 | yes |
| ayame-r2 | 163.0 | 50 | 0 | yes |

### Objective correctness

**3/4 committed.** Arkham-r2: `round_not_committed`, zero-length presentation — **correctness failure** under QA-off; not isolated to RP quality.

### Semantic

Ayame outputs coherent. Arkham-r1 strong Ivy monologue. Arkham-r2 N/A (failure).

### Architectural-work

Director QA removed (0 count all runs). Arkham-r2 anomalously low inference count (38) suggests early abort/failure path — **not** a clean cost sample.

### Provisional classification: **inconclusive** (lean **conditional retain**)

Marginal safety value **demonstrated** on one Arkham failure when QA disabled; Ayame stable 2/2. Cannot conclude removal-safe on stress benchmark from 1 failure / 1 success. **Retain Director QA** for stress until replicated; re-test with 3rd Arkham rep if authorized.

---

## 19–25. EXP-3 — Character orientation cognition bypass

### Intervention design

`roundOptions: { skipCharacterKnowledgeCognition: true }` (new investigation hook)

Skips `runCharacterKnowledgeCognition` (orientation inference + orientation-mediated librarian bundle). Character move still receives `prepareCharacterContext` authoritative manifest; `librarian_bundle` null.

### Information-preservation / confound analysis

| # | Analysis |
|---|----------|
| Cognition removed | `character_orientation`, orientation-mediated `librarian_mediation` |
| Disappears | Orientation `information_gaps`, KAR, orientation librarian bundle |
| Preserved | Authoritative perceptual inventory via prepareCharacterContext, director decision, continuity |
| Confound | **Moderate** — orientation-derived librarian bundle is genuinely novel; bypass tests manifest-only vs manifest+bundle |

**Note:** Initial run blocked by unregistered trace event; fixed to emit existing `hg/character-knowledge-cognition` with `cognition_stage: skipped`. EXP-3 resumed successfully.

### Per-run results

| Case | Wall (s) | Inferences | Orient. | Lib. med. | Committed |
|------|----------|------------|---------|-----------|-----------|
| arkham-r1 | 411.6 | 98 | **0** | 13 | yes |
| arkham-r2 | 272.5 | 80 | **0** | 5 | yes |
| ayame-r1 | 151.4 | 52 | **0** | 3 | yes |
| ayame-r2 | 144.0 | 46 | **0** | 2 | yes |

### Objective correctness

4/4 committed; orientation count **0** confirms bypass.

### Semantic

Outputs remain in-character; no obvious knowledge-boundary violations in presentation text.

### Architectural-work

Orientation removed as intended. **Wall time not reduced** (arkham-r1 **+36%** vs D0 mean); inference count **not lower** on arkham-r1 (98 vs 86). Suggests orientation cost is small relative to fan-out noise; removing bundle may shift work elsewhere.

### Provisional classification: **inconclusive**

Cannot support compact-topology removal of orientation from cost data alone. Correctness stable in 4/4 but **confound moderate**. Needs human quality comparison and possibly fair bundle-preservation variant (future, if authorized).

---

## 26. Cross-experiment comparison

| Exp | Arkham arch. signal | Ayame arch. signal | Correctness | Wall-time interpretability |
|-----|---------------------|--------------------|-------------|---------------------------|
| EXP-1 | −9–12 inferences | −11–15 inferences | 4/4 | Noisy |
| EXP-2 | QA off; 1/2 fail | Stable | 3/4 | Confounded by failure |
| EXP-3 | Orient 0; mixed inf | Orient 0; −6–10 inf | 4/4 | Noisy (r1 slower) |

**Strongest architectural delta:** EXP-1 preamble removal.  
**Strongest correctness signal:** EXP-2 Arkham failure without Director QA.  
**Weakest cost case for removal:** EXP-3 (orientation) — savings not proven.

---

## 27. Librarian / routing fan-out analysis

| Pattern | Observation |
|---------|-------------|
| D0 arkham lib_med | 10 vs 2 |
| EXP-1 arkham | 6 vs 8 |
| EXP-3 arkham | 13 vs 5 |
| Early abort (EXP-2 arkham-r2) | lib_med 1, inf 38 |

**Conclusion:** Librarian mediation fan-out dominates wall-time variance; architectural inference deltas must be reported **per-kind**, not raw wall alone.

---

## 28. World-state observational findings

Non-mutating harness observations (EXP-3 runs with full metadata):

| Dimension | Finding |
|-----------|---------|
| Player PVR recorded | valid on all observed runs |
| Player decomposition present | yes |
| Scene state read | turn_counter available; pressure fields not consistently exposed in API snapshot |
| Ayame portal narrative | door-open language present in committed presentations |
| Promotion to Continuity | **not asserted** — observe-only gap remains |

#200-deferred classifications unchanged.

---

## 29. Blind evaluator methodology / machine results

- **Human packet:** `outputs/issue201-stage2-human-blind-eval-packet.json` (20 samples: 4 D0 + 12 variants)
- **Answer key:** `outputs/issue201-stage2-human-blind-eval-answer-key.json` (restricted)
- **Human status:** **Prepared — awaiting Governance/user evaluation** (not completed autonomously)
- **Machine rubric:** Not used as sole authority per Governance directive

---

## 30. Human-blind packet location / status

**Location:** `data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/outputs/issue201-stage2-human-blind-eval-packet.json`  
**Status:** Ready for human scoring; architecture/experiment/latency stripped from evaluator-facing packet.

---

## 31. Implications for A0–A4

| Topology | Implication |
|----------|-------------|
| A4 (current) | Preamble (EXP-1) is largest **measurable** synchronous stack for tiering experiments |
| A3 compact | EXP-3 does **not** yet justify dropping orientation — cost unproven, confound moderate |
| A2/A1 | EXP-2 suggests Director QA has **conditional** safety value on stress |
| A0 | Insufficient evidence to collapse to single-call |

---

## 32. Next component to challenge

1. **Post-commit join / librarian proposal skip (D-10)** — after human eval on EXP-1 quality
2. **EXP-2 third Arkham rep** — confirm Director QA failure mode
3. **Fair orientation tiering** — only if Governance authorizes bundle-preservation variant

**Not recommended next:** PVR tiering, character semantic-eval removal, compact topology implementation.

---

## 33. Complexity frontier impact

Planned frontier (1-call → 2-call → compact → A4) **unchanged in ordering**. Evidence shifts **confidence**:

- Preamble tiering: **more plausible** (EXP-1 architectural delta)
- Orientation merge into character move: **less plausible** without quality gain (EXP-3)
- Checker removal: **higher risk** (EXP-2)

---

## 34. New blockers / defects

| Item | Severity |
|------|----------|
| EXP-3 trace event (fixed in-session) | Resolved — use existing trace type when skipping cognition |
| EXP-2 arkham-r2 failure | **Evidence**, not infrastructure blocker |
| No production defects blocking further tranches | — |

---

## 35. Durable evidence locations

| Artifact | Path |
|----------|------|
| Tranche report JSON | `.../issue201-package-d-stage2-tranche1-report.json` |
| Per-case meta | `.../outputs/*-meta.json` |
| Presentations | `.../outputs/*-presentation.txt` |
| Latency | `.../outputs/*-latency.txt` |
| Human blind packet | `.../outputs/issue201-stage2-human-blind-eval-packet.json` |

---

## 36. Questions for Governance

1. **Human blind eval:** Who scores `issue201-stage2-human-blind-eval-packet.json`?
2. **EXP-2 follow-up:** Authorize third Arkham EXP-2 repetition after r2 failure?
3. **EXP-1 tiering:** Authorize complexity-gated preamble skip for tier-1/simple scenes?
4. **EXP-3:** Authorize fair bundle-preservation variant, or accept manifest-only test as sufficient?
5. **Next tranche:** D-10 post-commit join vs re-run EXP-2 stress confirmation first?
6. **Issue body:** Update execution snapshot with Stage-2 evidence paths?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** EXP-1, EXP-2, EXP-3 (2× Arkham + 2× Ayame each) + human blind packet  
**Not executed:** Further tranches, E–G synthesis, production redesign
