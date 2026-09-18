## Summary

Define and execute **A2 Track D**: **migration acceptance / comparative validation** for the A2 path vs required RP outcomes and invariants (deterministic tests, regressions, representative live RP when authorized, complexity/latency/quality evidence). Child of **#201**. Does not implement migration slices — validates them.

## Type

quality

## Layer

application_infrastructure

## Pattern status

single_instance

## Workflow weight

Assigned: **standard** (recommended). Escalate to **full** for live acceptance campaigns. Bootstrap: **Standard**; **Full** if live validation authorized.

## Current status

open

## Parent / authority

- **#201** validation criteria and protected outcomes
- Package D / G3-E methodology for blind and cost forensics where applicable
- Tracks A–C deliverables

## Evidence (mandatory)

- **Scenario id:** `arkham_asylum_mess_hall_arena`, `ayame_household_entry_evaluation`
- **Audit session path:** n/a (program defines new acceptance bundles)
- **Turn index:** n/a

## Expected behavior

Documented acceptance matrix: each protected outcome mapped to tests and/or authorized live checks; pass/fail gates before declaring A2 migration milestones validated.

## Observed behavior

No unified A2 acceptance program yet; #201 assessment evidence is fragmented across investigation runs.

## Constraints

No premature live inference in intake phase. Live campaigns only with explicit Governance authorization per matrix.

## Affected modules

`v2/tests/`, investigation harness reuse, docs/testing.md, governance acceptance records.

## Validation criteria

1. Acceptance matrix approved at **`consensus_reached`**.
2. Executes after Track A minimum viable slice; expands as B/C land.
3. Results recorded with SHA + commands (§B.0.2 discipline).

## Documentation

- [ ] `docs/testing.md` and validation framework references updated when matrix stabilizes

## Dependencies

**Follows Tracks A–C** (iterative). Can start matrix design in parallel with Track A planning.
