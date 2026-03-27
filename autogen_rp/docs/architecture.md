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

### Protected architectural intent

- Do not move long-horizon continuity responsibility back into prompts or transcript growth.
- Do not treat the Director prompt as the default fix for runtime failures.
- Keep `app.py` as a thin composition layer.
- Preserve bounded-context strategies rather than reintroducing unbounded hidden chat state.
- Preserve `must_remain` as structural presence, not a requirement to speak every beat.

## Change strategy

Before making architecture-sensitive changes:

1. Identify the real layer involved.
2. Inspect likely downstream consumers.
3. Prefer the smallest fix that preserves the current design.
4. Update shared docs if the contract or expectation changes.

## RP audit diagnosis order

When debugging scene quality or continuity behavior, prefer this order:

1. continuity and state extraction
2. issue lifecycle and orchestration state
3. summary retrieval and compression
4. validation and enforcement boundaries
5. Director logic
6. Narrator rendering polish

This order mirrors the existing RP audit workflow and helps avoid prompt-first misdiagnosis.
