# Post–Scene Grounding validation — Audit 01 (Scenario A: Kizzie / low-agency stress)

**Audit type:** Post-implementation continuity → grounding validation (Phase 0 + Phase 1/2)  
**Saved:** 2026-03-29 (workspace)  
**Primary source:** `autogen_rp/python/data/sessions/kizzie_marlene_fletcher_20260329_061642.json`  
**Session id:** `kizzie_marlene_fletcher_20260329_061642`  
**Saved at (UTC):** 2026-03-29T07:42:49Z  
**Template:** `marlene_willow_dorm_omega_misassignment`  
**Cast:** Kizzie (omega), Marlene_Fletcher, Willow_Reeves — matches **Scenario A** (demure omega, two alphas, university dorm).  
**Scenario B (Harley):** Not covered in this file; run Audit 02 against `harley_quinn_marlene_fletcher_20260329_021944.json` or a fresh Harley session using the same checklist.

**Related procedure:** [autogen_rp/docs/audit-workflows.md](../../docs/audit-workflows.md) · [AUDIT_DOCUMENTATION.md](../rp_app/AUDIT_DOCUMENTATION.md) (Scene Grounding §)

**Note:** On-disk `rp_app/data/rp_audits/session_*/` JSON was not used for this pass; evidence is from **persisted session** (`team_state`, `continuity_manager` snapshot, `scene_grounding`, `public_events`).

---

## 1. Executive summary — did grounding persistence improve?

**For the allowlisted fact that did promote:** **Yes.** The **housing / res-life call completed** outcome is represented as a **stable `communication_state:housing_call|status=completed`** chain: multiple `PublicEvent` rows carry the same marker, and the saved **`scene_grounding`** snapshot shows **one** settled fact with **`supersedes`** pointing at an earlier event — consistent with **slot-based supersession**, not silent disappearance.

**For other persistent fiction (suppressants nuance, bunk assignment):** **No grounding facts** appear in the final snapshot for those threads. That is **not** evidence of Phase 0 regression; it matches **narrow lexical rules** today (e.g. bunk marker requires **agreement/commitment category** plus **bunk + top + marlene/mars**; suppressant formulation marker requires **revelation** plus specific **wrong physiology** phrasing). Dialogue in this run uses **generic “on suppressants”** and **conflict over floor vs bunk** without matching those patterns.

**Verdict:** Phase 0/1/2 behave as designed for **matched** signals; **Scenario A** still **stress-tests coverage gaps** (low drama, non-template phrasing) more than **persistence bugs** for facts that never emitted markers.

---

## 2. Saved `scene_grounding` (authoritative projection at save)

From `team_state.metadata.scene_grounding`:

| Field | Value |
|--------|--------|
| `schema_version` | 1 |
| `last_rebuilt_turn` | 71 |
| Active facts (count) | **1** |
| Category / key | `communication_state` / `housing_call` |
| `value_summary` | `Housing call: completed` |
| `source.ref` | `evt_2026-03-29T06:35:22.189201+00:00_14` |
| `supersedes` | `evt_2026-03-29T06:26:42.286538+00:00_6:0` |

**Interpretation:** Rebuild is **deterministic** and **stable** for this slot; later duplicate markers on other events **update the same logical slot** rather than multiplying bullets.

---

## 3. Additional conditions (explicit)

### 3.1 Marker persistence (critical)

| Observation | Classification |
|---------------|------------------|
| **Housing call completed** appears on **at least** `PublicEvent` ids `_4`, `_6`, `_14` (and matching `turn_metadata` entries with non-empty `grounding_markers`). | **PASS** — marker **persisted** on events and **projected** into final grounding. |
| Final grounding **does not drop** the fact without replacement; **supersedes** links earlier fact id. | **PASS** — no intermittent **vanish**. |
| **Suppressants “wrong formulation” / kitsune physiology**, **explicit top-bunk assignment to Kizzie** | **N/A / coverage gap** — **no** `medical_status:omega_suppressants` or `assignment:sleeping_surface` markers in `public_events` excerpt review. |

**Flagged for follow-up (observation only):** If players expect **every** suppressant or bunk beat to surface in SETTLED facts, **lexicon** must expand; current run **did not** hit existing rules.

### 3.2 Previously resolved topics reappearing

**Not fully adjudicated from JSON alone** (would need line-by-line chat vs prompts). Prior dorm audits ([Kizzie_dorm_rerun_audit_20260328.md](./Kizzie_dorm_rerun_audit_20260328.md)) documented **duplicate suppressants questioning** and **bunk re-litigation** on **other** session files.

**This session (061642):** Early beats include **Willow** demanding **suppressants / heat / paperwork** and **Marlene** pushing **bunk choice**; **Kizzie** complies incrementally (**sit**, **housing call**). Without replaying the full chat, **cannot** assert a P3-class duplicate thread here; **grounding would not have prevented** re-asks for facts **never promoted**.

### 3.3 Soft state resets

| Check | Result |
|--------|--------|
| **Housing call** fact | **No reset** — single line of truth at save. |
| **Other slots** (phone, weapon, dressing) | **Absent** — nothing to reset. |

**PASS** for persisted slot; **unknown** for fiction that never became a slot.

### 3.4 Stability under conflict (Harley scenario)

**Deferred** to Audit 02 (Harley session).

### 3.5 Coverage in low-signal turns (Kizzie)

- Many turns have **`grounding_markers`: []** while still creating rich **`PublicEvent`** summaries (authority, access, escalation) — **expected** (grounding is **not** all events).
- **Low-agency Kizzie** lines often **comply** without hitting **phone/bandage/weapon** or **bunk/marlene** templates.

**Flag:** **Important state** (e.g. “on suppressants, two months”) **does not** become a grounding fact under **current** rules → **sparse grounding** despite clear **in-fiction** establishment.

### 3.6 Over-promotion / noise

- **~58** continuity `public_events` in full snapshot (by structure); **only one** grounding slot populated at save.
- **PASS** for **grounding clutter** — facts list is **minimal**, not noisy.
- **Many** dramatic events without markers — **by design**, not over-promotion of grounding.

---

## 4. Specific examples

### 4.1 Successful persistence

- **Housing call completed:** Markers on events through turn metadata; final **`scene_grounding.facts[0]`** = `Housing call: completed` with provenance `evt_…_14` and **supersedes** earlier fact.

### 4.2 Missed persistence (coverage / phrasing, not Phase 0 drop)

- **Suppressants:** Dialogue includes **“I am on suppressants”** and Willow’s **“You got suppressants?”** — does **not** match **`medical_status:omega_suppressants`** rule (needs **revelation** + wrong physiology / formulation cues).
- **Bunk / sleep:** Multiple beats about **top bunk / floor / couch**; no marker matching **`assignment:sleeping_surface|...marlene...`** (needs **agreement/commitment** + **bunk + top + marlene/mars** substring set).

### 4.3 Incorrect resets

- **None observed** for **`housing_call`** in saved snapshot.

---

## 5. Kizzie (this run) vs Harley — comparison

| Dimension | Scenario A — this session (061642) | Scenario B — pending Audit 02 |
|-----------|--------------------------------------|--------------------------------|
| Marker persistence (allowlisted) | **Housing call** stable | *Run Harley JSON + chat* |
| Resolved-topic rehash | Not fully scored here | Prior file: triad chaos, open issue @ end |
| Soft resets | None for persisted slot | *TBD* |
| Low-signal coverage | **Sparse** grounding for compliant dialogue | Harley: high density, more lexical triggers possible |
| Noise | **Low** grounding cardinality | *TBD* |

---

## 6. Conclusions (no fixes in this document)

1. **Phase 0 invariant** appears **satisfied** for turns that emit markers: **housing** markers are **on `PublicEvent`** and **survive** into **`scene_grounding`**.  
2. **Scenario A** still exposes **coverage limits**: critical dorm beats may **never** enter grounding unless phrasing matches **tight** rules.  
3. **No sign** of grounding **oscillation** or **wrong pruning** for the **one** active slot.  
4. **Next step:** **Audit 02** on Harley (or fresh run) using the same six monitors; optionally enable **per-turn audit JSON** under `rp_app/data/rp_audits/` to correlate **SETTLED SCENE FACTS** strings in Director/character payloads.

---

*Audit 01 — Scenario A (Kizzie, session `kizzie_marlene_fletcher_20260329_061642`).*
