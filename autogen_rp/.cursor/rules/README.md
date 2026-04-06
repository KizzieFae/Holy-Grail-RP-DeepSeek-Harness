# Cursor Rules

These rules are a thin compatibility layer for using Cursor on this repository.

## Purpose

The files in this folder are not intended to be the primary source of project behavior.
Their job is to route Cursor into the shared repo docs that both Windsurf and Cursor can read.

## Source of truth

Maintain this priority order:

1. direct user request
2. `AGENTS.md`
3. shared docs in `docs/`
4. task-specific docs such as `python/README.md` and `python/rp_app/*.md`
5. files in `.cursor/rules/`

If a rule here conflicts with a shared repo doc, update the Cursor rule to match the repo doc.
Do not let important project behavior live only in this folder.

## Maintenance guidance

- keep these rules concise
- prefer references to shared docs over copied rule blocks
- preserve existing architecture and patterns unless the user explicitly asks otherwise
- update shared docs first when project behavior materially changes
- update Cursor rules only when routing or emphasis needs to change

## Current rule set

- `project-behavior.mdc` - repo-wide working behavior and shared-doc routing
- `architecture-protection.mdc` - architecture guardrails for Python and RP app work
- `testing-expectations.mdc` - test expectations for Python changes
- `rp-app-guidance.mdc` - RP app-specific runtime and audit guidance
- `github-issues.mdc` - file Issues on GitHub via `gh` when requested; canonical steps in `python/rp_app/ARCHITECTURE.md` §B.1

## Safe switching note

When switching from Windsurf to Cursor, re-read:

- `AGENTS.md`
- `docs/repo-map.md`
- `docs/code-style.md`
- `docs/testing.md`
- `docs/architecture.md`
- `docs/audit-workflows.md`

If the task touches the RP app, also read:

- `python/rp_app/README.md`
- `python/rp_app/ARCHITECTURE.md`
- `python/rp_app/AUDIT_DOCUMENTATION.md`
- `python/RP_SETUP_TODO.md`
