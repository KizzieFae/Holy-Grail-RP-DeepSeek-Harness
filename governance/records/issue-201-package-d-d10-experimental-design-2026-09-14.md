# Issue #201 — D-10 Post-Commit Storyteller vs Plot Experimental Design & Causal-Isolation Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full` (assigned + effective)  
**Bootstrap profile:** Full  
**Status:** Design consensus — **execution NOT authorized**

**Evidence anchors:**

| Anchor | SHA / path |
|--------|------------|
| D-01-L locked/decode | `5d15936` |
| Post-D-01-L lineage/VOI | `6ba1459` |
| D-01-L execution record | `governance/records/issue-201-package-d-d01l-execution-2026-09-14.md` |
| Control substrate | `c751ea6` |

---

## 1. #201 activation / state

| Field | Value |
|-------|-------|
| Issue | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-01-L | **Complete** — verdict accepted |
| Lineage reassessment | **Accepted** (with Scribe qualification) |
| D-10 | **Selected** — design step only |
| D-10 execution | **NOT authorized** |
| EXP-3 / secondary D-01-L | Deferred / declined |
| Final synthesis | **Deferred until D-10 completes** |
| Production remediation | **NOT authorized** |

---

## 2. Assigned / effective weight and bootstrap

- **Assigned workflow weight:** `full`
- **Effective workflow weight:** `full`
- **Bootstrap profile:** Full
- This document is a full-weight experimental-design consensus gate.

---

## 3. Authoritative evidence anchors

See table above. D-01-L established preamble ST insufficient for every-turn critical-path placement. Post-commit ST remains the highest-importance untested Storyteller responsibility in the Plot/ST consolidation question.

---

## 4. Repository-supported Plot / Storyteller lineage (exact citations)

### User-provided history (authoritative intent, not repo terminology)

Scribe/Scribal concepts integrated into Plot; user expected them in Storyteller; user now recognizes Plot as performing Storyteller's intended narrative-planning responsibility.

**Preserved as user design-intent/history only.** No `Scribe` / `Scribal` string matches in repository.

### Repository-supported functional lineage

| Source | Exact wording |
|--------|---------------|
| `docs/plot-cognition-overlay-contract.md` L5–6 | **Parent program:** Issue **#48** — **Storyteller persistent narrative cognition** |
| Same, L16–17 | Plot Cognition Overlay is a **bounded, persistent, cross-commit** representation of **Storyteller's evolving advisory** understanding of where the RP could productively go |
| Same, L20–27 | Authority flow: Storyteller proposes (overlay + Model A) → roles decide → **Continuity establishes truth** → Storyteller adapts plot cognition |
| `docs/plot-cognition-initialization-contract.md` L7, L72 | Parent program Issue **#48**; normal init-generated cognition uses **`creation_provenance.source = storyteller`** |
| `docs/plot-cognition-initialization-contract.md` L17 | Initialization is **not** Model A behavior |

**Governance-accepted functional lineage:**

> Plot cognition is the persistent narrative-planning branch/evolution of the Storyteller concept, incorporating the design responsibility the user remembers bringing from Scribe, while older round-local Storyteller machinery (Model A preamble) remained alongside it.

---

## 5. Exact D-10 causal question

> **Once Plot is the persistent narrative-cognition system, does post-commit Storyteller independently create narrative-pressure information that materially improves subsequent RP, or is it a second producer of substantially the same narrative understanding?**

Equivalent:

> **Does post-commit Storyteller produce unique durable narrative-state value that Plot cognition does not already provide or cannot naturally own?**

D-10 is a **complementarity-vs-duplication** experiment, not merely an efficiency test.

---

## 6. Current post-commit Storyteller implementation path

```text
Character commit (domain_commit_id)
  → DSH hg-round-orchestrator post-commit join (parallel with Narrator + Plot)
  → runPostCommitLibrarianLifecycle
      → prepareLibrarianProposalContext (Host)
          → evaluate_eligibility: ACTIVE/ESCALATING continuity issues
          → prepare_proposal_context + evidence catalog
          → inference_kind: storyteller_post_commit_issue_pressure
      → runLibrarianProposalGeneration (DSH)
          → LLM inference (+ optional contract_correction)
          → proposal_kind: issue_tension_pressure
          → proposal_origin: storyteller
      → finalizeLibrarianProposals (Host)
          → validate + Continuity accept/reject
          → apply_issue_tension_pressure → issue_pressure_semantic_overlays
  → scene_pressures digest (subsequent rounds) → Director / Character
```

**Key files:** `v2/rp_runtime/src/plugins/hg-round-orchestrator/service.mjs` (post-commit join); `v2/rp_runtime/src/lib/librarian-proposal-orchestration.mjs`; `v2/rp_runtime/src/lib/librarian-proposal-substrate.mjs`; `v2/domain_api/kernel.py` (`prepare_librarian_proposal_context`); `v2/domain/modules/continuity_librarian_issue_pressure.py`.

**Eligibility:** Skips inference when no ACTIVE/ESCALATING issues (`inference_required=false`, `eligibility_outcome` e.g. `no_eligible_active_issues`). Uncertainty fails open to assessment per architecture docs.

**Not gated by** `skipStorytellerCognition`.

---

## 7. Current Plot pressure implementation path

```text
Round start / post-commit (conditional, Domain-planned)
  → plot_cognition_init | plot_cognition_update | plot_cognition_epistemic_eval
  → PlotCognitionOverlay (session-persistent)
      → PlotGoal
      → UnresolvedNarrativePressure  (pressure_text, dramatic_rationale, continuity_issue_refs)
      → GlobalPlotFrame
  → project_director_overlay / Character advisory projection (epistemically gated)
  → Director / Character (same or subsequent turns)
```

**Semantic distinction** (`plot-cognition-overlay-contract.md`):

| Kind | Role |
|------|------|
| Continuity issue | Authoritative blocked/unresolved **world state** |
| UnresolvedNarrativePressure | Storyteller **observation** of unresolved dramatic potential |
| PlotGoal | Storyteller **intended pursuit** direction |

Post-commit `issue_tension_pressure` writes **derived** `semantic_unmet_condition` / `stakes_summary` per issue ref into Continuity overlays — a **different store and schema** from Plot overlay pressures, but overlapping narrative territory.

---

## 8. `skipLibrarianProposalGeneration` exact semantics

**Location:** `v2/rp_runtime/src/plugins/hg-round-orchestrator/service.mjs` L532–539.

When `options.skipLibrarianProposalGeneration === true`:

- `runPostCommitLibrarianLifecycle` is **not invoked**
- Returns immediate resolved promise: `{ ok: true, terminal: true, skipped: true, stage: 'skipped' }`
- **No** `prepareLibrarianProposalContext` Host call
- **No** `storyteller_post_commit_issue_pressure` inference
- **No** `finalizeLibrarianProposals` / overlay application
- **No** `hg/post-commit-semantic-started` trace events (verified in `librarian-proposal-orchestration.test.mjs`)

**Active proposal kinds in production sync path** (`librarian_proposal_contract.py`):

```python
S4A_ACTIVE_PROPOSAL_KINDS = frozenset({"issue_tension_pressure"})
```

Retired/legacy kinds (`consequence_meaning`, `information_salience`, `knowledge_revelation_significance`) are **not** in the active sync path.

---

## 9. Causal-isolation assessment of `skipLibrarianProposalGeneration`

| Question | Answer |
|----------|--------|
| Suppresses `storyteller_post_commit_issue_pressure`? | **Yes** — entire lifecycle skipped |
| Suppresses only Librarian proposal generation? | **Yes** — but in current production that path **is** the Storyteller post-commit issue-pressure producer (misleading legacy name) |
| Suppresses other proposal types? | **No active types** beyond `issue_tension_pressure` in sync path |
| Changes Plot inputs? | **No** — Plot runs via separate `runPostCommitPlotCognitionLifecycle` gated by `skipPlotCognitionOrchestration` |
| Changes authoritative Continuity? | **No** — only prevents **derived** overlay writes; commits/issues/events unchanged |
| Changes preamble behavior? | **No** — separate `skipStorytellerCognition` flag |
| Changes Character/Director/Narrator inputs independently of pressure removal? | **Only** via absent `scene_pressures` overlay contribution on **subsequent** turns; no same-turn change to committed facts |
| Suppresses entire mediation subsystem? | **No** — round-start `librarian_mediation` (Storyteller/KAR lanes) unaffected; only post-commit S4 join |

### Verdict

**Acceptable causal intervention for D-10 in current production**, with documentation caveat:

- Hook name says "Librarian" but `semantic_producer_role: 'storyteller'` and `inference_kind: storyteller_post_commit_issue_pressure` identify the semantic producer under test.
- Functionally isolates post-commit issue-pressure generation/application.

**Risk:** Future addition of new `S4A_ACTIVE_PROPOSAL_KINDS` would broaden the hook blast radius. D-10 execution record must verify active kinds at run time.

---

## 10. Proposed intervention / harness hook

### Primary (recommended): existing hook

```javascript
// Control arm
{ skipStorytellerCognition: true }  // preamble OFF (D-01-L verdict baseline)

// Ablated arm
{ skipStorytellerCognition: true, skipLibrarianProposalGeneration: true }
```

### Investigation-only alias (optional, not implemented)

Document in harness as **`skipPostCommitStorytellerIssuePressure`** mapping to `skipLibrarianProposalGeneration` for experiment clarity. **No production code change required** if mapping is harness-local documentation + roundOptions passthrough.

### Not recommended

- `skipPlotCognitionOrchestration` on ablated arm — would confound Plot retention requirement.
- Preamble ON on either arm — would reintroduce D-01-L confound.

---

## 11. Control arm

| Setting | Value |
|---------|-------|
| Plot cognition | **ON** |
| Storyteller synchronous preamble | **OFF** (`skipStorytellerCognition: true`) |
| Storyteller post-commit issue-pressure | **ON** |
| Continuity | normal |
| PVR / perception | normal |
| Director / Character / Narrator | normal |
| Post-commit Plot lifecycle | **ON** (not skipped) |
| Narrator presentation | normal |

---

## 12. Ablated arm

| Setting | Value |
|---------|-------|
| Plot cognition | **ON** |
| Storyteller synchronous preamble | **OFF** |
| Storyteller post-commit issue-pressure | **OFF** (`skipLibrarianProposalGeneration: true`) |
| All else | equivalent to control |

**Only intended causal difference:** post-commit Storyteller pressure producer + overlay application path.

---

## 13. Scenario selection and pressure-activation proof

### Arkham mess hall stress — **PRIMARY** (retain, extend policy)

**Rationale:** Multi-agenda public scene, guard pressure, recruitment, watch temptation, institutional surveillance — high likelihood of ACTIVE/ESCALATING continuity issues and dramatic escalation across turns.

**D-01-L forensic baseline (post-commit ST inferences per committed sequence):**

| Scenario | Arm | ST post-commit (seq) | Turns |
|----------|-----|---------------------:|------:|
| Arkham | control | 6, 9 | 5 |
| Arkham | ablated | 8, 8 | 5 |
| Ayame | control | 1, 2 | 3 |
| Ayame | ablated | 2, 2 | 3 |

**Prospective pressure pathway (Arkham control):**

| Turn | Expected post-commit trigger | Available next turn | Consumer |
|------|------------------------------|---------------------|----------|
| 1+ | Character commits → eligibility if issues ACTIVE/ESCALATING | Turn N+1 Director/Character `scene_pressures` | Director selection bias; Character tone/agenda |
| 2–5 | Cumulative commits escalate recruitment/guard/watch threads | Turns 3–5 | Delayed consequence, agenda persistence dimensions |

1. **Pressures created:** `issue_tension_pressure` per eligible commit (issue-bound semantic overlay).
2. **When available:** After join completes; consumed next Director cycle.
3. **Later consuming turns:** All subsequent turns in 5-turn sequence.
4. **Downstream cognition:** Director context digest, Character `scene_pressures`.
5. **Observable difference:** Escalation coherence, delayed consequences, scene momentum if overlays change director/character framing.

**Policy:** New frozen policy `arkham_d10_policy_v1` — adapt D-01-L Arkham predicates with **5 turns** (same arc structure); hash before any arm runs.

### Ayame household entry — **CONFIRMATORY** (retain with reduced weight)

**Rationale:** Controlled interview supports agenda/boundary pressure but **lower observed post-commit ST activation** in D-01-L (1–2 inferences per 3-turn sequence).

**Prospective assessment:**

| Criterion | Ayame |
|-----------|-------|
| Exercises `issue_tension_pressure`? | **Partially** — mechanism fires but less frequently |
| Meaningful later-turn consumption? | **Yes** when issues exist (interview terms, household control) |
| Worth full parity with Arkham? | **No** — reduced replication |

**Policy:** New frozen `ayame_d10_policy_v1` — **4 turns** (extend 1 turn vs D-01-L to allow one additional post-commit→consume cycle). Hash before execution.

**If prospectively <1 eligible post-commit activation per Ayame control sequence in pilot calibration:** drop Ayame from D-10 tranche (document trigger) rather than waste live cost.

---

## 14. Frozen player-policy design

Same discipline as D-01-L:

- Pre-authored semantic objectives per turn
- Deterministic predicate branching from **observable presentation text only**
- Frozen before either arm; SHA-256 hash recorded
- Per-turn log: `policy_hash`, `predicate_hits`, `winning_predicate`, `branch_id`, `exact_player_stimulus`
- **No** architecture identity in branch selection

**New policy IDs** (not reuse of D-01-L hashes): `arkham_d10_policy_v1`, `ayame_d10_policy_v1`.

---

## 15. Sequence length and sample count

**Do not automatically copy D-01-L 2×2×2 = 8.**

### Proposed bounded tranche

| Scenario | Turns | Sequences / arm | Sequences total / scenario |
|----------|------:|----------------:|---------------------------:|
| Arkham (primary) | 5 | **2** | 4 |
| Ayame (confirmatory) | 4 | **1** | 2 |

**Total: 6 sequences** (~26–28 committed turn-presentations depending on Ayame length).

### Rationale

| Factor | Implication |
|--------|-------------|
| Post-commit activation is **eligibility-gated** (not every commit) | Arkham needs replication; Ayame lower activation → fewer sequences |
| Longitudinal requirement | ≥4 turns so turn-N overlay affects turn N+1..end |
| D-01-L cost baseline | Arkham ~20 min/seq; 4 Arkham × 2 arms ≈ similar order to 4 Arkham D-01-L sequences |
| Branch variance | 2 Arkham reps minimum; expansion trigger if contradictory |

### Prospective expansion triggers (max +1 sequence/scenario/arm)

1. Contradictory sequence-level outcomes between replications
2. Contaminated/incomplete sequence
3. Intervention-specific correctness failure pattern
4. **Post-commit activation rate <1 eligible event per Arkham control sequence** (mechanism not exercised — not a semantic null result)
5. Extreme branch divergence preventing comparison

---

## 16. Pressure-propagation instrumentation

Per turn, capture in investigation report JSON (excluded from blind packet):

| # | Field |
|---|-------|
| 1 | `domain_commit_id`, committed event summary |
| 2 | `post_commit_librarian_skipped` (arm + hook) |
| 3 | `post_commit_eligibility_outcome` |
| 4 | `storyteller_post_commit_inference_ran` (bool) |
| 5 | Raw proposal batch (`issue_tension_pressure` payloads) |
| 6 | Accept/reject per proposal |
| 7 | `issue_pressure_semantic_overlays` delta (issue_ref keys) |
| 8 | `scene_pressures` digest snapshot (Director-relevant subset) |
| 9 | Plot overlay snapshot hash / pressure_ids before |
| 10 | Plot overlay snapshot after |
| 11 | `plot_pressure_equivalence_flags` (see §17) |
| 12 | Director overlay projection includes ST lanes / plot pressures (booleans) |
| 13 | Character projection pressure fields present |
| 14 | Narrator context (if pressure-relevant fields exist) |
| 15 | `downstream_decision_summary` (next_actor, presentation delta tag) |

**Sequence-level:** activation count, consumption count, storage-without-consumption count, duplicated-vs-unique pressure count.

Harness: extend D-01-L longitudinal script pattern; add Host state snapshots via existing report APIs / sequence JSON sidecars.

---

## 17. Semantic-equivalence analysis method

**Separate from blind RP-quality scoring.**

### Deterministic structural comparison (per turn pair)

For each `issue_tension_pressure` overlay applied (control arm forensics; both arms for Plot-native pressures):

| Check | Method |
|-------|--------|
| Issue linkage | `issue_ref` matches Plot pressure `continuity_issue_refs`? |
| Text overlap | Normalized token Jaccard between `semantic_unmet_condition` and Plot `pressure_text` (threshold ≥0.35 = `overlapping`) |
| Unique Plot pressure | Plot `UnresolvedNarrativePressure` with no matching issue overlay |
| Unique ST overlay | Overlay with no Plot pressure sharing issue_ref or token overlap |
| Contradiction | Same issue_ref with opposing stakes polarity (manual flag rule: negation patterns) |

Classify each pressure pair: `equivalent` | `overlapping` | `complementary` | `contradictory` | `unique_st` | `unique_plot`.

### Bounded semantic review (optional, not blind RP)

Governance may review **flagged overlapping pairs only** (structural score 0.35–0.55 band) in a separate non-blind appendix. **No always-on production LLM checker.**

---

## 18. Blind primary semantic endpoint

**Reuse D-01-L 10 sequence-level dimensions** (1–5 per sequence):

1. thread persistence  
2. escalation coherence  
3. agenda persistence  
4. delayed consequences  
5. scene momentum  
6. cross-turn initiative  
7. reactive-loop avoidance  
8. premature-resolution avoidance  
9. plot-drift control  
10. cross-turn emotional/narrative continuity  

**Evaluation unit:** complete chronological sequence.

**Separate forensic report:** pressure propagation metrics (§16–17) — **not** combined with subjective scores.

**Blinding:** Same rules as D-01-L; exclude pressure logs, Plot snapshots, inference, latency, arm identity.

---

## 19. Failure / replacement / expansion rules

| Class | Handling |
|-------|----------|
| Generic runtime (`character_failure`, timeout) | Preserve evidence; retry up to 2 attempts/sequence; then replacement if authorized |
| Infrastructure | Exclude from blind scoring; flag wall-time outlier |
| Intervention-specific repeated pattern | **Stop and report** — do not infinite retry |
| Noncommitted sequence | Excluded from blind packet; retained in failure inventory |
| Expansion | Per §15 triggers only; max +1 seq/scenario/arm |

---

## 20. Architectural / token / wall-time accounting

Per sequence (both arms):

| Metric |
|--------|
| Total inference count |
| `storyteller_post_commit_issue_pressure` (+ correction) count |
| `plot_cognition_*` count |
| Round-start `librarian_mediation` (if any with preamble OFF, expect near-zero ST lane) |
| Character / Director / Narrator inference counts |
| Input / output / reasoning tokens (where available) |
| Wall time per turn and per sequence |
| Retries / corrections |
| Post-commit join wait time (Narrator vs semantic join) |

**Separate reporting:**

- **Critical-path cost:** visible turn presentation latency
- **Total compute cost:** including post-commit parallel work
- **Next-turn inherited cost/state:** overlay/plot snapshot size deltas

---

## 21. Prospective interpretation rules

### Unique post-commit Storyteller value

Requires **all:**

- ST creates pressures classified `unique_st` or materially `complementary` (not merely `overlapping`)
- Pressures **consumed** (appear in downstream Director/Character context on later turns)
- Consumption associates with consequential trajectory difference
- Control shows **consistent** longitudinal advantage on pressure-relevant dimensions (delayed consequences, escalation, agenda persistence) with correctness matched

### Redundant post-commit Storyteller

- Plot independently represents `equivalent`/`overlapping` pressures
- ST overlays add little unique downstream information
- Ablated longitudinal quality/correctness **comparable** (overall Δ ≤0.15; no systematic loss on delayed-consequence / escalation dimensions)
- No systematic correctness degradation

### Complementary value

- Distinct ST pressures (`complementary` or `unique_st`) improve later decisions/trajectory
- Not explainable as Plot duplication alone

### Storage-without-value

- Distinct durable overlays created but rarely projected/consumed OR consumption decision-neutral

### Inconclusive

- Activation too rare (<1 eligible Arkham activation per control sequence across tranche)
- Hook blast radius changed (new S4A kinds)
- Branch divergence overwhelms comparison
- Sample conflict / reliability contamination

**Not sufficient:** control sequences score well in isolation. **Between-arm causal comparison required.**

---

## 22. Expected architecture discrimination

| D-10 outcome | Architectural implication |
|--------------|---------------------------|
| **Redundant** | Consolidate toward one persistent narrative-cognition subsystem (Plot-derived); remove post-commit duplicate producer; preamble already relocate candidate → strengthens **A2 / compact A3** |
| **Complementary** | Retain post-commit **function**; topology open (may still merge into single subsystem) |
| **Unique separate-agent value** | Evidence for distinct Storyteller responsibility → stronger specialized **A3** |
| **Inconclusive** | Preserve uncertainty; synthesis documents assumptions |

---

## 23. Durable record, Governance decisions required

| Item | Value |
|------|-------|
| **This design record** | `governance/records/issue-201-package-d-d10-experimental-design-2026-09-14.md` |
| **Commit SHA** | `d13f2a0` |
| Harness (future) | Extend `issue201-package-d-d01l-longitudinal.mjs` → `issue201-package-d-d10-post-commit.mjs` (not implemented) |
| Policies (future) | `governance/records/issue201-d10-policies/` (not created) |

### Exact Governance decisions required

1. **Accept D-10 experimental design** as specified (arms, hook, scenarios, sample size).
2. **Accept `skipLibrarianProposalGeneration`** as causal intervention with documented naming caveat + runtime S4A kind verification.
3. **Authorize or amend** sample tranche (6 sequences: 4 Arkham + 2 Ayame).
4. **Authorize or decline** Ayame confirmatory arm (or Arkham-only fallback if activation proof fails in calibration).
5. **Authorize D-10 execution** (separate step — **not** this document).
6. **Confirm** synthesis deferred until D-10 completes.
7. **Confirm** no production remediation Issue until #201 architectural conclusions.

**#201 remains:** `investigating` — In Progress / Investigating / **P1**

**Do not execute live D-10 in this step.**
