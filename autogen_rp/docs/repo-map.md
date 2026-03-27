# Repo Map

This file is a quick orientation guide for humans and AI tools.

## Top level

- `README.md` - upstream AutoGen overview
- `CONTRIBUTING.md` - contribution process and repo-wide development expectations
- `AGENTS.md` - repo-level AI working rules and source-of-truth entrypoint
- `docs/` - shared AI-compatible project guidance for Windsurf and Cursor
- `.windsurf/` - Windsurf-only automation and workflow files
- `.cursor/rules/` - Cursor-only routing rules that should reference shared docs
- `python/` - Python workspace and the main area for this fork's RP app work
- `dotnet/` - .NET packages and docs

## Python workspace

- `python/README.md` - Python development guide, setup, format/lint/test commands
- `python/RP_SETUP_TODO.md` - RP app roadmap and phase tracking
- `python/rp_app/` - Streamlit-based multi-character RP application and its tests/supporting code
- `python/tests/` - Python test suite, including RP app regression tests
- `python/data/` - character data, scene templates, sessions, and RP audit artifacts
- `python/packages/` - upstream AutoGen package sources

## RP app docs and anchors

- `python/rp_app/README.md` - runtime overview and module layout
- `python/rp_app/ARCHITECTURE.md` - authoritative RP architecture notes
- `python/rp_app/AUDIT_DOCUMENTATION.md` - audit artifact meanings and review procedure
- `python/rp_app/CHARACTER_MIGRATION_GUIDE.md` - character-card migration guidance

## Most likely files for RP runtime work

- `python/rp_app/app.py` - thin app entrypoint/composition layer
- `python/rp_app/turn_runner.py` - round orchestration entrypoint
- `python/rp_app/turn_runner_turn.py` - single-turn execution path
- `python/rp_app/turn_runner_updates.py` - post-turn continuity/orchestration updates
- `python/rp_app/continuity_manager.py` - durable narrative state updates
- `python/rp_app/app_turn_director.py` - Director selection logic
- `python/rp_app/prompt_builders.py` - prompt assembly
- `python/rp_app/response_validation*.py` - validation boundaries
- `python/rp_app/audit_logger*.py` - audit artifact generation

## Working assumption

If the user asks about audits, continuity, Director behavior, Narrator behavior, scene templates, or RP
runtime bugs, start in `python/rp_app/` and its docs before touching broader AutoGen packages.
