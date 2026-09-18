## Summary

Implement **A2 Track C**: move **Plot/Scribe persistent cognition** off the **mandatory synchronous per-turn critical path** while preserving persistence, projection, provenance, audit, safe consumption, and escalation when obligations require. **Not** deletion of Plot/Scribe. Child of **#201**.

## Type

design_gap

## Layer

memory

## Pattern status

single_instance

## Workflow weight

Assigned: **full** (recommended). Effective: **full**. Bootstrap: **Full**.

## Current status

open

## Parent / authority

- **#201** — LH-0/1B R0–R4 demonstrated; R5 unresolved and non-blocking
- G2 §8 persistent narrative cognition
- Decision: `governance/records/issue-201-final-architecture-decision-2026-09-17.md`

## Evidence (mandatory)

- **Scenario id:** `ayame_household_entry_evaluation` (LH evidence corpus)
- **Audit session path:** `data/investigation_runs/` (LH-1B, LH-0 — reference only)
- **Turn index:** n/a

## Expected behavior

Default beat path does not block on synchronous Plot update; persistent obligations remain durable; Character/Director consumers receive projections when policy demands; no advisory→authority leakage.

## Observed behavior

Plot/Scribe on synchronous path in A4; LH-1B shows R4 without R5 marginal retention proof.

## Constraints

No #201 aging/R5 experiments. Preserve investigation harness for research (`issue201-lh0-*`, `issue201-lh1b-*`) — do not delete in this track.

## Affected modules

Plot/Scribe orchestration, post-commit adapters, persistent store (`issue201-lh0-persistent-store` patterns → production paths), projection to Character manifest.

## Validation criteria

1. Async/default-off topology with explicit escalation paths.
2. Provenance + audit events for persistence and projection.
3. LH-0-style consumer tests adapted for production boundaries (Track D).
4. **`consensus_reached`** before production behavior change.

## Documentation

- [ ] Architecture overview alignment for Plot default topology

## Dependencies

**Requires Track A** skeleton. Coordinate with **Track B** for obligation triggers. **Feeds Track D**.
