# Issue #201 — Architecture Direction Record & Long-Horizon Validation Design

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Canonical state:** `consensus_reached` (unchanged during this proposal)  
**Project:** In Progress / P1  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  
**Phase:** Post-synthesis architectural decision recording + long-horizon validation **design only**  
**Prior synthesis:** `issue-201-final-architecture-synthesis-proposal-2026-09-15.md` (`b6d9085`)

**Authorization boundaries:**

| Action | Status |
|--------|--------|
| Record architecture direction | **Authorized** |
| Design long-horizon validation program | **Authorized** |
| Production A2 migration | **NOT authorized** |
| Long-horizon harness implementation | **NOT authorized** |
| Live long-horizon execution | **NOT authorized** |
| Successor Issue creation | **Proposal only** — not created in this step |

---

# Part A — Governance Decisions (Durable Record)

## Decision 1 — Intended architecture direction

**Recorded:**

> **A4 → A2 is the intended architectural migration direction**, contingent on supplementing the completed short/medium-horizon #201 evidence with the reserved long-horizon persistent-narrative-cognition evidence **before production migration begins**.

Current #201 evidence already establishes that A4's large always-on synchronous cognition topology is **not** the desired target architecture.

The remaining long-horizon work is **not** a rerun of the A2-vs-A4 question. It is intended primarily to determine the correct **persistent narrative cognition topology inside the A2 direction** and to ensure that short-horizon simplification has not removed capabilities whose value emerges only as an RP ages.

**Evidence basis:** G3-B/C/E (A2 ≥ lean A4 on blind quality at lower cost); Package D ablations (always-on stack not justified); final synthesis `b6d9085`.

---

## Decision 2 — Pruning versus redesign

**Recorded:**

> **A2 is the target architecture.** Existing A4 components survive, migrate, or are reused where they satisfy the accepted A2 responsibilities and contracts. Components do not survive merely because they already exist.

Architectural redesign and implementation reuse/pruning are expected to **converge**, not present as a false binary:

- prune A4; **OR**
- rewrite A2 from scratch.

**Implication:** Migration is selective reuse under A2 contracts (Continuity, PVR, Host validation, tiered orchestration), not wholesale retention of A4 topology.

---

## Decision 3 — Persistent narrative cognition remains unresolved

**Recorded:**

Short-horizon evidence is **insufficient** to determine the final disposition or topology of persistent narrative cognition.

| Fact | Implication |
|------|-------------|
| Four-turn G3-D is not long horizon | Cannot adjudicate aged-story value |
| G3-D had zero Plot projection/consumption (L2–L4 = 0) | Did not test consumed Plot value |
| Stage-3 Plot ON +0.239 immediate-turn marginal | Some immediate-turn Plot function evidenced |
| Storyteller poor on sync/short critical path (D-01-L, D-10) | Mechanism rejected, not responsibility settled |
| SEQ-G (5.00, Plot OFF, 4 turns) | Primary RP + Continuity can excel short-horizon |

**Therefore:** Plot/Scribe **and** Storyteller long-term responsibilities require explicit long-horizon evaluation before final architectural responsibilities are settled.

---

## Decision 4 — Storyteller must be included

**Recorded:**

The long-horizon program **must include Storyteller responsibilities as a first-class experimental subject**.

**Governance hypothesis to test (not assume):**

> Responsibilities currently distributed among Director, Storyteller, and Plot/Scribe may ultimately be better represented by a consolidated persistent narrative-intelligence responsibility/agent.

This is **not** the predetermined outcome. The experiment must permit evidence to support:

- separation;
- consolidation;
- partial consolidation;
- removal/reassignment.

---

## Conceptual distinction (carried forward)

| Capability | Question |
|------------|----------|
| **Immediate/local RP competence** | Can Primary RP maintain a coherent, compelling scene over the recent-context horizon? |
| **Persistent narrative cognition** | Can the architecture maintain and productively use story information whose value emerges only after substantial story aging? |

The long-horizon program exists primarily to test the **second** capability.

---

# Part B — Historical Responsibility Map

*Responsibility ≠ current mechanism. Sources: `llm-call-catalog.mjs`, `PACKET_CONTRACTS.md`, `architecture-overview.md`, G2 spec §11–14, Package D decode records.*

## Director

| Responsibility | Authority | Historical mechanism | #201 disposition |
|----------------|-----------|---------------------|------------------|
| Deterministic actor eligibility | Host/orchestration | Participation policy | **Retain** (deterministic) |
| Turn / actor selection among eligible NPCs | Director logical role | `director_turn` LLM | **Retain** (conditional LLM) |
| Narrative priority / spotlight when ambiguous | Director | `director_turn` | **Retain** (conditional) |
| Conflict arbitration (who yields) | Director | `director_turn` | **Conditional** |
| Immediate orchestration (not long-term planning) | Director | Sync round path | **Retain** — distinct from persistent narrative agent |
| Semantic QA on Director output | — | `director_semantic_qa` | **Do not rebuild** (D-06) |
| Long-horizon trajectory / unresolved-thread registry | — | Partially assumed by Director in A4 | **Reassign candidate** → persistent narrative cognition |

**Long-horizon test relevance:** immediate actor-selection only. Do **not** attribute aged-story outcomes to Director unless arm design explicitly assigns persistent planning to Director.

---

## Storyteller (historical mechanisms)

### Preamble (orientation + assessment)

| Responsibility | Historical mechanism | #201 short-horizon finding |
|----------------|---------------------|---------------------------|
| Round orientation / scene framing | `storyteller_orientation` | **Sync path rejected** (D-01-L) |
| Informed assessment / advisory package | `storyteller_assessment` + Librarian bundle | **Sync path rejected**; weak +0.079 marginal (Stage-3) |
| Live Director/Character injection (Model A) | S3c `bind_storyteller_advisory_package` | Invalidated on commit; not Narrator consumer |

### Post-commit

| Responsibility | Historical mechanism | #201 short-horizon finding |
|----------------|---------------------|---------------------------|
| Issue-tension pressure overlays | `storyteller_post_commit_issue_pressure` | **Sync LLM rejected** (D-10); durable-pressure causal gap |
| ACTIVE/ESCALATING issue assessment | Eligibility-gated post-commit | Function maps to Plot overlay + Continuity derived pressure |

### Intended long-horizon responsibilities (not settled)

| Responsibility | Evidence it may matter aged | Short-horizon status |
|----------------|----------------------------|----------------------|
| Unresolved narrative pressure tracking | `architecture-overview.md` §S4; Stage-3 Ayame ST interaction | Underpowered at 1 turn |
| Agenda persistence across turns | Stage-3 ST Ayame −0.225 when removed with Plot ON | Suggestive only |
| Escalation / trajectory hints | Storyteller advisory charter | Not tested aged |
| Narrative memory compression / salience | Overlaps retrieval + Plot | Mechanism open |
| NPC relationship / tension evolution advisory | Issue #164 lineage | Not tested aged |

---

## Plot / Scribe

| Responsibility | Historical mechanism | #201 finding |
|----------------|---------------------|--------------|
| Session/scene plot init | `plot_cognition_init` | Stage-3 Plot ON +0.239; G3-D init executed |
| Plot overlay update | `plot_cognition_update` | G3-D: 12 inferences; 10 persisted |
| Unresolved pressures / goals / trajectory | Plot overlay sidecar | G2 §13 retained function |
| Delayed consequence **proposals** | Plot output → Host review | Not tested consequentially |
| Scene-transition recommendations | Plot advisory | Not tested aged |
| Character advisory projection | `plot_cognition_epistemic_eval`, `character_advisory_generation` | Support chain; consolidate |
| **Consumption by Primary RP** | `plot_cognition_finalized_projection` → Character/Director lanes | **G3-D: L2–L4 = 0** (topology gap) |

**Critical seam:** generation and persistence occurred; **projection and consumption did not** in executed G3-D A2 path (`projectionLifecycleEnabled: false`).

---

## Continuity / retrieval support

| Responsibility | Mechanism | Role in aged stories |
|----------------|-----------|---------------------|
| Authoritative committed state | Continuity Host | **Necessary** — all arms |
| Scene-pressure freshness projection | `continuity_scene_pressure_projection.py` | Deterministic; high correctness value (#200) |
| Issue-pressure semantic overlays | `issue_pressure_semantic_overlays` | Derived; overlaps Storyteller/Plot function |
| Durable `rp_history` / transcript | Continuity + perception filter | Primary RP recent-context substrate |
| Retrieval / indexing / bounded projection | Domain + harness forensics | G3-E: necessary; K6 projection seam |
| Relationship / world-state summaries | Derived state (bounded) | Baseline for all arms |

---

# Part C — Long-Horizon Persistent Narrative Cognition Experimental Design Proposal

## 1. Activation / state / weights / bootstrap

See header. Design-only phase.

---

## 2. Durable recording of four Governance decisions

Recorded in **Part A** above. This document is the durable authority.

---

## 3. Historical responsibility map

See **Part B**.

---

## 4. Responsibility-overlap analysis

| Responsibility | Director | Storyteller (intent) | Plot/Scribe | Continuity/retrieval | Primary RP |
|----------------|:--------:|:--------------------:|:-----------:|:--------------------:|:----------:|
| Immediate actor selection | **primary** | — | advisory hint only | eligibility | — |
| Unresolved-thread registry | — | **overlap** | **overlap** | derived pressures | transcript-only |
| Long-horizon trajectory | — | **overlap** | **overlap** | — | — |
| Agenda / motivation persistence | — | **overlap** | **overlap** | character state | move history |
| Delayed consequences | — | partial (issue pressure) | **overlap** | consequence queue | — |
| Setup / payoff foreshadowing | — | **overlap** | **overlap** | — | local only |
| Narrative memory compression | — | **overlap** | **overlap** | retrieval summaries | context window |
| Relationship evolution advisory | — | **overlap** | partial | relationship state | portrayal |
| Tension / escalation management | — | **overlap** | **overlap** | scene pressures | beat-level |

**Overlap conclusion:** Storyteller and Plot/Scribe compete for the same **persistent narrative cognition** responsibility class. Director overlaps only at immediate orchestration. Consolidation hypothesis is **testable**, not assumed.

---

## 5. Hypotheses to test

| ID | Hypothesis |
|----|------------|
| **H0** | Primary RP + deterministic substrate + Continuity/retrieval suffice for high-quality aged RP without dedicated persistent narrative cognition. |
| **H1** | Plot/Scribe persistent cognition adds consequential aged-story value when a functioning consumption pathway exists. |
| **H2** | Storyteller-class persistent narrative responsibilities add consequential aged-story value when implemented off the rejected sync critical path. |
| **H3** | A consolidated persistent narrative-intelligence agent outperforms separate Plot + Storyteller responsibilities on quality-per-cost at long horizon. |
| **H4** | Persistent cognition value emerges only after a minimum story-age threshold (checkpoint divergence). |
| **H5** | Persistent cognition cost per consequential contribution remains justified at full horizon. |

---

## 6. Proposed experimental arms

| Arm | Label | Description |
|-----|-------|-------------|
| **LH-A** | `a2_primary_only` | Primary RP + deterministic substrate + Continuity/retrieval; **no** dedicated persistent narrative cognition LLM |
| **LH-B** | `a2_plot_scribe` | LH-A + async Plot/Scribe with **mandatory** generation → persistence → projection → consumption pathway |
| **LH-C** | `a2_storyteller_persistent` | LH-A + async Storyteller **responsibility implementation** (issue-pressure, agenda, trajectory, salience) — **not** sync preamble restoration |
| **LH-D** | `a2_narrative_intel_consolidated` | LH-A + single persistent narrative-intelligence agent owning appropriate Storyteller + Plot responsibilities; Director retains immediate selection only |

**Hard boundaries (all arms):** Character agency; entitlement/PVR; Continuity commit authority; Narrator rendering separation.

---

## 7. Staged arm design (preferred)

Four arms × full horizon × multiple scenarios × replication is prohibitively expensive. **Staged design recommended:**

| Stage | Purpose | Arms | Horizon |
|-------|---------|------|---------|
| **LH-0** | Consumption seam verification | B only (+ control trace on A) | 6-turn micro-sequence |
| **LH-1** | Screening + early divergence | A, B, C, D | **2 scenes, ~20–24 turns** |
| **LH-2** | Definitive aged-story test | Top 2 from LH-1 + mandatory A baseline | **3–4 scenes, ~45–60 turns** |

LH-0 is a **pre-execution gate**: LH-B/C/D cannot enter LH-1 until L2+ consumption is proven on the micro-fixture.

---

## 8. Proposed story-aging horizon(s) and rationale

| Horizon | Turns (indicative) | Scenes | What it exposes |
|---------|-------------------|--------|-----------------|
| **Micro (LH-0)** | 6 | 1 | Consumption pathway proof only |
| **Medium (LH-1)** | 20–24 | 2 + transition | Thread dormancy/resurface; scene-boundary memory; first cost/quality divergence |
| **Full (LH-2)** | 45–60 | 3–4 | Competing agendas; delayed consequences; foreshadow/payoff; context pressure; relationship drift |

**Rationale for not using 4 turns:** G3-D demonstrated that 4 turns fit in recent attention window — SEQ-G achieved 5.00 without Plot. Value that depends on information **leaving easy conversational attention** requires ≥15–20 turns minimum (medium horizon). Full horizon targets failures like forgotten promises, premature resolution, and contradiction under accumulated lore.

**Principled threshold hypothesis:** Checkpoint comparisons at turns **T8, T16, T24, T40, T56** (adjust per scenario pacing) to detect late-emerging divergence.

---

## 9. Scenario strategy

**Existing scenarios insufficient alone:**

| Scenario | Strength | Gap for long-horizon |
|----------|----------|---------------------|
| `ayame_household_entry_evaluation` | Controlled interview; SEQ-G thread persistence | Single-scene; low antagonism; needs multi-scene aging |
| `arkham_asylum_mess_hall_arena` | Multi-character; stress | 4-turn G3-D only; needs delayed consequences |

**Recommendation:** Purpose-built **long-horizon fixtures** (2 archetypes minimum):

1. **Controlled-pressure interview arc** (Ayame lineage) — promises, evasions, boundary tests across scenes/locations in the household.
2. **Antagonistic multi-character arena arc** (Arkham lineage) — competing agendas, social-knowledge traps, delayed consequences, non-redemption tone.

Each fixture embeds **scripted delayed obligations** (dormant threads, seeded facts, time-delayed consequences) without breaking RP credibility. Player branches remain real; obligations are **scenario-authored**, not memory-benchmark artificial.

---

## 10. Required delayed narrative obligations (per sequence)

Each long-horizon sequence must include at least:

| Obligation class | Example |
|------------------|---------|
| Dormant thread | Turn 3 question unanswered until Turn 18+ |
| Competing threads | Two NPC agendas that cannot both resolve early |
| Delayed consequence | Action Turn 10 → consequence Turn 35+ |
| Promise/commitment | Explicit character promise tested later |
| Foreshadow → payoff | Object/fact introduced early, decisive later |
| Relationship evolution | Trust/hostility shift across scenes |
| Old information resurface | Fact outside recent transcript window needed |
| Non-resolution pressure | Antagonism or tension that must not collapse early |
| Premature-resolution trap | Easy harmonic closure available but scenario-discouraged |
| Cross-scene continuity | Location/time transition without thread reset |

---

## 11. Consumption-path proof requirements

For every persistent-cognition arm (B, C, D), **mandatory forensic chain** per inference:

```
observation/input → generation → durable persistence → later projection
  → authorized consumer receipt → consumer use → decision influence → observable narrative consequence
```

| Level | Criterion | Credit for value? |
|-------|-----------|-------------------|
| L0 | Generated only | **No** |
| L1 | Persisted | **No** |
| L2 | Projected to authorized consumer package | **No** (necessary not sufficient) |
| L3 | Consumer references projected content in decision input | **Candidate** |
| L4 | Observable narrative consequence attributable to consumption | **Yes** |

**G3-D lesson:** LH-0 must fail-closed if any arm claims persistent value without L2+.

---

## 12. Knowledge / projection seam instrumentation

Extend G3-E K6 lesson. Per turn, log:

| Seam | Instrument |
|------|------------|
| Retrieval failure | eligible set vs required anchors |
| Entitlement failure | hard_access_rejected / forbidden manifest |
| Projection failure | required records absent from projected manifest |
| Consumer non-use | projected content not referenced in consumer input hash |
| Cognition failure | validation/repair events |

Attribute failures to seam class **before** blaming persistent narrative agent.

---

## 13. Blind quality rubric (overview)

Blind packet transport per #201 discipline. Sequence-level scoring (not single-beat). Governance scores locked before decode.

**Core dimensions (1–5):** character fidelity over time; relationship continuity/evolution; motivation consistency; responsiveness; initiative; coherence; prose quality; naturalness; unnecessary exposition.

---

## 14. Long-horizon-specific quality dimensions

| Dimension | Detects |
|-----------|---------|
| Unresolved-thread retention | Active obligations persist appropriately |
| Thread resurfacing quality | Dormant threads return naturally when relevant |
| Delayed consequence handling | Consequences arrive coherently, not forgotten |
| Setup/payoff quality | Foreshadowing pays off without contradiction |
| Narrative direction without forced resolution | Tension preserved per scenario tone |
| Forgotten-commitment avoidance | Promises/agendas not silently dropped |
| Premature-resolution avoidance | No inappropriate early closure |
| Repetitive/stagnant plotting avoidance | Progress without loop |
| Cross-scene coherence | Transitions do not reset narrative logic |
| Old-information integration | Aged facts used naturally when relevant |
| Surprise without contradiction | Revelations consistent with prior commits |
| Accumulated-world consistency | Lore/state remains coherent as volume grows |

**Anti-gaming rule:** Mentioning old facts is insufficient; resurfaced information must **matter** to the current story.

---

## 15. Dark-RP / non-resolution evaluation safeguards

Rubric instructions must state explicitly:

- Harmony, redemption, resolution, moral closure, and positive character development are **not** default superiority signals.
- Evaluate fidelity to **scenario-intended tone and trajectory**, including unresolved conflict, antagonism, harsh outcomes, manipulation, and worsening relationships when authored.
- Score **premature wholesome resolution** negatively when the scenario discourages it.
- Blind evaluators receive scenario **tone contract** (not arm identity).

---

## 16. Latency / cost metrics

Per sequence, capture:

| Metric | Purpose |
|--------|---------|
| Total inference count | Arm economics |
| Inference count by responsibility | Persistent vs Primary RP |
| Synchronous critical-path calls | Player-visible latency driver |
| Async/post-commit calls | Background cost |
| Input / output / reasoning tokens | Cumulative cost proxy |
| Wall time (operation + critical path) | Latency |
| Player-visible turn latency (p50/p95) | UX |
| Persistent-cognition cost per turn | Ongoing tax |
| Persistent-cognition cost per L4 consequential event | Value efficiency |
| Retrieval/projection volume | K6-class seam monitoring |
| Context growth vs turn index | Scaling pressure |

**Key economic question:**

> What additional long-horizon narrative value is purchased by each additional cognition responsibility, and at what cumulative latency/token cost?

---

## 17. Longitudinal checkpoint design

| Checkpoint | Approx turn | Analysis |
|------------|-------------|----------|
| C1 | 8 | Early competence — expect little arm divergence |
| C2 | 16 | Post-scene-1 — first resurface obligations |
| C3 | 24 | Medium horizon end — primary LH-1 comparison |
| C4 | 40 | Mid full horizon — aged-thread stress |
| C5 | 56 | Full horizon — definitive comparison |

At each checkpoint: rolling blind sub-scores on transcript slices + objective obligation trackers (automated: thread open/closed, promise ledger, consequence fired).

**Detectable pattern:** flat early → divergence after C2/C3 → persistent arm gains OR never justifies cost.

---

## 18. Replication strategy

| Parameter | Proposal |
|-----------|----------|
| LH-0 | 2 micro-sequences (verify seam) |
| LH-1 | 2 scenario archetypes × 4 arms × **2 reps** = **16 sequences** |
| LH-2 | 2 scenarios × **3 arms** (A + top 2) × **2 reps** = **12 sequences** |
| Player branch | Paired seeds where feasible (G3-D pattern) |
| Checkpoint scoring | All sequences at C1–C3; LH-2 also C4–C5 |
| Blind eval | Sequence-level packets batched by checkpoint slice + final |

**Total live sequences (if fully executed):** 16 + 12 = **28** (comparable to G3-E campaign scale) but **far more turns per sequence** (~20–60 vs 1).

---

## 19. Stopping / escalation rules

| Rule | Condition |
|------|-----------|
| **LH-0 fail-stop** | No L2+ consumption in Plot/Storyteller/consolidated arm → fix topology before LH-1 |
| **LH-1 eliminate** | Arm trails LH-A at C3 by >0.3 blind mean with no obligation-tracker advantage |
| **LH-1 escalate** | Arm within 0.15 of leader OR wins ≥2 obligation classes → LH-2 |
| **LH-2 early stop** | Mid-horizon arm shows contradiction explosion or entitlement failures — infrastructure not narrative |
| **Cost stop** | Arm requires >2× tokens of LH-A with zero L4 events by C3 → unlikely to justify at C5 |

---

## 20. Confounds and controls

| Confound | Control |
|----------|---------|
| Player branch divergence | Paired seeds; document branch points |
| Scenario tone | Two archetypes; tone contract per scenario |
| Director actor-selection variance | Log Director decisions; same eligibility rules all arms |
| Model nondeterminism | Fixed model config; rep variance reported |
| Context window growth | Track projection volume; entitlement parity |
| Consumption seam vs cognition | LH-0 gate; seam-class attribution |
| Evaluator tone bias | Dark-RP safeguards; blind transport |

---

## 21. Failure attribution model

```
Tier-1 infrastructure → entitlement/PVR/Tier-1 gate
Retrieval seam → eligible but not retrieved
Projection seam → retrieved but not projected (K6-class)
Consumption seam → projected but not in consumer input
Cognition seam → consumer failed to use available state
Narrative-quality seam → used but poor integration
```

Only **narrative-quality** failures count against persistent-agent architecture hypotheses.

---

## 22. Criteria supporting each outcome

| Outcome | Support criteria |
|---------|------------------|
| **No dedicated persistent agent** | LH-A matches/exceeds all arms at C3 and C5; obligation trackers parity; lower cost |
| **Plot/Scribe** | LH-B shows ≥0.20 blind lift at C4/C5; ≥N L4 events; obligation wins on delayed payoff |
| **Storyteller persistent** | LH-C shows lift on agenda/tension dimensions; L4 on issue-pressure-class obligations |
| **Consolidated narrative intel** | LH-D beats B and C on quality-per-cost at C5 |
| **Partial consolidation** | B wins some dimensions; C wins others; D does not dominate — assign split responsibilities |

---

## 23. Criteria falsifying / revising each hypothesis

| Hypothesis | Falsified / revised if |
|------------|------------------------|
| H0 | Any persistent arm wins decisively at C5 with L4 proof |
| H1 | LH-B never achieves L2+ or loses to LH-A at C5 despite consumption |
| H2 | LH-C shows no lift on Storyteller-class obligations aged |
| H3 | LH-D worse than best separate arm on quality-per-cost |
| H4 | All arms diverge at C1 (horizon too short) or none by C5 (horizon insufficient) |
| H5 | Persistent arm L4 cost/turn exceeds agreed budget with no blind lift |

---

## 24. Estimated experiment scale

| Stage | Sequences | Turns (approx) | Inferences (order of magnitude) |
|-------|-----------|----------------|--------------------------------|
| LH-0 | 2 | 12 | 50–150 (seam proof) |
| LH-1 | 16 | 320–384 | 3,000–8,000 |
| LH-2 | 12 | 540–720 | 5,000–15,000 |

**Derivation:** G3-D averaged ~10–16 LLM calls/turn with Plot ON; G3-B A2 simple beat ~2–3 sync/turn. Long-horizon A2 baseline estimate ~4–8 inferences/turn sync + async persistent arm overhead 1–3/turn. Full program is **~10–20× G3-E wall time** if naively executed — staging essential.

---

## 25. Required harness / instrumentation changes (design only)

1. **Consumption lifecycle enforcer** — projection must reach Character/Director packages; fail-closed audit if disabled.
2. **L0–L4 persistent cognition tracer** — per-inference transport record (extends G3-D causal trace).
3. **Obligation ledger** — scenario-authored delayed obligations with automated open/closed/satisfied states.
4. **Checkpoint slice exporter** — blind packets per checkpoint without arm identity.
5. **Seam-class failure classifier** — retrieval/projection/consumption/cognition.
6. **Long-horizon scenario fixture format** — multi-scene templates with transition hooks.
7. **Async persistent cognition scheduler** — post-commit + scene-boundary triggers (not sync preamble).
8. **Storyteller persistent arm adapter** — implements responsibilities without D-01-L/D-10 sync paths.
9. **Consolidated narrative-intel arm adapter** — single agent interface for LH-D.
10. **Cost accounting parity** — same metrics as G3-E `arm_accounting`.

---

## 26. Pre-execution seam-verification requirements

Before LH-1 authorization:

- [ ] LH-0 completes with **L2+ demonstrated** on LH-B micro-fixture
- [ ] Consumer receipt logged in execution evidence
- [ ] At least one **L4 synthetic obligation** satisfied in micro-fixture
- [ ] Projection seam tests pass for multi-record anchors (K6-aware, not K6-repaired)
- [ ] Blind packet generator validated on checkpoint slices
- [ ] Governance approves scenario tone contracts

---

## 27. Issue #201 lifecycle recommendation

| Option | Recommendation |
|--------|----------------|
| Keep #201 open indefinitely | **No** |
| Close #201 now | **No** — record decisions first |
| **Recommended** | Transition #201 to **`implemented`** (assessment + architecture direction complete) after Governance accepts this record + final synthesis; link successor Issue for long-horizon program |
| Alternative | Keep `consensus_reached` until successor Issue filed, then close #201 with explicit handoff comment |

**Rationale:** #201 assessment acceptance criteria are met (Packages A–D, G1–G3 complete). Long-horizon validation is a **distinct validation program**, not incomplete #201 assessment. Clean chain-of-custody: #201 = architecture assessment; successor = persistent narrative cognition validation.

**Production migration:** remains blocked until long-horizon evidence supplements short/medium-horizon conclusions (Decision 1).

---

## 28. Proposed successor Issue / workstream structure (not created)

| Proposed item | Scope |
|---------------|-------|
| **Issue: Long-horizon persistent narrative cognition validation** | LH-0 through LH-2 program; owns harness design + execution authority |
| **Issue: A2 production migration planning** | Parallel track; blocked on LH completion per Decision 1 |
| **Issue: K6 bounded projection redesign** | Orthogonal seam debt; may share instrumentation |

Link all successors from #201 closure/handoff comment. Do not fold into #201 body.

---

## 29. Documentation impact

On Governance acceptance:

- Add long-horizon reservation + program outline to `docs/architecture.md`
- Cross-link from `issue-201-final-architecture-synthesis-proposal-2026-09-15.md`
- Update Issue #201 body with Decision 1–4 summary and successor link
- Do not update production runtime docs until migration Issue authorized

---

## 30. Governance decisions required before implementation

1. **Accept** Decisions 1–4 as recorded in Part A.
2. **Accept or amend** this long-horizon experimental design.
3. **Authorize LH-0 seam verification** (implementation of micro-fixture harness only) — separate action.
4. **File successor Issue(s)** per §28 — separate action.
5. **Decide #201 lifecycle transition** (`consensus_reached` → `implemented` vs remain open until successor filed).
6. **Do not authorize** production A4→A2 migration until long-horizon evidence supplements short/medium-horizon record.
7. **Do not predetermine** Storyteller fate or consolidation outcome.

---

**STOP.** Design proposal only. No harness implementation. No live runs. No production migration.
