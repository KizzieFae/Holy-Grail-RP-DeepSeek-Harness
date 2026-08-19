# #227 Selective Cohesion — Evidence Synthesis (Phase 0 closeout)

**Date:** 2026-05-23  
**Tree SHA (investigation artifacts, uncommitted):** `e230e39526fce266e1023d71b90f412761e28474`  
**Sessions:** 899–907

## Artifact index

| Artifact | Path |
|----------|------|
| Anchor-only experiment report | `autogen_rp/python/validation_runs/anchor_only_must_remain_experiment_validation_report.md` |
| Broad validation slate report | `autogen_rp/python/validation_runs/broad_validation_slate_anchor_cohesion_report.md` |
| Raw manual adjudication packet | `autogen_rp/python/validation_runs/manual_adjudication_packet_raw.md` |
| Packet generator (repro) | `autogen_rp/python/validation_runs/_generate_raw_adjudication_packet.py` |
| Willow JSONL extracts | `autogen_rp/python/validation_runs/willow_departure_*_v1.jsonl` |
| Cohesion slate JSONL | `autogen_rp/python/validation_runs/cohesion_slate/*.jsonl` |

---

## 1. Anchor-only experiment (sessions 899–901)

| Arm | Session | Departure probes with accepted `off_focal` | C3 misses |
|-----|---------|---------------------------------------------|-----------|
| Baseline all `must_remain` | 899 | 0 / 3 | 4 |
| Willow flex | 900 | 3 / 3 | 0 |
| Both alphas flex | 901 | 2 / 3 | 3 |

**Reading:** Template-only selective flex unlocked lawful `off_focal` without legality bypass. Willow-only flex (900) is strongest; both-alphas-flex weaker.

---

## 2. Broad validation slate (sessions 902–907)

| Archetype | Automated read | Post–manual-review read |
|-----------|----------------|-------------------------|
| Willow/dorm | strong lift | confirmed |
| Household guard | strong lift | confirmed |
| Arkham cafeteria | weak/null | largely topology false positives |
| Apartment slow-burn | no lift | largely topology / probe-compliance reinterpretation |
| Controls (P02 threshold) | stable | confirmed |
| Legality retries | none | confirmed |

---

## 3. Manual review — 25-case corpus

### Strong true misses (non-anchor `must_remain` pressure)

| Case | Session / probe | Actor | Arm | Summary |
|------|-----------------|-------|-----|---------|
| **11** | 899 / P03 | Willow | baseline | Garage departure + remote phone; prose commits exit; `no_covered_change` under all `must_remain` |
| **12** | 899 / P04 | Willow | baseline | Key retrieval beat but continues leaving; downstream continuation miss |
| **15** | 902 / P03 | Hannah | baseline | Remote relocation to private quarters ignored; guard `must_remain` |

### Weakened / not independent true misses

| Case | Reclassification note |
|------|----------------------|
| **13** | Alphas-flex rebound; downstream contamination from earlier missed commit — not independent proof |
| **14** | Hannah clean withdrawal; probe compliance / structural guard-role pressure — not exit-semantics failure |
| **24** | Celina apartment phone probe; open kitchen/living-room topology + dramatic continuity — not clear semantic miss |

### Major false-positive classes (automated C3 overcount)

- Threshold / doorframe participation (899 P02, 902/903 P02)
- Within-earshot / tethered speech at margin
- Visual observation while still in scene
- Cafeteria wall / table / serving-line relocation without focal exit
- Open apartment kitchen ↔ living-room topology
- Rebound movement without actual departure
- Probe ignored or reinterpreted into better dramatic continuity
- Downstream contamination after earlier missed state commit

---

## 4. Final evidence conclusion

After manual adjudication, the convincing true misses associate with **non-anchor `must_remain` pressure** while the anchor role stayed `must_remain`.

The model generally handled topology, threshold participation, ambient observation, and open-layout spaces correctly. The audit/rubric layer overcounted failures because deterministic extraction treated movement/relocation as stronger evidence of scene exit than the prose supported.

---

## 5. Leading policy direction (consensus-prep → recorded on #227)

**Product / template:** Anchor-only `must_remain` by default — anchor structurally constrained; non-anchor characters generally `flexible` unless template-specific stronger cohesion is justified.

**Audit / evaluation:** Deterministic extraction should **flag** suspicious C3 rows; suspected misses require **human or selective LLM adjudication** before counting as true failures.

**Explicit non-goals (this phase):** No production template migration, no global legality change, no prompt-topology rewrite, no audit adjudication logic change yet.

---

## 6. Open decisions (for #227 thread)

1. How to express anchor-only template policy in schema/docs
2. Whether anchor-only becomes global default vs opt-in per archetype
3. When explicit stronger non-anchor cohesion overrides are allowed
4. How to integrate selective LLM audit adjudication for flagged misses
5. Scoped implementation child issue(s) after `consensus_reached`
