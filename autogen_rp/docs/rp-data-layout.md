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

**Read by:** `scene_template.py`, `scene_lifecycle_start.py`, prompts via `prompt_builders.py`. **Headless simulation:** when a scenario sets `scene_template_id` (and optional `scene_template_role_assignments` per [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md)), `prepare_headless_session` routes template setup through the **same** fresh-scene continuity bootstrap as Streamlit (GitHub **#83** — `scene_start_bootstrap` / `restore_or_initialize_continuity_manager`), so validators and prompts see the **same** template contract as UI template startup—not a deferred second merge pass.

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

## Persistence vs Audit Artifacts

Paths below are relative to the repository root (`autogen_rp/`) unless otherwise noted.

This section states how **runtime/session persistence** relates to **audit artifacts** on disk. Authoritative narrative state and production gating are defined in **`ContinuityManager`** / **`SceneState`** and related runtime docs; audit applicability and “non-authoritative” rules for observational signals are in **GitHub #59** ([`AUDIT_DOCUMENTATION.md`](../python/rp_app/AUDIT_DOCUMENTATION.md)).

### Runtime / session persistence

- **Location:** `autogen_rp/python/data/sessions/*.json`
- **Contents:** Each file includes serialized **`continuity_state`** (continuity snapshot), **`character_states`**, **`chat_history`**, team/session plumbing, and other fields written by **`SessionManager.save_session`**—see **Sessions** above and `session_lifecycle_save.py` under `python/rp_app/`.
- **Save / resume:** The Streamlit app **loads resumed play from these session JSON files** for continuity and UI state restoration. **`autogen_rp/python/data/sessions/_session_index.json`** supports listing; session truth for resume is the per-session `*.json` files.

### Audit artifacts

- **Location:** `autogen_rp/python/rp_app/data/rp_audits/session_*`
- **Role:** **Observational, debugging, and validation** output: per-turn logs, summaries (`_audit_summary.json`, `_narrative.json`, per-character `*_full.json`, etc.). **Issue #79** observability blocks (for example **`continuity_observability_summary_v1`**) appear **in audit summaries** as mirrors or rollups when emitted—they are **not** a substitute for **`ContinuityManager`** as system-of-record.

### Guarantees

- **UI resume** hydrates from **`autogen_rp/python/data/sessions/`** session files; it does **not** read **`rp_audits/`** to restore gameplay state.
- Audit files are **non-authoritative** for committed continuity truth; do not treat audit JSON as a second persistence store (**#59**).
- **Deleting** `autogen_rp/python/rp_app/data/rp_audits/session_*` trees does **not** invalidate or alter saved **`autogen_rp/python/data/sessions/*.json`** files.
- The runtime operates correctly with **auditing disabled** or with **audit directories removed**; absence of `rp_audits` does not block save/load of sessions.

### Relationship

- The **audit system observes** the runtime/session pipeline (logging, mirrors for operators and offline eval)—not the reverse.
- Audit output **must not** be used as a **persistence layer** or **authority layer** for resume, continuity commits, or production gating except where explicitly allowlisted under **#59** (empty by default).

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
