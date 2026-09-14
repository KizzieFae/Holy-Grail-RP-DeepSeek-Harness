# Issue #201 — Package D Stage-3 Decode Synthesis & Longitudinal Storyteller Experiment Proposal

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Control substrate SHA:** `c751ea666f0cae6524698005aa5859721c2e9738`  
**Stage-3 evidence commit:** `42be339`  
**Prior records:** D0 baseline, Stage-1/2 tranches, Stage-2 synthesis (`b391336`), Stage-3 preamble decomposition (`42be339`)  
**Locked scores:** `governance/records/issue201-stage3-governance-blind-scores-locked.json`

---

## 1. Exact current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| Package D D0 | **Accepted** |
| Stage-2 tranche 1 + refinement | **Accepted** (`b391336`) |
| Stage-3 preamble decomposition (D-01a + D-01b) | **Executed** (`42be339`) |
| Stage-3 blind eval | **Complete, locked, decoded** (Governance AI) |
| Longitudinal Storyteller test | **Proposed — NOT authorized** |
| D-10 post-commit join | **Deferred** pending longitudinal Storyteller decision |
| Production redesign / remediation | **NOT authorized** |
| Packages E–G | **NOT authorized** |

---

## 2. Durable evidence update

| Artifact | Path | Status |
|----------|------|--------|
| Stage-3 tranche report | `data/investigation_runs/issue201-package-d-stage3-2026-09-14T18-16-06-752Z/issue201-package-d-stage3-preamble-decomposition-report.json` | Gitignored; cited |
| Stage-3 blind packet | `.../outputs/issue201-stage3-human-blind-eval-packet.json` | Gitignored |
| Stage-3 answer key | `.../outputs/issue201-stage3-human-blind-eval-answer-key.json` | Gitignored |
| Stage-3 execution record | `governance/records/issue-201-package-d-stage3-preamble-decomposition-2026-09-14.md` | Committed `42be339` |
| **Locked Stage-3 blind scores** | `governance/records/issue201-stage3-governance-blind-scores-locked.json` | **This record** |
| **Stage-3 decode synthesis** | `governance/records/issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` | **This record** |

**Scoring integrity:** Governance locked all sample means **before** answer-key reveal. Implementation AI records decode mapping only; means are not rescored or altered.

**Reused evidence in Stage-3 matrix:**

| Source | Cases |
|--------|-------|
| D0 baseline (`issue201-d0-baseline-...`) | B, E, K, L |
| Stage-2 EXP-1 / D-01 (`issue201-package-d-stage2-...`) | G, H, I, N |
| Stage-3 live (D-01a, D-01b) | A, C, D, F, J, M, O, P |

---

## 3. Decoded 2×2 matrix (locked)

| Cell | Storyteller | Plot | Arkham | Ayame | Overall | Δ vs D0 |
|------|:-----------:|:----:|-------:|------:|--------:|--------:|
| **D0** | ON | ON | 4.545 | 4.405 | **4.475** | — |
| **D-01b** | OFF | ON | 4.545 | 4.180 | **4.363** | −0.113 |
| **D-01a** | ON | OFF | 4.270 | 4.135 | **4.203** | −0.272 |
| **D-01** | OFF | OFF | 4.225 | 4.090 | **4.158** | −0.318 |

**Small-N only (n=2 per scenario per cell).** Not statistically significant.

### Sample attribution (locked means)

| Label | Mean | Cell | Case |
|------:|-----:|------|------|
| A | 4.09 | D-01b | `D-01b-arkham_stress-r2` |
| B | 4.45 | D0 | `D0-arkham_stress-r2` |
| C | 4.45 | D-01b | `D-01b-ayame_controlled-r2` |
| D | 4.36 | D-01a | `D-01a-arkham_stress-r1` |
| E | 4.36 | D0 | `D0-ayame_controlled-r1` |
| F | 4.00 | D-01a | `D-01a-ayame_controlled-r1` |
| G | 4.45 | D-01 | `EXP-1-ayame_controlled-r2` |
| H | 4.36 | D-01 | `EXP-1-arkham_stress-r1` |
| I | 3.73 | D-01 | `EXP-1-ayame_controlled-r1` |
| J | 4.27 | D-01a | `D-01a-ayame_controlled-r2` |
| K | 4.45 | D0 | `D0-ayame_controlled-r2` |
| L | 4.64 | D0 | `D0-arkham_stress-r1` |
| M | 4.18 | D-01a | `D-01a-arkham_stress-r2` |
| N | 4.09 | D-01 | `EXP-1-arkham_stress-r2` |
| O | 3.91 | D-01b | `D-01b-ayame_controlled-r1` |
| P | **5.00** | D-01b | `D-01b-arkham_stress-r1` |

---

## 4. Factorial marginal effects (descriptive)

Computed from cell overall means (not population estimates):

| Effect | Value | Method |
|--------|------:|--------|
| **Plot ON vs OFF** | **+0.239** | mean(D0, D-01b) − mean(D-01a, D-01) |
| **Storyteller ON vs OFF** | **+0.079** | mean(D0, D-01a) − mean(D-01b, D-01) |
| **Interaction (DiD)** | **≈ +0.068** | (D0−D-01a) − (D-01b−D-01) |

**Plot marginal by scenario:**

| Scenario | Plot ON (D0, D-01b) | Plot OFF (D-01a, D-01) | Δ |
|----------|--------------------:|-----------------------:|--:|
| Arkham | 4.545 | 4.248 | +0.298 |
| Ayame | 4.293 | 4.113 | +0.180 |

**Storyteller marginal by scenario:**

| Scenario | ST ON (D0, D-01a) | ST OFF (D-01b, D-01) | Δ |
|----------|------------------:|---------------------:|--:|
| Arkham | 4.408 | 4.385 | +0.023 |
| Ayame | 4.270 | 4.135 | +0.135 |

---

## 5. Plot interpretation (provisional classification)

**Retain function — demonstrated marginal immediate-turn RP value. Architecture/topology unresolved.**

| Signal | Evidence |
|--------|----------|
| Overall marginal | Plot ON beats Plot OFF by **+0.239** (descriptive) |
| Arkham | Strong immediate-turn signal; Plot removal (D-01a) drops Arkham to 4.270 |
| Ayame | Moderate signal; both components contribute when removed singly |
| Stage-2 consistency | EXP-1 combined removal (−0.318 Stage-3; −0.32 Stage-2) — Plot is largest single-removal contributor |

**Does NOT establish:**

- Every Plot call is necessary every turn
- Current inference count is justified
- Current mediation/topology is optimal
- Plot must remain a separate agent

**Continue to distinguish useful function from current mechanism.**

---

## 6. Storyteller interpretation (provisional classification)

**Weak/conditional immediate-turn marginal value; strong consolidation/tiering/removal candidate for the synchronous turn path.**

| Signal | Evidence |
|--------|----------|
| Overall marginal | Storyteller ON beats OFF by only **+0.079** (descriptive) |
| Arkham | **No average degradation** when Storyteller removed with Plot ON (D-01b = D0 at 4.545) |
| Arkham peak | Blind top score **P = 5.00** is D-01b (Storyteller OFF / Plot ON) |
| Ayame | Storyteller removal with Plot ON costs **−0.225** (4.405 → 4.180) |
| Interaction | Positive DiD suggests Storyteller may partially compensate when Plot is off — treat cautiously (n=2/cell) |

**Do NOT classify Storyteller as globally unnecessary.**

Intended value may manifest over **multi-turn narrative horizon** (agenda persistence, escalation, unresolved-thread management) rather than in the immediately following presentation. Stage-3 one-turn design is **underpowered** for Storyteller's architectural charter per `architecture-overview.md` (advisory narrative cognition, issue-tension pressure).

---

## 7. Scenario-specific differences

### Arkham mess hall stress

| Cell | Score |
|------|------:|
| D0 | 4.545 |
| D-01b (ST OFF / Plot ON) | 4.545 |
| D-01a (ST ON / Plot OFF) | 4.270 |
| D-01 (both OFF) | 4.225 |

- Plot carries the dominant immediate-turn signal.
- Storyteller removal with Plot active shows **no observed average Arkham degradation**.
- Highest blind sample (P) is Storyteller-ablated with Plot retained.

### Ayame household entry (controlled)

| Cell | Score |
|------|------:|
| D0 | 4.405 |
| D-01b | 4.180 |
| D-01a | 4.135 |
| D-01 | 4.090 |

- Both preamble components show signal.
- Possible positive interaction (combined removal worse than sum of singles) — **cautious** (n=2/cell).
- Controlled threshold scenes may depend more on preamble framing than open stress scenes.

---

## 8. Reliability / failure interpretation (separate from semantic quality)

| Event | Case | Packet label | Classification |
|-------|------|:------------:|----------------|
| 2 superseded failures then 3rd commit | `D-01b-arkham_stress-r1` | P | **Insufficient evidence** for intervention-specific causation; pattern matches **generic orchestration/runtime instability** (`character_failure` 0-byte, `turn/end` timeout) — same class as Stage-2 EXP-2 forensic failures |
| 1 superseded `turn/end` then commit | `D-01a-arkham_stress-r1` | D | **Generic orchestration/runtime instability** |
| ~24 min wall outlier, normal inference band | `D-01a-arkham_stress-r2` | M | **Generic orchestration/runtime instability** (coordination/retry episode); **not** semantic-quality signal; locked mean 4.18 retained analytically separate |

**Defect-splitting assessment:** Existing evidence does **not** satisfy criteria for a separate remediation Issue. Failures are transient infrastructure class; committed presentations are valid (PVR valid, 4/4 final). No new blocker filed.

---

## 9. Implications for A0–A4

| Topology | Updated implication after Stage-3 decode |
|----------|----------------------------------------|
| **A4 (current)** | Plot preamble shows **measurable immediate-turn quality contribution**; Storyteller synchronous preamble shows **weak** immediate-turn contribution with **scenario interaction** |
| **A3 compact** | Storyteller **tiering/removal from synchronous path** strengthened as hypothesis; Plot **not** a removal candidate on one-turn evidence |
| **A2/A1** | EXP-2 (D-06) unchanged — Director QA combine/remove candidate |
| **A0** | Still insufficient to collapse; boundary + preamble machinery still required |

---

## 10. Updated component-value ledger

| Component / experiment | Stage-2 classification | Stage-3 update |
|------------------------|------------------------|----------------|
| **Plot cognition** | Retain (via EXP-1 decomposition candidate) | **Retain function** — strongest immediate-turn marginal; mechanism/topology still open |
| **Storyteller cognition** | Retain; decompose (EXP-1) | **Weak/conditional synchronous value**; **longitudinal test required** before tier/removal/consolidation decision |
| **EXP-1 / D-01 combined** | Retain function; decompose | Decomposed: Plot drives majority of combined delta |
| **EXP-2 / D-06 Director QA** | Combine/remove candidate | **Unchanged** |
| **EXP-3 / D-03 orientation** | Complexity-tier candidate | **Unchanged** — defer contrast |
| **D-10 post-commit join** | Candidate after preamble | **Deferred** — after longitudinal Storyteller gate |
| **Character orientation** | Tier candidate | Unchanged |
| **Librarian mediation** | Cost noise; fan-out | Unchanged — not isolated in Stage-3 |

---

## 11. New causal question

> **Does Storyteller cognition produce material value over a multi-turn narrative trajectory when Plot cognition remains active?**

Stage-3 answered **immediate-turn** preamble value decomposition. Storyteller's intended responsibilities (advisory narrative cognition, issue-tension persistence, escalation guidance) may not manifest in a single player murmur or knock. Next tranche must test Storyteller on a **longer horizon** with Plot held ON.

---

## 12. Proposed test design — **D-01-L** (longitudinal Storyteller value; NOT executed)

### 12.1 Concept

| Arm | Storyteller | Plot | `roundOptions` |
|-----|:-----------:|:----:|----------------|
| **Control** | ON | ON | none (D0-equivalent preamble) |
| **Storyteller-ablated** | OFF | ON | `skipStorytellerCognition: true` (D-01b-equivalent preamble) |

All other architecture matched (Director, character, narrator, PVR, continuity, EXP-2 QA state unchanged from control substrate).

### 12.2 Scenarios

| Priority | Scenario | Rationale |
|----------|----------|-----------|
| **Primary** | **Arkham mess hall — multi-turn stress arc** | Stage-3 shows Plot-dominant immediate signal but Storyteller may matter for escalation, ward dynamics, unresolved threads across turns |
| **Secondary (confirmatory)** | **Ayame household — 3-turn interview arc** | Tests whether Storyteller adds longitudinal value in controlled/threshold scenes (Stage-3 Ayame showed ST sensitivity) |

**Arkham alone is insufficient** for general Storyteller verdict; Ayame confirmatory arm prevents overfitting to stress-only conclusions.

**Optional later:** purpose-built multi-NPC agenda scenario — **not required** for first longitudinal tranche if Arkham+Ayame arcs are pre-authored with explicit narrative-pressure checkpoints.

### 12.3 Turn count

| Scenario | Turns per sequence | Rationale |
|----------|-------------------:|-----------|
| Arkham | **5** player turns | Allows: provocation → reaction → escalation → consequence hook → unresolved carryover |
| Ayame | **3** player turns | Knock/entry → evaluation probe → tension/reveal beat without excessive cost |

Evaluators score **per-turn presentations** and **sequence-level longitudinal dimensions**.

### 12.4 Player stimuli — fixed script (matched arms)

- **Fixed authored stimulus script per turn** — identical across control and ablated arms for each sequence replication.
- **No live adaptive player improvisation** during experiment execution.
- Branching only via **pre-committed script variants** if needed (both arms receive same branch).
- Preserves causal comparability; isolates Storyteller accumulation effects.

**Arkham example arc (illustrative):**

1. Magpie murmur (existing Stage-3 stimulus)
2. Magpie presses guard-watch angle / tests Harley-Ivy dynamic
3. Magpie makes semi-public bid for leverage
4. Magpie escalates or deflects guard attention
5. Magpie leaves thread open (non-resolution)

**Ayame example arc:**

1. Knock / entry (existing stimulus)
2. Kizzie answers evaluative question with partial disclosure
3. Kizzie challenges household rule / tests Ayame composure

### 12.5 Causal comparability controls

- Same `control_substrate_sha`, scenario ids, character cards, opener preferences
- Same repetition indices and harness instrumentation
- Plot ON in both arms; only `skipStorytellerCognition` differs
- Matched player stimulus scripts and turn order
- Same blind rubric + correctness gates
- Reuse D-01b Stage-3 hook surface (`skipStorytellerCognition`) — no new control-path code

### 12.6 Storyteller outputs expected to matter across turns

| Output | Turn scope | Longitudinal role |
|--------|------------|-------------------|
| `storyteller_orientation` | Per-turn preamble | Scene framing, attention allocation |
| `storyteller_assessment` | Per-turn preamble | Narrative pressure interpretation |
| `StorytellerAdvisoryPackage` → packaging lanes | Per-turn | Director/character suggestive context |
| Storyteller-mediated librarian bundles | Per-turn | Enriched advisory context |
| `storyteller_post_commit_issue_pressure` (#164) | Post-commit | Issue tension persistence / escalation eligibility |
| Preservation / tension signals | Advisory | Thread carryover hints (non-authoritative) |

### 12.7 Downstream consumers

| Consumer | Uses Storyteller output |
|----------|-------------------------|
| Packaging / Librarian | `storyteller_*` mediation lanes |
| Director | Advisory context in decision graph |
| Character prep | Indirect via manifest/advisory overlay |
| Post-commit semantic path | Issue tension pressure proposer (#164) |

### 12.8 Accumulation / expiry behavior

- **Plot cognition** persists via resume summaries and scope state — **continues normally** in ablated arm.
- **Storyteller advisory** is per-round generated; when skipped, downstream receives manifest **without** storyteller overlay; no synthetic backfill.
- **Issue pressure** may fail to accumulate/eligible-escalate without Storyteller post-commit assessments — measurable objective delta.
- **Continuity / PVR / authoritative commits** unchanged — ablation removes advisory cognition only.

### 12.9 When Storyteller absent (ablated arm)

- No orientation/assessment preamble inferences
- No storyteller-mediated librarian bundle
- Plot init/update and resume still execute
- Director/character operate on authoritative manifest + plot state only
- Post-commit `storyteller_post_commit_issue_pressure` may skip or run degraded — verify eligibility gate behavior in harness metrics

### 12.10 Plot fairness

Plot cognition **fully retained** in ablated arm (D-01b-equivalent). No plot starvation. Confound from Stage-3 D-01b (plot without storyteller binding) is **accepted and documented** — same as D-01b tranche.

### 12.11 Information-preservation rules

| Removed (ablated arm only) | Must preserve |
|----------------------------|---------------|
| Storyteller orientation/assessment | Scenario premise, character cards, continuity, PVR |
| Storyteller-mediated librarian | Plot cognition, authoritative manifest, director/character/narrator authoritative inputs |
| Storyteller advisory overlay | Legitimate plot resume + commit path to Character Move |

**Rule:** Ablations remove cognition only; no authoritative state starvation.

### 12.12 Authoritative state preservation

- Identical player stimulus scripts → identical player commit opportunities
- PVR validation required each turn
- Continuity turn index monotonic
- No manual continuity injection differing by arm

### 12.13 Objective correctness measures (per turn + sequence)

| Measure | Pass criterion |
|---------|----------------|
| `committed` | true all turns |
| `pvr_validation_status` | `valid` |
| `issue_count` (auto boundary) | 0 material violations |
| Turn completion | all scripted turns executed |
| Inference-kind presence | Plot kinds >0; Storyteller kinds =0 in ablated arm (preamble); control has Storyteller kinds |
| Wall-time outliers | Flagged separately; excluded from quality conclusions |
| Sequence integrity | No missing turns; matched commit counts across arms |

### 12.14 Longitudinal semantic-quality rubric

**Per-turn:** retain existing 11 dimensions (Stage-2/3 worksheet).

**Sequence-level additions (1–5 each):**

| Dimension | What to judge |
|-----------|----------------|
| **Thread persistence** | Do unresolved threads carry forward appropriately? |
| **Escalation coherence** | Does pressure build logically across turns? |
| **Agenda persistence** | Do NPC agendas remain active vs reset? |
| **Delayed consequences** | Do earlier beats matter later? |
| **Scene momentum** | Does the sequence advance vs stall? |
| **Cross-turn initiative** | Do NPCs proactively drive multi-turn beats? |
| **Reactive-loop avoidance** | Are repetitive stalls absent? |
| **Premature-resolution avoidance** | Is tension preserved when script expects it? |
| **Plot drift control** | Does narrative stay on-scenario rails? |
| **Emotional/narrative continuity (sequence)** | Cross-turn emotional through-line |

**Primary endpoint:** sequence mean of per-turn means + sequence-level mean (weighted 50/50 proposed).

### 12.15 Correctness rubric

Separate from semantic scores — automated harness + spot-check:

- Commit success rate
- PVR validity rate
- Boundary issue count
- Storyteller-kind zero in ablated preamble (with documented post-commit residual tolerance as in D-01b)
- Plot-kind non-zero both arms
- Turn/script adherence

### 12.16 Blind evaluation feasibility

**Feasible** with extensions:

- Blind **turn bundles** or **sequence excerpts** labeled anonymously (e.g., Seq-1 Turn-3 presentation)
- Evaluator receives scenario briefing + cumulative prior-turn context (player stimuli only) without arm identity
- Sequence-level scores applied after all turns in a bundle reviewed
- Lock scores before decode (same protocol as Stage-2/3)

### 12.17 Randomization / blinding

- Randomize sequence replications to blind labels
- Shuffle turn-bundle order where context window allows (or keep turn order within bundle — mandatory for longitudinal)
- Conceal: arm, session id, experiment id, inference counts, wall time
- Answer key maps blind label → arm + sequence + turn index

### 12.18 Expected inference / cost delta

| Metric | Estimate (per 5-turn Arkham sequence) |
|--------|--------------------------------------|
| Storyteller kinds removed (ablated) | ~3–6 preamble inferences/turn × 5 ≈ 15–30 fewer per sequence |
| Librarian storyteller lane | Variable; Stage-3 D-01b Δ lib ≈ −2.5 Arkham mean per **single** turn |
| Wall time | Stage-3 single-turn D-01b ≈ similar quality with mixed wall; expect **moderate** savings if storyteller preamble removed, not proportional to quality delta |
| Total tranche (proposed) | 2 arms × (2 Arkham seq + 2 Ayame seq) × reps — **~16–24 committed turns** depending on rep strategy |

### 12.19 Repetition strategy

| Unit | Reps | Rationale |
|------|------|-----------|
| Arkham 5-turn sequence | **2** per arm | Match Package D small-N discipline |
| Ayame 3-turn sequence | **2** per arm | Confirmatory |
| **Total** | **8 sequences** (4 per arm) | 32 turn-presentations for blind pool |

### 12.20 Stopping criteria

**Pre-registered (no mid-tranche peeking decode):**

1. Complete all scripted turns for all authorized sequences
2. ≥1 committed presentation per turn per sequence (retry supersession allowed as Stage-3)
3. If >2 consecutive `turn/end` failures on same case → pause tranche, forensic classify (do not auto-expand reps)
4. Decode only after blind lock
5. **No early stop for positive/negative quality** — small-N already limits power

### 12.21 Outcome discrimination framework

| Outcome pattern | Interpretation |
|-----------------|----------------|
| Control ≈ ablated on sequence rubric | **No Storyteller longitudinal value** (at tested horizon) → strong synchronous tiering/removal candidate |
| Control > ablated consistently | **Delayed Storyteller value** demonstrated → retain but reconsider placement (periodic/async) |
| Control > ablated only on Arkham (or high-complexity) | **Complexity-conditioned value** → tier by scene class |
| Ablated ≈ control on semantics but large objective pressure deltas | Value may be **off critical path** (post-commit / between scenes) |
| Mixed per-turn win + sequence loss | Storyteller helps **arc** not **line** — supports async/periodic hypothesis |

### 12.22 Synchronous vs periodic Storyteller hypotheses

Storyteller may be relocatable without loss:

| Mode | Testable if |
|------|-------------|
| **Periodic (every N turns)** | Longitudinal tranche shows value but not every-turn necessity |
| **Conditional (complexity gate)** | Arkham > Ayame differential repeats |
| **Between scenes** | Sequence-level value without per-turn prose delta |
| **After presentation (async advisory)** | Objective issue-pressure differs; per-turn prose neutral |

D-01-L does **not** implement relocations — it establishes whether **any** synchronous multi-turn value exists with Plot ON.

### 12.23 Risks / confounds

1. Storyteller↔Plot interaction (D-01b confound accepted)
2. Residual post-commit storyteller kinds on ablated arm
3. Fixed script reduces ecological validity
4. Small-N (2 sequences/arm/scenario)
5. Arkham vs Ayame divergence
6. Infrastructure `turn/end` noise (documented Stage-3)
7. Evaluator fatigue on multi-turn bundles
8. Continuity contamination if sequences share world state incorrectly — mitigate with fresh session per sequence

### 12.24 Expected information gain

| Question | Resolution power |
|----------|------------------|
| Does Storyteller matter when Plot ON over multiple turns? | **High** — primary gate for tier/removal |
| Is Storyteller value line-level or arc-level? | **Medium** — via per-turn vs sequence rubric split |
| Is value complexity-conditioned? | **Medium** — Arkham vs Ayame arms |
| Can Storyteller leave synchronous path? | **Medium** — if arc-level value without per-turn gain |
| Justify D-10 next? | **Low** — deferred until Storyteller placement decided |

---

## 13. D-10 status

**NOT executed.** Remains candidate for post-commit join cost (`skipLibrarianProposalGeneration`) **after** longitudinal Storyteller value decision. Stage-3 decode does not elevate D-10 priority above Storyteller horizon test.

---

## 14. Updated §1–23 assessment coverage

| § | Deliverable | Status after Stage-3 decode |
|---|-------------|----------------------------|
| 1 | Architecture map | **Advanced** — 2×2 preamble matrix populated |
| 2 | Critical-path map | **Advanced** — Stage-3 wall/inference per cell |
| 3 | Inference inventory | **Satisfied** |
| 4 | Component value ledger | **Advanced** — Plot retain; Storyteller conditional/longitudinal |
| 5 | Checker/correction ledger | **Advanced** — EXP-2 unchanged |
| 6 | Information-handoff map | **Advanced** — preamble decomposition complete |
| 7 | Historical rationale | **Satisfied** |
| 8 | Latency contribution | **Advanced** — outlier flagged separately |
| 9 | Correctness contribution | **Advanced** — 4/4 committed; reliability class noted |
| 10 | **Quality contribution** | **Advanced** — Stage-3 blind factorial decode |
| 11 | Failure modes | **Advanced** — transient infra class; no defect split |
| 12 | Duplication/redundancy | **Advanced** — Plot vs Storyteller overlap clarified |
| 13 | Creative-freedom | **Gap** |
| 14 | Decision-value ranking | **Advanced** — Plot > Storyteller on immediate-turn |
| 15 | Clearly justified | **Premature** |
| 16 | Conditional components | **Advanced** — Storyteller → longitudinal gate |
| 17 | Insufficient justification | **Advanced** — synchronous Storyteller on one-turn evidence |
| 18 | Candidate simplifications | **Advanced** — Storyteller tiering; Plot mechanism TBD |
| 19 | A0–A4 comparison | **Advanced** — §9 |
| 20 | Risk/tradeoff | **Partial** |
| 21 | Expected latency ranges | **Partial** — outlier documented |
| 22 | Validation strategy | **Advanced** — blind factorial proven twice |
| 23 | Remediation program | **Not authorized** |

---

## 15. Artifact disposition / commit SHAs

| Artifact | Disposition |
|----------|-------------|
| Stage-3 harness + helper | Committed `42be339` |
| Stage-3 execution record | Committed `42be339` |
| Locked Stage-3 scores + this synthesis | **Pending commit** (this step) |
| Gitignored Stage-3 run outputs | Retained locally |
| D-01-L harness | **Not created** — proposal only |

---

## 16. Governance decisions required

1. **Accept Stage-3 decode** — locked matrix, marginals, Plot/Storyteller provisional classifications?
2. **Authorize D-01-L longitudinal tranche** — Storyteller ON vs OFF with Plot ON; 5-turn Arkham + 3-turn Ayame; fixed scripts?
3. **Accept reliability classification** — transient infra; no separate remediation Issue?
4. **Defer D-10** until after D-01-L gate?
5. **Defer EXP-3 complexity contrast** — unchanged?
6. **Export Governance per-dimension Stage-3 matrix** to durable repo (optional)?
7. **Update #201 Issue body** with Stage-3 decode synthesis SHA?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** Stage-3 decode recorded; longitudinal Storyteller proposal prepared; locked scores durably stored  
**Not executed:** D-01-L, D-10, production tiering, Packages E–G synthesis
