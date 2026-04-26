# RP App Prototype

A Streamlit-based multi-character roleplay system using AutoGen.

## Current Architecture

- Character agents produce structured self-only moves with `action`, `dialogue`, and `motivation`
- A Director agent decides who acts next from structured scene state
- A Narrator agent renders character moves into scene prose
- Character dialogue is preserved verbatim during narration
- Each character keeps private state, identity anchors, and interpretation summaries
- **Phase 0.5 — packet seam (character path, complete):** **`CharacterPromptInputAssembly`** + `live_bundle_from_character_prompt_assembly` / `runtime_packets_from_character_prompt_assembly` in `runtime_packets.py`; **`RP_PACKET_SHADOW_COMPARE`** enables bundle parity (+ optional core prompt-text check, stderr logging — not audit-persisted). Director/Narrator not on this path yet. See `ARCHITECTURE.md` and `autogen_rp/docs/architecture.md`.

## Operating Rules

- Active LLM-controlled participants are the selected scene characters
- The user is present in-scene but remains separate from the LLM actor pool while directly controlled
- Any character-profile, including the user's persona if represented as a character card, may be either player-controlled or bot-controlled per scene, but never both at once
- A player-controlled character does not make an LLM call, and the user's post ends the round
- Default bot replies per user turn equals the number of active bot participants; the cap is **derived** from the selected NPC count (set at Start Scene / session load), not configured in the primary scene setup UI (GitHub **#103**)
- The same character should not act twice in the same response cycle
- Ending a scene saves and closes it; starting a new scene closes the current one first; interrupted active sessions are finalized on next startup

## Why continuity work is next

The app already keeps prompts smaller than a raw transcript-driven chat loop by using bounded model
contexts, recent dialogue windows, and recent structured move windows.

The next problem to solve is continuity quality, not just token count. Over long scenes, continuity is
still spread across recent dialogue, lightweight scene state, and ad-hoc character summaries.

That leads to the failure modes seen in long sessions:

- repetition and stalled scenes
- weak resolved vs unresolved pressure tracking
- temporary tactics becoming sticky identities
- viewpoint collapse when public facts and private interpretations blur together

The next architectural step is therefore a continuity engine that converts transient dialogue into
durable narrative state.

## Continuity-engine direction

The planned continuity model is:

- durable structures:
  - scene state
  - issue / pressure state
  - public event memory
  - character interpretation memory
  - canon anchors
- prompt policy:
  - keep only a small rolling dialogue window in prompts
  - promote important developments into structured continuity instead of carrying long dialogue logs

This keeps dialogue ephemeral while preserving the story state that actually matters.

## Quick Start

1. **Ensure DeepSeek API key is set:**

   ```powershell
   $env:DEEPSEEK_API_KEY = "your-api-key-here"
   ```

2. **Run the app:**

   ```bash
   streamlit run python/rp_app/app.py
   ```

3. **Use the interface:**
   - Choose your character as either a custom persona (name only) or a predefined character
   - For a **new** scene, the **NPC** multiselect starts **empty**; select one or more bot characters, then use **Start Scene** (GitHub **#104**)
   - **Load Session** restores a saved run’s cast as before; headless / scenario / bootstrap entry points are unchanged
   - Optionally choose a scene template and assign each selected character to an explicit role
   - For **template-asset** opening mode, pick an **Opener** when more than one exists for that **template** (a single opener is auto-selected; see **`ui_sidebar_opening`**, GitHub **#101**; **`character_asset`** is not used on Streamlit Start Scene—**#108**)
   - Click "Start Scene" to begin
   - Type your messages in the chat input
   - Bot-controlled characters respond dynamically; the per-round cap matches the selected cast size (see **Operating Rules** above; **#103**)
   - **Runtime / evaluation** (retrieval index, episodic memory flag, template hints): there is no in-app debug panel for these (**#105**). Use **env** (e.g. `RP_RETRIEVED_CONTEXT_INDEX`, `RP_EPISODIC_MEMORY`), **audits** when audit is enabled, or **headless** runs. **Audit logging** for the scene is still toggled in **scene setup** in the sidebar.
   - Sessions auto-save after each turn

## Scene Templates V1

Scene templates are a minimal first-pass scene setup asset for multi-character stability.

Templates live in:

`python/data/scene_templates/*.json`

Current V1 schema:

```json
{
  "template_id": "household_entry_evaluation",
  "premise": "A newcomer is evaluated while the host and guard remain present.",
  "opening_text": "The household receives a newcomer inside a controlled interior space...",
  "role_slots": [
    {
      "role_name": "host",
      "required": true,
      "presence_constraint": "must_remain",
      "authority": "high"
    }
  ]
}
```

`opening_text` is an **optional** on-disk field (legacy / compatibility). For **Start Scene** in **template-asset** mode, the Streamlit app resolves opening prose from **Opener** JSON assets and the sidebar (explicit selection when multiple openers exist for the **template**—**GitHub #101**); **`character_asset`** is for **authored** scenario/bootstrap, **headless** / CLI, and **legacy** paths, not the Streamlit opening UI (**#108**). It does not inject template card `opening_text` as the primary source for that path. See **[AUTHORED_SOURCE_CONTRACT.md](../../../AUTHORED_SOURCE_CONTRACT.md)**.

Role-slot fields are intentionally minimal in V1:

- `role_name`
- `required`
- `presence_constraint`
- optional informational `authority`

**`anchor_role_name`** (required in template JSON): exactly one `role_slots[].role_name` designated as the focal anchor for setup-seam resolution (Issue #80); must match a slot string on disk.

### Sidebar workflow

1. Select the participating characters.
2. Choose a scene template from the sidebar.
3. Assign each selected character to a role.
4. In **template-asset** mode, if multiple **Opener** JSON files exist for the **template**, **select** one in the opening section before starting; a single opener is auto-selected.
5. Start the scene only after all required roles are filled; when multiple **template** openers are in scope, **select** one first (Start Scene is blocked until then).

Validation is deterministic:

- every selected character must have a role assignment
- assigned roles must exist in the chosen template
- every required role must be filled before scene start

If no scene template is selected, use **custom text** in the opening UI; there is no separate “generic template `opening_text`” Start Scene path (GitHub **#100** / **#101** / **#108** / **#113**).

### What V1 enforces

- The Director receives the full cast role map and `presence_constraint` values every turn.
- The Director uses roles, `presence_constraint`, informational authority labels, active issues, location, scene phase, and the latest trigger as prompt-level evidence for turn selection.
- The Director is instructed to prefer the smallest relevant pressure core for the current beat rather than rotating the cast for fairness.
- Each character prompt receives its own role plus scene-role context.
- `must_remain` characters stay present in scene/prompt context.
- `must_remain` means structural presence, not a requirement to speak every beat.
- Validator checks reject direct exit / absence-contradiction moves for `must_remain` characters.

### What V1 does not do yet

- dynamic role reassignment mid-scene
- template inheritance
- AI role suggestion
- deterministic authority-based enforcement or hard routing
- richer freeform role semantics beyond the current flat slot schema

### Progression advisory parameters (Template-associated support file)

**Progression Advisory** reads a static profile (human-authored, not inferred at runtime) from **`python/data/scene_templates/{template_id}_progression.json`** (Template-associated support file per `../../../AUTHORED_SOURCE_CONTRACT.md` §1), or built-in defaults if the file is absent or invalid. **`progression_profile` is not read** from `{template_id}.json` (**#119**). Payload shape:

- **`advancement_channels`**: list of string channel ids (e.g. `physical_action`, `spatial_shift`, `bureaucratic_followthrough`, `social_reconfiguration`, `consequence`).
- **`common_stall_pattern`**: short description of the typical stall pattern for authoring context and advisory **note** text.

If the support file is absent and the legacy key is absent, the app uses a small built-in default profile. This does **not** change continuity authority or character state; it only shapes **optional prompt hints** and **audit/debug** fields when stall pressure is computed from existing scene signals. See `../Holy Grail PRD.md` §5.7 and `progression_advisory.py`. **Scene Grounding (settled scene facts, read-only prompts)** is specified in PRD §5.8 and `../../docs/scene-grounding-layer.md`.

### Audit visibility

When audit logging is enabled, scene-template metadata is captured in:

- `_manifest.json`
- `_narrative.json`
- `_audit_summary.json`
- granular per-bot `_full.json` logs

This includes the selected template ID, scene premise, cast-to-role assignments, presence constraints, authority labels, and per-turn acting-role metadata.

## Current module layout

- `app.py` - Thin Streamlit compatibility/composition entrypoint that preserves stable wrapper names for tests and callers
- `app_turn_helpers.py` - Compatibility export layer over `app_turn_director.py`, `app_turn_prompting.py`, `app_turn_rendering.py`, `app_turn_selector.py`, and `app_turn_audit.py`
- `app_state_helpers.py` - Compatibility export layer over `app_state_audit.py`, `app_state_characters.py`, `app_state_continuity.py`, `app_state_runtime.py`, `app_state_scene.py`, and `app_state_session.py`
- `ui_rendering.py` - Compatibility export layer for `ui_sidebar.py` and `ui_chat.py`
- `ui_sidebar.py` - Sidebar composition layer over `ui_sidebar_session.py`, `ui_sidebar_player.py`, `ui_sidebar_scene_setup.py`, and `ui_sidebar_opening.py`
- `app_memory_helpers.py` - Compatibility export layer over `app_memory_basics.py`, `app_memory_summary.py`, `app_memory_cross_session.py`, `app_memory_recording.py`, and `app_message_processing.py`
- `scene_lifecycle.py` - Compatibility export layer over `scene_lifecycle_start.py` and `scene_lifecycle_actions.py`
- `session_lifecycle.py` - Compatibility export layer over `session_lifecycle_save.py` and `session_lifecycle_load.py`
- `response_validation.py` - Compatibility export layer over content, presence, drift, parsing, and turn-selection helpers
- `memory_layer/` - Episodic write policy (`facade`, `writes`, `storage`) and read/format for character prompts (`retrieval`); see `../../docs/architecture.md`
- `character_state.py` - Compatibility export layer over `character_state_model.py` and `character_state_manager.py`
- `turn_runner.py` - Round orchestration entrypoint paired with `turn_runner_turn.py`, `turn_runner_updates.py`, and `turn_runner_audit.py`
- `progression_advisory.py` - Deterministic stall score and progression advisory for Director/character prompts and beat-shift hook (advisory only)
- `beat_shift_state.py` - Beat-shift pending state; unified `stall_score` threshold with short-user-message activation
- `character_loader.py` - Loads character JSON files and creates agents
- `session_manager.py` - Handles session save/load plus session indexing
- `continuity_manager.py` - Continuity engine for durable narrative state
- `audit_logger.py` - Audit logging infrastructure for scene analysis
- `ARCHITECTURE.md` - Architecture notes and design direction
- `AUDIT_DOCUMENTATION.md` - Scene audit system documentation and analysis guide
- `../data/autogen_characters/*.json` - Character definitions

## Character Format

For character conversion, opener formatting, and Janitor-to-AutoGen migration rules, see
[CHARACTER_MIGRATION_GUIDE.md](./CHARACTER_MIGRATION_GUIDE.md)

Character files are JSON with these fields:

```json
{
  "name": "Character Name",
  "description": "Brief description for selector",
  "system_prompt": "Full persona instructions",
  "personality": "Key traits",
  "speaking_style": "How they talk",
  "goals": "Character motivations",
  "core_goals": ["Stable long-term goal", "Second stable goal"],
  "voice_profile": {
    "speech_style": "blunt",
    "sentence_length": "short",
    "formality": "low"
  },
  "reaction_profile": {
    "worldview": "assumes deception",
    "trust_bias": "low",
    "conflict_style": "confrontational"
  },
  "speech_fingerprint": {
    "avg_sentence_length": "short",
    "question_frequency": "high",
    "formality_level": "casual"
  },
  "relationships": {"player": "relationship"},
  "lore_facts": ["Key background info"]
}
```

These identity-anchor fields are intended to remain stable across long sessions and are carried into
the character prompt without being intentionally summarized away.

## Character Move Format

Character agents are prompted to return JSON with core `action`, `dialogue`, and `motivation` fields, plus optional `scene_state_updates` for the currently supported resolved-outcome aspects when the acting speaker settles them in their own move:

```json
{
  "action": "leans against the table",
  "dialogue": "You're hiding something.",
  "motivation": {
    "goal": "expose Thorn",
    "tactic": "provoke anger",
    "emotional_driver": "resentment",
    "risk_level": "high"
  },
  "scene_state_updates": {
    "sleeping_surface_assignment": {
      "assignee_id": "Kizzie",
      "surface_id": "couch"
    }
  }
}
```

Only emit `scene_state_updates.sleeping_surface_assignment` when the acting speaker is establishing, enforcing, or explicitly reassigning where someone will sleep in that turn. Do not emit it for offers, suggestions, negotiation, reactions, or restating prior state.

For terminal housing / res-life contact, you may instead emit:

```json
{
  "scene_state_updates": {
    "housing_call_outcome": {
      "status": "completed"
    }
  }
}
```

Only emit `scene_state_updates.housing_call_outcome` when the acting speaker is explicitly settling the shared housing call by making it `completed` or `failed` in that turn. Do not emit it for planning, attempting, dialing, waiting on hold, or asking whether someone called.

For current suppressant formulation compatibility settlement, you may instead emit:

```json
{
  "scene_state_updates": {
    "suppressant_formulation_outcome": {
      "subject_id": "Kizzie",
      "status": "incompatible"
    }
  }
}
```

Only emit `scene_state_updates.suppressant_formulation_outcome` when the acting speaker is explicitly settling whether a named subject's current suppressant formulation is `compatible` or `incompatible` in that turn. Do not emit it for symptoms alone, suspicion, diagnosis, dosage changes, treatment planning, or historical formulations.

For current location entry permission settlement, you may instead emit:

```json
{
  "scene_state_updates": {
    "location_entry_outcome": {
      "subject_id": "Kizzie",
      "location_id": "clinic_room",
      "status": "allowed"
    }
  }
}
```

Only emit `scene_state_updates.location_entry_outcome` when the acting speaker explicitly settles a named subject's current permission to enter one bounded location in that turn. Do not emit it for requests, predictions, preferences, blocked paths, locked doors, physical obstruction, or partial/conditional permission.

Older `intent`-style outputs are still mapped into the new `motivation` structure for compatibility.

## Runtime Flow

1. The scene opener or user input updates the current scene state.
2. The Director chooses the next actor from the available bot-controlled participants using structured state, recent dialogue, and spotlight history.
3. A character who has already acted in the current response cycle is excluded from later picks in that same cycle.
4. The selected character receives the current scene state plus its own private state.
5. The character responds with structured JSON.
6. The Narrator renders that move into third-person prose while preserving dialogue exactly.
7. Character memory summaries and scene orchestration state are updated.

Current design direction for long-session continuity:

1. Keep only a small rolling dialogue window active in prompts.
2. Promote significant developments into public events and character-specific interpretations.
3. Track scene issues / pressures separately from completed events.
4. Feed layered scene state, issue state, and relevant memory back into Director and character prompts.
5. Keep the Narrator lightweight rather than turning it into a memory reasoner.

## Features

- **Configurable scene casts** with Director-controlled turn selection
- **Narrator rendering** with verbatim dialogue preservation
- **Identity anchors** for stronger voice persistence across long sessions
- **Per-character memory summaries** so characters keep different interpretations of events
- **Structured motivation** for more differentiated behavior
- **Per-scene control model** where a character card can be player-controlled or bot-controlled, but never both at once
- **Scene templates V1** with explicit cast-role assignment and deterministic required-role validation
- **Presence constraints** so `must_remain` characters stay structurally present and auditable
- **Session persistence** - save and resume conversations
- **Per-round bot turn cap** derived from active bot participants (no primary-UI limit control; **#103**)
- **Session list** - see and resume previous sessions
- **Auto-generated session IDs** based on characters and timestamp
- **Audit logging** - enable in sidebar to capture scene data for analysis
- **Hybrid tension pacing** — Director-primary `tension_shift`; when neutral, consequence tags may nudge tension up or down. **Saturation gate:** consequence-driven escalation is suppressed at maximum tension (`extreme`) to prevent no-op pacing activations. Director `escalate`/`soften` and consequence `down` are unchanged (see `ARCHITECTURE.md`, Hybrid tension pacing).

## Stage 4 Infrastructure (Completed)

The following Stage 4 hardening work has been implemented and is ready for calibration:

### Cross-Session Memory & Relationships
- **Session indexing** - `_session_index.json` provides bounded, cached retrieval without repeated full-session scans
- **Relationship trends** - trust history tracking with improving/stable/declining trend detection
- **Indexed metadata** - character presence, user relationships, and memory buckets pre-extracted for fast lookup

### Knowledge Propagation
- **Explicit `told` transitions** - when a character mentions an event to another by name, knowledge transfers as `told`
- **Limited inference** - token-overlap based inference for scene-local implied knowledge (conservative threshold)
- **Knowledge boundary validation** - `known_by`, `observed_by`, `told_to`, `inferred_by` tracked per event; **`PublicEvent.knowledge_level_for`** requires membership in **`known_by`** before any observed/told/inferred label applies
- **Audibility / perception (deterministic)** - structured moves may include **`audibility`** (`public` \| `directed` \| `private`) and **`audience`**; `perception_audibility.py` normalizes defaults and heuristics, then gates **per-recipient** transcript and structured **`dialogue`**, **`PublicEvent`** knower lists and safe summaries, **interpretation** quoting, and **Director** structured-move redaction. Narrator **`rendered`** prose is presentation only for this layer (not parsed for who heard what)

### Canon & Identity Enforcement
- **Extended drift detection** - voice profile, speech fingerprint, and reaction profile checks
- **Canon anchor awareness** - validation can reference seeded canon anchors from character state
- **Post-generation validation** - drift checked after character moves before narrator rendering

### Issue Lifecycle & Scene Pressure
- **Richer issue metadata** - `status_reason`, `matched_terms`, `related_event_ids`, `interaction_issue_ids`
- **Issue interaction tracking** - linked when participants and terms overlap
- **Pressure-shaped issue state** - `IssueState` now persists `pressure_kind`, `blocked_what`, `blocked_characters`, `last_change`, `required_next_step`, and plateau-tracking fields (`required_next_step_plateau_*`) used when mixed **`advanced`** / **`escalated`** issue transitions repeat without changing obligation text (`continuity_issue_helpers.apply_mixed_transition_plateau_refresh`)
- **Pressure-first hybrid matching** - issue matching prioritizes participants, `pressure_kind`, blocked objective, and next-step compatibility, with token overlap retained as fallback
- **Pressure-aware lifecycle reasons** - `status_reason` describes how pressure escalated, narrowed, advanced, stalled, or resolved
- **Conservative stall threshold** - 3 turns without material reinforcement (configurable via `ISSUE_STALL_TURN_THRESHOLD`)
- **Compatibility fallbacks remain** - signal/text heuristics still exist as a safety net when consequence classification is weak or older issue shapes are restored

### Summaries & Compression
- **Impact-scored summary blocks** - `impact_score` based on event significance (minor=1, major=2, pivotal=3)
- **Participant tracking** - `participant_names` and `dominant_issue_ids` per summary
- **Pressure-preserving issue updates** - summary blocks retain `pressure_kind`, `blocked_what`, and `required_next_step` alongside `status_reason`
- **Ranked retrieval** - summaries sorted by impact score for prompt assembly

## Stage 4 Calibration Plan

These systems now require real-session validation. Run audited scenarios and review immediately after each.

### Calibration Tracking

| Scenario | Date | Validator Tuning | Knowledge Prop | Issue Lifecycle | Summaries | Notes |
|----------|------|------------------|----------------|-----------------|-----------|-------|
| 2-char simple | | ☐ | ☐ | ☐ | ☐ | |
| 2-char emotional | | ☐ | ☐ | ☐ | ☐ | |
| 3-char confrontation | | ☐ | ☐ | ☐ | ☐ | |
| Long session (20+ turns) | | ☐ | ☐ | ☐ | ☐ | |
| Reload + continuity | | ☐ | ☐ | ☐ | ☐ | |

### What to Review Per Session

**Rejected Moves**
- False positives on drift detection
- Voice profile mismatches that should have passed
- Over-sensitive reaction profile triggers

**Knowledge Propagation**
- Characters using info they shouldn't know (knowledge leak)
- `told` status applied correctly when directly addressed
- Inferred knowledge too aggressive or too weak

**Issue Lifecycle**
- New issues read like blocked objectives / pressure, not paraphrased dialogue
- Matching looks primarily consequence- and pressure-driven rather than topic- or token-driven
- Fallback text heuristics are acting as safety nets rather than the main engine
- Status transitions feel natural
- Stalled issues actually feel stalled vs forgotten
- Resolved issues stay resolved appropriately

**Summaries**
- High-impact blocks retrieved when they should be
- Summary content useful for continuity, not noise
- Retrieval ranking picks relevant blocks
- Issue updates preserve meaningful pressure changes rather than only speech content

**Relationship Trends**
- Trust trajectory matches scene events
- Trend display in prompts helps or hinders
- Trust history not inflated on session reload

### After 3-5 Scenarios

Look for patterns across the tracking table, then do a calibration pass:
- Tune drift detection thresholds
- Adjust knowledge propagation overlap threshold
- Refine stall timing
- Tune summary ranking weights

### UI vs headless (validated baseline)

The Streamlit app and the headless scenario runner (`scripts/run_scene_simulation_llm.py` from `autogen_rp/python`) share the **same** core turn loop and fresh-scene bootstrap (GitHub **#83**); they are different **input surfaces**, not two runtime pipelines. When a UI run and a headless run **disagree**, treat the gap as **input-driven** first: scenario or CLI triggers, `startup_trigger_mode` on manifests, `--user-trigger-schedule`, authored retrieval activation (`RP_RETRIEVED_CONTEXT_INDEX` / `--retrieved-context-index`), and **deep simulation** vs short-cap modes. For **which Opener asset** starts the scene, Streamlit uses **`ui_sidebar_opening`** / `selected_opener_id` (operator UI: template / custom only—**#101**, **#108**, **#113**); headless and authored **scenario/CLI** composition may also resolve **`character_asset`**. Align on **resolved** opening text, not on UI-only controls. **Do not** infer a defect from mismatched inputs. Full semantics and commands are in **[SCENARIO_VALIDATION_FRAMEWORK.md](../../../SCENARIO_VALIDATION_FRAMEWORK.md)** (repo root).

### Running Audited Sessions

With audit logging enabled, **Streamlit** (sidebar toggle) and **headless** runs using **`--audit`** write the same **family** of artifacts under **`rp_app/data/rp_audits/`** (session folders, `_audit_summary.json`, per-turn logs). **Signal meaning and interpretation** (including advisory vs authoritative fields) are in **`AUDIT_DOCUMENTATION.md`**, not in this README.

1. Enable audit logging in the sidebar before starting the scene
2. Run 5-10 turns
3. Click the audit report link to view `_audit_summary.json`
4. Review the categories captured: turn selection, drift, memory, repetition
5. Note observations in the tracking table above

## Reference docs

- See `Current module layout` above for the active `python/rp_app/` structure
- **[MODULE_INDEX.md](../../../MODULE_INDEX.md)** — full symptom → module map (canonical at Holy Grail repo root); this folder’s `MODULE_INDEX.md` is a pointer
- `AUDIT_DOCUMENTATION.md` - Scene audit system documentation and analysis guide
- `CHARACTER_MIGRATION_GUIDE.md` - Character conversion and format guidance
