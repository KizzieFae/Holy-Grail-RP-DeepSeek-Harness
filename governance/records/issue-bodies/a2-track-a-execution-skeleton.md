## Summary

Implement **A2 Track A**: the simplified RP **execution skeleton** and deterministic substrate wiring while preserving logical authority boundaries (Character / Director / Narrator / Continuity). Child of **#201** final architecture decision (A2 accepted). Establishes the topology other migration tracks plug into.

## Type

design_gap

## Layer

orchestration

## Pattern status

single_instance

## Workflow weight

Assigned: **full** (recommended). Effective: **full** at implementation start unless Governance narrows scope. Bootstrap: **Full** per `docs/issue-bootstrap-profiles.md`.

## Current status

open

## Parent / authority

- Parent assessment: **#201**
- Decision: `governance/records/issue-201-final-architecture-decision-2026-09-17.md`
- Spec: `governance/records/issue-201-g2-a2-redesign-specification-2026-09-15.md`

## Evidence (mandatory)

- **Scenario id:** n/a (architecture migration)
- **Audit session path:** n/a
- **Turn index:** n/a — authority is governance records and G2 invariants

## Expected behavior

A documented, implementable A2 beat/turn execution topology: deterministic substrate gates first; primary RP cognitions with separated logical roles; hooks for obligation-driven escalation (Tracks B/C) without reintroducing A4 always-on stack.

## Observed behavior

Production path follows A4 synchronous stack documented in Package D and coverage audit.

## Deterministic reasoning

#201 accepted A2; migration requires a skeleton before tiering (B) and async Plot (C) can land safely.

## System impact

Foundation for latency/complexity reduction without sacrificing continuity, PVR, validation, or audit invariants.

## Constraints

Preserve G2 §6 invariants. No deletion of Plot capability. No information-aging / R5 work. Coordinate with Track D before claiming validated migration.

## Affected modules

`v2/rp_runtime/` (orchestration, phase executors, beat path), integration with `v2/domain_api/`, continuity commit boundaries.

## Validation criteria

1. Design + implementation plan recorded on Issue.
2. Contract tests for authority boundaries (advisory ≠ commit).
3. No regression to protected outcomes per Track D program (linked).
4. Reach **`consensus_reached`** before substantive production edits.

## Documentation

- [ ] Update architecture docs when skeleton contracts change

## Dependencies

None (first migration track). **Blocks** Tracks B, C (contract surfaces). **Feeds** Track D acceptance definitions.
