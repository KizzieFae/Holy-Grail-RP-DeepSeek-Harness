# RP app module index

**Location:** Every module named below lives in **`autogen_rp/python/rp_app/`** (unless a path is written out explicitly).

Quick map for **where to change what**. Architecture rules: [autogen_rp/python/rp_app/ARCHITECTURE.md](./autogen_rp/python/rp_app/ARCHITECTURE.md), [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md), and [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md). **Canonical knowledge:** [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) — offline compile (`schema_version` 2 default, 3 additive canonical fields); **runtime** still reads only legacy projection fields on chunks; continuity authoritative.

**Constraints (recurring):** Keep `app.py` thin. Do not fix continuity/orchestration bugs by bloating Director prompts. Preserve `must_remain` as **structural presence**, not “must speak every turn.”

For **diagnosis order** and layer rules, see [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

**Scenario Validation Framework** is a **core system** alongside the turn pipeline and continuity stack—not an optional add-on. It is how we lock behavioral changes: scenario manifests under `rp_app/data/progression_simulation_scenarios/`, `scripts/run_scene_simulation_llm.py`, and the canonical doc [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md).

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
| **Episodic prompt sections** / wrong “memories” block in character prompt | `memory_layer/retrieval.py`, `app_turn_prompting.py` (`build_character_state_context_for_prompt`); identity text: `character_state_model.py` (`to_prompt_identity_context`) |
| **Authored retrieval** / **bounded episodic** / `RetrievedContextBundle` / non-authoritative prompt block | `retrieved_context_select.py` (authored select + **merge** with episodic + log), `episodic_memory_compile.py`, `episodic_memory_cache.py`, `episodic_memory_select.py`, `episodic_memory_inputs.py`, `episodic_memory_prompt.py` (flag), `app_turn_prompting.py` (single call site; env **`RP_EPISODIC_MEMORY`**), `runtime_packets.py` (`RetrievedItem`, bundle, `format_retrieved_context_for_prompt`), `prompt_builders.py` (`retrieved_context_section`); env `RP_RETRIEVED_CONTEXT_INDEX` |
| **Plateau** / stalled high-tension verbal loop (advisory + beat-shift) | `progression_advisory.py`, `beat_shift_state.py`, `progression_enforcement.py`, `app_turn_director.py`, `app_turn_prompting.py`, `prompt_builders.py`, `turn_runner.py`, `turn_runner_turn.py` |
| Stale issues / bad event memory / knowledge boundaries | `continuity_manager.py`, `continuity_issue_helpers.py`, `continuity_knowledge_helpers.py`, `perception_audibility.py` |
| **Whisper / private line** known to wrong character; per-character prompt mismatch | `perception_audibility.py`, then `app_turn_prompting.py`, `continuity_manager.py`, `continuity_knowledge_helpers.py`, `app_turn_director.py` |
| **Settled facts** repeated / logistics reset in dialogue (after continuity looks correct) | `continuity_resolved_outcomes.py`, `scene_grounding.py`, `prompt_builders.py`, then continuity extraction if facts never promote |
| **Character contradicts** promoted binding facts (sleeping surface, location entry, etc.) after grounding is correct | `scene_grounding.py` (`format_character_binding_constraints_section`, `_BINDING_FACT_KEYS`), `app_turn_prompting.py` (`scene_binding_constraints_section`), `prompt_builders.py` (placement before **OUTPUT RULES**) |
| **Unsupported specifics** as clinical / institutional / “chart” truth | `prompt_builders.py` (`_EVIDENCE_AUTHORITY_DISCIPLINE_BLOCK`); rule out perception/grounding bugs first (`perception_audibility.py`, `scene_grounding.py`) |
| Scene start/end / template roles | `scene_lifecycle_start.py`, `scene_lifecycle_actions.py`, `scene_template.py` |
| **Session** not saving / reload wrong state | `session_manager.py`, `session_lifecycle_save.py`, `session_lifecycle_load.py`, `app_bootstrap.py` |
| **Audit** missing or wrong paths | `audit_logger_paths.py`, `audit_logger.py`, `turn_runner_audit.py` |
| **Scenario validation** (fixed manifests, headless LLM runs, `--audit`, metrics) | [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md); `autogen_rp/python/scripts/run_scene_simulation_llm.py`; `progression_simulation_scenarios.py`; `rp_app/data/progression_simulation_scenarios/*.json` |
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
| `memory_layer/` | `facade` (writes), `writes`, `storage`, `retrieval` (episodic prompt sections); see `autogen_rp/docs/architecture.md` |
| `character_state.py` | `character_state_model`, `character_state_manager` |

---

## Turn pipeline

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `turn_runner.py` | Orchestrates multi-bot turns per user round | `turn_runner_turn`, `turn_runner_updates`, audit, `beat_shift_state` | Passes active issues + recent moves into beat-shift; main loop entry |
| `turn_runner_turn.py` | Single character turn: Director path, character call, validate, Narrator | `app_turn_*`, `response_validation`, `semantic_validation`, `perception_audibility` | Normalizes move audibility after parse; chat append includes `actor` id |
| `turn_runner_updates.py` | Post-success continuity/orchestration updates | `ContinuityManager`, helpers | |
| `turn_runner_audit.py` | Audit summary refresh hooks | `audit_logger*` | |
| `progression_advisory.py` | Deterministic `stall_score`, `progression_advisory` blob, Director/character prompt snippets | `beat_shift_state` (plateau snapshot helper), scene template profile | Advisory only; no continuity writes |
| `progression_enforcement.py` | v1 **structural delta** contract (Q1–Q4) after `process_turn`; gate = beat-shift **or** high progression pressure | `turn_runner_turn`, `beat_shift_state`, `progression_advisory` | No continuity writes; snapshot/restore on retry |
| `anti_regression_advisory.py` | Ping-pong + post-break / low player-agency → short Director ANTI-REGRESSION block | `progression_advisory` (stall read-only), `director_decisions`, `recent_structured_moves`, session `player_character` / `user_name` | Option A trigger: no `high_stall` OR; orchestration cache only |
| `beat_shift_state.py` | Pending beat-shift lifecycle; **`stall_score`** threshold → `progression_stall` | `progression_advisory.compute_stall_score`, orchestration state | Unified plateau signal with short-message trigger |
| `app_turn_director.py` | Director selection logic / call path | `model_client`, `prompt_builders`, `progression_advisory`, `anti_regression_advisory` | Optional progression + anti-regression Director prefixes |
| `app_turn_selector.py` | Turn selection parsing / reconciliation | `response_validation_selection` | |
| `app_turn_prompting.py` | Character / Director / Narrator prompt assembly glue | `prompt_builders`, state, `progression_advisory`, `perception_audibility`, `offstage_prompt_filter`, `memory_layer.retrieval`, `prompt_derivations`, `retrieved_context_select`, `episodic_memory_*` (cache/inputs/select when **`RP_EPISODIC_MEMORY`**), `runtime_packets` | **Character path (Phase 0.5):** after retrieval/grounding, builds **`CharacterPromptInputAssembly`** once; **`live_bundle_from_character_prompt_assembly`** → kwargs for **`build_character_turn_prompt`**; **`RP_PACKET_SHADOW_COMPARE`:** packets from **`runtime_packets_from_character_prompt_assembly`**, reconstruct + compare (debug/validation; stderr only). **Phase 2–3.2:** **only** call site for retrieval — authored or merged episodic |
| `prompt_derivations.py` | Shared **relationship-name ordering** (`select_relationship_prompt_names`) and **priority ladder** (`build_priority_ladder`) for character prompts | `app_turn_prompting`, `runtime_packets` | **Phase 0.5:** extracted so `runtime_packets` can reconstruct prompt-input bundles without importing `app_turn_prompting`; **live path uses these same functions every turn** (not env-gated) |
| `runtime_packets.py` | **`CharacterPromptInputAssembly`**, `live_bundle_from_character_prompt_assembly`, `runtime_packets_from_character_prompt_assembly`; read-only types (`RuntimeScenePacket`, `RuntimeCharacterPacket`, `RetrievedContextBundle` + `RetrievedItem`); `format_retrieved_context_for_prompt`; split/merge scene state; `reconstruct_character_prompt_input_bundle`; `compare_character_prompt_bundles` | `app_turn_prompting` (character seam), `retrieved_context_select` (types), `prompt_derivations` / `prompt_builders` (reconstruction) | **Phase 0.5:** single assembly feeds both live bundle and packet builders (**character** `build_character_turn_prompt` boundary only). **Phase 2–3.2:** bundle may carry authored + episodic items; **no** selector here. **Shadow:** env-gated; mismatch logs **`rp_app.packet_shadow`** (stderr — not audit-persisted yet) |
| `retrieved_context_select.py` | **Phase 2–3.2** deterministic **authored JSON index** load + `select_retrieved_context_bundle`; **Phase 3.2:** `merge_retrieved_context_with_episodic`, `select_authored_retrieved_items_pre_global_cap`, `episodic_compiled_to_retrieved_item`; `lore` lane; per-kind subcaps; merged global cap (authored wins ties); dedup; `log_retrieval_if_active`; env path helper | `app_turn_prompting` (sole runtime caller), `runtime_packets` (types import), `episodic_memory_compile` (types) | **Not** vector/graph/transcript-wide memory; episodic is **continuity-row compile** only; non-authoritative |
| `episodic_memory_compile.py` | **Phase 3.2** pure candidate pool from `PublicEvent` / `CharacterInterpretation` / `IssueState` / `CanonAnchor`; template summaries; no LLM; no continuity writes | `episodic_memory_cache`, `retrieved_context_select` (mapping to `RetrievedItem`) | Visibility strict; skip events with `canon_impact` |
| `episodic_memory_cache.py` | Snapshot-keyed `session_state` cache for candidate pool; `clear_episodic_pool_cache` | `app_turn_prompting` | Read-only w.r.t. continuity |
| `episodic_memory_select.py` | Per-character filter + episodic-only subcaps from shared pool | `app_turn_prompting` | |
| `episodic_memory_inputs.py` | Read-only flatten/sort of continuity sequences for compile/cache | `app_turn_prompting` | |
| `episodic_memory_prompt.py` | `is_episodic_memory_enabled()` → `RP_EPISODIC_MEMORY` | `app_turn_prompting` | |
| `authored_index_compile.py` | Offline `compile_authored_index`: manifest → **`schema_version` 2** (legacy chunks only, default) or **3** (canonical fields + same legacy projection); strict adapter coverage; `lore` lane; OOC blocklist | `canonical_compile_adapters`, `scripts/compile_authored_retrieval_index.py`, tests (`test_authored_index_compile`, fixtures `compile_sample`, `compile_realistic`) | **Pre-packaging** artifact; does not change retrieval selector/merge at runtime |
| `canonical_compile_adapters.py` | Adapter registry: manifest entry type + JSON key path → `knowledge_type`, `authority_class`, `visibility`, **decomposition strategy**; unmapped → `lore_reference` / `reference_only` (**strict fallback**) | `authored_index_compile` | See implementation snapshot in [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) |
| `scripts/compile_authored_retrieval_index.py` | CLI: `--manifest` / `--output`, **`--schema-version 2`** (default) or **`3`** | `authored_index_compile` | Example manifest: `data/retrieval/authored_manifest.example.json`; output → `RP_RETRIEVED_CONTEXT_INDEX` |
| `app_turn_rendering.py` | Narrator render path | `model_client` | Preserve dialogue verbatim |
| `app_turn_audit.py` | Turn-level audit helpers | `audit_logger*` | |

---

## Continuity engine

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `continuity_manager.py` | Promote moves to events; issues; scene; interpretations; knowledge | `continuity_*_helpers`, `continuity_state`, `perception_audibility` | Authoritative narrative state; `PublicEvent` knowability via `known_by`/`observed_by`; safe summaries for non-public dialogue |
| `continuity_state.py` | Dataclasses: issues, events, interpretations, anchors, snapshots | — | `PublicEvent.knowledge_level_for` gates on `known_by` first |
| `continuity_issue_helpers.py` | Issue lifecycle, matching, summaries | `continuity_consequence_classifier` | |
| `continuity_knowledge_helpers.py` | Knowledge propagation, boundaries, `told`/inference | events, interpretations, `perception_audibility` | Dialogue-mediated propagation and interpretation quotes respect `viewer_may_perceive_dialogue` |
| `continuity_resolved_outcomes.py` | Facade: structured ingest helpers + delegates apply path to `resolved_outcome_engine` | `resolved_outcome_registry`, `resolved_outcome_engine`, `continuity_manager` | Current aspects: `lodging.sleep_surface`, `communication.housing_call`, `medical.suppressant_formulation`, `access.location_entry` |
| `resolved_outcome_registry.py` | `ASPECT_REGISTRY`, parse/validate, `slot_key` encoding, per-aspect promotion policy (read-only evaluate), local revocation | `continuity_state`, `resolved_outcome_engine` | New aspects = new rows; no inference |
| `resolved_outcome_engine.py` | Deterministic pipeline: ingest → slot → `no_op_existing_value` → revoke → promote → persist | `continuity_state`, `resolved_outcome_registry` | Core stays aspect-agnostic; policies live in registry |
| `continuity_scene_helpers.py` | Scene snapshots, orchestration context for prompts | scene state | |
| `continuity_summary_helpers.py` | Summary blocks, retrieval ranking support | issues, events | `key_events` derive from `event.summary` (already audibility-safe at promotion) |
| `continuity_consequence_classifier.py` | Consequence / category signals for issues | text signals | |
| `scene_grounding.py` | Derive **read-only** **scene facts** from continuity `PublicEvent.grounding_markers` and active resolved outcomes; format Director/character **SETTLED SCENE FACTS**; **character BINDING CONSTRAINTS** subset via `format_character_binding_constraints_section`; cap/prune | `continuity_manager`, `turn_runner_updates`, `prompt_builders`, `app_turn_director`, `app_turn_prompting` | **No** continuity or `CharacterState` writes; PRD §5.8; spec: `autogen_rp/docs/scene-grounding-layer.md` |
| `perception_audibility.py` | Deterministic **`audibility`** / **`audience`**; per-recipient transcript + structured-move filtering; **`public_safe_event_summary`**; Director orchestration redaction | `app_turn_prompting`, `app_turn_director`, `continuity_manager`, `continuity_knowledge_helpers`, `turn_runner_turn`, `orchestration_helpers`, `prompt_builders` | **Single source of truth** for perception boundaries; structured `move` only (no narrator prose parsing) |
| `offstage_prompt_filter.py` | Traveler + self-only transcript/moves for offstage characters | `app_turn_prompting` | Applied after perception filtering |

---

## Validation & semantics

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `response_validation_parsing.py` | Parse character moves, Director JSON | — | Optional `audibility`, `audience` on character moves |
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
| `orchestration_helpers.py` | Spotlight, continuation override, sync from continuity | `st.session_state` | Persists `audibility`/`audience` on structured move entries; narrator scene context uses perception-filtered transcript |
| `prompt_builders.py` | Structured prompt text for Director/characters/Narrator | continuity, templates | Labels perception-filtered transcript/structured sections; **character** template: optional `scene_binding_constraints_section`, static **EVIDENCE & AUTHORITY DISCIPLINE** block, then **OUTPUT RULES**; inputs assembled in `app_turn_prompting` (Phase 0.5 shadow parity in `runtime_packets`) |

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

- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) — behavioral validation layer (scenarios, headless runner, audits, structured metrics, baseline comparison)
- [README.md](./README.md) — project navigation
- [autogen_rp/python/rp_app/README.md](./autogen_rp/python/rp_app/README.md) — operator rules, formats
- [autogen_rp/python/rp_app/ARCHITECTURE.md](./autogen_rp/python/rp_app/ARCHITECTURE.md) — Director/Narrator/continuity deep dive
- [autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md](./autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md) — audit file meanings
- [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md) — data directories
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — packet contracts; Phase 0.5 **character-path** seam: `CharacterPromptInputAssembly`, `runtime_packets.py`, shadow compare (`RP_PACKET_SHADOW_COMPARE`)
- [autogen_rp/docs/scene-grounding-layer.md](./autogen_rp/docs/scene-grounding-layer.md) — Scene Grounding MVP (facts contract, lifecycle)

*A short pointer file remains at `autogen_rp/python/rp_app/MODULE_INDEX.md` so existing links into `rp_app/` still resolve.*
