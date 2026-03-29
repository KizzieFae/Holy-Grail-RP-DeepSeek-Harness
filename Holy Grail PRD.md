# Product Requirements Document (PRD)
## Multi-Agent Roleplay System with Knowledge-Driven Character Intelligence

---

## 1. Overview

### Purpose
Build a multi-agent roleplay (RP) system where AI-controlled characters interact in persistent, structured scenes with high fidelity to character identity, relationships, and world knowledge.

The system evolves from a **card-based, scene-forward model** into a **knowledge-driven architecture** powered by:
- structured state
- compiled character profiles
- dynamic retrieval
- graph/vector-backed knowledge

---

## 2. Core Goals

### Primary Goals
- Maintain **high character fidelity** (voice, knowledge, behavior)
- Support **persistent, resumable scenes**
- Enable **multi-character interaction with continuity**
- Ensure **deterministic orchestration and validation**
- Provide **scalable architecture for knowledge ingestion**

### Secondary Goals
- Reduce reliance on prompt-only inference
- Minimize brittle regex-based interpretation
- Enable future integration of:
  - graph databases (Neo4j)
  - vector retrieval
  - automated knowledge extraction from source material

---

## 3. High-Level Architecture

The system is divided into three primary layers:

### 3.1 Ingestion Layer (Future System)
Responsible for building structured knowledge.

**Responsibilities:**
- Extract entities, relationships, events from source material
- Store structured data in:
  - graph database (relationships)
  - vector database (semantic similarity)
- Compile character and world profiles

**Outputs:**
- Character cores
- Relationship profiles
- Event/memory datasets
- Voice examples

---

### 3.2 Packaging Layer (Critical Bridge Layer)

Responsible for transforming knowledge + state into runtime inputs.

**Responsibilities:**
- Assemble runtime context per turn
- Select relevant:
  - relationships
  - memories
  - world context
  - voice examples
- Combine with current scene state

**Outputs:**
- `RuntimeCharacterPacket`
- `RuntimeScenePacket`
- `RetrievedContextBundle`

---

### 3.3 RP Execution Layer (AutoGen Runtime)

Responsible for actual roleplay execution.

**Responsibilities:**
- Turn selection (Director)
- Orchestration
- Character response generation
- Validation and retry
- Continuity updates
- Audit logging

---

## 4. Key System Concepts

### 4.1 RuntimeCharacterPacket (Core Contract)

Defines all information a character receives per turn.

**Includes:**
- Identity core (stable traits)
- Voice/style guidance
- Current scene state
- Active issues/pressures
- Relationship overlays
- Retrieved memories/context
- Knowledge constraints

---

### 4.2 RuntimeScenePacket

Defines shared scene context.

**Includes:**
- Participants
- Environment
- Active issues
- Scene phase
- Recent events

---

### 4.3 RetrievedContextBundle

Dynamic, per-turn context.

**Includes:**
- Relevant past interactions
- Relationship highlights
- Emotional/behavioral patterns
- World knowledge snippets

---

## 5. Core Systems

### 5.1 Continuity Engine

Maintains authoritative state.

**Tracks:**
- scene state
- issue/pressure system
- presence (who is in scene)
- knowledge ownership
- consequences/events

**Responsibilities:**
- promote dialogue/actions to structured events
- update state deterministically
- enforce knowledge boundaries

---

### 5.2 Director (Turn Selection)

Selects next actor based on:
- active issues
- scene dynamics
- recent actions

Constraints:
- minimal logic complexity
- no prompt overloading
- no keyword heuristics

---

### 5.3 Orchestration Layer (Final Authority)

Determines final speaker using:

Priority order:
1. direct address
2. continuation override
3. Director selection
4. validation + reconciliation
5. progression override

---

### 5.4 Character Agents

Generate dialogue and actions.

Must:
- remain in-character
- respect knowledge boundaries
- escalate or respond appropriately
- maintain initiative

---

### 5.5 Validation Layer

Rejects invalid outputs:

Checks:
- presence violations
- must_remain violations
- duplicate dialogue
- knowledge violations (future)
- voice drift (future)

Supports:
- single retry behavior (targeted)

---

### 5.6 Audit System

Logs:
- turn selection
- validation events
- state updates
- issues and consequences

Purpose:
- debugging architecture
- regression tracking
- system calibration

---

### 5.7 Progression Advisory Layer (MVP)

A **minimal, deterministic, advisory-only** layer reduces **scene-level plateau / verbal stall** without becoming a second progression engine.

**What it does**

- Computes a bounded **`stall_score`** (0.0–1.0) from **existing** signals only: same-phase plateau snapshots, high or extreme tension, stable active issue statuses, and (optionally) low variety in recent structured-move consequence categories.
- Emits **`progression_advisory`** metadata (stall score, pressure band, template-sourced **recommended_channels**, human-readable **note**) for observability and prompt hints.
- **Template-grounded:** optional static **`progression_profile`** on scene templates (`advancement_channels`, `common_stall_pattern`); if absent, a small default profile is used. No runtime inference of channels.

**What it does not do**

- Does **not** add authoritative continuity or character state.
- Does **not** use LLMs for classification or stall detection.
- Does **not** enforce outcomes or override Director/orchestration decisions.

**Integration (prompts and beat-shift)**

- **Director:** when pressure is **high**, a short fixed **PROGRESSION ADVISORY** prefix is prepended to the Director selection prompt (JSON payload still omits hint keys; prefix is outside JSON).
- **Character:** when pressure is **high**, or **medium** while beat-shift is active, a short advisory suffix nudges concrete state change (action, movement, consequence, commitment)—not a hard rule.
- **Beat-shift:** a **single** unified stall path uses the same **`stall_score`** threshold (e.g. ≥ 0.6) alongside the existing short-user-message trigger; no separate duplicate plateau detector.

**Observability**

- Audit / debug output may include **`progression_advisory`** (scores, pressure, channels, **stall_components**) and logs when advisory text is injected or beat-shift sensitivity is engaged via stall score.

---

### 5.8 Scene Grounding Layer (MVP)

A **minimal, deterministic, read-only** projection of **settled in-scene truths** into prompts. Also referred to as **scene facts** or **scene locks** in engineering docs.

**Purpose**

- Preserve **logistics, object states, medical facts, and communication outcomes** that the fiction has already **established**, so the runtime does not **repeat questions**, **reset assignments**, or **escalate incoherently** against settled reality.
- **Anchor progression** (advisory + beat-shift) to **persistent scene reality** without creating a second narrative authority.

**Constraints (non-negotiable)**

- **Continuity remains the single source of truth.** Facts are **derived** from continuity outputs + **explicit deterministic rules** + optional **template/system seeds** — never from raw chat mining or LLM inference.
- **Read-only with respect to authority:** the layer **does not** mutate continuity blobs, **does not** mutate `CharacterState`, and **does not** control orchestration (no Director override).
- **Scene-local only:** facts are **cleared on scene end**; **capped** count; **allowlisted** keys per category.
- **Determinism:** no LLM classification; no fuzzy extraction from prose.

**Schema overview**

- Small **typed** record set: categories such as **`assignment`**, **`object_state`**, **`medical_status`**, **`communication_state`**, each with **closed** `key` + `value` shapes and a **deterministic one-line** `value_summary` for prompts.
- Full contract, promotion/invalidation rules, and prompt placement: **`autogen_rp/docs/scene-grounding-layer.md`**.

**Lifecycle rules (summary)**

- **Promotion:** after each continuity commit, structured signals (events, consequences, issue hooks) match **fixed promotion rules** → emit or update facts.
- **Supersession:** same `(category, key)` → new fact replaces old; chain via `supersedes`.
- **Invalidation:** **continuity wins** — if structured continuity contradicts a fact, **update or remove** the fact; on contradiction without structured signal, facts may lag until **extraction** improves (no LLM patch).
- **Pruning:** hard **max fact count**; drop lowest priority / oldest when over cap.

**Integration points**

- **Prompts:** concise **SETTLED SCENE FACTS** block for **Director** and **character** (and **Narrator** when needed), assembled by packaging/prompt builders.
- **Progression / anti-regression:** **orthogonal** — advisories suggest **change**; grounding states **what is already settled**. No shared writable state.
- **Issues:** remain authoritative for **open** pressure; facts may **mirror** resolved outcomes when rules tie resolution → fact.

**Non-goals (MVP)**

- Not a full memory system, not cross-session graph/vector truth, not LLM-based extraction, not a redesign of continuity or character cards, not anti-regression expansion.

---

## 6. Data Strategy

### 6.1 Current State (Phase 1)

- Static character cards
- Deterministic memory
- Prompt-based behavior

### 6.2 Target State

- Structured knowledge base
- Compiled character profiles
- Retrieval-driven context injection
- Reduced reliance on inference

---

## 7. Retrieval Strategy

### Role of Vector DB
Used for:
- similarity search
- retrieving relevant memories
- finding voice-consistent examples

Not used for:
- authoritative truth
- state tracking
- validation logic

---

### Retrieval Inputs
- relationship-linked events
- recent scene interactions
- emotionally similar moments
- character-specific patterns

---

### Constraints
- strict token budget
- relevance filtering
- deterministic gating before semantic ranking

---

## 8. Event-Based State Updates

Replace raw text interpretation with structured events.

Examples:
- `entered_scene`
- `exited_scene`
- `issue_advanced`
- `knowledge_revealed`
- `direct_address`
- `deflection`
- `escalation`

These events drive:
- continuity updates
- validation logic
- scene progression

---

## 9. Design Principles

- Prefer **structure over prompts**
- Prefer **state over re-interpretation**
- Use **AI only for bounded interpretation**
- Avoid keyword/regex-based semantic logic
- Separate **data, packaging, and execution**
- Keep runtime deterministic where possible
- Log everything important

---

## 10. Non-Goals (For Now)

- Full automation of ingestion pipeline
- Perfect semantic understanding of all text
- Fully autonomous narrative control
- Frontend polish (deferred)

---

## 11. Success Criteria

The system succeeds when:

- Characters remain consistently in-character across long sessions
- Scenes maintain continuity after reload
- Turn selection remains coherent and non-repetitive
- Scenes recover from **structural stalls** (repeated high-tension verbal loops) via **advisory** pressure and beat-shift sensitivity without corrupting continuity truth
- **Scene coherence over time:** **resolved facts** (logistics, medical agreements, object states, communication outcomes) **persist in prompts** via the **Scene Grounding** layer — **reduced repetition** and **fewer resets** of already-settled fiction, without a second authority competing with continuity
- Validation catches and corrects invalid outputs
- System scales to multi-character interactions
- New knowledge sources can be integrated without rewriting runtime

---

## 12. Future Extensions

- Graph-based relationship reasoning
- Advanced memory scoring (importance, emotional weight)
- Character personality modeling from extracted data
- Voice embedding / style modeling
- Multi-session long-term memory
- Tooling for content ingestion and verification

---

## 13. Summary

This system evolves from a **prompt-driven RP engine** into a **structured, knowledge-driven simulation framework**.

The key transition is:

**Static Cards → Runtime Packets → Retrieved Intelligence**

With:
- AutoGen as the execution engine
- Packaging layer as the control point
- Ingestion layer as the long-term intelligence source