# V2 Session Setup — M9 Implementation Report

**Status:** Completed (M9 — authored character cards, scene templates, opening configuration)  
**Date:** 2026-08-18  
**M8 durable transcript anchor:** `8f360a1`  
**Implementation HEAD:** `c86de28`

**Governing principle:**

> Authored assets are loaded and interpreted only by the Python Domain Host. The UI sends identifiers and choices; DSH never loads character files.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `8f360a1` |
| Assigned / effective workflow weight | standard / **full** |
| Bootstrap profile | full V2 implementation |

Pre-slice: 47 Python + 49 Node tests green (M8).

---

## 2. Authored setup inventory

### Character cards

| Item | Location / behavior |
|------|-------------------|
| Directory | `autogen_rp/python/data/autogen_characters/*.json` |
| Loader | `CharacterLoader` (`character_loader.py`) |
| ID | File stem (e.g. `kizzie`) |
| Display name | `name` field → authoritative `CharacterState.name` |
| Domain-only | `system_prompt`, `lore_facts`, full personality scaffolding |
| UI-safe | `character_id`, `display_name`, truncated `description` |

### Scene templates

| Item | Location / behavior |
|------|-------------------|
| Directory | `autogen_rp/python/data/scene_templates/{template_id}.json` |
| Manager | `SceneTemplateManager` |
| Authoritative fields | `premise`, `role_slots`, `anchor_role_name`, presence/authority via `apply_scene_setup_to_scene_state` |
| Opener assets | `{template_id}_*_initial_message.json` via `OpenerManager` |

### Opening modes (classified)

| Artifact | Classification |
|----------|----------------|
| Template premise / role slots | Authoritative `SceneState` |
| Template/custom opener prose | Presentation (`rp_history` kind `opening`) |
| `system_prompt` / `lore_facts` | Domain-only (ContextAssembly) |
| M9 scope | `minimal` (premise), `custom` text; template opener catalog exposed, full bootstrap deferred |

---

## 3. M9 ownership model

```text
Authored JSON assets
    ↓
Domain Host: setup_catalog.py + session_setup.py
    ↓
setup_snapshot (immutable at create) + LiveSession / ContinuityManager
    ↓
SessionRepository persistence (v2_host_state)
    ↓
Application API / HolyGrailApplicationClient (IDs only)
    ↓
Streamlit (pickers)
```

| Layer | Responsibility |
|-------|----------------|
| Domain Host | Load, validate, snapshot, initialize authoritative state |
| Application server | Proxy catalog + create; never parse cards |
| DSH | Orchestration only; context via `HgContextBridge` |
| UI | Select `character_id`, `scene_template_id`, opening mode |

---

## 4. Character-card architecture

- Reuses production `CharacterLoader` and `CharacterState` mapping (extracted from V1 `create_agent` without AutoGen).
- Stable IDs: file stems (`kizzie`, `willow`).
- Canonical actor identity for rounds: card `name` (`Kizzie`, `Willow Reeves`).
- `character_file_ids` map display name → file stem for forced-speaker alias resolution.

---

## 5. Scene-template architecture

- `session_setup._resolve_scene_setup` — headless V1 `resolve_scene_template_setup` (no Streamlit).
- `apply_scene_setup_to_scene_state` + `build_initial_scene_issues` → `ContinuityManager`.
- Template snapshot stored in `setup_snapshot.scene_template` at create time.

---

## 6. Opening semantics

| Mode | Behavior |
|------|----------|
| `minimal` | Uses template premise or default description; no extra history entry |
| `custom` | User text → `rp_history` kind `opening` (presentation) |
| `template` | Resolves opener asset by `opener_id` (API catalog supported; Streamlit defers to M10) |

Opening prose is **not** committed domain canon.

---

## 7. Session-setup contract

**Production `POST /v1/sessions/create`:**

```json
{
  "characters": ["kizzie", "willow"],
  "scene_template_id": "celina_apartment_recovery_watch",
  "role_assignments": {
    "kizzie": "recovering_demi_human",
    "willow": "protector"
  },
  "opening": { "mode": "minimal" }
}
```

**Test-only prototype path:** `{ "cast": ["Alice"] }` (unchanged for deterministic unit tests).

**Response:** `SessionInfoResponse` includes `setup_provenance` (UI-safe) and `character_file_ids`.

---

## 8. Asset provenance model

**Decision: snapshot at session creation.**

`setup_snapshot` persists:

- `character_cards` (full card JSON at create time)
- `scene_template` dict
- `role_assignments_by_file`, `opening`, `location`

Resumed sessions use persisted `CharacterState` + snapshot — **not** live file reinterpretation.

**Proof:** `test_snapshot_survives_card_edit_after_create` (Python).

---

## 9. Character/template discovery API

| Endpoint | Returns |
|----------|---------|
| `GET /v1/catalog/characters` | UI-safe character list |
| `GET /v1/catalog/scene-templates` | Template metadata + role slots |
| `GET /v1/catalog/scene-templates/{id}/openers` | Opener labels (no private card text) |
| `GET /api/characters` | Application proxy |
| `GET /api/scene-templates` | Application proxy |

---

## 10. Streamlit setup UX

`v2/ui/streamlit_app.py`:

- Character multiselect from catalog
- Optional scene template select
- Opening: minimal / custom
- Create session → shows `setup_provenance`
- Resume displays persisted setup (no re-pick)

Prototype comma-separated cast remains fallback when catalog unavailable.

---

## 11. Session reopen behavior

- `open_session` hydrates `setup_snapshot`, `character_file_ids`, `CharacterState`, `rp_history`.
- Transcript rebuilt via M8 projection (includes `opening` entries).
- No requirement to re-select cards/templates.

---

## 12. Context/isolation proof

`test_context_projection_isolates_private_material`:

```text
kizzie + willow + celina_apartment_recovery_watch
    → Domain Host CharacterState + scene roles
    → prepare_context (Kizzie)
    → character_profile + scene_state + character_private (Kizzie only)
```

No `system_prompt` field leakage; Willow private material absent from Kizzie manifest.

---

## 13. Production real-card round proof

- Python: session create from real cards + template + role validation
- Node: `session-setup.test.mjs` — catalog + authored create + file-id forced speaker
- Existing suites: 51 Python + 51 Node (includes live DeepSeek user-turn smoke from M7/M8)

---

## 14. Forced-speaker identity integration

`detectForcedSpeaker` accepts `characterFileIds` — mentions of file stem (`willow`) resolve to canonical display name (`Willow Reeves`) for `ParticipationDecision`.

---

## 15. V1 retirement candidates

| V1 component | V2 replacement | Removal condition |
|--------------|----------------|-------------------|
| `app.py` character file scanning | `GET /api/characters` | V2 default entry only |
| `ui_sidebar_*` card picker | Streamlit catalog pickers | V1 entry deleted |
| Streamlit `scene_role_assignments` init | `sessions/create` role_assignments | V1 setup path unused |
| Prototype cast text input (production) | Character ID multiselect | No production cast-name path |
| `resolve_scene_template_setup(st_module)` | `session_setup._resolve_scene_setup` | V1 scene start retired |

**Not deleted in M9** — classification only.

---

## 16. Remaining V1-only capabilities

| Area | Notes |
|------|-------|
| Audit/debug UI | Unchanged |
| Cross-session memory | Episodic memory not in V2 application |
| Knowledge / vector / graph DB | Not migrated |
| Full opener bootstrap (LLM-generated, character openers) | Catalog exposed; Streamlit minimal modes only |
| Rich settings / player character selection | Deferred |
| V1 `turn_runner` / AutoGen agents | Still V1 orchestration spine |

**Largest remaining blocker:** cross-session memory + knowledge retrieval (or audit UI if ops priority).

---

## 17. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python (`v2/tests/`) | 51 passed |
| V2 Node (`v2/rp_runtime/tests/`) | 51 passed |
| Session setup / snapshot / context isolation | ✅ |
| Application client + live DeepSeek smoke | ✅ |

---

## 18. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `setup_catalog.py`, `session_setup.py`, catalog HTTP, production `sessions/create`, setup provenance, V2 Streamlit pickers |
| **Reused/refactored** | `CharacterLoader`, `SceneTemplateManager`, `apply_scene_setup_to_scene_state`, `OpenerManager` |
| **Superseded for V2** | UI filesystem scanning, Streamlit-owned CharacterState init, production prototype cast names |
| **Transitional** | `cast: ["Alice"]` test-only create path |
| **Test-only** | `initialize_live_session` synthetic cast |

---

## 19. Challenge/refinement

| Question | Verdict |
|----------|---------|
| Domain Host owns authored semantics? | Yes |
| UI only chooses IDs? | Yes |
| Private card content leaked to UI? | No — catalog strips `system_prompt` / `lore_facts` |
| Resumed sessions stable after file edits? | Yes — snapshot semantics |
| Real cards through normal context projection? | Yes |
| Prototype cast production path removed? | Yes (Streamlit uses catalog when available) |

---

## 20. Architecture verdict

**Validated as designed** — authored setup boundary enforced; snapshot provenance protects historical sessions.

---

## 21. Repository state

| Field | Value |
|-------|-------|
| Commit (feat) | `c86de28` — `feat(v2): M9 session setup from authored cards and templates` |
| Branch | `main` |
| `origin/main` | aligned after push |

---

## 22. Next recommended migration slice

**M10 — Cross-session memory projection (recommended):** Wire episodic/session memory inputs behind Domain Host with explicit UI-safe recall boundaries; do not port V1 `st.session_state` memory caches. Alternative: **audit/debug UI** if operational visibility is higher priority. **Governance review required before implementation.**
