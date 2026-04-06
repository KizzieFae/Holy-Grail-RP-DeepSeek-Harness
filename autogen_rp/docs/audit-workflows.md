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
- **Authored retrieval (standard eval):** On **headless** audited runs, check `_audit_summary.json` → **`retrieval_session`** (`retrieval_mode`, `retrieval_verified_active`, index path/fingerprint) when present; on **any** audited character turn, `metadata` may include **`retrieval_summary`** (counts/refs only). See `python/rp_app/AUDIT_DOCUMENTATION.md` (*Authored index retrieval*) and repo-root `SCENARIO_VALIDATION_FRAMEWORK.md`. Run-level `retrieval_session` in `_audit_summary` is **headless-oriented** today.
- **Perception / audibility:** for whisper or directed beats, compare **this character’s** assembled prompt (or audit snapshot) to the **parsed `move`** (`audibility`, `audience`, `dialogue`). Non-recipients must not see verbatim private **`dialogue`** in transcript, structured moves, `PublicEvent.summary`, or interpretations; Director payload must use the same redaction rules.
- **`metadata.character_audit_v1`:** **`issue_engagement`** and **`pressure_move`** depend on fields **optional** on the character move. Empty move-level issue/tension/consequence fields are **expected** under the current contract; interpret CA3/CA7 as **visibility of those keys on the move**, not as proof the beat ignored continuity pressure (check **`_narrative.json`** and Director/continuity artifacts). See `python/rp_app/AUDIT_DOCUMENTATION.md` (*Character Audit v1*).

For issue updates, pay special attention to:

- `pressure_kind`
- `blocked_what`
- `required_next_step`
- `status_reason`

## Diagnosis order

Use the same layer order as `docs/architecture.md`:

1. continuity and state representation
2. **perception / audibility** (`perception_audibility.py` and prompt assembly) when the failure is impossible knowledge or leaked private lines
3. **scene grounding** (settled-facts projection vs continuity) when the failure is repeated logistics or missing/stale SETTLED SCENE FACTS
4. issue lifecycle and orchestration state
5. summary retrieval and compression
6. validation and enforcement
7. Director logic
8. Narrator rendering

## Relevant code areas for RP audits

Start with these files when the audit points to runtime behavior:

- `python/rp_app/continuity_manager.py`
- `python/rp_app/perception_audibility.py`
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
