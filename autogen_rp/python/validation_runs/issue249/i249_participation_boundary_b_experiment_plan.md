# Issue #249 Phase B — Participation Boundary Ontology Experiment Plan

Investigation-only. Non-canonical. Default topology remains `v1_next7`.

## Hypothesis

Concise dual-requirement participation-boundary teaching improves genuine missed-emission behavior without reintroducing malformed proposals or over-triggering tethered participation cases.

## Experimental topology

| Field | Value |
|---|---|
| Name | `v1_next7_participation_boundary_b` |
| Env | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_boundary_b` |
| Base stack | `v1_next7` + Phase A schema teaching (allowed/forbidden keys, examples, OUTPUT RULES mirror) |
| Delta | Replace schema_a fuzzy threshold line with participation-boundary block |
| Manifest markers | `proposal_schema_teaching_v249_a` + `participation_boundary_teaching_v249_b` |

## Rerun matrix

### Primary (genuine missed-emission / threshold)

| ID | Session | Turn | Actor | Expected |
|---|---|---|---|---|
| GM3 | 912 | 12 | willow_reeves | `off_focal` |
| GM4 | 910 | 7 | willow_reeves | `off_focal` |
| GM2 | 912 | 9 | willow_reeves | P04 rebound semantics |
| GM2-depart | 912 | 11 | willow_reeves | departure setup → `off_focal` |

### Controls

| ID | Session | Turn | Actor | Expected |
|---|---|---|---|---|
| CTRL-schema | 908 | 3 | willow_reeves | valid schema + covered emission |
| CTRL-threshold | 908 | 5 | willow_reeves | `no_covered_change` (P02) |
| CTRL-noop | 908 | 11 | willow_reeves | `no_covered_change` (P05) |
| CTRL-malformed-fixed | 908 | 7 | willow_reeves | valid schema if covered |

### Comparator

| ID | Session | Turn | Actor | Expected |
|---|---|---|---|---|
| C852 | 852 | 8 | hannah_lovelace | covered path, no regression |

## Method

Single-turn first-attempt replay from committed audit `input_messages[system]`:

1. Load committed character audit artifact.
2. Apply `apply_issue240_v1_next7_participation_boundary_b_prompt_overrides`.
3. One LLM call (no retry garnish).
4. Parse + ingress validate.
5. Compare against committed baseline and Phase A (`i249_proposal_schema_experiment_results.json`).

## Primary metrics

1. Proposal emission rate (primary cohort)
2. Schema validity rate
3. Ingress pass rate
4. Kind correctness (`off_focal` vs `reentry`)
5. Over-trigger rate on controls
6. Tether preservation on threshold/noop controls
7. Malformed-field regression (forbidden keys)

## Pre-rerun validation

```bash
cd autogen_rp/python
pytest tests/test_issue_240_prompt_topology.py tests/test_issue240_semantic_evaluation.py
```

## Execution

```bash
cd autogen_rp/python
set RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_boundary_b
python validation_runs/issue249/run_i249_participation_boundary_b_experiment.py
```

Requires `DEEPSEEK_API_KEY`.

## Out of scope

- Production default change
- Canonical documentation update
- Runtime legality changes
- Retry redesign (#250)
