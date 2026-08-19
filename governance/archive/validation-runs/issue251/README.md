# Issue #251 — exit-ontology investigation artifacts

**GitHub:** [Issue #251](https://github.com/KizzieFae/Holy_Grail_RP/issues/251) · **Doctrine index:** [CANONICAL_DOCTRINE.md](./CANONICAL_DOCTRINE.md)

**Current posture:** Doctrine-isolation **frozen**. **Governance-review candidate:** `simplified_structural_v1` on `v1_next7_issue251_physical_severance_guarded_v1`. **Not** production default. **Not** `validated`.

---

## Governance-review candidate (run / evidence)

| Field | Value |
|-------|--------|
| **Topology** | `v1_next7_issue251_physical_severance_guarded_v1` |
| **Variant** | `simplified_structural_v1` |
| **Full suite** | n=103 (`run_i251_physical_severance_guarded_simplified_fullsuite.py`) |
| **Focused slice** | n=55 threshold/guard (`run_i251_physical_severance_guarded_simplified_focused.py`) |

```bash
cd autogen_rp/python

# Topology + preflight tests
pytest tests/test_issue_240_prompt_topology.py tests/test_i251_doctrine_preflight.py -q

# Full simplified structural suite (requires DEEPSEEK_API_KEY)
python validation_runs/issue251/run_i251_physical_severance_guarded_simplified_fullsuite.py

# Focused threshold/guard slice
python validation_runs/issue251/run_i251_physical_severance_guarded_simplified_focused.py
```

**Tracked markdown summaries (commit-friendly):**

| File | Role |
|------|------|
| `i251_physical_severance_guarded_simplified_fullsuite_comparison.md` | Arm A/B/old C vs simplified aggregates |
| `i251_physical_severance_guarded_simplified_fullsuite_guard_delta.md` | Per-case guard FP |
| `i251_physical_severance_guarded_simplified_fullsuite_gm3_summary.md` | GM3 cohort |
| `i251_physical_severance_guarded_finalpatch_focused_delta.md` | **Rejected** finalpatch evidence |

**Local JSON matrices** (`*_matrix.json`, `*_summary.json`) from harness runs — evidence bundles; may be gitignored or untracked.

---

## Historical artifact families

### Hybrid awareness era (Arm A, n=32 broad matrix)

- **Topology:** `v1_next7_issue251_awareness_clean`
- **Runners:** `run_i251_exit_stability_matrix.py`, `run_i251_anchor_guard_experiment.py`, `run_i251_scenario_matrix.py`
- **Artifacts:** `i251_exit_stability_matrix.json`, `i251_exit_stability_matrix_adjudicated.json`, `i251_anchor_matrix.json`, `i251_guard_matrix.json`

### Doctrine isolation Phase 1 (Arm A vs B)

- **Runner:** `run_i251_doctrine_isolation_phase1.py`
- **Spec:** [PHYSICAL_SEVERANCE_DOCTRINE_DRAFT.md](./PHYSICAL_SEVERANCE_DOCTRINE_DRAFT.md)
- **Artifacts:** `i251_doctrine_isolation_phase1_matrix.json`, `i251_doctrine_isolation_phase1_summary.json`

### Physical / guarded comparators (Arm B, old C)

- **Runners:** `run_i251_physical_severance_full_suite.py`, `run_i251_physical_severance_guarded_suite.py`
- **Summaries:** `i251_physical_severance_full_suite_gm3_summary.md`, `i251_physical_severance_guarded_suite_guard_failures.md`

### Adjudication layer (#243-B reuse)

- `i251_replay_adjudication.py`, `run_i251_adjudicate_matrix.py`, `i251_doctrine_alignment.py`
- `i251_doctrine_preflight.py` — scoped contamination checks

---

## Metrics (S1–S4)

| Tier | Lane |
|------|------|
| **S1** | Semantic intent vs doctrine (**#251**) |
| **S2** | Parse + schema + ingress (**#249**) |
| **S3** | Authority accept |
| **S4** | Committed (diagnostic; **#250** when retry flattens) |

**#251 genuine miss:** S1 fail **and** S2 pass.

---

## Lane separation

**#224** continuity · **#246** adjudication (observational) · **#249** ingress · **#250** retry · **#251** exit ontology

See `validation_runs/issue249/` for proposal-schema lineage.
