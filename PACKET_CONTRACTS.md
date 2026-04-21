# Packet contracts (intent)

These are **architectural contracts** for the **packaging layer** described in [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) §§3.2, 4.1–4.3. They describe the **integration seam** between knowledge/retrieval and the **RP runtime** (`autogen_rp/python/rp_app`).

**Authored sources vs runtime:** **Character / Template / Scenario (bootstrap) / Opener** JSON **authoring** rules — what belongs in **files on disk** vs session vs ingestion manifests — live in **[AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)**. **This document** describes **turn-time packets** and **retrieval bundles**, not the authored JSON layout.

**Implementation status (Phase 0.5 — character prompt path):** The **mechanical seam** for **character** generation is implemented in **`runtime_packets.py`** + **`app_turn_prompting.py`**: **`CharacterPromptInputAssembly`** holds exactly the inputs required for **`prompt_builders.build_character_turn_prompt`** (this is the **seam boundary** for that path). **`RuntimeScenePacket`** and **`RuntimeCharacterPacket`** are built from that assembly; **`reconstruct_character_prompt_input_bundle`** rebuilds the same kwargs shape from packets + **`CharacterState`** and **must** receive the same **`get_character_display_name_fn`** as live assembly so **cast** / **OTHER PRESENT CHARACTERS** / **CAST ROLE MAP** inputs match: **id and display labels are treated as the same character** for actor exclusion and order-preserving dedupe (`prompt_builders.build_cast_and_scene_role_participants` / `prompt_identity_same`). **Shadow validation:** `RP_PACKET_SHADOW_COMPARE` — structural bundle equality (required); optional core prompt-text equality excluding beat-shift/progression suffixes. **Not yet:** Director or Narrator prompt paths do not consume this assembly; **`RuntimeScenePacket`** in code today supports the character path (stable scene slice + session fields), not the full shared-scene abstraction described below for every consumer. **Known gap:** shadow results log to **stderr** (`rp_app.packet_shadow`); they are **not** written into audit JSON yet.

For runtime behavior today, see `autogen_rp/python/rp_app/ARCHITECTURE.md` and `prompt_builders.py`.

**Post–#24 headless validation (2026-04-07):** Six scenario configurations with **`--audit`** confirmed sampled character prompts remained consistent with the cast/reconstruction contract (audits **`session_388`–`session_393`**; **`structured_eval`** JSON under `autogen_rp/python/validation_runs/plan_execution/`). **No regression** of id/display roster assembly on that evidence set. See **`SCENARIO_VALIDATION_FRAMEWORK.md`**.

---

## Design rules

1. **Stable vs dynamic** — Identity and long-lived voice/world anchors change slowly; per-turn overlays and retrieved snippets change every turn.
2. **Authoritative vs retrieved** — Scene truth, issues, presence, and knowledge boundaries come from **runtime continuity** (authoritative). Retrieval supplies **candidates**; packaging **selects and bounds** them. Neither vectors nor raw cards are “truth” for state.
3. **Runtime receives packets, not raw stores** — AutoGen agents should consume **assembled** packets, not ad-hoc DB/graph calls mid-turn.

---

## RuntimeCharacterPacket

**Intent:** Everything a **single character agent** needs for **one** generation step, already **merged and budgeted**.

| Grouping | Stability | Role |
|----------|-----------|------|
| Identity core | Stable | Name, persistent traits, canon anchors, core goals — aligned with card fields that must not be summarized away |
| Voice / style | Mostly stable | Profiles and fingerprints guiding diction; may include **examples** from retrieval later |
| Scene-facing slice | Dynamic (authoritative) | Subset of shared scene truth relevant to this actor: location, phase, who is present, active pressures/issues |
| Relationship overlays | Mixed | Structured relationship state toward others + user; trends as summaries |
| Retrieved context | Dynamic (non-authoritative) | `RetrievedContextBundle` scoped to this character (see below) |
| Knowledge constraints | Authoritative | What this character may/must not treat as known (boundaries from continuity) |

**Not in scope here:** raw JSON card path on disk, full chat transcript, or unbounded tool logs.

---

## RuntimeScenePacket

**Intent:** **Shared** context for Director, Narrator, and cross-character prompts — the “table” everyone agrees on for this beat.

| Grouping | Stability | Role |
|----------|-----------|------|
| Participants | Dynamic | Who is in scene; control mode (player vs bot) where relevant |
| Environment & phase | Dynamic | Setting, tone, scene phase / beat |
| Active issues / pressures | Dynamic | Issue list and metadata the Director and validators use |
| Recent structured history | Dynamic | Bounded windows of events/moves/dialogue **as chosen by packaging** from authoritative continuity |
| Template / role context | Setup-time | Template id, premise, role assignments, presence constraints (when using templates) |
| **Settled scene facts** (Scene Grounding MVP) | Dynamic (derived, read-only) | Capped, allowlisted **facts/locks** projected from continuity for prompt coherence — not a second authority ([PRD](./Holy%20Grail%20PRD.md) §5.8, [spec](./autogen_rp/docs/scene-grounding-layer.md)) |

This packet **does not** replace the continuity manager’s full internal state; it is the **projection** used for prompts and decisions.

---

## RetrievedContextBundle

**Intent:** **Per-turn**, **optional**, **bounded** context — **inputs to packaging**, not to validation truth. **Phase 2–3.1:** snippets from a **deterministic authored JSON index** (`retrieved_context_select.py`, env `RP_RETRIEVED_CONTEXT_INDEX`). **Phase 3.1:** index is **`schema_version` 2** with optional **`lore`**; JSON is produced offline by **`authored_index_compile.compile_authored_index`** from a **manifest** (CLI: `autogen_rp/python/scripts/compile_authored_retrieval_index.py`). **Phase 3.2:** when **`RP_EPISODIC_MEMORY`** is enabled, **bounded episodic** lines (compiled from explicit continuity rows only) are **merged** into the same bundle lane (`source_kind` prefixes such as `episodic:`), under a **single global cap** with authored winning ties — still **not** vector/graph/transcript-wide. **Later:** vector/graph/search pipelines may feed the same bundle shape.

**Retrieval-lock (Phase 1 — scoped validation, complete):** On the **character** path, retrieval enters the runtime **only** through the validated seam: the bundle is built in **`app_turn_prompting.build_character_turn_prompt`**, stored on **`CharacterPromptInputAssembly.retrieved_bundle`**, and the prompt string **`retrieved_context_section`** is **always** derived via **`format_retrieved_context_for_prompt(live_bundle_from_character_prompt_assembly(...))`** — **no parallel retrieval path**, **no seam bypass**. Phase 1 added **assembly invariant**, **bundle composition** snapshots/goldens, **prompt-shape** / **authority** placement tests, and **shadow** pytest coverage; it did **not** introduce new retrieval architecture, selector behavior, or lanes.

**Operational pilot baseline (accepted, documented):** The **reference** manifest compiles to **`schema_version` 3** and retrieves **minimal character `lore_facts`** plus **template `role_slots` + `premise`** (refined premise text in source templates). **Headless** supplies **`scene_template_id`** so template-scoped rows are selected on the same path as Streamlit. Retrieval stays **non-authoritative** and **bundle-driven**. A **low-tension template-row cap** experiment was **not adopted** and is **not** in the default selector. See `autogen_rp/python/data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md` and `autogen_rp/python/RP_SETUP_TODO.md`.

**Phase 4A (operationalized testing):** Standard simulation supports retrieval **OFF/ON** via **`RP_RETRIEVED_CONTEXT_INDEX`** (optional CLI `--retrieved-context-index`). Audits record **`retrieval_summary`** per character turn and **`retrieval_session`** at run level in headless **`structured_eval`** / merged **`_audit_summary.json`** (see `rp_app/AUDIT_DOCUMENTATION.md`). **No** change to bundle shape or selector.

**Placement:** formatted block is injected **after** scene grounding and **before** `CURRENT SCENE STATE` in `prompt_builders.build_character_turn_prompt`, with explicit **non-authoritative** instructions. Selection runs **only** in `app_turn_prompting.build_character_turn_prompt`.

Typical contents (all subject to token budget and relevance gates):

- Snippets of **past interactions** or summarized moments
- **Relationship** highlights (who to whom)
- **Emotional / behavioral** patterns (lightweight, not a second continuity engine)
- **World knowledge** excerpts (lore), clearly labeled as reference

**Explicit non-responsibilities:**

- Storing canonical “what happened” (that remains events/issues in continuity)
- Deciding **must_remain** or presence (orchestration/validation)
- Replacing Director logic

---

## Evolution path (documentation-only commitment)

1. Map today’s card + continuity + prompt sections → fields above **without behavior change**. **(Done for character path:** assembly + packets + reconstruction + shadow compare; see **Implementation status** above.)
2. Extend packaging so **Director / Narrator** (and any other consumers) can use the same packet discipline; runtime eventually reads packets as the primary input boundary instead of ad hoc assembly.
3. Wire retrieval outputs only into `RetrievedContextBundle` (character path: **done** via `app_turn_prompting`).

Track tasks: `autogen_rp/python/RP_SETUP_TODO.md` (Phase 1 scoped **retrieval-lock** validation **closed**; Phase 0.5 character path **closed**; Phase 2 retrieval, Phase 3.1 authored compile, Phase 3.2 bounded episodic; **operational retrieval pilot closed**; **Phase 4A retrieval workflow operationalization complete** — standard OFF/ON sim + audit visibility, no selector change).
