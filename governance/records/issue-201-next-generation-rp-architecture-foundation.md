# Holy Grail RP — Next-Generation Architecture Foundation

**Governing assessment:** [Issue #201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** Approved architectural **direction** and **work-in-progress** design foundation — **not** a frozen implementation specification  
**Evidence base:** #201 program records (Packages A–D, G3, long-horizon LH, information-aging stop)  
**Detailed current vs target mechanics:** [`issue-201-current-vs-a2-scene-data-pathway-matrix.md`](./issue-201-current-vs-a2-scene-data-pathway-matrix.md) (91 pathways)  
**Prior normative decision:** [`issue-201-final-architecture-decision-2026-09-17.md`](./issue-201-final-architecture-decision-2026-09-17.md)

---

## 1. Purpose and status

Issue #201 asked a first-principles question: **if Holy Grail were designed today, which parts of the current RP turn architecture would we deliberately build again?** The investigation was authorized because production rounds had become **architecturally heavy**: many successful specialist LLM stages per turn, long player-visible critical paths, and high coordination cost—while RP quality and operator experience remained unsatisfactory in key sessions. The redesign is driven by **architectural value**, **RP outcomes**, **complexity**, and **critical-path cost**, not by latency optimization alone.

Holy Grail accumulated a **layered synchronous stack**: primary role cognitions (Character, Director, Narrator) wrapped in orientation, Librarian mediation, Plot projection, Storyteller preamble and post-commit passes, environmental cognition, and routine semantic QA on Director, Character, and Narrator outputs. Deterministic substrate (Continuity, PVR, validation, commit, audit) grew alongside this stack and proved necessary; much of the **always-on semantic surround** did not earn retention as a design default.

This document records the **current approved foundation** for the **next generation** of Holy Grail RP. It is durable governance text intended for fresh-context reasoning before implementation Issues are confirmed, rescoped, or replaced.

> **This document describes an approved architectural direction, not a fully frozen implementation design.**

| Layer | Meaning |
|-------|---------|
| **Current production architecture** | What `v2/rp_runtime` and Domain Host execute today (see pathway matrix). |
| **Approved direction** | Principles and WIP shape Governance accepts for next-gen design. |
| **Open design questions** | Items explicitly **not** settled; missing answers are not “implementation debt against a frozen spec.” |

Future Governance may refine this foundation before any migration execution. **No implementation is authorized by this document alone.**

---

## 2. What exists today

Production RP is a **Node DSH runtime** orchestrating **Domain Host** context assembly and authoritative state, with **LLM inference** on ephemeral agents via manifest transport (`docs/architecture.md`).

### Cognitive actors (logical roles in current production)

| Actor | Primary role today |
|-------|-------------------|
| **Character** | Structured move / agency within knowledge and perception bounds |
| **Director** | Actor and beat selection (or participation-direct bypass) |
| **Narrator** | Post-commit presentation prose |
| **Storyteller** | Round-start advisory package; narrow post-commit issue-pressure path (#164) |
| **Librarian** | Contextual semantic mediation and post-commit semantic proposals (S4) |
| **Plot/Scribe (Plot Cognition)** | Overlay persistence, Character projection, round-start and post-commit update paths |

These are **both logical responsibilities and, in production, often separate physical LLM call families** (`llm-call-catalog.mjs`).

### Deterministic / authoritative substrate

| Subsystem | Role |
|-----------|------|
| **Scenario authority** | Premise, roles, scenario-bound facts |
| **Continuity** | Authoritative scene/character state and commit |
| **PVR / perceptual entitlement** | Who may know/observe what |
| **Validation** | Structural and policy gates before commit |
| **Commit** | Single transactional authority seam |
| **Retrieval / indexing** | Corpus recall with hard access constraints |
| **Audit / forensics** | Execution evidence, spans, proposal logs, plot chronicle |

### Broad current pattern

> Multiple specialist cognition calls, often surrounded by structural validation, semantic QA/evaluation, correction/retry, mediation, and projection stages—many on the **mandatory synchronous critical path** per player turn.

Round flow (compressed): player PVR → round preamble (Storyteller + Plot resume) → eligibility/participation → Director (+ QA) → Character (orientation, Librarian, Plot eval, move, semantic eval) → **commit** → parallel post-commit (issue pressure, Plot update, Narrator env + Librarian + presentation + QA) with **join** before the next Director cycle.

**Exact pathways:** [`issue-201-current-vs-a2-scene-data-pathway-matrix.md`](./issue-201-current-vs-a2-scene-data-pathway-matrix.md).

---

## 3. What we tested

Evidence is spread across governance records; this section is a **chronology**, not a full archive.

### Packages A–C (2026-09-14)

| Package | Focus | Headline |
|---------|--------|----------|
| **A** | Mechanism-independent outcomes | Which RP outcomes matter regardless of implementation shape |
| **B** | Node and edge inventory | ~25+ LLM kinds on synchronous path; coordination tax documented (`issue-201-packages-abc-investigation-2026-09-14.md`) |
| **C** | Counterfactual models A0–A4 | A4 = current deep stack; leaner models compared conceptually |

### Package D / G1 — component value

Causal ablations and blind evaluation on production-adjacent arms (see Package D syntheses, Stage 2/3, D-01-L, D-06, D-07, D-10). **Directional findings** (not over-claimed as universal causality):

| Mechanism | Architectural takeaway |
|-----------|-------------------------|
| Storyteller **preamble** | High cost; limited demonstrated marginal value on tested horizons |
| Storyteller **post-commit pressure** | Narrow S4 path; not justified as mandatory universal stack |
| **Director semantic QA** | Did not earn always-on retention |
| **Narrator semantic QA** | Did not earn always-on retention |
| **Environmental cognition** | Disproportionate cost on simple beats; situational |
| **Character orientation** | Support function; high cost when always-on |
| **Plot cognition** | Capability valued; synchronous placement questioned |
| **Routine Librarian mediation** | Mediation costly when default; retrieval distinct |

**A2** accepted as redesign direction in Package D / G2 (`issue-201-g2-a2-redesign-specification-2026-09-15.md`).

### G3 — prototype and blind comparisons

| Tranche | Focus | Headline |
|---------|--------|----------|
| **G3-B / F1** | Simple Ayame | A2 vs lean A4: quality/cost tradeoffs on simpler beats |
| **G3-C / F2** | Complex Arkham | Blind decode; both arms serviceable; A2 competitive at lower stack depth |
| **G3-D** | Causal / consumer traces | Plot projection consumption evidenced in traces |
| **G3-E** | Massive knowledge live blind | A2 modestly ahead on several blind dimensions vs lean A4; private-knowledge gates critical |

Token/call reductions on A2-class paths are **material** in investigation settings; exact production parity was not the claim—**architectural direction** was.

### Persistent cognition — LH-0, LH-1A, LH-1B

| Program | What it tested | Headline |
|---------|----------------|----------|
| **LH-0** | Immediate persistence → Character projection | Persistence **works**; not long-horizon R5 proof |
| **LH-1A** | Longitudinal descriptive (~176 turns) | Execution and blind **signals**; **not** clean R5 discrimination |
| **LH-1B** | Causal R0–R5 forks | **R0–R4 demonstrated** on persistence arms; lean substrate often sufficient |

> **Four-turn (or short-horizon) testing was not long-horizon evidence** for Storyteller’s broadest narrative charter.

### R5 and information-aging

| Topic | Position |
|-------|----------|
| **R5 marginal retention** | **Not demonstrated**; **unresolved**; **architecturally non-blocking** |
| **R5 disproven?** | **No** — absence of proof ≠ impossibility |
| **Aging program** | **Stopped** (2026-09-17): diminishing return; run2/run3 establishment issues; natural RP did not yield controlled shared state for intended comparison (`issue-201-whole-system-architectural-synthesis-2026-09-17.md`) |

**Persistence working (R0–R4) does not by itself demonstrate marginal necessity at R5.**

Storyteller’s **long-range** responsibilities (tension, promises, dormant threads, trajectory, foreshadow/payoff, premature-resolution avoidance) were **not adequately settled** by long-horizon work to date—and were **not disproven**.

---

## 4. Key findings

| Finding | Implication |
|---------|-------------|
| **Deterministic substrate earned its place** | Continuity, PVR, commit/validation, authority boundaries, retrieval/index substrate, auditability — **rebuild deliberately** |
| **Primary RP cognition earned its place** | Character and Narrator fundamental; Director judgment **where selection genuinely requires judgment** |
| **Many specialist calls are situational** | **Absence of obligation → absence of call** should be the default |
| **Routine semantic QA did not justify universal cost** | Keep structural/deterministic validation; semantic QA **not** a default architectural layer |
| **Retrieval valuable; routine Librarian cognition not automatic** | Separate **index/retrieval** from **semantic mediation** |
| **Persistent narrative cognition works (R0–R4)** | Capability real; **marginal always-on sync value not proven** |
| **Plot/Scribe promising** | **≠** approval of current synchronous Plot topology |
| **Storyteller intentionally unresolved** | Do **not** rebuild always-on sync preamble/pressure; **do not** claim long-range ST duties disproven |
| **A4 is migration baseline, not target** | Complete always-on synchronous stack not first-principles goal |

---

## 5. Design principles for the next generation

1. **Preserve logical responsibility; do not automatically preserve physical agent boundaries.** A duty may survive while its historical dedicated LLM stage does not.

2. **Separate cognition from authority.** Advisory LLM output must not silently acquire Continuity authority, Character agency, entitlement authority, or commit authority.

3. **Deterministic where objective.** Entitlement, structural validation, eligibility where possible, persistence/commit, routing where objective, audit.

4. **Semantic cognition where judgment is genuinely needed.** Not because the legacy stack used an LLM.

5. **Obligation-driven cognition.** Specialist stages run when a **concrete unresolved obligation** requires them (G2 §20 complexity-routing direction).

6. **Consolidate overlapping cognition where safe.** Shared context, separately typed outputs, intact authority boundaries, no quality collapse—**evidence required before adoption**.

7. **Preserve observability.** Consolidation must not hide: available information, obligation triggers, model conclusions, advisory vs authoritative vs committed outcomes (execution evidence, obligation manifests, audit).

---

## 6. Current approved work-in-progress architecture

Five conceptual layers—not a frozen component diagram.

### Layer 1 — Authority and deterministic substrate

**Approved foundation:** scenario/world authority; Continuity; authoritative Player turn record; PVR; deterministic eligibility/routing where objective; structural validation; authoritative commit; retrieval/index substrate; audit/forensics.

This layer defines **truth, visibility, persistence, and hard boundaries**. **LLM cognition does not own Layer 1.**

### Layer 2 — Context assembly

Build the **smallest sufficient** model-facing package from:

- identity / role; role-private knowledge; entitled Player stimulus; bounded entitled history; relevant Continuity state; deterministic retrieval; semantic retrieval **only when required**; relevant persistent narrative advisory **when available**; environmental information **when needed**.

**Do not assume** Character Orientation, Librarian mediation, Plot epistemic evaluation, etc. must remain separate visible pipeline stages. They may become **internal, conditional services** beneath assembly.

### Layer 3 — Primary RP cognition

**Character** — decide the Character’s next action respecting identity, knowledge, perception, world state, and agency.

Target concept: `context → Character cognition → validation → commit` (exact support topology **not frozen**).

**Narrator** — render committed events and relevant environment into player-facing narrative **without owning authoritative state**.

Target concept: `committed event + sufficient scene context → Narrator → presentation validation/filter → history` (env cognition, Librarian, semantic repair **conditional**, not presumed).

**Director function** — resolve actor/beat routing when deterministic policy cannot. **Not frozen** as necessarily a permanent separate physical LLM agent.

### Layer 4 — Persistent narrative intelligence (hypothesis; see §7)

Off-critical-path by default; may feed Layer 2 projections when obligations require.

### Layer 5 — Validation and repair philosophy (see §8)

Structural/deterministic first; bounded repair; conditional semantic review last—not universal second LLM per stage.

---

## 7. Persistent narrative intelligence — active design hypothesis

**Approved for further reasoning — NOT settled physical architecture.**

Governance is considering whether **Director**, **Storyteller**, and **Plot/Scribe** are **three logical responsibilities** that might **not** require **three permanent separate cognitive agents**.

| Responsibility | Logical scope |
|----------------|---------------|
| **Director** | Current-turn narrative/actor routing when judgment required |
| **Storyteller** | Longer-range dramatic understanding: unresolved tension, relationship trajectory, threats, promises, dormant threads, delayed consequences, foreshadow/payoff, resistance to premature resolution |
| **Plot/Scribe** | Durable narrative planning/state: persistent obligations, thread tracking, planned opportunities, durable state/projection |

**Active hypothesis:** a **single Persistent Narrative Intelligence** might perform these logical duties through **one shared cognition surface**, producing **separately typed outputs**, running **only when corresponding obligations require work**.

**Potential benefits:** shared context ingestion; less duplicated reasoning; fewer calls; holistic reconciliation of short-term routing with long-term trajectory; one inference satisfying multiple simultaneous narrative obligations when safe.

**Constraints:** Character retains agency; deterministic eligibility stays outside narrative intelligence; Continuity retains authoritative state; narrative output remains advisory until validated/persisted through proper seams; Director routing authority remains **logically distinguishable**; persistent updates auditable; combined cognition must be tested for overload and responsibility loss.

> **This consolidation is NOT approved as the final physical architecture.** It is the **leading hypothesis** to reason about after #201, alongside a **fresh Storyteller assessment**.

Default **approved** direction from #201 remains: **do not rebuild** always-on sync Storyteller stack; **Plot/Scribe off default synchronous critical path**; capability retained.

---

## 8. Validation and repair philosophy

Emerging replacement for QA-heavy stacks:

```text
cognition → deterministic/structural validation → accept
```

On objective failure:

```text
→ bounded repair/correction (including contract correction where applicable)
```

When genuine semantic uncertainty or high-value obligation remains:

```text
→ conditional semantic review
```

**Do not assume:** `every cognition → another LLM judging it`.

Package D evidence: routine Director/Narrator semantic QA **failed to demonstrate** enough marginal value for universal execution. **Character semantic evaluation** remains evidence-backed for specific failure classes (#193, #199)—likely **conditional**, not ceremonial always-on.

---

## 9. Simplified intended scene flow

```text
Scenario / Continuity / Player
        ↓
Ingress interpretation
        ↓
PVR / entitlement / authority
        ↓
Context assembly
        ↓
Deterministic routing
        ↓
Narrative routing judgment if required
        ↓
Character cognition
        ↓
Validation
        ↓
Authoritative commit
        ↓
Narrator context assembly
        ↓
Narrator
        ↓
Perceptual presentation filter
        ↓
Player-visible history
        ↓
Carryover / retrieval / persistent narrative update
```

**Persistent Narrative Intelligence** may operate: conditionally before a beat; conditionally after meaningful commits; **asynchronously/off critical path** for durable planning; once for multiple obligations when safe and tested. **Exact scheduler mechanics are not specified here.**

---

## 10. What is settled

| Question | Current position |
|----------|------------------|
| Continuity / authoritative commit | **Retain** (rebuild substrate) |
| PVR / entitlement | **Retain** |
| Character (logical role) | **Retain** |
| Narrator (logical role) | **Retain** |
| Deterministic validation + commit | **Retain** |
| Retrieval / index substrate | **Retain** |
| Auditability | **Retain** |
| Routine Librarian mediation | **Conditional**, not default |
| Routine semantic QA (Director/Narrator) | **Not default** |
| Environmental cognition | **Conditional** |
| Character orientation | **Conditional** / internal support |
| Storyteller sync preamble | **Do not rebuild** as mandatory |
| Storyteller post-commit pressure (default) | **Do not rebuild** as mandatory |
| Current Plot sync topology | **Do not preserve** by default |
| Plot/Scribe capability | **Retain** (topology change) |
| A4 full stack | **Migration baseline**, not target |
| R5 for architecture choice | **Non-blocking**; **not demonstrated** |

---

## 11. What is deliberately NOT settled

- Final **Storyteller responsibility set** and adequacy of prior long-horizon ST testing  
- Whether **Director + Storyteller + Plot/Scribe** become **one physical Narrative Intelligence**  
- Exact **Narrative Intelligence invocation policy** and obligation schema  
- Exact **async Plot / persistent-cognition scheduler** (#211-class detail)  
- Whether some support cognition **disappears** vs becomes conditional  
- Final **Character context-assembly** topology (stages vs internal services)  
- Final **semantic-review trigger** policy  
- Exact **post-commit join** architecture vs reduced work inside existing joins  
- **Migration Issue decomposition** ([#209](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/209)–[#212](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/212)) — may be confirmed, rescoped, replaced, or superseded  

> These are **open design questions**, not missing implementation work against a frozen architecture.

---

## 12. Existing migration Issues (paused)

| Issue | Earlier decomposition | Status |
|-------|----------------------|--------|
| [#209](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/209) | A2 Track A — execution skeleton | **Paused** |
| [#210](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/210) | A2 Track B — support tiering | **Paused** |
| [#211](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/211) | A2 Track C — Plot off critical path | **Paused** |
| [#212](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/212) | A2 Track D — migration acceptance | **Paused** |

These Issues reflect the **earlier A2 decomposition** and are **intentionally paused** pending further architectural reasoning on **this foundation**.

---

## 13. Next reasoning step

> Governance will revisit this foundation with fresh context before implementation decomposition.

1. **Storyteller responsibilities** — fresh assessment (not concluded by #201).  
2. **Narrative Intelligence consolidation hypothesis** — evaluate benefits, risks, and observability.  
3. **Scene architecture** — reason from **responsibilities and data flows** ([pathway matrix](./issue-201-current-vs-a2-scene-data-pathway-matrix.md)), not historical agent boundaries.  
4. **Only then** confirm, rescope, replace, or supersede #209–#212.

**No implementation should begin merely because this document exists.**

---

## Reference map (concise)

| Topic | Record |
|-------|--------|
| Whole-system synthesis | `issue-201-whole-system-architectural-synthesis-2026-09-17.md` |
| Final decision | `issue-201-final-architecture-decision-2026-09-17.md` |
| Pathway matrix | `issue-201-current-vs-a2-scene-data-pathway-matrix.md` |
| G2 A2 spec | `issue-201-g2-a2-redesign-specification-2026-09-15.md` |
| Packages A–C | `issue-201-packages-abc-investigation-2026-09-14.md` |
| Package D final | `issue-201-package-d-final-synthesis-first-principles-architecture-2026-09-15.md` |
| Runtime catalog | `v2/rp_runtime/src/application/llm-call-catalog.mjs`, `docs/architecture.md` |
