# Issue #201 — D-10 Locked Primary Decode & Plot/Storyteller Pressure-Forensics Synthesis

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**Execution record:** `governance/records/issue-201-package-d-d10-execution-2026-09-15.md`  
**Locked scores:** `governance/records/issue201-d10-governance-blind-scores-locked.json`  
**Score-lock commit:** `d36a023`  
**Execution anchor:** `1b8ff16`  
**Design anchor:** `d13f2a0`  
**Evidence root:** `data/investigation_runs/issue201-package-d-d10-2026-09-15T01-20-29-181Z/`  
**Forensics extract:** `data/investigation_runs/issue201-package-d-d10-2026-09-15T01-20-29-181Z/d10-pressure-forensics-decode.json`

**Scoring integrity:** Governance supplied and locked all primary longitudinal scores while sequence identities were anonymous (`scored_before_answer_key_reveal: true`). Implementation AI records decode mapping and pressure forensics only; locked scores are not rescored or altered.

**Causal question (D-10):** Once Plot is persistent narrative cognition, does post-commit Storyteller independently create narrative-pressure information that materially improves subsequent RP, or is it duplicative?

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| D-10 execution | **Complete** (`1b8ff16`) |
| D-10 primary blind eval | **Complete, locked** (`d36a023`) |
| D-10 decode + pressure forensics | **Complete** (this record) |
| Final architectural verdict | **NOT rendered** — Governance gate |
| #201 synthesis | **Deferred** pending Governance evaluation |
| Production remediation | **NOT authorized** |

---

## 2. Blind-score lock artifact and integrity

| Item | Value |
|------|-------|
| Lock artifact | `governance/records/issue201-d10-governance-blind-scores-locked.json` |
| Lock commit SHA | **`d36a0237284a698537e84c9fdd7d6ade52b0b882`** |
| Answer key path (concealed until lock) | `.../outputs/issue201-d10-blind-sequence-answer-key.json` |
| Decode authorized | **After** lock commit only |

**Proof lock preceded answer-key read:** Locked JSON records `scored_before_answer_key_reveal: true` and was committed at `d36a023` before this decode synthesis. HEAD at lock was `d36a023`; answer-key mapping and forensics extraction were performed only after that commit.

---

## 3. Complete SEQ-A … SEQ-F decode mapping

| Label | Arm | Scenario | Sequence ID | Rep | Session ID | Post-commit activations | Locked mean |
|-------|-----|----------|-------------|----:|------------|------------------------:|------------:|
| SEQ-A | ablated | Ayame household entry | `D10-ablated-ayame_controlled-seq1-a1` | 1 | `hg-session-1f252e91-526a-4c96-81db-b8d1a32d8f5f` | 0 | 4.60 |
| SEQ-B | ablated | Arkham mess hall stress | `D10-ablated-arkham_stress-seq2-a1` | 2 | `hg-session-af3926fe-0020-413a-ba96-1ca7397927ec` | 0 | 4.50 |
| SEQ-C | control | Ayame household entry | `D10-control-ayame_controlled-seq1-a1` | 1 | `hg-session-2a788143-7dce-4e85-b89b-59059d54ae71` | 1 | 4.10 |
| SEQ-D | control | Arkham mess hall stress | `D10-control-arkham_stress-seq1-a2` | 1 | `hg-session-b09c6fd7-1914-4b1a-95df-7cd336cb330b` | 5 | 4.90 |
| SEQ-E | control | Arkham mess hall stress | `D10-control-arkham_stress-seq2-a2` | 2 | `hg-session-a725b12d-d414-4171-bf28-9832a4230921` | 4 | 4.20 |
| SEQ-F | ablated | Arkham mess hall stress | `D10-ablated-arkham_stress-seq1-a2` | 1 | `hg-session-7291aebe-cb7c-44ba-88d1-18009382d86b` | 0 | 4.80 |

**Arm definitions (both arms `skipStorytellerCognition: true` for preamble):**

- **Control:** post-commit Storyteller issue-pressure ON  
- **Ablated:** `skipLibrarianProposalGeneration: true` (post-commit ST proposals suppressed); Plot retained

---

## 4. Replication-level locked scores (10 dimensions + mean)

Governance-assigned; not recomputed.

| Label | Arm | Thread | Escal. | Agenda | Delayed | Momentum | Initiative | Loop avoid. | No early res. | Drift | Continuity | **Mean** |
|-------|-----|-------:|-------:|-------:|--------:|---------:|-----------:|------------:|--------------:|------:|-----------:|---------:|
| SEQ-A | ablated | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 5 | 4 | 5 | **4.60** |
| SEQ-B | ablated | 5 | 4 | 5 | 4 | 4 | 5 | 3 | 5 | 5 | 5 | **4.50** |
| SEQ-C | control | 5 | 4 | 5 | 4 | 3 | 4 | 3 | 5 | 4 | 4 | **4.10** |
| SEQ-D | control | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | **4.90** |
| SEQ-E | control | 5 | 4 | 5 | 4 | 3 | 4 | 2 | 5 | 5 | 5 | **4.20** |
| SEQ-F | ablated | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 5 | **4.80** |

### Blind qualitative observations (preserved verbatim)

Cross-sequence blind observation: All six sequences retained basic narrative threads and NPC agendas (thread/agenda persistence 5/5). No obvious narrative-memory-collapse population. Principal discrimination is in escalation, delayed consequences, momentum, initiative, reactive-loop avoidance, and whether remembered pressure becomes consequential development.

- **SEQ-D (4.90):** Strongest sequence. Situation genuinely develops; guards narrow aisle; Ivy withdraws seat by Turn 5.
- **SEQ-F (4.80):** Excellent Harley trajectory; constraints converted into performance; minor Turn-5 spatial drift.
- **SEQ-A (4.60):** Strong Ayame agenda persistence; threshold organizing conflict; minor spatial tension.
- **SEQ-B (4.50):** Strong but recursive; Ivy reformulates similar pressure; lower loop avoidance.
- **SEQ-E (4.20):** Clearest looping; remembers state without advancing; radio late provides external development.
- **SEQ-C (4.10):** Competent but least progressive; static threshold interview.

> **Governance distinction (pre-decode):** Remembering pressure is not the same thing as advancing pressure.

---

## 5. Overall arm aggregates

| Arm | Sequences | Replication means | Arm average |
|-----|-----------|-------------------|------------:|
| **control** (post-commit ST ON) | SEQ-C, SEQ-D, SEQ-E | 4.10, 4.90, 4.20 | **4.40** |
| **ablated** (post-commit ST OFF) | SEQ-A, SEQ-B, SEQ-F | 4.60, 4.50, 4.80 | **4.63** |

**Between-arm delta (control − ablated):** **−0.23** (ablated higher)

---

## 6. Arkham aggregates

| Arm | Sequences | Means | Average |
|-----|-----------|------:|--------:|
| control | SEQ-D, SEQ-E | 4.90, 4.20 | **4.55** |
| ablated | SEQ-B, SEQ-F | 4.50, 4.80 | **4.65** |

**Arkham delta (control − ablated):** **−0.10** (ablated higher)

---

## 7. Ayame aggregates

| Arm | Sequences | Means | Average |
|-----|-----------|------:|--------:|
| control | SEQ-C | 4.10 | **4.10** |
| ablated | SEQ-A | 4.60 | **4.60** |

**Ayame delta (control − ablated):** **−0.50** (ablated higher; n=1 per arm)

---

## 8. Per-dimension control vs ablated matrix

Replication-level values preserved in §4. Arm means below (n=3 per arm).

| Dimension | Control mean | Ablated mean | Δ (control − ablated) |
|-----------|-------------:|-------------:|----------------------:|
| Thread persistence | 5.00 | 5.00 | 0.00 |
| Escalation coherence | 4.33 | 4.67 | −0.33 |
| Agenda persistence | 5.00 | 5.00 | 0.00 |
| Delayed consequences | 4.33 | 4.33 | 0.00 |
| Scene momentum | 3.67 | 4.33 | −0.67 |
| Cross-turn initiative | 4.33 | 5.00 | −0.67 |
| Reactive-loop avoidance | 3.00 | 3.67 | −0.67 |
| Premature-resolution avoidance | 5.00 | 5.00 | 0.00 |
| Plot-drift control | 4.67 | 4.33 | +0.33 |
| Cross-turn emotional/narrative continuity | 4.67 | 5.00 | −0.33 |

**Ablated advantage dimensions:** momentum (−0.67), initiative (−0.67), reactive-loop avoidance (−0.67), escalation coherence (−0.33), continuity (−0.33).  
**Control advantage:** plot-drift control (+0.33).  
**Tied at ceiling:** thread, agenda, premature-resolution avoidance.

---

## 9. Failed-attempt / reliability context

| Failed attempt | Classification | Replacement | In blind packet |
|----------------|----------------|---------------|-----------------|
| `D10-control-arkham_stress-seq1-a1` | `character_failure` turn 1 | `seq1-a2` → **SEQ-D** | a2 only |
| `D10-ablated-arkham_stress-seq1-a1` | `character_failure` turn 5 | `seq1-a2` → **SEQ-F** | a2 only |
| `D10-control-arkham_stress-seq2-a1` | `character_failure` turn 1 | `seq2-a2` → **SEQ-E** | a2 only |

No intervention-specific failure pattern. All 6/6 committed sequences (28 turn-presentations) in blind packet. Preflight: **PROCEED**.

---

## 10. Post-commit activation summary

| Label | Arm | Eligible turns | Post-commit ST inference events | Notes |
|-------|-----|---------------:|--------------------------------:|-------|
| SEQ-A | ablated | — | 0 | Hook skipped by arm |
| SEQ-B | ablated | — | 0 | Hook skipped by arm |
| SEQ-C | control | 4 | 1 | Ayame confirmatory calibration |
| SEQ-D | control | 5 | 5 | Highest activation density |
| SEQ-E | control | 5 | 4 | Looping sequence despite activations |
| SEQ-F | ablated | — | 0 | Highest ablated score without post-commit ST |

**Control arm totals:** 16 post-commit ST inference records across 3 sequences (10 activation-eligible turns). **Ablated:** 0.

**Causal isolation:** Ablated arm shows zero post-commit Storyteller inference with Plot retained on both arms.

---

## 11. Recovered Storyteller pressure dataset (control arm)

Source: execution-evidence `storyteller_post_commit_issue_pressure` attempts (`response.assistant_text` → `proposals[].proposed_payload`).

| Metric | Value |
|--------|------:|
| Total ST proposals recovered | 18 |
| Proposal kind | `issue_tension_pressure` (S4A sole active kind) |
| Host accepted | 18/18 |
| Continuity accepted count | 1 per proposal |
| `durable_mutation_applied` | **false** for all 18 |
| `overlay_count_after` (harness forensics) | **0** for all turns |
| `plot_pressure_count_after` (harness forensics) | **0** for all turns |

Representative SEQ-D Turn 1 (`da52d008-5b01-4d9b-ab9a-badf80081cf9`):

- `issue_ref`: `issue_2026-09-15T01:25:35.136735+00:00_1`
- `semantic_unmet_condition`: stable presence/positioning contested; public invitation is claim-test not resolution
- `stakes_summary`: escalating tension; pressure mounts; no stable positioning secured

Full row-level dataset: `d10-pressure-forensics-decode.json` → `st_plot_comparison`.

---

## 12. Recovered Plot-pressure dataset (control arm)

Source: execution-evidence `plot_cognition_init` / `plot_cognition_update` (`proposal.pressures` / `update_proposal.pressures`).

| Metric | Value |
|--------|------:|
| Plot pressure rows recovered | 40 |
| Init pressures (SEQ-D T1 example) | `pressure-arkham-mess-hall-containment` — sealed guard-monitored communal space |
| Update pressures (example) | `pressure-harley-ivy-mismatched-tempo`, `pressure-ward-attention-converging`, `pressure-guard-response-imminent` |

Plot cognition ran on all control turns (30 plot inferences across 3 control sequences per execution record). Same-turn plot pressure proposals were present on 16/18 ST-proposal turns.

Full dataset: `d10-pressure-forensics-decode.json` → `plot_dataset`.

---

## 13. Storyteller vs Plot pressure relationship table

Lexical Jaccard used as **screening only**; not equivalence proof.

| Structural class | Count | Interpretation |
|------------------|------:|----------------|
| `unique_st` | 18 | ST issue-pressure semantics do not lexically overlap Plot strategic pressures at screening thresholds |
| `overlapping` | 0 | — |
| `complementary` | 0 | — |
| `equivalent` | 0 | — |
| `contradictory` | 0 | — |

**Representative paired comparison (SEQ-D T2):**

| Layer | Example text | Issue linkage |
|-------|--------------|---------------|
| Storyteller | "Harley's public repositioning… presence_conflict unresolved" | `issue_2026-09-15T01:25:35…_1` |
| Plot | "Harley wants to move first and loudly; Ivy's willingness to absorb is finite" | strategic pressure id `pressure-harley-ivy-mismatched-tempo` |

**Candidate semantic relationship:** **complementary / non-redundant at text level** — Plot encodes strategic character-tempo framing; ST encodes continuity-issue unmet conditions tied to specific `issue_ref`. No evidence of direct semantic duplication; also no evidence ST text was structurally consumed into Plot overlay in this run.

Ambiguous pairs preserved in forensics JSON for Governance review.

---

## 14. Storage / projection / consumption / consequence analysis

Pipeline state per control ST proposal (n=18):

| Stage | Count | Evidence |
|-------|------:|----------|
| 1. Generated | 18 | Post-commit inference ran; proposals parsed from evidence |
| 2. Accepted | 18 | `host_accepted: true`, `continuity_accepted_count: 1` |
| 3. Stored (durable overlay) | **0** | `durable_mutation_applied: false`; `overlay_count_after: 0`; `issue_pressure_semantic_overlays: {}` |
| 4. Projected (Director/Character) | **unavailable** | No recoverable Director/Character projection of ST overlays in evidence or V1 session files |
| 5. Consumed | **indeterminate** | Cannot tie individual accepted proposals to isolated downstream decisions |
| 6. Consequential | **indeterminate at pressure level** | SEQ-D shows strong development with 5 activations; SEQ-E shows looping with 4 activations; SEQ-F shows strong development with 0 activations |

**Lexical projection heuristic (weak):** 14/18 proposals show ≥2 token hits in next-turn presentation text. This indicates surface continuity only; not causal consumption proof.

**Governance cost chain applied:** Cost → unique information → consequential decision → observable benefit. Steps 3–6 fail or remain indeterminate for durable ST overlay persistence in this evidence set.

---

## 15. Unavailable forensic evidence and why

| Field | Status | Reason |
|-------|--------|--------|
| `issue_pressure_semantic_overlays` in V1 session JSON | unavailable | V1 chat schema lacks embedded `continuity_manager` overlays |
| `scene_pressures` post-commit | unavailable | Not captured in harness turn forensics or session persistence |
| Plot overlay sidecar for D-10 sessions | unavailable | No `_plot_cognition_overlay` files for D-10 session IDs |
| `plot_before` / `plot_after` pressure counts in harness | reads 0 | Harness fixture snapshot does not reflect live plot store state |
| Director projection of ST pressure | unavailable | Not in execution evidence for these turns |
| Character projection of ST pressure | unavailable | Not in execution evidence for these turns |
| Per-pressure causal consumption | indeterminate | Branch-path divergence and n=1–2 per scenario prevent isolation |

No production code was modified to reconstruct unavailable historical evidence.

---

## 16. Objective cost / accounting comparison (committed sequences)

From D-10 execution record (`1b8ff16`); not used in blind scoring.

| Metric | Control (3 seq, 14 turns) | Ablated (3 seq, 14 turns) | Δ |
|--------|--------------------------:|--------------------------:|--:|
| Post-commit ST inferences | 16 | 0 | +16 |
| ST preamble inferences | 0 | 0 | 0 |
| Plot inferences | 30 | 27 | +3 |
| Wall time (ms) | 3,270,860 | 3,660,988 | −390,128 (ablated slower) |
| Input tokens | 162,558 | 93,834 | +68,724 |
| Output tokens | 110,909 | 86,813 | +24,096 |
| Reasoning tokens | 74,786 | 58,190 | +16,596 |

Post-commit ST adds measurable inference/token cost on control arm. Blind longitudinal primary endpoint favors ablated arm (−0.23 overall).

---

## 17. Causal-isolation caveats

| Caveat | Detail |
|--------|--------|
| Small n | 3 sequences per arm; 1 Ayame pair only |
| Branch divergence | Arkham replications differ (e.g., SEQ-D T2 `P2_HARLEY_DOMINANT` vs SEQ-E T2 `P2_DEFAULT`) |
| Replacement evidence | SEQ-D, SEQ-E, SEQ-F from authorized a2 replacements after `character_failure` |
| Overlay persistence gap | Accepted ST proposals did not produce durable overlay mutations in captured evidence |
| Activation ≠ outcome | SEQ-E high activation + low loop-avoidance score; SEQ-F zero activation + high score |
| Scenario split | Arkham Δ −0.10; Ayame Δ −0.50 — opposite direction from D-01-L Ayame pattern |
| Preamble parity | Both arms `skipStorytellerCognition: true` — isolates post-commit ST only |

---

## 18. Prospective D-10 classification evidence (NOT a Governance verdict)

Evidence mapped to interpretation categories. **Governance must render the final architectural verdict.**

### Unique post-commit ST narrative-pressure value

**Not supported by primary blind endpoint.** Overall Δ = −0.23 (ablated higher). Arkham Δ = −0.10 (ablated higher). Ayame Δ = −0.50 (ablated higher). Best sequence overall is control SEQ-D (4.90) but second-best is ablated SEQ-F (4.80) without any post-commit ST. Worst control SEQ-E (4.20) had 4 post-commit activations.

### Duplicative / Plot-subsumable

**Partially consistent with pressure-layer evidence, not proven.** ST proposals target continuity-issue unmet conditions; Plot pressures target strategic scene framing. Lexical screening shows no overlap; semantic layers appear complementary. However, accepted ST overlays did not durably persist in captured evidence — limiting proof that ST added information Plot lacked in runtime state.

### Complexity-conditioned value

**Weak signal only.** Both scenarios favor ablated in this sample; Ayame split larger (−0.50) but n=1 per arm.

### Inconclusive / confounded

**Partially applicable.** Overlay persistence failure in forensic capture, small n, branch divergence, and activation/outcome decoupling (SEQ-E vs SEQ-F) prevent clean causal attribution from blind scores alone.

### Potentially movable / deferrable post-commit ST

**Consistent with blind scores, not proven.** Ablated arm matched or exceeded control on primary longitudinal rubric while eliminating all post-commit ST work. Does not prove redundancy — could reflect confounds — but does not demonstrate required unique value.

---

## 19. Exact Governance decisions required next

1. **Render D-10 architectural verdict** on post-commit Storyteller issue-pressure value using locked blind scores, decode mapping, and pressure forensics in this record.
2. **Adjudicate overlay persistence gap** — accepted proposals with `durable_mutation_applied: false` and zero overlay counts: instrumentation defect, expected behavior, or evidentiary invalidation of pressure-propagation claims?
3. **Decide whether supplementary Host/session forensics** (plot overlay sidecar recovery, continuity overlay extraction) are required before #201 synthesis.
4. **Authorize or defer #201 Package D synthesis** and any production remediation — neither is authorized by this record.
5. **Confirm issue phase** — remain `investigating` unless Governance advances per Package D workflow.

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**

---

## 20. Durable record / commit state

| Artifact | Status |
|----------|--------|
| Blind scores locked | `d36a023` — `governance/records/issue201-d10-governance-blind-scores-locked.json` |
| Decode synthesis (this file) | committed with decode forensics commit (see Issue #201 comment) |
| Forensics JSON | `data/investigation_runs/.../d10-pressure-forensics-decode.json` |
| Answer key | unchanged; decode performed post-lock only |
| Production code | unchanged |
| Final architectural verdict | **deferred to Governance**
