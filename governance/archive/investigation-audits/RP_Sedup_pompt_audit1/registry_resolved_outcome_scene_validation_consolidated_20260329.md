# Registry resolved outcomes — real-environment scene validation (consolidated)

**Phase:** Scene validation per [resolved outcome system scene validation plan.md](../rp_app/resolved%20outcome%20system%20scene%20validation%20plan.md) (dual-layer audits, no code/schema/prompt changes during runs).

**Date:** 2026-03-29  
**Hard rules:** Record findings first; do not change prompts, JSON schema, or code while running or auditing scenes.

---

## 1. Scope (four aspects)

| Aspect | Role |
|--------|------|
| `lodging.sleep_surface` | Assignment |
| `communication.housing_call` | Terminal event |
| `medical.suppressant_formulation` | Subject attribute |
| `access.location_entry` | Permission; `location_id` bounded by template `location_entry_slots` |

**Expected emissions discipline (use on every turn):**

- Expected emissions require **explicit, present-tense settlement language** that matches the aspect’s emission rules (see `character_loader.py` — `CHARACTER_MOVE_SCHEMA` / system prompt; `prompt_builders.py` OUTPUT RULES).
- If language could be **ambiguous, advisory, conditional, delayed, or behavioral control** → **no** expected emission.
- If uncertain → **default to no expected emission** (do not over-predict).

**Per-turn Resolved Outcome Audit (minimum):**

Expected emissions → actual `scene_state_updates` (if present in structured move) → classification (Correct emission / False positive / Missed emission / Correct non-emission) → promotion result (`turn_metadata_by_index` debug) → slot impact (`continuity_state.resolved_outcomes`, active vs superseded) → grounding result (`metadata.scene_grounding` vs slot state).

**Narrative Audit:** existing qualitative scene analysis (story coherence, duplicate beats, etc.).

---

## 2. Authoritative artifacts and paths

| Item | Path |
|------|------|
| Plan | `autogen_rp/python/rp_app/resolved outcome system scene validation plan.md` (space in filename; quote in shells) |
| Persisted sessions | `autogen_rp/python/data/sessions/{session_id}.json` |
| Session index | `autogen_rp/python/data/sessions/_session_index.json` |
| App entry | `autogen_rp/python/rp_app/app.py` (Streamlit) |
| Continuity serialization | `metadata.continuity_state` from `ContinuityManager.to_dict()` → `continuity_scene_helpers.serialize_manager_state` |
| Engine debug merge | `continuity_manager.process_turn`: `turn_consequences["resolved_outcomes"]` updated from `apply_registered_resolved_outcome_updates` → stored in `turn_metadata_by_index[turn_index]` |
| Grounding rebuild | `scene_grounding.rebuild_scene_grounding_from_continuity` (markers on `PublicEvent` **and** active `resolved_outcomes`) |

**Legacy debug keys inside `turn_metadata_by_index[str(n)]["resolved_outcomes"]`:** one entry per registered aspect, keyed by **legacy key** (e.g. `housing_call`, `sleeping_surface`, `suppressant_formulation`, `location_entry`). Each value includes `decision`, `reason`, `candidate`, `outcome_id`, `supersedes_outcome_id`, etc. (see `resolved_outcome_engine.apply_registered_resolved_outcomes`).

**Continuity list:** `metadata.continuity_state.resolved_outcomes` — array of serialized `ResolvedOutcome` (when present); pair with `scene_state` / template fields such as `location_entry_slots` in `continuity_state.py`.

---

## 3. Critical finding: older session JSON shape

Inspection of **saved** sessions (e.g. `harley_quinn_marlene_fletcher_20260329_081213.json`, `kizzie_marlene_fletcher_20260329_061642.json`) shows `metadata.continuity_state` transitioning from **`public_events`** directly to **`interpretations`**, with **no** `resolved_outcomes` key between them.

Current code **does** include `resolved_outcomes` in `serialize_manager_state` (verified: `ContinuityManager.to_dict()` from `rp_app` working directory contains `public_events`, `resolved_outcomes`, `interpretations`).

**Implication for this validation phase:** Post–registry-commit runs must be **saved again** from the current app so that `continuity_state` includes `resolved_outcomes` and per-turn `resolved_outcomes` debug under `turn_metadata_by_index`. Relying only on the cited 2026-03-29 files **does not** satisfy the handoff’s requirement to audit promotion and slot state from disk for those artifacts.

**Grounding note:** The saved `scene_grounding.facts[]` for those runs shows `housing_call` with `source.kind`: **`continuity_event`** and `ref` pointing at a `PublicEvent` id — consistent with promotion via **event grounding markers**, not necessarily via a persisted `resolved_outcome` row in the file. Full dual-layer audits still need the structured move path + engine debug + `resolved_outcomes` list when validating the registry end-to-end.

---

## 4. Scene set — status vs plan

| # | Scene type | Plan checklist | Status | Evidence / notes |
|---|------------|----------------|--------|------------------|
| 1 | Calm / low-pressure | Low false positives; no casual emissions | **Not validated** (dedicated run) | No session mapped to this brief, minimal-conflict brief in this pass. |
| 2 | High-conflict / multi-speaker | Supersession, single active value per slot | **Partial** | Harley dorm run: `harley_quinn_marlene_fletcher_20260329_081213` (71 turns, 3 speakers). Narrative + grounding covered in [post_grounding_validation_audit_02_scenario_B_harley_20260329.md](./post_grounding_validation_audit_02_scenario_B_harley_20260329.md). **Registry per-turn audit** not completed on disk (serialization gap §3). |
| 3 | Control-language / ambiguity | “wait”, “not yet”, “for now”, etc. → `Correct non-emission` | **Not validated** | Requires scripted lines and per-turn classification; not present in cited sessions. |
| 4 | Mixed clarity + invalid bounded value | Valid emission only; `invalid_location_id` etc. | **Not validated** | Needs explicit invalid `location_id` and clear permission line in same scene. |
| 5 | Long (10–20 turns) | Stability, no drift | **Partial** | Harley session exceeds length; Kizzie `kizzie_marlene_fletcher_20260329_061642` also long. Grounding stability for `housing_call` documented in audits 01/02; **four-aspect** slot integrity not fully scored. |

**Related narrative/grounding audits (not a substitute for full Resolved Outcome Audit):**

- [post_grounding_validation_audit_01_scenario_A_kizzie_20260329.md](./post_grounding_validation_audit_01_scenario_A_kizzie_20260329.md) — `kizzie_marlene_fletcher_20260329_061642`
- [post_grounding_validation_audit_02_scenario_B_harley_20260329.md](./post_grounding_validation_audit_02_scenario_B_harley_20260329.md) — `harley_quinn_marlene_fletcher_20260329_081213`

---

## 5. Per-scene audit checklists (plan §Per-Scene Audit Checklist)

For each completed scene run, copy and fill with PASS/FAIL/N/A + turn indices.

### Emission accuracy

- [ ] All expected emissions occurred  
- [ ] No missed emissions  
- [ ] No false positives  
- [ ] Ambiguous cases correctly classified as non-emission  

### Promotion behavior

- [ ] All valid candidates promoted correctly  
- [ ] No incorrect promotions  
- [ ] No incorrect rejections  
- [ ] Identical-value no-ops handled correctly  

### Slot integrity

- [ ] No duplicate active states per slot  
- [ ] No cross-subject leakage  
- [ ] No subject/resource slot confusion  
- [ ] Supersession behavior is correct  

### Grounding consistency

- [ ] Grounding matches active slot state  
- [ ] No stale facts after supersession  
- [ ] No missing facts after valid promotion  
- [ ] No grounding from rejected/invalid outcomes  

---

## 6. Completion criteria (plan §Completion Criteria) — verdict

| Criterion | Verdict |
|-----------|---------|
| Near-zero false positives (all scenes) | **Open** — scenes 1, 3, 4 not run; 2/5 partial only. |
| Near-zero missed emissions | **Open** — same. |
| 100% correct promotion behavior | **Open** — cannot assert from disk without `resolved_outcomes` + per-turn debug in saved files. |
| 100% slot integrity | **Open** — same. |
| 100% grounding consistency | **Partial** — `housing_call` stable in audits 01/02; other aspects not evidenced on these runs. |

**Overall:** **Validation phase not complete.** Proceed only to “freeze baseline” after fresh real-environment runs (current app save format), five scene types, and filled per-turn Resolved Outcome Audits.

---

## 7. Execution notes for the next runner (Windows PowerShell)

- Chain commands with `;` not `&&`.  
- Quote paths that contain spaces.  
- After each scene: save session; open `autogen_rp/python/data/sessions/{session_id}.json`.  
- Confirm `metadata.continuity_state` contains **`resolved_outcomes`** and that `turn_metadata_by_index["<n>"]` contains **`resolved_outcomes`** with aspect keys.  
- Correlate `chat_history` / director payloads with turn indices (audit round/turn metadata in `metadata` when audit enabled).  
- Optional: `autogen_rp/python/rp_app/data/rp_audits/` for narrative audit artifacts — correlate via `audit_session_number` in session metadata.

**Implementation reference (read-only during validation):**

- `rp_app/resolved_outcome_registry.py`, `resolved_outcome_engine.py`  
- `rp_app/continuity_resolved_outcomes.py`, `continuity_manager.py`, `continuity_state.py`  
- `rp_app/scene_grounding.py`  
- `rp_app/character_loader.py`, `prompt_builders.py`  
- Tests: `tests/test_continuity_manager.py`, `test_scene_grounding.py`, `test_prompt_builders.py`, `test_characters.py`  
- Docs: `REGISTRY_VALIDATION_REPORT.md`, `DEBUGGING_GUIDE.md`, `autogen_rp/docs/audit-workflows.md`, `rp_app/AUDIT_DOCUMENTATION.md`

---

## 8. Deliverable template for each new scene

```markdown
## Scene N: <label>
- Session id:
- File: autogen_rp/python/data/sessions/<id>.json
- Template id / cast:
- Narrative Audit summary:
- Resolved Outcome Audit table: (per turn: expected → scene_state_updates → class → promotion → slot → grounding)
- Plan scene checklist: [x]/[ ]
- Per-scene audit checklist: [x]/[ ]
- Verdict: PASS partial / FAIL / blocked
```

When all scenes pass completion criteria, mark the plan’s exit condition and reference this file’s §6 update.
