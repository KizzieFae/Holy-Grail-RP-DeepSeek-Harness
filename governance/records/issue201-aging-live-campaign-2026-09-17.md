# Issue #201 — Live information-aging campaign (2026-09-17)

## Outcome

**Stop C — fail closed** (`establishment_asymmetry` at TRK-AYA-DORMANT-RECORD establishment, turn 5).

Live campaign **did not** reach a valid Stop A TESTED result. No R5 claim.

## Execution

| Field | Value |
|-------|--------|
| Entry | `node v2/rp_runtime/scripts/issue201-aging-seam-verification.mjs --execute-campaign --live-authorized` |
| Execution SHA (final) | `689753ffa86935d50900d4fb570bdad2d6cbe642` |
| Apparatus candidate | `94cba2d` |
| Evidence | `data/investigation_runs/issue201-aging-live-campaign-2026-09-17-run2/` |
| Started | `2026-09-18T02:39:45.281Z` |
| Ended | `2026-09-18T02:55:14.662Z` |
| LH-A session | `hg-session-9a2422e8-2c54-423c-815c-223b563a7c72` |
| LH-B session | `hg-session-faceac55-4e72-47c9-bfeb-caf9d117b659` |
| Turns A / B | 7 / 7 |

## Headline findings

- **TRK-AYA-MEAL-ALCOVE:** `PRESENT_RAW` after T6 establishment (transcript); opportunity correctly **not** fired at T14-equivalent path within 7 turns.
- **Shared establishment:** Live Character moves at T5 (dormant record) and T6 (meal) **diverged materially** between LH-A and LH-B despite identical Player stimuli — paired comparability failed.
- **Governance:** Do not interpret as persistence R5 evidence. Requires Governance review (establishment protocol, mock-seeded establishment turns, or comparability rules).

## Prior attempts

- Run1: anchor `await` bug (fixed `7223706`).
- Run2: missing `causal_design` on fixture (fixed `689753f`).

## #201 state

OPEN, `consensus_reached`, In Progress, P1 — not `implemented` / `validated` / closed.
