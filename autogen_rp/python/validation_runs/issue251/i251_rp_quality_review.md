# Issue #251 — RP quality review scaffold

**Experiment:** `issue251_awareness_clean_v1`  
**Reviewer:** _TBD_  
**Date:** _TBD_

Sample 3–5 turns per core scenario from `runs/baseline/` vs `runs/treatment/` for:

| Scenario | Baseline path | Treatment path | Reviewed? |
|----------|---------------|----------------|-----------|
| arrival_setup | `runs/baseline/arrival_setup/` | `runs/treatment/arrival_setup/` | [ ] |
| emotional_loop_2char | … | … | [ ] |
| conflict_3char | … | … | [ ] |
| strong_user_steer | … | … | [ ] |
| passive_observer | … | … | [ ] |

## Rubric (per scenario, comparative)

| Dimension | Baseline (1–5) | Treatment (1–5) | Regression? |
|-----------|----------------|-----------------|-------------|
| Character voice fidelity | | | |
| Scene coherence | | | |
| Conversational naturalness | | | |
| Emotional continuity | | | |
| Pacing | | | |
| Over-mechanical behavior | | | |
| Instruction leakage | | | |
| Inappropriate exit churn | | | |
| Narrator/render continuity | | | |

**Leakage grep** (automated hint): search session outputs for `covered_change`, `off_focal`, `semantic_evaluation` inside character dialogue.

## Churn check

From `i251_scenario_matrix_results.json` / emission maps:

- `off_focal_count` delta treatment − baseline  
- `oscillation_pairs` (off_focal → reentry within 2 turns)  

**Pass:** no material regression on ≥2 core scenarios; churn within agreed caps.

## Verdict

- [ ] Pass — proceed to validation review  
- [ ] Fail — RP regression  
- [ ] Inconclusive — insufficient samples  
