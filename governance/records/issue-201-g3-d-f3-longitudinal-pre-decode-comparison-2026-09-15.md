# Issue #201 G3-D F3 — Longitudinal Plot/Scribe Pre-Decode Comparison Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**G3-C decode SHA:** `08b46fa` (QUALIFIED A2 SUPPORT)  
**Status:** Pre-decode — blind sequence packet prepared; answer key **not opened**

---

## 1. Authorization

G3-D F3 longitudinal Plot/Scribe validation **authorized**. G3-E and production: **not authorized**.

---

## 2. Arms (causal comparison)

| Arm | Topology |
|-----|----------|
| `a2_plot_on` | Accepted primary path + post-commit Plot/Scribe (outside player-visible critical path) |
| `a2_plot_off` | Same primary path; Plot/Scribe skipped |

Storyteller (preamble + post-commit) **absent** both arms.

---

## 3. Plot initialization contract

- Trigger: first post-commit lifecycle after Turn 1 commit (when Plot ON)
- Timing: after player-visible presentation completes
- Inputs: committed events, continuity state, scenario authority
- Plot OFF receives same continuity/scenario substrate without overlay updates
- Synchronous Plot: **no**

---

## 4. Sequence matrix (8/8 objective clean)

| Sequence | Arm | Scenario | Rep | Attempt | Committed |
|----------|-----|----------|-----|---------|-----------|
| G3D-F3-a2_plot_on-arkham_stress-seq1-a1 | plot ON | Arkham | 1 | 1 | yes |
| G3D-F3-a2_plot_on-arkham_stress-seq2-a1 | plot ON | Arkham | 2 | 1 | yes |
| G3D-F3-a2_plot_on-ayame_controlled-seq1-a1 | plot ON | Ayame | 1 | 1 | yes |
| G3D-F3-a2_plot_on-ayame_controlled-seq2-a1 | plot ON | Ayame | 2 | 1 | yes |
| G3D-F3-a2_plot_off-arkham_stress-seq1-a1 | plot OFF | Arkham | 1 | 1 | yes |
| G3D-F3-a2_plot_off-arkham_stress-seq2-a2 | plot OFF | Arkham | 2 | 2 | yes (replacement) |
| G3D-F3-a2_plot_off-ayame_controlled-seq1-a1 | plot OFF | Ayame | 1 | 1 | yes |
| G3D-F3-a2_plot_off-ayame_controlled-seq2-a1 | plot OFF | Ayame | 2 | 1 | yes |

**Replacement:** `a2_plot_off-arkham_stress-seq2` attempt 1 failed turn 4 (`not_committed`); attempt 2 succeeded.

---

## 5. Per-turn actor matrix (Arkham — both arms)

Harley/Ivy alternation across turns (Director obligation-driven):  
`T1:Harley → T2:Ivy → T3:Harley → T4:Ivy` (all 4 Arkham sequences).

Ayame: single-actor eligibility — Ayame all turns both arms.

---

## 6. Plot lifecycle (Plot ON)

| Sequence | T1 | T2 | T3 | T4 |
|----------|----|----|----|-----|
| arkham seq1 | init/fail | init/ok | reconciliation/ok | semantic_update/ok |
| arkham seq2 | init/ok | reconciliation/ok | semantic_update/ok | semantic_update/ok |
| ayame seq1 | init/ok | reconciliation/ok | semantic_update/ok | semantic_update/ok |
| ayame seq2 | init/fail | init/ok | reconciliation/ok | semantic_update/ok |

**Note:** 2/4 sequences had Turn-1 init `forensic_persistence_failed` (objective validation) then recovered on subsequent post-commit operations. Overlay file forensics returned empty in harness path — cross-turn pressure keys not surfaced to file extractor; plot inference attempts and post-commit wall time confirm lifecycle execution.

---

## 7. Efficiency (4 sequences per arm)

| Metric | Plot ON | Plot OFF |
|--------|---------|----------|
| Primary-RP sync LLM | 53 | 42 |
| Plot inferences | 12 | 0 |
| Critical-path wall (ms) | 466,318 | 448,391 |
| Plot post-commit wall (ms) | 155,567 | 0 |
| Operation wall (ms) | 1,072,741 | 1,057,679 |

---

## 8. Objective gates

- 8/8 sequences all turns committed
- Plot OFF: zero plot cognition
- Plot ON: expected post-commit lifecycle (12 plot inferences)
- Storyteller absent all sequences
- Prohibited support cognition absent (orientation, semantic eval, env, librarian)
- Private-knowledge leaks: 0 observed
- Sample-D spatial debt: carried forward, not modified

---

## 9. Blind packet

`data/investigation_runs/issue201-g3d-f3-2026-09-15T06-44-23-918Z/outputs/issue201-g3d-f3-blind-sequence-packet.json`

Answer key concealed. Blinding integrity: **pass** (regenerated).

---

## 10. Governance next action

Score blind sequence packet (SEQ-A–SEQ-H). Lock scores before decode. Do not authorize G3-E without separate action.
