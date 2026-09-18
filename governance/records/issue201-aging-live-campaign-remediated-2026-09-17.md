# Issue #201 — Remediated live information-aging campaign (2026-09-17 run3)

## Outcome

**Stop C** — `unilateral_establishment` at `TRK-AYA-PROMISE-GATE`, turn **8** (LH-B semantically established; LH-A omitted). No valid **Stop A** TESTED result. No R5 claim.

## Execution

| Field | Value |
|-------|--------|
| Entry | `node v2/rp_runtime/scripts/issue201-aging-seam-verification.mjs --execute-campaign --live-authorized` |
| Durable start SHA | `e2575ea` |
| Apparatus candidate | `5b3b65c` |
| Execution SHA | `e2575ea` |
| Evidence | `data/investigation_runs/issue201-aging-live-campaign-remediated-2026-09-17-run3/` |
| Started | `2026-09-18T03:25:10.537Z` |
| Ended | `2026-09-18T03:49:57.774Z` |
| Wall | ~24.8 min |
| LH-A session | `hg-session-30cdba53-5a7c-4d31-a2a6-c80bfb5c8334` |
| LH-B session | `hg-session-fa497c84-12c3-4bc2-b400-6a592fafa1a3` |
| Turns A / B | 13 / 8 (B stopped early on integrity) |

## Item summary

| Item | Paired establishment | Aging |
|------|----------------------|--------|
| TRK-AYA-DORMANT-RECORD (T5) | Bilateral omission | Clock not started |
| TRK-AYA-MEAL-ALCOVE (T6) | Bilateral omission | Clock not started |
| TRK-AYA-PROMISE-GATE (T8) | Unilateral (B only) → Stop C | Invalid for campaign |

No `PERSISTENCE_PREESTABLISHMENT_CONTAMINATION` recorded on registry. No premature opportunity (contrast run2).

## #201 state

OPEN, `consensus_reached`, In Progress, P1 — unchanged.
