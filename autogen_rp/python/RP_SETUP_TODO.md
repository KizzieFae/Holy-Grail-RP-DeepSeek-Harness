# RP App - Step-by-Step Implementation (Updated)

**Goal**: A multi-agent roleplay system with strong continuity, deterministic orchestration, and future integration with knowledge-driven packet-based architecture.

This roadmap reflects the correct execution order:

1. Stabilize and validate the current runtime
2. Introduce the packet seam (no behavior change)
3. Validate again under packet alignment
4. Only then expand into retrieval
5. Only after that begin ingestion work

---

# Phase 0 — Stabilization & Validation (**complete — v1 checkpoint**; progression: `tests/Testing TODOs/progression layer validation status v1.md`, repo root `SCENARIO_VALIDATION_FRAMEWORK.md`; player-text perception closure: section **G** below)

## A. Structured scenario validation

- [x] Run 5–10 repeatable RP scenarios:
  - [x] one-on-one interaction
  - [x] emotional/relationship tension
  - [x] multi-character (3+ actors)
  - [x] long-session continuity
  - [x] reload-after-save

- [x] Ensure each scenario is reproducible

## B. Validate core behaviors

- [x] Turn selection correctness
- [x] Continuity integrity
- [x] Validation behavior
- [x] Character fidelity (no drift, no flattening)

## C. Failure classification

- [x] Log all failures via audit system
- [x] Categorize failures by layer:
  - [x] continuity
  - [x] orchestration
  - [x] validation
  - [x] prompt surface (last resort)

## D. Exit criteria

- [x] No recurring unclassified failures
- [x] All known failure types mapped to a layer
- [x] System behaves predictably across all test scenarios

---

## E. Progression Advisory Validation

- [x] Confirm plateau detection works
- [x] Confirm advisory triggers appropriately
- [x] Confirm beat-shifts introduce real state changes
- [x] Confirm no continuity corruption
- [x] Confirm characters remain consistent under pressure

---

## F. Scene Grounding Validation

- [x] Confirm settled facts do not re-litigate
- [x] Confirm grounding remains read-only
- [x] Confirm no unintended writes to continuity or character state

---

## G. Player-text perception & knowledge boundaries (Phase 0 closure)

- [x] Character prompts respect knowledge boundaries for **player** input (no global raw trigger for non-recipients)
- [x] All character-visible player text paths use **`perception_audibility`** rules:
  - [x] `TRIGGER FOR THIS BEAT`
  - [x] Beat-shift `LATEST PLAYER INPUT` (character suffix)
  - [x] User lines inside `RECENT SCENE TRANSCRIPT`
- [x] Scenario 1 — knowledge-boundary stress (`memory_private_directed`) **passes** (validated rerun: audit **`session_107`**)
- [x] Simulation pipeline matches Streamlit: same `app_turn_prompting` / `build_recent_dialogue_history_for_viewer` path; audits reflect **filtered** character system prompts
- [x] Director unchanged: full raw trigger and unfiltered user lines in orchestration transcript (`viewer_character_name=None`)
- [x] All **confirmed** Phase 0 runtime blockers resolved (including global player-trigger knowledge leak)

**Not claimed complete in Phase 0** (explicit follow-up, not blockers):

- [ ] Tighter **ambiguity** handling (MVP: ambiguous player input defaults to **public**)
- [ ] **Heuristic** improvements for whisper / directed inference on free-text player lines
- [ ] **Narrator** alignment with player-text perception boundaries
- [ ] Additional **memory** scenarios / memory-layer validation beyond existing checks

### Phase 0 completion note — player-text visibility

The Phase 0 blocker **character prompt knowledge leak from global player trigger visibility** is **closed**. Implementation: recipient-filtered player text via **`player_text_for_character_viewer`** in `perception_audibility.py`, invoked from **`app_turn_prompting`** (per-character trigger + beat-shift suffix) and **`build_recent_dialogue_history_for_viewer`** (user transcript lines). **Director** still receives the full raw trigger for selection. **MVP limitation:** ambiguous player input remains **public** by default to avoid over-redaction; revisit in a later phase.

---

# Phase 0.5 — Packet Seam Introduction (NO BEHAVIOR CHANGE)

**Goal**: Introduce a structured runtime interface (packets) without changing system behavior.

---

## A. Freeze baseline behavior

- [ ] Select 2–3 canonical test scenarios
- [ ] Save audit outputs for comparison
- [ ] Record expected:
  - [ ] turn selection
  - [ ] progression behavior
  - [ ] grounding behavior
  - [ ] continuity behavior

- [ ] Guardrails:
  - [ ] No changes to:
    - [ ] turn_runner*
    - [ ] app_turn_director.py
    - [ ] response_validation*
    - [ ] progression_enforcement.py
  - [ ] Changes limited to:
    - [ ] packet builders
    - [ ] prompt assembly glue

---

## B. Define packet structures

### ScenePacket

- [ ] template_id
- [ ] premise / opening_text
- [ ] location / time
- [ ] progression_profile
- [ ] role_slots / constraints

Runtime fields:
- [ ] present_characters
- [ ] offstage_characters
- [ ] scene_phase
- [ ] tension level
- [ ] recent events / delta

---

### CharacterPacket

Static:
- [ ] name / description
- [ ] personality / voice
- [ ] goals
- [ ] lore facts

Runtime:
- [ ] current_objective
- [ ] short_term_tactic
- [ ] emotional_state
- [ ] stress_level

---

### CharacterRuntimeContextPacket

- [ ] active issues
- [ ] recent public events
- [ ] summary blocks
- [ ] canon anchors
- [ ] interpretations
- [ ] filtered dialogue
- [ ] filtered moves
- [ ] scene grounding

---

### RetrievedContextBundle (stub)

- [ ] Exists but empty
- [ ] No retrieval logic yet

---

## C. Build packet builders

- [ ] `build_runtime_scene_packet(...)`
- [ ] `build_runtime_character_packet(...)`
- [ ] `build_character_runtime_context_packet(...)`

Sources:
- [ ] templates
- [ ] character cards
- [ ] continuity_manager
- [ ] character_state_manager
- [ ] perception filtering
- [ ] scene grounding

---

## D. Shadow-mode integration

- [ ] Generate packets alongside current prompt inputs
- [ ] Do NOT replace prompt builder yet

- [ ] Create adapters:
  - [ ] packet → prompt inputs

- [ ] Compare:
  - [ ] scene state
  - [ ] issues
  - [ ] summaries
  - [ ] grounding
  - [ ] dialogue windows
  - [ ] role mappings

- [ ] Log mismatches only

---

## E. File-level integration

### app_turn_prompting.py

- [ ] Entry point for packet building
- [ ] Shadow comparison logging

### prompt_builders.py

- [ ] Validate packet completeness

### character_state_manager.py

- [ ] Source runtime state (no changes)

### continuity_manager.py

- [ ] Source truth data (no logic changes)

### scene_grounding.py

- [ ] Provide grounding into packet

### app_turn_director.py

- [ ] Reference only (no edits)

---

## F. Data separation enforcement

- [ ] Scene owns:
  - [ ] situation
  - [ ] pressure
  - [ ] constraints

- [ ] Character owns:
  - [ ] voice
  - [ ] goals
  - [ ] behavior

- [ ] Remove duplication at packet level (no prompt edits yet)

---

## G. Validation

- [ ] Re-run baseline scenarios
- [ ] Compare:
  - [ ] audit outputs
  - [ ] narrative outputs
  - [ ] progression metrics

- [ ] Track mismatches:
  - [ ] missing fields
  - [ ] duplication
  - [ ] filtering errors
  - [ ] grounding mismatch

---

## H. Exit criteria

- [ ] Packets fully represent runtime inputs
- [ ] No behavior drift
- [ ] Prompt inputs reproducible from packets
- [ ] Director / validation unchanged

---

# Phase 1 — Packet-Aligned Runtime Validation

- [ ] Re-run all scenarios
- [ ] Confirm no regressions
- [ ] Validate packet completeness

**Exit criteria:**
- [ ] Stable behavior
- [ ] Packet structure confirmed

---

# Phase 2 — Retrieval (Controlled Introduction)

## HARD GATE

- Phase 0 + 0.5 complete

## Implementation

- [ ] Add bounded vector retrieval
- [ ] Inject into RetrievedContextBundle only
- [ ] Do NOT affect continuity or validation

## Evaluation

- [ ] Measure usefulness
- [ ] Monitor token cost
- [ ] Confirm no corruption

---

# Phase 3 — Ingestion System (Deferred)

## HARD GATE

- Retrieval proven
- Packet interface stable

## Steps

- [ ] Extract structured knowledge from sources
- [ ] Store in:
  - [ ] graph DB
  - [ ] vector DB

- [ ] Compile:
  - [ ] character profiles
  - [ ] relationships

- [ ] Feed into packet builders

---

# Core Principles

## Data Separation Principle

- Scene = situation / pressure / constraints
- Character = behavior / goals / voice

Static inputs remain stable:
- scene templates
- character cards
- initial messages

Packets:
- normalize inputs
- remove duplication
- prepare for retrieval

Packets do NOT change behavior.

---

## General Principles

- Fix correct layer, not symptoms
- Prefer structure over prompt tweaks
- Continuity is authoritative truth
- Retrieval is assistive only
- Maintain determinism where possible
- Avoid premature complexity

---

# Summary

Current phase:

→ Phase 0 (Validation)

Next:

→ Phase 0.5 (Packet seam)

Do NOT proceed to retrieval or ingestion until both are complete and validated.