# RP data layout

On-disk **data** for Holy Grail RP. Canonical root: **`data/`** at repository root (`HG_DATA_DIR`). Override with `HG_DATA_DIR`; sessions may use `HG_SESSIONS_DIR`.

Artifact semantics (especially audits): [audit-workflows.md](./audit-workflows.md). Product strategy: [Holy Grail PRD.md](../Holy%20Grail%20PRD.md) §6.

---

## Layout summary

```text
data/                           # HG_DATA_DIR
├── characters/                 # character cards (+ optional opener JSON)
├── scene_templates/            # scene template definitions
├── retrieval/                  # authored retrieval manifests; compiled index path is env-defined
├── fixtures/                   # tracked investigation / eval fixtures
│   └── progression_simulation_scenarios/   # scenario validation manifests
├── sessions/                   # persisted RP sessions (+ _session_index.json)
└── rp_audits/                  # optional per-turn audit trees (local, gitignored)
```

Local investigation output: `data/investigation_runs/` (gitignored).

---

## Character cards

**Path:** `data/characters/*.json`

**Contract:** [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md)

**Role:** Persona definitions — system prompt, personality, identity anchors, relationships, lore facts.

**Read by:** `character_loader.py`, `scene_opener.py`, UI modules.

**Written by:** Content authors / tooling outside the runtime turn loop.

---

## Scene templates

**Path:** `data/scene_templates/*.json` plus template-associated support files per [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md) (openers, progression payloads).

**Role:** Premise, `role_slots`, `anchor_role_name`, logistics anchors (`sleeping_surface_slots`, `location_entry_slots`), optional `opening_text`.

**Read by:** `scene_template.py`, `scene_lifecycle_start.py`, `prompt_builders.py`, `progression_advisory.py`.

Harness paths with `scene_template_id` use the same bootstrap spine as the application UI (`prepare_headless_session` / `scene_start_bootstrap`).

---

## Authored retrieval (offline)

**Manifest example:** `data/retrieval/authored_manifest.example.json`

**Compiled index:** produced offline; activate at runtime with `RP_RETRIEVED_CONTEXT_INDEX`. Not stored in-repo by default.

**Scope:** Pre-packaging ingestion only. Does not change continuity authority.

Operational baseline: [data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md](../data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md).

---

## Sessions

**Path:** `data/sessions/` (or `HG_SESSIONS_DIR`)

| Item | Description |
|------|-------------|
| `*.json` | One file per session id — team state, chat history, `character_states`, `continuity_state`, metadata |
| `_session_index.json` | Cached listing index (`SessionManager`) |

**Read by:** `SessionManager`, `session_lifecycle_load.py`

**Written by:** `SessionManager.save_session` via `session_lifecycle_save.py`

New sessions use opaque UUIDv4 filenames. Exact JSON keys follow code-defined serialization — not a stable public API.

### Audit identity in `metadata`

| Subfield | Role |
|----------|------|
| `audit_session_owner` | Canonical audit identity for audit-supported sessions |
| `scene_owner` | UI / display context only — not a substitute for `audit_session_owner` |

Saves lacking `audit_session_owner` cannot be audited on load (no backfill from `scene_owner`).

When Scene Grounding is active, expect prompt-facing derived facts in metadata or continuity blobs per [scene-grounding-layer.md](./scene-grounding-layer.md).

---

## Audit artifacts (`rp_audits`)

**Path:** `data/rp_audits/session_*` (gitignored generated trees)

**Role:** Optional per-turn investigation artifacts (`*_full.json`, summaries, manifests). **Not required** for session save/resume.

**Interpretation:** [audit-workflows.md](./audit-workflows.md)

**Cleanup:** permitted under agreed policy (GitHub #86). Deleting audit sessions does not corrupt saved UI sessions.

**Search tip:** gitignored trees may not appear in IDE search — confirm paths with filesystem listing.

---

## Fixtures

**Path:** `data/fixtures/`

Tracked JSON for investigation, evaluation, and scenario manifests. Scenario validation manifests: `data/fixtures/progression_simulation_scenarios/`.

---

## Environment variables

| Variable | Default | Role |
|----------|---------|------|
| `HG_DATA_DIR` | `<repo>/data` | Product data root |
| `HG_SESSIONS_DIR` | `<HG_DATA_DIR>/sessions` | Session persistence |
| `RP_RETRIEVED_CONTEXT_INDEX` | unset | Compiled retrieval index path |
| `RP_EPISODIC_MEMORY` | product default | Episodic memory feature flag |

---

## Persistence vs audit artifacts

| Store | Required for resume | Gitignored |
|-------|---------------------|------------|
| `data/sessions/*.json` | Yes | No (tracked or local per operator) |
| `data/rp_audits/` | No | Yes |

Trust **`continuity_state`** in session JSON and **`ContinuityManager`** at runtime before treating audit-only signals as proof of bugs.

---

## Related

- [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md)
- [MODULE_INDEX.md](../MODULE_INDEX.md) — `audit_logger_paths.py`, session modules
- `governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md` — historical artifact reference
