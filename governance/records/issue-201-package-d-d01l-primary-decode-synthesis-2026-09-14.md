# Issue #201 — D-01-L Locked Primary Decode Synthesis

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**Execution record:** `governance/records/issue-201-package-d-d01l-execution-2026-09-14.md`  
**Locked scores:** `governance/records/issue201-d01l-governance-blind-scores-locked.json`  
**Evidence commit (decode):** `232f1ef`  
**Control substrate:** `c751ea6`  
**D-01-L harness + policies:** `fc80461`

**Scoring integrity:** Governance assigned and locked all primary longitudinal scores while sequence identities were anonymous. Implementation AI records decode mapping only; scores are not rescored or altered.

**Causal question (narrow):** Does synchronous preamble Storyteller cognition add material multi-turn narrative value when Plot cognition and post-commit Storyteller cognition remain available?

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-01-L execution | **Complete** |
| D-01-L primary blind eval | **Complete, locked, decoded** |
| Secondary per-turn eval | **Not performed** |
| D-10 / EXP-3 | **Deferred** |
| Production redesign | **NOT authorized** |

---

## 2. Answer-key integrity verification

| Check | Result |
|-------|--------|
| Labels SEQ-A … SEQ-H one-to-one | **PASS** |
| Exactly 8 sequences | **PASS** |
| 4 control / 4 ablated | **PASS** |
| 2 Arkham + 2 Ayame per arm | **PASS** |
| Answer key matches finalized blind packet (stimulus text per turn) | **PASS** (all 8) |
| No packet rebuild after Governance scoring | **PASS** (packet unchanged since transport) |
| Failed/noncommitted attempts excluded | **PASS** |
| Replacement evidence maps correctly | **PASS** (`SEQ-D` → `D01L-ablated-arkham_stress-seq1-a1`) |
| Scenario identities match scored sequences | **PASS** |
| Control arm definition | ST preamble ON, Plot ON, post-commit ST retained |
| Ablated arm definition | ST preamble OFF (`skipStorytellerCognition`), Plot ON, post-commit ST retained |

**No discrepancies found.**

---

## 3. Complete SEQ-A … SEQ-H decode mapping

| Label | Scenario | Arm | ST preamble | Sequence ID | Session ID | Evidence | Locked mean |
|-------|----------|-----|:-----------:|-------------|------------|----------|------------:|
| SEQ-A | Ayame household entry | ablated | OFF | `D01L-ablated-ayame_controlled-seq1-a1` | `hg-session-7fe06b53-188e-49d6-aa01-0cbb42ea20ee` | original | 4.50 |
| SEQ-B | Ayame household entry | control | ON | `D01L-control-ayame_controlled-seq1-a1` | `hg-session-216f464c-c6bc-47ad-a054-91dad668459e` | original | 4.60 |
| SEQ-C | Ayame household entry | control | ON | `D01L-control-ayame_controlled-seq2-a1` | `hg-session-3410e327-73d0-4499-bc5a-ebe51bea25af` | original | 4.90 |
| SEQ-D | Arkham mess hall stress | ablated | OFF | `D01L-ablated-arkham_stress-seq1-a1` | `hg-session-73d564d5-539d-4db5-9c4a-d858aada57cb` | **replacement** | 4.30 |
| SEQ-E | Arkham mess hall stress | control | ON | `D01L-control-arkham_stress-seq2-a1` | `hg-session-1d79df7f-2858-4da9-9a73-c13208489f6d` | original | 3.90 |
| SEQ-F | Arkham mess hall stress | control | ON | `D01L-control-arkham_stress-seq1-a1` | `hg-session-0f44ecd0-2e3a-43fa-b9ef-3e26affb8167` | original | 4.90 |
| SEQ-G | Ayame household entry | ablated | OFF | `D01L-ablated-ayame_controlled-seq2-a1` | `hg-session-d97963f2-dd45-47f0-9fa6-d25f61f36107` | original | 4.30 |
| SEQ-H | Arkham mess hall stress | ablated | OFF | `D01L-ablated-arkham_stress-seq2-a2` | `hg-session-cf7ec9dc-154d-4e40-bf36-e46f4c98425b` | original (attempt 2) | 5.00 |

---

## 4. Replication-level locked scores (10 dimensions + mean)

Governance-assigned; not recomputed.

| Label | Arm | Thread | Escal. | Agenda | Delayed | Momentum | Initiative | Loop avoid. | No early res. | Drift | Continuity | **Mean** |
|-------|-----|-------:|-------:|-------:|--------:|---------:|-----------:|------------:|--------------:|------:|-----------:|---------:|
| SEQ-A | ablated | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | **4.50** |
| SEQ-B | control | 5 | 4 | 5 | 4 | 4 | 5 | 4 | 5 | 5 | 5 | **4.60** |
| SEQ-C | control | 5 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | **4.90** |
| SEQ-D | ablated | 5 | 4 | 5 | 5 | 3 | 4 | 2 | 5 | 5 | 5 | **4.30** |
| SEQ-E | control | 5 | 3 | 5 | 4 | 2 | 3 | 2 | 5 | 5 | 5 | **3.90** |
| SEQ-F | control | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | **4.90** |
| SEQ-G | ablated | 5 | 4 | 5 | 4 | 3 | 4 | 3 | 5 | 5 | 5 | **4.30** |
| SEQ-H | ablated | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |

### Blind qualitative observations (preserved verbatim)

- **SEQ-H:** Strongest overall trajectory — earlier pressures become later consequential actions rather than merely remaining mentioned.
- **SEQ-F:** Strong escalation, initiative, and delayed consequence.
- **SEQ-C:** Strongest Ayame trajectory — entry → boundaries → study → explicit definition of failure.
- **SEQ-B:** Useful persistence through Ayame repeatedly pursuing an unanswered interview question.
- **SEQ-A:** Maintained authority/continuity well but developed somewhat less.
- **SEQ-G:** Retained thread but became somewhat circular around unanswered-position interrogation.
- **SEQ-E:** Clearest example of strong memory without sufficient development — repeated watch/room/guards/terms/table/arithmetic imagery caused low momentum and reactive-loop avoidance.
- **SEQ-D:** Milder version of the same repetition/stalling problem.

> **Governance distinction:** Remembering a narrative pressure is not the same as advancing it.

---

## 5. Overall arm aggregates

| Arm | Sequences | Replication means | Arm average |
|-----|-----------|-------------------|------------:|
| **control** (ST preamble ON) | SEQ-B, SEQ-C, SEQ-E, SEQ-F | 4.60, 4.90, 3.90, 4.90 | **4.575** |
| **ablated** (ST preamble OFF) | SEQ-A, SEQ-D, SEQ-G, SEQ-H | 4.50, 4.30, 4.30, 5.00 | **4.525** |

**Between-arm delta (control − ablated):** **+0.05**

---

## 6. Arkham aggregates

| Arm | Sequences | Means | Average |
|-----|-----------|------:|--------:|
| control | SEQ-E, SEQ-F | 3.90, 4.90 | **4.400** |
| ablated | SEQ-D, SEQ-H | 4.30, 5.00 | **4.650** |

**Arkham delta (control − ablated):** **−0.25** (ablated higher)

---

## 7. Ayame aggregates

| Arm | Sequences | Means | Average |
|-----|-----------|------:|--------:|
| control | SEQ-B, SEQ-C | 4.60, 4.90 | **4.750** |
| ablated | SEQ-A, SEQ-G | 4.50, 4.30 | **4.400** |

**Ayame delta (control − ablated):** **+0.35** (control higher)

---

## 8. Per-dimension control vs ablated matrix

Replication-level values preserved in §4. Arm means below (n=4 per arm).

| Dimension | Control mean | Ablated mean | Δ (control − ablated) |
|-----------|-------------:|-------------:|----------------------:|
| Thread persistence | 5.00 | 5.00 | 0.00 |
| Escalation coherence | 4.25 | 4.25 | 0.00 |
| Agenda persistence | 5.00 | 5.00 | 0.00 |
| Delayed consequences | 4.25 | 4.50 | −0.25 |
| Scene momentum | 4.00 | 3.75 | +0.25 |
| Cross-turn initiative | 4.50 | 4.25 | +0.25 |
| Reactive-loop avoidance | 3.75 | 3.50 | +0.25 |
| Premature-resolution avoidance | 5.00 | 5.00 | 0.00 |
| Plot-drift control | 5.00 | 5.00 | 0.00 |
| Cross-turn emotional/narrative continuity | 5.00 | 5.00 | 0.00 |

**Storyteller-relevant dimensions with control advantage:** momentum (+0.25), initiative (+0.25), reactive-loop avoidance (+0.25).  
**Ablated advantage:** delayed consequences (−0.25).  
**Tied at ceiling:** thread, agenda, premature-resolution avoidance, drift control, continuity.

---

## 9. Architectural-work context (committed sequences)

From D-01-L execution record; not used in scoring.

| Metric | Control (4 seq) | Ablated (4 seq) | Δ |
|--------|----------------:|----------------:|--:|
| ST preamble inferences | 32 | 0 | +32 removed |
| ST post-commit inferences | 18 | 20 | −2 |
| Plot inferences | 32 | 35 | −3 |
| Total inferences | 98 | 55 | +43 |
| Wall time (min) | 61.3 | 49.3 | +12.0 |

Post-commit Storyteller remained active on both arms by design.

---

## 10. Correctness parity

| Check | Control | Ablated |
|-------|---------|---------|
| Committed sequences | 4/4 | 4/4 |
| Objective issues | 0 | 0 |
| PVR valid (all turns) | yes | yes |

Failed attempts excluded from scoring set. One ablated Arkham slot used authorized replacement evidence (`SEQ-D`).

---

## 11. Prospective interpretation evidence (not a Governance verdict)

Evidence mapped to pre-registered categories. **Governance must render the final architectural verdict.**

### Demonstrated longitudinal preamble value

**Weak / not supported.** Overall delta +0.05 is within the ≤0.15 “no demonstrated value” band. Arkham shows ablated **advantage** (−0.25). Only Ayame shows control advantage (+0.35). Control advantage on Storyteller-relevant dimensions (momentum, initiative, reactive-loop) is +0.25 each — below the ≥0.20 threshold for a consistent directional Storyteller-ON advantage **and** contradicted by Arkham replication direction. Best ablated sequence (SEQ-H, 5.00) exceeds best control (SEQ-C/F, 4.90); worst control Arkham (SEQ-E, 3.90) is lowest in matrix.

### No demonstrated preamble value

**Partially supported at overall level.** Δ ≈ +0.05 ≤ 0.15; correctness matched. However, scenario-level divergence prevents clean acceptance of a global null.

### Delayed vs immediate value

**Not supported as a clean pattern.** Per-dimension deltas are small (≤0.25). No sequence-level Storyteller-ON advantage ≥0.20 on four relevant dimensions across the bounded comparison. Ablated SEQ-H scores at ceiling on all dimensions including momentum/initiative.

### Complexity-conditioned value

**Supported.** Arkham Δ = −0.25; Ayame Δ = +0.35; |difference| = 0.60 ≥ 0.20 threshold. Effects are materially scenario-dependent and directionally opposite.

### Potentially movable off synchronous critical path

**Consistent with evidence, not proven.** Preamble removal did not collapse longitudinal quality; ablated Arkham matched or exceeded control while preamble work was fully removed. Post-commit Storyteller parity (+18 vs +20) means null/split preamble results specifically implicate **synchronous preamble placement**, not all Storyteller functions.

### Inconclusive / confounded

**Partially applicable.** Small n (2 per scenario per arm), opposite scenario directions, branch-path divergence between replications (e.g., control Arkham SEQ-E vs SEQ-F turn-2 branches), and replacement evidence for one ablated Arkham slot add interpretive caution. Not fully inconclusive because overall and per-dimension patterns are readable.

---

## 12. Confounds

| Confound | Detail |
|----------|--------|
| Small n | 2 sequences per scenario per arm |
| Branch divergence | Presentation-driven player-policy branches differ across replications (especially Arkham turn 2) |
| Replacement evidence | SEQ-D from authorized replacement after 2 failed attempts on original ablated Arkham seq1 |
| Post-commit ST retained | Both arms retain post-commit Storyteller — preamble-specific causal isolation only |
| Stochastic runtime | `character_failure` on ablated Arkham attempts (resolved before scoring set finalized) |
| Ceiling effects | Thread, agenda, drift, continuity at 5.0 for nearly all sequences |

---

## 13. Secondary per-turn evaluation — discriminating value assessment

**Likely low additional discriminating value for the preamble causal question** given:

- Primary longitudinal endpoint already exposes momentum/initiative/reactive-loop deficits (SEQ-E, SEQ-D) that Governance linked to repetition without advancement.
- Overall arm delta is near-null; scenario conditioning dominates.
- Per-turn rubric would re-measure overlapping constructs at finer granularity without resolving the Arkham/Ayame directional split.

Governance may still request secondary scoring if it wants turn-level granularity for mechanism documentation. **Not requested or performed in this pass.**

---

## 14. Exact Governance decisions required

1. **Render D-01-L architectural verdict** on synchronous preamble Storyteller value using pre-registered interpretation rules and this decode evidence.
2. **Decide whether secondary per-turn 11-dimension scoring** adds sufficient information value to authorize.
3. **Decide whether scenario-conditioned split** (Ayame control advantage vs Arkham ablated advantage) warrants follow-on design (not D-10/EXP-3 without separate authorization).
4. **Confirm issue phase transition** — remain `investigating` or advance per Package D workflow.
5. **Record consensus** if preamble placement recommendation is made (does not authorize production changes).

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
