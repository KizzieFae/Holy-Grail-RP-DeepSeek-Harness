# Issue #201 — D-01-L Execution & Pre-Decode Blind-Packet Report

**Date:** 2026-09-14 / 2026-09-15 (UTC)  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full` (assigned + effective)  
**Consensus anchors:** Stage-3 decode `da70fc7`; issue-body anchor `f7c9165`  
**Control substrate SHA:** `c751ea666f0cae6524698005aa5859721c2e9738`  
**Execution SHA (harness + policies):** `fc80461a3208e88addb6766669f7ef2abcd1d367`  
**Evidence commit (this record):** `16cb928`  
**Harness:** `v2/rp_runtime/scripts/issue201-package-d-d01l-longitudinal.mjs`  
**Player policy module:** `v2/rp_runtime/scripts/lib/issue201-d01l-player-policy.mjs`  
**Primary evidence root:** `data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z/`  
**Replacement evidence root:** `data/investigation_runs/issue201-package-d-d01l-2026-09-15T00-18-44-424Z/` (ablated Arkham seq1 only)

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-01-L execution | **Complete** |
| D-01-L primary blind eval | **Complete, locked, decoded** — see `issue-201-package-d-d01l-primary-decode-synthesis-2026-09-14.md` |
| Locked primary scores | `governance/records/issue201-d01l-governance-blind-scores-locked.json` |
| D-10 / EXP-3 | **Deferred** |
| Production redesign / remediation | **NOT authorized** |

---

## 2. Execution SHA

| Anchor | SHA |
|--------|-----|
| Repo HEAD at harness/policy commit | `fc80461` |
| Control substrate (frozen) | `c751ea6` |
| Stage-3 decode consensus | `da70fc7` |
| Issue-body anchor | `f7c9165` |
| Prior D-01-L prep commit | `0eb0cd6` |

No control-path production code changes. Intervention uses existing `skipStorytellerCognition` round option only.

---

## 3. Frozen Arkham policy + hash

| Field | Value |
|-------|-------|
| Policy ID | `arkham_d01l_policy_v1` |
| Path | `governance/records/issue201-d01l-policies/arkham_d01l_policy_v1.json` |
| SHA-256 | `df3dfa6b54480397c7f616d7749051c4b8abbedf9345ad00c58be5faef3d46ee` |
| Turns | 5 |
| Turn 1 | Fixed Stage-3 watch/murmur stimulus |
| Turns 2–5 | Predicate-driven branching from presentation text |

Frozen **before** any arm executed (`2026-09-14T22:12:05.832Z` per primary run manifest).

---

## 4. Frozen Ayame policy + hash

| Field | Value |
|-------|-------|
| Policy ID | `ayame_d01l_policy_v1` |
| Path | `governance/records/issue201-d01l-policies/ayame_d01l_policy_v1.json` |
| SHA-256 | `28e50a09ca6eea24bab0b4738bc64a1ccc6760ceb5eac486770a36f657b4c180` |
| Turns | 3 |
| Turn 1 | Fixed knock stimulus |
| Turns 2–3 | Predicate-driven branching from presentation text |

Frozen **before** any arm executed.

---

## 5. Arm definitions

| Arm | Storyteller preamble | Plot cognition | Post-commit Storyteller | Round options |
|-----|:--------------------:|:--------------:|:-----------------------:|---------------|
| **control** | ON | ON | unchanged (active) | `{}` |
| **ablated** | OFF | ON | unchanged (active) | `{ skipStorytellerCognition: true }` |

**Causal question (narrow):** Does synchronous preamble Storyteller cognition add material multi-turn narrative value when Plot cognition and post-commit Storyteller cognition remain available?

Post-commit Storyteller retention is intentional (D-01b parity). This experiment does **not** test global Storyteller removal.

---

## 6. Sequence inventory

**Authorized tranche:** 8 complete sequences (32 visible turn-presentations).

| Sequence ID | Blind label | Arm | Scenario | Rep | Turns | Status | HG session |
|-------------|-------------|-----|----------|-----|------:|--------|------------|
| `D01L-control-arkham_stress-seq1-a1` | SEQ-F | control | arkham_stress | 1 | 5/5 | committed | `hg-session-*` (see report JSON) |
| `D01L-control-arkham_stress-seq2-a1` | SEQ-E | control | arkham_stress | 2 | 5/5 | committed | see report |
| `D01L-ablated-arkham_stress-seq1-a1` | SEQ-D | ablated | arkham_stress | 1 | 5/5 | committed (replacement) | see report |
| `D01L-ablated-arkham_stress-seq2-a2` | SEQ-H | ablated | arkham_stress | 2 | 5/5 | committed (attempt 2) | see report |
| `D01L-control-ayame_controlled-seq1-a1` | SEQ-B | control | ayame_controlled | 1 | 3/3 | committed | see report |
| `D01L-control-ayame_controlled-seq2-a1` | SEQ-C | control | ayame_controlled | 2 | 3/3 | committed | see report |
| `D01L-ablated-ayame_controlled-seq1-a1` | SEQ-A | ablated | ayame_controlled | 1 | 3/3 | committed | see report |
| `D01L-ablated-ayame_controlled-seq2-a1` | SEQ-G | ablated | ayame_controlled | 2 | 3/3 | committed | see report |

Blind labels assigned with `random.seed(201)` shuffle. Full session IDs in `issue201-package-d-d01l-longitudinal-report.json`.

---

## 7. Retries / failures / replacements

| Attempt | Sequence | Outcome | Detail |
|---------|----------|---------|--------|
| a1 | `D01L-ablated-arkham_stress-seq1` | failed | `character_failure` turn 2 (not committed) |
| a2 | `D01L-ablated-arkham_stress-seq1` | failed | `character_failure` turn 2 (not committed) |
| a1 (replacement) | `D01L-ablated-arkham_stress-seq1-a1` | **committed** | Authorized replacement after 2 contaminated attempts |
| a1 | `D01L-ablated-arkham_stress-seq2` | failed | `character_failure` turn 4 |
| a2 | `D01L-ablated-arkham_stress-seq2-a2` | **committed** | Standard within-sequence retry (attempt 2) |

Failed/noncommitted sequences **excluded** from blind packet. Failed-attempt evidence preserved under primary evidence root `outputs/`.

**No intervention-specific correctness failure pattern** observed beyond transient `character_failure` on ablated Arkham runs (resolved by retry/replacement).

---

## 8. Policy branch trajectories

Branch selection used frozen policies only; predicates evaluated on prior presentation text. Per-turn logs include: `turn`, `policy_hash`, `predicate_hits`, `winning_predicate`, `branch_id`, `exact_player_stimulus`.

### Arkham — notable cross-arm divergence (presentation-driven, not arm-driven)

| Turn | Control seq1 | Ablated seq1 (replacement) | Control seq2 | Ablated seq2 |
|------|--------------|---------------------------|--------------|--------------|
| 2 | `P2_DEFAULT` | `P2_IVY_DIRECT` | `P2_HARLEY_DOMINANT` | `P2_DEFAULT` |
| 3–5 | `P3_GUARD_ESCALATION`, `P4_RECRUITMENT`, `P5_GUARD_THREAD` | same | same | same |

Turn 2 divergence reflects different presentation content after turn 1 (Ivy/Harley emphasis), not arm identity. Turns 3–5 player stimuli identical across committed Arkham sequences where predicates converged.

### Ayame — near parity

| Turn | All seq1 (control + ablated) | Control seq2 | Ablated seq2 |
|------|-------------------------------|--------------|--------------|
| 2 | `A2_FORMAL_CONTROL` | `A2_FORMAL_CONTROL` | `A2_FORMAL_CONTROL` |
| 3 | `A3_EVALUATIVE` | `A3_DEFAULT` | `A3_EVALUATIVE` |

Control Ayame seq2 turn 3 branched to `A3_DEFAULT` (different player stimulus) due to presentation-derived predicate evaluation — retained as experimental evidence.

---

## 9. Objective correctness results

All **8 committed sequences**: **0 objective issues** across all turns.

| Check | Result |
|-------|--------|
| PVR validation | `valid` on all committed turns |
| Round commit | all turns committed |
| `character_failure` | 0 on committed sequences |
| Presentation length | >0 on all committed turns |

Failed attempts excluded from correctness summary (infrastructure/runtime, not semantic scores).

---

## 10. Storyteller preamble work removed (ablated vs control)

| Scope | Control ST preamble | Ablated ST preamble | Removed |
|-------|--------------------:|--------------------:|--------:|
| All 8 sequences (committed) | 32 | 0 | **32** |
| Arkham (4 seq) | 20 | 0 | 20 |
| Ayame (4 seq) | 12 | 0 | 12 |

Per-sequence preamble counts (committed):

| Sequence | ST preamble |
|----------|------------:|
| control arkham seq1 | 10 |
| control arkham seq2 | 10 |
| control ayame seq1 | 6 |
| control ayame seq2 | 6 |
| ablated arkham seq1 (replacement) | 0 |
| ablated arkham seq2 | 0 |
| ablated ayame seq1 | 0 |
| ablated ayame seq2 | 0 |

---

## 11. Storyteller post-commit residual work

Post-commit Storyteller **intentionally retained** on both arms.

| Arm | ST post-commit (4 seq total) |
|-----|----------------------------:|
| control | 18 |
| ablated | 20 |

Ablated arm still receives post-commit Storyteller inferences (`storyteller_post_commit_issue_pressure` etc.). Slight ablated excess (+2) is not arm-config driven; reflects runtime/stochastic variation within retained path.

---

## 12. Plot work parity

| Arm | Plot inferences (4 seq) | Mean per sequence |
|-----|------------------------:|------------------:|
| control | 32 | 8.0 |
| ablated | 35 | 8.75 |

Plot cognition **ON** on both arms. Small count delta (+3 total) within normal run variance; no plot bypass on ablated arm.

---

## 13. Architectural-work delta (committed sequences)

| Metric | Control | Ablated | Δ (control − ablated) |
|--------|--------:|--------:|----------------------:|
| Total inferences | 98 | 55 | +43 |
| ST preamble | 32 | 0 | +32 |
| ST post-commit | 18 | 20 | −2 |
| Plot | 32 | 35 | −3 |
| Wall time (min) | 61.31 | 49.26 | +12.05 |

**Critical-path change:** Ablated arm removes synchronous preamble Storyteller from every turn; post-commit Storyteller and Plot remain on critical path.

Per-turn architectural accounting (inference kinds, wall ms, reasoning tokens, continuity index, actor routing) recorded in sequence JSON under primary evidence root.

---

## 14. Wall-time / reliability observations

| Observation | Detail |
|-------------|--------|
| Control mean wall (4 seq) | 15.33 min/seq |
| Ablated mean wall (4 seq) | 12.32 min/seq |
| Arkham control mean | ~23.0 min/seq (5 turns) |
| Arkham ablated mean | ~19.4 min/seq |
| Ayame control mean | ~7.65 min/seq |
| Ayame ablated mean | ~5.21 min/seq |
| Reliability | 2 ablated Arkham slots required retry/replacement (`character_failure`) |
| Outliers | Failed attempts flagged; not in blind packet |

Wall-time reduction on ablated arm correlates with removed preamble work; **not** disclosed in blind packet.

---

## 15. Continuity / state observations

- All committed sequences advanced continuity turn index monotonically within session.
- Multi-turn sessions used single `hg_session_id` per sequence (longitudinal trajectory preserved).
- No continuity mutation anomalies flagged in objective checks.
- Branch trajectories logged; predicate selection independent of arm identity.

---

## 16. Arkham objective comparison (control vs ablated)

| Metric | Control (2 seq) | Ablated (2 seq) |
|--------|----------------:|----------------:|
| Committed turns | 10/10 | 10/10 |
| Objective issues | 0 | 0 |
| ST preamble | 20 | 0 |
| ST post-commit | 15 | 16 |
| Plot | 25 | 28 |
| Branch parity (turns 3–5) | identical player stimuli | identical |
| Branch divergence (turn 2) | presentation-driven | presentation-driven |

---

## 17. Ayame objective comparison (control vs ablated)

| Metric | Control (2 seq) | Ablated (2 seq) |
|--------|----------------:|----------------:|
| Committed turns | 6/6 | 6/6 |
| Objective issues | 0 | 0 |
| ST preamble | 12 | 0 |
| ST post-commit | 3 | 4 |
| Plot | 7 | 7 |
| Branch parity | seq1 identical; seq2 turn-3 branch diverged (`A3_DEFAULT` vs `A3_EVALUATIVE`) |

---

## 18. Expansion-trigger use

| Field | Value |
|-------|-------|
| Triggered | **Yes** — once |
| Condition | #2 contaminated/incomplete sequence |
| Affected | ablated / arkham_stress / rep1 |
| Reason insufficient | Two full-sequence attempts failed at turn 2 (`character_failure`); no committed ablated Arkham seq1 for causal comparison |
| Additional sequence | `D01L-ablated-arkham_stress-seq1-a1` (replacement run, separate evidence root merged into primary) |
| Bound | Within +1 sequence/scenario/arm maximum |

No other expansion triggers invoked.

---

## 19. Blind sequence packet path

```
data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z/outputs/issue201-d01l-blind-sequence-packet.json
```

- Schema: `issue201_blind_sequence_packet_v1`
- 8 sequences: `SEQ-A` … `SEQ-H`
- 32 turn-presentations total
- Primary endpoint rubric: 10 sequence-level dimensions (listed in packet)
- Secondary: per-turn 11-dimension rubric (to be scored separately if needed)

**Governance transport doc:** `governance/records/issue201-d01l-governance-blind-transport.md`

---

## 20. Answer-key path (concealed)

```
data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z/outputs/issue201-d01l-blind-sequence-answer-key.json
```

**Do NOT transport to Governance until scoring is locked.**

---

## 21. Blinding-integrity verification

| Check | Result |
|-------|--------|
| Arm identity in packet | **Absent** |
| Storyteller status in packet | **Absent** |
| Session IDs in packet | **Absent** |
| Inference / latency / tokens in packet | **Absent** |
| Branch logs in packet | **Absent** |
| Architecture labels in packet | **Absent** |
| Sequence count | 8 (matches authorized tranche) |
| Labels | SEQ-A … SEQ-H unique |
| Answer key separated | **Yes** |
| Failed attempts excluded | **Yes** (1 failure record preserved outside packet) |
| Automated grep (`arm_id`, `storyteller`, `hg-session`, `inference`) | **No matches** in blind packet |

---

## 22. Artifact disposition

| Artifact | Path | Disposition |
|----------|------|-------------|
| D-01-L harness | `v2/rp_runtime/scripts/issue201-package-d-d01l-longitudinal.mjs` | Committed `0eb0cd6` |
| Player policy module | `v2/rp_runtime/scripts/lib/issue201-d01l-player-policy.mjs` | Committed `0eb0cd6` |
| Frozen policies | `governance/records/issue201-d01l-policies/` | Committed `fc80461` |
| Policy manifest | `governance/records/issue201-d01l-policies/d01l_policy_manifest.json` | Committed (this tranche) |
| Stage-3 per-dimension export | `governance/records/issue201-stage3-governance-blind-scores-per-dimension-export.md` | Committed `0eb0cd6` |
| Longitudinal report JSON | `.../issue201-package-d-d01l-longitudinal-report.json` | Gitignored evidence |
| Sequence JSON + presentations | `.../outputs/D01L-*` | Gitignored evidence |
| Blind packet | `.../outputs/issue201-d01l-blind-sequence-packet.json` | Gitignored — **transport to Governance** |
| Answer key | `.../outputs/issue201-d01l-blind-sequence-answer-key.json` | Gitignored — **concealed** |
| Merge helper | `tools/investigation/merge_d01l_evidence.py` | Commit (this tranche) |
| Summarize helper | `tools/investigation/summarize_d01l_report.py` | Commit (this tranche) |
| **This execution record** | `governance/records/issue-201-package-d-d01l-execution-2026-09-14.md` | Commit (this tranche) |
| Blind transport | `governance/records/issue201-d01l-governance-blind-transport.md` | Commit (this tranche) |

---

## 23. Exact Governance scoring request

**Request:** Governance AI blind scoring of D-01-L complete-sequence bundles.

1. **Transport** `issue201-d01l-blind-sequence-packet.json` + scenario briefings (`governance/records/issue201-stage2-human-evaluator-worksheet.md` or equivalent briefing keys `arkham_mess_hall_stress`, `ayame_household_entry`).
2. **Primary endpoint:** Score each of 8 anonymous sequences (`SEQ-A` … `SEQ-H`) on the **10 sequence-level dimensions** (1–5 scale). Complete chronological sequence is the evaluation unit.
3. **Secondary endpoint (optional, separate):** Per-turn 11-dimension rubric — keep results separate; do **not** composite with primary.
4. **Lock scores before decode.** Do not request answer key, arm mapping, or architectural metadata until scoring is locked.
5. **Do not interpret** from architecture identity. Implementation AI has **not** decoded semantic quality.
6. After locked scoring, Governance may request answer key for between-arm causal comparison per pre-registered interpretation rules in `issue-201-package-d-d01l-consensus-refinement-2026-09-14.md`.

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**

---

## Pre-execution durability (Stage-3 linkage)

| Requirement | Status |
|-------------|--------|
| Stage-3 per-dimension matrix exported | `governance/records/issue201-stage3-governance-blind-scores-per-dimension-export.md` |
| Locked sample means retained | `governance/records/issue201-stage3-governance-blind-scores-locked.json` |
| Scores locked before architecture decode | Recorded in `issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` |
| Per-dimension artifact linked from decode record | **Yes** — see Stage-3 decode synthesis §2 |

---

## Interpretation boundary (not applied)

This report stops at blind-packet readiness. No semantic verdict on preamble Storyteller value. Null or positive results apply only to **synchronous preamble placement**, not global Storyteller removal, invocation frequency, or post-commit design.
