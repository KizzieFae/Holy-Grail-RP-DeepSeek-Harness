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

## E. Progression Layer — manual behavioral validation suite

**Current phase:** **Manual behavioral validation**

**Status before starting this section:**

- [x] Progression design complete
- [x] Runtime implementation complete
- [x] Deterministic simulation coverage complete
- [x] Audit verification layer complete

**Purpose:** Validate how the implemented progression layer behaves in real scenes now that structural correctness is covered by automated tests. This section is about **behavioral validation**, not new feature design.

**What is already covered elsewhere:**

- `tests/test_progression_pressure.py` covers deterministic progression classification, debt, tiers, resets, no-op outcomes, and issue identity continuity rules.
- `tests/test_audit_progression_analysis.py` covers audit-side verification of classification, reset validity, plateau pressure, and fragmentation detection.

**What manual runs must answer:**

- [ ] Do scenes feel less comfortable staying static?
- [ ] Does escalation feel natural rather than forced?
- [ ] Does actor selection follow dominant unresolved pressure without collapsing character integrity?
- [ ] Do prompt hints support the structural layer without becoming the main mechanism?

**Known watch areas:**

- [ ] Issue identity continuity currently transfers debt only on exact structured fingerprint matches
- [ ] Early-scene reset behavior should be watched before dominant pressure is clearly established

**Overlap with §A:** The repeatable RP scenarios in **§A** are still the main source for progression observation. Use the checklist below during those runs (or clearly bounded replays) rather than creating a parallel testing track.

### Test execution guidelines

- [ ] Run each scenario independently or as a clearly bounded segment within a larger session
- [ ] Keep variables controlled
- [ ] Do not modify system behavior mid-test
- [ ] Capture audit output for each run
- [ ] Review both behavioral feel and `_audit_summary.json` `progression_analysis`

### Primary evidence to inspect

- [ ] `progression_analysis.turns[*].scene_classification`
- [ ] `progression_analysis.turns[*].issue_classifications`
- [ ] `progression_analysis.turns[*].reset_validation`
- [ ] `progression_analysis.turns[*].plateau_assessment`
- [ ] `progression_analysis.turns[*].pressure_targeting`
- [ ] `progression_analysis.turns[*].issue_identity_events`
- [ ] Runtime `progression_pressure` snapshots in audit metadata
- [ ] Advisory / beat-shift traces as supporting evidence only

### Test scenarios

#### 1. Baseline arrival scene

**Suggested cast:** Use **Kizzie** (demure, polite) rather than Harley for a lower-conflict baseline.

- [ ] Run scenario
- [ ] Observe introductions and orientation progression
- [ ] Observe a concrete setup beat (bunk / space assignment or equivalent)
- [ ] Confirm scene debt does not escalate prematurely
- [ ] Confirm no false reset or false progression credit appears in `progression_analysis`
- [ ] Confirm minimal or no intrusive pressure prompting

#### 2. Confined argument loop

- [ ] Run scenario
- [ ] Confirm a verbal loop forms
- [ ] Observe scene / issue debt rise across consecutive non-progressing turns
- [ ] Observe tiers escalate from Stable toward Unstable / Escalating / Forcing as applicable
- [ ] Confirm pressure targeting stays on the dominant unresolved issue
- [ ] Confirm the eventual reset only happens after meaningful structured change

#### 3. Strong user steer

- [ ] Run scenario
- [ ] Allow plateau to begin
- [ ] Inject short, strong user input
- [ ] Confirm beat-shift activation reason is visible when it occurs
- [ ] Confirm the next meaningful change is reflected through structured progression, not prompt text alone
- [ ] Verify actor selection supports execution on the pressured issue

#### 4. Silent observer case

- [ ] Run scenario
- [ ] Use passive observation input
- [ ] Confirm pressure does not escalate inappropriately when real structured progress is still occurring
- [ ] Confirm advisory does not over-trigger
- [ ] Confirm progression_analysis does not show false mismatches or false progression credit

#### 5. Real progress with continued tension

- [ ] Run scenario
- [ ] Ensure each turn includes real structured movement while tension stays high
- [ ] Confirm material or partial classification fits the observed structured deltas
- [ ] Confirm debt stays steady or resets only when justified
- [ ] Confirm pressure does not fight legitimate forward motion

#### 6. Early derail -> recovery

- [ ] Run scenario
- [ ] Introduce early destabilization
- [ ] Watch whether dominant pressure becomes clear quickly enough
- [ ] Confirm recovery produces justified reset behavior rather than accidental early reset
- [ ] Note any ambiguity around dominant issue selection for follow-up

#### 7. Issue identity continuity check

- [ ] Run a scene where the same underlying stalled pressure may reappear under a different issue id
- [ ] Confirm debt transfers only when the exact structured fingerprint matches
- [ ] Log fragmentation if the same pressure appears to split across ids without transfer
- [ ] Record whether the exact-match rule feels too strict in live usage

### Metrics tracking (each scenario)

- [ ] Record scene progression debt and tier
- [ ] Record highest issue debt and tier
- [ ] Record whether `progression_analysis` shows mismatches
- [ ] Record reset validation results
- [ ] Record plateau assessment
- [ ] Record pressure-targeting result
- [ ] Record issue-identity notes / fragmentation events
- [ ] Record advisory injection and beat-shift activation as secondary context

### Evaluation scorecard (rate 1–5, each scenario)

- [ ] Plateau resistance
- [ ] Naturalness of escalation
- [ ] Character fidelity under pressure
- [ ] Reset correctness
- [ ] Pressure targeting clarity

### Recommended execution order

1. Baseline arrival scene  
2. Confined argument loop  
3. Strong user steer  
4. Silent observer case  
5. Real progress with continued tension  
6. Early derail -> recovery  
7. Issue identity continuity check  

### Success criteria (manual behavioral validation)

- [ ] Plateau loops no longer remain comfortably static for long stretches
- [ ] Structured movement, not prose intensity alone, is what relieves pressure
- [ ] No systematic false resets or false progression credit appears in audits
- [ ] Character behavior remains consistent under elevated pressure
- [ ] Watch areas are either cleared or logged explicitly for follow-up

## F. Scene Grounding Layer (MVP) — implementation & validation

**Product:** [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8  
**Technical spec:** [autogen_rp/docs/scene-grounding-layer.md](../docs/scene-grounding-layer.md)

**Implementation order (when ready — follow technical spec):**

- [ ] Schema + `scene_grounding` session persistence + clear on scene end
- [ ] Promotion rules (initial allowlisted keys only) + unit tests
- [ ] Deterministic prompt block + Director / character injection (`prompt_builders` path)
- [ ] Invalidation / supersession + cap pruning + tests
- [ ] Narrow continuity extraction hooks (structured signals only; no LLM classification)

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