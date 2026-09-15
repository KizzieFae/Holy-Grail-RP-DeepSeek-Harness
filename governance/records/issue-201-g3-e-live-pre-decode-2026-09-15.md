# Issue #201 G3-E — Live Execution Pre-Decode Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Execution SHA:** `eff2021` (apparatus) + live harness additions (see commit after this record)  
**Apparatus SHA:** `eff2021`  
**Proposal SHA:** `a438635`  
**Canonical state:** `consensus_reached` (unchanged)  
**Blind decode:** NOT performed  
**Arm-level subjective quality conclusion:** NOT rendered

---

## Campaign summary

| Metric | Value |
|--------|-------|
| Planned runs | 28 |
| Completed / scored | 28 / 28 |
| Infrastructure replacements | 0 |
| Failed setup attempts (discarded) | 2 pre-success directories (scene-template / memory-scope validation) |
| Official evidence root | `data/investigation_runs/issue201-g3e-live-2026-09-15T19-07-03-775Z/` |

## Corpus / seeding

- Records: **307**; SHA256 `0cb74db3f507e8d4333582da9dec16f5a31f07acb1bdc6e1244c437cfa6f5e7c`
- Per-run isolated `hg-memory-scope-{uuid}` with deterministic corpus rewrite + manifest recovery + semantic index rebuild
- `HG_DATA_DIR`: repository `data/` (scene templates preserved; corpus scopes isolated)

## Execution order

Predetermined seed: `issue201-g3e-live-eff2021` — recorded in `execution-order.json` before inference.

## Tier-1 correctness

**No Tier-1 blocking failures** across 28 scored runs (entitlement leakage, stale authority auto-detector, untraceable knowledge, boundary violations).

## K3 (live seven-stage)

All four K3 runs (2 arms × 2 reps): **7/7 steps pass** including live cognition/presentation absence checks for `g3e-private-kizzie-debt`.

## K6 decomposition (notable)

- **K6-R:** PASS all runs (both required records in eligible set per probe forensics)
- **K6-P:** FAIL all runs (required records not in projected/ranked set under 8-item budget)
- **K6-C / K6-S:** mixed by presentation content (recorded per run in meta JSON)
- **K6-M:** instrumentation captured; not invoked as Librarian rescue on A2

## Arm accounting

| Arm | Runs | Librarian calls | Inferences | Input tokens | Output tokens | Wall ms |
|-----|------|-----------------|------------|--------------|---------------|---------|
| `a2_indexed_retrieval` | 14 | **0** | 296 | 82,617 | 113,520 | 934,589 |
| `lean_a4_knowledge` | 14 | **20** | 514 | 367,593 | 278,220 | 1,895,502 |

## Blind packet (locked for Governance)

| Artifact | Path | SHA256 |
|----------|------|--------|
| Blind packet | `outputs/issue201-g3e-blind-packet.json` | `9accab7e2c669527090a22037c39facb639be285fb72bd02581d7dd9adb6ea3a` |
| Answer key (separate, NOT decoded) | `outputs/issue201-g3e-blind-answer-key.json` | `bc6f56ff94d8b56133dbddfb227e28061c5f915da676a61ce1b096a0e2d62bf7` |

Schema: `issue201_g3e_blind_knowledge_packet_v1` — 28 samples `G3E-01` … `G3E-28`; architecture labels stripped.

## Governance next action

1. Score blind packet using frozen rubric dimensions (no Implementation decode).
2. Lock Governance scores before answer-key decode authorization.
3. Maintain `consensus_reached` until post-blind synthesis and architecture adjudication.
