# Holy Grail RP module index

Quick map for **where to change what** in the **current** system. Symptom routing only; architecture and invariants: [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md), [docs/architecture.md](./docs/architecture.md). Implementation entry: [v2/README.md](./v2/README.md). Authored files: [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md).

**Constraints:** Keep the Domain Host as the composition boundary for domain truth. Keep `v2/ui/` presentation-only. Do not fix continuity or speaker-selection bugs by bloating Director prompts. Preserve `must_remain` as **structural presence**, not “must speak every turn.” Production scene templates use **`cohesion_policy: anchor_only`** only (#245): anchor effective **`must_remain`** (interim until #247); non-anchor default **`flexible`**; non-anchor **`must_remain`** overrides require **`cohesion_rationale`**.

For **diagnosis order**, see [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md). Scenario manifests: `data/fixtures/progression_simulation_scenarios/` via `v2/domain/modules/progression_simulation_scenarios.py`. Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md). Offline audit analysis: `tools/investigation/`.

---

## Current owner roots

| Owner | Path | Use this map for |
|-------|------|------------------|
| UI (presentation) | `v2/ui/streamlit_app.py` | Catalog pickers, transcript display, HTTP to the Node application API |
| DSH / Node runtime | `v2/rp_runtime/` | Round sequencing, inference, provider routing, context **transport** |
| Domain Host | `v2/domain_api/` | Session/round APIs, context **assembly**, validate, `commit_move` |
| Domain library | `v2/domain/modules/` | Continuity, validation rules, prompt **text**, perception, grounding, templates |
| Product data | `data/` | Cards, templates, persisted sessions (`HG_DATA_DIR` / `HG_SESSIONS_DIR`) |

Node calls the Domain Host over HTTP. Python does not call DSH. `HgContextBridge` transports already-built manifests; it does not own domain interpretation.

---

## Symptom → first file to open

| Symptom or task | Start here |
|-----------------|------------|
| Launch / supervisor / app API | `v2/rp_runtime/bin/hg-app.mjs`, `src/runtime-supervisor/supervisor.mjs`, `src/application/app-server.mjs` |
| UI-only chrome (no domain truth) | `v2/ui/streamlit_app.py` |
| Session create / open / persist | `v2/domain_api/session_repository.py`, `session_setup.py`, `v2/domain/modules/session_manager.py` |
| Scene start / opener / roles | `v2/domain_api/session_setup.py`, `opening_prompt.py`; DSH `src/plugins/hg-phase-executors/opening-phase.mjs`; domain `scene_template.py`, `scene_opener.py`, `app_state_scene.py` |
| Failed round / who acts next | DSH `src/plugins/hg-round-orchestrator/service.mjs`; Host `participation_policy.py`, `kernel.py` (`eligible-actors`, `participation-decision`); domain `response_validation_selection.py` |
| Director decision / invalid `next_actor` / auxiliary contract | DSH `src/plugins/hg-phase-executors/director-phase.mjs`; Host `kernel.py` (`prepare_director_context`, `validate_director_decision`), `continuity_context_projector.py`; domain `director_decision_contract.py`, `response_validation_parsing.py`, `response_validation_selection.py`, `tension_pacing_policy.py` |
| Character move parse / unresolved placeholders / move-shape | domain `response_validation_parsing.py`, `response_validation_content.py` (`validate_bot_response_for_runtime`); Host `kernel.py` (`validate_move`); DSH `character-phase.mjs` |
| Presence / exit / `must_remain` | `response_validation_presence.py` (`get_must_remain_characters`), `scene_template.py`, `scene_template_cohesion.py` |
| Voice / drift / semantic prose quality (pre-publication) | DSH `character-phase.mjs`, `character-semantic-evaluation.mjs`; Host `semantic_evaluation_context.py`, `kernel.prepare_semantic_evaluation_context`; domain anchors in `character_state_model.py`, cards in `data/characters/` |
| Wrong prompt / missing context | Host `continuity_context_projector.py`, `kernel.py` (`prepare_context`, `prepare_director_context`, `prepare_narrator_context`); domain `prompt_builders.py`; DSH `src/plugins/hg-context-bridge/` (transport only) |
| Model / provider routing | DSH `src/lib/inference-profile.mjs`, `src/lib/mount-deepseek-provider.mjs`; settings surface `src/application/application-settings.mjs` |
| Stale issues / events / knowledge boundaries | `continuity_manager.py`, `continuity_issue_helpers.py`, `continuity_knowledge_helpers.py`, `perception_audibility.py` |
| Whisper / private line known to the wrong character | `perception_audibility.py`, then Host projector / `prompt_builders.py`, `continuity_manager.py` |
| Settled facts / binding constraints in prompts | `scene_grounding.py`, Host `continuity_context_projector.py`, `prompt_builders.py` |
| Episodic “memories” block | `memory_layer/retrieval.py`; Host `memory_service.py` / `memory_retrieval.py` |
| Authored retrieval / lore in prompts | Host `retrieval_selection.py`, `authored_knowledge.py`, `compiled_index_provider.py`, `retrieval_service.py` (#31) |
| Librarian knowledge bundles / semantic mediation (#34 S2a) | Host `librarian_service.py`, `librarian_mediation*.py`; DSH `librarian-mediation-substrate.mjs`; HTTP `/v1/librarian/mediation/*` |
| Librarian bundle → Packaging mapper (#34 S2b) | Host `librarian_packaging_mapper.py`, `librarian_packaging_policy.py`, `librarian_packaging_validity.py` |
| Librarian write-side proposal seam (#34 S4a) | Host `librarian_proposal_*.py`, `continuity_librarian_proposals.py`; DSH `librarian-proposal-substrate.mjs`; HTTP `/v1/librarian/proposals/*` |
| Storyteller advisory cognition (#32 S3a) | Host `storyteller_service.py`, `storyteller_contract.py`; DSH `storyteller-cognition-substrate.mjs`; HTTP `/v1/storyteller/*` (isolated; no role manifest wiring) |
| Storyteller → Packaging mapper (#32 S3b) | Host `storyteller_packaging_mapper.py`, `storyteller_packaging_policy.py`, `storyteller_packaging_validity.py` |
| Storyteller live round integration (#32 S3c, Model A) | `hg-round-orchestrator/service.mjs` round-start cognition; Host bind + Director/Character S3b injection; commit invalidates before Narrator (no live Narrator Storyteller lanes) |
| Commit / continuity not updating | Host `kernel.py` (`commit_move`); `continuity_manager.py` (`process_turn`), `continuity_mutation_pipeline.py` |
| Audit / trace missing | DSH `src/plugins/hg-trace-emitter/`; Host `session_history.py`; procedure [docs/audit-workflows.md](./docs/audit-workflows.md) |
| Forensic execution evidence / actor selection / semantic QA chain | `tools/investigation/list_execution_evidence.py`; `v2/rp_runtime/src/lib/execution-evidence/`; [docs/rp-data-layout.md](./docs/rp-data-layout.md) (#28) |
| Scenario validation | [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md); `progression_simulation_scenarios.py`; `v2/domain/tests/`; `v2/rp_runtime/tests/` |
| Prompt wording only (after ruling out state) | `prompt_builders.py` |

---

## Runtime surfaces

| Surface | Responsibility | Notes |
|---------|----------------|-------|
| `v2/ui/streamlit_app.py` | Presentation client: catalogs, setup pickers, transcript, HTTP to Node `/api/*` | No `ContinuityManager`. UI `st.session_state` is a display cache (`hg_session_id`, transcript), not orchestration authority |
| `v2/rp_runtime/src/application/hg-application-client.mjs` | Application session wiring; starts supervisor; runs rounds | Talks to Domain Host through the runtime, not from Streamlit |
| `v2/rp_runtime/src/plugins/hg-round-orchestrator/` | Round lifecycle: start round, eligibility, phase sequence, completion | Node-owned |
| `v2/rp_runtime/src/plugins/hg-phase-executors/` | Director, character, narrator, opening inference phases | Calls Host prepare/validate/commit around DSH inference |
| `v2/rp_runtime/src/plugins/hg-context-bridge/` | Registers Host prompt manifests onto an ephemeral DSH agent | Transport only |
| `v2/rp_runtime/src/lib/domain-api-client.mjs` | HTTP client for Domain Host `/v1/*` | Python does not call this |
| `v2/domain_api/kernel.py` | Authoritative Host operations: session, round, prepare, validate, commit | Production façade for domain truth |
| `v2/domain_api/http_transport.py` | Localhost HTTP for the Host contract | Replaceable transport |
| `v2/domain_api/session_repository.py` | Live session cache + durable save via `SessionManager` | Persistence owner with Host |
| `v2/domain_api/session_state.py` | `LiveSession` (continuity + character states + round fixture) | Not Streamlit session state |
| `v2/domain_api/continuity_context_projector.py` | Authoritative context projection into prompt contributions | Domain interpretation for prompts |
| `v2/domain_api/librarian_packaging_mapper.py` | Deterministic `LibrarianKnowledgeBundle` → `PromptContribution` mapping (#34 S2b) | Validity gate + consumer policies; not wired into Character manifests yet |
| `v2/domain_api/semantic_evaluation_context.py` | Read-only semantic evaluation context + authority references | Host prepares evidence; DSH owns judgment |
| `v2/domain_api/participation_policy.py` | Deterministic participation / forced-speaker policy | Complements Director phase |

---

## Continuity engine

Runtime authority: Host `commit_move` → `ContinuityManager.process_turn` → mutation pipeline compose/validate/apply. Direct excursion helpers that bypass that path are non-authoritative for turns.

| Module | Responsibility | Notes |
|--------|----------------|-------|
| `continuity_manager.py` | Façade: events, issues, scene, interpretations, knowledge | Authoritative narrative state; split across `continuity_manager_*_surface` modules |
| `continuity_mutation_pipeline.py` | Thin façade: compose, validate, apply, audit | Edit **leaves** (`continuity_mutation_pipeline_*`) for mechanics |
| `continuity_process_turn_orchestration.py` | Ordered post-apply `process_turn` steps | Sequencing glue only |
| `continuity_semantic_proposals.py` | Proposal legality; accept / reject / no_proposal | Consumed before commit |
| `continuity_reintegration.py` | Excursion close merge; atomic rollback on apply failure | Invoked from pipeline close apply |
| `continuity_state.py` | Dataclasses: issues, events, interpretations, anchors, snapshots | `PublicEvent.knowledge_level_for` gates on `known_by` first |
| `continuity_issue_helpers.py` | Issue lifecycle façade | Leaves: retrieval, lexicon, pressure, matching, transitions, lifecycle |
| `continuity_knowledge_helpers.py` | Knowledge propagation and boundaries | Respects `viewer_may_perceive_dialogue` |
| `continuity_resolved_outcomes.py` | Structured ingest; delegates apply to `resolved_outcome_engine` | Aspects in `resolved_outcome_registry.py` |
| `continuity_consequence_classifier.py` | Deterministic consequence tags from structured moves | Feeds turn metadata / Q1; not all progression-relevant behavior |
| `scene_grounding.py` | Read-only settled-facts / binding-constraint projection | No continuity or `CharacterState` writes |
| `perception_audibility.py` | Who may see dialogue / structured moves / narrator render | Façade over `perception_audibility_*` leaves |
| `tension_pacing_policy.py` | Consequence tag → tension shift gating | No Director prompt ownership |

Issue / presence / event / canon **leaves** under `continuity_*` remain the place to change those algorithms. Prefer editing the leaf named in the symptom table rather than the façade.

---

## Validation

Validators **reject or annotate**. They do not replace Director selection or continuity commits. Host `validate_move` / `validate_director_decision` are the production call sites.

| Module | Responsibility |
|--------|----------------|
| `response_validation.py` | Façade |
| `response_validation_parsing.py` | Character move and Director JSON parse |
| `response_validation_content.py` | Production runtime (`validate_bot_response_for_runtime`: R02a placeholders, R03 move-shape); offline scenario hook (`validate_bot_response_for_scenario`) |
| `response_validation_presence.py` | `must_remain` constraint helpers (`get_must_remain_characters`) |
| `response_validation_selection.py` | Eligibility helpers (`get_available_actors`, `eligible_agent_keys_for_present_characters`); non-authoritative vs Host/DSH Director selection |

---

## Scene, cards, session persistence

| Module | Responsibility | Notes |
|--------|----------------|-------|
| `scene_template.py` | Load/validate templates, roles, `anchor_role_name`, `cohesion_policy` | `data/scene_templates/` |
| `scene_template_cohesion.py` | `anchor_only` effective presence resolver | Missing `cohesion_policy` fails load |
| `scene_opener.py` | Opening text / opener JSON resolution | Used by Host setup |
| `app_state_scene.py` | Apply template setup onto `SceneState` | Called from `session_setup.py` |
| `continuity_setup_seam_v77.py` | Canonical continuity init/apply ordering at scene start | Host setup spine |
| `v2/domain/character_cards.py` | Character card I/O | Production card reader used by Host setup |
| `character_state_model.py` | Per-character state schema / identity prompt text | |
| `character_state_manager.py` | Update goals, emotions, relationships | |
| `session_manager.py` | Save/load JSON sessions, `_session_index.json` | Used by Host `SessionRepository`; not a Streamlit lifecycle module |
| `prompt_builders.py` | Structured prompt **text** for Director / character / Narrator | Inputs assembled by Host projector |
| `narrator_presentation_validation.py` | Deterministic Narrator F1/F2 speech fidelity | Host `validate_narrator_presentation`; runtime acceptance gate (#24) |

---

## Memory (domain)

| Module | Responsibility | Notes |
|--------|----------------|-------|
| `memory_layer/facade.py`, `writes.py`, `storage.py` | Commit-time episodic writes | Perception-filtered observers |
| `memory_layer/retrieval.py` | Episodic sections for prompt context | Host memory services are the production façade |
| `v2/domain_api/memory_service.py` | Host memory policy / cross-scope | |
| `v2/domain_api/memory_retrieval.py` | Host retrieval into context | |

---

## Related docs

- [v2/README.md](./v2/README.md) — implementation tree and run commands
- [docs/repo-map.md](./docs/repo-map.md) — physical topology
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) — diagnosis order
- [docs/architecture.md](./docs/architecture.md) — boundaries and invariants
- [docs/rp-data-layout.md](./docs/rp-data-layout.md) — on-disk data
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — packet seam intent
- [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md) — Scene Grounding MVP
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) — behavioral validation
