# Architecture guidance

Shared guardrails for Holy Grail RP. Product orientation: [governance/sources/architecture-overview.md](../governance/sources/architecture-overview.md). File routing: [MODULE_INDEX.md](../MODULE_INDEX.md).

**Authored JSON boundaries:** [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md).

**Scenario validation:** [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md) (canonical; do not duplicate here).

**Issue workflow:** [governance/sources/issue-tracking-workflow.md](../governance/sources/issue-tracking-workflow.md).

---

## Repository stance

- Preserve module boundaries unless the task requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless callers are explicitly in scope.

---

## Runtime stack

```text
Presentation (v2/ui/streamlit_app.py)
        ↓ HTTP
Node application / DSH runtime (v2/rp_runtime/)
        ↓ HTTP (domain-api-client)
Domain Host (v2/domain_api/)
        ↓
domain library (v2/domain/modules/)
        ↓
data/  (HG_DATA_DIR)
```

**Domain truth** lives in continuity and Host repositories. **Speaker selection** is Host participation policy plus DSH Director phase. **Inference** runs through DSH. **Context construction** is Domain Host **`PromptContributionManifest`** projection. Character paths use `kernel.prepare_context` with `character_context_projector.py` identity/scene/Director-advisory lanes plus perception-filtered **`recent_scene_transcript`** and **`user_turn_trigger`** from `rp_history`. DSH passes the accepted Director decision into Character context preparation as advisory `director_context` only. Director paths use `kernel.prepare_director_context` with bounded **`recent_orchestration`**, **`actor_suitability`**, and **`scene_pressures`** digests; authoritative skip-aware **`user_turn_source`**; optional derived **`user_steering_hints`**; plus existing **`scene_setup`**, **`scene_state`**, **`scene_progression`**, **`recent_environment`**, and related authoritative lanes. After deterministic Director acceptance, bounded semantic QA (#26) reviews decision defensibility via the same scene evidence plus the candidate package; the evaluator is subordinate QA and does not bind `next_actor` or emit authoritative replacement Director JSON. **Participation-direct** selections bypass Director inference and Director semantic QA. Narrator additionally receives bounded **`scene_setup`**, live **`scene_state`**, and authoritative **`scene_progression`**. `recent_delta` is internal continuity state and is not a progression prompt lane. `HgContextBridge` only transports manifests. Domain `prompt_builders.py` retains legacy formatting helpers but is not the live V2 composition path. Packaging does not replace continuity authority. Node calls the Domain Host; Python does not call DSH.

---

## Knowledge mediation and narrative intelligence (#33)

Parent program **#33** is closed; accepted architecture is authoritative on child Issues **#31**, **#34**, and **#32**. Child programs **#31**, **#32**, and **#34** are **closed** with governed validation of their in-scope slices (Retrieval S0+S1, Librarian S2/S4, Storyteller S3 Model A); remaining program items (for example S5 Continuity heuristic migrations, deferred Character direct Librarian wiring, post-commit Storyteller refresh) are explicitly deferred per those Issue records—not open implementation gates.

### Responsibility boundaries (accepted target)

- **Retrieval (#31)** — hard access/disclosure constraints, candidate generation, provenance-bearing records, backend abstraction, bounded recall. Does **not** own final semantic relevance. Live authoritative Continuity state is **not** ordinary retrieved lore. **#50 story knowledge:** see [story-knowledge.md](./story-knowledge.md) — occurrence-first JSONL corpus, evidence-budget selection, TF-IDF index, Librarian `mediation_outcome`.
- **Librarian (#34)** — `KnowledgeAccessRequest` in; provenance-aware `LibrarianKnowledgeBundle` out (S2a); deterministic Packaging mapper (S2b); post-commit grounded **`LibrarianSemanticProposal`** batches (S4a) via Host prepare/finalize + DSH inference → Continuity accept/reject boundary; **S4b `knowledge_revelation_significance`** may apply bounded **`PublicEvent.revelation_significance_by_character`** entries (augment-before-replace; **`known_by` unchanged**); **#40 B2 `issue_tension_pressure`** may apply bounded per-issue semantic overlays joined into **`scene_pressures`** (overlay store separate from **`IssueState`**; deterministic pressure fallback preserved). **Librarian may interpret committed truth; it may not manufacture truth.** Continuity remains exclusive transactional writer.
- **Storyteller (#32)** — bounded advisory narrative cognition: orientation → Librarian bundle → informed assessment → `StorytellerAdvisoryPackage` → deterministic Packaging mapper → suggestive `storyteller_*` lanes while the round-local package remains valid. **S3a/S3b/S3c implemented (Model A):** cognition loop, S3b mapper (Director/Character live; Narrator policy is a validated future socket), round-orchestrator pre-Director hook, round-local bind, Director/Character injection, commit invalidation before Narrator. Does **not** control plot outcomes, `next_actor`, Character intent, Narrator events, retrieval, information mediation, or persistence. `PreservationSignal` is an attention hint only and is not mapped to consumer lanes. Invalidated packages are **not** injected into subsequent `prepare_*` calls.
- **Packaging** — deterministic consumer-specific assembly; does not perform semantic relevance ranking or narrative interpretation.

### Current runtime (implemented today)

Character knowledge (#38): DSH **`runCharacterKnowledgeCognition`** → orientation → Character KAR → Librarian **`contextual_semantic`** → **`librarian_*`** manifest lanes via **`map_librarian_bundle_to_contributions`**. Character orientation sees full pre-Librarian upstream context; epistemic boundaries (`bound_character_id`, `known_by` hard access, viewer/subject binding) prevent hidden-knowledge leakage; **`deterministic_fallback`** is packaging-ineligible for Character. Director receives authoritative continuity projections/digests plus Storyteller advisory while the round-local package is valid. Character receives bounded Storyteller advisory (scoped) plus identity/scene/relationship lanes while valid. Authoritative Character commit invalidates the Storyteller package; Narrator then renders from committed move and authoritative scene context **without** Storyteller lanes in the normal flow. Librarian bundles also reach live rounds through the Storyteller cognition path (#32 S3c).

**Live post-commit S4 (#39, authority contract #100):** on every successful Character commit, DSH runs Narrator presentation and Librarian **`runLibrarianProposalGeneration`** in parallel from the same commit, then **joins** the Librarian branch (finalize + persist + terminal audit) before the next **`getEligibleActors`** / Director cycle—including multi-commit rounds (per-commit join, not round-end only). Host finalize paths persist session state and **`librarian_proposal_audit_log`** under per-session locks; this is a **second persistence seam** after normal `commit_move`, not a second unrestricted turn-commit authority.

**S4 durable mutation allowlist** (normative detail: [architecture-overview.md](../governance/sources/architecture-overview.md) → Continuity mutation authority seams; machine-readable: `S4_DURABLE_MUTATION_SURFACES_BY_KIND`, `S4_DURABLE_MUTATION_SURFACES`, and `S4B_MUTATING_PROPOSAL_KINDS` in `v2/domain_api/librarian_proposal_contract.py`):

| Surface | Proposal kind |
|---------|---------------|
| `PublicEvent.revelation_significance_by_character` | `knowledge_revelation_significance` |
| `ContinuityManager.issue_pressure_semantic_overlays` | `issue_tension_pressure` |

For `issue_tension_pressure`, `issue_ref` accepts the bare authoritative `issue_id` or the catalog stable reference `issue:{issue_id}` (same typed stable-reference pattern as `event_ref` / `event:{event_id}` for `knowledge_revelation_significance`).

S4 **must not** modify `turn_counter`, authoritative `IssueState`, or `known_by`. `consequence_meaning` and `information_salience` remain accepted audit-only kinds without durable Continuity mutation. At-most-once: terminal audit per `domain_commit_id` via `find_terminal_audit_for_commit`. See [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md).

**Future option (not implemented):** bounded post-commit Storyteller refresh (`material_commit_refresh`) could later activate the validated S3b Narrator mapper; not required for #32 completion.

### Implementation sequencing (recorded on #33)

S0 shared contracts → S1 #31 Retrieval façade → S2a #34 Librarian read → S2b Packaging bundle mapper → S3 #32 Storyteller advisory → **S4a #34 write/proposal seam (validated)** → **S4b `knowledge_revelation_significance` (implemented; single class)** → S5 Continuity heuristic migrations (per class). S3 does not require S4.

---

## Behavioral validation layer

Scenario validation is a **core architectural layer**: fixed JSON scenarios, domain manifest tests, integration tests, optional audit JSON, and offline investigation tools.

Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Domain architecture rules

Holy Grail RP uses Director + character agents + Narrator + continuity manager.

### Scene-start spine

Fresh scenes use one canonical continuity init/apply ordering (`continuity_setup_seam_v77`, Host `session_setup.py`). Application UI and test/runtime inputs are **separate surfaces** into that spine—not divergent template-application models.

**Opener selection (UI):** template-owned Opener JSON or custom text; multiple template openers require an explicit pick before scene start. The UI posts that choice through the Node application API. Test and DSH paths carry opener choice on Host session-create payloads. DSH `opening-phase.mjs` runs opening inference when the setup requests generated opening text.

**Persistent premise vs opener:** at scene start, template `premise` is written to continuity as `scene_state.scene_premise` and projected authoritatively through the shared `scene_setup` lane (including Character `scene_context`). The selected opener (or minimal/custom/generated opening text) is stored separately as `opening_description` and reaches ongoing Character cognition through `rp_history` / `recent_scene_transcript` — it must not substitute for the persistent scenario premise in `scene_setup`.

**Role-private scenario knowledge:** optional template `role_private_knowledge` is authored on the scenario/template object, keyed by role name. At bootstrap, assigned Characters receive their role's text through the existing `character_private_secrets` → `character_private` pipeline (character-only; not Librarian retrieval).

### Core responsibilities

- Character agents produce self-only structured moves.
- Optional move fields are **not** the authority boundary for issues, tension, or consequences.
- Director selects who acts next.
- Narrator renders prose after commit via deterministic acceptance: normalized `complete` completion, non-empty output, and Host F1/F2 speech fidelity (`narrator_presentation_validation.py`). After F1/F2 acceptance, bounded semantic fidelity QA (#27) reviews presentation against the same legitimate committed source surface via Narrator-local authority references; the evaluator is subordinate QA and does not emit replacement authoritative prose. Single two-generation Narrator budget (`MAX_NARRATOR_ATTEMPTS = 2`); soft exhaustion accepts with residual concerns; hard exhaustion or evaluator infrastructure failure uses deterministic degraded presentation from the committed `structured_move` when available (#29), otherwise committed-turn summary fallback (#24). Per-role reasoning profiles and **reference token ceilings** (director/character/opening 4096, narrator 8192, semantic evaluator 2048; tunable via `application-settings.mjs`) remain documented for analysis; **Holy-Grail application `maxTokens` enforcement is globally disabled during the present development period** (#152). **Plot Cognition update** and **Librarian post-commit proposal** retain reference **8192** headroom labels via `PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS` (#111). **Template opening segmentation** (`opening_segmentation`) uses operation-specific reasoning override with thinking disabled (#110). Streamlit no longer exposes a global reasoning selector. Provider `reasoningEffort: off` maps to `thinking: disabled` at the adapter boundary. `HG_INFERENCE_CALIBRATION=1` retains calibration labeling but does not reintroduce HG token ceilings while global quota disable is active.
- Continuity manager updates durable scene and issue state.
- Validation and enforcement remain separate from prompt styling.
- **`perception_audibility.py`** gates who may see dialogue and narrator render for others' beats.
- **Perceptual visibility (#81, generalized #90, player decomposition #91, Character derivation #92, player triage #121, viewer entitlement #155):** Human/UI transcript and Character `recent_scene_transcript` are distinct projections of the same `rp_history`. Narrator/opening prose is persisted in full for humans; new writes persist `metadata.perceptual_visibility` as a canonical **`PerceptualVisibilityRecord`** (schema v2) with semantic units (`observable_scene`, `observable_event`, `speech`, `internal`, `presentation_only`, plus synthesis-only `uniform_projection` on checker-routed player turns) and recipient scopes. Source-specific validation/normalization (Narrator presentation profile, opening profile, **player submit profile**, **character move profile**) resolves speech **`authority`** from authoritative structured-move beats or validated player recipient scope before projection; the common projector does not inspect `beat_index` or caller-supplied `structured_move`. **One deterministic projector** (`hg.perceptual_visibility.v1`, version 2 for #155) assembles viewer-eligible fragments; recipient scope and resolved speech authority may narrow visibility but never broaden it. **Recipient scope (Gate 1)** and **viewer perceptual entitlement (Gate 2)** are separate: `present_characters` is participation/recipient state, not visual co-presence; `offstage_characters` is not barrier geometry. Player posts may be **partially projected by unit** using optional `perception_channel` (`visual` | `auditory` | `non_perceptual`). When optional authoritative `perceptual_scene_context` is present on `scene_state`, closed opaque portals block visual units but may permit auditory units across an **ordinary** barrier; soundproof barriers block auditory units; missing spatial facts fail closed as `unknown` (withhold current perception, preserve source truth) and do **not** assume an ordinary door. **Absent `perceptual_scene_context` does not disable Gate 2:** non-spatial recipient contracts (`private`/`role_private`) and explicit unit kind/channel authority may still establish entitlement; spatially ambiguous current-perception units without sufficient facts fail closed as `unknown` rather than restoring legacy present-scope omniscience. Optional context means optional structured spatial evidence, not optional enforcement. Scene templates may seed threshold geometry (e.g. `ayame_household_entry_evaluation`) without a global migration mandate. `uniform_projection` is a construction optimization only — it does not bypass entitlement; mixed-modality uniform bundles require semantic PVR decomposition (no punctuation splitting on the authoritative path). `observable_event`/`observable_scene` default to `visual` channel by kind; `speech` defaults to `auditory`; uncertain text inference fails closed. All Character-facing Player lanes (`recent_scene_transcript`, `user_turn_trigger`, memory writes, semantic-evaluation context) derive from the same viewer-specific entitled source set via `assemble_viewer_player_perception` / `viewer_player_perception.py`; zero entitled units omit the Player-derived trigger without synthetic filler. No LLM perceptual rewrite and no fabricated sensory substitutes. Character-facing Narrator/opening/player/**committed Character** perception uses only this projector — no presentation-path `format_observable_v2` fallback and **no** `player_text_for_character_viewer` whole-blob heuristic. **Character commits (#92):** v2 action beats accept optional `recipients` (`present` default); Domain Host derives `source_kind: character` PVR before the first durable commit mutation, persists it atomically on `committed_turn.metadata`, and routes transcript, observer memory, and semantic-QA context through the common projector. Actor self-memory retains full authorized move summary; observer memory uses projector output only (skip when empty). Pre-#92 Character commits without PVR use safe-partial recovery (`validation_status: historical_partial`, `failure_class: historical_missing_character_perceptual_derivation`): speech from `audibility`/`audience`; historical action beats actor-only via conservative private scope. **Player turns (#91):** DSH performs bounded semantic decomposition once at submit (initial + one retry); Domain Host validates complete NFC/CRLF-normalized source accounting and persists original `content` plus canonical PVR or explicit failure state atomically before Character round processing. Director/orchestration retains full unredacted player source (#23). Current decomposition failure uses neutral transcript marker `[Player turn — perceptual detail unavailable to this character]`, omits Character trigger, and skips player-interaction memory. Pre-#91 user entries lacking PVR are omitted from Character transcript (`historical_missing_player_decomposition`) — not retroactively decomposed. Invalid Narrator records with authoritative structured-move information degrade to a canonical structured-recovery record and pass through the **same** projector (`invalid_fallback_structured`); invalid opening perception without structured authority is excluded/audited. Historical `metadata.narrative_visibility` is supported only via a read-only normalizer at the projection boundary (not a second projector). Projection audit metadata (`perceptual_visibility_projection`) records projector identity/version, validation/degraded classification, inclusion/exclusion reasons, authority narrowing, historical-normalization provenance, and (#155) per-unit entitlement decisions.

### Protected intent

- Do not move long-horizon continuity into prompts or unbounded transcripts.
- Do not treat Director prompt edits as the default runtime fix.
- Keep the Domain Host as the composition boundary; keep the UI a presentation client.
- **Progression advisory** is advisory only — it must not write continuity truth or mutate `CharacterState`.
- **Scene Grounding** is read-only prompt projection from continuity — not a second authority ([PRD](../Holy%20Grail%20PRD.md) §5.8, [scene-grounding-layer.md](./scene-grounding-layer.md)).

---

## Change strategy

1. Identify the real layer involved.
2. Inspect downstream consumers.
3. Prefer the smallest fix that preserves the design.
4. Update shared docs when contracts change.

### Forensic auditability (architecture completion)

Meaningful semantic decisions, inference paths, information-flow seams, and authoritative mutation paths should include forensic evidence and an investigation path in their **normal acceptance contract**. **Auditability is normally part of architecture completion, not a later optional enhancement.**

Normative standard: [forensic-auditability-standard.md](./forensic-auditability-standard.md). Retained-artifact contracts: [rp-data-layout.md](./rp-data-layout.md). Investigator procedure: [audit-workflows.md](./audit-workflows.md).

**Perceptual visibility projection audit (#90, #155):** Character-facing Narrator/opening assembly records `perceptual_visibility_projection` on chat history lines with `perceptual_assembled: true`. Fields include `projector_id`, `projector_version`, `viewer_character`, `source_kind`, `source_entry_id`, `validation_status`, `validation_profile`, `degraded_path`, `historical_normalization`, `legacy_metadata_key`, `included_unit_ids`, `excluded_unit_ids`, `exclusion_reasons`, `authority_narrowed_unit_ids`, optional `unit_entitlement_decisions` (per-unit channel, recipient/perceptual decision, basis, reason code, projected/withheld), and record identifiers when available. Degraded classifications distinguish `valid`, `invalid_fallback_structured`, `invalid_excluded`, and historical normalization. Perceptual visibility determines Character-facing projection only; it does not create Continuity truth, mutate `known_by`, mutate `character_private`, or replace Director canonical history.

---

## RP audit diagnosis order

When debugging scene quality or continuity:

1. continuity and state representation
2. perception / audibility (knowledge leaks, whispers, per-character prompt mismatch)
3. scene grounding (settled facts present, stale, or missing)
4. issue lifecycle and orchestration state
5. summary retrieval and compression
6. validation and enforcement boundaries
7. memory layer read path (`memory_layer/retrieval.py`)
8. Director logic (Host prepare/validate + DSH director phase)
9. Narrator rendering polish (DSH narrator phase)

Full workflow: [audit-workflows.md](./audit-workflows.md).

---

## Validation modules

Runtime validation is split under `v2/domain/modules/`:

- `response_validation.py` — facade
- `response_validation_parsing.py` — JSON / move parsing
- `response_validation_content.py` — **production runtime** (`validate_bot_response_for_runtime`: objective R02a placeholders + R03 move-shape/registry); **offline scenario** (`validate_bot_response_for_scenario` for investigation recall)
- `response_validation_presence.py` — `must_remain` helpers (`get_must_remain_characters`)
- `response_validation_selection.py` — eligibility helpers (non-authoritative vs Host/DSH Director selection)

Host `validate_move` calls `validate_bot_response_for_runtime` only. Deterministic textual/semantic quality heuristics (R02b, R11–R15) are **not** objective hard gates in Domain validation.

**Bounded Character semantic evaluation (#19):** DSH Character orchestration runs `generate → objective validate → bounded semantic evaluate → commit`. Semantic judgment lives in DSH (`character-semantic-evaluation.mjs`), not `kernel.validate_move`. The Host exposes read-only evaluation context via `prepare_semantic_evaluation_context` and delivers orchestration-only correction via `semantic_correction` manifest contributions on `prepare_context`. The evaluator does not mutate continuity, write RP, or enter canonical history. Hard findings require a valid authority reference from the evaluation context; soft findings allow one challenge then residual recording. Maximum three generated Character candidates per turn (`min(configured limit, 3)`). Full forensic chains are preserved in execution evidence (#15).

**Forensic execution evidence (#28):** Director/Narrator semantic QA patches use canonical **`decision.semantic_qa`** (including **`policy_action`**) on candidate attempts; participation-direct writes **`role: participation`** non-inference records; Director attempts carry bounded **`decision.director.eligibility`**. Derived navigation indexes (`qa_pass_chains`, `participation_by_round`) support investigation tooling — see [docs/rp-data-layout.md](./rp-data-layout.md) and [docs/audit-workflows.md](./audit-workflows.md). Post-#28 forensic completeness applies to sessions produced after #28 lands. **Forward standard** for new seams and decisions: [forensic-auditability-standard.md](./forensic-auditability-standard.md). **Ephemeral round summary (#94):** `runRound` returns **`role_inference_summary`** (per-role inference execution vs phase outcome); durable execution evidence remains authoritative for full chains — see [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md).

**Inference-health monitoring (#114):** Cross-runtime LLM attempts retain a compositional observational **`inference_health`** block on execution-evidence attempts (configured ceiling/`max_tokens`, usage, utilization when a ceiling exists, finish class, hard-exhaustion / provider-failure flags, objective structural validity when already known from existing contracts, and a separate **recovery** dimension). Utilization uses generation tokens constrained by the output ceiling (`outputTokens` + `reasoningTokens`), not prompt/input. Successful corrections are structurally evaluated on their own result; primary failure remains on the primary evidence and recovery lineage. Level-2 aggregates live under rebuildable **`index.inference_health`**. This is **not** Continuity state, not a parallel logger, and not live UI interruption. Near-ceiling **threshold/alert semantics are deliberately deferred**; utilization is raw evidence only. Historical attempts lacking ceiling/lineage report honest incompleteness (`not_observable`), never fabricated health. Operator discovery: `python tools/investigation/list_execution_evidence.py <hg_session_id> --inference-health`.

Validators **reject or annotate**; they do not replace Director selection or continuity commits.

**Director fallback:** on JSON parse failure, Host/DSH decision handling may record `"source": "fallback"`. Turn-selection preemption validation is skipped for fallback decisions; memory writes for committed turns are not.

**Director auxiliary contract (#23):** Host validation normalizes `tension_shift` to `escalate` / `soften` / `steady`. Unsupported values are neutralized to `steady`. `environment_event` remains a proposal until Host exact-deduplicates it against bounded continuity-owned environment evidence (Unicode NFKC, whitespace normalization, casefold) and continuity commits the normalized decision. Auxiliary normalization does not retry an otherwise-valid actor selection.

---

## Memory layer

**Policy owner** for episodic writes and prompt read/format. `CharacterState` holds storage plus identity/relationship prompt text.

- **Writes:** commit-time only, perception-filtered observers (`memory_layer/facade`, `writes`, `storage`).
- **Reads:** `memory_layer/retrieval.py` builds episodic sections for `state_context`.

### Prompt context contract

- Character/Director/Narrator **interpretation** is composed in Domain Host role modules (`director_context.py`, `character_context.py`, `narrator_context.py`, `opening_context.py`, `narrator_environment_context.py`) with shared primitives in `context_substrate.py` and Storyteller consumer packaging in `storyteller_round_packaging.py`. `DomainKernel.prepare_*` resolves session/fixture/round anchors and delegates assembly; cognition composition (`cognition_composition.py`) remains separate for application-lifetime service graphs (#53 C1 / #54 C2).
- **Character live manifest** (`kernel.prepare_context`): `character_identity` and `character_expression` project authoritative `CharacterState` portrayal fields (description, personality, goals, voice, reaction, speech fingerprint); `character_relationships` bounds relationship threads to the present cast; `scene_context` merges setup, progression, and role map; `scene_pressures` surfaces bounded active issues; `director_context` carries advisory Director handoff (`reason`, `environment_event`, `tension_shift` only — suggestive, not orchestration). Existing lanes remain: continuity canon/grounding/constraints, perception-filtered transcript/trigger, knowledge, memory, round committed moves, and `inference_instruction`. `hidden_agenda` is not projected. Identity duplicate canon anchors (`character_state.*` profile sources) are filtered from `continuity_canon` on the Character path.
- **Director manifest** (`kernel.prepare_director_context`): orchestration digests plus authoritative scene setup/state/progression; does not receive Character-private lanes.
- **Narrator manifest** (`kernel.prepare_narrator_context`): committed-move rendering surface plus bounded scene setup/state/progression, **`narrator_environment_baseline`** (`EnvironmentalCurrentView` — authored + story-derived B2, deterministic, zero LLM), **`triggering_user_context`** (#51 occurrence evidence), **`environmental_response_obligation`** (resolved perceptual obligations from cognition — #89). Full **`NarratorEnvironmentCognitionAudit`** is retained in `turn_metadata_by_index[].narrator_environment_audit` and execution evidence; it is **not** serialized into the presentation manifest (#131). Pre-render: DSH **`runNarratorEnvironmentCognition`** → Domain classification of raw inference (`cognition_status`, nullable `baseline_sufficient`, `status_reason` — #151) → structured N1/N2 when determined → targeted Librarian (`consumer_role=narrator`) only when determined insufficient → post-mediation **response-sufficiency** evaluation → category **A** composition from **`match`** when sufficient → minimum-necessary **B2** when insufficient (Host-gated, **`match` does not block**) → **`environmental_response_obligations`** → render. Indeterminate cognition emits `sufficiency_undetermined` (no fabricated needs, no B2, no Librarian); hard pipeline failure emits `cognition_unavailable`. DSH must not synthesize affirmative sufficiency on inference/parse failure. Obligation text appears only in the dedicated **`environmental_response_obligation`** lane, not embedded in **`inference_instruction`** (#131). B1 ephemeral texture is not persisted. Does not receive Director scratch or Character-private lanes. Manifest assembly lives in `narrator_context.py`; Narrator `inference_instruction` text formatting lives in `narrator_render_instruction.py` (visibility output schema from `narrative_visibility_prompt.py`).
- `prompt_builders` holds legacy/reference Director and Character prompt text formatters; it does not own live Narrator manifest assembly or render-instruction formatting.
- **Player decomposition (#91, #109, #120, #124, #125) and visibility triage (#121):** On player submit, DSH `runPlayerVisibilityTriagePhase` runs first (reasoning off; positive-safety JSON `uniform_projection_safe`). **Affirmative** `uniform_projection_safe: true` routes to deterministic `uniform_projection` synthesis (`scope: present`, synthesis-only kind, complete source accounting, `semantic_decomposition: not_performed`). Any checker uncertainty, failure, or negative result routes to full semantic PVR via `runPlayerDecompositionPhase`. **#125 entitlement context:** full semantic PVR receives bounded authoritative **`PlayerPvrEntitlementContextV1`** assembled Host-side in `prepare_player_decomposition_context` (`player_pvr_entitlement_context.py`): `session_cast` from session cast; `present_characters`, `offstage_characters`, and `role_assignments` from Continuity `scene_state` only — authoritative empties preserved, no cast/presence synthesis, no location/geometry/knowledge/grounding/history. The manifest contribution (`source_kind: player_pvr_entitlement_context`, `authority_class: authoritative`) is persisted through the existing execution-evidence / request-contributions path for forensic reconstruction. Semantic instructions explicitly bound recipient interpretation: presence constrains scope semantics but does not manufacture named private entitlement; named private/directed recipients require player-source support. V1 deliberately excludes `location_label`, presence annotations/constraints, grounding, transcript, knowledge, advisory, and spatial simulation. **#125 / G-125-01 `role_private` projection:** semantic PVR may classify `role_private` and preserve `recipients.roles`; deterministic viewer projection resolves role recipients through commit-time **`metadata.entitlement_authority_snapshot`** (`schema_version: 1`, `role_assignments`, `session_cast`) captured at `kernel.record_user_turn` — not current Continuity state. Role identifiers match exactly after strip against template-canonical assignment values. Multiple holders of the same role are all entitled; unknown roles fail closed; `role_private` does not filter through `present_characters`. Legacy pre-#125 player entries without the snapshot are not supported by the current runtime contract. **#124 semantic/mechanical split:** the semantic LLM emits only a minimal `semantic_decomposition` (`kind`, `recipients`, verbatim `text` excerpts). DSH performs transport JSON parse only; the Domain Host `POST /v1/sessions/player-decomposition/normalize` endpoint owns global deterministic source matching, source-derived canonical ordering, mechanical envelope construction, and existing `validate_player_perceptual_decomposition` — Node must not perform span/accounting normalization. **#124 deterministic work budget (G-124-03 / G-124-03b):** normalization charges a unified `deterministic_work_budget` (currently 350,000 units, `NORMALIZER_VERSION` 5) covering occurrence scanning, substantive-mask construction (source + span precompute), DFS visits, candidate probes, and overlap comparisons; exhaustion yields `normalization_search_budget_exceeded` (retry-eligible on attempt 0) with audit fields `work_consumed`, `work_overlap_checks`, `work_exhaustion_stage`, and breakdown counters — distinct from semantic invalidity. Both paths validate through `player_perceptual_service.py` at `record_user_turn` and converge on projector `hg.perceptual_visibility.v1`. The checker is routing-only — its `reason` is audit evidence, not semantic truth. Uniform synthesis requires DSH-issued checker `inference_id` provenance (`player-visibility-triage-*`); like all player decomposition envelopes, production authority rests on the DSH→Host submit boundary, not direct API forgery resistance. Full semantic PVR must not emit `uniform_projection` (prompt exclusion + validator rejection). **Player `internal` (#120):** intrinsically nonperceptual player information (cognition, private state, nonperceptual explanatory narration, and other non-observable narrative context) — never `public` scope; hard-excluded from Character projection. Concealed physical actions remain `observable_event` + restrictive scope. **`uniform_projection` (#121):** representation/derivation kind meaning whole-source uniform projection without semantic decomposition — not a speech/event/scene classification. **Checker validation asymmetry (#121):** A **false-simple** is when the checker returns `uniform_projection_safe: true` for a turn that actually requires semantic PVR — safety-critical because it can over-disclose to Characters; the mandatory regression/adversarial corpus therefore requires **zero false-simple** results (a corpus acceptance criterion, not a claim of mathematically zero real-world error). A **false-complex** is when a genuinely uniform-safe turn is routed to full PVR — cost/latency only, not the same disclosure risk. Report false-simple and false-complex **separately**; do not collapse them into a generic accuracy score.
- DSH `HgContextBridge` registers the Host manifest on an ephemeral inference agent. It does not reinterpret authority classes and **fail-closed rejects** any contribution package that violates the per-inference **`source_kind` allowlist** (`manifest_projection_policy.py` / `manifest-projection-policy.mjs`): invalid packages register **zero** contributions. **Prompt contributions are model-facing inference context only**; forensic/audit artifacts remain in durable evidence channels unless explicitly distilled into an authorized model-facing contribution (#134).

---

## Continuity authority and evidence lanes

**`SceneState`** and **`process_turn`** define committed truth. Distinguish **intent**, **interpretation**, **commit**, and **observation**. Narrator prose and classifier signals do not override `SceneState`.

**Bounded commit transaction (#55 C3-F):** `DomainKernel.commit_move` is a stable façade that resolves session/round anchors and delegates to `commit_move_transaction.execute_commit_move`. The transaction module owns dedup guards, commit-path input normalization, rollback snapshots, transactionally coupled state ordering (character memory, round bookkeeping, `domain_commit_id`, committed-turn `rp_history`, dedup record), and post-durable derived effects. **`ContinuityManager.process_turn`** remains the sole continuity legality and mutation authority — the transaction orchestrates it; it does not replace it. **`SessionRepository.persist`** is the sole durability gate per commit: committed-turn `rp_history` and the dedup record are coupled before that single persist (H1); Storyteller round-local advisory invalidation occurs only after successful persistence (S2); `KnowledgeService.promote_after_commit` runs post-durable as best-effort warn-only promotion (K2). If persistence fails, every in-process field that would imply success is rolled back to its pre-attempt state; Storyteller advisory remains unchanged.

**Promoted `PublicEvent` (#51):** A durable committed-occurrence/evidence boundary — not merely a prose summary, not a duplicate Continuity store, not an execution log. Classification metadata (`state_changes`, consequence tags) describes **what kind** of occurrence occurred; bounded semantic evidence (`summary`, optional `occurrence_evidence`) preserves **what actually happened** when epistemically permitted. One occurrence may retain multiple authoritative producer contributions (Character + Director environment) without expanding producer truth authority. `triggering_user` provides bounded causal provenance to a user history entry. `known_by` remains the live retrieval gate; scoped/private evidence is not globally embedded. Audit observability: `turn_metadata_by_index.summary_selection_source` and story JSONL `evidence_projection` — see [story-knowledge.md](./story-knowledge.md) and [audit-workflows.md](./audit-workflows.md).

Details: continuity modules under `v2/domain/modules/continuity_*.py`, [audit-workflows.md](./audit-workflows.md).

---

## Issue #240 / #249 character prompt topology

Default character prompt topology uses harmonized teaching blocks. Environment rollback flags exist for investigation fixtures; production defaults are defined in domain modules and tests under `v2/domain/tests/fixtures/issue240/` and `issue251/`.

---

## Runtime LLM call catalog and characterization (#152)

**Purpose:** Durable map of current production LLM configuration identities, executable quota/reasoning policy, and empirical characterization status — not a historical ledger of retired calls.

| Artifact | Role |
|----------|------|
| `v2/rp_runtime/src/application/application-settings.mjs` | **Executable authority** for reference token ceilings, global enforcement flag, and reasoning overrides |
| `v2/rp_runtime/src/application/llm-call-catalog.mjs` | **Metadata registry** (25 primary runtime rows + 2 harness annex rows) |
| `v2/rp_runtime/src/application/llm-call-catalog-policy.mjs` | Derives reference/enforced quota fields for catalog export |
| `v2/rp_runtime/scripts/generate-llm-call-catalog.mjs` | Deterministic generator |
| `docs/llm-call-catalog.json` | **Committed generated view** (regenerate after policy or characterization changes) |

**Population terminology (do not conflate):** 26 canonical `INFERENCE_KINDS`; 24 production-utilized unique kinds; **25 primary runtime configuration identity rows** (includes distinct `librarian_mediation@character` and `@narrator` quota resolution); 2 harness/test annex identities (visible, non-blocking).

**Global application quota policy (present development period):** Holy-Grail application `maxTokens` ceilings are **globally disabled** (`APPLICATION_TOKEN_QUOTAS_ENFORCED = false`). Ordinary runtime inference omits HG token quotas so natural-completion token and latency evidence can accumulate during LLM/prompt-efficiency work. This is intentional and temporary; restoring or replacing production quotas is deferred to separate governed work. Provider/model-native limits and non-token safeguards (attempt bounds, operator cancellation, retry/recovery boundaries) still apply.

**Reference vs enforced quota in catalog:** Each row carries `reference_application_token_quota` (baseline assignment such as 4096/8192 or `UNCAPPED`) and `application_token_quota: UNCAPPED` reflecting current enforcement. Reference values are for later whole-system latency analysis; they are **not currently enforced**.

**Characterization vs calibration:** `HG_INFERENCE_CHARACTERIZATION=1` remains a controlled measurement/batch mode (labeling, aggregation, experiment semantics). It no longer needs to be enabled merely to remove HG ceilings — ordinary runtime is already uncapped. `HG_INFERENCE_CALIBRATION=1` retains calibration labeling but does **not** reintroduce the historical 4096 HG ceiling while global quota disable is active. Both flags remain mutually exclusive.

**Evidence locations:** raw attempts remain under `data/execution_evidence/`; aggregated characterization summaries under `data/llm_characterization/` (`index.json`, `batches/<batch_id>/manifest.json`, `batches/<batch_id>/summaries/<call_id>.json`). Each batch manifest records `inference_mode` (`mock` or `live`); the catalog generator prefers **live** summaries when present. Mock batches validate infrastructure only and must not be treated as production-faithful token/latency evidence. **Authoritative inference duration (#158):** `inference_health.timing` with `measurement: dsh_session_turn_boundary` (paired DSH `turn/start` → `turn/end` for the ephemeral inference turn). Idle-boundary substrate wait is diagnostic only (`timing.diagnostics.idle_boundary`, not authoritative). Non-LLM orchestration intervals use `correlation.role: execution_span`. Player-wait measurement begins at `application_lifecycle` milestone `operation_began` (correlated by `operation_id`).

**Drift protection:** `v2/rp_runtime/tests/llm-call-catalog-consistency.test.mjs`, `v2/rp_runtime/tests/inference-global-quota-disabled.test.mjs`, plus catalog generator parity check the registry against executable policy and the committed JSON view.

---

## Related

- [rp-data-layout.md](./rp-data-layout.md) — on-disk data
- [scene-grounding-layer.md](./scene-grounding-layer.md) — Scene Grounding MVP
- [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md) — packet seam intent
