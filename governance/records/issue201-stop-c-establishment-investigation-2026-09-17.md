# Issue #201 — Stop C establishment-asymmetry investigation (2026-09-17)

## Summary

Live campaign **run2** (`issue201-aging-live-campaign-2026-09-17-run2`) stopped with **Stop C** (`establishment_asymmetry`, `TRK-AYA-DORMANT-RECORD`, turn 5). Root cause is **not** persistence-driven divergence at establishment. **Both arms** received the same Player stimulus at T5 but produced **different** Character moves; **neither** committed the fixture dormant-record proposition. The paired gate uses **verbatim** `move_text` equality (`issue201-aging-paired.mjs`), which is **incompatible** with live stochastic RP and misaligned with the governance requirement for **semantic** shared establishment.

Secondary apparatus defects exposed: aging monitor treats post–`establishment_turn` marker absence as `AGED_OUT` without validating establishment; live orchestrator defers Stop C until after LH-B replay (7 turns/arm); erroneous Stop A signal at T7 from premature opportunity scheduling.

## Durability

| Field | Value |
|-------|--------|
| Pre-investigation HEAD | `c2cb808` |
| Live campaign record | `c2cb808` — `governance/records/issue201-aging-live-campaign-2026-09-17.md` |
| Durability action | Pushed `main` `440cbb4..c2cb808` (orchestrator + live record) to `origin/main` |
| Post-durability HEAD / `origin/main` | `c2cb808` |
| Investigation record | This file (commit after report) |

## Execution anchor

| Field | Value |
|-------|--------|
| Campaign execution SHA | `689753ffa86935d50900d4fb570bdad2d6cbe642` |
| Apparatus candidate | `94cba2d054a058c1e8dfff8621f37a51fae730f2` |
| Evidence | `data/investigation_runs/issue201-aging-live-campaign-2026-09-17-run2/` |

## Recommended establishment model (proposal only)

1. **Semantic establishment checkpoint** — confirm both arms committed the tracked proposition (marker/fingerprint or classifier), not identical prose.
2. **Per-item aging clock** — start aging only after confirmed establishment on LH-A; allow turn skew between arms until checkpoint passes.
3. **Arm-neutral scaffold** — if live Character cannot reliably emit fixture facts, use committed Narrator/shared presentation or Director beat obligation **before** aging (ordinary story commit, not persistence injection on A).
4. **Paired comparability** — after semantic establishment, compare story state for opportunity pairing; fail closed on omission or incompatible forks.

## Minimal remediation scope (if Governance accepts)

- Replace verbatim `assertPairedComparability` with semantic establishment validator + fail closed on omission.
- Gate `updateRegistryForTurn` aging observations until establishment confirmed for that item on LH-A.
- Defer LH-B phase or stop LH-A immediately when establishment fails (optional hardening).
- Fix opportunity scheduler: no `pendingFire` without confirmatory `AGED_OUT` on LH-A.
- **No** production lean suppression; **no** live rerun without new authorization.

## Qualification (no live inference)

Extend AG suite with mocks: wording variation pass, semantic difference fail, omission fail, persistence-without-lean fail, per-item aging clock, pantry T14 regression, Stop C regression. AG1–AG16 remain baseline unless extended.

## Next Governance decision

Approve remediation design (semantic establishment + aging-clock gating) and qualification plan before any live retry. Optionally split CLI exit-semantics work to a separate issue.

## #201 state

OPEN, `consensus_reached`, In Progress, P1 — unchanged.
