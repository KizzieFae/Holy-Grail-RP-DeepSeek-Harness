# Glossary

Terms are aligned with [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) and the current `autogen_rp/python/rp_app` codebase. For file locations, see [MODULE_INDEX.md](./MODULE_INDEX.md). For diagnosis order, see [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

---

## Architecture layers

**Ingestion** — Future pipeline: extract entities, relationships, and events from sources; populate graph/vector stores and compiled profiles. Does not run the live turn loop.

**Packaging** — Bridge layer: merges authoritative state, stable identity, and **retrieved** candidates into **packets** ([PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)). Target seam before AutoGen calls.

**RP runtime / execution** — Live roleplay: Director, orchestration, character agents, Narrator, validation, continuity updates, audit. Implemented today primarily in `rp_app`.

---

## Roles and flow

**Director** — LLM (or agent) that chooses **who acts next** from structured scene/orchestration input. Does not render final prose. Prompt assembly: `app_turn_director.py`, `prompt_builders.py`. Policy is prompt-guided; avoid piling logic into prompts as a substitute for state fixes.

**Narrator** — LLM that turns a **validated structured character move** into scene prose; **dialogue** from the character must stay **verbatim** (`app_turn_rendering.py`, `model_client.py`).

**Orchestration** — Final authority ordering for **who actually speaks**, combining direct address, continuation override, Director output, validation, and progression rules (`orchestration_helpers.py`, PRD §5.3).

**Character agent** — Bot that emits structured JSON: `action`, `dialogue`, `motivation` (see `rp_app/README.md`). Must respect knowledge boundaries enforced by continuity/validation.

---

## State and continuity

**Continuity** — Durable narrative state between turns: scene snapshot, **issues**, **public events**, per-character **interpretations**, **canon anchors**, knowledge propagation. **Authoritative** for “what the fiction has established.” Primary implementation: `continuity_manager.py`, `continuity_state.py`, helpers under `continuity_*`.

**Scene facts / scene locks** — **Allowlisted, typed** entries in the **Scene Grounding** layer: settled logistics, object states, medical facts, communication outcomes. **Derived** from continuity + deterministic rules; **prompt-facing**; **not** a second authority (PRD §5.8, `autogen_rp/docs/scene-grounding-layer.md`).

**Scene Grounding layer (MVP)** — Read-only projection of **scene facts** into Director/character prompts **after** continuity commits. Cleared on scene end; capped count. Implemented in `scene_grounding.py` (markers on `PublicEvent`, rebuild in `turn_runner_updates`; see module index).

**Issue / pressure** — Structured dramatic tension or blocked objective (`IssueState`, lifecycle active → escalating → stalled → resolved, etc.). Director and validators use issue context; not the same as free-form “plot summary.”

**Event** — Structured promotion of what happened (e.g. dialogue/action distilled into `PublicEvent` and related structures). Feeds continuity and summaries—not raw log replay.

**Scene state** — Participants, environment, phase, recent beats—portion of continuity scoped to the current scene (`continuity_scene_helpers.py`, `scene_lifecycle_*`).

---

## Presence and validation

**Presence** — Who is **in the scene** for fiction and prompts. Distinct from “selected cast” UI lists.

**must_remain** — **Presence constraint** from scene templates: character must stay **structurally present** (no unjustified exit/absence). **Not** a rule that they must speak every beat (PRD + `response_validation_presence.py`).

**Validation** — Post-generation checks: parsing, drift, presence, turn-selection consistency (`response_validation*.py`, `semantic_validation.py`). Can trigger retry paths; not the same as continuity **authoring** of state.

---

## Data and packets

**Character card** — JSON file under `python/data/autogen_characters/` defining a persona (system prompt, anchors, relationships, etc.). **Current** primary character source (`character_loader.py`).

**Scene template** — JSON under `python/data/scene_templates/`: premise, roles, `presence_constraint`, optional authority labels, optional static **`progression_profile`** (`advancement_channels`, `common_stall_pattern`) for advisory hints only (`scene_template.py`, PRD §5.7). Structural progression pressure comes from continuity-owned runtime signals, not from this template metadata.

**Progression layer** — The current signal-based progression system. It classifies each turn at scene and issue level using structured deltas only, tracks progression debt and instability tiers, preserves dominant unresolved pressure, and feeds orchestration plus prompt salience without becoming continuity truth (`progression_pressure.py`).

**Progression advisory (support layer)** — Deterministic, **non-authoritative** prompt layer: computes **`stall_score`** from existing scene signals, maps to a prompt-facing pressure band, and may inject **short** Director/character prompt text plus audit metadata. Does **not** write continuity or `CharacterState` (`progression_advisory.py`).

**Progression pressure** — Derived orchestration-state memory for the progression layer: scene / issue debt, instability tiers, dominant issue ids, last-turn classification, and issue-identity continuity notes. Built only from resolved outcomes, issue-state deltas, and consequence-tagged continuity signals (`progression_pressure.py`).

**Stall score** — Float 0.0–1.0 from weighted boolean components (phase plateau snapshots, high tension, stable issue statuses, optional low consequence variety). Same signal can lower the bar for **beat-shift** activation (`beat_shift_state.py`); not LLM-classified.

**Session** — Persisted RP state (chat, team, character states, continuity snapshot, audit pointers, etc.) in `python/data/sessions/` (`session_manager.py`, `session_lifecycle_*`).

**Packet** — **Future** bounded runtime input object assembled by packaging (`RuntimeCharacterPacket`, `RuntimeScenePacket`, `RetrievedContextBundle` — [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)).

**Retrieved context** — **Non-authoritative** snippets from vector/graph search selected for a turn; must be gated and budgeted; never replaces continuity truth (PRD §7).

---

## Auditing

**Audit** — Optional JSON artifacts under `rp_app/data/rp_audits/` for debugging and regression: per-turn Director/character/Narrator payloads, manifests, narrative trace (`audit_logger*.py`, `AUDIT_DOCUMENTATION.md`).

---

## Misc

**Round / response cycle** — User message (or opener) triggers up to **N** bot replies; same character should not act twice in the same cycle (`rp_app/README.md`, `ARCHITECTURE.md`).

**AutoGen** — Microsoft AutoGen stack in `autogen_rp/python/packages/`; `rp_app` uses it for model clients/agents (`model_client.py`).
