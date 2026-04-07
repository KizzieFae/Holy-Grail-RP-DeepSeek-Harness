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

**Deterministic selection gates (before / after Director):** `app_turn_director.py` applies **forced speaker** and **continuation override** when eligible. **v1 policy:** if continuation override targets an actor who is already the **last spotlight** speaker, continuation is **skipped** (C2) and the Director runs instead — see `RP_SETUP_TODO.md` Phase 0 §I. After Director output, **progression override** and **participation fairness** may adjust the pick; they are explicitly gated so they do not apply when continuation already fired.

#### Progression advisory (MVP)

When the deterministic **progression advisory** layer detects elevated **stall pressure**, the Director may receive a short **PROGRESSION ADVISORY** prefix (outside the JSON payload) suggesting advancement channels from the scene template’s optional **`progression_profile`** (e.g. physical action, spatial shift, consequence). This is **guidance only**; it does not override selection logic or continuity.

Beat-shift activation uses the **same** computed **`stall_score`** threshold as this advisory layer (alongside the existing short-user-message path), so there is a **single** plateau-related signal rather than duplicate detectors.

#### Progression enforcement vs continuity classification

When **`stall_score`** is at or above the enforcement threshold (`progression_enforcement.py` / `progression_advisory.STALL_BEAT_SHIFT_THRESHOLD`), the character turn runner may **require** a qualifying structural delta after continuity **`process_turn`**. Qualification uses **Q1–Q4** in **`progression_enforcement.py`**, which read **`turn_metadata_by_index[turn_index]["consequences"]`** and related continuity fields (issues, presence markers, allowlisted `scene_state_updates`). **Continuity remains authoritative:** those consequence strings are produced by **`ContinuityManager._classify_turn_consequences`** → **`ConsequenceClassifier.classify_turn`** (`continuity_consequence_classifier.py`), not by progression enforcement.

**Long-session / progression-retry instability (resolved posture):** Spurious **`validation_progression_retry`** cases where the structured move was materially progressive but **`consequences`** was empty or Q1 was tripped by single-tag repetition were fixed by **improving deterministic consequence classification**, not by weakening enforcement or changing Q1–Q4. Concretely:

- **`REPOSITIONING`** uses bounded movement, locus, and transition substring rules; **`turn`** counts as locomotion only with **word-boundary** verb matching, and **negated** phrases such as “did not turn” / “didn’t turn” / “not turning” are scrubbed so they do not falsely satisfy movement.
- **`REFUSAL`** / stance uses **intent-aligned** rules on goal/tactic (**resist** / **challenge** / extended seeds) plus curated dialogue tokens or strong intent phrases—**not** dialogue alone.
- **Multi-tag** emission per turn is preserved (duplicate **categories** deduped); richer tag sets support **Q1** without altering Q1–Q4 definitions.
- **`progression_enforcement.py`** and advisory **thresholds** were **not** relaxed to mask thin classification.

Regression coverage: `python/tests/test_continuity_consequence_classifier.py`.

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

- **GitHub Issues** are the system of record for:
  - bugs
  - observed behavior problems
  - simulation anomalies
  - investigations and research threads
  - approved improvements and refactors
  - validation and follow-up work

- **Project files** (for example `RP_SETUP_TODO.md` at `autogen_rp/python/RP_SETUP_TODO.md`) remain responsible for:
  - roadmap and phase structure
  - architecture and system design
  - completion criteria and milestones

- **Do not** duplicate detailed issue logs in project files.

### A.1 Audit-driven workflow (reference)

Simulation and audit logging produce JSON under `rp_app/data/rp_audits/`. That output **requires interpretation** before work is scheduled; artifacts are **not** a substitute for filed issues. Methodology—pipeline (**Simulation → Audit → Interpretation → Issue detection → Classification → Tracking → Fix → Re-test**), roles (AI-assisted vs human), taxonomy (**bug** / **behavior** / **limitation**), evidence standards, heuristic signal limitations, and GitHub body fields—is documented in **`AUDIT_DOCUMENTATION.md`** → **Audit interpretation and issue tracking**. Deterministic audit layers (v1/v2) and LLM validation logs are **advisory** for observability unless explicitly documented as runtime gates.

### B. Standard workflow

Use this lifecycle; record progress in the Issue (description updates, comments, checklists).

1. **Observation** — Something unexpected is seen in runs, tests, or review. Note repro context and severity. Open or update an Issue when it may outlive the current session. When the issue should exist on GitHub and you are not only drafting text, create it using **§B.1** (CLI) or the web UI with the template in **§D**.

2. **Investigation** — Narrow cause, gather evidence (logs, audits, scenario IDs). Document hypotheses and ruled-out layers in comments.

3. **Consensus** — Agree on whether to fix, defer, or monitor; align on suspected layer and scope.

4. **Implementation** — Land changes; reference the Issue in commits (`#123`).

5. **Validation** — Confirm with tests, scenario reruns, or checklists defined in the Issue. **Closure happens after validation**, not merely after merge.

6. **Closure** — Close when validated, or close as **monitor** when no fix is required but the thread should remain discoverable.

**Rules of thumb:**

- Create an Issue when work may **persist beyond the current session**.
- Close Issues **only after validation** (or explicit **monitor** / **won’t fix** with rationale).
- Issues may be closed as **monitor** when no code change is required but observation is recorded.

### B.1 Filing issues via GitHub CLI (humans and agents)

Use this when creating the Issue on GitHub from a terminal—for example when an agent is asked to *file*, *create*, *open*, or *track* an issue, not merely to produce draft markdown.

1. Run commands from the **git root** of this repository (the directory that contains `.git` and whose `origin` remote is the GitHub repo where Issues live).
2. Run `gh auth status`. If authentication fails or `gh` is missing, say so and still provide the full issue body (**§D–§F**); the user can paste into the web UI or run `gh auth login`.
3. Prefer `gh issue create --title "..." --body-file path/to/body.md` over inline `--body` to avoid escaping problems. Align `--title` with **§F** and `--label` with **§C** (repeat `--label` for each label).
4. After a successful create, share the returned issue URL.

Unless the user explicitly asked for a **draft only**, treating the task as done means opening the issue on GitHub when `gh` is available and authenticated—not only pasting issue text in chat.

### C. Standard labels (explicit)

**Default label set** (do not expand without good reason):

- `bug`
- `improvement`
- `research`
- `tech-debt`
- `blocked`

**Optional** (add only when needed):

- `validation`
- `docs`
- `needs-reproduction`

Avoid growing the label set unnecessarily; prefer a small, consistent vocabulary.

### D. Issue structure (explicit template)

Use this as the **standard** issue body format:

- **Summary** — One short paragraph.
- **Type** — GitHub label alignment (`bug`, `improvement`, `research`, …). Optionally add a **taxonomy** line: **bug** (defect), **behavior** (needs validation or calibration), or **limitation** (known heuristic/design constraint)—see **`AUDIT_DOCUMENTATION.md`** → **Audit interpretation and issue tracking**. **Not all Issues are defects.**
- **Suspected layer** — Single value from the convention below (body field, not a label).
- **Area** — Optional but recommended: subsystem tag in prose (e.g. `continuity`, `progression`, `narrator`, `character`, `prose`, `audit/simulation`).
- **Severity** — Optional: `high` / `medium` / `low` (or narrative equivalent) when it helps triage.
- **Scenario / context** — How to reproduce or where it showed up (scenario id, UI path, command).
- **Observed behavior** — What actually happened.
- **Expected behavior** — What should happen instead (or success criteria for research).
- **Evidence** — Pointers to audits, commits, transcripts, metrics files (session id, artifact paths, fields).
- **Current assessment** — Confirmed / likely / unknown / watchlist; brief rationale.
- **Next step** — Who does what next (investigate, implement, rerun sim, etc.).
- **Validation criteria** — How we will know the Issue is truly done (tests, scenarios, audited re-runs, sign-off).

### E. Suspected layer convention

Record **Suspected layer** in the issue body (not as a label). Use one of:

- `progression`
- `continuity`
- `director`
- `grounding`
- `perception/audibility`
- `narrator`
- `memory/episodic`
- `orchestration`
- `audit/simulation`
- `unknown`

### F. Title conventions

Prefix titles for scanability:

- `[BUG]` — defects and incorrect behavior
- `[IMPROVEMENT]` — intentional behavior changes or enhancements
- `[RESEARCH]` — open investigation, spike, or pattern hunt
- `[TECH-DEBT]` — cleanup, refactors, maintainability

Example: `[BUG] Director skips addressee under low pressure`.

### G. Guiding principles

- Do **not** open Issues for trivial or disposable thoughts.
- **Do** open Issues for anything that may need investigation, implementation, validation, or **later reference**.
- Keep roadmap files **clean and phase-oriented**; avoid turning them into issue logs.
- Keep **high-churn investigative history** in Issues (comments and edits), not in duplicated markdown.
- **Reference Issues in commits** (`#nnn` or `Fixes #nnn` when appropriate).
- **Avoid duplicating** long narratives between Issues and repo markdown; link out instead.

### H. Flexibility clause

> These conventions represent the current standard workflow for this project and may be refined over time as the system evolves.
