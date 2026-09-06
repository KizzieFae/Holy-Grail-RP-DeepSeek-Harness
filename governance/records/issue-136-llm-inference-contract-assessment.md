# LLM Inference-Contract Architecture Assessment — Issue #136

**Assessment parent Issue:** [#136 — System-level LLM inference-contract and prompt architecture assessment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**Assessment dates:** 2026-09-06 (Phase 1 investigation)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full (`docs/issue-bootstrap-profiles.md`)  
**Remediation authorization on #136:** NONE (assessment only)  
**External review:** PR + Greptile required per #136 validation criteria

---

## Repository anchor (immutable at assessment publication)

| Field | Value |
|-------|-------|
| branch | `main` (assessment branch at PR) |
| investigation execution baseline | `c616d98912474cc1b3366ac21afebe9397885de3` |
| assessment publication commit | *(set at PR — see PR for exact SHA)* |

---

## 1. Executive summary

Holy Grail RP implements a **distributed inference architecture**: every RP LLM call is an **inference contract** assembled from `PromptContribution` manifests validated by `manifest_projection_policy.py` (#134), invoked through DSH `runEphemeralInference()` (`inference-substrate.mjs`), with Domain Host context packaging in `v2/domain_api/*_context.py`.

**Five core roles** are not monolithic system prompts. Each role may involve **multiple** LLM calls (primary + semantic QA + cognition/mediation sub-pipelines). Character is the deepest chain (orientation → Librarian mediation → optional plot cognition → move → semantic evaluation). Storyteller is advisory-only at round start. Librarian serves both read-side mediation and post-commit write-side proposals.

**Strengths observed from repository inspection:**

- Clear separation of **authoritative context projection** (`continuity_context_projector.py`) from **model-facing instructions** (`inference_instruction` contributions and DSH envelope prompts).
- Deterministic validation layers (move parse, narrator fidelity F1/F2, perceptual visibility, semantic QA rubrics) surround generative calls rather than relying on prompts alone.
- `manifest_projection_policy.py` enforces allowed `source_kind` lanes per `inference_kind`, reducing uncontrolled context injection.
- Narrator render instructions (`narrator_render_instruction.py`) encode verbatim dialogue contract and environmental duty economically with structured-move authority.
- Storyteller and Librarian proposal paths are explicitly **non-authoritative** for continuity mutation.

**Primary risks / refinement areas (repository inspection; runtime causality not claimed):**

- **Instruction duplication** between DSH `live-inference-prompts.mjs` and Host `inference_instruction` contributions for Director/Character (same JSON shape stated twice).
- **Context volume** from stacked advisory overlays (Storyteller, plot cognition, scene digests, Librarian bundles) competing with transcript and character state in Character/Director manifests.
- **Legacy drift:** `prompt_builders.py` remains in tree but is off the hot path — documentation risk only.
- **Auxiliary call cost:** Player PVR triage + decomposition and multi-step Character cognition multiply inference per player turn and per character turn.
- Several fidelity concerns are **architecturally owned by validation** (semantic QA, narrator fidelity) rather than prompt prose — assessment must not recommend prompt expansion where enforcement already exists.

**Phase 1 attestation:** No production prompts or runtime behavior were modified during this assessment.

---

## 2. Scope and methodology

### In scope

- Complete inventory of RP-relevant LLM calls in `v2/rp_runtime/` and matching Domain Host packaging.
- Architectural assessment of Director, Character, Narrator, Storyteller, Librarian as coupled inference roles.
- Auxiliary calls that analyze/decompose/transform inputs consumed downstream (player PVR, opening, segmentation, plot cognition, semantic QA).
- Cross-role handoffs, context projection, duplication, and prompt economy.
- Findings classified per `governance/sources/audit-semantics.md`.

### Out of scope (Phase 1)

- Prompt rewrites or runtime changes.
- Controlled longitudinal RP behavior attribution.
- Child Issues per agent.
- Implementation consensus.

### Method

1. Trace `runEphemeralInference` / `runInferenceWithContractCorrection` call sites in DSH phase executors.
2. Map each call to Domain Host `prepare_*` / `finalize_*` endpoints and context modules.
3. Read prompt/instruction sources: `live-inference-prompts.mjs`, `*-envelope.mjs`, `*_context.py` instruction contributions, `narrator_render_instruction.py`, `narrative_visibility_prompt.py`.
4. Trace consumers and validation per `MODULE_INDEX.md` and kernel validators.
5. Apply assessment principles (fidelity over valence, clear beats elaborate, role ownership, minimum-effective-prompt) as **evaluation lenses**, not assumed defects.

---

## 3. Workflow weight / repository anchor

| Item | Value |
|------|-------|
| Issue | #136 |
| Assigned weight | `standard` |
| Effective weight | `full` (architecture-sensitive multi-role investigation) |
| Bootstrap | Full per `docs/issue-bootstrap-profiles.md` |
| Base SHA | `c616d98912474cc1b3366ac21afebe9397885de3` |

---

## 4. Current LLM call-flow map

### 4.1 Shared substrate

```text
hg-application-client.mjs (player turn, opening)
        │
        ▼
hg-round-orchestrator/service.mjs
        │
        ├── Storyteller cognition (round start, skippable)
        │     orientation → librarian_mediation → assessment → bind advisory
        │
        └── loop until end_round
              ├── Director (+ director_semantic_qa)
              ├── Character (+ orientation → mediation → projection? → move + semantic_eval)
              │     └── commitMove
              ├── par async: Librarian proposal + Plot cognition lifecycle
              └── Narrator (+ env cognition → presentation + narrator_semantic_qa)
```

### 4.2 Pre-round / session paths

| Phase | Trigger | DSH executor | Host context |
|-------|---------|--------------|--------------|
| Player visibility triage | Player turn submit | `player-visibility-triage-phase.mjs` | `player_visibility_triage_context.py` |
| Player decomposition | Triage not uniform-safe | `player-decomposition-phase.mjs` | `player_decomposition_context.py` |
| Opening | Session bootstrap | `opening-phase.mjs` | `opening_context.py`, `opening_prompt.py` |
| Opening segmentation | After opening persist | `opening-segmentation-phase.mjs` | `opening_segmentation_context.py` |

### 4.3 Inference entry point

All calls funnel through `v2/rp_runtime/src/plugins/hg-phase-executors/inference-substrate.mjs` → `runEphemeralInference()`. Context bridge (`hg-context-bridge/service.mjs`) binds Host `PromptContribution` manifests into DSH agent context.

---

## 5. Inference-contract inventory

Canonical `inference_kind` values: `manifest_projection_policy.py` (`INFERENCE_KINDS`).

| Call / role | Caller / trigger | Architectural responsibility | Prompt / instruction sources | Dynamic + structured context | Output | Consumer | Authority | Validation / retry | Cross-role handoff | Volume concern | Tests / docs |
|-------------|------------------|------------------------------|-------------------------------|-------------------------------|--------|----------|-----------|-------------------|-------------------|----------------|--------------|
| **director_turn** | `director-phase.mjs` per round loop | Select next actor, end_round, tension_shift, optional environment_event | `LIVE_DIRECTOR_PROMPT`; `director_context.py` `inference_instruction`; scene digests | `project_authoritative_context`, storyteller advisory, plot overlay, eligible actors, scratch | JSON: next_actor, end_round, reason, environment_event, tension_shift | Round orchestrator → Character phase | **Authoritative** for actor selection (validated) | `validate_director_decision`; candidate budget; director semantic QA regen | Storyteller advisory in; decision to Character upstream | Moderate — digests + advisory stack | `director_context.py`, `test_manifest_policy_parity` |
| **director_semantic_qa** | Inside director phase | Advisory rubric on director candidate | `director-semantic-qa.mjs`, `director_semantic_qa_context.py` | Candidate + manifest context | `hg_semantic_qa_result_v1` | `applyDirectorSemanticPolicy` | **Advisory** gate | Soft/hard regen | Director candidate loop | Adds full eval call | semantic-qa tests |
| **storyteller_orientation** | Round start `storyteller-cognition-substrate.mjs` | Identify information gaps (focus questions) | `storyteller-orientation-envelope.mjs`; `storyteller_orientation_context.py` instruction | Scene snapshot, pressures, orchestration digest, user turn hints | `hg_storyteller_orientation_v1` | Mediation request builder | **Advisory** | `finalizeStorytellerOrientation` | → librarian_mediation → assessment | Bounded snapshots | #32 storyteller tests |
| **storyteller_assessment** | After ST mediation | Narrative priorities/tensions/hooks (advisory) | `storyteller-assessment-envelope.mjs`; `storyteller_assessment_context.py` | Orientation + librarian bundle digest | `hg_storyteller_assessment_v1` | `bindStorytellerAdvisoryPackage` → role manifests | **Advisory** | finalize + packaging validity | Packaged to Director/Character/Narrator | Caps on bundle entries (12×480 chars) | storyteller_packaging_* |
| **librarian_mediation** | ST cognition, Character orientation, Narrator env cognition | Select catalog entries for knowledge access request | `librarian-mediation-envelope.mjs`; `librarian_mediation_context.py` | KnowledgeAccessRequest + mediation catalog | `hg_librarian_mediation_result_v1` | LibrarianKnowledgeBundle → consumer packaging | **Advisory** bundle; authoritative catalog bounds | `finalizeLibrarianMediation` | Feeds Character/ST/Narrator contexts | Catalog size dependent | #34 S2a tests |
| **character_orientation** | Start of `character-phase.mjs` | Character knowledge cognition / access request | `character-orientation-envelope.mjs`; orientation context | Upstream auth context, memory | `hg_character_orientation_v1` | → librarian mediation | **Advisory** request | finalize orientation | Precedes move manifest | Extra call per character turn | character-cognition-substrate |
| **character_turn** | Character phase after cognition | Produce structured move (beats, motivation) | `LIVE_CHARACTER_PROMPT`; `character_context.py` instruction; upstream projector | Auth context, transcript, director decision, memory, librarian bundle, storyteller/plot overlays, correction | move_schema_version 2 JSON | `commitMove` → continuity | **Proposed** until validated/committed | `validate_move`; semantic eval; candidate budget | Director in; commit triggers Narrator/Librarian/Plot | **High** — richest manifest | character validation tests |
| **character_semantic_evaluation** | After move parse in character phase | Pre-commit prose/behavior rubric (R02b,R11,R12,R14,R15) | `character-semantic-evaluation.mjs` inline schema | Prepared semantic eval context | `hg_semantic_evaluation_result_v1` | Gates commit; correction_context | **Advisory** enforcement gate | soft/hard reject + regen | Character regen loop | Extra call per candidate | semantic_evaluation_context |
| **plot_cognition_*** | Post-commit async; optional character projection | Epistemic/plot overlay proposals | plot-cognition-*-envelope.mjs | Turn evidence, overlay service | init/update/replan schemas | Overlay contributions to Director/Character | **Advisory** | contract correction substrate | Parallel to Librarian proposal | Overlay duplication risk | plot cognition tests |
| **librarian_proposal** | Post-commit `librarian-proposal-substrate.mjs` | Propose consequence/salience/significance (no direct write) | `librarian-proposal-envelope.mjs` | Evidence catalog from committed turn | `hg_librarian_proposal_result_v1` | Audit batch; downstream pressure projection | **Proposed** | validate batch; contract correction | After character commit | Large catalog possible | #34 S4 tests |
| **narrator_environment_cognition** | Start `narrator-phase.mjs` | Resolve environmental information needs | cognition substrate inline JSON | Env packet, story records, turn context | baseline_sufficient, resolutions[] | Environmental obligations → narrator manifest | **Advisory** obligations | finalize cognition; may chain mediation | Precedes presentation | Known duplication concern (#131) | narrator_environment_* |
| **narrator_presentation** | After character commit | Render committed move to prose (+ NVR) | `LIVE_NARRATOR_PROMPT`; `build_narrator_render_prompt()`; visibility instruction | Auth projections, structured move (redacted), env baseline/obligations, storyteller advisory | Prose and/or JSON envelope with perceptual_visibility | Session history / UI | **Rendered** (non-authoritative for continuity) | F1/F2 fidelity; NVR validate; narrator semantic QA; max 2 attempts | Committed move in | Render rules + env duty block length | #24 narrator validation |
| **narrator_semantic_qa** | After presentation validation | Attribution/contradiction/invention rubric | `narrator-semantic-qa.mjs` | Presentation + context | `hg_semantic_qa_result_v1` | `applyNarratorSemanticPolicy` | **Advisory** gate | regen policy | Narrator loop | Extra call | narrator semantic tests |
| **opening** | Session bootstrap | Initial scene narration | `OPENING_PROMPT`; `opening_prompt.py` | Opening context manifest | presentation_text + optional NVR | Session history | **Rendered** | persist + NVR | Pre-round | Single session call | opening_context |
| **opening_segmentation** | After opening | NVR units for opening prose | segmentation phase + `OPENING_SEGMENTATION_OUTPUT_INSTRUCTION` | Opening text | perceptual_visibility.units | Opening metadata | **Derived** | NVR validation | After opening | One-time | #90 |
| **player_visibility_triage** | Player turn | Route uniform vs full PVR | `buildPlayerVisibilityTriageUserPrompt` | Entitlement + scene context | uniform_projection_safe | Decomposition vs shortcut | **Advisory** routing | parse boolean | Before decomposition | One call per player turn | #121 |
| **player_decomposition** | Player turn (non-uniform) | Semantic units for player text | `PLAYER_DECOMPOSITION_TASK_PROMPT` | PVR entitlement context | semantic_decomposition.units | Per-character perceptual records | **Proposed** → normalized | Host normalize | Before round | Cost/reliability (#112) | #109, #125 |

**Runtime aliases:** `director_decision` → `director_turn`; `character_move` → `character_turn` (`manifest-projection-policy.mjs`).

**Legacy (not hot path):** `v2/domain/modules/prompt_builders.py` — monolithic Director/Character prompts; superseded by manifest assembly.

---

## 6. Director assessment

### Clarity and scope

Director inference contract is **economical and well-scoped**: JSON-only output with explicit keys; scratch contribution states participation balance without prescribing narrative outcomes. `director_scene_evidence_contributions` and `continuity_context_projector` supply authoritative scene state separately from instructions.

### Responsibility alignment

Selection authority correctly belongs to Director; eligibility is pre-computed (`available_actors`) and validated post-hoc (`validate_director_decision`, `response_validation_selection.py` helpers). Storyteller/plot overlays are advisory lanes with distinct `source_kind` values gated by projection policy.

### Prompt economy

**Worthwhile refinement:** `LIVE_DIRECTOR_PROMPT` and `director_context.py` `inference_instruction` duplicate the same JSON contract. This is not a functional defect but adds token overhead and drift risk if one side updates without the other.

### Fidelity / drift lenses

Director does not generate character prose; drift risks are **orchestration-level** (wrong actor, inappropriate end_round, environment_event repetition). Instruction already discourages repeating recent environment developments. Semantic QA dimensions (`dir_*`) provide runtime checking beyond prompt text.

### Validation interaction

Director candidate budget + semantic QA implement **enforcement**; prompts remain minimal. Correct pattern per assessment principle 9.

### Already appropriate

- Separation of scratch guidance from authoritative projections.
- `tension_shift` enum constraint in both DSH and Host instruction.
- Context completeness validation (`validate_director_context_completeness`).

### Requires runtime evidence

Whether advisory overlays materially improve selection quality vs. context competition cannot be determined from static inspection alone.

---

## 7. Character assessment

### Clarity and scope

Character primary contract is **operational** (JSON move schema) with descriptive motivation object. Upstream manifest carries character identity, transcript, memory, perception-filtered history, director decision, and optional overlays — aligning descriptive state with structured output requirements.

### Pipeline depth

Character has the **deepest inference chain**: orientation → Librarian mediation → optional plot cognition projection → move → semantic evaluation. Each step has distinct architectural responsibility; risk is **cost and latency**, not necessarily prompt ambiguity.

### Descriptive vs operational

Character cards and `character_context_projector` supply descriptive characterization; move schema supplies operational structure. Absence of lengthy behavioral prose in prompts is **not inherently defective** per assessment principles 3–4.

### Fidelity preservation

Semantic evaluation dimensions (R02b, R11, R12, R14, R15) target unsupported transformation classes (player control, relationship drift, etc.) at **validation** layer. `buildCorrectionContextFromEvaluation` provides economical regen instruction.

### Action commitment

Action avoidance would manifest in action beats with excessive qualification; semantic eval may partially detect via R11/R12 but **runtime evidence required** to assess prevalence.

### Context competition

**Architectural debt (context volume):** Character manifest stacks auth projections, round transcript, memory, librarian bundle, storyteller advisory, plot overlay, and correction context. `manifest_projection_policy.py` helps lane discipline but does not cap total volume.

### Duplication

Character `inference_instruction` duplicates `LIVE_CHARACTER_PROMPT` schema elements (same as Director).

### Already appropriate

- Librarian bundle mapping with eligibility audit trail in provenance.
- `assemble_character_upstream_contributions` fingerprint for traceability.
- Private secret handling separated from global scene state.

---

## 8. Narrator assessment

### Clarity and scope

Narrator has **split contracts**: (1) environment cognition (JSON resolutions), (2) presentation (prose + optional NVR JSON). Render path is the most instruction-rich, appropriately so because rendering is the operational responsibility.

### Responsibility alignment

`redact_structured_move_for_orchestration` ensures narrator sees orchestration-safe move view. `build_narrator_render_prompt` encodes verbatim speech substring rules and environmental duty (#49/#89) with structured-move authority — strong alignment between structured input and render obligations.

### Prompt economy tension

`narrator_render_instruction.py` immersive rules block is substantive but targets a genuine operational gap (environmental presence) that structured move JSON does not carry. **Worthwhile refinement** candidate: ensure obligations are projected once (see #131 duplication concern) rather than expanding prose further.

### Fidelity / action avoidance

F1/F2 deterministic validation and narrator semantic QA (`nar_*` dimensions) enforce fidelity; prompts should not duplicate enforcement prose. `LIVE_NARRATOR_PROMPT` is intentionally minimal because manifest carries render instruction.

### NVR interaction

`NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION` shared across narrator, opening, segmentation, player decomposition — good single-source pattern in `narrative_visibility_prompt.py`.

### Already appropriate

- Third-person past tense, beat-order preservation, verbatim dialogue rules for v2 moves.
- Environmental baseline authority labeling.
- Max 2 presentation attempts with correction path.

### Requires runtime evidence

Whether immersive environment duty prose improves perceptual quality vs. token cost; whether cognition step is always necessary when baseline is sufficient.

---

## 9. Storyteller assessment

### Clarity and scope

Storyteller is explicitly **advisory** and **non-mutating**. Orientation instruction forbids prescribing plot outcomes, actor selection, dialogue, or continuity mutations. Assessment instruction consumes librarian bundle digest with bounded entry caps.

### Coupled system role

Storyteller runs **once per round** before Director loop, binding advisory package consumed by all three downstream role manifests via `storyteller_round_packaging.py` and `storyteller_contributions_for_consumer`. This is the correct architectural pattern for cross-role narrative guidance without authority leakage.

### Prompt economy

Instructions are relatively compact; bulk context is structured JSON digests. Packaging mapper applies consumer-specific policies — good separation.

### Fidelity lenses

Risk: advisory text could be misread as mandatory plot direction. Mitigation: `authority_class` on contributions and packaging validity gates. **Repository inspection supports design intent**; misinterpretation frequency needs runtime evidence.

### Already appropriate

- Three-step cognition (orientation → mediation → assessment) mirrors Character knowledge pattern consistently.
- `STORYTELLER_ORIENTATION_CONTRACT` / `STORYTELLER_ASSESSMENT_CONTRACT` versioning.
- Skip flag `skipStorytellerCognition` for controlled degradation.

---

## 10. Librarian assessment

### Dual inference contracts

**Read-side mediation** and **write-side proposal** are correctly separated:

| Path | When | Authority |
|------|------|-----------|
| Mediation | On-demand from ST/Character/Narrator cognition | Selects from Host-built catalog; bundle is advisory |
| Proposal | Post-commit async | Proposals validated; no direct continuity write |

### Clarity

Mediation prompt emphasizes information plane only (`KnowledgeAccessRequest`). Proposal envelope (`librarian-proposal-envelope.mjs`) is schema-explicit with forbidden field aliases — strong contract discipline (#72).

### Responsibility alignment

Librarian does not replace Character voice or Narrator rendering. Proposal kinds (`consequence_meaning`, `information_salience`, etc.) map to downstream projection helpers (`continuity_librarian_*`).

### Context volume

Proposal evidence catalog can be large (`librarian_proposal_context.py` builds from history, issues, premises). Host truncates excerpts (`_MAX_PREMISE_EXCERPT`, etc.) — economical bounds present.

### Already appropriate

- Catalog `source_id` validation on finalize.
- Contract correction substrate for structural failures.
- Epistemic authority metadata on proposal anchors.

### Worthwhile refinement

Ensure proposal catalog projection and issue-pressure overlay (#40) do not duplicate the same pressure facts in Director/Character manifests when already digested elsewhere — **potential duplication**; confirm with manifest forensics in runtime audits.

---

## 11. Auxiliary LLM-processing observations

### Player input path

1. **Visibility triage** — routes expensive decomposition; economical boolean contract.
2. **Decomposition** — highest auxiliary cost/risk (#112 evidence: 0% usable PVR in natural experiment while RP remained coherent). Architectural question is **when** full decomposition is necessary, not prompt wording alone.

### Opening path

Opening + segmentation mirror narrator NVR pattern for session start. Instructions centralized in `narrative_visibility_prompt.py`.

### Plot cognition

Post-commit async lifecycle parallels Librarian proposal. Overlay contributions to Director/Character are **advisory** via `plot_cognition_overlay_service.py`. Adds inference cost; value requires runtime evidence.

### Semantic QA family

Director, Character, and Narrator each have dedicated semantic eval calls sharing `semantic-qa-substrate.mjs` patterns. This is **architectural enforcement**, not prompt bloat — correct per principle 9.

---

## 12. Cross-role / context-projection assessment

### Handoff graph (material)

```text
Storyteller advisory ──► Director / Character / Narrator manifests
Director decision ──► Character upstream (director_decision field)
Character commit ──► Narrator (committed_move); Librarian proposal; Plot cognition
Librarian mediation ──► Character / Storyteller / Narrator env cognition
Narrator env cognition obligations ──► Narrator presentation manifest
Player decomposition ──► per-character perceptual records ──► Character/Narrator visibility context
```

### Projection policy (#134)

`manifest_projection_policy.py` is the **authoritative allowlist** for which `source_kind` values may appear per `inference_kind`. This implements architectural ENTITLEMENT/DECISION-RELEVANCE separation under different names.

### Cross-role risks

| Risk | Mechanism | Classification |
|------|-----------|----------------|
| Advisory read as authoritative | Missing authority_class discipline | **correct as-is** if packaging honored; runtime misread unverified |
| Duplicate JSON instructions | DSH + Host both state schema | **worthwhile refinement** |
| Overlay + digest redundancy | Multiple projections of scene pressures | **architectural debt** (see #131) |
| Legacy prompt_builders confusion | Dead code path | **worthwhile refinement** (docs/deprecation) |

---

## 13. Context-budget and duplication assessment

| Source | Roles affected | Concern |
|--------|----------------|---------|
| Round transcript in Character upstream | Character | Necessary; grows per turn |
| Storyteller advisory lanes | Director, Character, Narrator | Bounded by packaging policy |
| Scene pressure / orchestration digests | Director, Storyteller | Possible overlap with continuity summaries |
| Librarian bundle entries | Character, Storyteller assessment | Capped (12 entries, 480 chars) |
| Director/Character JSON instructions | Director, Character | Duplicated DSH+Host |
| Narrator env cognition + obligations text | Narrator | #131 flagged projection duplication |
| Semantic QA calls | All core roles | Extra full inference per candidate — trade enforcement for tokens |

**Recommendation direction (not authorized):** Prefer projection/selection fixes over expanding instructional prose when duplication is the issue.

---

## 14. Findings with evidence and classifications

| ID | Finding | Evidence | Classification | Disposition |
|----|---------|----------|----------------|-------------|
| F-136-01 | Inference architecture is manifest-based with per-kind allowlists | `manifest_projection_policy.py`, `inference-substrate.mjs` | **correct as-is** | Document as canonical pattern |
| F-136-02 | Director/Character JSON instructions duplicated across DSH and Host | `live-inference-prompts.mjs` vs `director_context.py` / `character_context.py` | **worthwhile refinement** | Single-source instruction ownership (future Issue) |
| F-136-03 | Character inference chain is deep (3–5+ calls per turn) | `character-phase.mjs`, `character-cognition-substrate.mjs` | **architectural debt** (cost/latency) | Assess skip/degrade policies with runtime metrics |
| F-136-04 | Narrator render contract is well-structured with deterministic fidelity enforcement | `narrator_render_instruction.py`, `narrator_presentation_validation.py` | **correct as-is** | Preserve; avoid prompt rewrites |
| F-136-05 | Storyteller advisory packaging respects non-authoritative boundary | `storyteller_orientation_context.py` instructions, packaging mappers | **correct as-is** | Preserve separation |
| F-136-06 | Librarian read/write paths correctly separated | mediation vs proposal modules | **correct as-is** | Preserve |
| F-136-07 | `prompt_builders.py` legacy off hot path | MODULE_INDEX.md, no imports from domain_api | **worthwhile refinement** | Deprecation doc only |
| F-136-08 | Player PVR decomposition reliability historically poor | issue-112 evidence | **architectural debt** | Runtime gating (triage) already exists; further work needs evidence |
| F-136-09 | Semantic QA provides enforcement beyond prompts | `*-semantic-*.mjs`, kernel validators | **correct as-is** | Do not duplicate in prompts |
| F-136-10 | Narrator env cognition projection duplication | #131 (related) | **architectural debt** | Tracked separately; cross-reference |

---

## 15. Areas assessed as already appropriate / no-change

- Manifest projection policy as inference-contract boundary (#134).
- Director selection validation pipeline (kernel + semantic QA).
- Character move schema v2 with beats/motivation separation.
- Narrator verbatim dialogue contract for structured moves.
- Storyteller non-mutating advisory role and round binding.
- Librarian proposal non-write semantics with schema enforcement.
- Perception/redaction path into narrator (`redact_structured_move_for_orchestration`).
- Centralized NVR instructions in `narrative_visibility_prompt.py`.
- Contract correction substrate for structural parse failures (max-1 retry).

---

## 16. Uncertainties and questions requiring runtime evidence

1. **Causal attribution:** Do observed RP fidelity issues correlate with specific prompt sections vs. validation failures vs. context omissions?
2. **Storyteller value:** Does advisory package improve downstream quality enough to justify token/latency cost?
3. **Character cognition steps:** When is orientation→mediation necessary vs. skip-safe?
4. **Plot cognition overlay:** Material effect on Director/Character choices?
5. **Player PVR:** Failure rates under current model/settings in production profile.
6. **Action avoidance:** Prevalence of qualification loops in action beats without semantic eval catch.
7. **Context competition:** At what manifest size do model failures increase?

---

## 17. System-level architectural observations

1. **Holy Grail does not use a monolithic system prompt** — correct architectural choice for role separation.
2. **Enforcement is layered:** parse validators → semantic QA → deterministic fidelity checks → continuity authority.
3. **Information vs decision relevance** is implemented via `source_kind`, `authority_class`, projection policies, and perception filters — not via a single named subsystem.
4. **Auxiliary calls materially shape downstream inference** (player decomposition, ST cognition, env cognition) and must be assessed as part of the coupled system.
5. **Minimum-effective-prompt** is often already practiced for Director/Character user prompts; Narrator render instruction is the exception where operational detail is warranted.

---

## 18. Candidate improvement directions (NOT authorized)

1. **Instruction single-sourcing** — Host-owned `inference_instruction` OR DSH user prompt, not both, for Director/Character JSON contracts.
2. **Manifest volume budgets** — per-role token/entry caps with deterministic trimming order (after forensic identification of low-value lanes).
3. **Conditional cognition** — skip orientation/mediation/env cognition when sufficiency flags true (partial patterns exist).
4. **PVR path rationalization** — build on #112/#121 triage outcomes; do not assume always-on decomposition.
5. **Legacy cleanup** — mark `prompt_builders.py` deprecated in MODULE_INDEX only (no deletion without consensus).
6. **Cross-reference #131** — narrator env cognition duplication remediation before prompt expansion elsewhere.

**Explicitly not recommended without evidence:** broad behavioral policy prose in Character prompts; valence-optimizing instructions; large negative-prohibition catalogs.

---

## 19. Recommended subjects for Governance consensus

1. Whether Phase 2 should prioritize **instruction deduplication** or **manifest volume caps** first.
2. Acceptable **inference cost budget** per player turn / per character turn.
3. Whether **Storyteller cognition** remains default-on for all sessions.
4. **Player PVR** strategic disposition (narrow, redesign, conditional) building on #112.
5. Scope boundaries for successor Issues (by Layer, not by agent persona).
6. Required **runtime audit protocol** before any prompt remediation Issue reaches `consensus_reached`.

---

## 20. No-implementation / no-runtime-behavior-mutation attestation

**Attestation:** Phase 1 assessment (#136) modified **only** this assessment document (and governance workflow artifacts). **No** production prompts, inference code, runtime behavior, or validation policies were changed during this investigation.

---

## Greptile review record

*(Completed in PR — see `governance/records/issue-136-pr*-greptile-review-*.md`)*
