# Issue #201 — Package D Post-D-01-L Value-of-Information & Scribe/Plot/Storyteller Lineage Reassessment

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**D-01-L decode anchor:** `5d15936`  
**Prior records:** D-01-L execution (`f5e1246`), primary decode (`5d15936`), Stage-3 decode (`da70fc7`)

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-01-L | **Complete** — verdict recorded |
| Secondary D-01-L per-turn eval | **Not authorized / intentionally omitted** |
| D-10 | Candidate — **reassessed; not executed** |
| EXP-3 | Candidate — **reassessed; not executed** |
| New live experiments | **NOT authorized this step** |
| Production redesign | **NOT authorized** |

---

## 2. Durable D-01-L verdict SHA

| Artifact | SHA |
|----------|-----|
| Locked primary scores + decode | `5d15936` |
| This reassessment record | *this commit* |

---

## 3. Accepted D-01-L Governance verdict

> **Synchronous preamble Storyteller cognition has not demonstrated sufficient marginal value to justify its current unconditional every-turn critical-path placement.**

**Scope:** synchronous Storyteller preamble path only.

**Does NOT establish:** global Storyteller worthlessness. Post-commit Storyteller remains a separate architectural question.

### Evidence summary

| Metric | Control (ST preamble ON) | Ablated (ST preamble OFF) |
|--------|-------------------------:|--------------------------:|
| Primary longitudinal mean | 4.575 | 4.525 |
| Δ control − ablated | **+0.05** | (within ≤0.15 comparability band) |
| ST preamble inferences | 32 | 0 |
| ST post-commit inferences | 18 | 20 |
| Plot inferences | 32 | 35 |
| Summed wall time (min) | 61.3 | 49.3 (~19.6% lower ablated; architectural cost evidence only) |
| Correctness | 4/4 committed, 0 issues | 4/4 committed, 0 issues |

**Scenario split (not established complexity-conditioned Storyteller benefit):**

| Scenario | Control | Ablated | Δ |
|----------|--------:|--------:|--:|
| Arkham | 4.400 | 4.650 | −0.25 |
| Ayame | 4.750 | 4.400 | +0.35 |

Blind top sequence: **SEQ-H** (5.00, Arkham, ST preamble OFF).

**D-01-L disposition:** experimental objective **complete** within #201.

---

## 4. User-provided Scribe/Storyteller historical clarification (authoritative intent)

The user states:

1. **Plot cognition** derives from integrating core concepts of an earlier **Scribe/Scribal bot**.
2. The user originally expected those Scribe concepts to become part of **Storyteller**.
3. On reflection, **Plot cognition is essentially performing the responsibility Storyteller was originally intended to perform**.

**Treatment:** authoritative **design-intent/history** evidence. Implementation lineage must still be verified against repository records.

---

## 5. Repository-supported Scribe lineage

| Finding | Evidence |
|---------|----------|
| **"Scribe" / "Scribal" named in repo** | **No matches** in `v2/`, `docs/`, `governance/`, `GLOSSARY.md`, `MODULE_INDEX.md`, or governance records |
| Documented Plot parent program | Issue **#48** — **Storyteller persistent narrative cognition** (`docs/plot-cognition-overlay-contract.md`) |
| Plot overlay framing | "bounded, persistent, cross-commit representation of Storyteller's evolving **advisory** understanding of where the RP could productively go" |
| Plot init provenance | `creation_provenance.source = storyteller` for normal init (`docs/plot-cognition-initialization-contract.md`) |
| Authority flow (canonical) | Storyteller proposes (overlay + Model A) → roles decide → Continuity establishes truth → Storyteller adapts plot cognition |

**Reconciliation with user clarification:**

- Repo canon frames Plot as an **extension of Storyteller's persistent narrative function** (#48), not a separately named Scribe subsystem.
- User's Scribe→Plot integration claim is **consistent with** Plot occupying the **persistent narrative-planning** niche Storyteller was meant to grow into.
- Repo does **not** document a distinct Scribe component surviving alongside Plot; the evolutionary story is **conceptual** (user history) mapped onto **Storyteller→Plot overlay** (repo canon).
- **Synchronous preamble Model A** (`StorytellerAdvisoryPackage`) appears to be a **parallel round-local mechanism** that persisted while Plot overlay absorbed cross-commit planning.

---

## 6. Original / intended Storyteller responsibility (repo evidence)

From `docs/architecture.md`, `governance/sources/architecture-overview.md`, `PACKET_CONTRACTS.md`:

| Responsibility | Intended? | Mechanism |
|----------------|:---------:|-----------|
| Plot threads / unresolved threads | Yes | Model A `unresolved_threads`; post-commit issue overlays |
| Narrative pressures / tensions | Yes | Model A `active_tensions`; post-commit `issue_tension_pressure` |
| Progression opportunities | Yes | Model A lanes |
| Agenda / pacing / scene direction | Advisory | `narrative_priorities`; Director retains selection authority |
| Delayed consequences | Indirect | Via influenced commits + durable overlays |
| Persistent cross-commit plot state | **Delegated to Plot overlay (#48)** | Not Model A (round-local, invalidated on commit) |
| Authoritative world truth | **No** | Continuity only |
| Turn selection | **No** | Director |
| Character intent / dialogue | **No** | Character |

**Original charter:** bounded **advisory narrative cognition** — orientation → Librarian bundle → assessment → packaging → suggestive Director/Character lanes.

---

## 7. Current Plot cognition responsibility

| Aspect | Detail |
|--------|--------|
| **Purpose** | Persistent advisory overlay: PlotGoal, UnresolvedNarrativePressure, GlobalPlotFrame |
| **Lifetime** | Cross-commit; session-scoped `plot_cognition_scope_id` |
| **Inputs** | Committed continuity, scenario premise, operative overlay, pending-work plans |
| **Outputs** | Updated overlay; Director/Character projections (epistemically gated for Character) |
| **Inference kinds** | `plot_cognition_init`, `plot_cognition_update`, `plot_cognition_epistemic_eval`, `character_advisory_generation` |
| **When** | Round-start pending work; conditional pre-Character; post-commit lifecycle (joined) |
| **Authority** | Non-authoritative; pointers to Continuity, not copies |
| **Consumers** | Director (overlay projection + Model A material); Character (gated advisory); may inform Model A orientation/assessment |

**Empirical classification (Stage 3 + D-01-L):** **retain function** — largest quality contributor when removed (−0.272 D-01a vs D0 immediate; +0.239 Plot marginal descriptive).

---

## 8. Current Storyteller preamble responsibility

| Aspect | Detail |
|--------|--------|
| **Purpose** | Round-local Model A advisory per turn |
| **Inference kinds** | `storyteller_orientation`, `librarian_mediation` (ST lane), `storyteller_assessment` |
| **Product** | `StorytellerAdvisoryPackage` on `RoundFixture` |
| **Lifetime** | **Invalidated on commit** — regenerated each round |
| **Consumers** | Director, Character (Narrator mapper exists but not live in S3c) |
| **Gated by** | `skipStorytellerCognition` |
| **Plot relationship** | Indirect — both read committed history; overlay may inform orientation/assessment |

**Empirical classification:** **strong remove/consolidate/relocate candidate** for synchronous critical path (D-01-L verdict).

---

## 9. Current Storyteller post-commit responsibility

| Aspect | Detail |
|--------|--------|
| **Purpose** | Assess ACTIVE/ESCALATING issues after Character commit |
| **Inference kind** | `storyteller_post_commit_issue_pressure` |
| **Product** | `LibrarianSemanticProposal` kind `issue_tension_pressure` |
| **Persistence** | `ContinuityManager.issue_pressure_semantic_overlays` → joined into `scene_pressures` |
| **Gated by** | **NOT** `skipStorytellerCognition` |
| **Consumers** | Director + Character via `scene_pressures` digest on **subsequent** rounds |
| **Distinct from Plot** | Issue-linked semantic overlays vs strategic overlay categories |

**Empirical classification:** **unresolved / potentially retained function** — not tested by D-01-L preamble ablation (retained on both arms).

---

## 10. Responsibility-overlap matrix

Legend: **A**=authoritative, **P**=primary cognition, **Adv**=advisory, **D**=derived projection, **C**=consumer only, **—**=absent

| Responsibility | Plot overlay | ST preamble | ST post-commit | Continuity | Director |
|----------------|:------------:|:-----------:|:--------------:|:----------:|:--------:|
| Identify active story threads | P/Adv | Adv | — | A (issues/events) | C |
| Maintain thread persistence | P | Adv (same-turn) | — | A | C |
| Create narrative pressure | P (`UnresolvedNarrativePressure`) | Adv (`active_tensions`) | P (`issue_tension_pressure`) | D (overlays) | C |
| Update narrative pressure | P | Adv (regenerated/turn) | P (per commit) | A/D | C |
| Detect opportunities | P (`PlotGoal`) | Adv | — | — | C |
| Reason about escalation | P/Adv | Adv | Adv (issue eligibility) | A (issue state) | C |
| Preserve unresolved tensions | P | Adv | Adv | A | C |
| Agenda progression | P/Adv | Adv | — | — | P (selection) |
| Delayed consequences | Adv (via commits) | Adv (via commits) | Adv (via overlays) | A | C |
| Scene momentum | Adv | Adv | — | — | P |
| Narrative prioritization | P (`GlobalPlotFrame`) | Adv | — | — | C |
| Advise Character | P (gated projection) | Adv | — | — | Adv |
| Advise Director | P + Adv packaging | Adv | — | — | — |
| Advise Narrator | — | Adv (mapper only) | — | — | — |
| Mutate durable story state | — | — | D (via Continuity accept) | A | — |
| Consume durable story state | C | C | C | — | C |
| Decide next actor | — | — | — | — | **P** |
| Decide next story development | Adv | Adv | Adv | — | P |

**Highlighted duplication (genuine overlap, not merely complementary):**

1. **Narrative pressure reasoning:** Plot `UnresolvedNarrativePressure` vs ST preamble `active_tensions` vs ST post-commit `issue_tension_pressure` → same semantic territory, different stores and lifetimes.
2. **Thread/tension persistence:** Plot overlay (cross-commit) vs preamble regeneration (per-turn re-inference) vs post-commit overlays (issue-scoped durable).
3. **Director/Character advisory packaging:** Plot projection + Model A lanes may convey overlapping guidance from the same committed facts.

---

## 11. Information-flow comparison

### Plot path

```text
Committed continuity + scenario + operative overlay
  → plot_cognition_init / update / epistemic_eval (conditional)
  → PlotGoal | UnresolvedNarrativePressure | GlobalPlotFrame (session-persistent overlay)
  → project_director_overlay / Character advisory projection
  → Director decision | Character move
```

**Unique information (when fresh):** strategic cross-commit plot frame, goals, ensemble pressures with grounding refs.

### Storyteller preamble path

```text
Committed continuity + bundle + (optional overlay inform)
  → orientation → librarian_mediation → assessment
  → StorytellerAdvisoryPackage (round-local)
  → packaging → storyteller_* suggestive lanes
  → Director / Character (same turn)
  → invalidated on commit
```

**Unique information (claimed):** fresh round-local synthesis of tensions/threads/opportunities. **Empirically:** marginal longitudinal value (+0.05) with Plot retained; Arkham favored ablation.

### Storyteller post-commit path

```text
Character commit + ACTIVE/ESCALATING issues
  → storyteller_post_commit_issue_pressure
  → issue_tension_pressure proposal
  → Continuity.issue_pressure_semantic_overlays
  → scene_pressures digest (future rounds)
  → Director / Character
```

**Unique information (claimed):** issue-scoped semantic unmet conditions and stakes summaries bound to authoritative issue refs.

### Duplication findings

| Pattern | Location |
|---------|----------|
| Repeated reading of committed history | Plot update + ST orientation + ST post-commit (independent inferences) |
| Duplicate pressure semantics | Plot `UnresolvedNarrativePressure` vs `issue_tension_pressure` overlays |
| Transform without new decision | Preamble regeneration of tensions Plot overlay may already hold |
| Plot without ST preamble | **Viable** — D-01-L + Stage 3 evidence |
| ST preamble without Plot | **Degrades quality** — D-01a −0.272 vs D0 |

---

## 12. Genuine duplication vs complementary function

| Relationship | Verdict |
|--------------|---------|
| Plot vs ST preamble | **Substantial overlap** in narrative-planning territory; **asymmetric substitutability** (Plot carries load without preamble; reverse not true) |
| Plot vs ST post-commit | **Partial overlap** on pressure semantics; **different persistence surfaces** (overlay categories vs issue overlays) — complementarity **unresolved** |
| ST preamble vs ST post-commit | **Complementary lifetimes** (same-turn vs post-commit durable) but **same Storyteller family** reasoning about narrative pressure |
| Continuity vs advisory layers | **Complementary** — authoritative vs derived (not duplicate) |
| Director vs advisory | **Complementary** — selection authority vs suggestive input |

---

## 13. Asymmetric-ablation interpretation

| Removal | Plot ON? | ST post-commit? | Quality signal |
|---------|:--------:|:---------------:|----------------|
| D-01a: Plot OFF, ST preamble ON | OFF | ON | −0.272 vs D0 (meaningful degradation) |
| D-01b: ST preamble OFF, Plot ON | ON | ON | −0.113 vs D0 (modest) |
| D-01-L: ST preamble OFF, Plot ON (longitudinal) | ON | ON | +0.05 vs control (negligible); Arkham favors ablation |

**Hypothesis (not architectural fact):**

> Plot appears able to carry much of the narrative-cognition responsibility without Storyteller preamble, while Storyteller preamble does not appear able to carry the same responsibility without Plot.

**Partial yes to consolidation question:** Plot is the **stronger implemented carrier** of persistent narrative cognition; preamble Model A looks like **legacy parallel machinery** in overlapping territory.

---

## 14. Updated component classifications

| Component | Classification | Rationale |
|-----------|----------------|-----------|
| **Plot cognition** | **Retain function** | Strongest ablation signal; persistent overlay; cross-commit value |
| **ST preamble (sync)** | **Remove / consolidate / relocate** | D-01-L verdict; cost without demonstrated marginal value |
| **ST post-commit** | **Unresolved — experiment or synthesis** | Retained in D-01-L; overlap with Plot pressures untested |
| **Continuity** | **Retain (authoritative)** | Non-negotiable state authority |
| **Director** | **Retain function**; D-06 QA **combine/remove candidate** | Selection authority essential |
| **Character orientation (EXP-3/D-03)** | **Conditional retain / tier candidate** | Stage-2 topology evidence; lower priority than Plot/ST overlap |
| **Librarian/KAR** | **Retain function**; mediation cost unresolved | Supports multiple cognitions |
| **PVR/perception** | **Retain** | Correctness foundation |
| **Narrator env cognition** | **Unresolved (D-04)** | Not experimentally characterized |
| **Structural validators / semantic QA** | **Partially tested (D-06)** | Combine candidate for Director QA |

---

## 15. D-10 value-of-information reassessment

**D-10 hook:** `skipLibrarianProposalGeneration` — disables post-commit `storyteller_post_commit_issue_pressure` path.

### Lineage-driven causal question (recommended framing)

> **Does post-commit Storyteller issue-pressure generation produce unique durable narrative-state contribution that Plot overlay cognition does not already provide or cannot naturally own?**

### Current evidence assessment

| Question | Evidence |
|----------|----------|
| What does post-commit add? | `semantic_unmet_condition`, `stakes_summary` per issue → `scene_pressures` |
| Relation to Plot state? | Plot has `UnresolvedNarrativePressure`; both advisory, different schemas/stores |
| Does Plot already reason over equivalent pressures? | **Yes, partially** — overlay pressures are strategic; issue overlays are issue-bound |
| Unique creator Plot consumes? | **Unclear** — both feed Director/Character pressure digests independently |
| Independent duplicate inference? | **Plausible** — separate LLM paths reading similar committed facts |
| Complementary or duplicate? | **Unresolved — D-10 directly tests this** |
| Removing tests unresolved responsibility? | **Yes** — only experiment targeting post-commit ST with Plot ON |

### D-10 expected information gain: **HIGH**

| Factor | Rating |
|--------|--------|
| Material architecture impact | High — determines whether post-commit ST survives consolidation |
| Cost | Moderate — smaller than D-01-L (no multi-turn tranche required if single-turn design reused) |
| Confounds | Plot ON must be held; preamble should be OFF or ON per arm design (recommend: **preamble OFF** to isolate post-commit given D-01-L verdict) |
| Existing evidence sufficient? | **No** — D-01-L intentionally retained post-commit on both arms |

**Recommendation:** D-10 is now the **highest-value remaining live experiment** for Package D, elevated from "efficiency overlap" to **architectural discriminator** after lineage analysis.

**NOT authorized for execution in this step.**

---

## 16. EXP-3 value-of-information reassessment

**EXP-3 / D-03:** `skipCharacterKnowledgeCognition` — Character orientation bypass.

| Factor | Assessment |
|--------|------------|
| Current evidence | Stage-2 topology decomposition; orientation-mediated mediation cost |
| Architecture impact | Moderate for A2/A3/A4 **topology** distinction (compact vs full stack) |
| Relation to Plot/ST lineage | **Low** — does not resolve Scribe/Plot/Storyteller overlap |
| Priority vs D-10 | **Lower** after D-01-L + lineage reassessment |

**Recommendation:** **Defer to synthesis** unless Governance prioritizes topology compaction over narrative-cognition consolidation.

---

## 17. Other unresolved component questions

| Candidate | Evidence | Unresolved question | Could change architecture? | Recommendation |
|-----------|----------|---------------------|---------------------------|----------------|
| **D-06 Director QA** | EXP-2 combined/remove candidate | Does semantic QA add quality vs cost? | Moderate | Defer to synthesis (partial evidence) |
| **D-04 Narrator env** | None | Env cognition value? | Low-moderate | Defer |
| **D-05 Librarian @character** | None | Mediation bypass value? | Moderate | Defer |
| **D-02 Plot init skip** | Folded in D-01 | Subset already tested | Low | No further investigation |
| **D-07/D-08/D-09** | Not authorized | High blast radius / low priority | Variable | Defer |
| **Librarian/KAR fan-out** | Architectural counts only | Mediation necessity per consumer | Moderate | Defer to synthesis |
| **Player decomposition** | Not Package D focus | Preamble cost | Low | Defer |
| **Coordination edges** | Failure forensics | Runtime stability | Operational, not architectural | Monitor; not experiment |

---

## 18. Architectural cost/coordination assessment

| Signal | Implication |
|--------|-------------|
| Preamble removal −32 ST inferences / 8 seq | Nontrivial synchronous work eliminated without quality collapse |
| ~19.6% lower summed wall time (ablated) | Cost evidence; not clean causal latency estimate |
| Plot counts similar across arms | Plot not disabled — valid comparison |
| Post-commit ST parity (18 vs 20) | Remaining ST work is mostly post-commit, not preamble |
| Multiple parallel post-commit joins (Narrator + Plot + ST) | D-10 targets join surface; coordination tax remains architectural concern |
| `character_failure` on ablated Arkham attempts | Runtime confound class; not semantic |

---

## 19. A0–A4 evidence update

| Topology | Post-D-01-L + lineage update |
|----------|------------------------------|
| **A4 (current)** | Plot **retain**; ST preamble **relocate/remove candidate**; post-commit ST **unresolved**; demonstrated **duplication risk** between Plot overlay and ST mechanisms |
| **A3 (compact specialized)** | **Strengthened** for preamble ST removal; Plot + Continuity + Director core; fewer synchronous cognitions |
| **A2 (single supervisory narrative cognition)** | **Strengthened** — evidence suggests **one persistent narrative cognition** (Plot-like) plus round-local/advisory layers may be redundant; consolidation of Plot + useful ST functions into one subsystem is **plausible** |
| **A1 (monolith + structured state)** | Unchanged — integration defect class separate from cognition value |
| **A0 (monolithic RP)** | Still insufficient — boundaries and state machinery required |

**Consolidation hypothesis:** Plot + retained post-commit/issue-pressure functions could merge into a **single narrative-cognition subsystem** (name agnostic) without preserving current every-turn preamble Model A.

**Unresolved ranking changers:** D-10 result; whether post-commit overlays are duplicate of Plot pressures; EXP-3 only if topology compaction is prioritized.

---

## 20. Remaining assumption inventory (ranked by decision importance)

| Rank | Assumption | Basis if experimentation stops now |
|------|------------|-----------------------------------|
| 1 | Post-commit ST adds unique value Plot cannot replace | **Assumption** — D-01-L retained post-commit on both arms |
| 2 | Issue `issue_tension_pressure` overlays are not redundant with Plot `UnresolvedNarrativePressure` | **Assumption** — schema separation only |
| 3 | Preamble removal generalizes beyond 2 scenarios × 2 reps | **Partial evidence** — D-01-L bounded tranche |
| 4 | Arkham ablation advantage is not stochastic/branch confound | **Assumption** — n=2, branch divergence |
| 5 | Director semantic QA (D-06) is safely combinable | **Partial** — EXP-2 only |
| 6 | Character orientation (EXP-3) tiering is safe | **Partial** — topology only |
| 7 | Optimal Plot invocation frequency | **Assumption** — retain function, not schedule |
| 8 | Librarian mediation per cognition is necessary | **Assumption** |
| 9 | Narrator env cognition cost/value | **Assumption** — untested |
| 10 | Final consolidated subsystem naming/topology | **Design choice** — not empirical |

---

## 21. Recommended next direction: **A — D-10 next**

### Rationale

1. **D-01-L closed the preamble question** — verdict recorded; further preamble experimentation would not change the placement conclusion materially.
2. **Lineage investigation** shows Plot absorbed persistent narrative-planning; post-commit ST is the **largest remaining untested Storyteller mechanism** with pressure-semantics overlap.
3. **D-10 directly tests** whether post-commit issue-pressure generation is complementary or duplicate relative to Plot overlay.
4. **EXP-3** does not discriminate Plot/ST consolidation; it addresses Character orientation topology.
5. **Synthesis (D)** is viable for preamble/tiering recommendations now, but **would leave assumption #1 unresolved** — the highest-importance remaining architectural fork.

### Proposed D-10 design constraints (for Governance authorization only)

- Hold **Plot ON** on both arms.
- Recommend **ST preamble OFF** on both arms (given D-01-L verdict) to isolate post-commit pathway.
- Control: post-commit ST ON; Ablated: `skipLibrarianProposalGeneration`.
- Reuse bounded scenario/tranche discipline from Package D.

**Do NOT execute without Governance authorization.**

---

## 22. What remains unresolved under recommendation A

- Post-commit ST unique value vs Plot overlay
- Whether `scene_pressures` can be fed solely from Plot + authoritative Continuity
- Long-term topology: A2-like consolidation vs A3 compact multi-agent
- Character orientation (EXP-3), Director QA (D-06), Narrator env (D-04)
- Invocation frequency / conditional triggers for any retained narrative cognition
- Production implementation — **not authorized**

---

## 23. Artifact disposition, commit SHA, #201 state, Governance decision

| Artifact | Path | Disposition |
|----------|------|-------------|
| D-01-L locked scores | `governance/records/issue201-d01l-governance-blind-scores-locked.json` | Committed `5d15936` |
| D-01-L primary decode | `governance/records/issue-201-package-d-d01l-primary-decode-synthesis-2026-09-14.md` | Committed `5d15936` |
| **This reassessment** | `governance/records/issue-201-package-d-post-d01l-voi-lineage-reassessment-2026-09-14.md` | **This commit** |
| D-01-L execution record | Updated with verdict link | **This commit** |
| Raw evidence roots | `data/investigation_runs/issue201-package-d-d01l-*` | Gitignored per policy |

**Secondary D-01-L per-turn scoring:** Not required / intentionally omitted by Governance after primary decode. Not missing validation.

**#201 remains:** `investigating` — In Progress / Investigating / **P1**

### Exact Governance decisions required

1. **Accept D-01-L preamble verdict** as Package D finding (sync ST preamble: remove/consolidate/relocate candidate).
2. **Accept or amend** Scribe/Plot/Storyteller lineage synthesis and duplication findings.
3. **Authorize or decline D-10** with proposed isolation design (Plot ON, preamble OFF, post-commit ablation).
4. **Decline or defer** EXP-3, secondary per-turn D-01-L scoring, and any new tranche.
5. **Decide synthesis timing** — begin A0–A4 consolidation report after D-10 vs immediately for preamble/tiering only.
6. **Confirm no production remediation Issue** until synthesis and explicit authorization.

---

## Architectural-history principle (recorded)

> What capability would we deliberately build today?

- **Valuable function:** persistent narrative cognition (currently Plot overlay), authoritative continuity, director selection, perception correctness.
- **Historical component:** synchronous preamble Model A — weak empirical support for every-turn placement.
- **Current mechanism:** Plot + ST preamble + ST post-commit — **likely over-factored** relative to user design intent; consolidation toward Plot-like persistent cognition is **evidence-consistent**.

Separate **function** from **component name** from **implementation topology**. A future subsystem may inherit Plot + selective post-commit responsibilities without preserving "Storyteller" or "Plot" labels.
