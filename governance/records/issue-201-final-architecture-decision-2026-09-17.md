# Issue #201 — Final Architecture Decision (Governance accepted 2026-09-17)

**Parent Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Synthesis basis:** `governance/records/issue-201-whole-system-architectural-synthesis-2026-09-17.md` (`32cbfaa`)  
**Decision status:** **Accepted** — durable architecture decision; **not** production implementation

---

## 1. Governing question (answered for assessment)

> If Holy Grail were designed today from first principles, which RP turn components would we deliberately build again?

**Answer:** **A2** — deterministic substrate + primary RP cognition (Character/Director/Narrator logical roles) + **persistent Plot/Scribe off the default synchronous critical path**, with **obligation-driven** support cognition. **Not** the current A4 always-on synchronous stack as the target.

---

## 2. Accepted decisions (normative)

### Deterministic substrate — deliberately rebuild

Continuity / authoritative state; commit semantics; PVR / perceptual entitlement; structural validation; auditability; bounded projection; retrieval/indexing; obligation routing and deterministic gating where appropriate.

### Primary RP cognition — deliberately rebuild

Character, Director, Narrator **logical responsibilities** with authority boundaries preserved (Character committed action; Director beat/actor selection; Narrator presentation-only; Continuity authoritative commit; advisory ≠ authority). Physical LLM call consolidation permitted only if boundaries remain enforceable and auditable.

### Plot/Scribe — retain capability; change default topology

**Demonstrated:** R0–R4 (generation/storage, projection, semantic receipt, use, decision influence).  
**R5 marginal factual-retention value:** **not demonstrated**; **unresolved**; **architecturally non-blocking**.  
**Default:** persistent Plot/Scribe **not** mandatory synchronous per-turn critical path; prefer async/off-path with explicit projection/escalation. **Not** deletion of capability.

### Storyteller-class — do not rebuild always-on sync stack

No mandatory synchronous preamble, post-commit pressure pass, or equivalent per-turn Storyteller stack. Broader Storyteller responsibilities (planning, dormant threads, salience, foreshadow, relationship trajectory, premature-resolution avoidance) remain **partially tested** and **not decision-critical** for A2. **No new #201 experiments** for them.

### Conditional support cognition

Librarian mediation, environmental cognition, orientation, semantic repair/QA, and similar checking → **obligation-driven / tiered**, not always-on.

### Not justified as mandatory per-turn mechanisms

Storyteller sync preamble; Storyteller post-commit pressure; always-on Director semantic QA; always-on Narrator semantic QA; routine Librarian mediation; always-on environmental cognition; always-on orientation; stacked check/repair/summarize without obligation triggers.

### A4 disposition

**Migration baseline, not target architecture.** Not every A4 mechanism is intrinsically harmful; the **complete always-on synchronous stack** has not earned first-principles retention.

---

## 3. Information-aging program — formal stop

**Stopped by Governance** after diminishing architectural return.

- Persistence through **R4** demonstrated; **R5 not demonstrated**; **R5 not disproven**.
- run2: absence vs forgetting; establishment defects; remediation (`5b3b65c` / `e2575ea`).
- run3: valid unilateral establishment Stop C; no valid R5/R5-null.
- Further aging would require **story entry/establishment redesign** — **declined** (R5 not decision-critical).
- **No reopen** under #201 for R5 chase.

---

## 4. Migration principle

Goal: **simplify architecture while preserving RP outcomes and invariants** (#201), not merely minimize LLM calls.

**Migration invariants** (minimum): Character agency; Director selection authority; Narrator rendering separation; Continuity authoritative commit; scenario authority; role-private boundaries; PVR; retrieval when needed; deterministic validation; semantic repair when genuinely required; auditability; no silent advisory→authority promotion.

---

## 5. Handoff

Implementation decomposed into **child Issues** (Tracks A–D) under A2 migration phase. See `governance/records/issue-201-a2-migration-handoff-2026-09-17.md`.

**Scene data-pathway map (current production vs accepted A2 target):** `governance/records/issue-201-current-vs-a2-scene-data-pathway-matrix.md` — canonical pre-migration reference for #209–#212; Governance review before #201 closure / #209 activation.

**Next-generation architecture foundation (WIP design thesis):** `governance/records/issue-201-next-generation-rp-architecture-foundation.md` — principal reasoning document for post-#201 design; migration Issues paused pending fresh-context review.

---

## 6. #201 lifecycle (canonical)

- **Do not** use invented state `architecture_decision_recorded`.
- **Remain OPEN** at **`Current status: consensus_reached`** until Governance evaluates **closure** after handoff (assessment deliverable complete; implementation tracked on children).
- **Do not** set **`implemented`** for architecture decision alone.
