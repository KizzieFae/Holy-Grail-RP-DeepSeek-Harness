# Resolved outcome scene validation — three runs (2026-03-30)

**Rubric source:** [resolved outcome system scene validation plan.md](../rp_app/resolved%20outcome%20system%20scene%20validation%20plan.md) (scene-type checklists + per-scene audit checklist + completion criteria).

**Method:** Evidence from persisted session JSON only (`metadata.continuity_state`, `metadata.scene_grounding`, `turn_metadata_by_index`). Narrative notes are high-level (no line-by-line chat replay).

---

## Shared template

| Field | Value |
|--------|--------|
| Template | `marlene_willow_dorm_omega_misassignment` |
| `location_entry_slots` @ save | `[]` in all three → **`access.location_entry` not exercised** (no bounded locations to validate). |

---

## Run A — Calm / low-pressure (Kizzie)

| Field | Value |
|--------|--------|
| **Session id** | `kizzie_marlene_fletcher_20260330_002953` |
| **File** | `autogen_rp/python/data/sessions/kizzie_marlene_fletcher_20260330_002953.json` |
| **Saved (UTC)** | `2026-03-30T02:11:40.086830+00:00` |
| **Cast** | Kizzie, Marlene_Fletcher, Willow_Reeves |
| **`scene_status`** | `closed` (`user_ended`) |
| **`turn_counter`** | 90 |

### Scene-type checklist (plan §1 Calm / low-pressure)

| Check | Result | Evidence |
|--------|--------|----------|
| No emissions without explicit settlement language | **PASS with caveat** | Sleeping + housing promotions align with turns carrying structured `scene_state_updates` **and** strong consequence tags (e.g. turn **3**: `decision_made`, `plan_committed`; turn **19**: `decision_made`, `plan_committed`; turn **21**: `commitment` + `housing_call_outcome` structured). |
| Ambiguous / casual phrasing does not trigger emissions | **Not fully scored** | Would require per-turn dialogue review; disk shows **many** turns with `resolved_outcomes.*.reason: "no_candidate"` — consistent with conservative parsing. |
| Grounding minimal and accurate | **PASS** | Final **`scene_grounding.facts`**: **2** facts — `sleeping_surface` (Kizzie → floor) and `housing_call` (completed). Both `source.kind`: **`resolved_outcome`**. |
| No false positives (any aspect) | **PASS** on disk | No `suppressant_formulation` or `location_entry` rows in `resolved_outcomes`; no extra stray grounded slots beyond the two above (+ none from markers in final facts). |

### High-value turns (Resolved Outcome Audit samples)

| Turn | Aspect | Expected (strict) | Engine | Classification |
|------|--------|---------------------|--------|----------------|
| **3** | `lodging.sleep_surface` | Emission plausible (structured assign + strong tags) | `promoted`, `lower_bunk_marlene`, `promoted_consequence` | **Correct emission** |
| **19** | `lodging.sleep_surface` | Reassignment with strong tags | `superseded` → floor, `superseded_by_reassignment` | **Correct emission + supersession** |
| **21** | `communication.housing_call` | Terminal completed in structured field | `promoted`, `structured_terminal`, `completed` | **Correct emission** |

### Per-scene audit checklist (plan §Per-Scene Audit)

| Section | Verdict | Notes |
|---------|---------|--------|
| **Emission accuracy** | **PASS** | `medical.suppressant_formulation` / `access.location_entry` not promoted; no evidence of spurious registry rows. |
| **Promotion behavior** | **PASS** | Sleeping supersession chain clear in `resolved_outcomes` + turn **19** debug. |
| **Slot integrity** | **PASS** | One active sleeping slot for Kizzie (floor); one active housing terminal (completed). |
| **Grounding consistency** | **PASS** | Final facts match **active** resolved outcomes (floor + housing completed); prior bunk is **superseded**, not duplicated in grounding. |

### Narrative (qualitative)

Intended calm/low-pressure, but **90 turns** indicates the scene **grew** into sustained conflict; mechanically, supersession still behaved correctly when Willow’s line of fiction moved Kizzie to **floor** over Marlene’s earlier **lower bunk**.

---

## Run B — High-conflict / multi-speaker (Harley)

| Field | Value |
|--------|--------|
| **Session id** | `harley_quinn_willow_reeves_20260330_021213` |
| **File** | `autogen_rp/python/data/sessions/harley_quinn_willow_reeves_20260330_021213.json` |
| **Saved (UTC)** | `2026-03-30T03:21:10.449520+00:00` |
| **Cast** | Harley_Quinn, Willow_Reeves, Marlene_Fletcher |
| **`turn_counter`** | 53 |

### Scene-type checklist (plan §2 High-conflict)

| Check | Result | Evidence |
|--------|--------|----------|
| Conflicting rulings → correct supersession | **PARTIAL / N/A on disk** | Only **one** sleeping promotion for Harley (**floor**, turn **2**, `issue_resolved`); **no** second competing `sleeping_surface` value appears in `resolved_outcomes` to test supersession. |
| One active value per slot | **PASS** | Single active `lodging.sleep_surface::Harley_Quinn`; single active `housing_call::scene`. |
| No duplicate active states | **PASS** | |
| Grounding = latest active only | **PASS** | `scene_grounding`: Harley → floor; housing → completed. |
| Prior states superseded correctly | **N/A** | No prior sleeping outcome in list except the active one. |

### Per-scene audit checklist

| Section | Verdict | Notes |
|---------|---------|--------|
| **Emission accuracy** | **PASS** | Same two aspects as Kizzie run; no registry pollution. |
| **Promotion behavior** | **PASS** | Sleeping promoted via **`assignment.sleeping_surface.issue_resolved.v1`** (seed issue closed on turn **2**). |
| **Slot integrity** | **PASS** | |
| **Grounding consistency** | **PASS** | |

### Narrative (qualitative)

High churn in dialogue, but **sleeping assignment did not re-litigate** into a second registry value; **supersession path untested** for sleeping in this file.

---

## Run C — Control-language / ambiguity stress (Ayame) — *weak manifest*

| Field | Value |
|--------|--------|
| **Session id** | `ayame_marlene_fletcher_20260330_032140` |
| **File** | `autogen_rp/python/data/sessions/ayame_marlene_fletcher_20260330_032140.json` |
| **Saved (UTC)** | `2026-03-30T04:35:35.877561+00:00` |
| **Cast** | Ayame, Marlene_Fletcher, Willow_Reeves |
| **`turn_counter`** | 63 |

### Scene-type checklist (plan §3 Control-language)

| Check | Result | Evidence |
|--------|--------|----------|
| No emissions from control language alone | **INCONCLUSIVE / weak run** | Prose **does** include plan-style phrases (e.g. Marlene: “**Couch is yours for now**”; Ayame: “**at least for now**”; Willow: “**Stay there**”, “**until it fucks with this room**”). **Disk alone** does not prove which turns carried `scene_state_updates` vs dialogue-only without mapping each bot payload. |
| No accidental promotion from ambiguous phrasing | **PASS on outcomes** | `resolved_outcomes`: only **sleeping** (couch, turn **2**, issue-resolved) + **housing_call** **failed** (turn **13**). No extra promotions. |
| Such turns → `Correct non-emission` | **Not scored turn-by-turn** | Requires pairing quoted lines to structured moves; recommend follow-up if this scene type is critical. |
| No grounding from control-only language | **MOSTLY PASS** | Grounding facts are **3**: (1) **`medical_status:omega_suppressants`** via **`continuity_event`** marker (legacy lexical path), (2) sleeping couch **`resolved_outcome`**, (3) housing **failed** **`resolved_outcome`**. No `location_entry`. |

### Per-scene audit checklist

| Section | Verdict | Notes |
|---------|---------|--------|
| **Emission accuracy** | **PASS** | No bogus fourth registry slot; housing **failed** is a valid terminal state. |
| **Promotion behavior** | **PASS** | |
| **Slot integrity** | **PASS** | |
| **Grounding consistency** | **WATCH** | **Two channels**: registry outcomes + **legacy event marker** for suppressants (`medical_status` ≠ `medical.suppressant_formulation` registry row). Facts are internally consistent at save but **dual pipelines** complicate “single source of truth” story. |

### Narrative (qualitative)

You noted Ayame’s **control** persona did not dominate; fiction still delivered **orders and hedged time phrases** suitable for a control-language audit, but **turn-level classification** was not fully extracted here.

---

## Summary: generalized vs scene-specific

### Generalized (expect across templates / casts if behavior unchanged)

| Topic | Finding |
|--------|---------|
| **Serialization / debug** | All three saves include **`resolved_outcomes`** and per-turn **`turn_metadata_by_index[n].resolved_outcomes`** — suitable for audits. |
| **`communication.housing_call`** | **Completed** (Kizzie, Harley) and **failed** (Ayame) both appear as **single active terminal** rows; grounding matches. |
| **`lodging.sleep_surface`** | Promotions tie to **structured assignments** + **promotion policy** (issue resolution and/or strong consequence tags in the Kizzie/Harley samples). |
| **`access.location_entry`** | **Not validated** in these runs (`location_entry_slots` empty). |
| **`medical.suppressant_formulation` (registry)** | **No** `resolved_outcomes` entries in any of the three runs; suppressant fiction does **not** automatically become registry state. |
| **Legacy grounding marker** | Ayame run shows **suppressant “wrong for physiology”** as a **continuity_event** fact — **generalized** risk: two different mechanisms can surface “medical” facts (markers vs registry). |

### Scene-specific (this cast / trajectory, not necessarily a system bug)

| Topic | Finding |
|--------|---------|
| **Kizzie “calm” length** | **90 turns** — low-pressure **intent** vs **long** mechanical trace; supersession (bunk → floor) is **story-specific** but **validates** plan §2-style slot replacement within one session. |
| **Harley supersession** | **No** conflicting sleeping registry values → **cannot** claim supersession stress from this file alone. |
| **Ayame control-language test** | **Under-realized** as a *stress* test: phrases appear in **narration**, but **rigorous** “Correct non-emission per turn” was **not** completed; scene also drifted toward **high tension** (Willow orders, case inspection). |
| **Ayame housing failed** | **Diegetic** outcome (call fails) — correct terminal **failed** state, not a generic failure mode. |

### Completion criteria (plan §Completion Criteria)

| Criterion | Status across these three runs |
|-----------|--------------------------------|
| Near-zero false positives | **Supported** for promoted registry rows observed. |
| Near-zero missed emissions | **Not established** (would need explicit expected-emission table per turn; `suppressant_formulation` / `location_entry` largely **out of scope** here). |
| 100% promotion / slot / grounding | **Met** for **sleeping_surface** + **housing_call** **where emitted**; **Ayame** adds **legacy medical marker** in grounding without registry `suppressant_formulation`. |

---

## Recommended follow-ups (optional)

1. **Harley-style run** where **two** explicit structured sleeping assignments **conflict** for the same assignee, to **force** registry supersession under fire.  
2. **Ayame / control-language**: re-run with **audit enabled** and export turns where dialogue contains “for now / wait / stay” **without** `scene_state_updates`, and mark each **Correct non-emission**.  
3. **Template** with non-empty **`location_entry_slots`** to validate **`access.location_entry`** + invalid id handling (plan §4).  
4. **Clarify documentation**: relationship between **`medical_status:omega_suppressants`** markers and **`medical.suppressant_formulation`** registry for validators.

---

## Phase closure — initial resolved-outcome validation (signed off)

**Scope:** Three live scenes (calm / Kizzie, high-conflict / Harley, control-language / Ayame) against the registry-backed aspects **implemented and exercised** in those runs. **Date:** 2026-03-30 (evidence: this file).

### Key confirmed behaviors

- **Emissions are conservative and correctly gated** — no evidence of false positives from ambiguous or casual language in the audited material.
- **Promotions occur only when supported** by structured `scene_state_updates` and/or strong consequence signals (per turn metadata).
- **Slot integrity is maintained** — one active value per slot, no duplication in `resolved_outcomes` or final grounding for the aspects observed.
- **Supersession is functioning** — observed for `lodging.sleep_surface` (Kizzie: lower bunk → floor).
- **Grounding reflects active resolved outcomes** and does not retain superseded states for those slots.

### Limitations (explicit)

- **Supersession** has not been stress-tested under *repeated* conflicting assignments in a single run.
- Some aspects were **not meaningfully exercised**: e.g. **`access.location_entry`** (empty template slots), **`medical.suppressant_formulation`** (no registry rows in these three saves).
- **Dual-path truth** for some domains (registry-backed resolved outcomes vs legacy continuity **grounding markers**) should be **clarified in documentation** later; it did not show as breaking behavior in these audits.
- **Full false-negative rate** (missed emissions) has **not** been rigorously established (no per-turn expected-emission matrix).

### Conclusion

The **resolved-outcome layer** is treated as **stable, conservative, and safe to build on** for the aspects currently implemented and validated here. It is **no longer regarded as the primary bottleneck** for scene performance in this fork’s current priorities.

### Next product focus

**Scene progression** is now the primary focus: stronger **pressure evolution**, **escalation**, and **decision-forcing** mechanics to address plateau behavior.

**Resolved-outcome expansion** (additional aspects, broader coverage, deeper validation — including optional items under *Recommended follow-ups* above) is **deferred until progression is stabilized**, unless a **new aspect is required specifically to support progression logic**.

---

*Audits produced from on-disk session state; no code or prompt changes were made during this review.*
