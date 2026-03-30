# Audit Workflows

This document turns important audit guidance into a shared repo procedure.

For artifact details, see `python/rp_app/AUDIT_DOCUMENTATION.md`.

## When to use this

Use this workflow for:

- RP continuity drift
- weak story progression
- stalled scenes
- selection or soft-dropout issues
- false validation or presence behavior
- render-layer anomalies

## Audit posture

- Start from the assumption that visible failure may be downstream of earlier signal loss.
- Do not default to Director prompt edits.
- Prefer the smallest correct fix at the correct layer.
- Do not propose new subsystems unless the user explicitly asks for them.

## Artifact reading order

For session audits, read in this order:

1. `python/rp_app/data/rp_audits/session_{###}/_audit_summary.json`
2. `python/rp_app/data/rp_audits/session_{###}/_narrative.json`
3. `python/rp_app/data/rp_audits/session_{###}/_round_index.json`
4. relevant per-turn `_full.json` artifacts

## What to inspect first

- whether turns produce meaningful `state_changes`
- whether `actionable_implications` describe actual next pressure or opportunity
- whether `issue_updates` reflect pressure movement rather than dialogue paraphrase
- whether `presence_changes` match true entries, exits, and absences
- whether summary blocks preserve important context or hide it
- whether `_audit_summary.json` `progression_analysis` matches the runtime's classification, debt, reset, plateau, and identity-continuity behavior

For issue updates, pay special attention to:

- `pressure_kind`
- `blocked_what`
- `required_next_step`
- `status_reason`

## Diagnosis order

Use the same layer order as `docs/architecture.md`:

1. continuity and state representation
2. issue lifecycle and orchestration state
3. summary retrieval and compression
4. validation and enforcement
5. Director logic
6. Narrator rendering

For progression-specific reviews, add this check between steps 2 and 3:

- verify `progression_analysis` mismatches, reset errors, plateau assessment, pressure targeting, and fragmentation events before changing prompts

## Relevant code areas for RP audits

Start with these files when the audit points to runtime behavior:

- `python/rp_app/continuity_manager.py`
- `python/rp_app/turn_runner.py`
- `python/rp_app/turn_runner_turn.py`
- `python/rp_app/turn_runner_updates.py`
- `python/rp_app/turn_runner_audit.py`
- `python/rp_app/app_turn_director.py`
- `python/rp_app/orchestration_helpers.py`
- `python/rp_app/prompt_builders.py`
- `python/rp_app/response_validation.py`
- `python/rp_app/audit_logger.py`

## Windsurf-only note

The repo also contains a Windsurf workflow at:

- `.windsurf/workflows/audit-continuity-review.md`

That file can remain as Windsurf automation, but this document is the shared procedure both Windsurf
and Cursor should follow.
