# Holy Grail System Product Requirements Document (Master PRD)

## Multi-Agent Narrative Simulation System

---

## Purpose

Build a multi-agent narrative simulation system where AI-controlled characters interact in persistent, structured scenes with high fidelity to identity, relationships, world knowledge, and continuity.

The system evolves from a card-based scene model into a knowledge-driven architecture powered by:

- structured state
- packetized runtime memory
- selective retrieval
- graph-backed narrative knowledge

---

## Core Goals

### Primary Goals

- maintain high character fidelity
- support persistent resumable scenes
- enable multi-character continuity
- enforce deterministic orchestration
- support scalable knowledge ingestion

---

### Secondary Goals

- reduce prompt-only inference
- reduce brittle semantic heuristics
- support graph-backed knowledge systems
- support long-term narrative memory

---

# System Architecture

The system consists of three primary layers.

---

# Layer 1 — Knowledge Ingestion Layer

Purpose:

Build structured narrative knowledge.

Responsibilities:

- extract entities
- extract relationships
- extract events
- extract causality
- extract psychology
- extract world-state

Outputs:

- packet-compatible character knowledge
- packet-compatible relationship knowledge
- packet-compatible event knowledge
- packet-compatible world knowledge

Storage:

- graph database
- vector database

---

# Layer 2 — Packaging Layer

Purpose:

Transform knowledge and state into runtime packets.

Responsibilities:

- assemble runtime context
- score memory packets
- select memory packets
- activate memory channels
- compose memory tiers
- build runtime packets

Outputs:

- RuntimeCharacterPacket
- RuntimeScenePacket
- RetrievedContextBundle

Core ownership:

MemorySelectionEngine

---

# Layer 3 — RP Execution Layer

Purpose:

Execute live narrative simulation.

Responsibilities:

- turn selection
- orchestration
- character generation
- validation
- continuity updates
- audit logging

---

# Core Runtime Contracts

---

# RuntimeCharacterPacket

Contains:

- identity core
- voice guidance
- active scene context
- active issues
- relationship overlays
- memory packets
- knowledge constraints

Purpose:

Character runtime input.

---

# RuntimeScenePacket

Contains:

- participants
- environment
- scene phase
- active issues
- recent exact history
- scene grounding

Purpose:

Shared runtime state.

---

# RetrievedContextBundle

Contains:

- selected memory packets
- selected relationship packets
- selected world packets
- selected conflict packets

Purpose:

Bounded contextual retrieval.

---

# Core Runtime Systems

---

# Continuity Engine

Purpose:

Authoritative truth engine.

Responsibilities:

- track state
- track consequences
- track issue evolution
- track presence
- promote events

Rule:

Continuity is authoritative.

Memory is not authority.

---

# Director

Purpose:

Turn selection.

Responsibilities:

- choose next actor
- maintain pressure
- maintain progression

---

# Validation Layer

Purpose:

Reject invalid runtime output.

Responsibilities:

- duplicate detection
- presence validation
- structural validation
- future knowledge validation

---

# Audit Layer

Purpose:

Observability.

Tracks:

- selection
- validation
- continuity updates
- memory selection
- consequences

---

# Data Strategy

Current:

- static cards
- deterministic memory
- prompt-driven behavior

Target:

- packetized memory
- selective retrieval
- graph-backed knowledge
- compressed event memory

---

# Design Principles

- structure over prompting
- continuity over memory
- state over inference
- deterministic where possible
- retrieval is assistive
- knowledge is structured

---

# Success Criteria

Success means:

- stable long-form scenes
- continuity persistence
- coherent turn flow
- reduced repetition
- scalable memory
- scalable knowledge ingestion

---

# System Evolution Path

Current:

Static Cards

↓

Runtime Packets

↓

Selective Memory

↓

Structured Event Memory

↓

Knowledge-Driven Narrative Intelligence