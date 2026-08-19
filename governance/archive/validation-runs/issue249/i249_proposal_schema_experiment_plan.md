# Issue #249 Phase A — Proposal Schema Teaching Experiment Plan

Investigation-only. Non-canonical. Default topology remains `v1_next7`.

## Hypothesis

Concise explicit proposal-schema teaching reduces malformed first-attempt proposal failures in the #249 cohort without redesigning retry (#250) or participation calibration.

## Experimental topology

| Field | Value |
|---|---|
| Name | `v1_next7_proposal_schema_a` |
| Env | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_proposal_schema_a` |
| Base stack | `v1_next7` (participation frame, arc, active focus unchanged) |
| Teaching delta | Allowed keys, forbidden keys, `{char_name}` examples, one-line threshold, OUTPUT RULES mirror |
| Excluded | Verbose v1_next7 calibration prose, excursion_lifecycle JSON example, participation calibration A blocks |

## Cohort matrix

### Core malformed (M1–M7)

| ID | Session | Turn | Actor | Baseline invalid field(s) |
|---|---|---|---|---|
| M1 | 908 | R1T3 | Willow | `reason` |
| M2 | 908 | R1T5 | Willow | `reason` |
| M3 | 908 | R1T7 | Willow | `reason` |
| M4 | 908 | R1T9 | Willow | `character_id`, `reason` |
| M5 | 910 | R5T3 | Willow | `description` |
| M6 | 910 | R7T3 | Willow | `strategy`, `rationale` |
| M7 | 912 | R1T10 | Kizzie | `subject` |

### Secondary missed (X1–X3)

| ID | Session | Turn | Actor | Probe |
|---|---|---|---|---|
| X1 | 911 | R1T3 | Willow | P01 |
| X2 | 912 | R1T9 | Willow | P04 |
| X3 | 912 | R1T12 | Willow | CASE-3 |

### Comparator

| ID | Session | Turn | Actor | Baseline |
|---|---|---|---|---|
| C852 | 852 | R1T8 | Hannah | Bucket B accept (off_focal) |

## Rerun method

Single-turn first-attempt replay from source audit `input_messages[system]`:

1. Load committed character audit artifact for target turn.
2. Apply `apply_issue240_v1_next7_proposal_schema_a_prompt_overrides` (same scene context, schema teaching swapped).
3. One LLM call (no retry garnish).
4. Parse + `validate_issue240_semantic_evaluation_ingress`.
5. Record dual-layer metrics vs baseline `*_parse_retry_full.json` first attempt.

## Primary metrics

- First-attempt schema-valid rate (proposal keys + non-empty `character`)
- First-attempt ingress pass rate (`semantic_evaluation` block)
- Proposal shape correctness (allowed keys only)
- Authority reached (`evaluate_proposal_legality` accept when covered_change emitted)

## Secondary metrics

- Missed cohort: emission vs baseline (`covered_change` + proposals)
- Comparator: no regression on successful accept path
- Retry flattening: N/A in single-shot replay (tracked observationally from baseline only)

## Pre-rerun validation

1. Topology env gate resolves to `v1_next7_proposal_schema_a`.
2. Manifest marker `proposal_schema_teaching_v249_a` present.
3. `{char_name}` appears in JSON examples.
4. Semantic block contains allowed/forbidden lists and compact examples.
5. `pytest tests/test_issue_240_prompt_topology.py tests/test_issue240_semantic_evaluation.py` pass.

## Execution

```bash
cd autogen_rp/python
set RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_proposal_schema_a
python validation_runs/issue249/run_i249_proposal_schema_experiment.py
```

Requires `DEEPSEEK_API_KEY`.

## Out of scope

- Production default change
- Canonical documentation update
- Issue #249 closure / state transition
- Retry redesign (#250)
- Participation calibration A/B expansion
