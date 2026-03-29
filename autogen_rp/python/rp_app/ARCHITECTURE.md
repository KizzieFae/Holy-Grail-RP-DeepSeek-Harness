# Director + Narrator Mediated Architecture

## Overview

This branch implements a director- and narrator-mediated roleplay architecture with private
per-character state.

**Goal:** Each non-narrator bot writes only their own parts and progresses their own character objectives without cross-character writing bleed.

## Operating Rules

### Participant and control model

- Active LLM-controlled participants are the selected scene characters.
- The user is present in-scene but remains separate from the LLM actor pool while directly controlled.
- Any character-profile, including the user's persona if represented as a character card, may be either player-controlled or bot-controlled per scene, but never both at once.
- A player-controlled character does not make an LLM call, and the user's post ends the round.

### Round structure

- Default bot replies per user turn equals the number of active bot participants, with user override allowed.
- The configured reply limit is a per-round cap on total bot replies, not a per-character quota.
- The same character should not act twice in the same response cycle.

### Scene lifecycle

- Ending a scene saves and closes it.
- Starting a new scene closes the current one first.
- Interrupted active sessions are finalized on next startup.

**Implemented in the current app:**

- Director-controlled turn selection using structured scene state
- Narrator-only prose rendering with verbatim dialogue preservation
- Stronger identity anchors in character prompts and state
- Per-character interpretation summaries to reduce worldview convergence
- Structured motivation in place of flat intent strings

## Architecture Changes

### Before (Free-form character prose)

- Characters wrote unrestricted third-person narrative prose
- Characters could accidentally narrate other characters' actions/thoughts
- No hard separation between self-narration and scene-narration

### After (Narrator-mediated)

- Characters produce structured self-only output:
  - `action`: brief visible action (self only)
  - `dialogue`: spoken words
  - `motivation`: private goal/tactic/emotional driver/risk level
- Director decides who acts next and may introduce a light environment or tension beat
- Narrator converts structured output into polished scene prose while preserving dialogue verbatim
- Each character has private state:
  - long-term goal
  - medium-term goal
  - short-term tactics
  - emotional state
  - private memories/interpretations
  - persistent identity anchors (`voice_profile`, `reaction_profile`, `speech_fingerprint`, `core_goals`)

## Key Components

### 1. Character State Management (`character_state.py` facade over `character_state_model.py` and `character_state_manager.py`)

Tracks per-character:

- Identity (name, description, personality)
- Goals (long-term, medium-term, current tactic/objective)
- Emotional state
- Persistent identity anchors:
  - `voice_profile`
  - `reaction_profile`
  - `speech_fingerprint`
  - `core_goals`
- Private memory/notes
- Character-specific interpretation summaries of scene events
- Relationship states

### 2. Structured Output Format

Characters now return:

```json
{
  "action": "lifted her cup, eyes narrowing at the doorway",
  "dialogue": "Who is she?",
  "motivation": {
    "goal": "test whether Celina knows the stranger",
    "tactic": "probe with a direct question",
    "emotional_driver": "suspicion",
    "risk_level": "low"
  }
}
```

### 3. Director Agent

Director receives structured orchestration inputs and returns:

- `next_actor`
- optional `environment_event`
- optional `tension_shift`
- `reason`

Director inputs are intentionally structured and lightweight:

- current scene state, including location, scene phase, present characters, and recent tension or environment beats
- scene-template context, including template ID and premise
- cast role map, including assigned roles, `presence_constraint`, and informational authority labels
- recent structured character actions
- public character goal/emotion snapshot
- active issues and recent public events
- recent dialogue history
- spotlight history and currently available next actors

Director selection policy is prompt-guided rather than hard-coded. It is instructed to:

- treat roles, presence constraints, authority labels, active issues, location, scene phase, and the latest trigger as primary evidence for who should act next
- prefer the smallest relevant pressure core for the current beat instead of rotating the cast for fairness
- treat `must_remain` as structural presence in the scene, not as a requirement to speak every beat
- avoid selecting secondary present characters unless they were directly addressed, are the natural responder, or would create an immediate consequential complication

The Director does not write prose.

#### Progression advisory (MVP)

When the deterministic **progression advisory** layer detects elevated **stall pressure**, the Director may receive a short **PROGRESSION ADVISORY** prefix (outside the JSON payload) suggesting advancement channels from the scene template’s optional **`progression_profile`** (e.g. physical action, spatial shift, consequence). This is **guidance only**; it does not override selection logic or continuity.

Beat-shift activation uses the **same** computed **`stall_score`** threshold as this advisory layer (alongside the existing short-user-message path), so there is a **single** plateau-related signal rather than duplicate detectors.

#### Scene Grounding layer (MVP)

A **read-only** **SETTLED SCENE FACTS** block is injected into Director and character prompts when facts exist. Facts are a **deterministic, capped, allowlisted** projection **derived from** `PublicEvent.grounding_markers` (computed in continuity classification) — not a second authority (PRD §5.8). See `scene_grounding.py` and `autogen_rp/docs/scene-grounding-layer.md`. Rebuilt in `turn_runner_updates` after each successful continuity `process_turn`; **no** writes to `CharacterState` or continuity.

### 4. Narrator Rendering

Narrator receives structured moves and renders:

- Scene-appropriate third-person prose
- Past tense, consistent style
- Proper attribution ("she said", character names)
- Exact dialogue preservation when dialogue is present

### 5. Orchestration Flow

```text
User Input
    ↓
Director evaluates structured scene state, roles, current pressures, and the latest trigger
    ↓
Available actor set excludes any character already used this round
    ↓
Character Agent sees:
    - Current scene state
    - Recent structured actions
    - Recent dialogue history
    - Director decision for the current beat
    - Its own private state
    ↓
Character outputs structured move (action/dialogue/motivation)
    ↓
Validation: reject if tries to narrate others
    ↓
Narrator renders character move → polished prose
    ↓
Update character private state (goals, emotional shift, memories)
    ↓
Update per-character interpretation summaries
    ↓
Render to UI
```

The user's controlled character is not included in the available actor set for Director selection.

### 6. Current Context Window Strategy

The current implementation now uses a hidden continuity manager plus bounded prompt windows.

The active prompt is kept bounded by:

- recent structured moves
- recent dialogue history
- scene state windows for tension/environment beats
- active issues / pressures
- recent public events and retrieved summary blocks
- each character's private state, interpretations, and canon anchors

The following identity anchors are treated as persistent and should not be summarized away:

- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`
- `core_goals`

#### Why continuity remains the main architectural lever

The current system already reduces prompt bloat better than a raw transcript-driven chat loop.

- recent dialogue is windowed
- recent structured moves are bounded
- agent model contexts are small
- scene state now carries structured continuity context

That means the main long-session problem is no longer just token count. The bigger issue is that
continuity quality now depends on how well the hidden continuity layer converts turns into durable,
pressure-shaped state rather than dialogue residue.

This causes several known failure modes:

- repetition and scene loops
- weak or overly text-driven pressure tracking when consequence classification is thin
- temporary tactics becoming sticky identities
- viewpoint collapse when interpretation and fact are not separated cleanly

The next architectural step is therefore to keep strengthening the continuity engine, not to move
weight back into prompts or transcript windows.

Complementing that, the **Scene Grounding** MVP projects a **small subset** of already-settled truths into prompts so models stop **re-asking** or **resetting** logistics the continuity layer has already established — without making prompts the **author** of those truths (see PRD §5.8).

## Planned Additions

### 7. Scene Opening System (Janitor-style initial messages)

The app needs authored starting messages similar to Janitor bot first messages. These are not generated from scratch each time. They are curated scene openers that establish tone, location, current pressure, and the immediate hook for player response.

#### Source pattern from archived definitions

Archived initial messages, such as Celina's, follow a clear structure:

- third-person past-tense prose
- immediate environmental framing
- character introduced through action, not biography
- clear situational tension
- direct final engagement hook aimed at `{{user}}`

#### Example shape

- setup: weather/location/mood
- inciting discovery or pressure event
- character reaction that reveals personality
- immediate playable situation
- closing line that invites user response

#### Planned AutoGen adaptation

Rather than asking the narrator to invent every opening, the narrator should select from stored authored opening assets.

#### Opening flow

```text
Scene start request
    ↓
Load selected characters + scenario metadata
    ↓
Load available authored opening message(s)
    ↓
Narrator selects or lightly adapts best-fit opener
    ↓
Narrator posts opening prose to chat
    ↓
Character turn orchestration begins from that established state
```

#### Recommended data model

Each character/scenario package should support an optional `initial_message` asset containing:

- opening prose
- scenario tags
- involved actors
- location/time metadata if known
- optional trigger conditions

#### Responsibility split

- character definitions provide authored opener content
- narrator chooses and posts the opener
- character agents do not post the initial scene block directly

### 8. Story Progression and Continuity System (Scribe2-inspired)

The RP app now includes a hidden continuity manager. The archived Scribe2 design was useful as a
directional model, but the current implementation has already adopted its central idea: a hidden
state compiler that turns transient interaction into durable continuity.

#### Current continuity model

The current continuity design uses five durable structures plus one prompt policy.

##### Durable structures

- `SceneState`
- `IssueState`
- public event memory
- character interpretation memory
- canon anchors

##### Prompt policy

- maintain only a small rolling dialogue window in prompts
- promote important developments into durable memory instead of carrying forward long dialogue logs

This keeps dialogue ephemeral while preserving the narrative state that actually matters.

#### Source pattern from Scribe2

Scribe2 is explicitly non-roleplay. It acts as a continuity manager that updates a compact structured memory block from story summaries.

#### Key lessons to carry over

##### Objective layering

Each AI-controlled character should have:

- long-term objective
- medium-term objective
- short-term objective

##### Knowledge boundaries

Characters should only know what they:

- directly observed
- were told
- can plausibly infer

##### Memory compression

Not all prior events should remain in active prompt context. The Scribe2 pattern separates:

- active facts affecting immediate play
- background facts needed for continuity
- canon anchors that should rarely change

For this RP app, the same principle should be extended to separate:

- public story events
- per-character interpretations of those events
- active vs resolved pressures
- canon anchors that should resist casual drift

##### Momentum tracking

Story progression is not just "what happened". It is also:

- what tensions were resolved
- what tensions remain unresolved
- whether a character's objectives are escalating, stable, compromised, or reversing

#### Implemented AutoGen adaptation

Instead of making Scribe2 a visible chat participant, the app uses a hidden continuity layer that
runs between scene beats.

This continuity manager acts as a story-state compiler:

- dialogue and structured actions go in
- durable story state comes out

Its job is not to write prose. Its job is to convert transient interaction into usable continuity.

#### Continuity flow

```text
User turn + character turns complete
    ↓
Inspect recent structured moves + recent dialogue window
    ↓
Promote significant developments into event objects
    ↓
Update scene state, issue state, and character interpretations
    ↓
Feed layered public + private context into next prompts
```

#### Recommended split between systems

- director: selects the next actor and optional environmental/tension beats
- narrator: posts prose to the chat
- character agents: choose self-only actions/dialogue/motivation
- continuity manager: updates durable structured story state

The narrator should remain lightweight. It should not become a long-horizon memory reasoner.

#### Practical mapping onto current codebase

Current `CharacterState` covers private goals, identity anchors, and private interpretation
summaries, while the continuity layer now provides the missing shared story-state structures:

- structured knowledge map through `PublicEvent.known_by` / `observed_by` / `told_to` / `inferred_by`
- active vs background fact separation through recent public events plus retrieved summary blocks
- resolved vs unresolved pressure tracking through `IssueState` lifecycle and filtered active issues
- scene-level continuity state shared across prompts through `SceneState`
- public event memory separated from private interpretation memory
- canon anchors made explicit as protected truths

The issue layer is currently a pressure-first hybrid rather than a fully consequence-native engine:

- issue creation builds a pressure profile from consequence tags, state changes, actionable implications, and bounded text fallback
- matching is primarily driven by participants, `pressure_kind`, blocked objective, and required next step
- update transitions still retain compatibility fallbacks through signal and text heuristics when structural evidence is weak

This means the continuity engine is now structurally grounded, but still intentionally conservative
about removing older fallback behavior.

#### Example conceptual split

- `SceneState`
  - setting
  - current time
  - present actors
  - environment state
  - active tensions
  - resolved tensions
  - scene phase
  - recent delta
  - canon anchors
- `IssueState`
  - issue id
  - participants
  - current status
  - `pressure_kind`
  - `blocked_what`
  - `blocked_characters`
  - `last_change`
  - `required_next_step`
  - escalation / resolution compatibility signals
- public event memory
  - event id
  - participants
  - event type
  - summary
  - story significance
- `CharacterState`
  - long/medium/short objectives
  - emotional state
  - private interpretation memory
  - known fact IDs
  - relationship stance

#### Guardrails for continuity updates

- not every line of dialogue should become an event
- event memory must not become a disguised transcript
- characters should only receive events they know or can plausibly infer
- director reasoning must not be written into character memory as self-truth
- canon anchors should constrain interpretation drift over long sessions

#### Retrieval strategy

Retrieval should begin with deterministic filters such as:

- participants involved
- issue ids
- location
- recency
- story significance

Embeddings may be useful later, but only after event schemas, knowledge boundaries, and deterministic retrieval behavior are stable and debuggable.

#### Why this matters

This is the most important path for improving story quality over long sessions because it addresses:

- repetition
- loss of scene pressure
- character drift
- omniscient responses
- weak long-horizon character development

## Near-Term Roadmap

1. Expand authored `initial_message` asset support during scene creation.
2. Reweight issue updates further toward structured pressure/consequence matching over fallback signal matches.
3. Tighten issue creation confidence without sacrificing continuity stability when classifier output is weak.
4. Strengthen scene state and issue / pressure tracking beyond the current bounded recent-history windows.
5. Continue improving summary retrieval and reload continuity so pressure developments survive compression cleanly.
6. Add deterministic retrieval improvements before evaluating any embedding-based retrieval.

## Benefits

- **Strong separation**: characters can't write for others
- **Objective tracking**: each bot has explicit goals it advances
- **Consistent narration**: narrator controls prose style while dialogue stays character-authored
- **Deliberate orchestration**: director balances spotlight and scene pressure
- **Identity retention**: persistent voice/reaction anchors reduce character convergence
- **Extensible**: foundation for secrets, private knowledge, relationship systems
