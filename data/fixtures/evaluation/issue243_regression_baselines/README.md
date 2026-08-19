# Issue #243 regression baselines

Frozen corpus regression anchors for offline semantic evaluation (#243). **Observational only** — not runtime truth.

| File | Phase | Purpose |
|------|-------|---------|
| `willow_v1.json`, `final_viability_v1.json` | #243-A | Calibration labels from frozen #240 corpora |
| `willow_v1_eval.json`, `final_viability_v1_eval.json` | #243-B | Profile-scoped `corrected_category` eval snapshots |

## Authority boundary

These baselines diff **offline evaluation outputs**. They do **not**:

- gate runtime turns or continuity
- merge into `_audit_summary.json`
- replace `#233` `semantic_proposal_decision` or `scene_state_after` as runtime truth

## Operator read discipline (#243-D)

### Primary vs secondary fields

| Field | Role |
|-------|------|
| **`corrected_category`** | **Primary** #243 evaluation output |
| **`limitations[]`** | Scope, caveats, disclaimers — read with every judgment |
| **`legacy_lane`** | **Secondary** — historical F-code context (`legacy_f_code`, `legacy_f_code_label`, `legacy_taxonomy_status`, …) |
| **`legacy_classifier_misflag`** | Legacy tooling overfire signal — **not** runtime failure |

### `corrected_category` values

- `success` — profile-scoped alignment; not “runtime healthy” by itself
- `evaluator_defect` — evaluator/classifier-side concern (offline)
- `contract_limited` — lifecycle/net-state constraint (e.g. same-turn round-trip)
- `ambiguous_threshold` — **valid** threshold disagreement — do not force PASS/FAIL
- `true_semantic_miss` — offline miss signal — requires runtime corroboration to file a bug

### Legacy F-codes (F0–F7)

Investigation-era labels from #240 matrix tooling. Nested under `legacy_lane` so old evidence stays interpretable. **Not** primary contract-alignment truth.

`legacy_taxonomy_status`:

- `compatible` — cautious legacy mapping agrees with corrected category
- `superseded` — corrected layer replaces legacy failure reading (often with `legacy_classifier_misflag`)
- `ambiguous` — mapping intentionally withheld or uncertain
- `historical` — recorded for context; do not treat as runtime verdict

### Before filing a runtime bug

Corroborate from committed audit/state evidence:

1. `#233` **`semantic_proposal_decision`**
2. **`scene_state_after`** / continuity commit
3. Accepted/rejected **`semantic_proposals`**
4. `_narrative.json` / turn metadata as applicable

An evaluator result **alone** is insufficient.

## Choreography scope tuning (pre-closure supplemental)

`participation_choreography` is split into **safe** vs **boundary_adjacent** in `semantic_eval_boundary_signals.py`. Doorway/corridor movement and overlay/`exec_depart` without dorm-safe in-room/info evidence classify as **`ambiguous_threshold`**, not automatic **`success`**. Committed eval baselines may still show **`success`** where frozen human-adjudication anchors apply — see `limitations[]` (`human_adjudication_calibration_anchor: not runtime authority`).

## CLI

From `autogen_rp/python/`:

```bash
python scripts/run_issue243_corpus_regression.py --eval
python scripts/run_issue243_corpus_regression.py --eval --summary --corpus willow_v1
python scripts/run_issue243_corpus_regression.py --legacy --corpus willow_v1
```

## Further reading

- `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` — *Semantic proposal evaluation — operator read discipline (#243-D)*
- `autogen_rp/docs/audit-workflows.md` — *Semantic proposal evaluation (#243)*
- Repo-root `SCENARIO_VALIDATION_FRAMEWORK.md` §4
