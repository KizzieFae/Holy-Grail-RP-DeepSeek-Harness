# Architecture Guidance

This document captures architecture guardrails that both Windsurf and Cursor should follow.

For detailed RP app architecture, see `python/rp_app/ARCHITECTURE.md`.

## Repo-level architecture stance

- Preserve existing module boundaries unless the task clearly requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid introducing parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless the task explicitly includes changing callers.

## Behavioral validation layer

Scenario validation is a **core architectural layer**: fixed JSON scenarios, headless runs on the same path as Streamlit, optional audit JSON, structured metrics (`structured_eval`), and baseline vs treatment (e.g. `--no-progression-enforcement` for progression). It answers whether a change **actually improved** emergent behavior, not only whether unit tests pass.

**Canonical spec:** [SCENARIO_VALIDATION_FRAMEWORK.md](../../SCENARIO_VALIDATION_FRAMEWORK.md) (repo root). Do not churn that document without evidence from real runs; prefer executing the framework.

## RP app architecture rules

The RP app uses a Director + Narrator + continuity-manager architecture.

### Core responsibilities

- Character agents produce self-only structured moves.
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
- **Scene Grounding (MVP)** is a **read-only, prompt-facing** projection of **settled scene facts** derived **only** from continuity outputs and deterministic rules. It lives **after** continuity commits and **before** LLM prompts. It must **not** write continuity or `CharacterState` or act as a second authority (see [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) §5.8, [scene-grounding-layer.md](./scene-grounding-layer.md)).

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

Turn-selection checks include participant / availability, optional offstage cross-check, optional preemption invariants when kwargs are supplied, and **`end_round` + empty `next_actor`**. Preemption validation is **skipped** when the decision is marked fallback (`decision.get("source") == "fallback"` or truthy `is_fallback`).

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
