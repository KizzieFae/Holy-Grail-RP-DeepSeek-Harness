# Anchor-only `must_remain` Experiment — Validation Report

**Experiment ID:** `i227_anchor_only_must_remain`  
**Commit SHA (uncommitted work tree):** `e230e39526fce266e1023d71b90f412761e28474`  
**Date:** 2026-05-23  
**Scope:** Controlled doctrine validation only — no production template or global legality changes.

---

## 1. System understanding report

### Doctrine baseline (from #77/#80/#81, #223–#227, session_890/892)

- Anchor-centered focal continuity is real: `anchor_role_name` marks the omega focal role; non-anchor excursions are architecturally legitimate.
- `anchor_role_name` and `presence_constraint` are **separate** fields — not auto-linked in code.
- Production template `marlene_willow_dorm_omega_misassignment` assigns **`must_remain` to all three roles** (Marlene, Willow, omega/Kizzie).
- Legality (`continuity_semantic_proposals.py`) rejects committed `off_focal` for any character with `must_remain` (`REASON_MUST_REMAIN_OFF_FOCAL`).
- Prompt guidance permits offstage semantics, but legality blocks committed `off_focal` for `must_remain` — documented contradiction tracked on **#227**.
- Willow tether/rebound in session_890 reads as **cohesion pressure** (template + legality + active-focus capsules), not pure model incapability.

### Experiment hypothesis

> Reducing non-anchor `must_remain` pressure (template-only) should allow natural `off_focal` proposal emission and roster commits **without** bypassing legality, proposal authority, or continuity architecture.

### What changed vs what did not

| Layer | Changed | Unchanged |
|-------|---------|-----------|
| Template variants | Willow → `flexible` (arm B); both alphas → `flexible` (arm C) | Production `marlene_willow_dorm_omega_misassignment.json` |
| Runtime legality | — | `REASON_MUST_REMAIN_OFF_FOCAL` still enforced |
| Prompt topology | — | Same v1_next7 participation calibration path as #240 harness |
| Harness | New #227 scenarios + probe schedule | Actor-targeted forced speaker, `--ignore-end-round` pattern reused |

---

## 2. Experimental template variants

### Production baseline (unchanged)

`autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment.json`

| Role | `presence_constraint` |
|------|----------------------|
| `alpha_roommate_marlene` | `must_remain` |
| `alpha_roommate_willow` | `must_remain` |
| `misassigned_omega_student` (anchor) | `must_remain` |

### Variant A — anchor + Marlene `must_remain`; Willow `flexible`

**File:** `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_willow_flexible.json`  
**Progression parity:** `..._anchor_willow_flexible_progression.json`

```diff
 alpha_roommate_willow:
-  "presence_constraint": "must_remain"
+  "presence_constraint": "flexible"
 (Marlene + omega anchor unchanged: must_remain)
```

### Variant B — anchor `must_remain`; both alphas `flexible`

**File:** `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_alphas_flexible.json`  
**Progression parity:** `..._anchor_alphas_flexible_progression.json`

```diff
 alpha_roommate_marlene:
-  "presence_constraint": "must_remain"
+  "presence_constraint": "flexible"
 alpha_roommate_willow:
-  "presence_constraint": "must_remain"
+  "presence_constraint": "flexible"
 (omega anchor unchanged: must_remain)
```

All other template fields (`anchor_role_name`, premise, slots, authority) preserved.

---

## 3. Validation sessions executed

### Harness artifacts

| Artifact | Path |
|----------|------|
| Probe schedule | `autogen_rp/python/data/issue227/i227_willow_departure_probe_schedule_v1.json` |
| Probe manifest | `autogen_rp/python/data/issue227/i227_willow_departure_probe_manifest_v1.json` |
| Baseline scenario | `autogen_rp/python/rp_app/data/progression_simulation_scenarios/investigate_i227_willow_departure_baseline.json` |
| Willow-flex scenario | `.../investigate_i227_willow_departure_willow_flex.json` |
| Alphas-flex scenario | `.../investigate_i227_willow_departure_alphas_flex.json` |

### Probe matrix (Willow actor-targeted, turns 3/5/7/9/11)

| Probe | Type | Expected rubric |
|-------|------|-----------------|
| P01 | clean withdrawal | covered_change |
| P02 | threshold/doorway continuation | no_covered_change |
| P03 | remote garage/phone | covered_change |
| P04 | rebound immediate return | covered_change |
| P05 | present disengaged | no_covered_change |

### Validation command (each arm)

```bash
cd autogen_rp/python
python scripts/run_scene_simulation_llm.py \
  --scenario investigate_i227_willow_departure_<arm> \
  --audit --turns 12 --ignore-end-round \
  --user-trigger-schedule data/issue227/i227_willow_departure_probe_schedule_v1.json
```

### Sessions

| Arm | Scenario | Session | Runtime | Log |
|-----|----------|---------|---------|-----|
| Baseline (all `must_remain`) | `investigate_i227_willow_departure_baseline` | **899** | ~3.4 min | `validation_runs/i227_baseline_run.log` |
| Willow flex | `investigate_i227_willow_departure_willow_flex` | **900** | ~4.4 min | `validation_runs/i227_willow_flex_run.log` |
| Alphas flex | `investigate_i227_willow_departure_alphas_flex` | **901** | ~3.6 min | `validation_runs/i227_alphas_flex_run.log` |

Audit roots: `autogen_rp/python/rp_app/data/rp_audits/session_{899,900,901}/`

### Extraction commands

```bash
python scripts/extract_willow_departure_experiment.py --audit-session-number 899 \
  --summary-out validation_runs/willow_departure_baseline_summary.json \
  --out-jsonl validation_runs/willow_departure_baseline_v1.jsonl

python scripts/extract_willow_departure_experiment.py --audit-session-number 900 \
  --summary-out validation_runs/willow_departure_willow_flex_summary.json \
  --out-jsonl validation_runs/willow_departure_willow_flex_v1.jsonl

python scripts/extract_willow_departure_experiment.py --audit-session-number 901 \
  --summary-out validation_runs/willow_departure_alphas_flex_summary.json \
  --out-jsonl validation_runs/willow_departure_alphas_flex_v1.jsonl

python scripts/compare_willow_departure_experiment.py \
  --baseline-summary validation_runs/willow_departure_baseline_summary.json \
  --willow-flex-summary validation_runs/willow_departure_willow_flex_summary.json \
  --alphas-flex-summary validation_runs/willow_departure_alphas_flex_summary.json \
  --out validation_runs/willow_departure_experiment_comparison.json
```

---

## 4. Proposal emission comparison

### First-actor probe outcomes (primary metric)

| Probe | Baseline (899) | Willow flex (900) | Alphas flex (901) |
|-------|----------------|-------------------|-------------------|
| P01 clean withdrawal | C3 miss — `no_covered_change`, 0 proposals | **C2 — `off_focal` accept** | **C2 — `off_focal` accept** |
| P02 threshold | C1 correct no-change | C1 correct no-change | C1 correct no-change |
| P03 garage/phone | C3 miss — fiction exits, 0 proposals | **C2 — `off_focal` accept** | **C2 — `off_focal` accept** |
| P04 rebound return | C3 miss — tethered keys beat, 0 proposals | **C2 — `off_focal` accept** | C3 miss — stayed onstage |
| P05 disengaged | C1 correct no-change | C1 correct no-change | C1 correct no-change |

### Aggregate proposal metrics

| Metric | Baseline | Willow flex | Alphas flex |
|--------|----------|-------------|-------------|
| Probe `off_focal` proposals emitted | **0** | **3** | **2** |
| Proposals accepted (legality pass) | 0 | 3 | 2 |
| Legality retries (`C5`) | 0 | 0 | 0 |
| First-actor C2 (correct covered) | 0 | **3** | 2 |
| First-actor C3 (missed covered) | **4** | 0 | 3 |
| First-actor C1 (correct no-change) | 2 | 2 | 2 |

### Mechanism confirmation (session 900, P01)

Prompt carried template diff into runtime state:

```json
"character_presence_constraints": {
  "Kizzie": "must_remain",
  "Marlene_Fletcher": "must_remain",
  "Willow_Reeves": "flexible"
}
```

Willow emitted:

```json
"semantic_evaluation": {
  "decision": "covered_change",
  "proposals": [{ "kind": "off_focal", "character": "Willow_Reeves" }]
}
```

→ accepted → `temporary_offstage`, removed from `present_characters`.

Baseline (899, P01) with identical trigger: `decision: no_covered_change` despite exit fiction (door + hall); Willow remained in `present_characters` with `must_remain` in prompt.

**Conclusion:** Template `flexible` alone unlocks lawful proposal emission; no legality bypass required.

---

## 5. Narrative behavior comparison

### Baseline (899) — social continuity > physical continuity

- **P01:** Fiction walks to door, stops at frame, keeps talking — no proposal. Classic tether-at-threshold.
- **P03:** Elaborate garage/phone fiction while roster keeps Willow onstage; active focus still “in the room with the live exchange”; **fiction-roster drift** flagged.
- **P04:** “Forgot keys” beat — hand through door gap, does not fully re-enter, leaves again — rebound semantics in fiction without roster update.
- **P02/P05:** Correct no-change controls held.

Narrative quality: emotionally coherent Willow voice; departures expressed as **socially tethered edge behavior** rather than committed off-focal state.

### Willow flex (900) — cleaner departure commits

- **P01:** Clean hall exit, door shut, empty dialogue — proposal + commit. Less verbal tether.
- **P03:** Full garage relocation + phone call; offstage commit matches fiction.
- **P04:** Brief key retrieval while maintaining offstage status (`temporary_offstage` throughout) — rebound **fiction** present but roster reflects distance.
- **P02:** Doorway margin talk — correctly no proposal (threshold continuation control).

Tether cues still appear in narrative (phone/garage language) but **roster state tracks fiction** on covered-change probes.

### Alphas flex (901) — partial lift, more drift

- P01/P03: proposals emit and accept (same as willow flex).
- P04/P05: missed covered change with **in-room focus** and **fiction-roster drift** — suggests broadening both alphas to `flexible` without further prompt tuning may reintroduce cohesion ambiguity on edge cases.

### Rebound / tether counts (probe rows)

| Flag | Baseline | Willow flex | Alphas flex |
|------|----------|-------------|-------------|
| Rebound cues | 1 | 2 | 3 |
| Tether cues | 2 | 4 | 4 |
| In-room focus capsules | 3 | 1 | 5 |
| Fiction-roster drift | 1 | 1 | 3 |

**Interpretation:** Willow-only flex reduces in-room focus pressure and improves proposal/roster alignment on departure probes. Alphas-flex increases drift on P04/P05 — not clearly better than willow-only arm.

---

## 6. Drift / cohesion analysis

| State field | Baseline pattern | Willow flex pattern |
|-------------|------------------|---------------------|
| `present_characters` | Willow always listed on covered-change probes | Removed on P01/P03/P04 commits |
| `offstage_characters` | Always empty | `Willow_Reeves` on committed beats |
| `character_presence_status` | Always `onstage` for Willow | `temporary_offstage` when committed |
| Active focus | “In the room with the live exchange” on P02/P03 | Drops after off_focal commit |
| Participation arc | “Marlene tried to pull you back…” persists | Shifts to withdrawn/margin wording post-exit |

**Fiction-roster divergence** was the dominant baseline failure mode: model authored exits but self-reported `no_covered_change`, leaving continuity roster stale. Template flex arm aligns self-report, proposals, and commits.

**Social continuity > physical continuity** remains visible in all arms (doorway talk, phone tethering) — the experiment improves **state honesty**, not elimination of tether narrative.

---

## 7. False-positive / regression analysis

### Monitored risks

| Risk | Baseline | Willow flex | Alphas flex |
|------|----------|-------------|-------------|
| Accidental cast dropout | None — Willow never left roster | None — anchor + Marlene stable | None |
| Anchor instability | Kizzie remained focal/onstage throughout | Same | Same |
| Incoherent exits | Low — fiction coherent but uncommitted | Low — commits match beats | Mixed on P04 |
| Excessive offscreen narration | N/A (never offstage) | Minimal | Minimal |
| Weakened dramatic continuity | High social tether, stale roster | Improved pacing on exits; phone tether remains | More drift on P04/P05 |
| Legality false blocks | N/A (no proposals) | None observed | None observed |

### Controls (P02, P05)

All three arms scored **C1** on threshold continuation and present-disengaged probes — no false-positive `off_focal` on no-change cases for willow-flex arm.

### Verdict

- **Willow-only flex:** Strongest signal — healthier departure semantics without ensemble damage.
- **Both-alphas flex:** Weaker edge-case behavior; not recommended as next default without further tuning.
- Success metric met: **not** “more exits = success” but **honest participation state on real departures**.

---

## 8. Doctrine implications for #227

1. **Legacy template ecology carries real cohesion pressure.** All-role `must_remain` on a 3-person dorm template correlates with zero `off_focal` proposals and systematic C3 misses on departure probes — even when fiction depicts exits.

2. **Anchor-only `must_remain` is sufficient for this scene.** Omega anchor + Marlene `must_remain`, Willow `flexible` matches #77/#80/#81 intent without destabilizing the focal omega or roommate authority structure.

3. **Legality is not the binding constraint for Willow departures in this harness** — template constraint is. Legality would block `off_focal` if Willow stayed `must_remain`; once `flexible`, existing legality accepts commits with zero retries.

4. **Guidance/legality contradiction on #227 remains** for characters still marked `must_remain`. This experiment does not resolve whether to change global legality (options A–E); it shows **template alignment** alone produces measurable lift.

5. **Prompt participation calibration (#240) is orthogonal.** Same topology ran across arms; lift came from template diff, not prompt variant change.

---

## 9. Findings to append vs promote into issues

### Append to **#227** (primary policy lane)

- Controlled A/B/C evidence: sessions 899–901.
- Template-only Willow `flexible` → 3/3 covered-change probes emit accepted `off_focal`; baseline → 0/3.
- Recommend **Option-class template migration** (anchor + co-anchor `must_remain`, non-anchor principals `flexible`) as leading candidate — pending broader template audit.

### Append to **#225** (Willow validation)

- Willow departure probe harness + extraction tooling now exists under `data/issue227/`.
- session_890-style tether/rebound reinterpreted: model capable of exit fiction; failure mode is **semantic self-report + roster commit gap** under `must_remain`.

### Append to **#240** (emission calibration)

- Participation prompt calibration alone did not drive this lift; template presence_constraint did.
- Reuse actor-targeted harness pattern for future doctrine experiments.

### Promote / new sub-issue candidate

- **Template audit:** enumerate V1 templates with all-role `must_remain` vs anchor doctrine; prioritize dorm/ensemble scenes.
- **Alphas-flex edge cases:** P04/P05 regression under both-alphas-flex — investigate whether Marlene `flexible` adds cohesion noise (optional follow-up, lower priority than willow-only).

### Preserve from prior arc

- Anchor-doctrine verification (#77/#80/#81)
- Legacy cohesion pressure findings (#223–#227)
- Social continuity > physical continuity behavior
- Rebound/tether as narrative strategy under stale roster

---

## 10. Recommended next governance action

1. **Do not** globally change legality or production templates yet.
2. **On #227:** Attach this report; move discussion toward **template presence_constraint alignment** with anchor doctrine (Willow-only flex as minimal production-adjacent patch candidate for `marlene_willow_dorm_omega_misassignment` after stakeholder review).
3. **Run one live (non-harness) validation** on willow-flex template with natural user triggers before any production swap.
4. **Schedule template audit issue** for remaining all-`must_remain` V1 scenes.
5. **Keep alphas-flex variant** as experimental reference only until P04/P05 drift is understood.

---

## Files modified / created (exact list)

### New template variants (experimental)
- `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_willow_flexible.json`
- `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_willow_flexible_progression.json`
- `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_alphas_flexible.json`
- `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment_anchor_alphas_flexible_progression.json`

### Harness data
- `autogen_rp/python/data/issue227/i227_willow_departure_probe_schedule_v1.json`
- `autogen_rp/python/data/issue227/i227_willow_departure_probe_manifest_v1.json`
- `autogen_rp/python/rp_app/data/progression_simulation_scenarios/investigate_i227_willow_departure_baseline.json`
- `autogen_rp/python/rp_app/data/progression_simulation_scenarios/investigate_i227_willow_departure_willow_flex.json`
- `autogen_rp/python/rp_app/data/progression_simulation_scenarios/investigate_i227_willow_departure_alphas_flex.json`

### Tooling
- `autogen_rp/python/rp_app/willow_departure_experiment_extract.py`
- `autogen_rp/python/scripts/extract_willow_departure_experiment.py`
- `autogen_rp/python/scripts/compare_willow_departure_experiment.py`
- `autogen_rp/python/scripts/run_scene_simulation_llm.py` (allow `--ignore-end-round` for `investigate_i227_willow_departure_*`)

### Validation outputs
- `autogen_rp/python/validation_runs/willow_departure_baseline_v1.jsonl` (+ `.csv`, `_summary.json`)
- `autogen_rp/python/validation_runs/willow_departure_willow_flex_v1.jsonl` (+ `.csv`, `_summary.json`)
- `autogen_rp/python/validation_runs/willow_departure_alphas_flex_v1.jsonl` (+ `.csv`, `_summary.json`)
- `autogen_rp/python/validation_runs/willow_departure_experiment_comparison.json`
- `autogen_rp/python/validation_runs/i227_{baseline,willow_flex,alphas_flex}_run.log`
- `autogen_rp/python/rp_app/data/rp_audits/session_{899,900,901}/`

### Unchanged (by design)
- `autogen_rp/python/data/scene_templates/marlene_willow_dorm_omega_misassignment.json` (production)
- `autogen_rp/python/rp_app/continuity_semantic_proposals.py` (legality)
