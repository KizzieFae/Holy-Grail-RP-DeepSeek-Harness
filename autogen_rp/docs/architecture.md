# Architecture Guidance

This document captures architecture guardrails that both Windsurf and Cursor should follow.

For detailed RP app architecture, see `python/rp_app/ARCHITECTURE.md`.

## Repo-level architecture stance

- Preserve existing module boundaries unless the task clearly requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid introducing parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless the task explicitly includes changing callers.

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

When debugging scene quality or continuity behavior, prefer this order:

1. continuity and state extraction
2. **scene grounding** (prompt projection: are settled facts present, stale, or missing?)
3. issue lifecycle and orchestration state
4. summary retrieval and compression
5. validation and enforcement boundaries
6. Director logic
7. Narrator rendering polish

This order mirrors the existing RP audit workflow and helps avoid prompt-first misdiagnosis.
