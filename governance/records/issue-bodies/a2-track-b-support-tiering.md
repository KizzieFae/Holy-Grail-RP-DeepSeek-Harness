## Summary

Implement **A2 Track B**: convert always-on **support cognition** toward **obligation-driven / conditional / tiered** invocation (orientation, environmental cognition, semantic QA/repair, Librarian mediation). Child of **#201** / A2 migration. Depends on Track A execution skeleton.

## Type

design_gap

## Layer

orchestration

## Pattern status

single_instance

## Workflow weight

Assigned: **standard** (recommended). Escalate to **full** if cross-cutting prompt/authority changes or Package-D-equivalent ablations required. Bootstrap: **Standard** default; **Full** if escalated.

## Current status

open

## Parent / authority

- **#201** — Package D removals (D-03, D-04R, D-06, D-07, D-01-L, D-10)
- Decision: `governance/records/issue-201-final-architecture-decision-2026-09-17.md`

## Evidence (mandatory)

- **Scenario id:** n/a
- **Audit session path:** n/a
- **Turn index:** n/a — Package D + G3 records are authority

## Expected behavior

Support cognitions run only when deterministic obligation signals authorize them; simple beats avoid Librarian/orientation/env/QA stacks by default.

## Observed behavior

A4 invokes multiple support stages per turn (coverage audit).

## Deterministic reasoning

#201 evidence does not justify mandatory per-turn support LLM stages.

## Constraints

Do not weaken validation fail-closed behavior. Semantic repair remains available on failure/uncertainty. No always-on reintroduction without new evidence.

## Affected modules

`v2/rp_runtime/` cognition orchestration, librarian/orientation/env/QA hooks, round options / obligation routing.

## Validation criteria

1. Tiering triggers documented and testable.
2. Causal/cost comparison vs baseline on representative beats (Track D).
3. **`consensus_reached`** before code changes.

## Documentation

- [ ] Document tiering triggers in `docs/` or architecture sources

## Dependencies

**Requires Track A** obligation hooks and beat classification. Parallel with Track C after A milestone.
