# AGENTS.md

This file is the repo-level source of truth for AI assistants working in this repository.

Use this document together with the files in `docs/` before making multi-file, architectural,
workflow, or audit-sensitive changes.

## Instruction priority

1. Direct user request
2. This file
3. Shared repo docs in `docs/`
4. Existing package- or app-specific docs such as `python/README.md` and `python/rp_app/*.md`
5. Tool-specific features such as Windsurf workflows or Cursor rules

Do not rely on tool memory as the only source of important project behavior.

## Repo working rules

- Preserve existing architecture and patterns unless the user explicitly asks for a redesign.
- Prefer small, reviewable diffs over broad rewrites.
- Focus on files relevant to the task.
- Do not change unrelated code just because it is nearby.
- Prefer extending existing modules and workflows before inventing new ones.
- Keep important guidance in repo files, not only in tool-specific settings.
- If code behavior, architecture constraints, or test expectations change, update the relevant docs.
- Do not overwrite environment or secret files without explicit user confirmation.

## Where to start

- For **Holy Grail** product architecture and packet intent (workspace parent): `../MODULE_INDEX.md`, `../ARCHITECTURE_OVERVIEW.md`, `../DEBUGGING_GUIDE.md`, `../PACKET_CONTRACTS.md`, `../GLOSSARY.md`, and `../Holy Grail PRD.md`.
- Read `docs/repo-map.md` for repo structure.
- Read `docs/rp-data-layout.md` for RP on-disk data (characters, sessions, audits).
- Read `docs/code-style.md` for change-scope and coding expectations.
- Read `docs/testing.md` before changing Python code (includes Holy Grail default `pytest` scope and optional vendored-package test deps).
- Read `docs/architecture.md` before touching `python/rp_app/` or other core workflow code.
- Read `docs/audit-workflows.md` before auditing RP sessions or diagnosing continuity issues.

## Active project areas

This repository is a large AutoGen monorepo. For local work in this fork, the most actively customized
area is usually `python/rp_app/`.

If a task touches the RP app, also read:

- `../MODULE_INDEX.md` (file-level map; canonical at repo root)
- `../Holy Grail PRD.md` (product intent, including **Progression Advisory MVP** in §5.7 and **Scene Grounding MVP** in §5.8)
- `docs/scene-grounding-layer.md` (Scene Grounding: facts contract, lifecycle, prompt integration — under `autogen_rp/`)
- `python/rp_app/README.md`
- `python/rp_app/ARCHITECTURE.md`
- `python/rp_app/AUDIT_DOCUMENTATION.md`
- `python/RP_SETUP_TODO.md`

**Progression layer (current):** the implemented structural layer is **signal-based** and derives scene / issue progression classification, debt, instability tiers, dominant pressure ids, and issue-identity continuity notes from existing continuity-owned signals. Runtime state lives in `python/rp_app/progression_pressure.py` and orchestration integration spans `orchestration_helpers.py`, `turn_runner_updates.py`, `app_turn_director.py`, `app_turn_prompting.py`, `prompt_builders.py`, `turn_runner_audit.py`, and audits. It does **not** write continuity truth or `CharacterState`.

**Progression advisory (legacy support layer):** `python/rp_app/progression_advisory.py` still provides deterministic `stall_score`-based prompt hints plus the shared beat-shift hook, but it is no longer the only progression mechanism.

**Current project phase:** **Manual behavioral validation**. Progression design, implementation, deterministic simulation tests, and audit verification are complete. Current live-scene watch areas are:

- issue identity continuity still relies on exact structured fingerprint transfer when issue ids change
- early scene reset behavior should be watched until dominant pressure is clearly established

## Tool-specific compatibility

### Windsurf

Windsurf-specific automation may exist under `.windsurf/`, especially workflows. Keep those files if
they still provide useful IDE automation, but do not let them become the only source of critical rules.

### Cursor

Cursor should use `.cursor/rules/` only as a routing layer into this file and the shared docs in `docs/`.
Avoid duplicating large rule blocks in Cursor-only files when a shared repo doc can hold the guidance.

## Safe switching rule

When switching between Windsurf and Cursor:

- treat repo files as authoritative
- re-read this file and the relevant docs for the task
- do not assume tool memory contains the latest architecture or workflow decisions
- keep tool-specific rules thin and aligned to the shared docs
