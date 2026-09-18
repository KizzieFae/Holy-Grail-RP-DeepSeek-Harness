# Issue #201 — Information-aging apparatus remote durability (2026-09-17)

## Milestone

Post-qualification **durability gate** for the information-aging experimental apparatus. **No live information-aging campaign** has been executed.

## Identity

| Field | Value |
|-------|--------|
| Phase | 5 — long-horizon persistent narrative cognition |
| Weight | `full` / `full`, Full bootstrap |
| **Apparatus candidate SHA** | `94cba2d054a058c1e8dfff8621f37a51fae730f2` |
| Prior chain | `8c4c32a` (R5 apparatus), `1b482d7` (R5 runner), `94cba2d` (aging monitor/scheduler/qual) |
| Remote | `origin/main` pushed to apparatus candidate (see final durable SHA after this record commit) |

## Qualification

- **AG1–AG15:** fast synthetic — `runAgingApparatusQualification({ skipPantryRegression: true })`
- **AG16:** long real-runner pantry regression (~11 min) — `node v2/rp_runtime/scripts/issue201-aging-seam-verification.mjs --qualify`
- **Status:** AG1–AG16 PASS on accepted candidate state
- **Historical:** filtered test run `522407` failed AG9/AG12 on an **intermediate** build; superseded by fixes on `94cba2d`. Not a failure of the accepted candidate.

## Pantry regression (AG16 significance)

At T14, while the meal-alcove proposition remains in Character's actual `recent_scene_transcript`, the monitor classifies **`PRESENT_RAW`** and the scheduler **withholds** `OPP-MEAL-CHAIR` (no fixed-turn R5 test).

## Completed

- Tracked items A–C registry, aging lifecycle, LH-A–authoritative gated scheduler, stopping rules, AG1–AG16 mock qualification, remote push of apparatus commits.

## Remaining

- Governance decision on **live information-aging campaign** authorization (paired LH-A/LH-B runner orchestration; not implemented in this tranche).
- No production behavior changes; no lean suppression.

## Next step

Governance: authorize or defer **live** aging campaign entry (still fail-closed until explicitly authorized).
