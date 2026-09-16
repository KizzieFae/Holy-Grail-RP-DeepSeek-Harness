# Issue #201 LH-1A Blind Evaluation & Architectural Analysis Report

**Date:** 2026-09-16  
**Issue:** #201 — OPEN, `consensus_reached`  
**Phase:** 5 LH-1A blind evaluation → decode → analysis  
**Workflow weight:** `full` / `full`

## Machine-readable artifacts

| Artifact | Path | SHA-256 |
|----------|------|---------|
| Blind integrity report | `governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-integrity-report.json` | (see file) |
| Evaluable blind packet | `governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-sequence-packet-evaluable.json` | `3348a4a5d4086210f9fc600c5a25f88e9aef1de9b492301fdc838aa4aa271e82` |
| Placeholder blind packet (campaign dir) | `data/investigation_runs/.../issue201-lh1a-blind-sequence-packet.json` | `a669c6395bf7b3519d21deac2d56143e0e03ced513e17659a9cf5cf6dbc0b0f5` |
| Answer key | `data/investigation_runs/.../issue201-lh1a-blind-sequence-answer-key.json` | `a9bdb2c367774f443d1496d55bc8dcea69e9259169347075eb10a7c32b69539c` |
| Rubric | `governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json` | `f533cc604b276f7798639db863c8e2264254233ab162de03b343841df840bb91` |
| Score lock | `governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-score-lock.json` | `345a59ab89556f95d4830cb8d500b8d2662521d3229cc9cfca2c43908ef773ea` |
| Decode adjudication | `governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-decode-adjudication.json` | (see file) |

**Score lock preceded decode:** `locked_at` 2026-09-16T07:04:34.180Z < `decoded_at` 2026-09-16T07:04:34.222Z; `answer_key_accessed_before_lock: false`.

## Remediation commit identity

| Field | Value |
|-------|-------|
| Pre-commit SHA | `818afc9a3c9b3e44ab9460ed8558b4c36cb84411` |
| Remediation commit SHA | `bc569c6` |
| Attempt 2 evidence root | `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z/` |
| Attempt 1 (forensic, non-evaluable) | `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-03-03-444Z/` |

## Blind integrity verification

- 8/8 evaluable sequences present; 22/22 committed turns each.
- Frozen rubric hash verified.
- Evaluable packet rebuilt from sequence artifacts because campaign-dir blind packet contained placeholder presentation text (transport bug in `buildLh1aBlindPacket` hardcoded stub). Evaluator-facing packet uses anonymous labels only; forbidden-pattern scan **PASS**.
- Answer key remains separate; not accessed during scoring.

## Decoded arm mapping

| Blind | Arm | Scenario | Session |
|-------|-----|----------|---------|
| SEQ-A | LH-A | Ayame | `hg-session-f6a88ae0-...` |
| SEQ-B | LH-B | Ayame | `hg-session-d37e42ba-...` |
| SEQ-C | LH-C | Ayame | `hg-session-2ccc78a0-...` |
| SEQ-D | LH-D | Ayame | `hg-session-a75b0ac7-...` |
| SEQ-E | LH-A | Arkham | `hg-session-50402afe-...` |
| SEQ-F | LH-B | Arkham | `hg-session-3660aca9-...` |
| SEQ-G | LH-C | Arkham | `hg-session-f81a7554-...` |
| SEQ-H | LH-D | Arkham | `hg-session-227959da-...` |

## Blind scores (locked, 19-dimension means)

| Blind | Mean 19d |
|-------|----------|
| SEQ-A | 4.53 |
| SEQ-B | 4.84 |
| SEQ-C | 3.79 |
| SEQ-D | 4.89 |
| SEQ-E | 3.84 |
| SEQ-F | 3.89 |
| SEQ-G | 4.63 |
| SEQ-H | 4.16 |

Population mean (all dimensions): **4.329**.

### By arm (decoded, descriptive only — not architecture decision)

| Arm | Ayame | Arkham | Pooled mean |
|-----|-------|--------|-------------|
| LH-A | 4.53 | 3.84 | 4.19 |
| LH-B | 4.84 | 3.89 | 4.37 |
| LH-C | 3.79 | 4.63 | 4.21 |
| LH-D | 4.89 | 4.16 | 4.53 |

**Critical finding:** Strong **scenario×arm interaction**. Ayame ranks LH-D > LH-B > LH-A > LH-C. Arkham ranks LH-C > LH-D > LH-B > LH-A. No arm wins both scenarios.

## Architectural hypotheses (assessment, no winner selected)

### LH-A — Primary RP sufficiency

Maintains strong Ayame performance (4.53) with lowest inference cost (118 calls / 44 turns). Arkham weaker (3.84) on repetition and voice distinction. Coherence, thread retention, and dark tone adequate on Ayame without persistent cognition. **Sufficient for controlled single-NPC interview aging; weaker under Arkham multi-NPC stress.**

### LH-B — Plot/Scribe marginal value

Second-highest Ayame score (4.84) with threshold/empty-chair structural discipline. Arkham marginal (3.89). Persistent obligations generated (10/seq) with consequential activations logged, but archaeology shows `consumer_use: non_use_or_pending` on sampled obligations — **marginal narrative value not clearly attributable to consumed Plot output** vs transcript discipline. First meaningful aging comparison still ambiguous on consumption path.

### LH-C — Storyteller-class value

**Weakest Ayame (3.79)** — mid-arc accommodation (written terms T8/T14) hurt dark-tone and premature-resolution dimensions. **Strongest Arkham (4.63)** — best Ivy/Harley separation and competing-thread handling. Scenario-dependent; persistent Storyteller value appears **stress-scenario-specific**, not general.

### LH-D — Consolidated intelligence

**Highest Ayame (4.89)** — threshold/name spine, superior long-horizon thread gating. Solid Arkham (4.16) but below LH-C. Director fairness preserved (no observed selection override). Consolidation appears to help **structured interview control** more than **mess-hall chaos**.

## Cost analysis (Attempt 2, from turn inference aggregates)

| Arm | Inf calls | Input tok | Output tok | Wall ms | Retries | Obligations gen |
|-----|-----------|-----------|------------|---------|---------|-----------------|
| LH-A | 118 | 1.19M | 230k | 2.81M | 8 | 0 |
| LH-B | 253 | 2.57M | 512k | 4.59M | 9 | 20 |
| LH-C | 204 | 2.42M | 487k | 4.24M | 5 | 20 |
| LH-D | 207 | 2.38M | 536k | 4.39M | 9 | 20 |

LH-A ~2× cheaper than persistent arms. Persistent arms show high `consequential_activations` in ledger but **deferred_valid = 0** across campaign — obligations activated without demonstrated deferred-precision payoff in this 22-turn window.

## Reliability observation

| Item | Value |
|------|-------|
| Attempt 1 SEQ-A T11 | Terminal `character_failure` (schema exhaustion) |
| Remediation | `bc569c6` structural retry guidance |
| Attempt 2 structural rejections | 24 (recovered within budget) |
| Turn-level retries | 31 |
| Terminal beat failures (Attempt 2) | 0 |

**Provisional classification:** Residual first-attempt schema-compliance weakness successfully contained; not independent debt yet.

## LH-1B recommendation

**Warranted — targeted replication.** Material uncertainty from scenario×arm crossover (LH-C Arkham vs Ayame inversion; LH-D Ayame lead). Smallest scope:

1. **Ayame LH-C** single replication (accommodation weakness may be stochastic).
2. **Arkham LH-A** single replication (control baseline under stress).
3. Optional: **Ayame LH-A vs LH-D** paired replication if Governance wants to confirm threshold-architecture advantage.

Do **not** replicate full 8-sequence campaign.

## LH-2 necessity

**Likely necessary before certifying ultimate long-term persistent-cognition behavior.** 22 turns demonstrated meaningful aging but `deferred_valid = 0` and many obligations show `consumer_use: non_use_or_pending`. Evidence may suffice for **redesign direction** (scenario-dependent arm value) but **not** for certifying 100+ turn or multi-session persistence yield.

## Exact next Governance decision

1. Accept locked blind scores and decode record.
2. Decide whether to authorize **targeted LH-1B** replication per smallest scope above.
3. Decide whether **LH-2 longer horizon** is required before architecture selection.
4. Commit evaluation artifacts (`governance/records/issue201-lh1a-evaluation/`).
5. Keep #201 OPEN — do not transition to `implemented`.
