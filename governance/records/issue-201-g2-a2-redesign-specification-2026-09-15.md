# Issue #201 — First-Principles A2 Redesign Specification

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Execution stage:** `consensus_reached` — In Progress / Awaiting Consensus / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  
**G1 acceptance:** `aafee62` — `issue-201-package-d-final-synthesis-first-principles-architecture-2026-09-15.md`  
**G1 transition record:** `issue-201-g1-acceptance-phase-transition-2026-09-15.md`  
**Status:** Architecture-level redesign specification — **NOT implementation**

---

## 1. Executive specification

Holy Grail RP should be rebuilt around **A2**:

1. **Deterministic substrate** — Continuity, PVR/entitlement, retrieval/indexing, validation, audit.
2. **Primary RP cognition** — logically distinct Character agency, Director turn selection, and Narrator presentation; **physically** may coalesce on simple beats but **never** without inspectable authority boundaries.
3. **Persistent Plot/Scribe cognition** — narrative planning, unresolved pressure, long-horizon trajectory; **off the synchronous critical path by default**.
4. **Obligation-driven escalation** — additional cognition only when deterministic signals authorize it.
5. **Layered protection** — deterministic validation first; narrow semantic repair only on failure/uncertainty.

**Design thesis:** Minimum cognition necessary for the obligations present on that turn.

**Not in scope:** implementation classes, prompts, model providers, numeric thresholds, latency SLAs, rollout sequencing.

---

## 2. Accepted #201 decisions (G1)

See `issue-201-g1-acceptance-phase-transition-2026-09-15.md`. Package D experimentation is **closed**. Target architecture is **A2**.

---

## 3. Design goals

| Goal | Measure |
|------|---------|
| Preserve demonstrated RP capabilities | No regression on protected outcomes (§24) |
| Reduce synchronous cognition bureaucracy | Fewer always-on LLM stages vs A4 |
| Preserve forensic causality | Intent → commit → presentation traceable |
| Scale massive knowledge without agent proliferation | Retrieval/indexing + projection |
| Tier simple vs complex beats | Additive escalation, not parallel architectures |
| Falsifiable redesign | §29 criteria |

---

## 4. Non-goals (G2)

- Exact module/class layout
- Prompt text or model selection
- Numerical complexity scores or latency/token caps
- Migration sequencing or production deletion order
- Prototype execution (G3)
- Remediation child-Issue creation

---

## 5. Required outcomes (mechanism-independent)

All outcomes from final synthesis §5 remain mandatory. The specification assigns **logical owners** in §8–17 and **proof** in §24.

---

## 6. Architectural invariants

Derived from project authority (`architecture-overview`, `PACKET_CONTRACTS`, `AUTHORED_SOURCE_CONTRACT`, audit semantics):

1. **Only Continuity (Host kernel) commits authoritative world/character state.**
2. **Advisory cognition cannot silently become authority** — Plot/Scribe, retrieval summaries, env enrichment are advisory until Host-validated commit.
3. **No Character receives knowledge outside entitlement** — PVR projection is mandatory gate.
4. **Rendering cannot mutate committed state** — Narrator output is presentation-only; state changes flow through move commit.
5. **Retrieval provenance remains inspectable** — every fact in a cognition package has source record + entitlement path.
6. **Failed validation cannot silently pass** — fail-closed or bounded repair; no "soft ignore."
7. **Repair is bounded** — max attempts, declared failure surface, audit event.
8. **Optional cognition cannot alter authority boundaries** — tiering changes inputs, not who may commit.
9. **Every durable derived/advisory state has freshness semantics** — `as_of_turn`, `stale_after`, or explicit invalidation event.
10. **Every LLM inference has declared consumer and decision purpose** — no orphan cognition.
11. **Player authorship is protected** — deterministic rules; model cannot rewrite player intent.
12. **Scenario authority is enforced** — premise secrets and role facts are not inventable by creative cognition.
13. **Per-character move contracts remain inspectable** — even when batched physically.
14. **Audit distinguishes** intent, interpretation, decision, commit, presentation/observation, repair.

---

## 7. Logical vs physical cognition

### Rule

**Logical roles** define authority and contracts. **Physical calls** are packaging optimizations subject to invariants §6.

A single physical inference may implement multiple logical roles **only if**:

- outputs are separable in the execution contract (distinct JSON regions or ordered phases within one response);
- validators can inspect each logical output independently;
- commit boundary occurs before presentation when Character and Narrator cohabit one call;
- audit records logical step boundaries even when physical call count is one.

### Logical role catalog

| Logical role | Typical physical binding |
|--------------|--------------------------|
| Player ingress boundary | Deterministic |
| PVR triage / uniform gate | Deterministic |
| Entitlement projection | Deterministic |
| Retrieval selection | Deterministic (+ optional mediation) |
| Director eligibility | Deterministic |
| Director turn decision | Primary RP LLM **or** deterministic policy |
| Character move generation | Primary RP LLM (per entitled actor) |
| Narrator presentation | Primary RP LLM |
| Env obligation resolution | Conditional Primary RP or dedicated conditional call |
| Plot/Scribe update | Scribe LLM (usually post-commit / async) |
| Deterministic validation | Deterministic |
| Semantic repair | Conditional LLM |
| Audit emission | Deterministic |

---

## 8. Deterministic substrate

### 8.1 Continuity

| State class | Authority | Persistence |
|-------------|-----------|-------------|
| Committed world/scene facts | Authoritative | Durable |
| Character state (location, posture, inventory, flags) | Authoritative | Durable |
| Relationship state | Authoritative | Durable |
| Persistent objects / props | Authoritative | Durable |
| Locations / portals / connectivity | Authoritative | Durable |
| Scenario facts / secrets (role-gated) | Authoritative | Durable |
| Delayed consequence queue | Authoritative | Durable until fired |
| Plot overlay (pressures, goals, trajectory) | **Derived advisory** | Durable with freshness |
| Scene-local ephemeral flags | Derived | Scene-local |
| Staleness markers | Meta | Turn-indexed |

**Writes:** only through Host-validated commit API after validation pass.

### 8.2 Perception / knowledge (PVR)

- **Viewer-relative visibility** — what a given actor/player may perceive.
- **Channel separation** — auditory / visual / non-perceptual / narrative-only.
- **Portal/location constraints** — separated rooms, closed doors.
- **Private knowledge** — character-scoped facts never in another actor's package.
- **Scenario-role knowledge** — GM/scenario facts gated by role.
- **Entitlement** — who may know/act on what this beat.
- **Projection** — deterministic assembly of `ActorContextPackage` per consumer.

**Player decomposition** — conditional LLM only when uniform-eligible path fails or semantic decomposition obligation is raised (not default simple beat).

### 8.3 Retrieval

```text
need signal → index query → entitlement filter → rank → provenance bundle → budget trim → projection template
```

- Indexed lore, entity graphs, session history summaries, relationship edges.
- **Provenance:** record id, source corpus, entitlement class, excerpt bounds.
- **Context-budget management:** deterministic truncation with explicit "omitted" manifest.

### 8.4 Validation

| Validator family | Detects (examples) |
|------------------|-------------------|
| Schema/contract | Malformed move/presentation JSON |
| Authority | State mutation from presentation; out-of-role action |
| Perception/knowledge | Leak across entitlement boundaries |
| Spatial | Actor at conflicting location; portal violation (Sample E class) |
| Player authorship | Player text rewritten or attributed incorrectly |
| Committed-move consistency | Move contradicts prior commit without legal transition |
| Scenario authority | Invented premise fact |

### 8.5 Audit

Forensic chain per turn:

```text
player_intent → ingress_classification → projections_emitted → cognitions_invoked
→ decisions_proposed → validations_run → commit_applied → presentation_rendered
→ post_commit_derivations → repairs_if_any
```

---

## 9. Primary RP intelligence

### Minimum responsibilities

| Responsibility | Default owner | Notes |
|----------------|---------------|-------|
| Character move generation | Primary RP | Core creative endpoint — **retain** |
| Local character reasoning (voice, reaction) | Primary RP | Bundled with move |
| Actor/turn selection | Director logical role | See §11 |
| Immediate dramatic choice (who speaks/acts) | Director | Not Scribe |
| Narrator rendering | Primary RP | Separate logical contract from move |
| Environmental enrichment | Conditional | Only on env obligation (§15) |
| Local scene progression prose | Narrator | Must not commit state |

### Physical packaging options (not prescriptive)

| Beat class | Allowed packaging |
|------------|-------------------|
| Simple single-actor | **Option A:** separate Character move call + Narrator call. **Option B:** one call with **enforced** `proposed_move` then `presentation` sections; Host commits between logical phases via staged validation. |
| Complex multi-actor | Separate Character calls per entitled autonomous actor; shared Narrator call **or** per-location presentation slices |

**G2 determination:** Do **not** mandate single-prompt merging. Default **logical separation** of move vs presentation. Physical coalescence is **permitted only on simple beats** where staged validation is provable in prototype (G3).

---

## 10. Character agency model

### 10.1 One relevant NPC

```text
Director (deterministic eligibility + optional LLM selection)
→ per-actor projection (deterministic)
→ Character move cognition (1 call)
→ move validation → commit
→ Narrator presentation
```

### 10.2 Multiple relevant NPCs

When **actor multiplicity** and **entitlement divergence** obligations are present (§20):

- Each NPC requiring **independent agency** this beat receives:
  - isolated `ActorContextPackage` (private knowledge, perception, agenda slice);
  - independent `CharacterMoveProposal` contract;
  - independent validation + commit (may batch commits atomically at Host).

**Cross-character leakage prevention:**

- No shared prompt section containing another actor's private knowledge.
- Parallel proposals validated independently.
- Audit tags `character_id` on every proposal.

### 10.3 Simultaneously acting NPCs

**G2 specification:**

- **One primary inference may NOT safely generate multiple independently entitled autonomous moves** when private knowledge or agendas diverge.
- **Authorized pattern:** N Character move cognitions for N entitled autonomous actors on that beat (parallel allowed).
- **Exception (G3 must validate):** purely choreographed non-agentive background motion may be Narrator-local color **without** character move commits.

**Do not sacrifice agency for call-count targets.**

### 10.4 Orientation / context preparation

| Attribute | Value |
|-----------|-------|
| Logical role | Assemble character-local situational framing before move |
| Authority | Advisory input to Character move only |
| Invocation | **Conditional** — complexity / retrieval / agenda obligation |
| Physical | May be folded into Character call context assembly (deterministic + retrieval) rather than separate LLM |

---

## 11. Director responsibility

| Function | Owner | Invocation |
|----------|-------|------------|
| Deterministic eligibility (who may act) | Orchestration / Host | Always |
| Turn ownership / round structure | Orchestration | Always |
| Actor selection among eligible set | Director logical role | Always when >0 NPC eligible |
| Narrative priority / spotlight | Director LLM **or** deterministic policy | Conditional |
| Conflict arbitration (who yields) | Director LLM | Only when policy ambiguous |
| Semantic QA on Director output | **Removed** | D-06 evidence |

**G2 determination:** Director does **not** require a dedicated LLM on every turn.

- **Simple beat, single eligible actor:** deterministic selection (no LLM).
- **Multiple eligible actors or policy ambiguity:** Director LLM **or** deterministic priority rules with Scribe advisory hints (read-only).

Scribe may recommend spotlight; **Director/Host** decides turn selection.

---

## 12. Narrator responsibility

| Function | Owner |
|----------|-------|
| Render committed events | Narrator |
| Player-visible projection | Narrator |
| Environmental description | Narrator (from committed + obligation-resolved facts) |
| Scene composition / prose | Narrator |
| Correctness validation | **Deterministic** (§17) |
| Semantic repair | Conditional (§17) |

### Authority rule

> Narration must not silently change authoritative committed state.

### Commit boundary when co-located with Character

If physical coalescence is used:

```text
1. Model emits proposed_move (structured)
2. Deterministic validation on proposed_move
3. Host commit (authoritative)
4. Model emits presentation from CommittedEventManifest only
5. Deterministic validation on presentation (no state deltas)
```

If this staged boundary cannot be enforced reliably in G3 prototype → **mandate separate Narrator call** for that beat class.

### Environment enrichment

Not part of default Narrator path. Resolved under env obligation (§15) **before** presentation assembly when obligation exists.

---

## 13. Plot / Scribe responsibility

**Plot function retained** (Stage-3 +0.239). Design as **persistent narrative cognition** — user "Scribe" lineage without requiring that name in code.

### Reads

- Committed state snapshot (post-commit preferred)
- Durable Plot overlay (prior pressures, goals, trajectory)
- Scene facts, character relationship summaries (bounded)
- Player action + committed moves this turn
- Retrieval packages (historical narrative threads) when obligation raised

### Writes

| Output | Authority | Persistence |
|--------|-----------|-------------|
| Unresolved pressures | Advisory | Durable derived |
| Character/scene goals | Advisory | Durable derived |
| Trajectory / escalation possibilities | Advisory | Durable derived |
| Delayed consequence **proposals** | Advisory | Queue for Host review |
| Scene-transition recommendations | Advisory | Ephemeral or scene-local |

**Plot does not commit world facts.** It proposes overlay deltas; Host ingests validated overlay records.

### Invocation (default off critical path)

| Mode | When |
|------|------|
| **Post-commit async** | Default after player-visible presentation |
| **Scene boundary** | Location/time/scene card change |
| **Event-triggered** | Major state mutation, conflict resolution, revelation |
| **Complexity-triggered sync** | Only if Plot obligation signal + beat cannot proceed without fresh overlay (rare; G3 calibrates) |
| **Init** | Session/scene start |

**Do not** recreate synchronous Storyteller preamble. **Do not** duplicate post-commit ST pressure LLM (D-10).

### Supporting calls under Plot

| Current | G2 disposition |
|---------|----------------|
| `plot_cognition_init` | Retain — scene/session init |
| `plot_cognition_update` | Retain — core Scribe function |
| Plot epistemic eval | **Do not rebuild** default |
| Plot advisory generation chain | Consolidate into update output |
| Plot contract correction | Fold into shared repair policy |

---

## 14. Storyteller responsibility migration

| Historical ST responsibility | New owner |
|------------------------------|-----------|
| Round orientation / scene framing preamble | **Discard** sync path; deterministic scene card + optional Plot init |
| Assessment / summarization preamble | **Discard**; retrieval projection replaces |
| Post-commit issue pressure overlays | **Discard** LLM path; Plot overlay + Continuity derived pressure |
| Unresolved narrative pressure | **Plot/Scribe** |
| Long-horizon trajectory | **Plot/Scribe** |
| Narrative memory compression | **Retrieval** + Plot overlay summaries |
| NPC agenda hints at round start | **Plot overlay** (advisory) + per-character projection |

**Responsibilities that cannot be assigned elsewhere:** **None identified.** Post-commit ST durable overlay **mechanism** existed (D-10) but **function** maps to Plot + Continuity without separate ST LLM.

---

## 15. Environment obligations

**Retain capability; tier mechanism.** Define **obligations**, not numeric thresholds.

| Obligation signal | Authoritative source | May authorize |
|-------------------|---------------------|---------------|
| Missing presentation-critical physical detail | Committed state vs Narrator contract gap | Env resolution cognition |
| Unresolved B2/environmental fact blocking coherent presentation | Scenario fact registry + commit manifest | Env resolution |
| Spatial consequence of committed move | Spatial validator / move commit | Env resolution or deterministic derivation |
| Object affordance required for Character decision | Object state + action intent | Pre-move env resolution |
| Scene transition requiring new grounding | Scene boundary event | Retrieval + optional env cognition |
| **Baseline sufficient** | Projected context covers contract fields | **No** extra cognition |

**Gate design (future):** deterministic inspection of obligation signals — **not** a free-form LLM router (§20).

---

## 16. Retrieval / Librarian redesign

### Default path

```text
need → deterministic/indexed retrieval → provenance-preserving selection → direct context projection
```

### Legitimate semantic mediation obligations

| Obligation | Example |
|------------|---------|
| Conflicting sources | Two lore entries disagree |
| Ambiguous referent | "the magistrate" matches multiple entities |
| Multi-record synthesis | Answer spans >N records with non-trivial merge |
| Insufficiency determination | Retrieval set empty but need persists |
| Semantic reconciliation | Cannot pick deterministically |

**Invocation:** failure-triggered or obligation-triggered — **not** per-orientation fan-out.

### Disposition of current `librarian_mediation`

- **Do not rebuild** as default KAR-lane mediation.
- **Retain function** under conditional mediation with declared obligation.

---

## 17. Validation and repair

### Rejected default pattern

```text
LLM → independent LLM checker → repair   (every turn)
```

### Specified layered protection

```text
generation → deterministic validation → accept
```

When needed:

```text
generation → deterministic failure OR semantic_uncertainty_flag
→ targeted repair OR semantic adjudication (narrow)
→ deterministic revalidation → accept | bounded_fail
```

### Objectively detectable (deterministic)

- Player authorship violation
- Schema/contract malformation
- Illegal state mutation in presentation
- Spatial contradiction (Sample E class)
- Perception entitlement leak
- Known scenario contradiction
- Committed-move inconsistency

### Residual semantic judgment (conditional)

- Character move plausibility vs voice/agency (#193 class) — **retain function**, topology open
- Ambiguous player intent decomposition
- Narrative tone/coherence repair **only after** deterministic pass still fails player-visible contract

**Character semantic evaluation:** retain; may consolidate with move validation pass in G3.

---

## 18. Simple-turn flow

**Example obligations absent:** knock, look, short line, one obvious responder, no retrieval ambiguity, no private-knowledge conflict, no major state mutation.

```text
1. [DET] Player ingress + authorship capture
2. [DET] PVR triage → uniform-eligible path (skip decomposition LLM)
3. [DET] Entitlement projection (player + eligible actors)
4. [DET] Director eligibility → single eligible actor (skip Director LLM)
5. [DET] Retrieval: none unless indexed scene card suffices
6. [COG] Character move OR direct Narrator-only beat (if player action is observational)
7. [DET] Move validation suite
8. [DET] Host commit
9. [COG] Narrator presentation (may be co-located with 6 on G3-validated simple beats only)
10. [DET] Presentation validation (no state delta)
11. [DET] Audit emission
12. [PLAYER VISIBLE]
13. [COG] Plot/Scribe update — post-commit async (off critical path)
14. [DET] Continuity persistence + freshness markers
```

**Skipped optional cognition:** ST preamble, post-commit ST, Director QA, Narrator QA, env cognition, orientation LLM, librarian mediation, plot sync update, decomposition, semantic second opinions.

---

## 19. Complex-turn flow

**Additive** over §18 when obligations present (§20):

```text
… steps 1–4 with:
  - [DET] decomposition LLM if uniform path fails
  - [DET] multi-actor eligibility
  - [COG] Director LLM if selection ambiguous
  - [DET] retrieval obligation → indexed retrieval
  - [COG] conditional mediation if reconciliation obligation
  - [COG] per-actor Character move (N parallel) if N autonomous actors
  - [COG] env obligation resolution before Narrator
  - [DET] expanded validation (spatial, perception, scenario)
  - [COG] Plot sync update ONLY if plot_obligation blocks beat (else post-commit)
… commit → presentation → async Plot default
```

---

## 20. Complexity-routing contract

**No numeric score.** Router is **deterministic obligation aggregator** (future implementation).

| Signal | Authoritative source | Detection | Authorizes | Does NOT authorize |
|--------|---------------------|-----------|------------|-------------------|
| Actor multiplicity | Eligibility engine | DET | Director LLM; N Character calls | Plot sync by itself |
| Entitlement divergence | PVR | DET | Separate per-actor projections + moves | Shared private-knowledge prompt |
| Retrieval obligation | Context manifest gaps | DET (+ optional mediation) | Retrieval path | Default librarian fan-out |
| Environmental obligation | §15 signals | DET | Env cognition | Always-on env |
| Plot obligation | Overlay staleness + beat needs | DET | Sync Plot read (rare) | ST preamble |
| State-mutation risk | Move classifier | DET | Expanded validators | Extra QA layer |
| Semantic ambiguity | Validator uncertainty flags | DET → conditional | Targeted repair | Always-on Narrator QA |
| Repair requirement | Validation failure | DET | Repair call | Retry storm |

**Router must not be a free-form LLM gate** unless G3 evidence proves deterministic signals insufficient.

---

## 21. Massive-knowledge architecture

| Requirement | Mechanism |
|-------------|-----------|
| Novels / lore books | Corpus index + entity linking |
| Thousands of entities | Entity graph + typed queries |
| Long session histories | Rolling summaries in Continuity + indexed turn records |
| Relationships | Structured relationship store + retrieval |
| World geography | Location hierarchy index |
| Private knowledge | Entitlement-tagged records; never in global retrieval |
| Historical descriptions | Provenance-preserving excerpts |

**Scale through infrastructure, not agents.** LLM sees **bounded packages** with omission manifests.

---

## 22. Information-flow minimization

**Eliminated handoffs (vs A4):**

- ST assessment → Librarian → ST orientation chain
- Plot epistemic eval → advisory gen → Character (default)
- Director output → Director QA → repair
- Narrator output → Narrator QA → regen
- Post-commit ST ∥ Plot pressure duplication
- Env cognition when baseline sufficient

**Test for each retained handoff:** unique information created + downstream decision changed. Otherwise remove.

---

## 23. Proposed physical-call envelopes

Estimates are **conceptual**, not SLAs.

| Turn class | Likely cognition | Notes |
|------------|------------------|-------|
| **Simple** | 1–2 Primary RP + 0 sync Scribe | Director LLM usually 0; Plot async post-commit |
| **Typical** | 2–3 Primary RP + 0–1 conditional + async Scribe | May add retrieval (det) + 1 Character |
| **Complex multi-character** | 1 Director + N Character + 1 Narrator + 0–1 env + async Scribe | N = entitled autonomous actors |
| **Repair case** | +1 targeted repair/adjudication | Failure-triggered only |

**vs A4 ~26 kinds / ~38+ calls:** orders-of-magnitude reduction on simple path; complex path still multi-call by necessity.

---

## 24. Protected-capability proof

| Outcome | Preserving mechanism |
|---------|---------------------|
| Character fidelity | Character move + validation + character card in projection |
| Independent agency | Per-actor move cognitions + isolated projections |
| Private knowledge | PVR entitlement + per-actor packages |
| Perception | Viewer-relative projection + presentation filter |
| Scenario authority | Continuity scenario facts + scenario validator |
| World continuity | Continuity commits |
| Persistent objects | Object state in Continuity |
| Delayed consequences | Consequence queue + Plot advisory proposals |
| Narrative pressure | Plot overlay (not ST post-commit) |
| Environmental grounding | Conditional env obligation resolution + Narrator contract |
| Massive retrieval | Index/retrieval/projection stack |
| Player authorship | Deterministic authorship validator |
| Malformed output | Schema validation + bounded repair |
| Hallucinated state | Host commit gate + spatial/scenario validators |
| Long-session drift | Continuity + bounded retrieval; Plot trajectory overlay |
| Audit reconstruction | §8.5 forensic chain |

**G3 must validate:** spatial validator catches Sample-E-class defects without Narrator QA.

---

## 25. A4→A2 migration matrix

| Current responsibility | Current producer | Proposed owner | Authority change | Invocation change | Evidence |
|------------------------|------------------|----------------|------------------|-------------------|----------|
| Committed world state | Continuity/Host | Continuity/Host | None | None | Architecture |
| PVR triage/uniform | Player/PVR | Deterministic substrate | None | Tier decomposition | #197, #194 |
| Player decomposition | `player_decomposition` | Conditional Primary ingress | None | Simple: skip | #194 |
| Director turn selection | `director_turn` | Director logical / deterministic | None | Simple: det only | Core |
| Director semantic QA | `director_semantic_qa` | Deterministic policy + repair | Removed advisory | **Off** | D-06 |
| Character move | `character_move` | Primary RP | None | Retain | Core |
| Character semantic eval | `character_semantic_evaluation` | Validation layer | None | Failure/complex | #193 |
| Character orientation | `character_orientation` | Det projection + conditional context | Advisory only | Complex only | D-03 mixed |
| Librarian mediation | `librarian_mediation` | Retrieval + conditional mediation | None | **Off default** | D0 fan-out |
| Plot init/update | `plot_cognition_*` | Scribe/Plot | Advisory | Post-commit default | Stage-3 |
| Plot epistemic eval | plot support chain | **Removed default** | N/A | Off | Coverage audit |
| ST preamble orientation | `storyteller_orientation` | Scene card + Plot init | Removed | **Off** | D-01-L |
| ST preamble assessment | `storyteller_assessment` | Retrieval summaries | Removed | **Off** | D-01-L |
| ST post-commit pressure | `storyteller_post_commit_issue_pressure` | Plot overlay | Removed duplicate | **Off** | D-10 |
| Narrator presentation | `narrator_presentation` | Primary RP Narrator | None | Retain | Core |
| Narrator env cognition | `narrator_environment_cognition` | Conditional env obligation | Advisory | Tiered | D-04R |
| Narrator semantic QA | `narrator_semantic_qa` | Deterministic + repair | Removed | **Off** | D-07 |
| Contract corrections (various) | per-kind LLM | Shared repair policy | None | Failure only | Coverage audit |
| Opening/segmentation | opening LLM kinds | Session init conditional | None | Init only | Low decision value |

---

## 26. Audit model

See §8.5. Every cognition invocation logs: `inference_kind`, `logical_role`, `consumer`, `obligation_trigger`, `input_manifest_hash`, `output_contract_version`.

Post-commit Plot runs logged as **off-critical-path** with `blocks_presentation: false`.

---

## 27. Failure model

| Failure | Response |
|---------|----------|
| Malformed JSON | Deterministic reject → bounded structural repair |
| Validation failure | Deterministic reject → targeted repair or turn fail |
| Retrieval empty | Insufficiency obligation → mediation or degrade with explicit omission |
| Model timeout | Retry policy with audit; no silent skip |
| Repair exhaustion | Fail turn with forensic bundle; no partial commit of invalid state |
| Plot async lag | Stale overlay marker; sync obligation rare escape hatch |

---

## 28. Prototype/shadow validation plan (G3)

**Not executed in G2.** Success criteria are conceptual.

| Suite | Purpose | Success (conceptual) |
|-------|---------|----------------------|
| Shadow A2 vs A4 lean baselines | Quality + cost | A2 ≥ ablated-arm blind quality on matched scenarios; fewer sync cognitions |
| Simple-beat (F06 knock class) | Latency + quality | No blind regression vs D-07 ablated; material call reduction |
| Complex-beat (Arkham stress) | Agency + knowledge | No leakage; ≥ Stage-3 Plot-off delta recovery with Plot on |
| Longitudinal | Plot persistence | Pressure/goals persist across sessions without ST post-commit |
| Massive-retrieval | Lore scale | Correct entitlement + relevance without default mediation |
| Correctness battery | PVR, spatial, authorship | Sample-E class caught deterministically |
| Blind semantic quality | Concealed labels | Neutral or positive vs lean baselines |
| Efficiency | Counts, latency, tokens | Simple path materially below A4 |
| Failure injection | Malformed, ambiguity | Bounded repair; no silent corruption |

---

## 29. Falsification criteria

Governance should **reject or substantially revise A2** if G3 shows:

- Independent Character agency materially degrades vs A4
- Multi-character private-knowledge leakage increases
- Plot/Scribe cannot preserve long-horizon progression without ST post-commit
- Primary cognition overload harms RP quality on typical beats
- Simple path latency gains paired with blind quality loss
- Complex path recreates A4 bureaucracy (call count approaches current)
- Retrieval-first path loses necessary semantic context systematically
- Audit causality becomes opaque in merged-call experiments

---

## 30. Open design questions

| Question | Blocker? |
|----------|----------|
| Simple-beat Character+Narrator physical coalescence safety | G3 |
| Exact spatial validator rules (Sample E) | G3 |
| Director deterministic policy completeness | G3 |
| Plot sync obligation rare vs never | G3 |
| Character semantic eval topology (folded vs separate) | G3 |
| Mediation obligation detector precision | G3 |
| Optimal Plot overlay schema | G3 |

**None block G2 acceptance or G3 authorization.**

---

## 31. Recommended G3 decision

Governance should decide:

1. **Accept** this G2 specification as the authoritative redesign target.
2. **Authorize** prototype/shadow implementation **only** for non-production experimental paths.
3. **Decline** production mutation until G3 validation passes falsification checks.
4. **Maintain** #201 at `consensus_reached` through G3 planning; advance to `implemented` only when a governed prototype exists (not in this phase).

---

**No production mutation. No remediation Issues. Package D closed.**
