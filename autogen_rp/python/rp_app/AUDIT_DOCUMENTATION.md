# RP App Audit System Documentation

This document describes the audit logging system for the RP app, enabling scene analysis and bot behavior debugging.

## Overview

The audit system captures every bot interaction during roleplay scenes, creating both granular per-bot logs and
session-level summaries. It is designed to support both prose review and architecture-level debugging.

This allows for:

- Complete scene reconstruction
- Per-character contribution analysis
- Director decision tracking
- Spotlight (turn distribution) analysis
- Bot behavior debugging
- Continuity-state and issue-lifecycle analysis
- State-change and consequence tracking
- Summary-block visibility and retrieval analysis

### Progression advisory (MVP) in audits

When enabled, Director turn metadata may include a **`progression_advisory`** object (not continuity truth): **`stall_score`**, **`progression_pressure`** (`low` / `medium` / `high`), **`recommended_channels`**, **`stall_components`** (booleans: same phase, high tension, issue stability, low consequence variety), and related fields consistent with `progression_advisory.py`. Logs may also record when advisory text is injected into prompts or when beat-shift eligibility is influenced by the unified **`stall_score`** threshold.

### Anti-regression advisory (MVP) in audits

Director turn metadata may include **`anti_regression_advisory`**: **`active`** (whether the ANTI-REGRESSION Director prefix was injected this call), **`ping_pong_detected`**, **`post_break_window_active`**, **`low_player_agency`**, **`ping_pong_actors`** (the two alternating `next_actor` ids when detected), and **`ticks_after_decrement`** (remaining post-break window ticks after this Director step). This mirrors orchestration cache fields from `anti_regression_advisory.py` and is not continuity truth. Application logs under **`rp_app.anti_regression_advisory`** record injection and post-break arming when enabled.

**Character** and **Narrator** per-turn audit metadata also include **`progression_advisory`** and **`anti_regression_advisory`** snapshots read from orchestration cache at log time (same fields as above, where present). That lets you correlate each rendered beat with stall pressure, ping-pong flags, and post-break window state without relying on Director JSON alone.

### Scene Grounding (MVP) in audits

Audits may record a compact **`scene_grounding`** snapshot (or **`scene_grounding_summary`**) per relevant turn: **active fact count**, **categories** present, **`fact_id`** list or hashed fingerprint of `(category, key)` pairs, and optionally the **exact `value_summary` lines** injected into prompts. This is **observability** for the prompt projection — **not** continuity truth (continuity remains authoritative; facts are derived).

**What to verify in audits**

- After a turn where continuity established a settled logistic (e.g. bunk assignment), the next turn’s **Director/character** audit payload should show the **SETTLED SCENE FACTS** block (or metadata proving injection).
- **No drift** between **continuity event** and **grounding** for the same key: if promotion rules fired, `source.ref` should tie to the continuity artifact.
- **Cap behavior:** fact count ≤ configured maximum; pruning should be visible if many keys compete.
- **Scene end:** grounding snapshot should be **empty** or **absent** on the next scene’s first turn after grounding state clears.

## Directory Structure

All audit files are stored in:
```
rp_app/data/rp_audits/
```

Organised by session number first, then round number:
```
rp_audits/
└── session_{###}/                   # 3-digit session number
    ├── _manifest.json                # Scene cast and metadata
    ├── _round_index.json             # Round -> ordered turn mapping
    ├── _narrative.json               # Story trace + turn-level continuity facts
    ├── _audit_summary.json           # Session-level audit dashboard
    ├── round_001/
    │   ├── {owner}_session{###}_round001_turn01_director_full.json
    │   ├── {owner}_session{###}_round001_turn01_director_light.json
    │   ├── {owner}_session{###}_round001_turn01_{character}_full.json
    │   ├── {owner}_session{###}_round001_turn01_{character}_light.json
    │   ├── {owner}_session{###}_round001_turn01_narrator_full.json
    │   ├── {owner}_session{###}_round001_turn01_narrator_light.json
    │   ├── {owner}_session{###}_round001_turn02_director_full.json
    │   └── ...
    └── round_{###}/
```

## Key Files

### 1. `_manifest.json`
**Purpose**: Scene overview and cast list

**Created**: Once, when scene starts

**Contents**:
```json
{
  "session_number": 42,
  "timestamp": "2026-03-14T12:45:30Z",
  "cast": ["Ayame", "Celina", "Kizzie"],
  "user_name": "Player",
  "opening_description": "Rain had been falling...",
  "total_characters": 3,
  "scene_template": {
    "template_id": "household_entry_evaluation",
    "premise": "A host evaluates a newcomer while a guard remains present.",
    "role_assignments": {
      "Ayame": "host",
      "Celina": "applicant",
      "Kizzie": "guard"
    },
    "character_presence_constraints": {
      "Ayame": "must_remain",
      "Celina": "must_remain",
      "Kizzie": "must_remain"
    },
    "character_authority_labels": {
      "Ayame": "high",
      "Celina": "low",
      "Kizzie": "medium"
    }
  }
}
```

### 2. `_round_index.json`
**Purpose**: Maps each round to its ordered turns

**Created**: Updated after each turn

**Contents**:
```json
{
  "rounds": [
    {
      "round_number": 1,
      "turns": [
        {
          "turn_number": 1,
          "acting_character": "Ayame",
          "director_reason": "Ayame was directly addressed and had narrative momentum.",
          "acting_role": "host",
          "presence_constraint": "must_remain",
          "authority_label": "high",
          "continuity_event_type": "decision",
          "state_change_count": 1,
          "issue_update_count": 1,
          "presence_change_count": 0,
          "timestamp": "2026-03-14T12:45:45Z"
        },
        {
          "turn_number": 2,
          "acting_character": "Celina",
          "director_reason": "Celina's reaction would heighten the tension.",
          "acting_role": "applicant",
          "presence_constraint": "must_remain",
          "authority_label": "low",
          "timestamp": "2026-03-14T12:46:10Z"
        }
      ]
    }
  ]
}
```

### 3. `_narrative.json`
**Purpose**: Human-readable story trace with per-turn continuity and orchestration facts

**Created**: Updated after each turn

**Contents**:
```json
{
  "session_owner": "Ayame",
  "session_number": 42,
  "created_at": "2026-03-14T12:45:30Z",
  "last_updated": "2026-03-14T12:52:15Z",
  "total_rounds": 6,

  "scene_template": {
    "template_id": "household_entry_evaluation",
    "premise": "A host evaluates a newcomer while a guard remains present.",
    "role_assignments": {
      "Ayame": "host",
      "Celina": "applicant",
      "Kizzie": "guard"
    },
    "character_presence_constraints": {
      "Ayame": "must_remain",
      "Celina": "must_remain",
      "Kizzie": "must_remain"
    },
    "character_authority_labels": {
      "Ayame": "high",
      "Celina": "low",
      "Kizzie": "medium"
    }
  },
  
  "complete_narrative": "Rain had been falling steadily...\n\nAyame eased herself back...\n\nCelina crossed to the cabinet...",
  
  "turns": [
    {
      "round": 1,
      "turn": 1,
      "character": "Ayame",
      "character_role": "host",
      "character_presence_constraint": "must_remain",
      "character_authority_label": "high",
      "director_reason": "Ayame was directly addressed and had narrative momentum.",
      "environment_event": "",
      "tension_shift": "escalate",
      "character_action": "eased back onto the couch, movements deliberately slow",
      "character_dialogue": "As you command. Stitches and a tetanus shot...",
      "character_motivation": {
        "goal": "maintain psychological dominance",
        "tactic": "comply superficially while maintaining control",
        "emotional_driver": "amused confidence",
        "risk_level": "low"
      },
      "rendered_output": "Ayame eased herself back onto the couch...",
      "continuity_event_type": "decision",
      "continuity_event_summary": "Ayame refused the current demand, request, or proposed course of action.",
      "continuity_event_significance": "pivotal",
      "continuity_related_issue_ids": ["issue_1"],
      "state_changes": [
        "Ayame refused the current demand, request, or proposed course of action."
      ],
      "actionable_implications": [
        "The cast must respond to the refusal or choose a different course."
      ],
      "scene_recent_delta": "Ayame refused the current demand, request, or proposed course of action.",
      "scene_phase": "rising",
      "current_tension_level": "moderate",
      "active_issue_ids_after": ["issue_1"],
      "present_characters_after": ["Ayame", "Celina", "Kizzie"],
      "absent_but_relevant_after": [],
      "issue_updates": [
        {
          "issue_id": "issue_1",
          "description": "The current proposed course of action. Required next move: The cast must respond to the refusal or choose a different course.",
          "status": "escalating",
          "status_reason": "Ayame refused the current demand, request, or proposed course of action. escalated the plan execution; The cast must respond to the refusal or choose a different course.",
          "pressure_kind": "plan_execution",
          "blocked_what": "The current proposed course of action",
          "required_next_step": "The cast must respond to the refusal or choose a different course."
        }
      ],
      "presence_changes": [],
      "timestamp": "2026-03-14T12:46:00Z"
    }
  ],
  
  "character_stats": {
    "Ayame": {
      "turns": 3,
      "dialogue_count": 3,
      "total_response_length": 342,
      "avg_response_length": 114,
      "spotlight_percentage": 50.0
    },
    "Celina": {
      "turns": 3,
      "dialogue_count": 2,
      "total_response_length": 298,
      "avg_response_length": 99,
      "spotlight_percentage": 50.0
    }
  }
}
```

### 4. `_audit_summary.json` ⭐ PRIMARY AUDIT DASHBOARD
**Purpose**: Session-level audit dashboard aligned with the current continuity/orchestration architecture

**Created**: Refreshed during audited scene flow

**Highlights**:
- `overview`: rounds, turns, update timestamp
- `continuity_overview`: state-change coverage, issue updates, presence transitions, low-change turns
- `scene_template.role_coverage`: role/presence/authority coverage across the cast
- `round_summaries`: one compact entry per round, including continuity movement and summary-block use
- `summary_block_visibility`: raw prompt-visibility metrics
- `summary_block_quality`: availability/injection/fallback rates
- `issue_categories` / `heuristic_issue_categories`: confirmed and text-derived pressure buckets
- `regression_checks`: session-level pass/fail indicators

### 5. Granular Bot Logs
**Naming**: `{owner}_session{###}_round{###}_turn{##}_{bot}_{level}.json`

**Examples**:
- `ayame_session042_round001_turn01_director_full.json`
- `ayame_session042_round001_turn01_ayame_full.json`
- `ayame_session042_round001_turn01_narrator_full.json`
- `ayame_session042_round001_turn02_director_light.json`
- `ayame_session042_round001_turn02_celina_light.json`
- `ayame_session042_round001_turn02_narrator_light.json`

**Two Levels**:
- `_full.json`: Complete prompt, raw response, parsed output, context snapshot
- `_light.json`: Message summaries, previews, metadata (smaller, faster to scan)

When scene templates are active, the granular `_full.json` logs also include `context_snapshot.scene_template`
with the template ID, premise, role assignments, presence constraints, and authority labels that were active
for that turn.

## How to Audit a Scene

### Quick Scene Read
1. Navigate to `rp_audits/session_{###}/`
2. Open `_audit_summary.json`
3. Check `overview`, `continuity_overview`, `issue_categories`, and `recent_rounds`
4. Open `_narrative.json` for the prose story and turn-by-turn trace
5. Use `_round_index.json` if you need the per-turn order and continuity counts within a round

### Analyze Character Contributions
1. Open `_narrative.json`
2. Review `turns[]` array
3. Each turn shows:
   - Who acted (`character`)
   - Why they were chosen (`director_reason`)
   - What they did (`character_action`)
   - What they said (`character_dialogue`)
   - Their motivation (`character_motivation`)
   - What changed (`state_changes`)
   - What became actionable (`actionable_implications`)
   - Which issues moved (`issue_updates`)
   - Final rendered output (`rendered_output`)

### Audit Continuity and State Transitions
1. Start with `_audit_summary.json`
2. Review `continuity_overview` for:
   - `turns_with_state_change`
   - `turns_with_issue_update`
   - `turns_without_material_change`
   - `presence_transition_count`
3. Review `round_summaries[]` for:
   - `continuity_event_types`
   - `state_change_count`
   - `issue_update_count`
   - `presence_change_count`
   - `scene_recent_deltas`
   - whether issue updates read like pressure shifts instead of dialogue paraphrase
4. Cross-check `_narrative.json` `turns[]` if you need the exact turn that changed state

When reviewing `issue_updates`, treat the most useful fields as:

- `pressure_kind`
- `blocked_what`
- `required_next_step`
- `status_reason`

The current issue engine is pressure-first but still hybrid. If a turn only updated an issue through
textual fallback, that should be read as a continuity safety-net path rather than the ideal signal path.

### Check Spotlight Balance
1. Open `_narrative.json`
2. Review `character_stats` section
3. Compare `spotlight_percentage` across characters
4. Check `turns` count per character
5. Look at `avg_response_length` for verbosity patterns

### Audit Scene-Template Role Coverage
1. Open `_audit_summary.json`
2. Check `scene_template.template_id` to confirm the intended template was active
3. Review `scene_template.role_coverage` for each assigned character's:
   - `role`
   - `presence_constraint`
   - `authority_label`
   - `turns`
   - `spotlight_percentage`
4. Check `scene_template.must_remain.characters_with_zero_turns`
5. Treat any `must_remain` character with zero turns as a watch item for soft dropout or Director neglect
6. Treat any audit artifact showing role changes after setup as a bug, not a presumed setup error

### Debug Director Decisions
1. Check `_audit_summary.json` `round_summaries[].director_reasons`
2. Check `_narrative.json` `turns[].director_reason`
3. If more detail needed, open granular file:
   `{owner}_session{###}_round{#}_director_full.json`
4. Review `input_messages` for what Director saw
5. Compare `raw_response` vs `parsed_output`
6. Check `metadata.turn_selection_issues` and semantic assessment metadata
7. If scene templates are active, confirm the Director saw `context_snapshot.scene_template`

### Debug Character Behavior
1. Check `_narrative.json` `turns[].character_motivation`
2. If more detail needed, open:
   `{owner}_session{###}_round{#}_{character}_full.json`
3. Review full prompt in `input_messages`
4. Check identity anchors were present
5. Check `turns[].character_role` and `turns[].character_presence_constraint`
6. Check `context_snapshot.continuity_event` and `scene_state_after` to see what state the turn created

### Debug Narrator Rendering
1. Compare `turns[].character_dialogue` vs `turns[].rendered_output`
2. Check verbatim preservation
3. If issues, open:
   `{owner}_session{###}_round{#}_narrator_full.json`
4. Review render prompt and rules given
5. If scene templates are active, confirm the acting character's role metadata is present in the narrator audit

### Debug Summary Retrieval and Prompt Compression
1. Open `_audit_summary.json`
2. Review `summary_block_visibility`
3. Review `summary_block_quality`
4. Check `round_summaries[].summary_block_usage`
5. If needed, open the corresponding `_full.json` files and inspect `metadata.summary_blocks`

## Multi-Character Scenes

For scenes with 2-6 characters:

- All characters appear in `_manifest.json` `cast`
- Scene-template sessions also record `scene_template.role_assignments` in `_manifest.json`
- `_round_index.json` shows turn order inside each round
- `_narrative.json` `character_stats` compares contributions and `turns[]` captures continuity deltas
- `_audit_summary.json` `scene_template.role_coverage` helps spot role imbalance and soft dropout watch items
- `_audit_summary.json` `continuity_overview` helps spot consequence-free drift across the whole session
- Granular files are named by the **acting character** (not owner)

Example 3-character scene:
```
rp_audits/session_042/
├── _manifest.json (cast: ["Ayame", "Celina", "Kizzie"])
├── _round_index.json (round 1 turns: Ayame, Celina; round 2 turns: ...)
├── _narrative.json (stats for all 3)
├── round_001/
│   ├── ayame_session042_round001_turn01_director_full.json
│   ├── ayame_session042_round001_turn01_ayame_full.json
│   ├── ayame_session042_round001_turn01_narrator_full.json
│   ├── ayame_session042_round001_turn02_director_full.json
│   ├── ayame_session042_round001_turn02_celina_full.json
│   └── ayame_session042_round001_turn02_narrator_full.json
├── round_002/
│   └── ayame_session042_round002_turn01_director_full.json
└── ...
```

## Common Audit Tasks

### "Who dominated the conversation?"
Check `_narrative.json` → `character_stats` → `spotlight_percentage`

### "Did the scene keep changing, or did it drift into low-consequence beats?"
Check `_audit_summary.json` → `continuity_overview`

### "Did a `must_remain` character effectively disappear?"
Check `_audit_summary.json` → `scene_template.must_remain.characters_with_zero_turns`

Then cross-check `_round_index.json` and `_narrative.json` to see whether the character remained structurally
present but stopped receiving turns.

### "Who was filling each template role?"
Check `_manifest.json` → `scene_template.role_assignments`

### "Which role was active on a given turn?"
Check `_narrative.json` → `turns[]` → `character_role`

### "Why did the Director choose X at round 3?"
Check `_narrative.json` → `turns[2]` (0-indexed: round 3 = index 2) → `director_reason`

### "Was dialogue preserved verbatim?"
Compare `_narrative.json` → `turns[].character_dialogue` vs `turns[].rendered_output`

### "What was the environment event at round 5?"
Check `_narrative.json` → `turns[4]` → `environment_event`

### "What actually changed on a given turn?"
Check `_narrative.json` → `turns[]` → `state_changes`, `actionable_implications`, `issue_updates`,
`scene_recent_delta`

For issue movement, inspect whether `status_reason`, `pressure_kind`, `blocked_what`, and
`required_next_step` describe a concrete pressure shift or merely restate speech content.

### "Show me the complete scene as rendered"
Check `_narrative.json` → `complete_narrative`

### "How did character motivations evolve?"
Check `_narrative.json` → `turns[].character_motivation` across all rounds for that character

## File Reference for AI Assistants

When asked to audit a scene:

1. **Locate the session**: 
   - Ask user for the session number (or check most recent session folder)
   - Navigate to `rp_audits/`
   - Find the relevant `session_{###}` folder

2. **Start with the audit dashboard**:
   - Read `_audit_summary.json`
   - Extract `overview`, `continuity_overview`, `issue_categories`, and `recent_rounds`
   - For issue movement, prefer pressure-shaped evidence over raw counts alone

3. **Then read the narrative trace**:
   - Read `_narrative.json`
   - Extract `complete_narrative` for the story
   - Use `turns[]` for exact continuity/state transitions
   - Use `character_stats` for contribution analysis

4. **Drill down as needed**:
   - For specific turn details: use `_narrative.json` `turns[]`
   - For turn order and continuity counts: use `_round_index.json`
   - For bot debugging: open granular `_full.json` files

5. **Cross-reference cast**:
   - Check `_manifest.json` for full character list
   - Ensure you're accounting for all characters in analysis

## Long-Scene Context Safeguard

This RP app uses bounded AutoGen model contexts for the Director, Narrator, and character agents.

- Character agents are created with `BufferedChatCompletionContext(buffer_size=1)`
- Director and Narrator agents are also created with `BufferedChatCompletionContext(buffer_size=1)`
- On reruns and resumed sessions, character agents are rebuilt from stored state so they do not keep stale accumulated internal chat history

This matters because the source of truth for the scene is intended to be:

- `team_state` / `scene_state`
- `character_states`
- recent structured moves and recent dialogue history

Not the agent's hidden accumulated chat transcript.

### If a future token-limit error occurs

Future AI assistants auditing a context-length failure should check these in order:

1. Whether the failure came from a single oversized prompt payload
2. Whether bounded model context is still configured on the relevant agent constructors
3. Whether character agents are being rebuilt correctly on rerun / session restore
4. Whether a new feature introduced unbounded data into `scene_state`, prompt assembly, or audit payload construction

Do not assume that a long-scene token failure is caused by the visible prompt text alone. In this codebase, an important prior failure mode was hidden agent-side context accumulation from unbounded model context.

## Technical Notes

- Audit files are **not version controlled** (in `.gitignore`)
- Files are UTF-8 encoded JSON
- Timestamps are UTC ISO format
- File writes are wrapped in try/except - audit failures don't break scene flow
- Round numbers start at 1; `turn_number` increments within each round
- Session numbers are 3-digit, allocated by the audit logger's next-session lookup
