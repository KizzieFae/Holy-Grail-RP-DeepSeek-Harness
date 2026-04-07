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

**Prompt assembly note:** Identity and relationship text for character prompts comes from **`CharacterState.to_prompt_identity_context`**. Episodic list formatting (**`character_memory_summary`**, **`recent_observations`**) is owned by **`memory_layer.retrieval`** and composed into a single **`state_context`** string in **`app_turn_prompting.build_character_turn_prompt`** via **`build_character_state_context_for_prompt`**, then passed unchanged into **`prompt_builders.build_character_turn_prompt`**. See **`autogen_rp/docs/architecture.md`** for the full `state_context` contract and fallback-vs-memory invariant.

Commit-time episodic writes are owned by **`memory_layer`** (facade → writes → storage); observer lines are perception-filtered at write time (`perception_audibility`). **`ContinuityManager`** remains authoritative for scene/issue/event truth—do not conflate it with per-character episodic prompt text.

#### Runtime Packet Seam (Phase 0.5 — character prompt path complete)

A **read-only** seam for **character** prompts: **`CharacterPromptInputAssembly`** captures the **exact inputs** to **`prompt_builders.build_character_turn_prompt`** once per turn. **`live_bundle_from_character_prompt_assembly`** and **`runtime_packets_from_character_prompt_assembly`** derive the live kwargs dict and **`RuntimeScenePacket`** / **`RuntimeCharacterPacket`** from that assembly (**no dual derivation**). **`RuntimeScenePacket`** (stable scene slice + session fields) supports this character path; it is **not** yet the full shared-scene packet for Director/Narrator. **`RetrievedContextBundle`** (Phase 2+: optional authored index + episodic merge; non-authoritative). **Continuity and `CharacterState` remain the source of truth**; packets are **normalized projections** for future packaging, not a second store.

- **Phase 2–3.1 retrieval (authored index only):** **Non-authoritative** optional snippets from a **JSON index** on disk (`schema_version` 2 includes **`lore`**). **Phase 3.1:** offline **`authored_index_compile.compile_authored_index`** from a **manifest** → compiled JSON; CLI **`scripts/compile_authored_retrieval_index.py`**. Not vector search, graph DB, transcript mining, or dynamic memory. Selection runs **once** in **`app_turn_prompting.build_character_turn_prompt`** via **`retrieved_context_select.py`**; **`runtime_packets.build_runtime_character_packet`** only receives **`retrieved=`** (no selector calls inside `runtime_packets`). Optional index path: env **`RP_RETRIEVED_CONTEXT_INDEX`**. Primary lane order: **template → setup → world_lore (template/tag match) → self (`character_local` only) → relationship**; per-`source_kind` subcaps; **lore text truncated at selection** if over cap (full text stored in compiled index). Formatted text is injected in **`prompt_builders.build_character_turn_prompt`** **immediately after** the scene grounding block and **before** **CURRENT SCENE STATE** (therefore before **RECENT SCENE TRANSCRIPT** and the rest of the structured prompt). Active retrieval logs at INFO under **`rp_app.retrieved_context`** (item count, char count, `source_ref` list). **Accepted baseline + Phase 4A:** **minimal `lore_facts` + template `role_slots` + `premise`**; activation **only** via **`RP_RETRIEVED_CONTEXT_INDEX`** (optional CLI **`--retrieved-context-index`** on headless sim). **Headless** **`scene_template_id`** for template-aware selection. **Audits:** **`retrieval_summary`** per character turn; **`retrieval_session`** in **`structured_eval`** and merged into **`_audit_summary.json`** after headless runs — see **`AUDIT_DOCUMENTATION.md`**. **Strict** headless verify when ON + template id. **Historical pilot** + **rejected situational cap:** **`data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md`** / **`RP_SETUP_TODO.md`**.
- **Where built:** `app_turn_prompting.build_character_turn_prompt` constructs **`CharacterPromptInputAssembly`**, then the live kwargs bundle, then calls the prompt builder. When env **`RP_PACKET_SHADOW_COMPARE`** is `1`, `true`, or `yes` (default **off**), packets are built **from the same assembly**, reconstructed, and compared. Shadow adds **no** continuity/character-state mutations—only logging on mismatch (`rp_app.packet_shadow`, **stderr**; not audit-persisted). Optional core prompt-text compare when structured bundles match; suffix layers excluded.
- **Validation:** **Structured** comparison of the kwargs-shaped bundle for `prompt_builders.build_character_turn_prompt` (live vs reconstructed from packets + the same `CharacterState` instance), including **`retrieved_context_section`**. Parity corpus: **`tests/test_runtime_packets.py`**. Helpers in **`runtime_packets.py`**; shared ladder/relationship logic in **`prompt_derivations.py`** avoids circular imports.
- **Cast / presence labels (id vs display):** **`prompt_builders.build_cast_and_scene_role_participants`** (with **`prompt_identity_same`**) excludes the acting character from the others-only cast and dedupes **CAST ROLE MAP** inputs using the same **`get_character_display_name_fn`** as live assembly. **`runtime_packets.reconstruct_character_prompt_input_bundle`** requires that resolver for parity with **`app_turn_prompting.build_character_turn_prompt`**. **`prompt_derivations`** still uses raw string equality where it compares names; the normalized **`cast`** list supplied to the prompt builder addresses the id/display duplicate and self-in-others failure mode on this path.
- **Post–#24 validation wave (2026-04-07):** Headless scenario matrix with audits **`session_388`–`session_393`** and sampled character `*_full.json` checks — **no regression** on this seam for the runs recorded under **`SCENARIO_VALIDATION_FRAMEWORK.md`** / **`RP_SETUP_TODO.md`** (Issue Tracking). Identity bleed (**GitHub #1**) was **not** targeted for reproduction; remains **open**.
- **Phase 1 — scoped retrieval-lock (complete):** Inventory confirmed **no retrieval seam bypass** on this path; **`RetrievedContextBundle`** on **`CharacterPromptInputAssembly`** is the **behavioral source**; **`retrieved_context_section`** is **pure derived** from that bundle (**assembly invariant**). Added invariant + snapshot + prompt-shape tests only — **no** new selector behavior, lanes, or retrieval architecture. See **`RP_SETUP_TODO.md`** Phase 1; **`tests/test_phase1_retrieval_seam.py`**.

**Phase 3.4 — canonical knowledge (contract only):** The repo-root **`CANONICAL_KNOWLEDGE_MODEL.md`** defines the **canonical knowledge entry** contract, **authority ceilings** by `knowledge_type`, **`subject_scope`** resolution rules, and **future** graph/vector/agent retrieval compatibility. Phase 3.4 is **spec + static ingestion contract**; it **does not** require changing the runtime retrieval selector, merge behavior, or packet APIs unless a later phase explicitly schedules that work.

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
  },
  "audibility": "public",
  "audience": []
}
```

Optional fields **`audibility`** (`public` \| `directed` \| `private`) and **`audience`** (names, for non-public) are parsed from character JSON when present, then **normalized** in `perception_audibility.py` (including deterministic whisper-style heuristics on structured `action`/`dialogue` only). **Perception boundaries use the structured move as ground truth**; narrator `rendered` prose is not parsed to infer who heard what.

The JSON above is the **stable** self-only core. The pipeline may accept **additional** optional keys; **issue pressure and consequence structure** for the scene are **primarily** produced by **continuity** and reflected in **narrative/orchestration** artifacts. Missing optional keys on the move must **not** be read as “no story pressure changed.”

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
- recent structured character actions (**non-public `dialogue` redacted** in the Director payload)
- public character goal/emotion snapshot
- active issues and recent public events
- recent scene transcript (**perception-filtered**: only **public** beats use full narrator `rendered`; directed/private beats use structured, observable stubs—see `perception_audibility.py`)
- spotlight history and currently available next actors

Director selection policy is prompt-guided rather than hard-coded. It is instructed to:

- treat roles, presence constraints, authority labels, active issues, location, scene phase, and the latest trigger as primary evidence for who should act next
- prefer the smallest relevant pressure core for the current beat instead of rotating the cast for fairness
- treat `must_remain` as structural presence in the scene, not as a requirement to speak every beat
- avoid selecting secondary present characters unless they were directly addressed, are the natural responder, or would create an immediate consequential complication

The Director does not write prose.

#### Hybrid tension pacing (continuity application)

When the Director is **neutral** on directional `tension_shift` (no valid `escalate` / `soften` token), classified consequence tags may recommend a tension nudge **`up`** or **`down`** via `tension_pacing_policy.resolve_hybrid_pacing`, applied in `ContinuityManager._update_scene_state`. **Saturation gate:** consequence-driven **`up`** is **suppressed** when `current_tension_level` is already **`extreme`** (effective `none` / `hold`; character audit `metadata.hybrid_pacing` may set `consequence_up_suppressed_saturation: true`). **Director** explicit `escalate` / `soften` and consequence **`down`** are unaffected. **No** phase- or climax-specific logic in this gate.

**Deterministic selection gates (before / after Director):** `app_turn_director.py` applies **forced speaker** and **continuation override** when eligible. **v1 policy:** if continuation override targets an actor who is already the **last spotlight** speaker, continuation is **skipped** (C2) and the Director runs instead — see `RP_SETUP_TODO.md` Phase 0 §I. After Director output, **progression override** and **participation fairness** may adjust the pick; they are explicitly gated so they do not apply when continuation already fired.

**Progression-gated addressee alignment:** When the **progression enforcement gate** is active for the beat, `semantic_validation.apply_gated_addressee_alignment_under_progression_enforcement` may **override** `decision["next_actor"]` with the resolved semantic **`direct_address_target`** if the semantic assessment is clean (no parse error), confidence ≥ `SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD`, `should_flag_direct_address_miss` is true, and the target is in the available pool. Hybrid pacing and other Director policies are unchanged; this path is **narrow** and **does not** subsume post-validation **fairness_rotation** or general validated-vs-final pick reconciliation (tracked separately: GitHub **#25**).

#### Progression advisory (MVP)

When the deterministic **progression advisory** layer detects elevated **stall pressure**, the Director may receive a short **PROGRESSION ADVISORY** prefix (outside the JSON payload) suggesting advancement channels from the scene template’s optional **`progression_profile`** (e.g. physical action, spatial shift, consequence). This is **guidance only**; it does not override selection logic or continuity.

Beat-shift activation uses the **same** computed **`stall_score`** threshold as this advisory layer (alongside the existing short-user-message path), so there is a **single** plateau-related signal rather than duplicate detectors.

#### Progression enforcement vs continuity classification

When **`stall_score`** is at or above the enforcement threshold (`progression_enforcement.py` / `progression_advisory.STALL_BEAT_SHIFT_THRESHOLD`), the character turn runner may **require** a qualifying structural delta after continuity **`process_turn`**. Qualification uses **Q1–Q4** in **`progression_enforcement.py`**, which read **`turn_metadata_by_index[turn_index]["consequences"]`** and related continuity fields (issues, presence markers, allowlisted `scene_state_updates`). **Continuity remains authoritative:** those consequence strings are produced by **`ContinuityManager._classify_turn_consequences`** → **`ConsequenceClassifier.classify_turn`** (`continuity_consequence_classifier.py`), not by progression enforcement.

**Long-session / progression-retry instability (resolved posture):** Spurious **`validation_progression_retry`** cases where the structured move was materially progressive but **`consequences`** was empty or Q1 was tripped by single-tag repetition were fixed by **improving deterministic consequence classification**, not by weakening enforcement or changing Q1–Q4. Concretely:

- **`REPOSITIONING`** uses bounded movement, locus, and transition substring rules; **`turn`** counts as locomotion only with **word-boundary** verb matching, and **negated** phrases such as “did not turn” / “didn’t turn” / “not turning” are scrubbed so they do not falsely satisfy movement.
- **`REFUSAL`** / stance uses **intent-aligned** rules on goal/tactic (**resist** / **challenge** / extended seeds) plus curated dialogue tokens, **legacy** dialogue markers (`won't`, `refuse`, `deny` remain substring-based), or strong intent phrases—**not** dialogue alone. In the **legacy** path only, **`no`** and **`not`** match as **standalone words** (word-boundary / token style), not raw substrings, so words like "nothing" or "know" do not trigger REFUSAL via those two markers.
- **Multi-tag** emission per turn is preserved (duplicate **categories** deduped); richer tag sets support **Q1** without altering Q1–Q4 definitions.
- **`progression_enforcement.py`** and advisory **thresholds** were **not** relaxed to mask thin classification.

Regression coverage: `python/tests/test_continuity_consequence_classifier.py`.

**Known coverage gap (low priority):** Deterministic rules still omit **`consequences`** for some **low-intensity** beats (passive compliance, soft interaction shifts without geometry or strong stance signals). That is consistent with current design and does not imply incorrect labels when enforcement is stable; broadening sensitivity without inflating Q1 or calm-scene noise is **future work**. Tracked on GitHub: https://github.com/KizzieFae/Holy_Grail_RP/issues/23

#### Exit narrative vs effective on-stage presence

**Resolution (GitHub #18):** **`ContinuityManager.process_turn`** finalizes scene presence (reconcile / invariants) **before** creating **`PublicEvent`**. When **`exit`** is classified but the actor **remains** in **`present_characters`** (e.g. **`must_remain`** or soft exit skip), **`_align_exit_narrative_with_effective_presence`** replaces definitive **“left the immediate scene”**-style **`state_changes`** / matching **`summary`** / standard EXIT **`actionable_implications`** with wording that reflects **retained on-stage presence**. **True** departures (actor **not** on **`present_characters`**) keep the original EXIT phrasing. Classifier, rendering, prompts, and **`tags` / `consequences`** lists were unchanged in that fix.

**Watch:** **`exit`** may still appear in **`tags`** or **`consequences`** when the actor stays on the roster. **`present_characters`** (and related **`SceneState`**) are **authoritative** for whether someone has actually left; do **not** infer physical removal from the **`exit`** tag alone.

#### Scene Grounding layer (MVP)

A **read-only** **SETTLED SCENE FACTS** block is injected into Director and character prompts when facts exist. Facts are a **deterministic, capped, allowlisted** projection **derived from** `PublicEvent.grounding_markers` (computed in continuity classification) — not a second authority (PRD §5.8). See `scene_grounding.py` and `autogen_rp/docs/scene-grounding-layer.md`. Rebuilt in `turn_runner_updates` after each successful continuity `process_turn`; **no** writes to `CharacterState` or continuity.

**Character prompts only — BINDING CONSTRAINTS:** a **high-priority** subsection lists a **filtered** subset of the same promoted facts (allowlisted keys) so the model treats assignment / entry-type settlements as non-deniable in dialogue. Formatted by `format_character_binding_constraints_section` in `scene_grounding.py`, passed as `scene_binding_constraints_section` from `app_turn_prompting`, inserted in `prompt_builders.build_character_turn_prompt` **before** **OUTPUT RULES**.

**Character prompts only — EVIDENCE & AUTHORITY DISCIPLINE:** a **static** instruction block in `prompt_builders.py` (after binding constraints, before **OUTPUT RULES**) discourages stating **unsupported** concrete specifics as clinical / institutional / “noted” fact while still allowing strong pressure and contestable bluffing. Prompt-only; no schema or validator changes.

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
    - Recent structured actions (**`dialogue` redacted** when this character is not allowed to perceive it)
    - Recent scene transcript (**perception-filtered for this character**; full narrator prose for others’ beats only when audibility is `public` or this character is in `audience`)
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

- recent structured moves (**per-recipient**: non-perceivable **`dialogue`** cleared)
- recent scene transcript (**per-recipient** / Director-global-safe via `perception_audibility`)
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
Inspect recent structured moves + recent transcript window (prompt-facing views are perception-filtered)
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

- structured knowledge map through `PublicEvent.known_by` / `observed_by` / `told_to` / `inferred_by` (**`known_by` is authoritative** for retrieval; new events scope knowers by audibility; summaries avoid embedding verbatim non-public **`dialogue`**—see `perception_audibility.public_safe_event_summary`)
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
  - `required_next_step_plateau_*` — streak / last-normalized text / last turn index / whether an **`advanced`** transition occurred in the current streak window; supports `continuity_issue_helpers.apply_mixed_transition_plateau_refresh` (fires after repeated **`advanced`** / **`escalated`** transitions when obligation text is frozen)
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

## Issue Tracking & Investigation Workflow

### A. System of record

- **GitHub Issues** are the system of record for bugs, quality/design work, simulation anomalies, investigations, refactors, and validation follow-up.
- **Project files** (for example `RP_SETUP_TODO.md` at `autogen_rp/python/RP_SETUP_TODO.md`) remain responsible for roadmap, phase structure, architecture notes, and milestones—not for live issue logs.
- **Do not** duplicate detailed issue logs in project files.
- **Reference markdown** in-repo may capture background and acceptance criteria but is **reference-only** for task tracking. **GitHub Issues** hold status, discussion, and closure.

**Non-negotiable tracking rules**

1. GitHub Issues are the **single** source of truth for tracked work.
2. Documentation is **reference only**, not a substitute for Issues.
3. **No issue without evidence** (mandatory fields in **§D**).
4. **One primary Layer** per issue (**§F**).
5. **No implementation before consensus** (`Current status` must reach **`consensus_reached`** before code changes for that issue, except duplicate/withdrawn intake—**§H**).
6. **Quality** and **design_gap** items are **not** silently filed as **bug**; **Type** follows **§E** (PRD authority).
7. **Pattern status** is always explicit (**§I**).
8. **Documentation reviewed and updated** where contracts or behavior changed **before** terminal closure (**§D** checklist).

### A.1 Audit-driven workflow (reference)

Simulation and audit logging produce JSON under `rp_app/data/rp_audits/`. That output **requires interpretation** before work is scheduled; artifacts are **not** a substitute for filed issues. Pipeline: **Simulation → Audit → Interpretation → Issue detection → Classification → Tracking → Fix → Re-test.** Roles, **Type** / **Layer** / **Pattern status**, evidence standards, and heuristic caveats are in **`AUDIT_DOCUMENTATION.md`** → **Audit interpretation and issue tracking**. Deterministic audit layers (v1/v2) and LLM validation logs are **advisory** unless explicitly documented as runtime gates.

### B. Standard workflow

Record progress in the Issue (description updates, comments, checklists). **Status** line must follow **§H**.

1. **Observation** — Unexpected behavior in runs, tests, or review. Open or update an Issue when work may outlive the session. Create on GitHub via **§B.1** (CLI) or the web UI using **`.github/ISSUE_TEMPLATE/holy_grail_rp.yml`** (repository root).
2. **Investigation** — Gather evidence; set **`Current status: investigating`**. Document ruled-out **Layers** in comments.
3. **Consensus** — Agree fix / defer / monitor / won’t fix; align on **Layer** and scope. Set **`Current status: consensus_reached`** before implementation.
4. **Implementation** — Land changes; reference the Issue in commits (`#123`). Set **`Current status: implemented`** when merged or landed.
5. **Validation** — Tests, scenario reruns, checklists in the Issue. Set **`Current status: validated`** when criteria pass.
6. **Closure** — Set terminal **§H** status; GitHub closed when appropriate. Complete **§D** documentation checklist before **`closed`**.

### B.1 Filing issues via GitHub CLI (humans and agents)

Use when creating the Issue on GitHub from a terminal (e.g. agent asked to *file* / *create* / *open* / *track*, not draft-only).

1. Run commands from the **git root** (directory with `.git` whose `origin` hosts Issues).
2. Run `gh auth status`. If auth fails or `gh` is missing, provide full body per **§D** (and semantics **§E–§I**); user may paste into the web UI or run `gh auth login`.
3. Prefer `gh issue create --title "..." --body-file path/to/body.md`. Align **title** with **§G**; optional GitHub **labels** with **§C** (repeat `--label` per label).
4. Share the returned issue URL after success.

Unless the user asked **draft only**, done means the Issue exists on GitHub when `gh` works—not only chat markdown.

### C. Standard GitHub labels (optional adjunct)

Labels do **not** replace **Type** or **Layer** in the body. Default set (do not expand without reason): `bug`, `improvement`, `research`, `tech-debt`, `blocked`. Optional: `validation`, `docs`, `needs-reproduction`.

### D. Issue body template (canonical contract)

Use these sections **in order** (copy into `body.md` or the root issue form).

- **Summary** — One short paragraph.
- **Type** — One of **`bug`** | **`quality`** | **`design_gap`** (definitions **§E**).
- **Layer** — One primary value from **§F** (body field, not a label). If **`other`**, include **justification** and **intended final Layer** per **§F**.
- **Pattern status** — One of **`single_instance`** | **`potential_pattern`** | **`confirmed_pattern`** (rules **§I**).
- **Current status** — Exactly one value from **§H** on a single line: `Current status: <value>`.
- **Evidence (mandatory)** — **Scenario id**; **audit session path** (repo-relative or unambiguous); **turn index** or `n/a` with reason.
- **Evidence (preferred)** — Structured move excerpt; consequence output if applicable; continuity snapshot excerpt if applicable.
- **Expected behavior** — What should happen (cite PRD/architecture when **Type** is **bug** or **design_gap**).
- **Observed behavior** — What happened (concrete fields/paths).
- **Deterministic reasoning** — Why observed violates expected (rules, fields, code path—no hand-waving).
- **System impact** — Operator/user-visible effect.
- **Constraints** — e.g. no LLM-only fix; no prompt workaround; no weakening enforcement; continuity authoritative—or `none`.
- **Affected modules** — Concrete paths (e.g. `autogen_rp/python/rp_app/continuity_consequence_classifier.py`).
- **Validation criteria** — Tests / scenario ids / audit checks required to reach **`validated`**.
- **Documentation** — Before terminal closure: `[ ]` Documentation reviewed and updated where behavior or contracts changed (list files in a closing comment).

Optional: **Severity** (`high` / `medium` / `low`); **Next step** (owner / action).

### E. Type (classification; PRD authority)

**Authority:** [Holy Grail PRD.md](../../../Holy%20Grail%20PRD.md) (repository root) and [ARCHITECTURE_OVERVIEW.md](../../../ARCHITECTURE_OVERVIEW.md) / this file for architecture expectations. If PRD/architecture are silent, prefer **`quality`** or **`design_gap`** until the spec is updated—not **`bug`**.

| Type | Definition |
|------|------------|
| **bug** | Behavior **violates an explicit** must/should/owns expectation in PRD or linked architecture docs. |
| **quality** | Undesirable but **not** specified as incorrect in those documents (calibration, UX, heuristic noise). |
| **design_gap** | Required capability **missing**, or **implied by stated design** but not implemented. |

### F. Layer (primary; mutually exclusive)

Record **one** **Layer** in the issue body. Snake_case identifiers only.

**Boundary (orchestration vs response_validation)**

- If the bug affects **which actor is selected or allowed to act** → **`orchestration`**.
- If the bug affects **validity of a produced character move or narrator structured output** → **`response_validation`** (not “who speaks next”).

#### `consequence_classification`

Deterministic mapping from a **validated structured character move** (and closely coupled exit signals) to **consequence labels** consumed downstream. Does **not** own authoritative state mutation.

**Belongs:** Wrong/missing tags vs structured move; classifier/dedupe logic; `continuity_consequence_classifier.py`; `scene_exit_detection.py` when the fault is **classification from the move**, not applying state.

**Does not belong:** Wrong issues/events/scene after tags are correct → **`continuity_state`**. Wrong Q interpretation → **`progression`**. Wrong prompt projection → **`grounding`**, **`perception`**, **`memory`**, or **`rendering`** as appropriate.

**Examples:** False REFUSAL; missed REPOSITIONING; duplicate classifier emissions for one turn.

#### `continuity_state`

Authoritative **runtime narrative state** after a turn (events, issues, scene, interpretations, knowledge) in **`ContinuityManager`** and continuity helpers.

**Belongs:** Wrong committed state given correct inputs/tags; issue lifecycle; `continuity_manager.py`, `continuity_*_helpers.py`, `turn_runner_updates.py` when **committed truth** is wrong.

**Does not belong:** Tags wrong before commit → **`consequence_classification`**. Next actor wrong → **`orchestration`**. Move invalid → **`response_validation`**.

**Examples:** Exit not applied offstage; stale active issues; wrong event from correct consequences.

#### `progression`

Deterministic **stall / advisory / enforcement** reading continuity-emitted signals. Does **not** author consequences or continuity truth.

**Belongs:** Q1–Q4, retries, gates, `stall_score`, `progression_advisory`, beat-shift enforcement hooks.

**Does not belong:** Wrong consequence strings → **`consequence_classification`**. Wrong continuity issues → **`continuity_state`**.

**Examples:** Retry when Q satisfied; wrong qualification; `stall_score` inconsistent with committed scene signals.

#### `orchestration`

Turn flow: **who may act next**—address, continuation, spotlight, forced speaker, Director merge, **selection-path** validation whose purpose is **choosing or allowing the next actor** (including `response_validation_selection.py` when the defect is **selection outcome or eligibility**).

**Belongs:** Wrong `next_actor` / pool / continuation; `orchestration_helpers.py`, `app_turn_director.py`, `semantic_validation.py` for selection reconciliation.

**Does not belong:** Character/narrator **payload** validity (parse, presence, duplicate dialogue) → **`response_validation`**.

**Examples:** Ineligible actor selected; addressee skipped against rules; selector decisions contradict policy.

#### `response_validation`

Validation of **character** and **narrator** **structured outputs**—whether a **produced move or narrator payload** is **valid** under rules—**excluding** the Director **selection** pipeline (**`orchestration`** owns that).

**Belongs:** `response_validation_parsing.py`, `response_validation_content.py`, `response_validation_presence.py`, `response_validation_drift.py` (and peers) for character/narrator validation.

**Does not belong:** Which actor Director picked → **`orchestration`**. Classifier tags → **`consequence_classification`**. Grounding text wrong with valid move → **`grounding`**.

**Examples:** False must_remain; duplicate-line false positive; malformed move rejection when schema should pass.

#### `grounding`

Scene **grounding** read model: settled facts, binding constraints, **projection into prompts** (non-authoritative vs continuity).

**Belongs:** `scene_grounding.py`; grounding-related prompt assembly when facts/bindings disagree with continuity snapshot.

**Does not belong:** Continuity never updated truth → **`continuity_state`**. Dialogue visibility → **`perception`**.

**Examples:** Missing BINDING CONSTRAINTS; stale SETTLED SCENE FACTS vs continuity.

#### `perception`

**Knowledge boundaries** for prompt assembly: who may see others’ dialogue / rendered text / filtered tails (`perception_audibility` and call sites).

**Belongs:** Leaks or incorrect withholding in per-character prompts.

**Does not belong:** Wrong continuity knowledge records → **`continuity_state`**. Retrieval bundle → **`memory`**.

**Examples:** Whisper visible to wrong character; offstage sees full dialogue against rules.

#### `memory`

Episodic compile/select/cache and **retrieved context** merge into bundles and prompt sections (non-authoritative vs continuity).

**Belongs:** `memory_layer/`, `episodic_memory_*.py`, merge/format of `RetrievedContextBundle` given continuity inputs.

**Does not belong:** Continuity wrote wrong events → **`continuity_state`**. Perception gating → **`perception`**.

**Examples:** Empty episodic when events exist; wrong merge caps/order; retrieval summary inconsistent with bundle passed to prompts.

#### `rendering`

Narrator / UI **presentation** path; dialogue verbatim contract in rendered output.

**Belongs:** `app_turn_rendering.py`, narrator presentation bugs.

**Does not belong:** Move validation → **`response_validation`**. Committed state wrong → **`continuity_state`**. Audit file shape → **`audit_simulation`**.

**Examples:** Paraphrased dialogue in chat; render ordering bug.

#### `audit_simulation`

Observability and **behavioral harness**: headless runs, audit writers, metrics / `structured_eval` when the fault is **instrumentation or driver**, not runtime truth.

**Belongs:** Missing/wrong audit fields; broken `--audit`; CLI/scenario driver bugs.

**Does not belong:** Runtime wrong with correct audits → owning **Layer** above.

**Examples:** `_audit_summary.json` missing promised blocks; misaligned turn indices in artifacts.

#### `application_infrastructure`

Cross-cutting: Streamlit shell, session plumbing, encoding/IO, env/deps, **authored asset loaders** when the bug is **mechanical** (path/schema load), not wrong narrative semantics after load.

**Belongs:** `app.py` wiring; mojibake; broken data paths.

**Does not belong:** Wrong scene semantics after clean load → domain **Layer**. Audit format → **`audit_simulation`**.

**Examples:** Session key loss on rerun; bad encoding in saved JSON.

#### `other`

Allowed **only** when: **(1)** non-runtime (process/tooling/repo workflow outside the Layers above), **or** **(2)** **`Current status` is `investigating`** and the body includes a **target Layer hypothesis** (intended final Layer).

**Always required for `other`:** **justification** (why no named runtime Layer applies yet, or why the issue is non-runtime) and **intended final Layer** (for triage: where the issue should land after investigation). **`other`** is **not** terminal for runtime bugs once **`consensus_reached`**—reclassify to a concrete **Layer**.

**Tie-break order (deterministic):** wrong tags from move → **`consequence_classification`**; wrong state given correct tags → **`continuity_state`**; wrong gate/retry from metadata → **`progression`**; wrong next actor → **`orchestration`**; wrong move/narrator payload validity → **`response_validation`**; wrong facts/bindings in prompts, continuity correct → **`grounding`**; wrong visibility of others’ text → **`perception`**; wrong episodic/retrieved bundle → **`memory`**; wrong final prose path → **`rendering`**; wrong audit/sim artifact → **`audit_simulation`**; load/encoding/UI shell → **`application_infrastructure`**.

### G. Title conventions

Prefix by **Type**:

- `[BUG]` — **bug**
- `[QUALITY]` — **quality**
- `[DESIGN_GAP]` — **design_gap**

Example: `[BUG] Orchestration selects ineligible actor under continuation override`.

### H. Status (single active; transitions)

**Allowed values:** `open` | `investigating` | `consensus_reached` | `implemented` | `validated` | `closed` | `monitor` | `wont_fix`

**Representation:** exactly one line in the body: `Current status: <value>`.

**Allowed transitions**

| From | To |
|------|-----|
| `open` | `investigating` |
| `investigating` | `consensus_reached` |
| `consensus_reached` | `implemented` |
| `implemented` | `validated` |
| `validated` | `closed` |
| `investigating` | `monitor` |
| `investigating` | `wont_fix` |

**Exception:** `open` → `closed` only for **duplicate** or **withdrawn** filings (document in a comment). No other skips (e.g. do not jump from `open` to `implemented`).

Terminal statuses: **`closed`**, **`monitor`**, **`wont_fix`**.

### I. Pattern status (discipline)

1. **Audit-only (no GitHub Issue):** Incomplete mandatory evidence (scenario id, audit session path, turn index or documented `n/a`) **or** purely heuristic audit noise without runtime contradiction—keep in audit notes until evidence is complete and **Pattern status** can be assigned.
2. **`single_instance`:** Allowed only when mandatory evidence is complete **and** impact is **high** (integrity, safety, hard contradiction across truth layers, blocking repro), **or** the team explicitly accepts a one-shot fix with documented risk. Otherwise wait for repetition.
3. **`potential_pattern`:** Two or more similar instances **or** one strong instance plus a clear code signature suggesting repeat risk.
4. **`confirmed_pattern`:** Same signature across **distinct** scenarios or sessions (or repeated runs showing the same failure mode).
5. **Escalation:** `single_instance` → `potential_pattern` when a second instance matches; `potential_pattern` → `confirmed_pattern` when the signature holds across distinct scenarios/sessions. Downgrade if evidence shows operator error or invalid run.
6. **Type** is independent of **Pattern status**; do not use **bug** without **§E** and **consensus**.

### J. Guiding principles

- Do **not** open Issues for trivial or disposable thoughts.
- **Do** open Issues when work may need investigation, implementation, validation, or later reference—subject to **§I**.
- Keep roadmap files phase-oriented; keep investigative history in Issues.
- **Reference Issues in commits** (`#nnn` / `Fixes #nnn` when appropriate).
- **Avoid duplicating** long narratives between Issues and repo markdown; link out.

### K. Flexibility clause

> These conventions are the current standard and may be refined by explicit doc change.
