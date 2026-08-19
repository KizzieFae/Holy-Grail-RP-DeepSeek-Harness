# Broad Validation Slate — Anchor-only Cohesion Doctrine

**Experiment ID:** `i227_broad_validation_slate`  
**Commit SHA (uncommitted work tree):** `e230e39526fce266e1023d71b90f412761e28474`  
**Date:** 2026-05-23  
**Phase:** Generalization validation only — no production migration.

---

## 1. System understanding report

### Doctrine context (carried forward)

- **#77/#80/#81** established anchor-centered focal continuity; non-anchor excursions are architecturally legitimate.
- **`presence_constraint` and `anchor_role_name` are decoupled** in code — template ecology still assigns broad `must_remain` on many principals.
- **Legality, proposal authority, and retry already work** when characters are `flexible` (Willow experiment, sessions 899–900).
- **Legacy cohesion pressure** manifests as fiction–roster drift: models author exits but self-report `no_covered_change` under broad `must_remain`.
- **Selective flex pattern:** anchor + structural authority `must_remain`; mobile/support principals → `flexible`.

### This slate tests generalization across four archetype categories

| Category | Template | Probe target | Baseline session | Flex session |
|----------|----------|--------------|------------------|--------------|
| **A** Medium ensemble social | `ayame_household_entry_evaluation` | Hannah (guard) | 902 | 903 |
| **B** Mobility-heavy (same harness) | same + `location_entry_slots` | Hannah (foyer/quarters moves) | 902 | 903 |
| **C** Arkham cafeteria ensemble | `arkham_asylum_mess_hall_arena` | Harley (instigator) + Selina (witness P06) | 904 | 905 |
| **D** Slow-burn dyad | `celina_apartment_recovery_watch` | Celina (protector) | 906 | 907 |
| **Prior** Dorm / Willow (reference) | `marlene_willow_dorm_omega_misassignment` | Willow | 899 | 900 |

### Unchanged by design

- Global legality (`REASON_MUST_REMAIN_OFF_FOCAL`)
- Production templates
- Continuity architecture / runtime states
- Prompt topology (same v1_next7 path as #240 harness)

---

## 2. Validation archetypes and template variants

### Variant pattern (all arms)

**Anchor-selective flex:** focal anchor (+ host/authority where structurally required) stays `must_remain`; probed mobile principal becomes `flexible`.

| Production template | Experimental variant | Flex diff |
|----------------------|---------------------|-----------|
| `ayame_household_entry_evaluation` | `ayame_household_entry_evaluation_anchor_selective_flex` | `guard`: must_remain → **flexible** |
| `arkham_asylum_mess_hall_arena` | `arkham_asylum_mess_hall_arena_anchor_selective_flex` | `instigator` + `instigator_accomplice`: must_remain → **flexible**; `guard_or_staff_response`: flexible → **must_remain** |
| `celina_apartment_recovery_watch` | `celina_apartment_recovery_watch_anchor_selective_flex` | `protector`: must_remain → **flexible** |
| `marlene_willow_dorm_omega_misassignment` *(prior)* | `..._anchor_willow_flexible` | Willow: must_remain → **flexible** |

### Harness artifacts

| Archetype | Schedule | Manifest |
|-----------|----------|----------|
| A/B household | `data/issue227/cohesion_slate/household_probe_schedule_v1.json` | `household_probe_manifest_v1.json` |
| C Arkham | `data/issue227/cohesion_slate/arkham_probe_schedule_v1.json` | `arkham_probe_manifest_v1.json` |
| D apartment | `data/issue227/cohesion_slate/apartment_probe_schedule_v1.json` | `apartment_probe_manifest_v1.json` |

### Scenarios

- `investigate_i227_cohesion_household_{baseline,selective_flex}`
- `investigate_i227_cohesion_arkham_{baseline,selective_flex}`
- `investigate_i227_cohesion_apartment_{baseline,selective_flex}`

---

## 3. Sessions executed

### Batch command

```bash
cd autogen_rp/python
python scripts/run_cohesion_slate_batch.py
```

### Per-arm commands (equivalent)

```bash
python scripts/run_scene_simulation_llm.py \
  --scenario investigate_i227_cohesion_<archetype>_<arm> \
  --audit --turns <N> --ignore-end-round \
  --user-trigger-schedule data/issue227/cohesion_slate/<schedule>.json
```

| Arm | Turns | Session | Runtime log |
|-----|-------|---------|-------------|
| Household baseline | 12 | **902** | `validation_runs/cohesion_slate/run_household_baseline.log` |
| Household selective flex | 12 | **903** | `run_household_flex.log` |
| Arkham baseline | 14 | **904** | `run_arkham_baseline.log` |
| Arkham selective flex | 14 | **905** | `run_arkham_flex.log` |
| Apartment baseline | 16 | **906** | `run_apartment_baseline.log` |
| Apartment selective flex | 16 | **907** | `run_apartment_flex.log` |

Audit roots: `rp_app/data/rp_audits/session_{902..907}/`

### Extraction

```bash
python scripts/extract_cohesion_slate.py --audit-session-number <NNN> \
  --manifest data/issue227/cohesion_slate/<manifest>.json \
  --out-jsonl validation_runs/cohesion_slate/<arm>.jsonl \
  --summary-out validation_runs/cohesion_slate/<arm>_summary.json

python scripts/compare_cohesion_slate.py \
  --baseline-summary ... --flex-summary ... \
  --archetype-id <ID> --out validation_runs/cohesion_slate/<archetype>_comparison.json
```

Aggregate index: `validation_runs/cohesion_slate/cohesion_slate_aggregate.json`

---

## 4. Proposal emission comparisons

### Cross-archetype summary (departure-class probes only)

| Archetype | Baseline accepted `off_focal` | Flex accepted `off_focal` | Δ C2 (correct covered) | Δ C3 (missed covered) | C5 retries |
|-----------|------------------------------|----------------------------|------------------------|----------------------|------------|
| **Willow/dorm** *(prior 899→900)* | 0/3 | **3/3** | +3 | −4 | 0 |
| **A/B household** (902→903) | 0/3 | **2/3** | +2 | −2 | 0 |
| **C Arkham Harley** (904→905) | 0/4 | 1/4 | 0 | 0 | 0 |
| **C Arkham Selina P06** *(already flex in baseline)* | 1/1 | 0/1 | −1 | +1 | 0 |
| **D apartment** (906→907) | 0/3 | 0/3 | 0 | 0 | 0 |

### Control probes (no-change expected: P02, P05; apartment P06–P07)

| Archetype | Baseline C1 | Flex C1 | False-positive C4 |
|-----------|-------------|---------|---------------------|
| Household | 2/2 | 2/2 | 0 |
| Arkham | 2/2 | 2/2 | 0 |
| Apartment | 3/3 | 3/3 | 0 |
| Willow *(prior)* | 2/2 | 2/2 | 0 |

**Legality/retry:** zero `C5` across all 9 sessions (902–907 + prior 899–900).

### Interpretation

- **Clear lift:** Willow dorm, household guard — template flex unlocks lawful `off_focal` without infrastructure changes.
- **Partial / null lift:** Arkham Harley (high-volatility instigator), apartment protector (slow-burn dyad).
- **Not universal:** flex alone does not guarantee emission; character/scene volatility and prompt participation weight still matter.

---

## 5. Narrative/pacing observations

### Household (A/B) — generalizes Willow pattern

- **Baseline (902):** Hannah walks to foyer/quarters in fiction but stays on roster; rebound beat (P04 ledger) without commit.
- **Flex (903):** P01/P03 emit accepted `off_focal`; roster shows `temporary_offstage`. P04 rebound still narratively present but **misses** covered change (same residual edge case as Willow alphas-flex arm).
- **P02 doorway tether:** correctly `no_covered_change` both arms.
- **Pacing:** flex arm resolves departures in fewer verbal loops; less “still in the room” capsule pressure after commits.

### Mobility lens (category B, same sessions)

- P03 (private quarters relocation) and P01 (foyer exit) behave like Willow garage/phone probes.
- **Mobility-heavy moves benefit when the moving role is flexed** — same evidence as A.

### Apartment slow-burn (D)

- **Both arms:** Celina authors kitchen/phone/hall fiction but consistently `no_covered_change` — even when `flexible`.
- **Slow-burn controls (P06 silence, P07 minimal reply):** clean C1 both arms — **no offscreen filler** (`F_filler_cue` = 0 all probes).
- **Tether cues decreased in flex** (−3 vs baseline) but without roster commits — social continuity persists without state honesty gain.
- **Protector role** may need additional participation calibration (not just template flex) for slow-burn safehouse scenes.

### Willow reference (prior)

- Strongest narrative/roster alignment in the entire arc; see `validation_runs/anchor_only_must_remain_experiment_validation_report.md`.

---

## 6. Cohesion/orchestration analysis

| Risk | Household | Arkham | Apartment |
|------|-----------|--------|-----------|
| Cast evaporation | None — Ayame/Celina stable | None — 6-char cast present throughout | None — Kizzie anchor stable |
| Anchor instability | Celina (applicant) onstage all beats | Magpie (new_arrival) onstage | Kizzie onstage |
| Conversation fragmentation | Low | **Moderate** — multi-thread cafeteria pressure | Low |
| Director stability | Stable forced-speaker routing | Stable; high issue churn | Stable |
| Fiction–roster drift | Baseline 0; flex 1 (P02 threshold) | 1 both arms (P04 rebound) | 0 both arms |
| Side-thread coherence | Good | Witness P06 regressed in flex arm | N/A (dyad) |

**Orchestration did not collapse** in any flex arm. No accidental mass dropout, no C4 false positives, no legality storms.

---

## 7. Arkham cafeteria findings (required)

### Setup

- **6-character** cast: Harley, Ivy, Magpie, Selina, Cash, Jane Doe.
- **Baseline template:** instigators + anchor `must_remain`; witnesses/guards already mixed.
- **Flex variant:** instigators → `flexible`; anchor + **Cash** → `must_remain` (staff anchor for ensemble stability).

### Key results

1. **Harley (instigator) probes — limited lift:** flex arm improved P03 (tray window relocation) to C2; P01/P04 still C3. High-volatility instigator in public arena does not mirror Willow/household lift magnitude.
2. **Selina (witness, already flexible in baseline) — regression:** P06 soft withdrawal was **C2 in baseline (904)** but **C3 in flex (905)** when instigators were flexed. Suggests **ensemble volatility interacts with who is flexed** — freeing instigators may increase scene turbulence that suppresses witness emission.
3. **No cast evaporation:** all six names remain in rotation; Cash/Magpie anchor presence holds.
4. **Staff `must_remain` upgrade in flex variant** appears correct for stability — guards did not spuriously exit.
5. **Some support characters remain better as `must_remain`:** staff/guard roles and possibly co-anchor hosts; **instigators in mess-hall arena may need flex + prompt tuning**, not flex alone.

### Arkham-specific doctrine note

> Anchor-only selective cohesion **preserves ensemble stability** but **does not automatically improve every mobile role** in high-visibility, multi-thread cafeteria scenes. Witness roles already `flexible` can regress when instigator cohesion loosens.

---

## 8. Failure modes / regressions

| Failure mode | Observed? | Where |
|--------------|-----------|-------|
| Accidental cast dropout | **No** | All sessions |
| Incoherent mass exit | **No** | All sessions |
| False-positive off_focal (C4) | **No** | All sessions |
| Legality retry storm (C5) | **No** | All sessions |
| Offscreen filler increase | **No** | `filler_probe_count` = 0 everywhere |
| Rebound miss under flex | **Yes** | Household P04; Arkham P04; Willow alphas-flex P04 *(prior)* |
| Witness regression when instigators flex | **Yes** | Arkham Selina P06: 904 C2 → 905 C3 |
| Template flex with zero emission lift | **Yes** | Apartment 906→907 (protector still never emits) |
| Social tether without roster update | **Yes** | Apartment both arms; baseline household/arkham |

**Not counted as failure:** continued `no_covered_change` on threshold/doorway controls — correct behavior.

---

## 9. Doctrine implications for #227

1. **Selective cohesion generalizes beyond Willow** for controlled ensemble + mobility scenes (household guard, dorm Willow) — **not universally** (apartment dyad, arkham instigator).
2. **Template alignment is necessary but not sufficient** in slow-burn protector/recovering dyads and volatile public instigator roles.
3. **Anchor + authority `must_remain` is stable** across all tested ensembles; flex on mobile principals did not destabilize anchors.
4. **Broad flex remains risky** *(prior Willow alphas-flex 901)* — this slate reinforces **surgical flex** over blanket non-anchor flex.
5. **Runtime is capable** — when flex aligns with scene semantics, proposals emit and commit with zero retries; infrastructure is not the bottleneck.
6. **#227 policy question narrows:** not “whether flex works” but **which role classes per template archetype** should default to `must_remain` vs `flexible`.
7. **Legality/guidance contradiction** remains for roles still marked `must_remain`; template migration is the low-blast-radius first lever.

---

## 10. Findings to append vs promote into issues

### Append to **#227** (primary)

- Broad slate sessions 902–907 + aggregate comparisons in `validation_runs/cohesion_slate/`.
- Cross-archetype table (Section 4) and Arkham cafeteria analysis (Section 7).
- **Leading policy candidate:** anchor + structural authority `must_remain`; mobile/support principals `flexible` — **per template archetype matrix**, not global.

### Append to **#225**

- Apartment protector shows **residual emission gap** even with flex — may need participation prompt calibration follow-up, not template-only fix.

### Append to **#240**

- Reuse `cohesion_slate_extract.py` / actor-targeted probe harness for future doctrine experiments.

### Promote / new sub-issue candidates

1. **Template archetype matrix issue:** classify V1 templates (dorm, household, mess hall, apartment dyad, shrine) with recommended default presence constraints.
2. **Arkham ensemble follow-up:** instigator flex + witness stability — test flex on witnesses only while keeping instigators `must_remain` vs current inverse.
3. **Slow-burn dyad calibration:** protector/recovering apartment — combine template flex with participation topology tweak.

### Preserve from arc

- Anchor-doctrine verification (#77/#80/#81)
- Legacy broad-cast cohesion pressure (#223–#227)
- Social continuity > physical continuity
- Willow 899→900 as canonical positive control

---

## 11. Recommended next governance action

1. **Do not** migrate production templates globally yet.
2. **On #227:** Attach this report + prior Willow report; advance **archetype-specific template matrix** as the decision artifact (not a single global rule).
3. **Pilot candidates for staged template update** (after stakeholder review):
   - `marlene_willow_dorm_omega_misassignment` → Willow flex *(strongest evidence)*
   - `ayame_household_entry_evaluation` → guard flex *(strong evidence)*
4. **Hold for further experiment:** `arkham_asylum_mess_hall_arena`, `celina_apartment_recovery_watch` — need variant design iteration, not production swap.
5. **Schedule template audit issue** enumerating all-role `must_remain` V1 templates against anchor doctrine.
6. **Optional live (non-harness) validation** on household + dorm variants before any production-facing swap.

---

## Analysis question index (required 12)

| # | Question | Answer |
|---|----------|--------|
| 1 | Generalizes beyond Willow? | **Partially yes** — household guard yes; apartment/arkham instigator inconclusive |
| 2 | Archetypes benefit most? | Controlled 3-char ensemble + mobility (dorm, household) |
| 3 | Archetypes need stronger cohesion? | Arkham public instigators; slow-burn protector dyads; staff/guards |
| 4 | Broad flex increases instability? | **Yes** *(prior 901 + Arkham Selina P06 regression)* |
| 5 | Selective flex reduces drift? | **When emission lifts** (Willow, household); not always |
| 6 | Reduces tether/rebound? | Narrative tether persists; roster honesty improves on successful commits |
| 7 | Pacing improves? | **Yes** where commits land; marginal elsewhere |
| 8 | Offscreen filler? | **No increase** observed |
| 9 | More believable departures? | **Yes** on C2 probes (Willow, household, Arkham P03 flex) |
| 10 | Runtime naturally capable? | **Yes** once template pressure reduced |
| 11 | Selective cohesion emerging as direction? | **Yes, with archetype-specific caveats** |
| 12 | #227 vs new sub-issues? | #227: matrix policy; new: template audit, arkham variant iteration, apartment calibration |

---

## Files created/modified (exact list)

### Template variants
- `data/scene_templates/ayame_household_entry_evaluation_anchor_selective_flex.json`
- `data/scene_templates/arkham_asylum_mess_hall_arena_anchor_selective_flex.json`
- `data/scene_templates/celina_apartment_recovery_watch_anchor_selective_flex.json`

### Harness
- `data/issue227/cohesion_slate/household_probe_{schedule,manifest}_v1.json`
- `data/issue227/cohesion_slate/arkham_probe_{schedule,manifest}_v1.json`
- `data/issue227/cohesion_slate/apartment_probe_{schedule,manifest}_v1.json`
- `rp_app/data/progression_simulation_scenarios/investigate_i227_cohesion_*` (6 scenarios)

### Tooling
- `rp_app/cohesion_slate_extract.py`
- `scripts/extract_cohesion_slate.py`
- `scripts/compare_cohesion_slate.py`
- `scripts/run_cohesion_slate_batch.py`
- `scripts/run_scene_simulation_llm.py` (extended `--ignore-end-round` for `investigate_i227_cohesion_*`)

### Outputs
- `validation_runs/cohesion_slate/*_{baseline,flex}.{jsonl,summary.json}`
- `validation_runs/cohesion_slate/{household,arkham,apartment}_comparison.json`
- `validation_runs/cohesion_slate/cohesion_slate_aggregate.json`
- `validation_runs/cohesion_slate/run_*.log`
- `rp_app/data/rp_audits/session_{902..907}/`

### Prior experiment (referenced, not re-run)
- `validation_runs/anchor_only_must_remain_experiment_validation_report.md`
- Sessions **899–901**, Willow comparisons in `validation_runs/willow_departure_experiment_comparison.json`

### Unchanged (by design)
- Production templates
- `continuity_semantic_proposals.py` (legality)
