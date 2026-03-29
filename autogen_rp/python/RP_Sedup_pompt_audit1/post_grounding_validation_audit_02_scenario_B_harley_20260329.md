# Post–Scene Grounding validation — Audit 02 (Scenario B: Harley / high-agency stress)

**Audit type:** Post-implementation continuity → grounding validation (Phase 0 + Phase 1/2)  
**Primary source:** `autogen_rp/python/data/sessions/harley_quinn_marlene_fletcher_20260329_081213.json`  
**Session id:** `harley_quinn_marlene_fletcher_20260329_081213`  
**Saved at (UTC):** 2026-03-29T09:23:59Z  
**Template:** `marlene_willow_dorm_omega_misassignment`  
**Cast:** Harley_Quinn (omega), Marlene_Fletcher, Willow_Reeves — **Scenario B** (chaotic / provocative omega, two alphas).  
**Scene end:** `user_ended` · `scene_status`: **closed**

**Paired audit:** [post_grounding_validation_audit_01_scenario_A_kizzie_20260329.md](./post_grounding_validation_audit_01_scenario_A_kizzie_20260329.md) (Kizzie, low-agency)

**Procedure:** [autogen_rp/docs/audit-workflows.md](../../docs/audit-workflows.md) · Evidence from **session JSON** (`team_state`, `continuity_manager` snapshot, `scene_grounding`, `public_events`); per-turn `rp_audits/*.json` not used for this pass.

---

## 1. Executive summary

**Grounding pipeline:** The **same allowlisted logistics fact** as the Kizzie run—**housing / res-life call completed**—is present in **`scene_grounding`** at save, sourced from **`evt_…_9`**, with **`supersedes`: null** (only **one** promoting event for that slot in this session; no multi-event supersession chain like Audit 01).

**Stability under high churn:** From **`last_rebuilt_turn`: 71** and a long tail of **`PublicEvent`s** with **empty `grounding_markers`**, the **single** settled fact **does not oscillate or vanish**—there is simply **no competing marker** for that slot. This is **PASS** for “facts don’t flicker wrongfully,” **limited** for “rich medical / territorial / injury state” because **those beats never matched** current lexical rules.

**Scenario B dynamics:** **High** structural stall (**`stall_score` 0.85**), **`issue_stability`: true**, **anti-regression `active`: true** with **`ping_pong_detected`** on **Harley_Quinn ↔ Marlene_Fletcher**. Late Directors explicitly reference **breaking ping-pong** and **only available actor** when **Willow_Reeves** is **offstage**. Continuity keeps a **single escalating safety issue** open at save. **`pending_beat_shift`**: **inactive** (clean vs older Kizzie session 57 pattern).

**Verdict:** **Phase 0 persistence** holds for the **housing_call** slot under **dense, confrontational turns**. **Coverage** remains **narrow**: dramatic content (secrets, territory, physical provocation) does **not** translate into additional grounded facts without **new promotion rules**.

---

## 2. Saved `scene_grounding` (at save)

| Field | Value |
|--------|--------|
| `schema_version` | 1 |
| `last_rebuilt_turn` | 71 |
| Facts (count) | **1** |
| Category / key | `communication_state` / `housing_call` |
| `value_summary` | `Housing call: completed` |
| `source.ref` | `evt_2026-03-29T08:20:55.373347+00:00_9` |
| `supersedes` | **null** |

---

## 3. Mechanical signals at save (stress vs Audit 01)

| Signal | Harley (this run) | Kizzie (Audit 01) |
|--------|-------------------|-------------------|
| `stall_score` | **0.85** | 0.6 (from prior note in 061642 metadata region) |
| `progression_pressure` | **high** | high |
| `stall_components.issue_stability` | **true** | false (Kizzie 061642) |
| `anti_regression.active` | **true** | false (Kizzie 061642) |
| `ping_pong_detected` | **true** (Harley ↔ Marlene) | false |
| `pending_beat_shift.active` | **false** | (Kizzie 061642: false) |
| `offstage_characters` @ save | **`["Willow_Reeves"]`** | (not flagged same way in excerpt) |
| `continuity_active_issues` | **1** escalating, unresolved | 1 escalating @ save (061642) |

---

## 4. Additional validation dimensions

### 4.1 Marker persistence

- **`communication_state:housing_call|status=completed`** appears on **`evt_…_9`** (and matching **`turn_metadata`**).  
- **PASS:** Fact **survives** full rebuild through turn **71**; **no** intermittent drop for that slot.

### 4.2 Previously resolved topics / rehash

- Not scored line-by-line against chat. Fiction includes **long Marlene ↔ Harley** run (secrets, trauma weaponized, territorial denial). **Grounding** does **not** encode “secret shared” or “Willow backstory” — so **re-asking** those in prose would **not** be contradicted by SETTLED FACTS (coverage gap, not persistence bug).

### 4.3 Soft state resets (grounding layer)

- **No** second housing marker later contradicting “completed.”  
- **PASS** for **grounding** consistency on the **one** slot.

### 4.4 Stability under conflict (Scenario B goal)

- **~60+** turns with **extreme** tension and **many** `PublicEvent`s; **grounding fact count stays 1**.  
- **PASS:** No evidence of **wrongful oscillation** on `housing_call`.  
- **Observation:** **Escalation did not add** new grounded slots (e.g. no **bandage** / **weapon** hits in this run’s text search—arc is **not** the bathroom-injury path from the older Harley session in `Kizzie_dorm_rerun_audit_20260328.md`).

### 4.5 Low-signal turns

- N/A as primary stressor; Harley run is **high** signal density.

### 4.6 Over-promotion / noise

- **Many** continuity events; **one** grounding bullet.  
- **PASS:** Grounding is **not** cluttered.

---

## 5. Narrative / orchestration notes (observation only)

- **Director** tail reasons describe **Marlene–Harley** as the only practical pair when **Willow** is **offstage**, while **anti-regression** flags **Harley ↔ Marlene ping-pong** — tension between **structural detection** and **cast availability** is visible in metadata (no fix proposed here).
- **Player character** remains **`null`** in JSON (custom persona / Traveler pattern from prior audits may still apply to **`low_player_agency`**).

---

## 6. Kizzie (Audit 01) vs Harley (Audit 02) — grounding-focused

| Dimension | Kizzie `…061642` | Harley `…081213` |
|-----------|------------------|------------------|
| Settled facts @ save | 1 (`housing_call`) | 1 (`housing_call`) |
| Supersession chain | **Yes** (earlier fact id superseded) | **No** (single promoter for slot) |
| Stall / ping-pong | Lower stall; no AR ping-pong in snippet | **0.85** stall; **ping_pong true** |
| Grounding oscillation | None observed | None observed |
| Coverage beyond housing | Sparse (suppressants / sleep phrasing) | Sparse (secrets / territory not in allowlist) |

---

## 7. Conclusions (no fixes in this document)

1. **Harley run** validates **persistence + non-oscillation** of the **housing_call** grounded fact across **high event density** and **71** continuity turns.  
2. **Scenario B** does **not** automatically produce **more** grounded facts; **lexical allowlist** still gates what enters SETTLED SCENE FACTS.  
3. **Anti-regression + high stall** coexisting with **volatile** fiction matches earlier **Harley dorm** notes: the **metric** reads “stuck”; the **play** can still feel **kinetically busy**.  
4. Optional follow-up: **per-turn audit JSON** under `rp_app/data/rp_audits/session_061/` (if present) to confirm **SETTLED SCENE FACTS** text in Director/character payloads on late turns.

---

*Audit 02 — Scenario B (Harley, session `harley_quinn_marlene_fletcher_20260329_081213`).*
