# Glossary

Conceptual vocabulary for Holy Grail RP. Product intent: [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md). System topology: [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md).

For **symptom → owner** routing and current module names, use [MODULE_INDEX.md](./MODULE_INDEX.md). For diagnosis order, use [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md). This glossary is **not** a module-path catalog.

---

## Runtime topology (current)

**DSH (DeepSeek Harness)** — Node RP runtime under `v2/rp_runtime/`. Owns the turn loop, Cordis phase plugins (Director, character generation, Narrator), and HTTP integration with the Domain Host. Python domain code does **not** call DSH.

**Domain Host** — Python service under `v2/domain_api/`. Owns session lifecycle, continuity commit, validation call sites, knowledge projection, and prompt assembly inputs consumed by DSH.

**Cordis** — Phase-plugin architecture inside DSH: each beat runs through named phases (Director decision, character move, validation, Narrator render, continuity commit via Host).

**Presentation UI** — `v2/ui/` client of the Node application API; does not load domain modules directly.

---

## Architecture layers

**Ingestion** — Offline pipeline: authored JSON (characters, templates, manifests) is compiled or normalized into retrieval-ready artifacts. Does not run the live turn loop.

**Packaging** — Merge layer: combines authoritative continuity state, stable identity, scene-facing projections, and **retrieved** candidates into bounded **packets** ([PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)) before LLM calls.

**RP runtime / execution** — Live roleplay: Director selection, character agents, Narrator rendering, validation, continuity updates, optional audit. Implemented in **DSH + Domain Host** (`v2/rp_runtime/`, `v2/domain_api/`, `v2/domain/modules/`).

---

## Roles and flow

**Director** — Chooses **who acts next** from structured scene/orchestration input. Does not render final prose. In DSH, Director execution is a Cordis phase plugin; context preparation and decision validation live in Domain Host.

**Narrator** — Turns a **validated structured character move** into scene prose; character **dialogue** from the move must stay **verbatim**.

**Orchestration** — Final authority for **who actually speaks**, combining direct address, continuation rules, Director output, validation, and progression policy.

**Character agent** — Emits structured JSON: `action`, `dialogue`, `motivation`, and optionally **`audibility`** / **`audience`**. Knowledge boundaries combine continuity (who knows what) with **perception/audibility** rules so each character prompt reflects what that actor may treat as known.

---

## State and continuity

**Continuity** — Durable narrative state between turns: scene snapshot, **issues**, **public events**, per-character **interpretations**, **canon anchors**, knowledge propagation. **Authoritative** for what the fiction has established. Primary implementation: `continuity_manager.py`, `continuity_state.py`, and related helpers under `v2/domain/modules/`.

**Continuity authority (#224)** — **`SceneState`** and the continuity **commit** path (`ContinuityManager.process_turn`) own **committed** presence and narrative state. Audits, mirrors, orchestration **`consequences`**, and classifier tags are **observational** or auxiliary unless they reflect **already-committed** facts. **Narrator rendered prose** is not continuity authority. Umbrella: [Issue #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224).

**Intent (continuity evidence)** — What the **structured character move** expresses. Input to processing — not, alone, proof of **commit**.

**Interpretation (continuity evidence)** — Classifier output, exit heuristics, audit summaries, and similar **readings** of the move or scene. May inform continuity; **not** a substitute for **`SceneState`** as proof of **commit**.

**Commit (continuity evidence)** — What continuity **adopts** on the authoritative path for a beat.

**Observation (continuity evidence)** — Audit rows, scene-state mirrors, session narrative **`consequences`**, tags, and other telemetry. **Observational** unless tied to facts **already** committed in continuity.

**Scene facts / scene locks** — **Allowlisted, typed** entries in the **Scene Grounding** layer: settled logistics, object states, medical facts, communication outcomes. **Derived** from continuity + deterministic rules; **prompt-facing**; **not** a second authority (PRD §5.8, [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md)).

**Scene Grounding layer (MVP)** — Read-only projection of **scene facts** into Director/character prompts **after** continuity commits. Cleared on scene end; capped count. See [MODULE_INDEX.md](./MODULE_INDEX.md) → Scene Grounding.

**BINDING CONSTRAINTS (character prompt)** — High-priority bullet list of a **filtered** subset of grounded facts injected only into **character** system prompts so dialogue does not **deny** promoted settlements. Distinct from the full **SETTLED SCENE FACTS** block.

**Issue / pressure** — Structured dramatic tension or blocked objective (`IssueState`, lifecycle active → escalating → stalled → resolved, etc.). Director and validators use issue context; not the same as free-form plot summary.

**Event** — Structured promotion of what happened (e.g. dialogue/action distilled into `PublicEvent` and related structures). **`PublicEvent`** is a durable **committed-occurrence/evidence boundary**: not merely a prose summary, not a duplicate Continuity state store, and not an execution log. Rows represent **knowability** for retrieval: **`known_by`** (and aligned **`observed_by`**) are scoped by **audibility**; **`summary`** is the audibility-safe headline. **`state_changes`** and classifier tags describe **what kind** of occurrence was classified; they must not replace specific semantic meaning when move-specific evidence exists. Optional **`occurrence_evidence`** (Issue #51) carries bounded **`contributions[]`**, **`triggering_user`**, **`structured_fact_refs[]`**, and **`scoped_evidence[]`** without copying full moves or Continuity registries. Turn **`summary_selection_source`** in `turn_metadata_by_index` records which semantic branch produced the promoted summary (audit observability only).

**`recent_delta`** — Internal continuity-owned synopsis finalized after a turn commits and event promotion completes. It is persisted for local state compatibility but is not projected as a second progression timeline; prompt-facing progression uses committed `PublicEvent`s plus phase/tension.

**`tension_shift`** — Normalized Director auxiliary pacing token: `escalate`, `soften`, or `steady`. `steady` is Director-neutral and permits consequence-derived pacing; unsupported values normalize to `steady`.

**continuity_turn_index (audit)** — Integer on audit **`context_snapshot`**: **post-commit** **`ContinuityManager.turn_counter`** for that beat. Primary structural join key for offline audit pairing. **Not** a runtime control signal.

**Turn (structural) vs event (`PublicEvent`)** — A **structural turn** is identified by the continuity **turn counter** after a beat commits. A **`PublicEvent`** is an optional **promoted** narrative fact for that turn; **event absence does not mean the turn did not commit**.

**Consequence classification** — Deterministic tagging of structured character moves (e.g. **`refusal`**, **`repositioning`**) feeding turn metadata and progression signals.

**Scene state** — Participants, environment, phase, recent beats — portion of continuity scoped to the current scene.

---

## Presence and validation

**Presence** — Who is **in the scene** for fiction and prompts. Distinct from UI cast selection lists.

**must_remain** — **Presence constraint** from scene templates: character must stay **structurally present** (no unjustified exit/absence). **Not** a rule that they must speak every beat.

**Validation** — Post-generation checks: parsing, drift, presence, turn-selection consistency. Can trigger retry paths; not the same as continuity **authoring** of state.

---

## Data and packets

**Authored source contract** — [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md). Canonical **authored file types**: **Character**, **Template**, **Scenario / Bootstrap**, **Opener**. Retrieval manifests are compile-time inputs, not bootstrap truth.

**Bootstrap (scenario)** — Authored **scene-start contract** JSON (`bootstrap_schema_version`, `id`, `character_refs`, optional `template_ref`, `opening`, `first_round_user_line`, `initial_continuity`, etc.). Distinct from **session** state and from Character/Template knowledge files.

**Opener** — Authored **opening prose** asset, referenced from bootstrap `opening`. Not a substitute for Template structure.

**Character card** — JSON under `data/characters/` defining a persona. **Normative field set** per **Authored source contract**; legacy keys may remain until migration.

**Scene template** — JSON under `data/scene_templates/`: premise, roles, `presence_constraint`, optional authority labels. Template-associated support files (openers, progression payloads) are **not** the canonical Template body.

**Progression advisory (MVP)** — Deterministic, **non-authoritative** layer: **`stall_score`**, **`progression_pressure`**, optional short prompt text, audit metadata. Does **not** write continuity or `CharacterState`.

**Stall score** — Float 0.0–1.0 from weighted scene signals. Same signal arms beat-shift and progression enforcement when at or above threshold; not LLM-classified.

**Session** — Persisted RP state under `data/sessions/` (or `HG_SESSIONS_DIR`): chat, character states, continuity snapshot, metadata. See [docs/rp-data-layout.md](./docs/rp-data-layout.md).

**Packet** — Bounded runtime input projection (`RuntimeCharacterPacket`, `RuntimeScenePacket`, `RetrievedContextBundle` — [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)). Character inference context is assembled as Domain Host **`PromptContributionManifest`** contributions (including **`recent_scene_transcript`** and **`user_turn_trigger`** from durable `rp_history`), transported by DSH **`HgContextBridge`**, with continuity-backed state, grounding, cross-session buckets (when enabled), and formatted retrieval.

**Prompt contribution** — A single model-facing inference input lane (`PromptContribution`) or packaged collection (`PromptContributionManifest`). Prompt contributions are **not** forensic retention channels; audit artifacts stay in durable evidence stores unless explicitly distilled into an authorized model-facing contribution (#134). Host and Bridge enforce per-inference **`source_kind` allowlists** and reject invalid packages atomically.

**Retrieved context** — **Non-authoritative** snippets from compiled indexes or scope knowledge, selected per turn under caps. Never replaces continuity truth (PRD §7).

**Cross-session memory** — Optional aggregation of bounded text buckets from **prior saved sessions** when starting a new scene with overlapping cast. Controlled by `RP_CROSS_SESSION_MEMORY`. See [docs/cross_session_memory.md](./docs/cross_session_memory.md).

---

## Auditing

**Audit** — Optional JSON artifacts under `data/rp_audits/` for debugging and regression. Interpretation: [docs/audit-workflows.md](./docs/audit-workflows.md), [governance/sources/audit-semantics.md](./governance/sources/audit-semantics.md).

---

## Historical aliases (interpretive only)

These terms appear in **historical records** or pre-DSH program docs. They are **not** current stack names:

| Term | Meaning today |
|------|----------------|
| **AutoGen stack** / **rp_app runtime** | Retired V1 Python runtime; replaced by DSH + Domain Host |
| **V1 turn-loop modules** | Retired pre-DSH Python turn assembly (`Director`, `Narrator`, prompting helpers) |
| **Legacy `python/data` paths** | Retired path prefix; product data lives under `data/` |

When reading historical PRDs or workshop records under `governance/records/`, treat path and module names as **period-accurate**, not live navigation.

---

## Narrator environmental response (#49)

**EnvironmentalCurrentView** — Deterministic Host projection of **authored environmental baseline** plus **story-derived B2** descriptors for the active location. Surfaces effective properties, supersession, conflicts, and bounded recent changes. Not LLM-inferred.

**Narrator environmental packet** — Bounded manifest lane `narrator_environment_baseline` assembled from `EnvironmentalCurrentView` for Narrator pre-render cognition and render. Separate from Scene Grounding logistics.

**Environmental descriptor (B2)** — Continuity-bearing perceptible property on a persistent referent, persisted as a **derived** StoryKnowledge record (`event_type=environmental_descriptor`) only after **Host deterministic establishment** accepts a Narrator **proposal**. Distinct from Narrator self-classification.

**Environmental taxonomy (N2)** — **A** established/mediated detail; **B1** ephemeral presentation texture (non-persistent); **B2** persistent environmental descriptor (Host-gated); **C** material story fact (not Narrator-establishable); **cannot_safely_resolve** when ambiguity/failure blocks invention.

**Proposal vs acceptance** — Narrator N2 may **propose** B2; **Host** (`host_environmental_b2_validation`) emits a durable `decision_id` that authorizes `#50` persistence and `EpistemicAuthorityRef`. Narrator classification alone does not establish truth.

---

## Misc

**Round / response cycle** — User message (or opener) triggers up to **N** bot replies; same character should not act twice in the same cycle unless orchestration rules allow.

**Canonical knowledge entry** — Compiled envelope for injectable knowledge (`knowledge_id`, `authority_class`, etc.). Spec: [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md).
