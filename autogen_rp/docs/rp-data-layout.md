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

**Contract:** Canonical authored fields and exclusions (vs bootstrap/session/ingestion) are defined in **[AUTHORED_SOURCE_CONTRACT.md](../../AUTHORED_SOURCE_CONTRACT.md)**. Files may still be **legacy or mixed** until the **dedicated migration issue** (linked from **GitHub #82** and `AUTHORED_SOURCE_CONTRACT.md` §8) is implemented.

**Role:** Static (or hand-edited) **persona definitions**—system prompt, personality, identity anchors (`voice_profile`, `reaction_profile`, `speech_fingerprint`, `core_goals`), relationships, lore facts.

**Read by:** `character_loader.py`, `scene_opener.py` (initial messages), UI sidebar modules.

**Written by:** Content authors / tooling **outside** the runtime turn loop (not by continuity).

**Related:** `CHARACTER_MIGRATION_GUIDE.md` in `rp_app/`.

---

## Scene templates (“scenario” setup assets)

**Path:** `python/data/scene_templates/*.json` (primary **template** **definition** per `template_id`) **and** **Template-associated support files** in the same directory (see **[AUTHORED_SOURCE_CONTRACT.md](../../AUTHORED_SOURCE_CONTRACT.md)** §1 *Template-associated support files*): e.g. `{template_id}_initial_message.json` (Opener), `{template_id}_progression.json` (Progression Advisory payload for **Template Exclude** `progression_profile`). These co-located files are **not** `SceneTemplate` bodies; **enumeration** excludes them from the **template list** (same family of rule as `*_initial_message` / `*_progression`).

**Contract:** Structural template knowledge vs **Scenario / Bootstrap** scene-start records vs **Opener** prose is defined in **[AUTHORED_SOURCE_CONTRACT.md](../../AUTHORED_SOURCE_CONTRACT.md)** (`opening_text` = legacy fallback; `initial_messages` not canonical). **`progression_profile`** is **Template Exclude**; **authored** payload is **only** in `{template_id}_progression.json` (**#119**), **not** in `{template_id}.json`.

**Role (primary `template_id.json`):** Premise, `role_slots` (e.g. `presence_constraint`: `must_remain`), required top-level **`anchor_role_name`** (one slot id for focal-thread setup; Issue #80), optional `opening_text`, and **bounded logistics anchors** such as `sleeping_surface_slots` and `location_entry_slots` (authoritative ids for registry-backed structured moves—not inferred from prose).

**Read by:** `scene_template.py`, `scene_lifecycle_start.py`, prompts via `prompt_builders.py`; **`progression_advisory.load_progression_profile_for_template_id`** for `{template_id}_progression.json` or defaults. **Headless simulation:** when a scenario sets `scene_template_id` (and optional `scene_template_role_assignments` per [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md)), `prepare_headless_session` routes template setup through the **same** fresh-scene continuity bootstrap as Streamlit (GitHub **#83** — `scene_start_bootstrap` / `restore_or_initialize_continuity_manager`), so validators and prompts see the **same** template contract as UI template startup—not a deferred second merge pass.

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
| `*.json` (excluding index) | One file per RP session id: team/agent state, chat history, serialized `character_states`, `continuity_state`, memory buckets, scene status, audit session numbers, etc. **New** sessions use an **opaque UUIDv4** string as `session_id` / filename stem ([Issue #109](https://github.com/KizzieFae/Holy_Grail_RP/issues/109)). **Legacy** files may retain older cast+timestamp-shaped stems; load by stored `session_id` as-is (no migration). |
| `_session_index.json` | Cached index for listing/resuming sessions (versioned in code: `SessionManager`) |

**Read by:** `SessionManager`, `session_lifecycle_load.py`, startup recovery in `app_bootstrap.py`.

**Written by:** `SessionManager.save_session` via `session_lifecycle_save.py` (typically after turns and scene changes).

**Note:** Exact JSON keys evolve with `continuity_manager.to_dict()` and character state serialization; treat shape as **code-defined**, not stable public API.

### Top-level session JSON shape

Each `{session_id}.json` file is written by `SessionManager.save_session` and contains:

| Field | Role |
|-------|------|
| `session_id` | Filename key and identifier in UI — **opaque** UUIDv4 for new saves (#109); legacy shapes may still exist on disk |
| `saved_at` | UTC ISO timestamp |
| `characters` | Cast names for this session |
| `team_state` | Serialized AutoGen team state (`team.save_state()`) |
| `player_character` | Which card the user controls, if any |
| `chat_history` | Messages for replay in UI |
| `metadata` | Extensible bag (see below) |

### Audit identity in `metadata` (Issue #106)

| Subfield | Role |
|----------|------|
| `audit_session_owner` | **Canonical audit identity** (required for any audit-supported session). Set at **ingress** (Streamlit, headless, or from a save that already persisted this field). Used for audit filenames, manifest / narrative / summary `session_owner` strings. **No** inference from `scene_owner`, cast, or display names. [Issue #106](https://github.com/KizzieFae/Holy_Grail_RP/issues/106). **Streamlit (auditing on):** deterministic slug of opaque `session_id` only (#109). **Headless:** unchanged scenario/harness/ad-hoc labels (#109). |
| `scene_owner` | **UI / session / narrator context only** (e.g. display, packets). **Not** a substitute for `audit_session_owner` and **not** a fallback if `audit_session_owner` is missing. [Issue #107](https://github.com/KizzieFae/Holy_Grail_RP/issues/107) |

**Load behavior:** `audit_session_owner` is **required** to treat a session as audit-supported. Saves that lack it (legacy) **cannot** be audited: auditing is **disabled** on load; there is **no** backfill from `scene_owner` (archival only, not migration).

**`metadata`** (populated from `session_lifecycle_save.py` among others) also typically includes: `summary`, `character_states`, `memory_buckets`, `bot_reply_limit`, `continuity_state`, `player_control_mode`, `scene_status`, `scene_closed_reason`, audit counters (`audit_session_number`, `audit_round_number`, `audit_turn_number`), `audit_enabled`, and the audit fields above. When the **Scene Grounding** MVP is implemented, expect a scene-scoped **`scene_grounding`** (or equivalent) blob: **prompt-facing derived facts**, not a second continuity authority — see [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8 and [scene-grounding-layer.md](./scene-grounding-layer.md). **Trust the code** for the current full set.

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
- **User callout files (GitHub #55 / #125 / #126):** Under each **`session_*/`**, per-session **`user_callouts_v1.json`** stores callouts: an optional **operator** **note** plus **system-authored** **`artifact_refs`** (including optional **`related_artifact_refs`**, **#126** at save; operators do not pick paths in the app). At the **`rp_audits/`** root, **`_user_callout_review_index_v1.json`** is the **keyed review queue only** and **does not** contain **`artifact_refs`** (those live on the per-session file). **`_user_callout_issue_links_v1.json`** maps **`callout_id` → GitHub issue** (sole “promoted” link record). New callouts from Streamlit **append** to the per-session file and **upsert** the review index. **List / show / dismiss / promote / rebuild / links** are **operator CLI** only: `autogen_rp/python/scripts/user_callout_review.py`. **Default** `promote` rejects a duplicate `callout_id` already in the link map; **`promote --replace`** rewrites the **one** link row when reconciliation requires a different issue target (updates `linked_at_utc`; does not track GitHub lifecycle; raw callouts unchanged). Authoritative details: **[`AUDIT_DOCUMENTATION.md`](../python/rp_app/AUDIT_DOCUMENTATION.md)** **§6–§8** (not restated here).

#### Audit artifact discovery (tooling)

`rp_app/data/rp_audits/` is governed by a restrictive `.gitignore` (session trees and nearly all JSON are **not** tracked). **Default IDE and Cursor workspace search (including Glob-style repo search) typically skip gitignored paths**, so a **zero-result search does not prove** that `session_*` is missing on disk.

**Before concluding an audit session is absent**, verify on the real filesystem: list `autogen_rp/python/rp_app/data/rp_audits/session_{NNN}/` (audit ordinal, 3-digit folder name) or **read** a concrete path from `user_callouts_v1.json` → `artifact_refs` (or the user-provided path). **Absence from Git / from workspace search ≠ absence from the runtime environment.**

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
