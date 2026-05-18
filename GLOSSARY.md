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

**Orchestration** — Final authority ordering for **who actually speaks**, combining direct address, continuation override (with **v1 C2** skip when last spotlight already matches continuation — `app_turn_director.py`, `RP_SETUP_TODO.md` §I), Director output, validation, and progression rules (`orchestration_helpers.py`, PRD §5.3).

**Character agent** — Bot that emits structured JSON: `action`, `dialogue`, `motivation`, and optionally **`audibility`** / **`audience`** (see `rp_app/README.md`). Knowledge boundaries combine continuity (`PublicEvent` knowers, interpretations) with **`perception_audibility.py`** (per-recipient prompts; structured move is the perception source of truth).

---

## State and continuity

**Continuity** — Durable narrative state between turns: scene snapshot, **issues**, **public events**, per-character **interpretations**, **canon anchors**, knowledge propagation. **Authoritative** for “what the fiction has established.” Primary implementation: `continuity_manager.py`, `continuity_state.py`, helpers under `continuity_*`. **Authority posture (GitHub #224):** **`SceneState`** and the **`ContinuityManager.process_turn`** path own **committed** continuity truth; see **Continuity authority (#224)** below.

**Continuity authority (#224)** — Reconciled doctrine that **`SceneState`** / continuity **commit** path is authoritative for **committed** presence and narrative state; **audits**, **mirrors**, orchestration **`consequences`**, and **classifier tags** are **observational** or auxiliary unless they reflect **already-committed** facts. **Narrator `rendered` prose** is not continuity authority. Umbrella record: **[Issue #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224)**; vocabulary table: **`autogen_rp/python/rp_app/ARCHITECTURE.md`** (*Continuity authority and evidence lanes*). Related work: [#225](https://github.com/KizzieFae/Holy_Grail_RP/issues/225), [#226](https://github.com/KizzieFae/Holy_Grail_RP/issues/226), [#227](https://github.com/KizzieFae/Holy_Grail_RP/issues/227) (do not treat as replacing #224 doctrine).

**Intent (continuity evidence)** — What the **structured character move** expresses (beats, motivation, etc.). **Input** to processing — not, alone, proof of **commit**.

**Interpretation (continuity evidence)** — Classifier output, exit heuristics, audit summaries, and similar **readings** of the move or scene. May inform continuity; **not** a substitute for **`SceneState`** as proof of **commit**.

**Commit (continuity evidence)** — What continuity **adopts** on the authoritative path (**`process_turn`**, pipeline-backed mutations, reconciled presence) for a beat.

**Observation (continuity evidence)** — Audit rows, **`scene_state_after`** mirrors, session narrative **`consequences`**, **tags**, and other telemetry. **Observational** unless tied to the same facts **already** committed in continuity.

**Scene facts / scene locks** — **Allowlisted, typed** entries in the **Scene Grounding** layer: settled logistics, object states, medical facts, communication outcomes. **Derived** from continuity + deterministic rules; **prompt-facing**; **not** a second authority (PRD §5.8, `autogen_rp/docs/scene-grounding-layer.md`).

**Scene Grounding layer (MVP)** — Read-only projection of **scene facts** into Director/character prompts **after** continuity commits. Cleared on scene end; capped count. Implemented in `scene_grounding.py` (markers on `PublicEvent`, rebuild in `turn_runner_updates`; see module index).

**BINDING CONSTRAINTS (character prompt)** — High-priority bullet list of a **filtered** subset of grounded facts (e.g. sleeping surface, location entry) injected only into **character** system prompts so dialogue does not **deny** promoted settlements; built by `format_character_binding_constraints_section` in `scene_grounding.py`. Distinct from the full **SETTLED SCENE FACTS** block. **EVIDENCE & AUTHORITY DISCIPLINE** — static instructions in `prompt_builders.py` (after binding text, before OUTPUT RULES) to avoid stating unsupported concrete specifics as clinical / institutional fact.

**Issue / pressure** — Structured dramatic tension or blocked objective (`IssueState`, lifecycle active → escalating → stalled → resolved, etc.). Director and validators use issue context; not the same as free-form “plot summary.”

**Event** — Structured promotion of what happened (e.g. dialogue/action distilled into `PublicEvent` and related structures). Feeds continuity and summaries—not raw log replay. **`PublicEvent`** rows represent **knowability** for retrieval: **`known_by`** (and aligned **`observed_by`**) are scoped by **audibility**; **`summary`** avoids verbatim non-public **`dialogue`** via `public_safe_event_summary` at promotion time. **`event_id`** is **semantic** and **optional** by beat; offline audit joins prefer **`continuity_turn_index`**, not **`event_id`**, when both rows carry the former (Issue #72 — **`AUDIT_DOCUMENTATION.md`**).

**continuity_turn_index** (audit) — Integer on **`context_snapshot`** in full per-turn audit rows: **post-commit** **`ContinuityManager.turn_counter`** for that beat. **Primary structural join key** for narrator↔character audit pairing (**manual/scripted** offline analysis today; **specified** for deferred Issue **#69** offline evaluator — **`AUDIT_DOCUMENTATION.md`**). **Not** a runtime control signal.

**Turn (structural) vs event (`PublicEvent`)** — A **structural turn** is identified by the continuity **turn counter** after a beat commits. A **`PublicEvent`** is an optional **promoted** narrative fact for that turn when continuity creates one; **event absence does not mean the turn did not commit** (Issue #72).

**Consequence classification** — Deterministic tagging of structured character moves into categories such as **`refusal`** and **`repositioning`** (`continuity_consequence_classifier.py` → `ContinuityManager._classify_turn_consequences`), feeding turn metadata and progression Q1. For **REFUSAL**, **legacy** dialogue markers **`no` / `not`** match as **standalone tokens** (word boundaries), not raw substrings, avoiding false positives inside words like "nothing" or "know"; other legacy markers (`won't`, `refuse`, `deny`), curated REFUSAL phrases, and strong-intent phrases are unchanged. See `autogen_rp/python/rp_app/ARCHITECTURE.md` (*Progression enforcement vs continuity classification*).

**Scene state** — Participants, environment, phase, recent beats—portion of continuity scoped to the current scene (`continuity_scene_helpers.py`, `scene_lifecycle_*`).

---

## Presence and validation

**Presence** — Who is **in the scene** for fiction and prompts. Distinct from “selected cast” UI lists.

**must_remain** — **Presence constraint** from scene templates: character must stay **structurally present** (no unjustified exit/absence). **Not** a rule that they must speak every beat (PRD + `response_validation_presence.py`).

**Validation** — Post-generation checks: parsing, drift, presence, turn-selection consistency (`response_validation*.py`, `semantic_validation.py`). Can trigger retry paths; not the same as continuity **authoring** of state.

---

## Data and packets

**Authored source contract** — **[AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)**. Canonical **authored file types**: **Character** (durable knowledge), **Template** (reusable structure), **Scenario / Bootstrap** (deterministic scene-start contract), **Opener** (authored opening prose). **Not** canonical template knowledge: `initial_messages`, `progression_profile`; **not** canonical character knowledge: `agent_name`. **`opening_text`** on templates is legacy fallback. **Retrieval manifests** are compile-time inputs, not bootstrap truth.

**Bootstrap (scenario)** — Authored **scene-start contract** JSON (`bootstrap_schema_version`, `id`, `character_refs`, optional `template_ref`, `opening` with `strategy` / `ref`, `first_round_user_line`, `initial_continuity`, etc.). Distinct from **session** state and from **Character**/**Template** knowledge files; see **Authored source contract**.

**Opener** — Authored **opening prose** asset, referenced from bootstrap `opening` when strategy is asset-based; not a substitute for **Template** structure. In **Streamlit**, the **template** defines which template-scoped openers are **available**; the applied opener is **selected** at bootstrap (**#101**, **#108**). The sidebar shows **label** and **description** (file-level) and requires an explicit **selection** when more than one opener exists for that **template**. **`character_asset`** is for authored bootstrap, headless / CLI, and legacy paths, not the Streamlit Start Scene UI. Headless runs use manifest/composition inputs instead of that UI.

**Character card** — JSON file under `python/data/autogen_characters/` defining a persona (system prompt, anchors, relationships, etc.). **Current** primary character source (`character_loader.py`). **Normative field set** per **Authored source contract**; on-disk files may still carry legacy keys until migration.

**Scene template** — JSON under `python/data/scene_templates/`: premise, roles, `presence_constraint`, optional authority labels. **Template-associated support files** in the same directory (e.g. `{template_id}_progression.json` for **Template Exclude** `progression_profile` per **Authored source contract** §1) supply advisory-only channel lists for **Progression Advisory** (`progression_advisory.py`, PRD §5.7). **`progression_profile`** is **not** in canonical `template_id`.json. **`opening_text`** is legacy fallback, not the primary opener model.

**Progression advisory (MVP)** — Deterministic, **non-authoritative** layer: computes **`stall_score`** from existing scene signals, maps to **`progression_pressure`**, and may inject **short** Director/character prompt text plus audit metadata. Does **not** write continuity or `CharacterState` (`progression_advisory.py`).

**Stall score** — Float 0.0–1.0 from weighted boolean components (phase plateau snapshots, high tension, stable issue statuses, optional exact structural repetition vs the immediate prior same-actor move). Same signal arms **beat-shift** (`beat_shift_state.py`) and **progression enforcement** when at or above the threshold; not LLM-classified.

**Session** — Persisted RP state (chat, team, character states, continuity snapshot, audit pointers, etc.) in `python/data/sessions/` (`session_manager.py`, `session_lifecycle_*`).

**Packet** — Bounded runtime input projection (`RuntimeCharacterPacket`, `RuntimeScenePacket`, `RetrievedContextBundle` — [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)). **Phase 0.5:** **Character** prompt path uses **`CharacterPromptInputAssembly`** and packet builders/reconstruction at the **`build_character_turn_prompt`** seam; Director/Narrator not yet on the same mechanical path. **Cast / others lists** in the character prompt use **`get_character_display_name_fn`** for live and reconstructed bundles so **id vs display** labels do not duplicate roster rows or list the actor under **OTHER PRESENT CHARACTERS**.

**Retrieved context** — **Non-authoritative** snippets from vector/graph search selected for a turn; must be gated and budgeted; never replaces continuity truth (PRD §7).

---

## Auditing

**Audit** — Optional JSON artifacts under `rp_app/data/rp_audits/` for debugging and regression: per-turn Director/character/Narrator payloads, manifests, narrative trace (`audit_logger*.py`, `AUDIT_DOCUMENTATION.md`).

---

## Misc

**Round / response cycle** — User message (or opener) triggers up to **N** bot replies; same character should not act twice in the same cycle (`rp_app/README.md`, `ARCHITECTURE.md`).

**AutoGen** — Microsoft AutoGen stack in `autogen_rp/python/packages/`; `rp_app` uses it for model clients/agents (`model_client.py`).
