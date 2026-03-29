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

### Offstage / membership / eligibility / perceptual scope (checklist)

Treat **`present_characters` as cast membership** for orchestration, not literal sensory co-presence. **On-stage** for a beat means present and **not** listed in **`offstage_characters`**.

When replaying a session or reading per-turn audits, verify:

1. **Slot-filling / Director input**
   - After a justified offstage transition, **`offstage_characters`** in structured scene state (or equivalent continuity snapshot) includes the expected name(s) while they remain in **`present_characters`** if `must_remain` or cast retention applies.
   - **`available_next_actors`** (or the Director payload field that mirrors it) **does not** list offstage names unless the same round already cleared offstage (e.g. direct-address / forced speaker, Traveler re-entry wording, or embodied re-entry in the move).
   - When only offstage characters would be left to speak and the beat does not require an offstage line, the Director or cycle should prefer **`end_round`** over inventing a third on-stage speaker.

2. **User-authored exits and routing**
   - Traveler text that clearly exits a character (left, garage, out of the room, etc.) should move **`offstage_characters`** **before** turn selection for that user message’s bot cycle, so the same cycle does not default-route that character without justification.
   - **Audit caveat:** user-trigger exit matching is applied per mentioned cast name against **whole-message** exit/re-entry cues. A single line that names multiple characters and also contains exit-like wording for only one of them can produce **false offstage** for others; flag those for `user_presence_signals` tuning rather than Director-only fixes.

3. **Knowledge / prompt assembly**
   - For a character turn audit while offstage: character prompt (or redacted snapshot) should include the **OFFSTAGE / PERCEPTUAL SCOPE** block and **filtered** recent dialogue / structured moves (Traveler + self), not full in-room lines from other assistants—unless a separate mechanism explicitly granted remote perception.

4. **Re-entry conservatism**
   - Offstage clears only when evidence matches **user re-entry phrasing**, **embodied re-entry** in the character move, structured **entry** consequence, or **forced-speaker** release—not from vague proximity or motivation-only intent.

5. **False exits**
   - If **`detect_exit_from_scene`** misfires, expect a **wrong offstage** flag rather than silent removal from **`present_characters`**. Flag those cases as **continuity/state representation** or **exit-detection tuning**, not Director-only fixes.
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
- `python/rp_app/turn_runner.py`
- `python/rp_app/user_presence_signals.py`
- `python/rp_app/offstage_prompt_filter.py`
- `python/rp_app/scene_exit_detection.py`
- `python/rp_app/response_validation_selection.py`
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
   - Confusing **membership** (`present_characters`) with **literal on-stage presence**; missing or incorrect **`offstage_characters`** relative to the fiction

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

- focused tests to run (including `python/tests/test_offstage_presence.py` and offstage routing integration coverage)
- audited scenario(s) to rerun
- what success would look like in `_audit_summary.json` and `_narrative.json`
- increased rate of meaningful non-empty `state_changes`
- more outcome-focused `scene_recent_delta`
- reduced dialogue-only `continuity_event_type` patterns
- fewer stalled issues surfaced as actionable pressure when they should no longer drive the scene
- **offstage-specific:** offstage characters do not appear in **`available_next_actors`** for the same user cycle after a clear Traveler exit unless re-entry or forced address applies; character-turn artifacts show **OFFSTAGE** scope text and **narrowed** dialogue/move context; no systematic **in-room omniscience** for offstage speakers across multiple replay rounds

## Important anti-patterns

Avoid these failure modes in the audit:

- recommending Director prompt edits before checking continuity state and issue signals
- treating repeated dialogue as a prompt-style problem without checking whether the system produced any real change signals
- recommending architecture changes when a targeted fix to existing continuity or audit wiring would solve it
- ignoring role, presence, or authority metadata when scene templates are active
- assuming role changes in audit artifacts are user error rather than a bug
- filling out the workflow sections without tracing evidence across audit artifacts and code
