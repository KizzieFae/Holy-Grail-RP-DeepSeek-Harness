# Packet contracts (intent)

These are **architectural contracts** for the **packaging layer** described in [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md). They describe the **integration seam** between knowledge/retrieval and the **RP runtime** (`v2/domain/modules/`, orchestrated by DSH + Domain Host).

**Authored sources vs runtime:** **Character / Template / Scenario (bootstrap) / Opener** JSON authoring rules live in **[AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)**. **This document** describes **turn-time packets** and **retrieval bundles**.

**Implementation status (DSH / Domain Host):** Character turn context is assembled as **`PromptContributionManifest`** contributions in Domain Host **`kernel.prepare_context`** (`v2/domain_api/kernel.py`), including bounded **`recent_scene_transcript`** and **`user_turn_trigger`** projections from durable `rp_history` (perception-filtered). DSH **`HgContextBridge`** transports manifests to inference without reinterpreting domain semantics. Knowledge projection and retrieval selection run in **`KnowledgeService.project_context`** (`v2/domain_api/knowledge_service.py`), using **`retrieval_selection.py`**, **`authored_knowledge.py`**, and optional **`CompiledIndexRetrievalProvider`** (`compiled_index_provider.py`). Legacy **`prompt_builders.build_character_turn_prompt`** retains formatting reference semantics but is not the live V2 composition path. Continuity commit remains in Domain Host.

**Durable `rp_history` presentation semantics (#12):** Each `presentation` entry records `presentation_status` (`rendered` | `failed`), `metadata.presentation_source` (`narrator` | `committed_fallback`), and provider-neutral `metadata.inference_outcome` (`succeeded` | `empty_output` | `inference_error` | optional `output_limit`). UI/history transcript projection (`project_history_to_transcript`) may show narrator prose or committed-move fallback display text. Character manifest transcript projection (`project_history_to_character_context_chat` → `recent_scene_transcript`) uses narrator prose only when provenance/outcome indicate a successful narrator presentation; failed, committed-fallback, or `output_limit` rows pair with the durable `committed_turn.metadata.structured_move` snapshot and reuse perception/audibility formatting. Narrator presentation is non-authoritative relative to committed continuity; provider finish objects stay in runtime only.

For runtime behavior and guardrails, see [docs/architecture.md](./docs/architecture.md) and [MODULE_INDEX.md](./MODULE_INDEX.md).

---

## Design rules

1. **Stable vs dynamic** — Identity and long-lived voice/world anchors change slowly; per-turn overlays and retrieved snippets change every turn.
2. **Authoritative vs retrieved** — Scene truth, issues, presence, and knowledge boundaries come from **runtime continuity** (authoritative). Retrieval supplies **candidates**; packaging **selects and bounds** them. Neither vectors nor raw cards are “truth” for state.
3. **Runtime receives packets, not raw stores** — Agents consume **assembled** prompt projections, not ad-hoc store calls mid-turn.

---

## RuntimeCharacterPacket

**Intent:** Everything a **single character agent** needs for **one** generation step, already **merged and budgeted**.

| Grouping | Stability | Role |
|----------|-----------|------|
| Identity core | Stable | Name, persistent traits, canon anchors, core goals — aligned with card fields that must not be summarized away |
| Voice / style | Mostly stable | Profiles and fingerprints guiding diction; may include **examples** from retrieval later |
| Scene-facing slice | Dynamic (authoritative) | Subset of shared scene truth relevant to this actor: location, phase, who is present, active pressures/issues |
| Relationship overlays | Mixed | Structured relationship state toward others + user; trends as summaries |
| Retrieved context | Dynamic (non-authoritative) | Scoped retrieval records / formatted section (see below) |
| Knowledge constraints | Authoritative | What this character may/must not treat as known (boundaries from continuity) |
| Cross-session buckets | Dynamic (optional) | Aggregated prior-session strings when `RP_CROSS_SESSION_MEMORY` is enabled |

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
| **Settled scene facts** (Scene Grounding MVP) | Dynamic (derived, read-only) | Capped, allowlisted **facts/locks** projected from continuity for prompt coherence — not a second authority ([PRD](./governance/sources/holy-grail-prd.md) §5.8, [spec](./docs/scene-grounding-layer.md)) |

This packet **does not** replace the continuity manager’s full internal state; it is the **projection** used for prompts and decisions.

---

## RetrievedContextBundle

**Intent:** **Per-turn**, **optional**, **bounded** context — **inputs to packaging**, not to validation truth.

**Current implementation (M11–M12):**

- **Authored knowledge** — Compiled from setup snapshot via `authored_knowledge.compile_authored_records_from_snapshot` and merged in `KnowledgeService.project_context`.
- **Compiled retrieval index (optional)** — When `RP_RETRIEVED_CONTEXT_INDEX` or `HG_RETRIEVAL_INDEX_PATH` points at a JSON index under `data/retrieval/compiled/`, `CompiledIndexRetrievalProvider` supplies additional rows; `retrieval_selection.select_retrieval_records` applies deterministic caps and dedupe.
- **Scope knowledge lanes** — User profile / learned-world records via `ScopeKnowledgeRepository` when enabled by product policy.
- **Formatting** — Selected records become formatted retrieval blocks in Host manifest contributions (or equivalent non-authoritative sections), with explicit **non-authoritative** labeling. Live character path: **`KnowledgeService`** → manifest contributions consumed via **`HgContextBridge`**.

**Activation:**

```text
RP_RETRIEVED_CONTEXT_INDEX=<path-to-compiled-index.json>
# or
HG_RETRIEVAL_INDEX_PATH=<same>
```

**Accepted baseline content** (operational): character `lore_facts` + template `role_slots` + refined `premise` from the reference manifest (`data/retrieval/manifests/operational_pilot.json` → `data/retrieval/compiled/operational_pilot_v3.json`). Historical pilot runbook: [governance/records/operational-retrieval-pilot.md](./governance/records/operational-retrieval-pilot.md).

**Authority ordering (unchanged):** continuity → scene grounding → binding constraints → **retrieved (non-authoritative)**. Retrieval must not override continuity commits or settled grounding facts.

**Retrieval-lock discipline:** On the character path, retrieval enters prompts **only** through the validated Host seam (`KnowledgeService` → prompt builder). No parallel ad-hoc retrieval injection mid-turn.

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

## Evolution path (documentation commitment)

1. Map card + continuity + prompt sections → packet fields above **without behavior change**. **(Character path:** live V2 composition is Domain Host **`PromptContributionManifest`** → **`HgContextBridge`** (`kernel.prepare_context`, including **`recent_scene_transcript`** / **`user_turn_trigger`** from `rp_history`); legacy monolithic `build_character_turn_prompt` remains reference-only, not production.)
2. Extend the same packet discipline so **Director / Narrator** consumers share explicit bundle boundaries where not already structured.
3. Wire additional retrieval outputs only into the retrieved lane (character path: **done** via `KnowledgeService` + selection caps).

Scenario validation for retrieval OFF/ON: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Related

- [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md) — compiled knowledge envelope
- [docs/rp-data-layout.md](./docs/rp-data-layout.md) — on-disk manifests and compiled indexes
- [GLOSSARY.md](./GLOSSARY.md) — conceptual vocabulary
