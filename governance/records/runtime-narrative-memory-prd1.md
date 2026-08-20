> **HISTORICAL RECORD** — Not current operational authority. Preserves program/planning evidence from an earlier phase. For current product architecture see `governance/sources/holy-grail-prd.md` and `governance/sources/architecture-overview.md`.

# Runtime Narrative Memory Product Requirements Document

## Adaptive Narrative Memory Runtime (ANMR)

---

## Purpose

Evolve the Holy Grail runtime into a hierarchical selective memory architecture.

This system improves runtime memory quality without increasing prompt instability.

---

## Problem Statement

Current strengths:

- continuity authority
- structured moves
- bounded retrieval
- deterministic orchestration

Current weaknesses:

- static retrieval
- weak relevance scoring
- flat memory weighting
- reactive instability handling

Goal:

Build selective hierarchical runtime memory.

---

# Product Goals

---

# Goal 1 — Hierarchical Runtime Memory

Create three memory tiers.

---

## Tier 1 — Active Window

Purpose:

Exact recent context.

Contains:

- recent dialogue
- recent actions
- unresolved exchanges

Properties:

- exact fidelity
- short-lived

---

## Tier 2 — Scene Event Memory

Purpose:

Compressed scene history.

Contains:

- event packets
- relationship deltas
- consequence deltas
- scene commitments

Properties:

- structured
- compressed
- retrievable

---

## Tier 3 — Canonical Continuity State

Purpose:

Authoritative stable truth.

Contains:

- resolved outcomes
- stable truths
- durable world facts
- durable relationship state

Properties:

- authoritative
- persistent

Rule:

Not memory.

Truth.

---

# Goal 2 — Retrieval Gating

Replace broad retrieval with scored retrieval.

Scoring:

- goal relevance
- emotional relevance
- relationship relevance
- location relevance
- conflict relevance
- continuity relevance

Deliverable:

MemorySelectionEngine

Owner:

Packaging Layer

---

# Goal 3 — Memory Channelization

Separate memory domains.

Channels:

- relationship
- character
- world
- conflict
- continuity

Goal:

Selective activation.

---

# Goal 4 — Event Compression

Transform runtime events into event packets.

Required fields:

- actor
- target
- action
- emotional shift
- consequence shift
- relationship delta
- scene delta

Goal:

Meaning-preserving compression.

---

# Goal 5 — Adaptive Recovery

Detect instability.

Signals:

- repetition
- escalation stall
- contradiction pressure
- identity drift

Recovery:

- widen retrieval horizon
- reinforce grounding
- reinforce relationship memory
- reinforce conflict memory

---

# Functional Requirements

FR1:

Prompt assembly supports tiered memory.

FR2:

Retrieval supports scored selection.

FR3:

Runtime supports memory channels.

FR4:

Continuity remains authoritative.

FR5:

Events become packetized.

FR6:

Adaptive recovery changes retrieval behavior.

---

# Non-Functional Requirements

- no authority duplication
- deterministic ordering
- audit visibility
- migration compatibility

---

# Success Metrics

- reduced repetition
- improved continuity adherence
- improved retrieval quality
- reduced prompt cost
- improved scene coherence