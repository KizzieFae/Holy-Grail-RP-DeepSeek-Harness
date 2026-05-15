# Architecture overview

This document expands the three-layer model in [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) for engineers and tools. Authoritative product intent remains in the PRD.

## Three layers

```text
┌─────────────────────────────────────────────────────────────┐
│  Ingestion (static today at the packaging boundary edge)     │
│  Authored JSON → offline canonical compile → index artifact  │
│  (future: entities, relationships, graph/vector stores)      │
└───────────────────────────────┬─────────────────────────────┘
                                │ structured knowledge outputs
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Packaging (bridge — target integration seam)               │
│  Knowledge + authoritative state → per-turn runtime inputs  │
│  Outputs: RuntimeCharacterPacket, RuntimeScenePacket,       │
│            RetrievedContextBundle (see PACKET_CONTRACTS.md)   │
└───────────────────────────────┬─────────────────────────────┘
                                │ bounded prompts / structured context
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  RP execution (AutoGen runtime — current bulk: rp_app)        │
│  Director, orchestration, characters, Narrator, validation,  │
│  continuity engine, Scene Grounding (MVP spec), audit        │
└─────────────────────────────────────────────────────────────┘
```

### Dependency direction

- **Ingestion** does not call the live RP UI or turn loop. It produces **durable knowledge artifacts** consumable by packaging. **Today:** deterministic **offline** compile of authored sources to a JSON index (`authored_index_compile` / `compile_authored_retrieval_index`, `schema_version` 2 or 3) is the implemented slice; **runtime** behavior is unchanged—`retrieved_context_select` still consumes the **legacy** chunk fields only.
- **Packaging** reads authoritative **runtime state** (from the continuity/orchestration side) and **retrieved** candidates; it does not replace continuity as source of truth for “what happened.” Future packaging should also include the **Scene Grounding** read model (settled scene facts for prompts — PRD §5.8).
- **RP runtime** executes turns; it **updates** authoritative state and **logs** audits. Today it builds prompts largely from cards + continuity structures; tomorrow the same boundaries should consume **packets** at the packaging boundary.

### System boundaries

| Concern | Layer |
|--------|--------|
| Extracting lore from external sources, graph/vector stores | Ingestion (future) |
| Selecting what enters a token-bounded turn context | Packaging |
| Who speaks next, validation, scene/session persistence | RP runtime |
| Authoritative scene/issue/knowledge-boundary state | RP runtime (continuity engine today) |
| Settled-scene **prompt projection** (facts/locks, read-only, derived from continuity) | RP runtime → prompts (Scene Grounding MVP — [spec](./autogen_rp/docs/scene-grounding-layer.md)) |

**Turn-time roles (truth vs voice):** **Character** emits the **contractual** structured move (e.g. action, dialogue, motivation; optional perception fields). **Director** owns **turn selection** and **decision** fields such as **`tension_shift`** / **`environment_event`** in its JSON. **Continuity** owns **authoritative** issue lifecycle, state changes, and classification that feed **`_narrative.json`** and summaries. **Orchestration** merges **enriched** structured history (e.g. for prompts and tails). **Narrator** owns **rendering** only. Do not assign continuity outcomes to the character layer **solely** because a heuristic audit read an empty field on the **raw move** (see `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` — Character Audit v1).

PRD alignment: vector retrieval is for **similarity and suggestions**, not authoritative truth ([Holy Grail PRD.md](./Holy%20Grail%20PRD.md) §7).

---

## Current system (working reality)

- **Location:** `autogen_rp/python/rp_app/` (+ tests under `autogen_rp/python/tests/`, data under `autogen_rp/python/data/`, audits under `autogen_rp/python/rp_app/data/rp_audits/`).
- **Characters:** JSON **cards** in `python/data/autogen_characters/`; loaded by `character_loader.py`; agents created via `model_client.py`.
- **Scenes:** Streamlit-driven; **scene templates** in `python/data/scene_templates/`; openers are loaded and selected via `scene_opener.py`, `ui_sidebar_opening`, and `scene_lifecycle_start` (the **template** defines the available template-scoped opener set; the **selected** opener is applied at **bootstrap**—**[Issue #101](https://github.com/KizzieFae/Holy_Grail_RP/issues/101)**, **[Issue #108](https://github.com/KizzieFae/Holy_Grail_RP/issues/108)**; Streamlit does not use `character_asset` or cast-driven opener **availability**; generic template `opening_text` as the primary Start Scene path removed—**[Issue #100](https://github.com/KizzieFae/Holy_Grail_RP/issues/100)**).
- **State:** `ContinuityManager` and related types hold structured scene, issue, event, and interpretation state (see `continuity_manager.py`, `continuity_state.py`). **Runtime Continuity Contract** (**GitHub #77** / **#81**): **#77 Slice A** (validated) covers the **foundational** seam (**D3** gating), authored **anchor** resolution (**#80**), **`ContinuityPromptProjectionV77`**, projection-level Director/character parity, and **API-level** excursion scaffolding with **P_focal ∩ E_active = ∅** enforcement on covered paths—not the **full** contract end-to-end. **#81** (closed): **`continuity_mutation_pipeline`** commits **`SceneState.location`** (**Slice A**), applies **excursion lifecycle** open/update/close (**Slice B**), and **close + reintegration** merges via **`continuity_reintegration`** (**Slice C**) inside **`process_turn`** (D→S→M composer; **S** via optional `session_mutation_candidates`). **Runtime turns:** that pipeline path is **authoritative**; direct **`open_excursion` / `update_excursion` / `close_excursion`**, raw **`SceneState.location`** writes, and out-of-band **`apply_excursion_close_reintegration_mutation`** **bypass** pipeline validation and are **non-authoritative / unsafe** for turn parity. **Presence** is **canonical stored state** on **`SceneState`** (reconciled); **soft offstage** is canonical but **cleared for `E_active`**. **Reintegration** is **not** the only event/outcome path; **atomic rollback** and **`reintegration_commit_id`** idempotency apply **only** to the reintegration merge (see **`autogen_rp/python/rp_app/ARCHITECTURE.md`**). **Signal contract (#216):** continuity is authoritative; explicit **`excursion_lifecycle`**, **reintegration**, and **`session_mutation_candidates`** are the preferred path for **committed** off-focal state; classifier/interpreter heuristics are secondary; orchestration consumes **presence**; **perception** is separate; narrator prose is non-authoritative—see **`autogen_rp/python/rp_app/ARCHITECTURE.md`** (*Off-focal / reentry signal contract*) and **`autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`** (*Perception-only privacy vs continuity-grounded offstage*). Broader **#33/#34** product validation and orchestration wiring remain follow-on where not yet in scope.
- **Consequence classification:** deterministic tags on structured moves (`continuity_consequence_classifier.py`) feed continuity turn metadata and progression Q1; REFUSAL **legacy** dialogue markers **`no` / `not`** match **standalone words** only (word boundaries), not embedded substrings (e.g. "nothing", "know"). Details: `autogen_rp/python/rp_app/ARCHITECTURE.md`.
- **Turn flow:** Director selection → character structured move → validation → Narrator render → continuity updates (see `turn_runner*.py`, `app_turn_*.py`). **Scene Grounding (MVP):** after continuity commit, derive a capped **settled facts** block for Director/character prompts — [PRD](./Holy%20Grail%20PRD.md) §5.8, [technical spec](./autogen_rp/docs/scene-grounding-layer.md).
- **Memory layer (`memory_layer/`):** commit-time episodic writes (perception-filtered observers) and episodic **read/format** for character prompts; **`state_context`** is composed in `app_turn_prompting` and passed unchanged to `prompt_builders` — [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md).
- **Phase 0.5 packet seam (character prompt path — complete):** `CharacterPromptInputAssembly` is the **single source of truth** for inputs to **`prompt_builders.build_character_turn_prompt`**; `live_bundle_from_character_prompt_assembly` and `runtime_packets_from_character_prompt_assembly` derive the live kwargs dict and `RuntimeScenePacket` / `RuntimeCharacterPacket` from that assembly (no dual derivation). **Cast / others list:** live and reconstructed bundles both use **`get_character_display_name_fn`** so id vs display labels do not duplicate **CAST ROLE MAP** rows or leave the actor in **OTHER PRESENT CHARACTERS**. `RP_PACKET_SHADOW_COMPARE` enables structured bundle parity + optional core prompt-text check (suffix layers excluded). **Scope:** character prompts only; Director and Narrator do not yet use this seam. Details: [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md), [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md).
- **Behavioral validation (2026-04-07 checkpoint):** After GitHub **#24** (prompt integrity) fix, a **closed** headless wave re-validated cast/roster prompts across six scenario configurations (audits **`session_388`–`session_393`**; metrics under `autogen_rp/python/validation_runs/plan_execution/`). **No #24 regression** in sampled character audits; classifier/progression pytest gate green; **`long_session`** used for exit-vs-presence stimulus. **#1** (identity bleed) not reproduced — still open. See [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) and [RP_SETUP_TODO.md](./autogen_rp/python/RP_SETUP_TODO.md) Issue Tracking subsection.
- **Phase 1 — scoped retrieval-lock / validation (complete):** Confirmed **no retrieval seam bypass**; **`RetrievedContextBundle`** is the **behavioral source**; **`retrieved_context_section`** is **non-authoritative**, **bundle-driven**, **pure derived** text. Added **assembly invariant**, **bundle composition** snapshots/goldens, **prompt-shape** / **authority** tests; shadow pytest subset with `RP_PACKET_SHADOW_COMPARE=1` green. **Did not** add selector features, new lanes, graph/vector retrieval, or expand Director involvement. See `autogen_rp/python/RP_SETUP_TODO.md` Phase 1 and `PACKET_CONTRACTS.md` §RetrievedContextBundle.
- **Authored retrieval — accepted baseline + standard eval (Phase 4A):** **Accepted** content is **minimal character `lore_facts`** + **template `role_slots` + refined `premise`** (operational manifest → `operational_pilot_v3.json`), activated **only** via **`RP_RETRIEVED_CONTEXT_INDEX`**. **Simulation:** OFF/ON is a **standard** headless mode (`--retrieved-context-index`, `structured_eval.retrieval_session`, strict verify when ON + `scene_template_id`). **Historical pilot** evaluation and **rejected situational template cap** are documented in `OPERATIONAL_RETRIEVAL_PILOT.md` / `RP_SETUP_TODO.md` (pilot section); runbook remains the artifact map. **Headless** **`scene_template_id`** matches Streamlit. Selector: **fixed per-`source_kind` subcaps** only. See [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) (*Authored retrieval*) and `rp_app/AUDIT_DOCUMENTATION.md`.
- **Orchestration:** Final speaker resolution combines address, continuation override, Director, validation/reconciliation (PRD §5.3); implemented in `orchestration_helpers.py` and turn pipeline.
- **Behavioral Validation Layer:** Scenario manifests, headless runs on the same path as Streamlit, optional audit JSON, structured metrics (`structured_eval`), and baseline vs treatment (e.g. `--no-progression-enforcement`). Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md).

- **Continuity audit observability (Issue #79, closed):** Per-turn audit rows can carry **CTAR** (`metadata.ctar`), **`scene_state_after`** mirrors, excursion digest, and pipeline **`continuity_audit_origin`**; **`_audit_summary.json`** includes **`continuity_observability_summary_v1`** when **`write_summary_report`** receives a **`ContinuityManager`**, otherwise **`continuity_observability_status_v1`** (**`unavailable`**) — never a silent omission. These surfaces are **observational** only (**#59**); committed state remains **`ContinuityManager` / `SceneState` / excursions**. Details: [autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md](./autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md) (*Continuity observability (Issue #79)*).

Details: `autogen_rp/python/rp_app/ARCHITECTURE.md`, `autogen_rp/docs/architecture.md`.

---

## Future system (direction, not a rewrite yet)

- **Cards** remain the practical source until ingestion + packaging land; the **packet contracts** describe the intended **runtime-facing** shape ([PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)).
- **Phase 0.5 (character packet seam):** Mechanical seam at **`build_character_turn_prompt`** inputs is **implemented and validated**; see current system bullets above.
- **Phase 3.4 (canonical compile milestone):** [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) defines the contract; **offline** compile supports **`schema_version` 3** (canonical fields alongside legacy projection). This **does not** change runtime retrieval or merge—continuity and scene grounding remain authoritative; v3 is **opt-in** at compile time (`--schema-version 3`; CLI default remains **2**).
- **Later:** Graph/vector stores and optional **request-driven retrieval** (e.g. a retrieval agent) must **conform** to that canonical envelope; agents may rank candidates but **do not** determine truth ([CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) §11).
- **Packaging** becomes the single place that merges: stable identity, dynamic state, relationships, **retrieved** snippets, and scene-facing summaries—so the runtime does not grow ad-hoc retrieval logic.
- **Ingestion** supplies compiled profiles and retrievable corpora; **runtime** stays deterministic where possible for orchestration and validation.

Roadmap tasks: `autogen_rp/python/RP_SETUP_TODO.md` (packet layer section).

---

## Where not to “fix” things

- Do not move **long-horizon truth** into prompts or unbounded transcript growth (see `autogen_rp/docs/architecture.md`).
- Do not treat **Director prompt tweaks** as the default fix for continuity or orchestration bugs.
- Keep **`app.py`** a thin composition layer unless the task explicitly expands it.

---

## How to approach problems

Prefer **continuity → scene grounding → orchestration → summaries → validation → Director → Narrator** before changing prompt copy. Use the **symptom → file** table in [MODULE_INDEX.md](./MODULE_INDEX.md) for a quick entry point, and [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) for full rules, per-symptom notes, and persistence/audit pointers.

---

## Related docs

- [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md) — **Canonical authored file types** (Character, Template, Scenario/Bootstrap, Opener), exclusions, bootstrap vs knowledge; central contract for **on-disk authoring**
- [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) — Phase 3.4 canonical knowledge contract, authority/visibility, static ingestion boundaries, future retrieval compatibility
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) — **Behavioral Validation Layer** (core architectural layer: scenarios, headless LLM runs, audits, metrics, baseline comparison)
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) — diagnosis order and symptom routing
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — packet intent and field groupings
- [GLOSSARY.md](./GLOSSARY.md) — terms
- [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md) — on-disk data
- [autogen_rp/docs/scene-grounding-layer.md](./autogen_rp/docs/scene-grounding-layer.md) — Scene Grounding MVP (facts contract, lifecycle, prompts)
- [MODULE_INDEX.md](./MODULE_INDEX.md) — code map (`autogen_rp/python/rp_app/`)
- [autogen_rp/python/data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md](./autogen_rp/python/data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md) — operational authored retrieval baseline, OFF/ON wiring, headless template id, rejected selector experiment
