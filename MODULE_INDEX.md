# RP app module index

**Location:** Every module named below lives in **`autogen_rp/python/rp_app/`** (unless a path is written out explicitly).

Quick map for **where to change what**. Architecture rules: [autogen_rp/python/rp_app/ARCHITECTURE.md](./autogen_rp/python/rp_app/ARCHITECTURE.md), [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md), and [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md).

**Constraints (recurring):** Keep `app.py` thin. Do not fix continuity/orchestration bugs by bloating Director prompts. Preserve `must_remain` as **structural presence**, not “must speak every turn.”

For **diagnosis order** and layer rules, see [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

---

## Symptom → first file to open

Use this for a fast landing spot; the tables below add detail. Full workflow: [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

| Symptom or task | Start here (under `autogen_rp/python/rp_app/`) |
|-----------------|-----------------------------------------------|
| Wrong actor / rotation / “ignored” address | `orchestration_helpers.py`, then `app_turn_director.py`, `response_validation_selection.py`, `semantic_validation.py` |
| Director JSON parse / invalid `next_actor` | `response_validation_parsing.py`, `response_validation_selection.py`, `app_turn_director.py` |
| Character speaks for others / bad JSON shape | `response_validation_content.py`, `response_validation_parsing.py` |
| **Duplicate** dialogue or repeated line | `response_validation_content.py` (`is_duplicate_dialogue`), `turn_runner_turn.py` (retry path) |
| **Presence** / exit / `must_remain` | `response_validation_presence.py`, `scene_template.py`, `semantic_validation.py` (override paths) |
| **Drift** / voice / anchors | `response_validation_drift.py`, `character_state_model.py`, cards in `autogen_rp/python/data/autogen_characters/` |
| **Plateau** / stalled high-tension verbal loop (progression pressure + advisory + beat-shift) | `progression_pressure.py`, `orchestration_helpers.py`, `app_turn_director.py`, `turn_runner_updates.py`, `progression_advisory.py`, `beat_shift_state.py`, `app_turn_prompting.py`, `prompt_builders.py` |
| Stale issues / bad event memory / knowledge boundaries | `continuity_manager.py`, `continuity_issue_helpers.py`, `continuity_knowledge_helpers.py` |
| **Settled facts** repeated / logistics reset in dialogue (after continuity looks correct) | `continuity_resolved_outcomes.py`, `scene_grounding.py`, `prompt_builders.py`, then continuity extraction if facts never promote |
| Scene start/end / template roles | `scene_lifecycle_start.py`, `scene_lifecycle_actions.py`, `scene_template.py` |
| **Session** not saving / reload wrong state | `session_manager.py`, `session_lifecycle_save.py`, `session_lifecycle_load.py`, `app_bootstrap.py` |
| **Audit** missing or wrong paths | `audit_logger_paths.py`, `audit_logger.py`, `turn_runner_audit.py` |
| Prompt wording only (after ruling out state) | `prompt_builders.py` |

---

## Entry & bootstrap

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `app.py` | Streamlit entry; wires session state, UI, turn pipeline | Most subsystems via injected helpers | Composition only; stable names for tests |
| `app_bootstrap.py` | Startup: incomplete session recovery, deferred load | `SessionManager`, `session_lifecycle` | Runs once per session |

---

## Facade / re-export layers

These aggregate focused modules; prefer editing **leaf** files unless the facade is the compatibility surface.

| Module | Re-exports / covers |
|--------|---------------------|
| `app_turn_helpers.py` | `app_turn_director`, `app_turn_prompting`, `app_turn_rendering`, `app_turn_selector`, `app_turn_audit` |
| `app_state_helpers.py` | `app_state_audit`, `app_state_characters`, `app_state_continuity`, `app_state_runtime`, `app_state_scene`, `app_state_session` |
| `app_memory_helpers.py` | `app_memory_basics`, `app_memory_summary`, `app_memory_cross_session`, `app_memory_recording`, `app_message_processing` |
| `ui_rendering.py` | `ui_sidebar`, `ui_chat`, `ui_debug` |
| `ui_sidebar.py` | `ui_sidebar_session`, `ui_sidebar_player`, `ui_sidebar_scene_setup`, `ui_sidebar_opening` |
| `scene_lifecycle.py` | `scene_lifecycle_start`, `scene_lifecycle_actions` |
| `session_lifecycle.py` | `session_lifecycle_save`, `session_lifecycle_load` |
| `response_validation.py` | `response_validation_*` (content, presence, drift, parsing, selection) |
| `character_state.py` | `character_state_model`, `character_state_manager` |

---

## Turn pipeline

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `turn_runner.py` | Orchestrates multi-bot turns per user round | `turn_runner_turn`, `turn_runner_updates`, audit, `beat_shift_state` | Main loop entry; progression pressure refresh happens in post-turn update path |
| `turn_runner_turn.py` | Single character turn: Director path, character call, validate, Narrator | `app_turn_*`, `response_validation`, `semantic_validation` | |
| `turn_runner_updates.py` | Post-success continuity/orchestration updates | `ContinuityManager`, helpers | Refreshes derived progression pressure after continuity commits |
| `turn_runner_audit.py` | Audit summary refresh hooks | `audit_logger*` | |
| `progression_pressure.py` | Deterministic scene / issue progression classification, debt, tiers, dominant issue tracking, issue identity continuity notes | continuity state snapshots, orchestration state, Director prompting / selection | Derived pressure memory only; no continuity writes |
| `progression_advisory.py` | Deterministic `stall_score`, `progression_advisory` blob, Director/character prompt snippets | `beat_shift_state` (plateau snapshot helper), scene template profile | Prompt-facing support layer; complements structural progression pressure |
| `anti_regression_advisory.py` | Ping-pong + post-break / low player-agency → short Director ANTI-REGRESSION block | `progression_advisory` (stall read-only), `director_decisions`, `recent_structured_moves`, session `player_character` / `user_name` | Option A trigger: no `high_stall` OR; orchestration cache only |
| `beat_shift_state.py` | Pending beat-shift lifecycle; **`stall_score`** threshold → `progression_stall` | `progression_advisory.compute_stall_score`, orchestration state | Unified plateau signal with short-message trigger |
| `app_turn_director.py` | Director selection logic / call path | `model_client`, `prompt_builders`, `progression_advisory`, `progression_pressure`, `anti_regression_advisory` | Progression pressure payload/prefix plus actor-selection override under elevated pressure |
| `app_turn_selector.py` | Turn selection parsing / reconciliation | `response_validation_selection` | |
| `app_turn_prompting.py` | Character / Director / Narrator prompt assembly glue | `prompt_builders`, state, `progression_advisory`, `progression_pressure` | Optional pressure-aware suffixes layered with advisory/beat-shift hints |
| `app_turn_rendering.py` | Narrator render path | `model_client` | Preserve dialogue verbatim |
| `app_turn_audit.py` | Turn-level audit helpers | `audit_logger*` | |

---

## Continuity engine

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `continuity_manager.py` | Promote moves to events; issues; scene; interpretations; knowledge | `continuity_*_helpers`, `continuity_state` | Authoritative narrative state |
| `continuity_state.py` | Dataclasses: issues, events, interpretations, anchors, snapshots | — | Serialization shapes for sessions |
| `continuity_issue_helpers.py` | Issue lifecycle, matching, summaries | `continuity_consequence_classifier` | |
| `continuity_knowledge_helpers.py` | Knowledge propagation, boundaries, `told`/inference | events, interpretations | |
| `continuity_resolved_outcomes.py` | Facade: structured ingest helpers + delegates apply path to `resolved_outcome_engine` | `resolved_outcome_registry`, `resolved_outcome_engine`, `continuity_manager` | V1: `lodging.sleep_surface`, `communication.housing_call` |
| `resolved_outcome_registry.py` | `ASPECT_REGISTRY`, parse/validate, `slot_key` encoding, per-aspect promotion policy (read-only evaluate), local revocation | `continuity_state`, `resolved_outcome_engine` | New aspects = new rows; no inference |
| `resolved_outcome_engine.py` | Deterministic pipeline: ingest → slot → `no_op_existing_value` → revoke → promote → persist | `continuity_state`, `resolved_outcome_registry` | Core stays aspect-agnostic; policies live in registry |
| `continuity_scene_helpers.py` | Scene snapshots, orchestration context for prompts | scene state | |
| `continuity_summary_helpers.py` | Summary blocks, retrieval ranking support | issues, events | |
| `continuity_consequence_classifier.py` | Consequence / category signals for issues | text signals | |
| `scene_grounding.py` | Derive **read-only** **scene facts** from continuity `PublicEvent.grounding_markers` and active resolved outcomes; format Director/character prompt blocks; cap/prune | `continuity_manager`, `turn_runner_updates`, `prompt_builders`, `app_turn_director`, `app_turn_prompting` | **No** continuity or `CharacterState` writes; PRD §5.8; spec: `autogen_rp/docs/scene-grounding-layer.md` |

---

## Validation & semantics

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `response_validation_parsing.py` | Parse character moves, Director JSON | — | |
| `response_validation_content.py` | Self-narration / structural checks | parsed moves | |
| `response_validation_presence.py` | must_remain / exit contradictions | scene, templates | |
| `response_validation_drift.py` | Voice / profile drift vs anchors | `character_state` | |
| `response_validation_selection.py` | Turn-selection validation | Director output | |
| `semantic_validation.py` | LLM-assisted semantic checks / overrides | async model calls | Use sparingly; bounded |

---

## Scene & session lifecycle

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `scene_lifecycle_start.py` | Start scene, team setup | `scene_template`, `scene_opener` | |
| `scene_lifecycle_actions.py` | End scene, skip, close, recreate team | `session_lifecycle`, continuity | |
| `scene_template.py` | Load/validate templates, role assignments | `data/scene_templates` | Optional `progression_profile` on JSON templates |
| `scene_opener.py` | Opening text / initial message resolution | `autogen_characters` | |
| `scene_exit_detection.py` | Hard departure signals for continuity | text / moves | |
| `session_lifecycle_save.py` | Persist session + continuity + audit ids | `SessionManager` | |
| `session_lifecycle_load.py` | Restore session into Streamlit state | `SessionManager` | |
| `session_manager.py` | Save/load JSON sessions, `_session_index.json` | `data/sessions` | |

---

## Characters & orchestration

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `character_loader.py` | Load JSON cards, build agents | `data/autogen_characters`, `model_client` | Current “ingestion” is files |
| `character_state_model.py` | Per-character state schema | cards | Identity anchors |
| `character_state_manager.py` | Update goals, emotions, relationships | continuity, turns | |
| `orchestration_helpers.py` | Spotlight, continuation override, sync from continuity | `st.session_state` | Final speaker ordering support |
| `prompt_builders.py` | Structured prompt text for Director/characters/Narrator | continuity, templates | Future: consume packets |

---

## Model & audit

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `model_client.py` | DeepSeek / agent construction | AutoGen stack | Env: API keys |
| `audit_logger.py` | Audit session/round/turn lifecycle | `audit_logger_paths`, writers | |
| `audit_logger_paths.py` | Paths: `rp_app/data/rp_audits` | — | |
| `audit_logger_writers.py` | Write JSON artifacts | — | |
| `audit_logger_serialization.py` | Serialize payloads | — | |
| `audit_logger_summary_rounds.py` | Round-level summary data | — | |
| `audit_logger_summary_report.py` | `_audit_summary` aggregation | — | |
| `audit_logger_summary_output.py` | Output formatting helpers | — | |
| `audit_progression_analysis.py` | Audit-side verification of progression classification, debt, reset validity, plateau pressure, targeting, and identity continuity | `_narrative.json` structured turn artifacts, observed progression state | Independent of runtime classifier |
| `summary_audit_helpers.py` | Prompt/audit bridges for summaries | continuity | |

---

## UI (Streamlit)

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `ui_chat.py` | Chat history, input | turn_runner | |
| `ui_sidebar_session.py` | Session list, load/save | `SessionManager` | |
| `ui_sidebar_player.py` | Player character selection | cards | |
| `ui_sidebar_scene_setup.py` | Cast, template, roles, audit toggle | `scene_template` | |
| `ui_sidebar_opening.py` | Opener mode UI | `scene_opener` | |
| `ui_debug.py` | Debug panels | state | |

---

## Related docs

- [README.md](./README.md) — project navigation
- [autogen_rp/python/rp_app/README.md](./autogen_rp/python/rp_app/README.md) — operator rules, formats
- [autogen_rp/python/rp_app/ARCHITECTURE.md](./autogen_rp/python/rp_app/ARCHITECTURE.md) — Director/Narrator/continuity deep dive
- [autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md](./autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md) — audit file meanings
- [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md) — data directories
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — future packet seam
- [autogen_rp/docs/scene-grounding-layer.md](./autogen_rp/docs/scene-grounding-layer.md) — Scene Grounding MVP (facts contract, lifecycle)

*A short pointer file remains at `autogen_rp/python/rp_app/MODULE_INDEX.md` so existing links into `rp_app/` still resolve.*
