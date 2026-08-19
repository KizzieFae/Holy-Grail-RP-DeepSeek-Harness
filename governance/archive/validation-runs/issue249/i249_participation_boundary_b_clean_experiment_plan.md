# Issue #249 Phase B.2 — Clean Ontology Isolation Experiment Plan

Investigation-only. Non-canonical. Default topology remains `v1_next7`.

## Hypothesis

The prior Phase B negative result may have been caused by **ontology conflict contamination** (participation arc/focus capsules, margin/tether framing, fuzzy threshold, participation decision frame) still active alongside the boundary block. Phase B.2 tests whether removing that conflicting language materially changes genuine missed-emission behavior.

## Experimental topology

| Field | Value |
|---|---|
| Name | `v1_next7_participation_boundary_b_clean` |
| Env | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_boundary_b_clean` |
| Base stack | Phase A schema teaching + approved participation-boundary block |
| Delta vs Phase B | Suppress participation interpretation capsules/heuristics; neutral opening; strip baked-in audit contamination on replay |
| Manifest markers | `proposal_schema_teaching_v249_a` + `participation_boundary_teaching_v249_b` + `participation_boundary_clean_isolation_v249_b2` |

## Rerun matrix

Same as Phase B (GM3, GM4, GM2, GM2-depart; CTRL-*; C852).

## Comparison layers

| Layer | Topology |
|---|---|
| Baseline | committed production |
| Phase A | `v1_next7_proposal_schema_a` |
| Phase B | `v1_next7_participation_boundary_b` (contaminated) |
| Phase B.2 | `v1_next7_participation_boundary_b_clean` |

## Pre-rerun validation

```bash
cd autogen_rp/python
pytest tests/test_issue_240_prompt_topology.py tests/test_issue240_semantic_evaluation.py -k "participation_boundary"
```

## Execution

```bash
cd autogen_rp/python
set RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_boundary_b_clean
python validation_runs/issue249/run_i249_participation_boundary_b_clean_experiment.py
```

Requires `DEEPSEEK_API_KEY`.

Dry-run artifact resolution only:

```bash
python validation_runs/issue249/run_i249_participation_boundary_b_clean_experiment.py --dry-run
```
