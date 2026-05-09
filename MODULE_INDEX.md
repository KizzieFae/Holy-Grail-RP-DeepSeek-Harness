# RP app module index

**Location:** Every module named below lives in **`autogen_rp/python/rp_app/`** (unless a path is written out explicitly).

Quick map for **where to change what**. Architecture rules: [autogen_rp/python/rp_app/ARCHITECTURE.md](./autogen_rp/python/rp_app/ARCHITECTURE.md), [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md), and [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md). **Authored files (Character / Template / Bootstrap / Opener):** [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md). **Canonical compiled knowledge (retrieval envelope):** [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) — offline compile (`schema_version` 2 default, 3 additive canonical fields); **runtime** still reads only legacy projection fields on chunks; continuity authoritative.

**Constraints (recurring):** Keep `app.py` thin. Do not fix continuity/orchestration bugs by bloating Director prompts. Preserve `must_remain` as **structural presence**, not “must speak every turn.”

For **diagnosis order** and layer rules, see [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

**Scenario Validation Framework** is a **core system** alongside the turn pipeline and continuity stack—not an optional add-on. It is how we lock behavioral changes: scenario manifests under `rp_app/data/progression_simulation_scenarios/`, `scripts/run_scene_simulation_llm.py`, and the canonical doc [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Symptom → first file to open

Use this for a fast landing spot; the tables below add detail. Full workflow: [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

| Symptom or task | Start here (under `autogen_rp/python/rp_app/`) |
|-----------------|-----------------------------------------------|
| Wrong actor / rotation / “ignored” address | `orchestration_helpers.py` (**façade**; **#164** leaf modules listed under **Characters & orchestration**), then `app_turn_director.py`, `response_validation_selection.py`, `semantic_validation.py` |
| Director JSON parse / invalid `next_actor` | `response_validation_parsing.py`, `response_validation_selection.py`, `app_turn_director.py` |
| Character speaks for others / bad JSON shape | `response_validation_content.py`, `response_validation_parsing.py` |
| **Duplicate** dialogue or repeated line | `response_validation_content.py` (`is_duplicate_dialogue`), `turn_runner_character_attempt.py` (retry path; façade `turn_runner_turn.py`) |
| **Presence** / exit / `must_remain` | `response_validation_presence.py`, `scene_template.py`, `semantic_validation.py` (override paths) |
| **Drift** / voice / anchors | `response_validation_drift.py`, `character_state_model.py`, cards in `autogen_rp/python/data/autogen_characters/` |
| **Episodic prompt sections** / wrong “memories” block in character prompt | `memory_layer/retrieval.py`, `prompt_state_context.py` (`build_state_context_for_character_prompt`); façade: `app_turn_prompting.py`; identity text: `character_state_model.py` (`to_prompt_identity_context`) |
| **Authored retrieval** / **bounded episodic** / `RetrievedContextBundle` / non-authoritative prompt block | `retrieved_context_select.py` (authored select + **merge** with episodic + log), `prompt_retrieval_assembly.py` (**sole** runtime bundle build; env index via `get_index_path_from_env`), `episodic_memory_compile.py`, `episodic_memory_cache.py`, `episodic_memory_select.py`, `episodic_memory_inputs.py`, `episodic_memory_prompt.py` (flag), `app_turn_prompting.py` (composition), `runtime_packets.py` (`RetrievedItem`, bundle, `format_retrieved_context_for_prompt`), `prompt_builders.py` (`retrieved_context_section`); env **`RP_RETRIEVED_CONTEXT_INDEX`** (sole ON/OFF switch). **Phase 4A observability:** `retrieval_audit_helpers.py` (`apply_retrieval_session_to_audit_summary`), `app_state_audit.py` (Streamlit `refresh_audit_summary_report`), `turn_runner_audit.py` (`retrieval_summary`), `headless_scene_simulation.py` (strict verify headless-only), `tests/test_retrieval_workflow_audit.py`. **Standard eval + pilot artifact map:** [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) (*Authored retrieval*), `autogen_rp/python/data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md`, manifest `operational_pilot.json`, matrix `scripts/run_operational_pilot_eval_matrix.py`. **Phase 1 retrieval-lock tests:** `tests/test_phase1_retrieval_seam.py`, `tests/test_retrieved_context_merge.py`, `tests/test_prompt_builders.py`; headless template id: `tests/test_prepare_headless_scene_template_id.py` |
| **Plateau** / stalled high-tension verbal loop (advisory + beat-shift) | `progression_advisory.py`, `beat_shift_state.py`, `progression_enforcement.py`, `continuity_consequence_classifier.py`, `app_turn_director.py`, `app_turn_prompting.py`, `prompt_builders.py`, `turn_runner.py`, `turn_runner_character_attempt.py`, `turn_runner_turn.py` |
| Stale issues / bad event memory / knowledge boundaries | `continuity_manager.py`, `continuity_issue_helpers.py`, `continuity_knowledge_helpers.py`, `perception_audibility.py` |
| **Whisper / private line** known to wrong character; per-character prompt mismatch | `perception_audibility.py`, then `app_turn_prompting.py`, `continuity_manager.py`, `continuity_knowledge_helpers.py`, `app_turn_director.py` |
| **Settled facts** repeated / logistics reset in dialogue (after continuity looks correct) | `continuity_resolved_outcomes.py`, `scene_grounding.py`, `prompt_builders.py`, then continuity extraction if facts never promote |
| **Transactional** commitments (order placed, delivery pending, void/replace) — in-flight **scene** state | `resolved_outcome_registry.py` / `resolved_outcome_engine.py` (aspect `transaction.scene_commitment`), `continuity_resolved_outcomes.py`, `scene_grounding.py` — structured `move["scene_state_updates"]["transactional_commitment"]` (GitHub #127) |
| **Character contradicts** promoted binding facts (sleeping surface, location entry, etc.) after grounding is correct | `scene_grounding.py` (`format_character_binding_constraints_section`, `_BINDING_FACT_KEYS`), `prompt_grounding_assembly.py` / `app_turn_prompting.py` (`scene_binding_constraints_section`), `prompt_builders.py` (placement before **OUTPUT RULES**) |
| **Unsupported specifics** as clinical / institutional / “chart” truth | `prompt_builders.py` (`_EVIDENCE_AUTHORITY_DISCIPLINE_BLOCK`); rule out perception/grounding bugs first (`perception_audibility.py`, `scene_grounding.py`) |
| Scene start/end / template roles | **`bootstrap_composition.py`** (**façade**, Issue #94 `BootstrapInterpretation`; **#165** leaves: `bootstrap_interpretation.py`, `bootstrap_streamlit_opening_modes.py`, `bootstrap_context_inputs.py`, `bootstrap_strategy_shared.py`, `bootstrap_strategy_streamlit.py`, `bootstrap_compose_streamlit.py`, `bootstrap_compose_headless.py`), `scene_start_bootstrap.py`, `app_state_continuity.py` (`restore_or_initialize_continuity_manager`), `scene_lifecycle_start.py`, `scene_lifecycle_actions.py`, `scene_template.py` |
| **Session** not saving / reload wrong state | `session_manager.py`, `session_lifecycle_save.py`, `session_lifecycle_load.py`, `app_bootstrap.py` |
| **Audit** missing or wrong paths | `audit_logger_paths.py`, `audit_logger.py`, `turn_runner_audit.py`; **#79 continuity observability:** `audit_ctar.py`, `audit_runtime_mirrors.py`, `continuity_audit_origin.py`, `continuity_observability_summary.py` |
| **Scenario validation** (fixed manifests, headless LLM runs, `--audit`, metrics) | [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) (2026-04-07 post–#24 wave); `autogen_rp/python/scripts/run_scene_simulation_llm.py` (**`--scene-template-id`**, **`--scene-template-roles`**, **`--retrieved-context-index`** for authored retrieval OFF/ON; optional **`--fact-spec`** / **`--fact-track-out`** for offline fact-track companion — GitHub **#62**); **`headless_scene_simulation.py`** (facade: `prepare_headless_session`, `run_headless_llm_scene`; implementation split Issue **#156**: `headless_session_prepare.py`, `headless_turn_runner_wire.py`, `headless_simulation_runner.py`, `headless_simulation_reporting.py`) — `prepare_headless_session` **`scene_template_id`**, post-run **`apply_retrieval_session_to_audit_summary`** + strict verify headless-only in runner; `progression_simulation_scenarios.py` (**`startup_trigger_mode`**, **`effective_round1_trigger_text_headless`**); `rp_app/data/progression_simulation_scenarios/*.json`; example metrics: `autogen_rp/python/validation_runs/plan_execution/*.json` |
| **OTHER PRESENT CHARACTERS** lists the acting character, or **CAST ROLE MAP** repeats the same person under id vs display | `prompt_builders.py` (`prompt_identity_same`, `build_cast_and_scene_role_participants`), `app_turn_prompting.py`, `runtime_packets.py` (`reconstruct_character_prompt_input_bundle` — pass the same **`get_character_display_name_fn`** as live assembly) |
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
| `ui_rendering.py` | `ui_sidebar`, `ui_chat` |
| `ui_sidebar.py` | `ui_sidebar_session`, `ui_sidebar_player`, `ui_sidebar_scene_setup`, `ui_sidebar_opening` |
| `scene_lifecycle.py` | `scene_lifecycle_start`, `scene_lifecycle_actions` |
| `session_lifecycle.py` | `session_lifecycle_save`, `session_lifecycle_load` |
| `response_validation.py` | `response_validation_*` (content, presence, drift, parsing, selection) |
| `memory_layer/` | `facade` (writes), `writes`, `storage`, `retrieval` (episodic prompt sections); see `autogen_rp/docs/architecture.md` |
| `character_state.py` | `character_state_model`, `character_state_manager` |
| `orchestration_helpers.py` | `orchestration_state_init`, `orchestration_continuity_mirror`, `orchestration_continuation`, `orchestration_spotlight`, `orchestration_progression`, `orchestration_scene_context`, `orchestration_turn_append` (**#164**; see Characters & orchestration) |
| `bootstrap_composition.py` | `bootstrap_interpretation`, `bootstrap_streamlit_opening_modes`, `bootstrap_context_inputs`, `bootstrap_strategy_shared`, `bootstrap_strategy_streamlit`, `bootstrap_compose_streamlit`, `bootstrap_compose_headless` (**#165**; symptom row → scene lifecycle) |
| `runtime_packets.py` | `runtime_packet_types`, `runtime_packet_formatting`, `runtime_packet_scene_split`, `runtime_packet_build`, `runtime_packet_prompt_bundle`, `runtime_packet_reconstruct`, `runtime_packet_parity` (**#166**; see Turn pipeline) |
| `retrieved_context_select.py` | `authored_retrieval_index`, `retrieved_selection_authored`, `retrieved_episodic_merge`, `retrieved_context_ops` (**#166**; see Turn pipeline) |

---

## Turn pipeline

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `turn_runner.py` | Orchestrates multi-bot turns per user round | `turn_runner_turn`, `turn_runner_updates`, audit, `beat_shift_state` | Passes active issues + recent moves into beat-shift; main loop entry |
| `turn_runner_turn.py` | **Façade**: `execute_character_turn` phase sequencing; re-exports **`DEFAULT_MAX_CHARACTER_ATTEMPTS`** / **`_CHARACTER_MOVE_PARSE_JSON_DISCIPLINE_NOTE`** / **`_narrate_move_for_character_turn`** for tests and docs | `turn_runner_character_attempt`, `turn_runner_character_render` | Public API stable; implementation split per **#150** |
| `turn_runner_character_attempt.py` | Single-turn **attempt** slice: retry garnish, agent call, parse, normalize, validate, structured retries, **`process_turn`** + progression gate, character audit payloads / `log_character_turn_audit` | Injected `validate_bot_response_fn`, `progression_enforcement`, continuity, `perception_audibility` (normalize only), `response_validation_*` helpers | v2 move object identity preserved where applicable |
| `turn_runner_character_render.py` | Single-turn **render** slice: `_narrate_move_for_character_turn`, narrator call, semantic review, fallback render, narrator audits, `chat_history` append, render/chat rollback | `app_turn_rendering` (injected), narrator audit builders, `ContinuityManager` rollback snapshots | Chat append still uses pre-fallback **`rendered`** where historical behavior did |
| `turn_runner_updates.py` | Post-success continuity/orchestration updates | `ContinuityManager`, helpers | |
| `turn_runner_audit.py` | Character/narrator audit payloads, CTAR / scene mirror / excursion digest / **`continuity_audit_origin`** merge | `audit_ctar`, `audit_runtime_mirrors`, `continuity_audit_origin`, `audit_logger*` | |
| `progression_advisory.py` | Deterministic `stall_score`, `progression_advisory` blob, Director/character prompt snippets; `load_progression_profile_for_template_id` reads `{template_id}_progression.json` or defaults (**#119**) | `beat_shift_state` (plateau snapshot helper) | Advisory only; no continuity writes |
| `progression_enforcement.py` | v1 **structural delta** contract (Q1–Q4) after `process_turn`; gate = beat-shift **or** high progression pressure | `turn_runner_character_attempt`, `beat_shift_state`, `progression_advisory` | No continuity writes; snapshot/restore on retry; reads continuity **`consequences`** only—thin/empty tags are fixed in **`continuity_consequence_classifier.py`**, not by changing Q1–Q4 |
| `anti_regression_advisory.py` | Ping-pong + post-break / low player-agency → short Director ANTI-REGRESSION block | `progression_advisory` (stall read-only), `director_decisions`, `recent_structured_moves`, session `player_character` / `user_name` | Option A trigger: no `high_stall` OR; orchestration cache only |
| `beat_shift_state.py` | Pending beat-shift lifecycle; **`stall_score`** threshold → `progression_stall` | `progression_advisory.compute_stall_score`, orchestration state | Unified plateau signal with short-message trigger |
| `app_turn_director.py` | Director turn **facade** — early routes, Director LLM call, parse/fallback, delegates payload + post-pick pipeline | `director_prompt_payload`, `director_selection_postprocess`, `prompt_builders`, `model_client`; advisory: `progression_advisory`, `anti_regression_advisory`, `beat_shift_state`, `director_low_pressure_guidance` | **Issue #151:** `director_prompt_payload.py` assembles prompts; `director_selection_postprocess.py` runs validation→semantic→reconciliation→align→override→fairness |
| `director_prompt_payload.py` | Director **`director_payload`** assembly: issue split, obligation / action-responsibility hints, arch-quality prefix stripping, scene grounding injection, advisory prefix fields | Continuity projection, orchestration/state snapshots, scene grounding helper | Imported by **`app_turn_director`** |
| `director_selection_postprocess.py` | Post-parse orchestration pipeline: deterministic turn validation, semantic assessment, reconcile, addressee alignment, progression override, fairness, attribution + Director audit logging | **`semantic_validation`**, **`turn_selection_preference`**, **`orchestration_helpers`** participation/override helpers; injected validators | Imported by **`app_turn_director`** |
| `app_turn_selector.py` | Turn selection parsing / reconciliation | `response_validation_selection` | |
| `app_turn_prompting.py` | Character prompt **façade** (continuity/cast/perception/offstage orchestration); delegates `state_context`, grounding sections, retrieval bundle, and `CharacterPromptInputAssembly` + live kwargs | `prompt_builders`, `prompt_derivations`, `prompt_state_context`, `prompt_grounding_assembly`, `prompt_retrieval_assembly`, `prompt_input_assembly`, `progression_advisory`, `perception_audibility`, `offstage_prompt_filter`, `continuity_prompt_projection_v77` | **Stable API:** `build_character_turn_prompt`, `build_recent_scene_context`. **Phase 0.5:** single assembly + live bundle via **`prompt_input_assembly`**; shadow compare observational only |
| `prompt_state_context.py` | `state_context` string for character prompts | `memory_layer.retrieval` | Only callsite for `build_character_state_context_for_prompt` on this path |
| `prompt_grounding_assembly.py` | Scene grounding + binding constraint sections from session `scene_grounding` | `scene_grounding` | Read-only projection |
| `prompt_retrieval_assembly.py` | Load authored index (env), select/merge retrieved bundle, episodic branch, `log_retrieval_if_active` | `retrieved_context_select`, `episodic_memory_*` | **Sole** runtime invoker of `select_retrieved_context_bundle` / `merge_retrieved_context_with_episodic` for character turns |
| `prompt_input_assembly.py` | Constructs **`CharacterPromptInputAssembly`**, `live_bundle_from_character_prompt_assembly`, optional `RP_PACKET_SHADOW_COMPARE` (logging only) | `runtime_packets` | **Only** module that instantiates `CharacterPromptInputAssembly` |
| `prompt_derivations.py` | Shared **relationship-name ordering** (`select_relationship_prompt_names`) and **priority ladder** (`build_priority_ladder`) for character prompts | `app_turn_prompting`, `runtime_packets` | **Phase 0.5:** extracted so `runtime_packets` can reconstruct prompt-input bundles without importing `app_turn_prompting`; **live path uses these same functions every turn** (not env-gated) |
| `runtime_packets.py` | **Façade:** **`CharacterPromptInputAssembly`**, `live_bundle_from_character_prompt_assembly`, `runtime_packets_from_character_prompt_assembly`; read-only types (`RuntimeScenePacket`, `RuntimeCharacterPacket`, `RetrievedContextBundle` + `RetrievedItem`); `format_retrieved_context_for_prompt`; split/merge scene state; `reconstruct_character_prompt_input_bundle`; `compare_character_prompt_bundles` — implementations in leaf modules (**#166**) | `runtime_packet_types`, `runtime_packet_formatting`, `runtime_packet_scene_split`, `runtime_packet_build`, `runtime_packet_prompt_bundle`, `runtime_packet_reconstruct`, `runtime_packet_parity`; `prompt_input_assembly` (assembly + live bundle), `retrieved_context_select` (types), `prompt_derivations` / `prompt_builders` (reconstruction) | **Phase 0.5:** single assembly feeds both live bundle and packet builders (**character** `build_character_turn_prompt` boundary only). **Phase 2–3.2:** bundle may carry authored + episodic items; **no** selector here. **Shadow:** env-gated; mismatch logs **`rp_app.packet_shadow`** (stderr — not audit-persisted yet) |
| `retrieved_context_select.py` | **Façade:** **Phase 2–3.2** authored index load + `select_retrieved_context_bundle`; **Phase 3.2** merge/episodic helpers; `lore` lane; per-kind subcaps; merged global cap; dedup; `log_retrieval_if_active`; env path; **`MAX_*` caps on this module** for test monkeypatch — leaf logic (**#166**) | `authored_retrieval_index`, `retrieved_selection_authored`, `retrieved_episodic_merge`, `retrieved_context_ops`; **`prompt_retrieval_assembly`** (sole runtime caller for character bundle build), `runtime_packets` (types import), `episodic_memory_compile` (types) | **Not** vector/graph/transcript-wide memory; episodic is **continuity-row compile** only; non-authoritative |
| `episodic_memory_compile.py` | **Phase 3.2** pure candidate pool from `PublicEvent` / `CharacterInterpretation` / `IssueState` / `CanonAnchor`; template summaries; no LLM; no continuity writes | `episodic_memory_cache`, `retrieved_context_select` (mapping to `RetrievedItem`) | Visibility strict; skip events with `canon_impact` |
| `episodic_memory_cache.py` | Snapshot-keyed `session_state` cache for candidate pool; `clear_episodic_pool_cache` | **`prompt_retrieval_assembly`** | Read-only w.r.t. continuity |
| `episodic_memory_select.py` | Per-character filter + episodic-only subcaps from shared pool | **`prompt_retrieval_assembly`** | |
| `episodic_memory_inputs.py` | Read-only flatten/sort of continuity sequences for compile/cache | **`prompt_retrieval_assembly`** | |
| `episodic_memory_prompt.py` | `is_episodic_memory_enabled()` → `RP_EPISODIC_MEMORY` | **`prompt_retrieval_assembly`** | |
| `authored_index_compile.py` | Offline `compile_authored_index`: manifest → **`schema_version` 2** (legacy chunks only, default) or **3** (canonical fields + same legacy projection); strict adapter coverage; `lore` lane; OOC blocklist | `canonical_compile_adapters`, `scripts/compile_authored_retrieval_index.py`, tests (`test_authored_index_compile`, fixtures `compile_sample`, `compile_realistic`) | **Pre-packaging** artifact; does not change retrieval selector/merge at runtime |
| `canonical_compile_adapters.py` | Adapter registry: manifest entry type + JSON key path → `knowledge_type`, `authority_class`, `visibility`, **decomposition strategy**; unmapped → `lore_reference` / `reference_only` (**strict fallback**) | `authored_index_compile` | See implementation snapshot in [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) |
| `scripts/compile_authored_retrieval_index.py` | CLI: `--manifest` / `--output`, **`--schema-version 2`** (default) or **`3`** | `authored_index_compile` | Example manifest: `data/retrieval/authored_manifest.example.json`; output → `RP_RETRIEVED_CONTEXT_INDEX` |
| `app_turn_rendering.py` | Narrator render path | `model_client` | Preserve dialogue verbatim |
| `app_turn_audit.py` | Turn-level audit helpers | `audit_logger*` | |

---

## Continuity engine

**#77 / #81 posture:** **#77** Slice **A** (validated) = foundational continuity seam + **`ContinuityPromptProjectionV77`** + API excursion scaffolding. **#81** (closed) = **`continuity_mutation_pipeline`** + canonical **`SceneState.location`** (**Slice A**), excursion lifecycle on **`process_turn`** (**Slice B**), and **close + reintegration** merges (**Slice C**). **Runtime authority:** `process_turn` → composer + **`validate_resolved_mutations_globally`** + **`apply_resolved_mutations`** is the authoritative turn path; direct excursion APIs, raw location assignment, and out-of-band **`apply_excursion_close_reintegration_mutation`** bypass that validation (non-authoritative for turns). **Atomic rollback** + **`reintegration_commit_id`** idempotency = **reintegration merge only**; **no** global atomicity/idempotency across spatial/excursion keys. Further atoms / broader **#33/#34** product paths = follow-on issues if needed.

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `continuity_mutation_pipeline.py` | **#81** typed mutation requests, D→S→M composer per `CanonicalAtom`, spatial **M** extraction from `spatial_transition`; excursion lifecycle + reintegration payload application | `continuity_state` (`SceneState`), `continuity_reintegration` | **Authoritative for runtime turns** via `continuity_manager.process_turn`; `validate_spatial_transition_move_shape` in `response_validation_content` |
| `continuity_process_turn_orchestration.py` | **#149** Slice **5:** ordered `process_turn` steps after `apply_resolved_mutations` (classification → scene → event → issues → resolved outcomes → interpretations → knowledge → metadata → audit) | `continuity_manager` (callbacks on `self`), `continuity_mutation_pipeline`, `continuity_resolved_outcomes`, `continuity_audit_origin` | **Sequencing glue only** — compose/validate/apply stay on `ContinuityManager.process_turn`; no alternate commit path |
| `continuity_reintegration.py` | **#81 Slice C:** structured merge on excursion close; **atomic rollback** on apply failure; **`reintegration_commit_id`** idempotency | `continuity_state`, `continuity_mutation_pipeline` | Invoked from pipeline **`EXCURSION_CLOSE`** apply only (module function callable directly but bypasses turn validation) |
| `continuity_manager.py` | Promote moves to events; issues; scene; interpretations; knowledge | `continuity_*_helpers`, `continuity_state`, `continuity_mutation_pipeline`, `continuity_process_turn_orchestration`, `continuity_consequence_phrase_maps`, `continuity_issue_manager_wiring`, `continuity_event_promotion_policy`, `continuity_presence_helpers`, `perception_audibility`, `tension_pacing_policy`, `continuity_manager_*_surface` | **#168:** Thin façade — authoritative narrative state unchanged; body split across `continuity_manager_*_surface` modules (mechanical extraction). **`process_turn`** ordering unchanged. |
| `continuity_manager_excursions.py` | **#168** excursion open/update/close + audit hooks; resync presence | `continuity_manager_presence_surface`, `continuity_audit_origin`, `continuity_state` | Callable surface only; `ContinuityManager` delegates |
| `continuity_manager_presence_surface.py` | **#168** presence scratch/reconcile/sync + pre-turn routing + soft-exit guards | `continuity_presence_pipeline`, `continuity_manager_issue_surface` (confrontation guard) | Callable surface only |
| `continuity_manager_issue_surface.py` | **#168** issue create/update + summary-window issue updates + confrontation guard | `continuity_issue_helpers`, `continuity_summary_helpers`, `continuity_issue_manager_wiring` | Callable surface only |
| `continuity_manager_event_surface.py` | **#168** `PublicEvent` promotion path helpers + summary/interpretation-shift collection | `perception_audibility`, `continuity_summary_helpers`, `continuity_state` | Callable surface only |
| `continuity_manager_canon_surface.py` | **#168** canon anchor seed/get/upsert | `continuity_canon_anchors` | Callable surface only |
| `continuity_manager_queries.py` | **#168** retrieval, orchestration context, character context, snapshot, knowledge propagation, interpretations | `continuity_issue_helpers`, `continuity_knowledge_helpers`, `continuity_scene_helpers`, `continuity_summary_helpers` | Callable surface only |
| `tension_pacing_policy.py` | Director-neutral vs directional `tension_shift`; consequence tag → `up`/`down`/`hold`; `resolve_hybrid_pacing`; `apply_consequence_up_saturation_gate` | `continuity_manager` | Consequence `up` suppressed at `extreme`; Director / `down` unchanged |
| `continuity_state.py` | Dataclasses: issues, events, interpretations, anchors, snapshots | — | `PublicEvent.knowledge_level_for` gates on `known_by` first |
| `continuity_issue_helpers.py` | **#157** façade: re-exports issue lifecycle API + patch targets | `continuity_issue_retrieval`, `continuity_issue_lexicon`, `continuity_issue_pressure`, `continuity_issue_matching`, `continuity_issue_transitions`, `continuity_issue_lifecycle` | Issue retrieval, pressure profiles, matching, transitions (incl. plateau), `maybe_create_issue` / `update_issues`; stable `continuity_issue_helpers.*` imports |
| `continuity_issue_retrieval.py` | **#157** read-only issue/event/summary queries from manager | `continuity_state` | `get_active_issues`, `retrieve_public_events`, `retrieve_summary_blocks`, `get_resolved_issue_descriptions` |
| `continuity_issue_lexicon.py` | **#157** tokenize move/event text for matching | `character_move_adapters`, `continuity_state` | `issue_tokens`, `turn_tokens`, `event_tokens` |
| `continuity_issue_pressure.py` | **#157** pressure kinds, markers, turn/issue profiles | `continuity_state` | `_build_turn_pressure_profile`, `_build_issue_profile_from_issue`, tag/marker constants |
| `continuity_issue_matching.py` | **#157** overlap scoring, interaction graph, `find_matching_issue` | `continuity_issue_pressure`, `continuity_state` | `_pressure_match_score`, `merge_issue_terms`, `link_issue_interactions` |
| `continuity_issue_transitions.py` | **#157** transition resolution + **plateau** refresh on `required_next_step` | `continuity_issue_matching`, `continuity_issue_pressure`, `continuity_state` | `_determine_issue_transition`, `apply_mixed_transition_plateau_refresh`, `_build_status_reason` |
| `continuity_issue_lifecycle.py` | **#157** `maybe_create_issue` + `update_issues` (mutation authority) | `continuity_issue_pressure`, `continuity_issue_matching`, `continuity_issue_transitions`, `continuity_state` | Sole writers to `manager.issues` / active issue list in this lane |
| `continuity_knowledge_helpers.py` | Knowledge propagation, boundaries, `told`/inference | events, interpretations, `perception_audibility` | Dialogue-mediated propagation and interpretation quotes respect `viewer_may_perceive_dialogue` |
| `continuity_resolved_outcomes.py` | Facade: structured ingest helpers + delegates apply path to `resolved_outcome_engine` | `resolved_outcome_registry`, `resolved_outcome_engine`, `continuity_manager` | Current aspects: `lodging.sleep_surface`, `communication.housing_call`, `medical.suppressant_formulation`, `access.location_entry` |
| `resolved_outcome_registry.py` | **#163** façade: `ASPECT_REGISTRY` + stable re-exports; parse/promotion split across `resolved_outcome_spec`, `resolved_outcome_normalize`, `resolved_outcome_lodging_sleep_surface`, `resolved_outcome_communication_housing_call`, `resolved_outcome_medical_suppressant_formulation`, `resolved_outcome_access_location_entry`, `resolved_outcome_transaction_scene_commitment` (incl. **`parse_scene_commitment_outcome_candidates`** / merge helpers, GitHub **#127**) | `resolved_outcome_*` leaves, `continuity_state`, `resolved_outcome_engine` | New aspects = new rows; no inference |
| `resolved_outcome_engine.py` | Deterministic pipeline: ingest → slot → `no_op_existing_value` → revoke → promote → persist | `continuity_state`, `resolved_outcome_registry` | Core stays aspect-agnostic; policies live in registry |
| `continuity_scene_helpers.py` | Scene snapshots, orchestration context for prompts | scene state | |
| `continuity_summary_helpers.py` | Summary blocks, retrieval ranking support | issues, events | `key_events` derive from `event.summary` (already audibility-safe at promotion) |
| `continuity_consequence_classifier.py` | Deterministic **`ConsequenceCategory`** detection from structured move; feeds **`turn_metadata` `consequences`**, issues, progression **Q1** | `continuity_manager._classify_turn_consequences` | **Narrow deterministic detector** for the **classifier lane** only; does **not** capture all progression-relevant behavior (**`continuity_manager`**, **`progression_enforcement`** Q2/Q4). **REPOSITIONING** / **REFUSAL**-stance rules, multi-tag + per-category dedupe, negated **`turn`** scrub; REFUSAL **legacy** **`no` / `not`** = standalone-word match only (not embedded substrings); no LLM |
| `continuity_issue_manager_wiring.py` | Issue-related **constants** + thin bridges from `ContinuityManager` to `continuity_issue_helpers` (Issue **#149** Slice 2) | `continuity_issue_helpers`, `continuity_state.IssueState` | **Wiring only** — no algorithm changes; `ISSUE_TOKEN_STOPWORDS` etc. still re-exported from `continuity_manager` for compatibility |
| `continuity_consequence_phrase_maps.py` | Static category→phrase maps for state-change text and actionable implications consumed in **`_classify_turn_consequences`** (Issue **#149** Slice 1) | `continuity_state.ConsequenceCategory` | **Data only** — no classification or promotion logic |
| `continuity_event_promotion_policy.py` | Event type, significance, summary ladder, grounding promotion + **`should_create_event`** gates (Issue **#149** Slice 3) | `continuity_state.ConsequenceCategory`, `character_move_adapters`, `scene_grounding` | **Policy only** — consumed from **`_classify_turn_consequences`**; no `PublicEvent` construction |
| `continuity_presence_helpers.py` | Presence scratch reconciliation, excursion focal/offstage gates, reentry/exit/offstage transitions, deadlock guard, exit-narrative alignment (Issue **#149** Slice 4) | `continuity_state.SceneState`, `scene_exit_detection` | **Scratch + pure helpers only** — authoritative **`SceneState`** presence fields committed only via **`ContinuityManager._synchronize_presence_from_canonical_authority`** |
| `scene_grounding.py` | Derive **read-only** **scene facts** from continuity `PublicEvent.grounding_markers` and active resolved outcomes; format Director/character **SETTLED SCENE FACTS**; **character BINDING CONSTRAINTS** subset via `format_character_binding_constraints_section`; cap/prune | `continuity_manager`, `turn_runner_updates`, `prompt_builders`, `app_turn_director`, `app_turn_prompting` | **No** continuity or `CharacterState` writes; PRD §5.8; spec: `autogen_rp/docs/scene-grounding-layer.md` |
| `perception_audibility.py` | Deterministic **`audibility`** / **`audience`**; per-recipient transcript + structured-move filtering; **`public_safe_event_summary`**; Director orchestration redaction | `app_turn_prompting`, `app_turn_director`, `continuity_manager`, `continuity_knowledge_helpers`, `turn_runner_turn`, `orchestration_helpers`, `prompt_builders` | **#169:** Thin façade — **single source of truth** unchanged; body split across `perception_audibility_*` modules (mechanical extraction). Structured `move` only (no narrator prose parsing) |
| `perception_audibility_constants.py` | **#169** audibility tokens + redacted stubs | — | Imported by other `perception_audibility_*` modules |
| `perception_audibility_normalize.py` | **#169** audience hygiene + infer heuristics + normalize v1/v2 audibility | `perception_audibility_constants`, `character_move_adapters` | |
| `perception_audibility_visibility.py` | **#169** speech/move visibility + full-narrator gating | `perception_audibility_normalize`, `character_move_adapters` | |
| `perception_audibility_quote_policy.py` | **#169** interpretation dialogue quoting policy | `perception_audibility_visibility`, `character_move_adapters` | |
| `perception_audibility_events.py` | **#169** event knower sets + public-safe summaries | `perception_audibility_normalize`, `character_move_adapters` | `public_event_extraction` alias |
| `perception_audibility_formatting.py` | **#169** observable v1/v2 transcript line formatting | `perception_audibility_visibility`, `perception_audibility_constants` | |
| `perception_audibility_player.py` | **#169** player-line projection for character prompts | `perception_audibility_normalize`, `perception_audibility_visibility`, `perception_audibility_formatting` | |
| `perception_audibility_history.py` | **#169** recent dialogue history assembly | `perception_audibility_normalize`, `perception_audibility_visibility`, `perception_audibility_formatting`, `perception_audibility_player`, `character_move_adapters` | |
| `perception_audibility_structured.py` | **#169** per-viewer structured move derivation + Director copy | `perception_audibility_normalize`, `perception_audibility_visibility`, `character_move_adapters` | |
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
| `scene_template.py` | Load/validate templates, role assignments, **`anchor_role_name`** (Issue #80) | `data/scene_templates` | `list_templates` skips `*_initial_message` / `*_progression` (see **Template-associated support files** in `AUTHORED_SOURCE_CONTRACT.md` §1) |
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
| `orchestration_helpers.py` | **Façade:** orchestration cache + selection policy (state init, continuity sync, continuation override, spotlight / fairness / fallback, progression override, bounded histories, `build_recent_scene_context`) — implementations in leaf modules (**#164**) | `orchestration_state_init`, `orchestration_continuity_mirror`, `orchestration_continuation`, `orchestration_spotlight`, `orchestration_progression`, `orchestration_scene_context`, `orchestration_turn_append`, `st.session_state` | Persists `audibility`/`audience` on structured move entries; narrator scene context uses perception-filtered transcript. **#152** in-file normalization (historical “domains A–G”) preceded **#164** mechanical split — prefer editing **leaf** files for behavior changes. |
| `prompt_builders.py` | Structured prompt text for Director/characters/Narrator | continuity, templates | Labels perception-filtered transcript/structured sections; **character** template: optional `scene_binding_constraints_section`, static **EVIDENCE & AUTHORITY DISCIPLINE** block, then **OUTPUT RULES**; inputs assembled in `app_turn_prompting` (Phase 0.5 shadow parity in `runtime_packets`) |

---

## Model & audit

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `model_client.py` | DeepSeek / agent construction | AutoGen stack | Env: API keys |
| `audit_fact_tracking.py` | Offline `fact_spec.v1` post-processor: `failure_classification` over character `*_full.json` (**#58**); shared **`run_fact_track_postprocess`** + companion JSON (**#62**) | `issue29_investigation`, `audit_support_manifest` | **Not** runtime / not on #59 allowlist; CLIs `run_audit_fact_track.py` (stdout) and `run_scene_simulation_llm.py` **`--fact-spec`** (audited runs) |
| `audit_logger.py` | Audit session/round/turn lifecycle | `audit_logger_paths`, writers | |
| `audit_logger_paths.py` | Paths: `rp_app/data/rp_audits` | — | |
| `audit_logger_writers.py` | Write JSON artifacts; **`update_manifest_turn_counter`** (read-merge-write session manifest) | — | |
| `audit_logger_serialization.py` | Serialize payloads | — | |
| `audit_logger_summary_issue_taxonomy.py` | Issue category keys + `_audit_summary` issue bucketing helpers | `audit_logger` | **#154** Slice A |
| `audit_logger_summary_prep.py` | Pre-assembly: manifest/narrative/index backfill + audit artifact gap scan | `audit_logger_summary_report`, `audit_instrumentation`, `audit_logger_summary_output_continuity` | **#154** Slice C |
| `audit_logger_summary_rounds.py` | Round-level summary data | — | |
| `audit_logger_summary_report.py` | `_audit_summary.json` aggregation; **`continuity_observability_summary_v1`** when `write_summary_report` receives **`continuity_manager`**, else **`continuity_observability_status_v1`** (unavailable — no synthetic summary) | `continuity_observability_summary`, `audit_logger_summary_output`, `audit_logger_summary_prep` | |
| `audit_logger_summary_output.py` | **`build_report`** façade + spotlight/role/regression helpers; re-exports continuity + core assembler | `audit_logger_summary_output_report_core`, `audit_logger_summary_output_continuity` | **#154** Slice E |
| `audit_logger_summary_output_continuity.py` | Continuity overview + indexed-turn counting used by summary prep/output | — | **#154** Slice E |
| `audit_logger_summary_output_report_core.py` | **`assemble_audit_summary_report_dict`** — deterministic `_audit_summary.json` dict assembly | `audit_logger_summary_output_continuity` | **#154** Slice E |
| `summary_audit_helpers.py` | Prompt/audit bridges for summaries | continuity | |
| `audit_ctar.py` | CTAR projection for **`metadata.ctar`** (**#79**) | `turn_runner_audit` | |
| `audit_runtime_mirrors.py` | **`scene_state_after`** mirror; **`excursion_audit_digest_v1`** (**#79**) | `turn_runner_audit` | |
| `continuity_audit_origin.py` | Bypass vs pipeline classification; **`flush_continuity_audit_origin_export_payload`** (**#79**) | `continuity_manager`, `continuity_observability_summary` | |
| `continuity_observability_summary.py` | **`continuity_observability_summary_v1`** rollup and **`continuity_observability_status_v1`** (unavailable marker) for **`_audit_summary.json`** (**#79**) | `continuity_audit_origin`, `audit_logger_summary_report` | |
| `audit_v2_deterministic.py` | **Audit v2** deterministic envelopes (character / narrator / prose); **`char_masked_progression_strict`** masked-progression observability (**#73**) | `audit_v2_escalation_policy`, `audit_v2_pipeline`, `turn_runner_turn` | Log-only; masked check escalation always **`pass`** |
| `audit_v2_escalation_policy.py` | V2 **check_id** → dimension mapping; tri-state scoring; escalation rollup | `audit_v2_deterministic`, `audit_v2_pipeline` | **`char_masked_progression_strict`** is non-gating |
| `audit_v2_pipeline.py` | Async V2 bundle assembly (deterministic + optional LLM) | `audit_v2_deterministic`, `audit_v2_llm` | |

---

## UI (Streamlit)

| Module | Responsibility | Interacts with | Notes |
|--------|----------------|----------------|-------|
| `ui_chat.py` | Chat history, input | turn_runner | |
| `ui_sidebar_session.py` | Session list, load/save | `SessionManager` | |
| `ui_sidebar_player.py` | Player character selection | cards | |
| `ui_sidebar_scene_setup.py` | Cast, template, roles, audit toggle | `scene_template` | |
| `ui_sidebar_opening.py` | Template opener list, multi-opener selection (GitHub #101); template defines available openers, bootstrap applies selection, operator UI template/custom only—no `character_asset` in Streamlit (GitHub #108, #113) | `scene_opener` | |

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
