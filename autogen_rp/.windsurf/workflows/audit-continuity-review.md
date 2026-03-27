---
description: Run a continuity-aware RP audit that diagnoses the full pipeline before recommending changes
---

# Audit Continuity Review

Use this workflow when auditing RP scene quality, pacing, looping, continuity drift, orchestration failures, or weak progression.

Goal: produce recommendations that target the correct layer of the system instead of defaulting to `python/rp_app/model_client.py` or other Director-only prompt changes.

## Required audit posture

- Start from the assumption that the visible failure may be downstream of earlier signal loss.
- Do not treat the Director as the default root cause.
- Do not recommend Director prompt changes unless upstream state representation, continuity extraction, issue lifecycle handling, summary retrieval, and enforcement boundaries have already been checked.
- Prefer the smallest correct fix at the correct layer.
- Do not propose new subsystems or architectural expansion unless the user explicitly asks for that.

## Step 1: Identify the session and read the audit artifacts in the correct order

1. Locate the relevant session under `python/data/rp_audits/session_{###}/`.
2. Read `python/rp_app/AUDIT_DOCUMENTATION.md` if you need to confirm artifact meanings.
3. Read these artifacts in this order:
   - `_audit_summary.json`
   - `_narrative.json`
   - `_round_index.json`
   - relevant per-turn `_full.json` files for Director, character, and narrator
4. Summarize:
   - the visible scene failure
   - the rounds/turns where it becomes clear
   - whether the failure is a pacing problem, continuity problem, issue-lifecycle problem, selector problem, rendering problem, or a mix

## Step 2: Audit the continuity and orchestration signals before the prompts

From the audit files, explicitly evaluate:

- whether turns produce meaningful `state_changes`
- whether `state_changes` describe actual world, constraint, pressure, access, presence, or option changes rather than paraphrased speech
- whether turns produce meaningful `actionable_implications`
- whether `actionable_implications` are consequence-shaped next pressures or openings rather than dialogue restatements
- whether `continuity_event_type` reflects what materially changed
- whether `continuity_event_type` is consequence-shaped rather than just a dialogue-shaped paraphrase of the exchange
- whether `scene_recent_delta` tracks the consequential change rather than just dialogue
- whether `issue_updates` show escalation, reinforcement, stalling, or resolution at the right times
- whether `presence_changes` and scene presence state reflect exits, entries, and absences correctly
- whether `summary_block_visibility` / `summary_block_quality` suggest prompt compression is helping or hiding important context
- whether rounds drift into low-change beats despite active unresolved pressure

If the audit shows dialogue-heavy turns with weak material change signals, treat that as evidence against a Director-first diagnosis.

## Step 3: Review the full pipeline in code before recommending fixes

Inspect the moving parts that shape scene progression. At minimum, review the relevant portions of:

- `python/rp_app/continuity_manager.py`
- `python/rp_app/continuity_issue_helpers.py`
- `python/rp_app/continuity_summary_helpers.py`
- `python/rp_app/continuity_scene_helpers.py`
- `python/rp_app/continuity_state.py`
- `python/rp_app/app_turn_director.py`
- `python/rp_app/app_turn_prompting.py`
- `python/rp_app/orchestration_helpers.py`
- `python/rp_app/character_state_manager.py`
- `python/rp_app/turn_runner_turn.py`
- `python/rp_app/turn_runner_updates.py`
- `python/rp_app/turn_runner_audit.py`
- `python/rp_app/prompt_builders.py`
- `python/rp_app/model_client.py`
- `python/rp_app/audit_logger.py`
- `python/rp_app/audit_logger_writers.py`
- `python/rp_app/audit_logger_summary_rounds.py`
- `python/rp_app/audit_logger_summary_output.py`

Also inspect any directly implicated validator or scene-template files if the audit points there.

## Step 4: Diagnose by layer

For each observed failure, classify the most likely intervention layer:

1. `continuity/state representation`
   - Missing or weak state transitions
   - Consequences not being extracted
   - Presence or scene deltas not being updated

2. `issue lifecycle / orchestration state`
   - Pressure not being created
   - Issues not escalating, resolving, or stalling correctly
   - Active issues not matching the true scene state

3. `summary/retrieval/compression`
   - Important older state is not reaching prompts
   - Summary blocks compress speech but miss consequences

4. `validation / enforcement boundary`
   - The system detects the problem but does not stop or correct it
   - Must-remain, direct-address, or authority constraints are weakly enforced

5. `Director decision logic`
   - Only use this category after checking the earlier layers
   - Use only when the Director clearly received good, consequence-rich signals but still made the wrong choice
   - Do not classify a failure here unless the audit shows the Director received clear, consequence-rich signals and still selected the wrong beat

6. `Narrator or rendering layer`
   - The underlying move is sound but the final prose introduces drift or repetition

## Step 5: Produce recommendations in the right order

When recommending changes:

1. List the root cause by layer.
2. State the smallest correct fix.
3. Identify which files should change.
4. Identify likely downstream consumers affected by that change.
5. Explicitly justify why the recommendation should not start in the Director layer if that is your conclusion.

If multiple fixes are needed, order them like this unless the evidence clearly says otherwise:

1. continuity/state extraction
2. issue lifecycle/orchestration state
3. summary retrieval/compression
4. validation/enforcement
5. Director prompt/rules
6. narrator/render polish

## Step 6: Output format

Return the audit result using this structure:

### Findings

- visible failure
- strongest evidence from the audit artifacts
- earliest turn where the failure becomes structurally clear

### Root cause by layer

- continuity/state representation
- issue lifecycle/orchestration
- summary/retrieval
- validation/enforcement
- Director logic
- narrator/rendering

### Recommended fixes

- file(s)
- reason for change
- why this is the correct layer
- why earlier or later layers are not the primary fix

### Validation plan

- focused tests to run
- audited scenario(s) to rerun
- what success would look like in `_audit_summary.json` and `_narrative.json`
- increased rate of meaningful non-empty `state_changes`
- more outcome-focused `scene_recent_delta`
- reduced dialogue-only `continuity_event_type` patterns
- fewer stalled issues surfaced as actionable pressure when they should no longer drive the scene

## Important anti-patterns

Avoid these failure modes in the audit:

- recommending Director prompt edits before checking continuity state and issue signals
- treating repeated dialogue as a prompt-style problem without checking whether the system produced any real change signals
- recommending architecture changes when a targeted fix to existing continuity or audit wiring would solve it
- ignoring role, presence, or authority metadata when scene templates are active
- assuming role changes in audit artifacts are user error rather than a bug
- filling out the workflow sections without tracing evidence across audit artifacts and code
