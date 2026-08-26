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

- **Retrieval (#31)** — hard access/disclosure constraints, candidate generation, provenance-bearing records, backend abstraction, bounded recall. Does **not** own final semantic relevance. Live authoritative Continuity state is **not** ordinary retrieved lore.
- **Librarian (#34)** — `KnowledgeAccessRequest` in; provenance-aware `LibrarianKnowledgeBundle` out (S2a); deterministic Packaging mapper (S2b); post-commit grounded **`LibrarianSemanticProposal`** batches (S4a) via Host prepare/finalize + DSH inference → Continuity accept/reject boundary; **S4b `knowledge_revelation_significance`** may apply bounded **`PublicEvent.revelation_significance_by_character`** entries (augment-before-replace; **`known_by` unchanged**); **#40 B2 `issue_tension_pressure`** may apply bounded per-issue semantic overlays joined into **`scene_pressures`** (overlay store separate from **`IssueState`**; deterministic pressure fallback preserved). **Librarian may interpret committed truth; it may not manufacture truth.** Continuity remains exclusive transactional writer.
- **Storyteller (#32)** — bounded advisory narrative cognition: orientation → Librarian bundle → informed assessment → `StorytellerAdvisoryPackage` → deterministic Packaging mapper → suggestive `storyteller_*` lanes while the round-local package remains valid. **S3a/S3b/S3c implemented (Model A):** cognition loop, S3b mapper (Director/Character live; Narrator policy is a validated future socket), round-orchestrator pre-Director hook, round-local bind, Director/Character injection, commit invalidation before Narrator. Does **not** control plot outcomes, `next_actor`, Character intent, Narrator events, retrieval, information mediation, or persistence. `PreservationSignal` is an attention hint only and is not mapped to consumer lanes. Invalidated packages are **not** injected into subsequent `prepare_*` calls.
- **Packaging** — deterministic consumer-specific assembly; does not perform semantic relevance ranking or narrative interpretation.

### Current runtime (implemented today)

Character knowledge (#38): DSH **`runCharacterKnowledgeCognition`** → orientation → Character KAR → Librarian **`contextual_semantic`** → **`librarian_*`** manifest lanes via **`map_librarian_bundle_to_contributions`**. Character orientation sees full pre-Librarian upstream context; epistemic boundaries (`bound_character_id`, `known_by` hard access, viewer/subject binding) prevent hidden-knowledge leakage; **`deterministic_fallback`** is packaging-ineligible for Character. Director receives authoritative continuity projections/digests plus Storyteller advisory while the round-local package is valid. Character receives bounded Storyteller advisory (scoped) plus identity/scene/relationship lanes while valid. Authoritative Character commit invalidates the Storyteller package; Narrator then renders from committed move and authoritative scene context **without** Storyteller lanes in the normal flow. Librarian bundles also reach live rounds through the Storyteller cognition path (#32 S3c).

**Live post-commit S4 (#39):** on every successful Character commit, DSH runs Narrator presentation and Librarian **`runLibrarianProposalGeneration`** in parallel from the same commit, then **joins** the Librarian branch (finalize + persist + terminal audit) before the next **`getEligibleActors`** / Director cycle—including multi-commit rounds (per-commit join, not round-end only). Host finalize paths persist authoritative session state and **`librarian_proposal_audit_log`** under per-session locks. See [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md).

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

### Core responsibilities

- Character agents produce self-only structured moves.
- Optional move fields are **not** the authority boundary for issues, tension, or consequences.
- Director selects who acts next.
- Narrator renders prose after commit via deterministic acceptance: normalized `complete` completion, non-empty output, and Host F1/F2 speech fidelity (`narrator_presentation_validation.py`). After F1/F2 acceptance, bounded semantic fidelity QA (#27) reviews presentation against the same legitimate committed source surface via Narrator-local authority references; the evaluator is subordinate QA and does not emit replacement authoritative prose. Single two-generation Narrator budget (`MAX_NARRATOR_ATTEMPTS = 2`); soft exhaustion accepts with residual concerns; hard exhaustion or evaluator infrastructure failure uses deterministic degraded presentation from the committed `structured_move` when available (#29), otherwise committed-turn summary fallback (#24). Per-role reasoning profiles and **generous runaway-safety token ceilings** (director/character/opening 4096, narrator 8192, semantic evaluator 2048; tunable via `application-settings.mjs`) are internal runtime configuration (#29); Streamlit no longer exposes a global reasoning selector. Provider `reasoningEffort: off` maps to `thinking: disabled` at the adapter boundary. Set `HG_INFERENCE_CALIBRATION=1` for bounded diagnostic token ceilings (4096) during calibration runs only.
- Continuity manager updates durable scene and issue state.
- Validation and enforcement remain separate from prompt styling.
- **`perception_audibility.py`** gates who may see dialogue and narrator render for others' beats.

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

**Forensic execution evidence (#28):** Director/Narrator semantic QA patches use canonical **`decision.semantic_qa`** (including **`policy_action`**) on candidate attempts; participation-direct writes **`role: participation`** non-inference records; Director attempts carry bounded **`decision.director.eligibility`**. Derived navigation indexes (`qa_pass_chains`, `participation_by_round`) support investigation tooling — see [docs/rp-data-layout.md](./rp-data-layout.md) and [docs/audit-workflows.md](./audit-workflows.md). Post-#28 forensic completeness applies to sessions produced after #28 lands. **Forward standard** for new seams and decisions: [forensic-auditability-standard.md](./forensic-auditability-standard.md).

Validators **reject or annotate**; they do not replace Director selection or continuity commits.

**Director fallback:** on JSON parse failure, Host/DSH decision handling may record `"source": "fallback"`. Turn-selection preemption validation is skipped for fallback decisions; memory writes for committed turns are not.

**Director auxiliary contract (#23):** Host validation normalizes `tension_shift` to `escalate` / `soften` / `steady`. Unsupported values are neutralized to `steady`. `environment_event` remains a proposal until Host exact-deduplicates it against bounded continuity-owned environment evidence (Unicode NFKC, whitespace normalization, casefold) and continuity commits the normalized decision. Auxiliary normalization does not retry an otherwise-valid actor selection.

---

## Memory layer

**Policy owner** for episodic writes and prompt read/format. `CharacterState` holds storage plus identity/relationship prompt text.

- **Writes:** commit-time only, perception-filtered observers (`memory_layer/facade`, `writes`, `storage`).
- **Reads:** `memory_layer/retrieval.py` builds episodic sections for `state_context`.

### Prompt context contract

- Character/Director/Narrator **interpretation** is composed in Domain Host (`continuity_context_projector.py`, `character_context_projector.py`, `kernel.prepare_*`) using domain `prompt_builders.py` and memory/retrieval services.
- **Character live manifest** (`kernel.prepare_context`): `character_identity` and `character_expression` project authoritative `CharacterState` portrayal fields (description, personality, goals, voice, reaction, speech fingerprint); `character_relationships` bounds relationship threads to the present cast; `scene_context` merges setup, progression, and role map; `scene_pressures` surfaces bounded active issues; `director_context` carries advisory Director handoff (`reason`, `environment_event`, `tension_shift` only — suggestive, not orchestration). Existing lanes remain: continuity canon/grounding/constraints, perception-filtered transcript/trigger, knowledge, memory, round committed moves, and `inference_instruction`. `hidden_agenda` is not projected. Identity duplicate canon anchors (`character_state.*` profile sources) are filtered from `continuity_canon` on the Character path.
- **Director manifest** (`kernel.prepare_director_context`): orchestration digests plus authoritative scene setup/state/progression; does not receive Character-private lanes.
- **Narrator manifest** (`kernel.prepare_narrator_context`): committed-move rendering surface plus bounded scene setup/state/progression; does not receive Director scratch or Character-private lanes.
- `prompt_builders` formats prompt text; it does not re-read memory buckets or own round sequencing.
- DSH `HgContextBridge` registers the Host manifest on an ephemeral inference agent and does not reinterpret authority classes.

---

## Continuity authority and evidence lanes

**`SceneState`** and **`process_turn`** define committed truth. Distinguish **intent**, **interpretation**, **commit**, and **observation**. Narrator prose and classifier signals do not override `SceneState`.

Details: continuity modules under `v2/domain/modules/continuity_*.py`, [audit-workflows.md](./audit-workflows.md).

---

## Issue #240 / #249 character prompt topology

Default character prompt topology uses harmonized teaching blocks. Environment rollback flags exist for investigation fixtures; production defaults are defined in domain modules and tests under `v2/domain/tests/fixtures/issue240/` and `issue251/`.

---

## Related

- [rp-data-layout.md](./rp-data-layout.md) — on-disk data
- [scene-grounding-layer.md](./scene-grounding-layer.md) — Scene Grounding MVP
- [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md) — packet seam intent
