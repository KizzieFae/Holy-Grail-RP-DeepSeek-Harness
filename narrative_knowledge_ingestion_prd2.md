# Narrative Knowledge Ingestion Product Requirements Document

## Narrative Canonical Knowledge Engine (NCKE)

---

## Purpose

Build a structured ingestion pipeline for narrative source material.

Convert prose into structured packet-compatible knowledge.

This system supplies runtime memory.

---

## Problem Statement

Raw prose is inefficient runtime knowledge.

Problems:

- redundancy
- retrieval noise
- buried causality
- implicit relationships

Goal:

Convert prose into structured narrative intelligence.

---

# Product Goals

---

# Goal 1 — Entity Extraction

Extract:

- characters
- locations
- factions
- institutions
- artifacts
- concepts

---

# Goal 2 — Relationship Extraction

Build relationship graphs.

Tracks:

- trust
- alliance
- hostility
- romance
- hierarchy
- dependency

Track changes over time.

---

# Goal 3 — Event Extraction

Convert narrative into events.

Required:

- actor
- target
- event
- change
- location
- time

---

# Goal 4 — Causal Extraction

Track causality.

Examples:

A caused B

B caused C

C caused D

Purpose:

Narrative logic reconstruction.

---

# Goal 5 — Character Psychology Extraction

Extract:

- values
- fears
- goals
- wounds
- motivations
- contradictions

---

# Goal 6 — World-State Extraction

Extract:

- lore
- institutions
- political systems
- geography
- rules

---

# Goal 7 — Theme Extraction

Extract:

- redemption
- sacrifice
- obsession
- corruption

Purpose:

Narrative resonance.

---

# Ingestion Pipeline

Stage 1:

Entity extraction

Stage 2:

Relationship extraction

Stage 3:

Event extraction

Stage 4:

State delta extraction

Stage 5:

Causal extraction

Stage 6:

Psychology extraction

Stage 7:

Theme extraction

Stage 8:

Cross-book synthesis

---

# Output Contracts

Produces:

- Character Memory Packets
- Relationship Memory Packets
- Event Memory Packets
- World Memory Packets

Compatibility target:

Memory Packet Contract v1

---

# Functional Requirements

FR1:

Support chapter ingestion.

FR2:

Support book synthesis.

FR3:

Support cross-book synthesis.

FR4:

Store state deltas.

FR5:

Store causality.

FR6:

Store psychology.

FR7:

Produce runtime-compatible packets.

---

# Non-Functional Requirements

- deterministic writes
- replayable ingestion
- auditable transformation
- idempotent imports

---

# Dependency Rule

Depends on:

Runtime Narrative Memory PRD

Reason:

Runtime defines the memory contract.

Knowledge supplies the memory contract.

---

# Success Metrics

- accurate extraction
- strong relationship fidelity
- strong causal fidelity
- high retrieval precision
- reduced runtime prompt load