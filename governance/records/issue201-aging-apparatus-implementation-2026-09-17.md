# Issue #201 — Information-aging apparatus (2026-09-17)

## Summary

Implemented **information-aging long-horizon experimental apparatus** (design-only execution; **no live inference**).

- Tracked items **A–C** (`TRK-AYA-MEAL-ALCOVE`, `TRK-AYA-PROMISE-GATE`, `TRK-AYA-DORMANT-RECORD`)
- Aging lifecycle monitor on actual assembled Character requests
- LH-A–authoritative **gated opportunity** scheduler
- Paired-arm eligibility sync and campaign stopping rules (Stop A/B/C)
- Qualification gates **AG1–AG16** (AG16 = pantry T14 regression via real R5 runner path)

**AG1–AG16:** PASS (mock/synthetic + runner pantry regression).

**Live information-aging campaign:** NOT authorized.

## Pantry regression (AG16)

At **T14** on the real mock runner path:

- `TRK-AYA-MEAL-ALCOVE` → **`PRESENT_RAW`** (`transcript_sufficient`)
- Opportunity **OPP-MEAL-CHAIR** **withheld** (`fired: false`, fallback stimulus used)
- No R5 test at T14

## Entry points

- `node v2/rp_runtime/scripts/issue201-aging-seam-verification.mjs --qualify`
- Libraries under `v2/rp_runtime/scripts/lib/issue201-aging-*.mjs`

## Prior reuse

- R5 apparatus `8c4c32a`, R5 runner `1b482d7`, `classifyActualSubstrateUniqueness`, LH-1B causal R0–R5, `executeR5MockSequence`

## Remote durability

Push `main` (includes prior `8c4c32a`, `1b482d7`, and aging commit) before live campaign authorization.
