# Packet contracts (intent)

These are **architectural contracts** for the **packaging layer** described in [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md). They describe the **integration seam** between knowledge/retrieval and the **RP runtime** (`v2/domain/modules/`, orchestrated by DSH + Domain Host).

**Authored sources vs runtime:** **Character / Template / Scenario (bootstrap) / Opener** JSON authoring rules live in **[AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)**. **This document** describes **turn-time packets** and **retrieval bundles**.

**Implementation status (DSH / Domain Host):** Character turn context is assembled as **`PromptContributionManifest`** contributions in Domain Host **`kernel.prepare_context`** (`v2/domain_api/kernel.py`), including bounded **`recent_scene_transcript`** and **`user_turn_trigger`** projections from durable `rp_history` (perception-filtered). **#38 Character knowledge path:** DSH **`runCharacterKnowledgeCognition`** performs Character knowledge-orientation → Character **`KnowledgeAccessRequest`** → Librarian **`contextual_semantic`** mediation → Host **`map_librarian_bundle_to_contributions`** (`librarian_knowledge` / `librarian_synthesis` lanes). Orientation consumes the same pre-Librarian upstream assembly as final `prepare_context` (`character_upstream_context.py`). Librarian failure omits knowledge lanes visibly; there is **no** silent fallback to legacy `KnowledgeService` projection. Director context (`kernel.prepare_director_context`) adds bounded **`recent_orchestration`**, **`actor_suitability`**, and **`scene_pressures`** digests; authoritative skip-aware **`user_turn_source`**; optional derived **`user_steering_hints`**; plus existing **`scene_setup`**, **`scene_state`**, **`scene_progression`**, **`recent_environment`**, and related authoritative lanes. Director semantic QA (#26) uses **`POST /v1/director/semantic-qa/context/prepare`** with the same scene evidence plus candidate package. DSH **`HgContextBridge`** transports manifests to inference without reinterpreting domain semantics. **`KnowledgeService`** (`knowledge_service.py`) retains authored/scope retrieval helpers and post-commit promotion; it is **not** the live Character manifest knowledge path. Legacy **`prompt_builders.build_character_turn_prompt`** retains formatting reference semantics but is not the live V2 composition path. Continuity commit remains in Domain Host.

**#32 S3a (Storyteller cognition — validated isolated slice):** Host **`storyteller_service.py`** + contracts (`storyteller_contract.py`) implement orientation → `KnowledgeAccessRequest` → validated #34 Librarian read path → informed assessment → **`StorytellerAdvisoryPackage`**. DSH substrate: **`storyteller-cognition-substrate.mjs`**. Host endpoints: **`POST /v1/storyteller/orientation/prepare|finalize`**, **`POST /v1/storyteller/assessment/prepare|finalize`**. Anti-railroading validation is deterministic. **S3a scope:** cognition loop validated in isolation; **live Director/Character consumer wiring** is provided by **S3c (Model A)** below.

**#32 S3b (Storyteller → Packaging mapper):** Host **`storyteller_packaging_mapper.py`** maps validated **`StorytellerAdvisoryPackage`** slices into suggestive **`storyteller_*`** `PromptContribution` lanes via deterministic consumer policies (`storyteller_packaging_policy.py`) and a validity gate (`storyteller_packaging_validity.py`). Packaging does not rerank, reinterpret, or regenerate Storyteller advice. **`PreservationSignal`** is not mapped to consumer lanes.

**#164 post-commit semantic authority (implemented):** producer-neutral post-commit semantic proposal seam (Host **`prepare_librarian_proposal_context`** / **`finalize_librarian_proposals`**, DSH **`runLibrarianProposalGeneration`**). **Storyteller** is the semantic proposer for the routine synchronous path via narrow inference kind **`storyteller_post_commit_issue_pressure`** (0–1 LLM per commit). **Eligibility gate:** when no **ACTIVE/ESCALATING** issues exist, finalize records terminal **`eligibility_skipped`** audit with zero proposals and **no** semantic LLM; eligibility uncertainty **fails open** to assessment. **Routine sync production:** **`issue_tension_pressure` only**. **`consequence_meaning`** and **`information_salience`** are **retired** as post-commit LLM kinds (S2a salience unchanged). **`knowledge_revelation_significance`** capability/validators remain for separately exercised legacy replay (`allow_legacy_kinds`); routine catalog sync omits revelation annotations. Historical **`librarian_proposal_audit_log`** records are preserved. Fail-open inference/validation; blocking persistence failure semantics unchanged.

**#39 live post-commit orchestration (implemented):** after each successful Character commit, DSH **`hg-round-orchestrator`** runs **Narrator** and post-commit semantic lifecycle **concurrently**. A **per-commit join** (`hg/librarian-proposal-join`) completes semantic disposition (including Host **`SessionRepository.persist`**) before the next Director/eligibility cycle. Host uses per-**`hg_scene_id`** session locks; **`librarian_proposal_audit_log`** persists for replay/at-most-once protection. Test-only **`skipLibrarianProposalGeneration`** may suppress the path.

**#34 S4b (`knowledge_revelation_significance` — capability preserved, not routine sync):** augment-before-replace durable mutation on **`PublicEvent.revelation_significance_by_character`**. Not emitted on the #164 routine synchronous path; apply/validation paths remain for governed separate invocation.

**#40 B2 (`issue_tension_pressure` — implemented):** Storyteller-originated post-commit assessment for **active issue pressure** when eligible. Accepted proposals persist derived overlays on **`ContinuityManager.issue_pressure_semantic_overlays`**; **`scene_pressures`** consumers unchanged. Deterministic issue-pressure fallback preserved.

**#32 S3c (Storyteller live round integration — Model A):** DSH **`runStorytellerCognition`** runs once after **`hg/round-started`** and before the first Director attempt; Host **`bind_storyteller_advisory_package`** stores round-local advisory state. While the package remains valid, **`kernel.prepare_director_context`** and **`prepare_context`** inject validated S3b mapper output for Director and scoped Character consumers. Authoritative **`commit_move`** invalidates the package (`authoritative_commit`) **before** Narrator; **`prepare_narrator_context`** therefore receives **no** Storyteller lanes in the normal V2 flow (Narrator renders from committed/authoritative context). The S3b Narrator mapper remains a **validated future socket** for an optional post-commit refresh policy — not live in S3c. Storyteller remains optional — failures skip advisory injection and baseline runtime continues. **Not implemented:** post-commit Storyteller refresh, unbounded refresh loops, actor-selection authority changes.

**#34 S2b (Librarian → Packaging mapper):** Host **`librarian_packaging_mapper.py`** maps validated **`LibrarianKnowledgeBundle`** output into **`librarian_knowledge`** / **`librarian_synthesis`** `PromptContribution` lanes via deterministic consumer policies (`librarian_packaging_policy.py`) and a validity gate (`librarian_packaging_validity.py`). Packaging does not rerank, reinterpret, or regenerate Librarian output. **#38** wires the Character live path: orientation → KAR → Librarian → mapper in **`prepare_context`**. Character packaging rejects **`deterministic_fallback`** mediation. A **`storyteller`** consumer policy exists as a future #32 socket without Packaging injection yet.

**Durable `rp_history` presentation semantics (#12, hardened #24, #29, #81, generalized #90, player decomposition #91, Character derivation #92):** Each `presentation` entry records `presentation_status` (`rendered` | `failed`), `metadata.presentation_source` (`narrator` | `degraded_deterministic_fallback` | `committed_fallback`), optional `metadata.presentation_degraded` (boolean), and provider-neutral `metadata.inference_outcome` (`succeeded` | `empty_output` | `inference_error` | `output_limit`). Successful narrator/opening publication persists `metadata.perceptual_visibility` (`PerceptualVisibilityRecord`, schema v2) with semantic units, recipient scopes, and resolved speech authority for deterministic Character-side assembly via projector `hg.perceptual_visibility.v1`. **Character committed turns (#92):** v2 action beats accept optional `recipients` (`present` default). `validate_move` derives/validates `source_kind: character` PVR before commit; `commit_move_transaction` re-verifies and persists PVR atomically on `committed_turn.metadata` before continuity mutation. Character transcript, observer memory, and semantic-QA context consume projector output only (`hg.perceptual_visibility.v1`). Actor self-memory retains full move summary; observer memory skips empty projection. Pre-#92 Character commits without PVR use safe-partial recovery (`historical_partial` / `historical_missing_character_perceptual_derivation`). **Player user turns (#91, #120):** `POST /v1/sessions/history/user-turn` accepts optional `player_decomposition` from DSH (`runPlayerDecomposition`, initial + one retry). Domain Host validates complete normalized source accounting (`projects` / `non_projects` only), resolves player speech authority from recipient scope, and atomically persists original `content` plus canonical PVR or explicit failure record on `metadata.perceptual_visibility` before Character round processing. Player `internal` means intrinsically nonperceptual information (including but not limited to cognition) and is never Character-projected; concealed physical actions use `observable_event` + restrictive scope. Character `recent_scene_transcript`, `user_turn_trigger`, semantic QA inheritance, and player-interaction memory all consume projector-governed assembly; Director/orchestration retains full unredacted `content`. Current decomposition failure: neutral transcript marker, omitted Character trigger, no player-interaction memory write. Pre-#91 user entries lacking PVR are omitted from Character transcript (`historical_missing_player_decomposition`). Human/UI transcript projection (`project_history_to_transcript`) always shows full stored prose. Character manifest transcript projection (`project_history_to_character_context_chat` → `recent_scene_transcript`) assembles viewer-eligible fragments only through the canonical perceptual projector; audit metadata is attached as `perceptual_visibility_projection` on assembled chat lines (`perceptual_assembled: true`). Invalid Narrator perception with a linked authoritative `structured_move` degrades to structured-recovery units through the same projector; invalid/missing opening perception is excluded. Historical `metadata.narrative_visibility` may be normalized read-only at projection time. Opening entries follow the same perceptual contract after bootstrap segmentation.

**Explicit Skip Turn (#13):** `kind: player_skip` records non-dialogue player advance intent (`POST /api/turns/skip` → `record_player_skip` → `runRound`). Skip does not create user conversational memory or `kind: user` history. `user_turn_trigger` is suppressed when a `player_skip` entry follows the latest substantive user entry; prior user text may remain in `recent_scene_transcript` as historical context only.

For runtime behavior and guardrails, see [docs/architecture.md](./docs/architecture.md) and [MODULE_INDEX.md](./MODULE_INDEX.md).

**#134 model-context manifest policy:** `PromptContribution`, `PromptContributionManifest`, and equivalent bridge-bound `contributions` tuples are **model-facing inference context only**. Membership in a manifest means the content is intentionally model-facing for that inference path. Forensic/audit artifacts (execution evidence, turn metadata, cognition audits, plot cognition forensic handoffs, Librarian audit/disposition structures, etc.) remain in **separate durable channels** unless explicitly distilled into an authorized model-facing contribution. Domain Host **`finalize_prompt_contribution_manifest`** / **`validate_contribution_package`** enforce per-inference **`source_kind` allowlists** (`manifest_projection_policy.py`, keyed by **`inference_kind`**) before manifests are returned. DSH **`HgContextBridge`** validates again and **fail-closed rejects the entire package** (zero partial registration) when any contribution violates the applicable allowlist. For **`PromptContributionManifest`**, **`inference_kind` is required** on the manifest itself — external caller fallback cannot repair a malformed manifest, and manifest/caller kind mismatch rejects. Non-manifest bridge-bound contribution collections may supply an explicit authoritative `inference_kind` at registration time. Python and JavaScript policy maps are kept synchronized by deterministic parity tests. There is no `projection` field, no `evidence_only` PromptContribution, and no Bridge skip/filter mode. `provenance.visibility` does not determine model projection. **#138 extension:** plot-cognition production inference kinds (`plot_cognition_init`, `plot_cognition_update`, `plot_cognition_epistemic_eval`, `character_advisory_generation`, and their `_contract_correction` siblings) are registered in the same policy maps; DSH **`bridgeManifestFromHostPrepare`** (`bridge-manifest.mjs`) preserves authoritative Host manifest metadata when contributions are synthesized or transformed.

---

## DSH round result — `role_inference_summary` (#94)

**Authority:** Ephemeral **round-result projection** returned by `hg-round-orchestrator` (`runRound`). **Not** durable forensic evidence. Full attempt chains, semantic QA passes, rejected candidates, and participation-direct records remain authoritative in `data/execution_evidence/` (see [docs/rp-data-layout.md](./docs/rp-data-layout.md)).

Replaces the former nullable `role_inference_traces` trace-or-null map, which conflated intentional bypass, degraded fallback, and failure-before-inference.

### Scope (most recent role activity)

Each scalar `role_inference_summary.<role>` entry describes the **most recent invocation/activity of that role within the round** — not a whole-round aggregate history. When the same role acts multiple times in one round (for example Director inference on an earlier turn followed by participation-direct on a later turn), the summary reflects **only the latest activity**. Earlier inference for that role remains reconstructable from durable execution evidence and relevant `scene_events` (`hg/director-*`, `hg/participation-decision`, etc.).

The legacy top-level round field `director_inference_session_id` retains the **last Director inference session id observed during the round** when provider inference ran. It is **not** guaranteed to match `role_inference_summary.director.inference_session_id`, which belongs to the most recent Director activity represented by the summary (null when the latest activity was a bypass).

### Per-role entry (`director` | `character` | `narrator`)

| Field | Meaning |
|-------|---------|
| `inference_execution` | Provider inference only: `not_executed` \| `attempted` \| `completed`. `not_executed` = no provider invocation for the summarized activity. `attempted` = invocation occurred but did not produce a normally completed inference result (trace may be null on inference-boundary throws). `completed` = normally completed provider inference result — downstream validation/selection/commit/presentation may still fail. |
| `phase_outcome` | Orchestration resolution only: `not_reached` \| `bypassed` \| `succeeded` \| `degraded` \| `failed`. |
| `inference_trace` | Bounded `extractInferenceTrace` result for the **final inference attempt of the summarized activity**, or `null` when `inference_execution === not_executed` or when no truthful trace object exists for an `attempted` boundary throw. |
| `inference_session_id` | DSH session id for that same final attempt, or `null`. |
| `evidence_id` | Final-attempt durable evidence id when enabled, or `null`. When present, must identify the attempt represented by the summary — never a superseded earlier attempt. |

**Rules**

- Do **not** treat a non-null `inference_trace` as proof of phase success.
- Participation-direct Director (most recent activity): `not_executed` + `bypassed` + null trace/session (#28 durable `role: participation` remains authoritative).
- Narrator terminal fallback: `degraded`; when the final provider invocation completed normally, populate last-attempt trace/session/evidence; when the final invocation threw before trace assembly, use `attempted` with null trace/session and final-attempt `evidence_id` when durable evidence exists; when failure occurred before any provider invocation, `not_executed` with null trace.
- Never carry a prior attempt's trace/session/evidence forward when the summary describes a later final attempt.
- Roles whose phase never ran in the round: `not_reached`.

---

## Knowledge mediation architecture (#33 — target vs current)

Parent program **#33** closed with accepted child architecture on **#31** Retrieval, **#34** Librarian, and **#32** Storyteller. **#31**, **#34**, and **#32** core seams are implemented and validated in production runtime. **#38** retired the legacy Character **`KnowledgeService.project_context`** manifest lane; Character knowledge is Librarian-mediated under per-character epistemic boundaries.

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
- **`LibrarianSemanticProposal`** — post-commit grounded proposal batch (**S4a validated**; **S4b `knowledge_revelation_significance` implemented**): `proposal_id`, `proposal_kind`, non-empty `evidence_anchors`, `derivation_summary`, `confidence`, typed `proposed_payload`, Librarian provenance, `commit_binding` (`domain_commit_id`, post_commit). Continuity validation accepts/rejects; **only `knowledge_revelation_significance` may apply bounded durable per-character annotations** on grounded **`PublicEvent`** records (`revelation_significance_by_character`). Other kinds remain audit-only. Heuristic migration for additional classes deferred to later S4b/S5 cycles.
- **`StorytellerAdvisoryPackage`** — round-scoped advisory narrative assessment (**S3a validated**); **S3b Packaging mapper validated**; **S3c live integration (Model A):** Director + Character while valid; commit invalidates before Narrator.

### Current implementation seam

**RetrievedContextBundle** (below) remains the **live Character retrieval-to-packaging path**. **Librarian S2b** adds the mapper seam but does **not** replace Character retrieval/memory lanes or wire into `kernel.prepare_context` yet. **Librarian S4a/S4b:** post-commit **`LibrarianSemanticProposal`** prepare/finalize + Continuity accept/reject; **S4b `knowledge_revelation_significance`** applies bounded per-knower **`revelation_significance_by_character`** annotations (global **`PublicEvent.significance`** unchanged). Other proposal kinds remain audit-only. **Storyteller S3a/S3b/S3c (Model A):** round-start package maps to suggestive `storyteller_*` lanes for **Director and scoped Character** while valid; authoritative commit invalidates the package before Narrator, so Narrator normally receives no Storyteller advisory. Optional future post-commit refresh could activate the validated S3b Narrator mapper. Storyteller does not affect actor selection or Continuity truth.

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

- **Authored knowledge** — Compiled from setup snapshot via `authored_knowledge.compile_authored_records_from_snapshot`; accessed through **#31 Retrieval** (`retrieval_service.py`, `retrieval_selection.py`) for tests, scope promotion, and Librarian candidate pools—not via legacy Character manifest projection.
- **Story knowledge (#50)** — See [docs/story-knowledge.md](./docs/story-knowledge.md). Projected from committed `PublicEvent` into `data/sessions/_story_knowledge/{memory_scope_id}/`; retrieved via `story_occurrence` / `story_derived`; live `known_by` at query; `mediation_outcome` distinguishes failure modes from `no_match`. Forensic record: `governance/records/issue-50-story-knowledge-forensic-record.md`.
- **`PublicEvent.occurrence_evidence` (#51)** — Optional bounded companion on promoted occurrences: `contributions[]`, `triggering_user`, `structured_fact_refs[]`, `scoped_evidence[]`. Classification metadata (`state_changes`, `significance`) remains distinct from semantic evidence. `turn_metadata_by_index.summary_selection_source` records summary-selection provenance. #50 occurrence JSONL may include `evidence_projection` listing globally projected components. Continuity remains authoritative state writer; PublicEvent does not duplicate registries.
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

**Host assembly:** `semantic_qa_context.py` provides role-neutral manifest assembly helpers. Director semantic QA prepare is implemented at **`POST /v1/director/semantic-qa/context/prepare`** (#26). Narrator semantic QA prepare is implemented at **`POST /v1/narrator/semantic-qa/context/prepare`** (#27): bounded authority references from the same legitimate Narrator source surface (committed move slices, authoritative scene lanes, derived director decision, public events, **environmental baseline**) plus candidate presentation package.

**#49 Narrator environmental response (implemented):** Pre-render cognition at **`POST /v1/narrator/environment/cognition/prepare`** + **`finalize`**; manifest lanes **`narrator_environment_baseline`**, **`triggering_user_context`**, **`narrator_environment_cognition`**. `EnvironmentalCurrentView` = authored baseline + story-derived B2 with supersession. B2 → `submit_derived_record` (`environmental_descriptor`); B1 presentation-only; C requires separate establishment. DSH: `narrator-environment-cognition-substrate.mjs` before `prepareNarratorContext`. **#151:** Domain classifies `cognition_status` / nullable `baseline_sufficient` / `status_reason`; DSH passes raw inference facts only (no sufficiency synthesis on failure).

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
