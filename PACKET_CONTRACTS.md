# Packet contracts (intent)

These are **architectural contracts** for the **packaging layer** described in [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md). They describe the **integration seam** between knowledge/retrieval and the **RP runtime** (`v2/domain/modules/`, orchestrated by DSH + Domain Host).

**Authored sources vs runtime:** **Character / Template / Scenario (bootstrap) / Opener** JSON authoring rules live in **[AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)**. **This document** describes **turn-time packets** and **retrieval bundles**.

**Implementation status (DSH / Domain Host):** Character turn context is assembled as **`PromptContributionManifest`** contributions in Domain Host **`kernel.prepare_context`** (`v2/domain_api/kernel.py`), including bounded **`recent_scene_transcript`** and **`user_turn_trigger`** projections from durable `rp_history` (perception-filtered). Director context (`kernel.prepare_director_context`) adds bounded **`recent_orchestration`**, **`actor_suitability`**, and **`scene_pressures`** digests; authoritative skip-aware **`user_turn_source`**; optional derived **`user_steering_hints`**; plus existing **`scene_setup`**, **`scene_state`**, **`scene_progression`**, **`recent_environment`**, and related authoritative lanes. Director semantic QA (#26) uses **`POST /v1/director/semantic-qa/context/prepare`** with the same scene evidence plus candidate package. DSH **`HgContextBridge`** transports manifests to inference without reinterpreting domain semantics. Knowledge projection and retrieval selection run in **`KnowledgeService.project_context`** (`v2/domain_api/knowledge_service.py`), using **`retrieval_selection.py`**, **`authored_knowledge.py`**, and optional **`CompiledIndexRetrievalProvider`** (`compiled_index_provider.py`). Legacy **`prompt_builders.build_character_turn_prompt`** retains formatting reference semantics but is not the live V2 composition path. Continuity commit remains in Domain Host.

**#32 S3a (Storyteller cognition — isolated slice):** Host **`storyteller_service.py`** + contracts (`storyteller_contract.py`) implement orientation → `KnowledgeAccessRequest` → validated #34 Librarian read path → informed assessment → **`StorytellerAdvisoryPackage`**. DSH substrate: **`storyteller-cognition-substrate.mjs`**. Host endpoints: **`POST /v1/storyteller/orientation/prepare|finalize`**, **`POST /v1/storyteller/assessment/prepare|finalize`**. Anti-railroading validation is deterministic. **Consumer wiring not implemented:** packages are produced/validated in isolation; **`kernel.prepare_*`** role manifests and round orchestrator are unchanged.

**#32 S3b (Storyteller → Packaging mapper):** Host **`storyteller_packaging_mapper.py`** maps validated **`StorytellerAdvisoryPackage`** slices into suggestive **`storyteller_*`** `PromptContribution` lanes via deterministic consumer policies (`storyteller_packaging_policy.py`) and a validity gate (`storyteller_packaging_validity.py`). Packaging does not rerank, reinterpret, or regenerate Storyteller advice. **`PreservationSignal`** is not mapped to consumer lanes.

**#34 S4a (Librarian write-side proposal seam — implemented):** post-commit **`LibrarianSemanticProposal`** batches via Host **`prepare_librarian_proposal_context`** / **`finalize_librarian_proposals`** and DSH **`runLibrarianProposalGeneration`**. Host validates grounding (`evidence_anchors`, catalog closure, no PreservationSignal evidence); Continuity **`evaluate_librarian_proposal_batch`** accepts or rejects **without durable mutation** in S4a. Fail-open: inference/validation failure leaves baseline deterministic Continuity behavior unchanged. **Not implemented:** heuristic-class migration (S4b/S5), automatic durable commits from accepted proposals.

**#32 S3c (Storyteller live round integration — Model A):** DSH **`runStorytellerCognition`** runs once after **`hg/round-started`** and before the first Director attempt; Host **`bind_storyteller_advisory_package`** stores round-local advisory state. While the package remains valid, **`kernel.prepare_director_context`** and **`prepare_context`** inject validated S3b mapper output for Director and scoped Character consumers. Authoritative **`commit_move`** invalidates the package (`authoritative_commit`) **before** Narrator; **`prepare_narrator_context`** therefore receives **no** Storyteller lanes in the normal V2 flow (Narrator renders from committed/authoritative context). The S3b Narrator mapper remains a **validated future socket** for an optional post-commit refresh policy — not live in S3c. Storyteller remains optional — failures skip advisory injection and baseline runtime continues. **Not implemented:** post-commit Storyteller refresh, #34 write-side proposals, unbounded refresh loops, actor-selection authority changes.

**#34 S2b (Librarian → Packaging mapper):** Host **`librarian_packaging_mapper.py`** maps validated **`LibrarianKnowledgeBundle`** output into **`librarian_knowledge`** / **`librarian_synthesis`** `PromptContribution` lanes via deterministic consumer policies (`librarian_packaging_policy.py`) and a validity gate (`librarian_packaging_validity.py`). Packaging does not rerank, reinterpret, or regenerate Librarian output. Character **`prepare_context`** is unchanged in S2b; a **`storyteller`** consumer policy exists as a future #32 socket without Packaging injection yet.

**Durable `rp_history` presentation semantics (#12, hardened #24, #29):** Each `presentation` entry records `presentation_status` (`rendered` | `failed`), `metadata.presentation_source` (`narrator` | `degraded_deterministic_fallback` | `committed_fallback`), optional `metadata.presentation_degraded` (boolean), and provider-neutral `metadata.inference_outcome` (`succeeded` | `empty_output` | `inference_error` | `output_limit`). Successful narrator publication requires normalized `complete` completion, non-empty prose, and deterministic speech fidelity (Issue #24). Output-limited, unknown, fidelity-rejected, or otherwise terminal rejected narrator prose is **not** persisted as successful presentation; after recovery is exhausted, terminal failure uses a deterministic renderer of the authoritative committed `structured_move` when available (`degraded_deterministic_fallback`, #29), otherwise committed-turn summary text (`committed_fallback`). Forensic execution evidence retains rejected partial text. UI/history transcript projection (`project_history_to_transcript`) shows narrator prose only for successful narrator presentation, otherwise degraded/fallback display text. Character manifest transcript projection (`project_history_to_character_context_chat` → `recent_scene_transcript`) uses narrator prose only when provenance/outcome indicate a successful narrator presentation; failed, degraded/fallback, or `output_limit` rows pair with the durable `committed_turn.metadata.structured_move` snapshot and reuse perception/audibility formatting. Provider finish objects are normalized at runtime via canonical classes (`complete`, `output_limit`, `provider_error`, `unknown`) with raw finish preserved in execution evidence.

**Explicit Skip Turn (#13):** `kind: player_skip` records non-dialogue player advance intent (`POST /api/turns/skip` → `record_player_skip` → `runRound`). Skip does not create user conversational memory or `kind: user` history. `user_turn_trigger` is suppressed when a `player_skip` entry follows the latest substantive user entry; prior user text may remain in `recent_scene_transcript` as historical context only.

For runtime behavior and guardrails, see [docs/architecture.md](./docs/architecture.md) and [MODULE_INDEX.md](./MODULE_INDEX.md).

---

## Knowledge mediation architecture (#33 — target vs current)

Parent program **#33** closed with accepted child architecture on **#31** Retrieval, **#34** Librarian, and **#32** Storyteller. **None of the target layers below are implemented in production runtime yet** except the legacy Character retrieval path documented under **RetrievedContextBundle**.

### Accepted responsibility model

| Layer | Role at packaging boundary |
|-------|----------------------------|
| **Retrieval (#31)** | Candidate access under hard visibility/budget constraints; provenance-bearing records; no final semantic relevance |
| **Librarian (#34)** | `KnowledgeAccessRequest` → provenance-aware `LibrarianKnowledgeBundle`; optional `LibrarianSemanticProposal` post-commit |
| **Storyteller (#32)** | Advisory `StorytellerAdvisoryPackage` → suggestive role lanes via deterministic Packaging mapping |
| **Packaging** | Assembles `PromptContributionManifest`; does not rank or reinterpret semantic/narrative meaning |
| **Continuity** | Authoritative truth; live projection always stage-current |

**Principles:** Librarian may interpret committed truth; it may not manufacture truth. Storyteller output is suggestive only; invalidated Storyteller packages are not injected. Contextual intelligence proposes meaning; deterministic authority decides legality and records truth.

### Target bundles (S2a validated; S2b mapper landed)

- **`LibrarianKnowledgeBundle`** — bounded, provenance-aware information plane output from Librarian read path (S2a validated at `db67e05`); may include suggestive cross-source synthesis with explicit source refs; coexists with fresh authoritative projection each stage.
- **`LibrarianKnowledgeBundle` → Packaging** — S2b deterministic mapper (`librarian_packaging_mapper.py`) projects bundle slices into **`librarian_knowledge`** / **`librarian_synthesis`** lanes under consumer policy; stale bundles are omitted; live authoritative lanes remain separate.
- **`LibrarianSemanticProposal`** — post-commit grounded proposal batch (**S4a implemented**): `proposal_id`, `proposal_kind`, non-empty `evidence_anchors`, `derivation_summary`, `confidence`, typed `proposed_payload`, Librarian provenance, `commit_binding` (`domain_commit_id`, post_commit). Continuity validation accepts/rejects; **no durable mutation in S4a**. Heuristic migration deferred to S4b/S5.
- **`StorytellerAdvisoryPackage`** — round-scoped advisory narrative assessment (**S3a validated**); **S3b Packaging mapper validated**; **S3c live integration (Model A):** Director + Character while valid; commit invalidates before Narrator.

### Current implementation seam

**RetrievedContextBundle** (below) remains the **live Character retrieval-to-packaging path**. **Librarian S2b** adds the mapper seam but does **not** replace Character retrieval/memory lanes or wire into `kernel.prepare_context` yet. **Librarian S4a** adds post-commit **`LibrarianSemanticProposal`** prepare/finalize + Continuity accept/reject boundary without heuristic migration or durable mutation. **Storyteller S3a/S3b/S3c (Model A):** round-start package maps to suggestive `storyteller_*` lanes for **Director and scoped Character** while valid; authoritative commit invalidates the package before Narrator, so Narrator normally receives no Storyteller advisory. Optional future post-commit refresh could activate the validated S3b Narrator mapper. Storyteller does not affect actor selection or Continuity truth.

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

## Shared semantic QA result envelope (#25)

**Intent:** Common **evaluator output** and **authority-reference** transport for Director/Narrator bounded semantic QA (#25 substrate; wired in production via #26/#27). Character continues using `hg_semantic_evaluation_result_v1` on its existing path.

**Schema:** `hg_semantic_qa_result_v1` — parsed by `v2/domain/modules/semantic_qa_envelope.py` and `v2/rp_runtime/src/lib/semantic-qa-envelope.mjs`.

| Field | Role |
|-------|------|
| `evaluation_target_role` | Subject under QA (`director` \| `narrator` \| `character`) |
| `evaluation_pass_id` | Correlation id linking candidate → evaluator evidence |
| `overall_result` | Evaluator-stated `pass` \| `reject_soft` \| `reject_hard` (role policy interprets) |
| `findings[]` | Opaque per-role `dimension` ids; `severity`; optional `authoritative_citation.ref_id` |
| `evaluator_summary` | Optional neutral summary (no correction policy) |

**Authority references (semantic QA lane):** records with `authority_class` `authoritative` \| `derived` \| `advisory`. Shared citation validation reports membership/class **without** mutating finding severity or promoting advisory material to continuity truth.

**Runtime substrate:** `semantic-qa-substrate.mjs` invokes evaluator inference (`role: semantic_evaluator` in execution evidence) and returns parse/citation sidecars to role integration. Durable candidate patches use **`decision.semantic_qa`** including **`policy_action`** (#28). Role children own rubrics, context enrichment, acceptance/retry/fallback.

**Host assembly:** `semantic_qa_context.py` provides role-neutral manifest assembly helpers. Director semantic QA prepare is implemented at **`POST /v1/director/semantic-qa/context/prepare`** (#26). Narrator semantic QA prepare is implemented at **`POST /v1/narrator/semantic-qa/context/prepare`** (#27): bounded authority references from the same legitimate Narrator source surface (committed move slices, authoritative scene lanes, derived director decision, public events) plus candidate presentation package; no Narrator context enrichment program.

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
