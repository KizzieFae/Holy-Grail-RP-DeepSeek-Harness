# Issue #251 — awareness-clean experiment artifacts

**Experiment:** `issue251_awareness_clean_v1`  
**Baseline:** `v1_next7`  
**Treatment:** `v1_next7_issue251_awareness_clean` (investigation-only; **canonical working doctrine** — see [CANONICAL_DOCTRINE.md](./CANONICAL_DOCTRINE.md))

**GitHub system of record:** [Issue #251](https://github.com/KizzieFae/Holy_Grail_RP/issues/251) (resume table at top of body). Evidence index: [comment #4537220243](https://github.com/KizzieFae/Holy_Grail_RP/issues/251#issuecomment-4537220243).

## Canonical doctrine (accepted)

Three-line severance + four-factor awareness block in `prompt_topology_issue240.py` when `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_issue251_awareness_clean`. Marker: `participation_severance_doctrine_issue251_canonical_v1`.

**Rejected:** continuity-preservation sentence; margin/deepen/reverse ontology restoration.

**Remaining failure type:** temporary / hesitation / threshold exits and departure-completion ambiguity (not broad non-exit FP).

## Run order

```bash
cd autogen_rp/python

# Topology tests
pytest tests/test_issue_240_prompt_topology.py::test_issue251_awareness_clean_topology tests/test_prompt_topology_manifest.py tests/test_i251_replay_adjudication.py -q

# Anchor + guard matrix (requires DEEPSEEK_API_KEY)
python validation_runs/issue251/run_i251_anchor_guard_experiment.py

# Cohort D scenario matrix
python validation_runs/issue251/run_i251_scenario_matrix.py

# Broad exit-stability matrix (treatment; includes adjudication post-pass)
python validation_runs/issue251/run_i251_exit_stability_matrix.py

# Adjudicate an existing matrix JSON without re-running LLM replays
python validation_runs/issue251/run_i251_adjudicate_matrix.py
```

Dry-run (no LLM):

```bash
python validation_runs/issue251/run_i251_anchor_guard_experiment.py --dry-run
python validation_runs/issue251/run_i251_scenario_matrix.py --dry-run
```

## Artifacts

| File | Contents |
|------|----------|
| [CANONICAL_DOCTRINE.md](./CANONICAL_DOCTRINE.md) | Canon status, evidence, narrowed failure type |
| `i251_scenario_matrix_plan.json` | Cohort D scenario list and turn caps |
| `i251_anchor_matrix.json` | GM3, 908-P01 × baseline/treatment × N=3 |
| `i251_guard_matrix.json` | False-positive guards + observational GM4/GM2-depart |
| `i251_exit_stability_matrix.json` | 32-case ordinary-exit matrix (deterministic) |
| `i251_exit_stability_matrix_adjudicated.json` | Broad matrix + adjudication_summary |
| `i251_min_clarification_ab_matrix.json` | Severance-only A/B |
| `i251_min_clarification_ab_v2_continuity_matrix.json` | Rejected continuity-preservation A/B |
| `i251_aggregate_metrics.json` | Summary S1 rates and acceptance helpers |
| `i251_rp_quality_review.md` | Human rubric scaffold |
| `runs/<arm>/<scenario_id>/` | Per-scenario `--metrics-out` from headless runner |

## Metrics (S1–S4)

- **S1** — semantic intent vs doctrine on first attempt  
- **S2** — parse + schema + ingress  
- **S3** — authority accept  
- **S4** — committed (diagnostic)  

**#251 miss:** doctrine requires emission, S1 false, S2 true.

## Adjudicated semantic layer (#243-B / #249 reuse)

Replay matrices attach an observational adjudication pass via `i251_replay_adjudication.py` (`evaluate_case` + #251 doctrine alignment). **Deterministic S1/S2 preserved; adjudication separate.** Required for meaning-heavy matrix readouts.

| File | Role |
|------|------|
| `i251_replay_adjudication.py` | Post-replay adjudication adapter |
| `run_i251_adjudicate_matrix.py` | Pilot post-process on saved matrix JSON |

## Historical comparison

See `validation_runs/issue249/` for proposal-schema and participation-boundary investigation lineage.
