# Architecture Guidance

This document captures architecture guardrails that both Windsurf and Cursor should follow.

**What this file is for:** RP **package** integration — module boundaries, validation posture, and how `python/rp_app/` fits the monorepo. It is **not** the only architecture entrypoint.

- **Product-level orientation and file routing:** [`ARCHITECTURE_OVERVIEW.md`](../../ARCHITECTURE_OVERVIEW.md) and [`MODULE_INDEX.md`](../../MODULE_INDEX.md) (repo root). **Authored JSON boundaries (Character / Template / Bootstrap / Opener):** [`AUTHORED_SOURCE_CONTRACT.md`](../../AUTHORED_SOURCE_CONTRACT.md).
- **This file (`autogen_rp/docs/architecture.md`):** shared guardrails for tooling and cross-package work under `autogen_rp/`.
- **App runtime (Director, Narrator, continuity, enforcement):** [`python/rp_app/ARCHITECTURE.md`](../python/rp_app/ARCHITECTURE.md).
- **Scenario validation** (scenarios, headless runs, `structured_eval`, audits): **[`SCENARIO_VALIDATION_FRAMEWORK.md`](../../SCENARIO_VALIDATION_FRAMEWORK.md)** (repo root) — canonical; do not duplicate here.

For detailed RP app architecture, see `python/rp_app/ARCHITECTURE.md`. For GitHub Issues / Projects workflow (**§A–§K**, including **§B.0**–**§B.5** and **§B.2** verification), see [`../../governance/rp-app/issue-tracking-workflow.md`](../../governance/rp-app/issue-tracking-workflow.md) (Issue #45 governance relocation).

## Repo-level architecture stance

- Preserve existing module boundaries unless the task clearly requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid introducing parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless the task explicitly includes changing callers.

## Behavioral validation layer

Scenario validation is a **core architectural layer**: fixed JSON scenarios, headless runs on the **same turn loop and fresh-scene bootstrap** as Streamlit (GitHub **#83**), optional audit JSON, structured metrics (`structured_eval`), and baseline vs treatment (e.g. `--no-progression-enforcement` for progression). It answers whether a change **actually improved** emergent behavior, not only whether unit tests pass.

**Canonical spec:** [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md) (repo root). Do not churn that document without evidence from real runs; prefer executing the framework.

## RP app architecture rules

The RP app uses a Director + Narrator + continuity-manager architecture.

**Scene-start spine (GitHub #83):** **Fresh** scenes use one canonical continuity init/apply ordering (`scene_start_bootstrap`, `app_state_continuity.restore_or_initialize_continuity_manager`). Streamlit and headless simulation are **separate input surfaces** into that spine (UI flow vs scenario/CLI fields), not divergent template-application models. Template-derived setup merges on **first** continuity init; there is no second headless-only patch pass after partial startup. **Streamlit opener UI (GitHub #101, closed; #108; #113):** the **template** defines the available template-scoped **Opener** JSON set; the sidebar offers **template** and **custom** opening modes (legacy persisted `generated` values migrate on load; not `character_asset`). Multiple openers for the same **template** require an explicit pick before **Start Scene**; one opener auto-resolves. Composed `opening.strategy` / `opening.ref` and resolved prose flow through `bootstrap_composition` / `BootstrapInterpretation` with `scene_lifecycle_start.start_scene` (not a second bootstrap pipeline). Headless runs do not use Streamlit’s `selected_opener_id`; they use scenario/CLI inputs into the same composition spine.

### Core responsibilities

- Character agents produce self-only structured moves.
- Optional or model-supplied fields on the character move are **not** the authority boundary for **issues, tension trajectory, or consequences**; those are **continuity / Director / enriched history** concerns. Heuristic **Character Audit v1** metadata that keys off move-only fields measures **move-level expression / observability** on the parsed move, not full scene truth — see `python/rp_app/AUDIT_DOCUMENTATION.md` (*Character Audit v1*, including **Interpretation and Intended Use**).
- The Director selects who acts next.
- The Narrator renders prose and should preserve character dialogue verbatim.
- The continuity manager updates durable scene and issue state.
- Validation and enforcement should remain separate from prompt styling.
- **`perception_audibility.py`** is the authoritative gate for who may see **`dialogue`** and full narrator **`rendered`** for others’ beats in prompts; structured **`move`** (including optional **`audibility`** / **`audience`**) is the source of truth—narrator prose is not parsed for boundaries.

### Protected architectural intent

- Do not move long-horizon continuity responsibility back into prompts or transcript growth.
- Do not treat the Director prompt as the default fix for runtime failures.
- Keep `app.py` as a thin composition layer.
- Preserve bounded-context strategies rather than reintroducing unbounded hidden chat state.
- Preserve `must_remain` as structural presence, not a requirement to speak every beat.
- **Progression advisory (MVP)** is **advisory only**: it may add short Director/character prompt text and feed a **single** deterministic **`stall_score`** into beat-shift eligibility. It must **not** write continuity truth, mutate `CharacterState`, or add a parallel progression authority.
- **Progression enforcement** (`progression_enforcement.py`) may require a structural delta (Q1–Q4) after continuity `process_turn`; it **does not** classify moves. Empty or thin **`consequences`** on continuity turn metadata are corrected in **`continuity_consequence_classifier.py`** (deterministic rules, continuity still authoritative)—**not** by weakening the gate or editing Q1–Q4. REFUSAL **legacy** **`no` / `not`** dialogue matching uses **word boundaries** (standalone tokens), not raw substrings. See `python/rp_app/ARCHITECTURE.md` (*Progression enforcement vs continuity classification*).
- **Scene Grounding (MVP)** is a **read-only, prompt-facing** projection of **settled scene facts** derived **only** from continuity outputs and deterministic rules. It lives **after** continuity commits and **before** LLM prompts. It must **not** write continuity or `CharacterState` or act as a second authority (see [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8, [scene-grounding-layer.md](./scene-grounding-layer.md)).
- **Character prompts** add **BINDING CONSTRAINTS** (filtered subset of the same facts, high salience before OUTPUT RULES) and a static **EVIDENCE & AUTHORITY DISCIPLINE** block in `prompt_builders.py` (prompt-only stability; see `RP_SETUP_TODO.md` Phase 0 section H).

## Change strategy

Before making architecture-sensitive changes:

1. Identify the real layer involved.
2. Inspect likely downstream consumers.
3. Prefer the smallest fix that preserves the current design.
4. Update shared docs if the contract or expectation changes.

## RP audit diagnosis order

When debugging scene quality or continuity behavior, prefer this order (see also `docs/audit-workflows.md`):

1. continuity and state representation
2. **perception / audibility** when the symptom is impossible knowledge, leaked private lines, or per-character prompt mismatch (`perception_audibility.py`, `app_turn_prompting.py`, per-character `_full.json` prompts)
3. **scene grounding** (prompt projection: are settled facts present, stale, or missing?)
4. issue lifecycle and orchestration state
5. summary retrieval and compression
6. validation and enforcement boundaries
7. **memory layer (read path)** — episodic sections inside character `state_context` (`memory_layer/retrieval.py`); distinct from continuity truth
8. Director logic
9. Narrator rendering polish

This order mirrors the RP audit workflow and helps avoid prompt-first misdiagnosis.

---

## Validation layer (consolidated modules)

Runtime validation is split under `autogen_rp/python/rp_app/`:

- **`response_validation.py`** — stable facade re-exporting leaf modules.
- **`response_validation_parsing.py`** — JSON / move / Director decision parsing.
- **`response_validation_content.py`** — structural checks, duplicates, `validate_bot_response` orchestration.
- **`response_validation_drift.py`** — character drift / identity anchors.
- **`response_validation_presence.py`** — scene presence / `must_remain`-related checks.
- **`response_validation_selection.py`** — deterministic turn-selection checks (non-authoritative).

Validators **reject or annotate**; they do **not** replace Director selection or continuity commits. **Intentional pipeline order** inside `validate_bot_response`: **duplicate → drift → presence** (duplicate first as loop prevention).

Turn-selection checks include participant / availability, optional offstage cross-check, optional preemption invariants when kwargs are supplied, and **`end_round` + empty `next_actor`**. Preemption validation is **skipped** when the decision is marked fallback (`decision.get("source") == "fallback"` or truthy `is_fallback`). **Continuation preemption** (next actor must match `continuation_override_actor` when that actor is available) is **not** enforced when the **v1 C2** rule applies: last non-empty `spotlight_history` entry equals the continuation actor — then the runtime falls through to Director (`app_turn_director.py`) instead of the continuation hard route, and validation matches that policy.

## Director fallback marker (cross-layer contract)

On Director JSON **parse failure**, the built `decision` dict includes **`"source": "fallback"`**. Consumers (e.g. turn-selection validation) rely on this field; audit entries also record `is_fallback` / `parse_error` in **metadata** for the same event—metadata is supplementary; the **runtime contract** on the `decision` object is **`source`**.

## Memory layer (`memory_layer/`)

**Policy owner** for per-character episodic **writes** and **read/format** for prompts. **`CharacterState`** holds storage plus **identity/relationship** prompt text only (`to_prompt_identity_context`).

- **Phase A (writes):** `facade`, `writes`, `storage` — all commit-time episodic writes go through the facade; **`storage`** is the only path that calls `CharacterStateManager.remember_event`. **Observer** episodic lines are written only for names in **`event_knowledge_recipients`** after **`normalize_move_audibility`** (`perception_audibility.py`). **`present_characters`** for that pass: `continuity_manager.scene_state.present_characters` when non-empty, else the turn’s cast / `char_names`.

- **Phase B (reads):** `retrieval.py` — builds episodic prompt sections from **`character_memory_summary`** and **`recent_observations`**. The latter is a **legacy self-trace** source (e.g. `update_from_move`); it is included for **prompt parity**, not because it is the same conceptual bucket as interpretation summaries.

### Invariant: fallback vs memory

**Memory writes** follow **committed turns** only. They do **not** depend on validation rule type or rejection reasons. **`decision["source"] = "fallback"`** does **not** suppress or alter episodic memory writes for an otherwise committed turn. (Contrast: **turn-selection preemption validation** is skipped for fallback decisions—that is validation-only, not memory policy.)

## `state_context` contract (cross-layer)

For **production** character turn prompts:

- **`state_context`** is a **single composed string** passed into **`prompt_builders.build_character_turn_prompt`**.
- It is **assembled only** in **`app_turn_prompting.build_character_turn_prompt`** via **`build_character_state_context_for_prompt`** (`memory_layer.retrieval`), which combines **`CharacterState.to_prompt_identity_context(...)`** with episodic sections from retrieval.
- **`prompt_builders`** must **not** re-read `character_memory_summary` or `recent_observations` from `CharacterState`; they insert **`state_context`** into the template **unchanged**.

**Streamlit** (`app.py` → `app_turn_helpers` → `app_turn_prompting`) and **headless simulation** (`headless_scene_simulation` → same `turn_helpers.build_character_turn_prompt`) use this **same** spine. Unit tests may pass a synthetic `state_context` directly into `prompt_builders` to test template shape in isolation—that is not a second runtime path.

## Runtime packet seam (Phase 0.5 + Phase 2 retrieval)

**Purpose:** Introduce **read-only** runtime packets (`RuntimeScenePacket`, `RuntimeCharacterPacket`, `RetrievedContextBundle`) and **structured** parity checks. **Phase 0.5 (character path, complete):** **`CharacterPromptInputAssembly`** is the **single** assembled snapshot of everything needed for **`prompt_builders.build_character_turn_prompt`** (the **seam boundary** for that path). **`live_bundle_from_character_prompt_assembly`** and **`runtime_packets_from_character_prompt_assembly`** both read that assembly only (no dual derivation). **Phase 2** wires **authored-index-only** retrieval (still non-authoritative).

- **Headless validation checkpoint (2026-04-07):** After GitHub **#24**, scenario runs with audits **`session_388`–`session_393`** sampled character prompts for cast/roster integrity — **no regression** on that evidence (**`SCENARIO_VALIDATION_FRAMEWORK.md`**).

- **Phase 2–3.1 retrieval:** **JSON index** (`RP_RETRIEVED_CONTEXT_INDEX`, `schema_version` 2 with optional **`lore`**). **Offline compile:** **`authored_index_compile.compile_authored_index`** from a **manifest** (CLI: **`scripts/compile_authored_retrieval_index.py`**). **Deterministic** selection in **`retrieved_context_select.py`**, invoked **only** from **`app_turn_prompting.build_character_turn_prompt`**. Bundle attaches to **`RuntimeCharacterPacket.retrieved`**; primary lane: template → setup → world_lore → self (`character_local` only) → relationship; per-kind subcaps; lore truncation at selection. Prompt section is **after** scene grounding and **before** `CURRENT SCENE STATE`, with explicit **non-authoritative** wording. **Not** vector/graph retrieval or transcript/dynamic-memory sourcing.
- **Authored retrieval — baseline + standard eval (Phase 4A):** **Accepted** index content is **character `lore_facts` + template `role_slots` + `premise`**. **Headless** sets **`scene_template_id`** via **`prepare_headless_session`**, scenario JSON, and **`run_scene_simulation_llm.py --scene-template-id`**, matching Streamlit. **OFF/ON** for validation: **`RP_RETRIEVED_CONTEXT_INDEX`** (optional **`--retrieved-context-index`**); audits: **`retrieval_summary`** / **`retrieval_session`** — see **`rp_app/AUDIT_DOCUMENTATION.md`**. **Historical pilot** + **rejected situational cap** in **`OPERATIONAL_RETRIEVAL_PILOT.md`** / **`RP_SETUP_TODO.md`**. Selector: **fixed subcaps** only.
- **Shadow-only (compare):** Default **off**. Set **`RP_PACKET_SHADOW_COMPARE`** to `1`, `true`, or `yes` to compare live vs reconstructed **prompt-input bundles** (kwargs for `prompt_builders.build_character_turn_prompt`), including **`retrieved_context_section`**. Reconstruction **`reconstruct_character_prompt_input_bundle`** must use the same **`get_character_display_name_fn`** as live assembly so **cast** / others lists treat **id and display** as the same character (matches **`prompt_builders.build_cast_and_scene_role_participants`**). When bundles match structurally, an optional **core prompt-text** comparison runs (same builder call; beat-shift / progression suffixes excluded from that check). Mismatch → **`rp_app.packet_shadow`** warning + optional debug string diff (**stderr**; **not** persisted in audit JSON today). **No** writes to continuity or character state from shadow compare. **Scope:** **character** prompts only — Director and Narrator are **not** on this assembly path yet.
- **Phase 1 (scoped retrieval-lock / validation — complete):** **`RetrievedContextBundle`** on **`CharacterPromptInputAssembly`** is the **behavioral source** for retrieval in the seam; **`retrieved_context_section`** is **pure derived** formatting (**assembly invariant**: section == `format_retrieved_context_for_prompt(bundle)`). Inventory: **no seam bypass**. **Golden/snapshot** tests stabilize bundle composition; **prompt-shape invariance** and **authority** placement tests document current `build_character_turn_prompt` layout. **`RP_PACKET_SHADOW_COMPARE=1`** on retrieved / runtime_packets / perception / episodic prompt tests — **green**. **No** new retrieval lanes, selector branches, graph/vector path, or Director retrieval expansion in this phase.
- **Authority:** **Continuity** and **`CharacterState`** stay authoritative; packets and retrieved snippets are **projections / assistive reference** only (`runtime_packets.py`, `retrieved_context_select.py`).
- **Implementation note:** **`prompt_derivations.py`** holds shared relationship ordering and priority-ladder logic used by both the live path and packet reconstruction (avoids circular imports).
