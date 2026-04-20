# RP data layout

On-disk and in-repo **data** used by `autogen_rp/python/rp_app`. Paths are relative to **`autogen_rp/python/`** unless noted. For artifact semantics (especially audits), see `python/rp_app/AUDIT_DOCUMENTATION.md`. Product-level data strategy: [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §6.

---

## Layout summary

```text
python/
├── data/
│   ├── autogen_characters/     # character cards (+ optional opener JSON)
│   ├── scene_templates/        # scene template definitions
│   ├── retrieval/              # authored retrieval manifest example(s); compiled index path is env-defined
│   └── sessions/               # persisted RP sessions (+ _session_index.json)
└── rp_app/
    └── data/
        └── rp_audits/          # optional per-turn audit trees
```

---

## Character cards

**Path:** `python/data/autogen_characters/*.json`

**Role:** Static (or hand-edited) **persona definitions**—system prompt, personality, identity anchors (`voice_profile`, `reaction_profile`, `speech_fingerprint`, `core_goals`), relationships, lore facts.

**Read by:** `character_loader.py`, `scene_opener.py` (initial messages), UI sidebar modules.

**Written by:** Content authors / tooling **outside** the runtime turn loop (not by continuity).

**Related:** `CHARACTER_MIGRATION_GUIDE.md` in `rp_app/`.

---

## Scene templates (“scenario” setup assets)

**Path:** `python/data/scene_templates/*.json`

**Role:** Premise, `role_slots` (e.g. `presence_constraint`: `must_remain`), required top-level **`anchor_role_name`** (one slot id for focal-thread setup; Issue #80), optional `opening_text`, and **bounded logistics anchors** such as `sleeping_surface_slots` and `location_entry_slots` (authoritative ids for registry-backed structured moves—not inferred from prose).

**Read by:** `scene_template.py`, `scene_lifecycle_start.py`, prompts via `prompt_builders.py`. **Headless simulation:** when a scenario sets `scene_template_id` (and optional `scene_template_role_assignments` per [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md)), `prepare_headless_session` loads the same JSON and merges those fields into `ContinuityManager.scene_state` so validators and prompts see the same contract as Streamlit template setup.

**Written by:** Designers / content; not mutated by session save.

---

## Authored retrieval manifest & compiled index (offline)

**Manifest (author input):** Lists static sources (character paths, templates, lore files, optional `initial_message` entries) for the **offline** compiler. **Example:** `python/data/retrieval/authored_manifest.example.json` — copy and extend for a real build; paths are relative to the manifest file’s directory unless absolute.

**Compiled index (artifact):** Produced by `python/scripts/compile_authored_retrieval_index.py` with **`--schema-version 2`** (default, legacy chunk shape only) or **`--schema-version 3`** (adds canonical fields per [CANONICAL_KNOWLEDGE_MODEL.md](../../CANONICAL_KNOWLEDGE_MODEL.md); **same** legacy fields the runtime reads). Not stored in-repo by default; set **`RP_RETRIEVED_CONTEXT_INDEX`** to the output JSON path when using authored retrieval.

**Scope:** Pre-packaging **ingestion** only. Does **not** integrate vector/graph retrieval or change continuity authority.

---

## Sessions

**Path:** `python/data/sessions/`

| Item | Description |
|------|-------------|
| `*.json` (excluding index) | One file per RP session id: team/agent state, chat history, serialized `character_states`, `continuity_state`, memory buckets, scene status, audit session numbers, etc. |
| `_session_index.json` | Cached index for listing/resuming sessions (versioned in code: `SessionManager`) |

**Read by:** `SessionManager`, `session_lifecycle_load.py`, startup recovery in `app_bootstrap.py`.

**Written by:** `SessionManager.save_session` via `session_lifecycle_save.py` (typically after turns and scene changes).

**Note:** Exact JSON keys evolve with `continuity_manager.to_dict()` and character state serialization; treat shape as **code-defined**, not stable public API.

### Top-level session JSON shape

Each `{session_id}.json` file is written by `SessionManager.save_session` and contains:

| Field | Role |
|-------|------|
| `session_id` | Filename key and identifier in UI |
| `saved_at` | UTC ISO timestamp |
| `characters` | Cast names for this session |
| `team_state` | Serialized AutoGen team state (`team.save_state()`) |
| `player_character` | Which card the user controls, if any |
| `chat_history` | Messages for replay in UI |
| `metadata` | Extensible bag (see below) |

**`metadata`** (populated from `session_lifecycle_save.py` among others) typically includes: `summary`, `character_states`, `memory_buckets`, `bot_reply_limit`, `continuity_state`, `player_control_mode`, `scene_status`, `scene_closed_reason`, audit counters (`audit_session_number`, `audit_round_number`, `audit_turn_number`), `audit_enabled`, `scene_owner` / `audit_session_owner`. When the **Scene Grounding** MVP is implemented, expect a scene-scoped **`scene_grounding`** (or equivalent) blob: **prompt-facing derived facts**, not a second continuity authority — see [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8 and [scene-grounding-layer.md](./scene-grounding-layer.md). **Trust the code** for the current full set.

### When sessions are saved

Saves go through `session_lifecycle_save.py` → `SessionManager.save_session` when the app persists (e.g. after turns and scene transitions—see call sites from `app.py` / lifecycle). If something is wrong **only after reload**, compare **disk JSON** to what `session_lifecycle_load.py` restores into `st.session_state`.

### `_session_index.json`

Derived index for fast listing; updated when sessions are saved. If the list UI looks wrong but the `.json` session file is fine, inspect index update logic in `session_manager.py`.

### Reload debugging (quick)

1. Open `python/data/sessions/{session_id}.json` and confirm `continuity_state` / `character_states` / `chat_history` look plausible.
2. Trace `load_session` → `session_lifecycle_load.py` for which keys hydrate Streamlit state.
3. Check `app_bootstrap.py` for incomplete-session recovery altering startup.

More: [DEBUGGING_GUIDE.md](../../DEBUGGING_GUIDE.md) § persistence.

---

## Audit outputs

**Path:** `python/rp_app/data/rp_audits/` (default; see `audit_logger_paths.py`)

**Layout:** `session_{nnn}/` → `_manifest.json`, `_round_index.json`, `_narrative.json`, `_audit_summary.json`, `round_{nnn}/` → per-turn `*_director_*`, `*_{character}_*`, `*_narrator_*` JSON files.

**Session folder number** (`session_047`) is the **audit** session ordinal, not necessarily the same string as the **persistence** `session_id` in `data/sessions/`. Correlation is via saved metadata (`audit_session_number`, etc.) when enabled.

**Typical analysis path:** `_manifest.json` (cast + template) → `_round_index.json` (turn order) → per-turn `*_director_light.json` / `*_full.json` for decisions and payloads → `_narrative.json` / `_audit_summary.json` for rolled-up story and flags.

**Read by:** Humans, external review workflows, tests; `audit_logger` / summary modules for refresh.

**Written by:** `audit_logger*.py` when audit enabled in UI.

**Details:** `python/rp_app/AUDIT_DOCUMENTATION.md`, `docs/audit-workflows.md`.

---

## What is *not* here yet

- **Graph / vector databases** — future ingestion layer (PRD §§3.1, 7).
- **Compiled packet store** — packaging layer will read authoritative session/continuity state plus retrieval outputs; see [PACKET_CONTRACTS.md](../../PACKET_CONTRACTS.md).

---

## Related

- [repo-map.md](./repo-map.md) — repo-wide orientation
- [architecture.md](./architecture.md) — guardrails
- [MODULE_INDEX.md](../../MODULE_INDEX.md) — which code reads/writes each concern
