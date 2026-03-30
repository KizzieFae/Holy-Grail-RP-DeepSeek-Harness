# RP App - Step-by-Step Implementation (Updated)

**Goal**: A multi-agent roleplay system with strong continuity, deterministic orchestration, and future integration with knowledge-driven packet-based architecture.

This roadmap reflects the correct execution order:

1. Stabilize and validate the current runtime
2. Introduce the packet seam (no behavior change)
3. Validate again under packet alignment
4. Only then expand into retrieval
5. Only after that begin ingestion work

---

# Phase 0 — Stabilization & Validation (CURRENT PRIORITY)

**Goal**: Prove the current system is correct, stable, and debuggable using the new documentation and audit workflow.

## A. Structured scenario validation

- [ ] Run 5–10 repeatable RP scenarios:
  - one-on-one interaction
  - emotional/relationship tension
  - multi-character (3+ actors)
  - long-session continuity
  - reload-after-save
- [ ] Ensure each scenario is reproducible
- [ ] For **Progression Advisory / plateau** validation, drive **§E** from these same runs where a scenario aligns (argument loop, short user steer, passive observation, etc.)—no separate duplicate scenario matrix required.

## B. Validate core behaviors

- [ ] Turn selection correctness:
  - direct address honored
  - continuation override holds
  - progression override does not overfire
- [ ] Continuity integrity:
  - issues persist and evolve correctly
  - events are promoted correctly
  - knowledge boundaries enforced
- [ ] Validation behavior:
  - duplicate dialogue triggers single retry
  - no permanent skipped turns
  - presence (`must_remain`) enforced correctly
- [ ] Character fidelity:
  - no long-session drift
  - no personality flattening

## C. Failure classification

- [ ] Log all failures via audit system
- [ ] Categorize failures by layer:
  - continuity
  - orchestration
  - validation
  - prompt surface (last resort)
- [ ] Fix only at the correct layer (see DEBUGGING_GUIDE.md)

## D. Exit criteria

- [ ] No recurring unclassified failures
- [ ] All known failure types mapped to a layer
- [ ] System behaves predictably across all test scenarios

## E. Progression Advisory Layer — plateau test suite (manual / audit)

**Purpose:** Validate deterministic **stall signals**, **advisory injection**, and **beat-shift** behavior using live sessions and audits. This is **manual / qualitative** where noted; automated wiring is covered by `tests/test_progression_advisory.py` and related tests.

**Overlap with §A:** The repeatable RP scenarios in **§A** are the usual sessions that surface plateau issues; use the checklist below during those runs (or targeted replays) instead of inventing parallel scenarios.

### Test execution guidelines

- [ ] Run each scenario **independently** (or as a clearly bounded segment within a §A run)
- [ ] Keep variables controlled
- [ ] Do **not** modify system behavior mid-test
- [ ] Capture **audit output** for each run
- [ ] Evaluate both **mechanical signals** (scores, logs) and **scene quality** (subjective)

### Test scenarios

#### 1. Baseline arrival scene

**Suggested cast:** Use **Kizzie** (demure, polite) rather than Harley—aims for a **low-conflict** baseline so `stall_score` and advisory stay naturally subdued.

- [ ] Run scenario
- [ ] Observe introductions occur
- [ ] Observe orientation progression
- [ ] Observe bunk/space assignment (or equivalent concrete setup beat)
- [ ] Check `stall_score` remains low / moderate
- [ ] Confirm minimal or no advisory injection
- [ ] Confirm no forced or unnatural shifts

#### 2. Confined argument loop

- [ ] Run scenario
- [ ] Confirm loop forms (verbal escalation pattern)
- [ ] Observe `stall_score` increase
- [ ] Observe `progression_pressure` reach high
- [ ] Confirm advisory activation
- [ ] Confirm next beat introduces **state change**
- [ ] Verify change is **structural** (not only tone)—subjective rating

#### 3. Strong user steer

- [ ] Run scenario
- [ ] Allow plateau to begin
- [ ] Inject short, strong user input
- [ ] Confirm beat-shift activation (and note **reason** in audit: short message vs `progression_stall`)
- [ ] Confirm advisory alignment
- [ ] Confirm next turn executes concrete action
- [ ] Verify actor selection supports execution
- [ ] Verify beat type changes—subjective rating

#### 4. Silent observer case

- [ ] Run scenario
- [ ] Use passive observation input
- [ ] Confirm advisory does **not** over-trigger
- [ ] Confirm natural progression continues
- [ ] Verify `stall_score` is not inflated incorrectly

#### 5. Real progress with continued tension

- [ ] Run scenario
- [ ] Ensure each turn includes real state change
- [ ] Confirm `stall_score` remains moderate or drops
- [ ] Confirm advisory does not interfere inappropriately
- [ ] Verify system recognizes progress correctly—subjective rating

#### 6. Early derail → recovery

- [ ] Run scenario
- [ ] Introduce early destabilization
- [ ] Confirm derailment occurs
- [ ] Observe stall detection timing
- [ ] Confirm system transitions out of loop
- [ ] Verify progression resumes via a new channel—subjective rating

#### 7. Template fit check

- [ ] Run **dorm arrival** (or similar) template with a known `progression_profile`
- [ ] Verify appropriate progression channels appear in advisory metadata when pressure is high
- [ ] Run a **confrontation** (or second) template with a **distinct** `progression_profile` *when authored*; otherwise skip or mark N/A
- [ ] Confirm recommendations match the **template** channels (static profile—not inferred)

### Metrics tracking (each scenario)

- [ ] Record `stall_score` progression
- [ ] Record `progression_pressure`
- [ ] Log advisory injection (Director / Character)
- [ ] Log beat-shift activation **reason**
- [ ] Count turns before state change
- [ ] Tag dialogue-only vs state-changing turns—subjective where needed

### Evaluation scorecard (rate 1–5, each scenario)

- [ ] Plateau detection accuracy
- [ ] Scene advancement quality
- [ ] Character fidelity
- [ ] Naturalness of transition
- [ ] Over-triggering / under-triggering

### Recommended execution order

1. Baseline arrival scene  
2. Confined argument loop  
3. Strong user steer  
4. Silent observer case  
5. Real progress with continued tension  
6. Early derail → recovery  
7. Template fit check  

### Success criteria (Progression Advisory MVP)

- [ ] Plateau loops break **earlier** than pre-advisory baseline—subjective / comparative
- [ ] Scene advances through **concrete** state changes when stuck
- [ ] Advisory triggers **appropriately** (not constantly)
- [ ] Character behavior remains consistent
- [ ] **No continuity corruption** (advisory remains non-authoritative)

## F. Scene Grounding Layer (MVP) — validation

**Product:** [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8  
**Technical spec:** [autogen_rp/docs/scene-grounding-layer.md](../docs/scene-grounding-layer.md)

**Current baseline:** Scene grounding is already implemented in the current validation/stabilization phase. Use the technical spec and the checks below to validate the existing read-only grounding path rather than treating it as future implementation work.

**Validation:**

- [ ] Replay or manual runs: settled logistics / facts do not **re-litigate** once continuity has promoted them (see dorm audit examples: bunk, suppressants)
- [ ] Audits: grounding snapshot or injection metadata when enabled ([AUDIT_DOCUMENTATION.md](./rp_app/AUDIT_DOCUMENTATION.md))
- [ ] Confirm: **no** writes to continuity blobs or `CharacterState` from grounding code paths

---

# Phase 0.5 — Packet Seam Introduction (NO BEHAVIOR CHANGE)

**Goal**: Introduce the packaging layer interface without altering runtime behavior.

This is the bridge to the PRD architecture.

## A. Define packet builders

- [ ] Create:
  - `build_runtime_character_packet(...)`
  - `build_runtime_scene_packet(...)`
- [ ] Source data from:
  - character cards
  - continuity state
  - existing prompt inputs

## B. Map current system → packet structure

- [ ] Identity → Identity core
- [ ] Continuity → Scene-facing slice
- [ ] Relationships → Relationship overlays
- [ ] Existing summaries → RetrievedContextBundle (stub, no retrieval yet)

## C. Shadow mode validation

- [ ] Generate packets alongside current prompt inputs
- [ ] Compare:
  - existing prompt inputs
  - packet-derived inputs
- [ ] Ensure equivalence (no behavior drift)

## D. Constraints

- [ ] Do NOT modify:
  - Director logic
  - orchestration flow
  - validation system
- [ ] Do NOT introduce:
  - retrieval
  - vector search
  - ingestion inputs

## E. Exit criteria

- [ ] Packets fully represent current runtime inputs
- [ ] No change in system behavior
- [ ] Packet layer is ready to become runtime input source

---

# Phase 1 — Packet-Aligned Runtime Validation

**Goal**: Ensure system remains stable when conceptually aligned to packet structure.

## A. Re-run validation scenarios

- [ ] Repeat all Phase 0 scenarios (including **Phase 0 §E** plateau/advisory checks where relevant)
- [ ] Confirm:
  - no regressions
  - no drift introduced by packet mapping

## B. Audit packet quality

- [ ] Verify:
  - correct data inclusion
  - no missing context
  - no redundant or bloated fields

## C. Refine packet structure

- [ ] Adjust field grouping if needed
- [ ] Ensure:
  - clear separation of authoritative vs retrieved
  - stable vs dynamic fields are cleanly divided

## D. Exit criteria

- [ ] Packet structure validated against real scenarios
- [ ] Ready to support retrieval inputs

---

# Phase 2 — Retrieval (Controlled Introduction)

**Goal**: Introduce semantic retrieval safely through the packet layer.

## HARD GATE

Do NOT begin until:
- Phase 0 and 0.5 are complete
- Packet structure is stable

## A. Retrieval prototype

- [ ] Implement vector search for:
  - past interactions
  - relationship-relevant moments
- [ ] Keep retrieval:
  - bounded
  - optional
  - non-authoritative

## B. Integration point

- [ ] Inject ONLY into:
  - `RetrievedContextBundle`
- [ ] Do NOT:
  - modify continuity
  - override state truth
  - affect validation directly

## C. Evaluation

- [ ] Measure:
  - relevance of retrieved context
  - impact on character fidelity
  - token cost vs value

## D. Exit criteria

- [ ] Retrieval improves output quality
- [ ] No corruption of continuity or orchestration
- [ ] Retrieval remains bounded and controlled

---

# Phase 3 — Ingestion System (Deferred)

**Goal**: Build structured knowledge pipeline for characters and world data.

## HARD GATE

Do NOT begin until:
- Retrieval is proven useful
- Packet interface is stable

## A. Extraction

- [ ] Parse source material into:
  - characters
  - relationships
  - events
  - world knowledge

## B. Storage

- [ ] Graph DB (relationships)
- [ ] Vector DB (semantic retrieval)

## C. Compilation

- [ ] Build:
  - character profiles
  - relationship summaries
  - memory datasets

## D. Integration

- [ ] Feed outputs into:
  - packaging layer
  - packet builders

## E. Exit criteria

- [ ] Ingested knowledge improves RP quality
- [ ] No disruption to runtime stability
- [ ] Clear separation of:
  - authoritative state (continuity)
  - external knowledge (retrieval)

---

# Core Principles (Enforced Throughout)

- Fix the correct layer, not symptoms
- Prefer structure over prompts
- Continuity is authoritative truth
- Retrieval is assistive, never authoritative
- Keep runtime deterministic where possible
- Avoid premature complexity
- Do not expand system surface before stabilizing base

---

# Summary

You are currently in:

→ Phase 0 (Stabilization & Validation), including **§E** (Progression Advisory plateau checklist—manual/audit, layered on **§A** runs)

The next critical milestone is:

→ Phase 0.5 (Packet Seam Introduction)

Do not proceed to retrieval or ingestion until both are complete and validated.