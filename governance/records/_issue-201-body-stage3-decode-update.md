## Summary

Holy Grail RP now produces **multi-minute successful rounds** (repeat-F06: R1 **156.8s**, R2 **192.6s**) with **38/38 successful inferences, zero retries, and no material error budget**—yet output remained stiff, narratively subpar, and affected by two separate semantic violations (**#199**, **#200**). Historical user-observed waits were roughly **30–60s**. Recent optimizations (#165, #166, #173–#176, #194, #197) improved portions of F06 but did not close the usability gap.

This Issue authorizes a **first-principles whole-system architecture value assessment**: not latency optimization of the current topology, but determining which synchronous RP-turn components justify their existence, placement, complexity, and maintenance cost.

**Finding class:** `architectural debt`  
**Recommended disposition:** `remediation_tracked`  
**Source audit:** Repeat F06 Latency + Quality Causal Audit (Implementation-AI, read-only, 2026-09-14)

## Type

design_gap

## Layer

orchestration

## Pattern status

single_instance

## Workflow weight

full

## Current status

investigating

## Execution anchor

- Primary evidence session: `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311`
- Historical comparison: `hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40`
- Investigation activation SHA: `43db105401769750980bdc214666424fa11985cb`
- Package D control substrate SHA: `c751ea666f0cae6524698005aa5859721c2e9738` (post-#206 / PR #207)
- Package D D0 evidence: `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/`
- Package D Stage-2 evidence: `data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/`
- Package D Stage-3 evidence: `data/investigation_runs/issue201-package-d-stage3-2026-09-14T18-16-06-752Z/`
- Stage-2 synthesis: `b391336` — `governance/records/issue-201-package-d-stage2-synthesis-2026-09-14.md`
- Stage-3 execution SHA: `42be339` — `governance/records/issue-201-package-d-stage3-preamble-decomposition-2026-09-14.md`
- Stage-3 decode synthesis: `governance/records/issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` (pending commit SHA)
- Packages A–C record: `governance/records/issue-201-packages-abc-investigation-2026-09-14.md`

## Execution snapshot

**Package D Stage 3 complete — preamble decomposition decoded (2026-09-14).**

**Assigned / effective workflow weight:** `full`  
**Required bootstrap:** Full (`docs/issue-bootstrap-profiles.md`)

**Completed Package D milestones:**

| Milestone | Status |
|-----------|--------|
| Packages A–C | Accepted |
| D0 baseline | Accepted |
| Stage-2 tranche 1 (EXP-1/2/3) | Accepted (`b391336`) |
| Governance blind eval (Stage-2) | Locked, decoded |
| Stage-3 preamble decomposition (D-01a + D-01b) | Executed (`42be339`) |
| Governance blind eval (Stage-3) | Locked, decoded |

**Stage-3 decoded 2×2 matrix (locked means; small-N):**

| Cell | ST | Plot | Overall | Δ vs D0 |
|------|:--:|:----:|--------:|--------:|
| D0 | ON | ON | 4.475 | — |
| D-01b | OFF | ON | 4.363 | −0.113 |
| D-01a | ON | OFF | 4.203 | −0.272 |
| D-01 | OFF | OFF | 4.158 | −0.318 |

**Stage-3 provisional classifications (Governance-accepted pending formal sign-off):**

- **Plot cognition:** Retain function — demonstrated marginal immediate-turn RP value; architecture/topology unresolved
- **Storyteller cognition:** Weak/conditional immediate-turn marginal value; longitudinal test required before tier/removal decision
- **EXP-2 / D-06:** Unchanged — combine/remove candidate
- **EXP-3 / D-03:** Unchanged — complexity-tier candidate

**Next proposed tranche (NOT authorized):** **D-01-L** — longitudinal Storyteller value test (Plot ON; Storyteller ON vs OFF; multi-turn Arkham + Ayame arcs). See decode synthesis record.

**Deferred:** D-10 post-commit join — pending longitudinal Storyteller gate.

**Explicit prohibitions:** no production redesign/remediation; no preamble production tiering; no D-10/Librarian/PVR/compact-topology ablations without Governance gate; no Packages E–G synthesis unless separately authorized.

### User sequencing decision (binding — historical record preserved)

1. **Create all three Issues now** (**#199**, **#200**, **#201**).
2. **Remediate and validate** the two correctness defects (**#199**, **#200**) first.
3. **Then execute** this whole-architecture assessment (**#201**).
4. **Only after assessment consensus** should architectural redesign/optimization implementation begin.

**Prerequisite gate status (2026-09-14):** **SATISFIED.** **#199** closed (PR #202). **#200** closed (PR #203).

Priority **P1** does **not** override this phase sequence.

## Evidence (mandatory)

- **Scenario ids:** `arkham_asylum_mess_hall_arena`, `ayame_household_entry_evaluation`
- **Package D evidence roots:** see Execution anchor
- **Turn index:** n/a (program assessment; per-session turn indexes in corpus)

## Evidence (preferred)

Repeat-F06 audit; Package D causal ablation tranches; blind semantic evaluation records under `governance/records/issue201-stage{2,3}-*`.

## Expected behavior

Governance can answer for **every material synchronous RP-turn component**: why it exists, what unique value it provides, what it costs, what evidence supports that value, and whether that value justifies its current form and placement.

## Observed behavior

Current architecture stacks enough **successful** serial and parallel cognition to produce ~2.5–3+ minute rounds. Package D ablations are measuring which layers contribute measurable architectural work and RP quality.

## Deterministic reasoning

Latency expansion correlates with added cognition layers documented in execution evidence—not with retry pathology in baseline sessions.

## System impact

Operator RP experience unacceptable for live play; maintenance burden and information-handoff risk increase with layer count.

## Constraints

Assessment must **not** be framed as latency-only optimization or default parallelization.

**Hard requirements to preserve** (outcomes, not mechanisms): authoritative continuity/state; Player agency; perceptual/knowledge boundaries; role-private knowledge; Character identity/fidelity; coherent environmental grounding; auditability; deterministic authority for objective legality; scenario premise authority; strong NPC agency; high-quality natural RP prose.

Do not implement candidate architectures during assessment phase.

## Affected modules

End-to-end RP turn pipeline: `v2/rp_runtime/`, `v2/domain/`, `v2/domain_api/`, execution evidence instrumentation on critical path.

## Governing assessment question

> **If Holy Grail were being designed today from first principles, with the project's current requirements and everything learned from implementation and live sessions, which components of the existing RP turn architecture would we deliberately choose to build again?**

## Required assessment scope

(Sections 1–23 deliverable framework unchanged — see original Issue body.)

## Validation criteria

1. Deliverable sections 1–23 recorded on Issue (or linked durable governance record) with evidence citations.
2. Corpus coverage documented; gaps labeled honestly.
3. Explicit disposition recommendation per major component.
4. Candidate architectures compared without implementation.
5. Assessment execution begins only after **#199** and **#200** reach validated remediation. **Gate satisfied.**

## Documentation

- [ ] Documentation reviewed and updated where assessment changes architecture contracts (post-assessment phase only)

## Related work

- **#199** — completed prerequisite (closed PR #202)
- **#200** — completed prerequisite (closed PR #203)
- **#206** — manifest policy parity (resolved before D0)
- **#112**, **#136**, **#194** — narrower-scope inputs

## Next step

Governance review of Stage-3 decode synthesis; authorize or revise **D-01-L** longitudinal Storyteller proposal. Remain at `investigating`. No production redesign.
