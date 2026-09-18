# Issue #201 — Establishment semantics remediation (2026-09-17)

## Summary

Post–Stop C apparatus remediation: semantic establishment lifecycle (`UNESTABLISHED` → `ESTABLISHED` → aging), paired semantic equivalence (not verbatim `move_text`), persistence pre-establishment contamination gate, scheduler prerequisite chain, run2 bilateral-omission regression, AG17–AG28 qualification gates.

**No production behavior change.** No live inference. No deterministic establishment scaffold.

## Anchor

| Field | Value |
|-------|--------|
| Pre-remediation SHA | `c01737b` |
| Remediation candidate SHA | `5b3b65c` |
| Apparatus lineage | `94cba2d` → establishment-semantics remediation |
| Qualification | AG1–AG28 PASS; AG16 pantry PASS (`t6_semantic_establishment` + T14 `PRESENT_RAW`, opportunity withheld) |

## Modules

- `issue201-aging-establishment.mjs` — semantic detect/equivalence, contamination, opportunity block
- `issue201-aging-registry.mjs` — per-turn advance, paired finalize, LH-A aging replay
- `issue201-aging-qualification-establishment.mjs` — AG17–AG28 + run2 regression

## Next

Governance: authorize live information-aging campaign retry when ready (prerequisites now include semantic establishment + contamination gates).

## #201 state

OPEN, `consensus_reached`, In Progress, P1.
