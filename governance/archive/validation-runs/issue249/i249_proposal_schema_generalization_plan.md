# Issue #249 Phase A — Schema Teaching Generalization Validation Plan

Investigation-only. Topology: **`v1_next7_proposal_schema_a` only**.

## Goal

Determine whether Phase A schema teaching generalizes across scene categories without regressions.

## Out of scope

- #251 genuine missed-emission investigation
- #250 retry flattening
- Phase B/B.2 ontology topologies
- Production default / canonical promotion

## Matrix categories

| Cat | Focus | Cases |
|-----|-------|-------|
| A | Clean exits | A1–A3 |
| B | Reentries | B1–B2 |
| C | Temporary practical movement | C1–C2 |
| D | Tethered participation | D1–D4 |
| E | Emotional / high-intensity | E1–E3 |
| F | Multi-character crowded | F1–F3 |
| G | Low-pressure slice-of-life | G1–G3 |
| M | Malformed baseline cohort | M1–M7 |

## Stochastic coverage

3 passes each for: M1–M7, D1–D2, E1/E3, F1/F3 (deduped unique audit turns).

## Execution

```bash
cd autogen_rp/python
set RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_proposal_schema_a
python validation_runs/issue249/run_i249_proposal_schema_generalization.py
python validation_runs/issue249/run_i249_proposal_schema_generalization.py --dry-run
```

Requires `DEEPSEEK_API_KEY` for live reruns.
