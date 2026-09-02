# Repository-Wide Architectural Efficiency & Redundancy Audit

**Audit parent Issue:** [#98 — Repository-wide architectural efficiency and redundancy audit](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/98)  
**Audit dates:** 2026-09-01 (investigation and report at repository anchor)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full (`docs/issue-bootstrap-profiles.md`)  
**Remediation authorization this cycle:** NONE  
**Report commit:** `10289f8d8eb0959005b2f6332dc4f8e5e315aeeb` (initial); consolidated refinement per external verification — see audit PR #99 head  
**External review:** PR [#99](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99); Greptile conversational challenges incorporated by Governance (see §External verification)

---

## Repository anchor (immutable)

| Field | Value |
|-------|-------|
| branch | `main` |
| HEAD SHA | `ba54016e37c914b54f081110ab0986349063a5be` |
| origin/main SHA | `ba54016e37c914b54f081110ab0986349063a5be` |
| divergence | `0` ahead / `0` behind |
| working tree at activation | clean |

---

## Primary audit question

> Across the system as it exists today, are we solving the same responsibility more than once, enforcing the same invariant through multiple mechanisms, or retaining architecture that no longer needs to exist?

---

## Methodology

1. **Full bootstrap** per `docs/issue-bootstrap-profiles.md` (AGENTS.md, architecture-overview, audit-semantics, issue-tracking-workflow, MODULE_INDEX, docs/architecture.md, docs/rp-data-layout.md, docs/forensic-auditability-standard.md, docs/audit-workflows.md, bindings).
2. **Responsibility-cardinality inventory** — for each major architectural responsibility, count independently executing mechanisms; treat cardinality >1 as investigation trigger, not automatic finding.
3. **Static trace** — callers/callees, write paths, documentation authority, tests proving reachability.
4. **Counterevidence discipline** — for each candidate finding, search for trust-boundary, authority/projection, deterministic/semantic, persistent/ephemeral, and defense-in-depth justifications.
5. **Read-only investigation** — no production/test/config mutation during evidence gathering.

---

## Coverage

### Investigated (sections A–L)

| Area | Coverage |
|------|----------|
| A. Duplicate responsibility / authority | Full static trace across turn selection, continuity, validation, context |
| B. Privacy / knowledge boundaries | perception_audibility, known_by, retrieval, Librarian, PVR, plot cognition |
| C. Validation / semantic-QA duplication | ingress → parse → runtime rules → Host validate → semantic eval → narrator QA |
| D. Persistence / mutation authority | session, rp_history, memory, story knowledge, overlays, forensics |
| E. Context preparation / mediation | kernel.prepare_*, projector, Librarian/Storyteller mappers, Scene Grounding |
| F. Legacy / superseded architecture | perceptual_visibility_legacy, character_move_adapters, v1 ingress removal, prompt_builders |
| G. DSH / Cordis duplication | mount-hg-services, round orchestrator vs Cordis Service lifecycle |
| H. Execution-evidence / forensic duplication | execution-evidence, trace emitter, rp_history, audit tags, librarian audit log |
| I. Contract / configuration fragmentation | reasoning effort, retry budgets across phase executors |
| J. Unnecessary indirection | HgContextBridge, substrates, domain-api-client |
| K. Dead / obsolete architecture | LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS, FixtureStore, scenario-only validators |
| L. Aggregate accidental complexity | cross-store reconstruction, validation depth, S4 post-commit seam |

### Explicit gaps

- **Live multi-turn scenario replay** at audit anchor — not executed; static/test reachability only.
- **Greptile conversational verification** — full challenge cycle incorporated (Governance-accepted dispositions); see §External verification. External review is evidence, not governance authority; absence of an additional Greptile finding is not proof of absence.
- **Full DSH/Cordis upstream capability inventory** — compared architectural roles, not exhaustive semver feature matrix of `@deepseek-ai/cordis` packages.
- **Every config literal** — sampled retry/reasoning fragmentation; not exhaustive grep of all duplicated constants.
- **Node application API** (`v2/rp_runtime` application layer beyond orchestrator) — surveyed for session lifecycle overlap only.

---

## Material findings summary

| ID | Title | Classification | Significance | Confidence |
|----|-------|----------------|--------------|------------|
| A1 | Post-commit Librarian S4 as bounded second continuity mutation seam | architectural debt | high | high |
| A2 | Dead `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` guard constant | worthwhile refinement | low | high |
| A3 | Narrator render-instruction formatter ownership remains in `prompt_builders` despite manifest-first assembly | worthwhile refinement | low–moderate | high |
| A4 | Multi-contract forensic reconstruction and tooling burden | architectural debt | moderate | moderate |
| A5 | Phase-local retry/reasoning policy fragmentation (drift risk) | worthwhile refinement | moderate | moderate |

**Total material findings:** 5 — `architectural debt`: 2 (A1, A4); `worthwhile refinement`: 3 (A2, A3, A5); `actual defect`: 0

---

## Material findings (detail)

### A1 — Post-commit Librarian S4 as bounded separately persisted Continuity mutation seam

| Field | Value |
|-------|-------|
| **Classification** | architectural debt |
| **Severity / architectural significance** | high — affects continuity authority model and audit reconstruction |
| **Confidence** | high |
| **Responsibility** | continuity state mutation (bounded post-commit derived state) |
| **Components** | `v2/domain_api/commit_move_transaction.py` (`process_turn`); `v2/domain_api/librarian_proposal_service.py` (`finalize_proposals`); `v2/domain/modules/continuity_librarian_issue_pressure.py` (`apply_accepted_librarian_proposals`); `v2/domain/modules/continuity_librarian_knowledge_significance.py` (`apply_knowledge_revelation_significance`) |
| **Execution/data-flow** | **Normal turn commitment** remains owned by `ContinuityManager.process_turn`: DSH → Host `commit_move` → `execute_commit_move` → `process_turn` (sole normal turn-commit path; production caller grep confirms only `commit_move_transaction.py:237`). **Separately**, post-commit S4: DSH orchestrator joins Librarian proposal batch → Host `finalize_proposals` → `apply_accepted_librarian_proposals` mutates manager-owned **derived** continuity state for accepted `knowledge_revelation_significance` and issue-pressure overlays **outside** the normal `process_turn` transaction, with results persisted via `SessionRepository.persist` in `librarian_proposal_audit_log`. |
| **Authority scope (critical)** | This is **not** a second unrestricted/full Continuity turn-commit authority. S4 does **not** create a normal committed turn, does **not** increment the normal turn counter, does **not** independently reopen broad `known_by` authority, and does **not** constitute unrestricted competing narrative-truth authority. It **is** a real production mutation with durable persistence outside the normal `process_turn` transaction, bounded to specific derived overlays. |
| **Overlap evidence** | Two durable mutation entry points on `ContinuityManager` for committed narrative state within one round lifecycle. S4b explicitly does **not** mutate `known_by` (module header in `continuity_librarian_knowledge_significance.py`). |
| **Architectural authority** | `governance/sources/architecture-overview.md` — `process_turn` sole turn-commit authority; Librarian S4 documented as post-commit bounded apply (#39, #34). `docs/architecture.md` — bounded commit transaction; Librarian audit log persisted in session. |
| **Legitimate reason** | Post-commit semantic interpretation must not block turn commit; proposal evaluate→apply→audit chain is anchor-bound; revelation significance is annotation overlay, not full turn replay. |
| **Counterargument assessment** | **Partially stronger than redundancy case** — separation is intentional for latency and commit atomicity. **Debt remains** because the second persistence/mutation seam complicates the otherwise strong single-authority model; operators auditing continuity must know two mutation seams exist and which forensic surfaces record each (`librarian_proposal_audit_log` vs `process_turn` audit origin). |
| **External verification** | Greptile (PR #99 thread [r3910104177](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910104177)) — **supported with authority-scope qualification**: bounded second manager-state mutation seam, not second full turn-commit authority. |
| **Likely authoritative owner** | Turn commits: `ContinuityManager.process_turn`. Post-commit proposals: `librarian_proposal_service` + `continuity_librarian_*` apply modules. |
| **Candidate consolidation surface** | Document-only in short term; any future consolidation must preserve post-commit join semantics and at-most-once apply — not a simple merge into `process_turn`. |
| **Efficiency impact** | Moderate maintenance — new proposal kinds must route through evaluate→apply→audit; risk of ad-hoc manager mutation if pattern is copied. |
| **Stability/auditability impact** | High — forensic reconstruction must correlate `domain_commit_id`, librarian batch IDs, and session `librarian_proposal_audit_log`. |
| **Scalability/maintenance impact** | Moderate — bounded today; expands with additional S4 proposal classes. |
| **Recommended disposition** | `investigate further` / `retain as intentional` with explicit operator documentation; candidate successor Issue: "S4 continuity mutation seam audit playbook" (recommendation only). |
| **Evidence** | `grep process_turn(` — production path only `commit_move_transaction.py`; `librarian_proposal_service.py:243` calls `apply_accepted_librarian_proposals`; `continuity_manager.py` docstring: "sole orchestrator for `process_turn`". |

---

### A2 — Dead `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` guard constant

| Field | Value |
|-------|-------|
| **Classification** | worthwhile refinement |
| **Severity / architectural significance** | low |
| **Confidence** | high |
| **Responsibility** | context packaging / legacy source-kind enforcement |
| **Components** | `v2/domain_api/character_upstream_context.py` lines 20–27 |
| **Execution/data-flow** | Constant defined; **zero references** in static repository tracing (grep sole hit is definition). `assemble_character_upstream_contributions` does not consult it; active completeness uses `has_continuity_summary`, `has_transcript`, `has_trigger`, `has_private`, and `memory_lane_count`. |
| **Static-reachability qualification** | No live V2 production reader was found in static implementation tracing. This is **not** mathematical proof that dynamic/generated access is impossible. |
| **Overlap evidence** | Appears intended as migration guard against legacy knowledge source kinds leaking into Character manifests; never wired. |
| **Architectural authority** | `architecture-overview.md` — Packaging assembles per-consumer runtime context; Retrieval/Librarian own candidate access. |
| **Legitimate reason** | Placeholder for future completeness enforcement during Character adapter retirement. |
| **Counterargument assessment** | Weak — dead code adds false signal of active enforcement. |
| **Likely authoritative owner** | `character_upstream_context.py` / Packaging completeness checks. |
| **Candidate consolidation surface** | Wire into `completeness` dict in `CharacterUpstreamContext` or remove constant. |
| **Efficiency impact** | Low — no runtime cost; confuses auditors. |
| **Stability/auditability impact** | Low — none today. |
| **Scalability/maintenance impact** | Low. |
| **Recommended disposition** | `create Issue` (small cleanup) after Governance review — recommendation only. |
| **Evidence** | `grep LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` — single file, definition only. |
| **External verification** | Greptile (PR #99 thread [r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) — **supported** as dead residue / low-severity cleanup, subject to static-reachability qualification. |

---

### A3 — Narrator render-instruction formatter ownership remains in `prompt_builders` despite manifest-first assembly

| Field | Value |
|-------|-------|
| **Classification** | worthwhile refinement |
| **Severity / architectural significance** | low–moderate — organizational indirection, not duplicate context authority |
| **Confidence** | high |
| **Responsibility** | context packaging / render-instruction formatting |
| **Components** | `v2/domain_api/narrator_context.py` (`prepare_narrator_context`); `v2/domain/modules/prompt_builders.py` (`build_narrator_render_prompt`); `narrative_visibility_prompt.py` (visibility output instruction consumed by formatter) |
| **Execution/data-flow** | `prepare_narrator_context` is manifest-first: it calls `project_authoritative_context`, assembles multiple `PromptContribution` lanes (environmental baseline, committed move, director decision, storyteller lanes, etc.), and **always** incorporates `build_narrator_render_prompt` output as an `inference_instruction` contribution (`source_kind="inference_instruction"`, `priority=30`) before returning `PromptContributionManifest` (`narrator_context.py:107–116`, `194–202`, `256–266`). Narrator **does participate** in the manifest-first context architecture; the formatter is a delegated string builder inside that path. |
| **Overlap evidence** | **Not** duplicate assembly authority. The remaining concern is **formatter module ownership**: `prompt_builders.py` hosts `build_narrator_render_prompt` (and other legacy formatters such as `build_character_turn_prompt`, `build_director_selection_prompt` with **no** active `v2/` production callers at audit anchor) while `narrator_context.py` owns manifest composition. This is residual shared-module indirection, not a parallel context pipeline. |
| **Architectural authority** | `architecture-overview.md` — Packaging = Host `kernel.prepare_*`; `docs/architecture.md` line 180 — `prompt_builders` formats prompt text without re-reading memory or owning round sequencing. |
| **Legitimate reason** | `build_narrator_render_prompt` encodes live contracts: v2 `beats[]` verbatim-dialogue rules, environmental baseline/obligation blocks (#49/#89), `NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION`, and legacy dialogue-path fallback. Centralizing these rules in a tested formatter provides a stable formatting boundary. |
| **Counterargument assessment** | **GF-1 accepted (Governance):** initial audit incorrectly claimed manifest migration was still required. Formatter ownership may remain appropriate; moving it is organizational cleanup only unless contracts change. **Not** independently executing duplicate authority. |
| **Likely authoritative owner** | Manifest composition: `narrator_context.py`. Render-instruction formatting: `prompt_builders.build_narrator_render_prompt` (delegated helper). |
| **Candidate consolidation/review surface** | **Investigation only (not pre-authorized):** (a) retain formatter in `prompt_builders`; (b) colocate formatter nearer `narrator_context.py`; (c) otherwise simplify indirection. Any future change must preserve: v2 beat-order and verbatim-dialogue rules; environmental baseline/obligation integration; narrator visibility output instruction; manifest `inference_instruction` contribution shape and provenance; dialogue/visibility contracts enforced by `redact_structured_move_for_orchestration` upstream. |
| **Efficiency impact** | Low — minor navigation cost when evolving narrator render rules across module boundary. |
| **Stability/auditability impact** | Low — render instruction is captured in manifest contribution content; fingerprinting includes this lane. |
| **Scalability/maintenance impact** | Low–moderate — `prompt_builders.py` also contains unused-at-anchor legacy formatters that may confuse auditors. |
| **Recommended disposition** | `investigate further` / `no action` — optional ownership cleanup after Governance review; not urgent. |
| **Evidence** | `narrator_context.py:107–116, 194–202, 256–266`; `grep build_narrator_render_prompt` — production caller `narrator_context.py` only (+ tests); `grep prompt_builders` in `v2/` — sole production import is narrator_context. |
| **External review** | Greptile GF-1 (P2, PR #99 [r3909996072](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3909996072)) — **accepted by Governance**; corrected manifest-migration mischaracterization. Greptile follow-up ([r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) — **supported** corrected framing: formatter is live, not removable without behavior change; concern is organizational ownership/navigation only. |

---

### A4 — Multi-contract forensic reconstruction and tooling burden

| Field | Value |
|-------|-------|
| **Classification** | architectural debt |
| **Severity / architectural significance** | moderate — operational/tooling burden, not evidence-store redundancy |
| **Confidence** | moderate |
| **Responsibility** | forensic reconstruction / correlation across durable contracts |
| **Defensible finding** | Complete forensic reconstruction spans several independently justified **durable contracts** without a unified durable turn-level view, creating correlation and tooling cost despite shared identifiers and existing investigation tooling. This is **not** equivalent to “six independent durable writes required for every character turn.” |
| **Evidence taxonomy** | Surfaces differ by contract class: **canonical** (session JSON — `continuity_state`, `rp_history`, commit metadata); **forensic** (execution-evidence attempt files/indexes); **mediated** (session `librarian_proposal_audit_log` — Host mediation and bounded S4 apply results); **derived** (story knowledge searchable projection; memory/context projections); **conditional** (Plot Cognition overlay/chronicle; human audit tags); **transient/ephemeral** (DSH `HgTraceEmitter` `hg/*` events; `role_inference_summary` consumer projection); **legacy** (V1 `data/rp_audits/session_*` — historical/off-path for V2 save/resume); **rebuildable** (execution-evidence, semantic, Plot Cognition, and audit-tag indexes/manifests — navigation/recovery metadata, not independent semantic records). |
| **Components** | `v2/rp_runtime/src/lib/execution-evidence/`; `hg-trace-emitter/service.mjs`; `v2/domain_api/session_history.py`; session `librarian_proposal_audit_log`; `plot_cognition_forensics_repository`; `audit-tags/service.mjs`; `continuity_audit_origin` / occurrence evidence (#51); `tools/investigation/*` |
| **Execution/data-flow** | A normal round/turn forensic reconstruction generally joins durable session JSON, execution-evidence files/indexes, and often persisted Librarian audit; conditional/derived surfaces apply when relevant. Correlation mitigated by shared IDs (`domain_commit_id`, `hg_round_id`, `continuity_turn_index`, `entry_id`, `event_id`, `evidence_id`, `inference_id`, evaluator IDs, Plot Cognition identifiers) per `docs/forensic-auditability-standard.md` intent and investigation tooling (e.g. `tools/investigation/list_execution_evidence.py`). |
| **Overlap evidence** | Similar *events* or IDs/text may appear across trace, execution evidence, and `rp_history`; this is often deliberate denormalization across authority boundaries, retention policies, and query lifecycles — not duplicate forensic *authority*. |
| **Architectural authority** | `docs/forensic-auditability-standard.md`, `docs/rp-data-layout.md`, `docs/audit-workflows.md`. |
| **Legitimate reason** | Distinct consumers (resume, investigator CLI, human audit, runtime tooling) require distinct retention, provenance, and query contracts. |
| **Counterargument assessment** | **Strong for retention** — stores are not redundant authorities. **Debt** is multi-contract join burden and absence of a unified durable turn-level view; shared IDs and investigation tooling **mitigate** but do not eliminate operator/investigator correlation work. Human-auditor burden varies by reconstruction depth and is **not uniformly high** for all tasks. |
| **Likely authoritative owner** | Per-surface owners; no single forensic aggregator at `main`. |
| **Candidate consolidation surface** | Investigation tooling / correlation navigation (not merge legitimate stores). |
| **Efficiency impact** | Moderate for deep forensic reconstruction; low for runtime. |
| **Stability/auditability impact** | Moderate risk if correlation IDs drift between surfaces. |
| **Scalability/maintenance impact** | Moderate — each new phase or forensic surface adds correlation surface area. |
| **Recommended disposition** | `monitor` / `investigate further` for improved forensic correlation/navigation tooling — recommendation only. |
| **Evidence** | `MODULE_INDEX.md` forensic routing; `execution-evidence/recorder.mjs` observational comment; `docs/rp-data-layout.md` artifact classes table. |
| **External verification** | Greptile (PR #99 thread [r3910199780](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910199780)) — **supported with reconstruction/taxonomy/severity qualification**: real multi-contract burden; original per-turn durable store cardinality framing too broad. |

---

### A5 — Phase-local retry/candidate policy fragmentation (drift risk)

| Field | Value |
|-------|-------|
| **Classification** | worthwhile refinement |
| **Severity / architectural significance** | moderate |
| **Confidence** | moderate |
| **Responsibility** | phase-local retry/correction budgets and candidate ceilings |
| **Already centralized (not A5 scope)** | Core inference/reasoning infrastructure is substantially centralized: `application-settings.mjs` (role reasoning defaults, token ceilings, `liveMaxAttempts`, role profiles); `inference-profile.mjs` (provider/model/reasoning/temperature/token resolution per role); `reasoning-provider-options.mjs` (reasoning level mapping); `inference-substrate.mjs` (ephemeral DSH agent creation, provider invocation, execution evidence); `semantic-qa-substrate.mjs` and `contract-correction-substrate.mjs` (semantic evaluation and bounded structural correction). **A5 does not claim** provider invocation, reasoning mapping, or all inference settings are independently duplicated. |
| **Independently maintained (A5 scope)** | Phase-local policy that can drift: infrastructure retry counts (`EVAL_INFRA_RETRIES`, `CHAR_INFRA_RETRIES` across `narrator-phase.mjs`, `character-phase.mjs`, `director-phase.mjs`); candidate ceilings (`character-candidate-budget.mjs`, `director-candidate-budget.mjs` — both use ceiling `3` in separate modules); semantic correction/regeneration budgets and terminal disposition per phase; opening/segmentation/decomposition attempt caps (`opening-phase.mjs`, `opening-segmentation-phase.mjs`, `player-decomposition-phase.mjs`); `liveMaxAttempts` vs Narrator fixed `MAX_NARRATOR_ATTEMPTS` and public opening/segmentation controls in `hg-application-client.mjs`. |
| **Execution/data-flow** | Each phase executor implements role-specific retry/regen semantics locally. Shared substrates centralize inference invocation but **not** governing retry/candidate policy loops; `inferenceAttemptLimit(...)` exists but live phase loops do not consistently use it as governing policy. |
| **Overlap evidence** | Repeated policy dimensions (e.g. `EVAL_INFRA_RETRIES = 1`, candidate ceiling `3`) independently defined in multiple phase files/modules. |
| **Architectural authority** | `docs/architecture.md` — DSH owns semantic QA judgment; no central phase retry-policy registry documented. |
| **Legitimate reason** | Phase-specific failure modes (Character move validity vs Director selection/regeneration vs Narrator presentation fidelity vs auxiliary opening/decomposition contracts) warrant different semantic retry behavior. A single generic retry loop would risk erasing trust/authority distinctions. |
| **Counterargument assessment** | Semantic differences justify separation; **structural drift risk** remains for repeated numeric policy dimensions maintained in multiple executing locations. **No observed production policy divergence** was independently evidenced at audit anchor — risk is maintenance/structural, not proven runtime mismatch. |
| **Likely authoritative owner** | DSH phase executors collectively; partial centralization in `application-settings.mjs` for shared defaults only. |
| **Candidate consolidation surface** | Shared retry/candidate policy primitives with phase-specific profiles (preserve intentional role semantics; do not collapse into one global loop). |
| **Efficiency impact** | Low today; higher when tuning retry/candidate behavior globally. |
| **Stability/auditability impact** | Moderate — inconsistent retry caps could confuse forensic replay if drift occurs. |
| **Scalability/maintenance impact** | Moderate. |
| **Recommended disposition** | `investigate further` — evaluate shared policy primitives for repeated dimensions — recommendation only. |
| **Evidence** | `narrator-phase.mjs`, `character-phase.mjs`, `director-phase.mjs`, budget modules, `application-settings.mjs`, `inference-substrate.mjs`. |
| **External verification** | Greptile (PR #99 thread [r3910282152](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910282152)) — **supported narrowly**: worthwhile configuration/policy centralization refinement with real drift risk; not material duplicated execution policy or authority. |

---

## Investigated Apparent Duplications That Are Intentional / Justified

### J1 — Turn selection: eligibility vs participation policy vs Director inference

| Field | Detail |
|-------|--------|
| **Responsibility** | turn selection / participation eligibility |
| **Apparent overlap** | `kernel._eligibility_projection`, `participation_policy.evaluate_participation_policy`, Director `validate_director_decision`, DSH `getEligibleActors` / `getParticipationDecision` |
| **Why redundant-looking** | Multiple API calls per round for "who acts next" |
| **Traced relationship** | Orchestrator: eligibility snapshot → participation decision → **either** direct selection (`selection_mode === 'direct'`) **or** Director phase. `response_validation_selection.py` is shared library, not second authority. |
| **Distinct boundary** | Eligibility = hard constraints; participation policy = C2/forced/continuation bypass; Director = deliberative choice among eligible actors |
| **Counterevidence** | `MODULE_INDEX.md` — selection-path validation vs move validation layers; `architecture-overview.md` — Director owns turn selection |
| **Conclusion** | Justified layered pipeline |
| **Disposition** | `retain as intentional` |

### J2 — Privacy: audibility vs known_by vs retrieval hard access

| Field | Detail |
|-------|--------|
| **Responsibility** | knowledge authorization / privacy |
| **Apparent overlap** | `perception_audibility`, `PublicEvent.known_by`, `character_may_know_candidate`, Librarian mediation, Packaging/PVR |
| **Why redundant-looking** | Multiple "can character X know Y?" checks |
| **Traced relationship** | Audibility/perception filters **verbatim dialogue** in structured moves; durable `known_by` gates **event knowledge** at continuity; retrieval gates **candidate provenance** before Librarian mediation; Librarian mediation selects among already-eligible catalog material; Packaging/PVR enforce consumer-boundary and recipient-specific projection |
| **Distinct boundary** | Different objects, representations, and trust boundaries (dialogue vs event vs candidate vs mediated bundle vs transcript view) |
| **Consistency surface** | Shared audibility primitives and repeated defensive checks at boundaries create a maintenance/consistency surface, but do **not** constitute materially duplicated privacy **authority** |
| **Counterevidence** | `perception_audibility.py` module contract; `architecture-overview.md` #33 decomposition |
| **Conclusion** | Justified intentional separation — not redundant enforcement of one rule |
| **Disposition** | `retain as intentional` |
| **External verification** | Greptile (PR #99 [r3910150099](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910150099)) — **supported with boundary/primitive-overlap qualification**. |

### J3 — Deterministic validation vs semantic QA

| Field | Detail |
|-------|--------|
| **Responsibility** | validation / semantic QA |
| **Apparent overlap** | `validate_move`, `validate_bot_response_for_runtime`, character semantic evaluation, director/narrator semantic QA |
| **Traced relationship** | Ingress → parse → runtime rules → Host validate (deterministic) → DSH semantic eval (LLM judgment for deferred rules per `response_validation_content.py` header) |
| **Distinct boundary** | Deterministic validators enforce machine-checkable contracts (shape, recipients, transitions, PVR correspondence, verbatim speech order); semantic QA evaluates meaning, contradiction, attribution, framing, agency, and related interpretive properties |
| **Structural rechecks** | Some structural invariants are deliberately rechecked after normalization or at representation boundaries (e.g. PVR derivation then PVR validation; semantic envelope parsing). These are boundary checks, not materially duplicated semantic authority |
| **Counterevidence** | `response_validation_content.py` documents R02b/R11–R15 deferral to semantic evaluation; Narrator semantic QA explicitly avoids duplicating deterministic F1/F2 verbatim/order checks |
| **Conclusion** | Justified staged separation, not duplicate contract |
| **Disposition** | `retain as intentional` |
| **External verification** | Greptile (PR #99 [r3910150099](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910150099)) — **supported with structural-recheck qualification**. |

### J4 — Scene Grounding vs Continuity truth

| Field | Detail |
|-------|--------|
| **Responsibility** | scene grounding |
| **Apparent overlap** | `scene_grounding.rebuild_scene_grounding_from_continuity` vs `ContinuityManager` state |
| **Traced relationship** | Scene Grounding rebuilt from continuity each `prepare_*` call — read-only projection |
| **Distinct boundary** | Authority vs prompt projection (`docs/scene-grounding-layer.md`) |
| **Conclusion** | Correct authority/projection split |
| **Disposition** | `retain as intentional` |

### J5 — Execution evidence vs trace vs rp_history

| Field | Detail |
|-------|--------|
| **Responsibility** | forensic evidence |
| **Apparent overlap** | Multiple evidence surfaces per round |
| **Traced relationship** | Session JSON = **canonical** resumable state/history; execution evidence = **forensic** per-inference payloads; Librarian audit = **mediated** post-commit forensic record; story knowledge = **derived** searchable projection; Plot Cognition overlay/chronicle = **conditional** operational/append-only records; audit tags = **conditional** human anchors; DSH trace / `role_inference_summary` = **transient/ephemeral**; V1 `rp_audits` = **legacy/off-path**; indexes/manifests = **rebuildable** navigation metadata |
| **Distinct boundary** | Retention scope, durability, provenance, and query consumers differ; repeated IDs/text are often deliberate denormalization for provenance, auditability, and consumer isolation — not redundant forensic authority |
| **Low-unique-value categories** | Rebuildable indexes have navigation/performance value, not independent semantic authority; legacy V1 audit artifacts are historical/off-path for current V2 reconstruction; transient traces/summaries are not additional durable forensic authorities |
| **Conclusion** | Justified multi-contract architecture; operational cost is reconstruction/tooling burden (A4), not store redundancy |
| **Disposition** | `retain as intentional` |
| **External verification** | Greptile (PR #99 [r3910199780](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910199780)) — **supported with evidence-taxonomy qualification**. |

### J6 — DSH custom orchestration over Cordis

| Field | Detail |
|-------|--------|
| **Responsibility** | runtime orchestration |
| **Apparent overlap** | Cordis `Service` lifecycle vs `HgRoundOrchestrator` |
| **Traced relationship** | Cordis/DSH provide plugin mounting, `agentLoop.create`, system-prompt context, provider adapter, session events, and fiber lifecycle; HG custom layers implement domain round state machine, phase executors, Host HTTP client, participation/Director/Librarian S4 joins, and evidence instrumentation |
| **Distinct boundary** | Framework lifecycle/provider primitives vs Holy Grail domain semantics and necessary integration boundaries (Node → HTTP → Python Host) |
| **Scope qualification** | No **material duplication of DSH/Cordis responsibilities visible in the inspected production integration** was found; custom layers predominantly implement Holy-Grail-specific semantics or required boundaries. This is **not** an exhaustive claim about every capability in upstream `@deepseek-ai/cordis` packages (see Explicit gaps). |
| **Conclusion** | Required custom domain layer — not framework reinvention in inspected paths |
| **Disposition** | `retain as intentional` |
| **External verification** | Greptile (PR #99 [r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) — **supported within inspected integration scope**. |

### J7 — Shared `continuity_context_projector` across role prepare paths

| Field | Detail |
|-------|--------|
| **Responsibility** | context packaging |
| **Apparent overlap** | Director, Character, Narrator each have `prepare_*` modules |
| **Traced relationship** | All call `project_authoritative_context` once; role modules add digests/advisory lanes only |
| **Conclusion** | Correct modular decomposition, not redundant mediation |
| **Disposition** | `retain as intentional` |

### J8 — `character_move_ingress` vs `response_validation_parsing`

| Field | Detail |
|-------|-------|
| **Responsibility** | validation ingress |
| **Apparent overlap** | Two parse paths for character moves |
| **Traced relationship** | Ingress = strict transport boundary (v2-only, issue240 fields); parsing module = shared parse façade used by `validate_move` |
| **Conclusion** | Layered boundary, not parallel authority |
| **Disposition** | `retain as intentional` |

### J9 — `perceptual_visibility_legacy` read adapter

| Field | Detail |
|-------|--------|
| **Responsibility** | perception / history projection |
| **Apparent overlap** | Legacy metadata normalization alongside PVR |
| **Traced relationship** | Read-time adapter for old session metadata; callers: `session_history.py`, `character_conversation_projection.py` |
| **Conclusion** | Active compatibility requirement |
| **Disposition** | `retain as intentional` until legacy sessions age out |

---

## Responsibility-cardinality appendix

| Responsibility | Documented owner | Actual executors/enforcers | Independent mechanism count | Writers | Read-only projections | Durable evidence | Cardinality concern? | Reference |
|----------------|------------------|---------------------------|----------------------------|---------|----------------------|------------------|---------------------|-----------|
| Turn selection | Director + participation policy | `participation_policy.py`, `kernel._eligibility_projection`, Director phase, `detect-forced-speaker.mjs`, app bootstrap first actor | 5 | participation output, Director decision (pre-commit) | eligibility snapshots, traces | execution evidence, trace | Investigated — justified (J1) | J1 |
| Participation eligibility | Host kernel | `response_validation_selection.py`, `kernel._eligibility_projection` | 1 (+ shared lib) | none (projection) | EligibleActorsResponse | trace | No | J1 |
| Continuity truth | `ContinuityManager.process_turn` | `commit_move_transaction` → `process_turn`; S4 `apply_accepted_librarian_proposals` | 2 | `process_turn`, S4 apply | Scene Grounding, context projector | session JSON, occurrence evidence | **Yes** — bounded second seam | A1 |
| State mutation (turn) | `process_turn` | mutation pipeline modules | 1 primary | `process_turn` | — | continuity in session | No (primary) | A1 counterevidence |
| Knowledge authorization (`known_by`) | Continuity | `continuity_knowledge_helpers`, event surface | 1 writer | event creation / share | retrieval gates, Librarian | story knowledge JSONL | No | J2 |
| Dialogue privacy | perception_audibility | `filter_structured_move_for_viewer`, PVR | 2 layers | none | history projections | PVR metadata in rp_history | Investigated — different objects | J2 |
| Retrieval eligibility | Retrieval #31 | `retrieval_service.py`, `character_epistemic.py` | 1 | scope/story append (post-commit promotion) | candidates | story knowledge | No | J2 |
| Semantic mediation | Librarian #34 | `librarian_service.py`, packaging mapper | 1 | proposal apply (S4) | bundles | librarian audit log | S4 write seam | A1 |
| Context packaging | Host `prepare_*` | role context modules, projector | 4 pipelines / 1 projector | none | manifests | manifest fingerprints in traces | No | J7 |
| Scene grounding | Continuity (source) | `scene_grounding.py` rebuild | 1 | none (rebuild) | prompt lanes | — | No | J4 |
| Character context | `character_context.py` | upstream + Librarian mapper | 1 path | none | manifest | — | No | J7 |
| Narrator context | `narrator_context.py` | projector + delegated `prompt_builders` formatter | 1 manifest path | none | manifest (incl. `inference_instruction`) | — | Formatter ownership only (A3) | A3 |
| Director context | `director_context.py` | projector + digests | 1 | none | manifest | — | No | J7 |
| Story progression advice | progression advisory | `progression_advisory` modules | 1 | advisory only | prompts | — | No | architecture-overview |
| Validation (deterministic) | Host validators | `response_validation_*`, `kernel.validate_*` | 3 stages | none | annotations | — | No | J3 |
| Semantic QA | DSH phases | semantic eval substrates, QA contexts | 3 role-specific | none | QA traces | execution evidence | No | J3 |
| Retry/correction | DSH phases | phase executors, retry helpers | 3+ independent | none | retry metadata | execution evidence | Drift risk | A5 |
| Persistence (session) | SessionRepository | `session_manager.py` | 1 gate | `persist` | — | `data/sessions/` | No | — |
| Derived knowledge | story/scope repos | `knowledge_write_policy`, story pipeline | 2 | append-only | retrieval | JSONL | No | — |
| Evidence recording | multiple contracts | execution-evidence, trace, rp_history, audit tags, librarian audit, conditional Plot Cognition | multi-contract (taxonomy-dependent) | observational | — | canonical + forensic + mediated + conditional + transient + rebuildable | Reconstruction/tooling cost (A4) | A4, J5 |
| Forensic reconstruction | investigation tools | `tools/investigation/*` | N projections | none | reports | — | Tooling gap (no unified durable turn view) | A4 |
| Session/round identity | Host + DSH | `session_state.py`, round orchestrator | 2 (coordination) | round bookkeeping on commit | — | session + evidence | No | — |
| Provider invocation | DSH + Cordis | `assembled-request.mjs`, provider mount | 1 | none | profiles | execution evidence | No | — |
| Runtime defaults/config | split | `application-settings.mjs` (centralized) + phase-local retry/candidate policy | partial centralization | — | — | — | Phase-local drift risk (A5) | A5 |

---

## Whole-system assessment

### Strongest confirmed architectural inefficiencies

1. **A1** — Bounded separately persisted post-commit Continuity mutation seam increases audit cognitive load despite intentional design.
2. **A4** — Multi-contract forensic reconstruction/tooling burden without a unified durable turn-level view (mitigated partially by shared IDs and investigation tooling).

**Note:** A3 was reclassified per GF-1 and external verification — formatter ownership is a lower-significance worthwhile refinement, not a primary inefficiency.

### Highest-risk ownership/authority overlaps

- **Continuity mutation (A1)** — highest authority risk; currently bounded and audited, but expansion of S4 proposal classes without discipline would compound debt.
- **No confirmed duplicate continuity truth writers** beyond documented S4 seam at `main`.

### Legacy/superseded residue and minor external-review observations

| Item | Status |
|------|--------|
| v1 character move ingress | Removed (#143) |
| `perceptual_visibility_legacy` | Active read adapter (J9) |
| `character_move_adapters` | Active read projection |
| `prompt_builders` | Active formatter module — `build_narrator_render_prompt` called from `narrator_context.py`; output wrapped in manifest `inference_instruction` (A3). Other formatters in module have no `v2/` production callers at anchor (possible off-path/migration residue; caller evidence incomplete). |
| `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` | Dead code (A2) |
| `FixtureStore` | Test-only |
| `validate_bot_response_for_scenario` | Tests/offline only |
| `character-inference-slice.mjs` | Unconfirmed secondary execution surface — exported via `HgPhaseExecutors.runCharacterInference`; **no active application caller established** in external review (not promoted to material finding) |
| `SessionRepository.create_scene` | Transitional compatibility alias for prototype `/v1/scenes` |
| `project-history.mjs` | Non-authoritative Node-side presentation/transcript projection |
| V1 `data/rp_audits/session_*` | Legacy/historical — off-path for V2 save/resume reconstruction |
| Rebuildable evidence indexes/manifests | Navigation/recovery metadata, not independent semantic authorities |
| DSH trace / `role_inference_summary` | Transient/ephemeral — not additional durable forensic authorities |

### Areas found architecturally healthy

- **Domain Host / DSH boundary** — clean HTTP composition; Python does not call DSH.
- **Shared eligibility library** — single implementation, single authority.
- **Scene Grounding** — correct read-only projection from continuity.
- **Deterministic vs semantic validation** — documented deferral, not duplicate contracts.
- **Cordis vs HG orchestration** — justified custom domain layer.

### Privacy/knowledge-boundary health

**Healthy** with intentional multi-layer checks on different objects (J2). No evidence of redundant `known_by` writers from S4b.

### Validation/semantic-QA layering health

**Healthy** pipeline (J3). Depth is high but stage boundaries are documented.

### Persistence/mutation ownership health

**Mostly healthy** — single `SessionRepository.persist` gate per commit; **exception** S4 post-commit apply (A1).

### Context/mediation health

**Healthy** — shared projector (J7); Narrator is manifest-first with delegated formatter ownership in `prompt_builders` (A3, worthwhile refinement; GF-1 corrected initial mischaracterization).

### DSH/Cordis/native-utilization health

**Appropriate within inspected integration scope** — custom orchestration encodes domain rules and necessary boundaries; no material DSH/Cordis duplication found in production integration paths reviewed (J6). Exhaustive upstream framework comparison remains out of scope.

### Forensic/evidence architecture health

**Functionally sound**, **operationally moderate burden** for deep reconstruction (A4). Distinct evidence contracts are justified (J5); correlation IDs and investigation tooling mitigate join cost; unified durable turn-level view remains a tooling gap, not evidence-store redundancy.

### Configuration/contract centralization health

**Partial centralization** — core inference/reasoning infrastructure centralized; **phase-local retry/candidate policy drift risk** remains (A5). Packet contracts centralized in `PACKET_CONTRACTS.md`.

### Overall architectural efficiency

Widespread accidental duplication of architectural **responsibility** was **not** found. Most apparent overlaps resolve into intentional separation of authority, projection, validation stage, forensic contract, compatibility, or framework/domain responsibility. **True redundant authority is rare** at `main`; the strongest remaining inefficiencies are **bounded and specific** (A1 mutation seam, A4 reconstruction/tooling burden). **No actual defect** was established. External challenge found **no additional confirmed material architectural redundancy** beyond the discussed findings — this is **not** proof that no redundancy exists anywhere.

The system exhibits substantial intentional layering from incremental Issue-driven delivery (#31–#55, Librarian S4, forensic standard). Dominant costs are audit surface area (forensic correlation, S4 mutation seam), phase-local policy maintenance (A5), and residual module indirection (A3 formatter ownership, dead legacy constant A2).

### Aggregate accidental complexity

Incremental additions (validation depth, forensic surfaces, S4 post-commit join, plot cognition overlay) create a **whole greater than the sum of individually justified parts**. Maintenance burden is **measurable in operator/investigator time**, not runtime failure rate.

### Focused follow-up audits warranted?

- **S4 continuity mutation playbook** (narrow) — recommended after this report.
- **Retry/reasoning policy registry** (DSH config) — optional.
- **Not warranted:** broad re-audit of Retrieval/Librarian/Storyteller decomposition — found healthy.

### Candidate successor Issue packages (recommendations only — NOT authorized)

1. **Documentation:** Formalize A1 bounded mutation authority (S4 vs `process_turn` matrix) for operators/auditors.
2. **Tooling:** Improve forensic correlation/navigation across durable contracts — **not** merge legitimate evidence stores (A4).
3. **Cleanup:** Remove or wire `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` if prioritized (A2).
4. **Optional review:** Narrator render-instruction formatter ownership — colocate vs retain in `prompt_builders` only if navigation/maintenance value warrants it; **not** manifest migration (A3).
5. **Policy primitives:** Evaluate shared retry/candidate policy primitives for repeated dimensions while preserving intentional role-specific semantics (A5).
6. **Reachability check:** Investigate `character-inference-slice.mjs` callers only if secondary surface merits follow-up (minor external-review observation; not a material finding).

---

## External verification

Greptile was used as an **external implementation-aware reviewer** after the initial audit report, via conversational challenges in the PR #99 review thread rooted at [discussion_r3909996072](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3909996072). Greptile supplied independent challenge evidence; **Governance determined dispositions**. External review is evidence, not governance authority. Absence of an additional Greptile finding is **not** proof of absence.

### Disposition summary

| Topic | Greptile disposition | Governance action |
|-------|---------------------|-------------------|
| **A1** | Supported with authority-scope qualification | Narrow wording — bounded post-commit seam, not second full turn-commit authority ([r3910104177](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910104177)) |
| **A2** | Supported | Retain worthwhile refinement; add static-reachability qualification ([r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) |
| **A3 (corrected)** | Supported after GF-1 reclassification | Retain worthwhile refinement; GF-1 caused original correction ([r3909996072](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3909996072), [r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) |
| **A4** | Supported with reconstruction/taxonomy/severity qualification | Adopt evidence taxonomy; moderate cardinality/severity framing ([r3910199780](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910199780)) |
| **A5** | Supported narrowly | Clarify centralized vs phase-local policy; retain worthwhile refinement ([r3910282152](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910282152)) |
| **J2** | Supported with boundary-overlap qualification | Acknowledge consistency surface without duplicate authority ([r3910150099](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910150099)) |
| **J3** | Supported with structural-recheck qualification | Acknowledge representation-boundary rechecks ([r3910150099](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910150099)) |
| **J5** | Supported with evidence-taxonomy qualification | Adopt taxonomy in J5 ([r3910199780](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910199780)) |
| **J6** | Supported within inspected integration scope | Retain scoped wording; no exhaustive upstream claim ([r3910240568](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910240568)) |
| **Global missed-redundancy search** | No additional **confirmed material** architectural redundancy | Record qualified negative finding ([r3910282152](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99#discussion_r3910282152)) |

### Material changes from external verification

- **A3** materially changed: GF-1 reclassified from architectural debt to worthwhile refinement (formatter ownership, not parallel manifest assembly).
- **A1, A4, A5, J2, J3, J5, J6** sharpened with qualifications; classifications largely retained with refined wording.
- **No new material findings** promoted from global search; `character-inference-slice.mjs` noted as unconfirmed secondary surface only.

### Remediation performed

None — audit report documentation refinement only.

---

## Internal report validation

| Check | Result |
|-------|--------|
| Cited files exist at anchor | Pass — spot-checked paths at `ba54016` |
| Callers/execution paths supported | Pass — `process_turn` production caller verified; narrator manifest integration verified |
| A1 does not imply second unrestricted turn authority | Pass — bounded post-commit seam language applied |
| A3 accurately represents execution flow | Pass — manifest-first; formatter delegated; worthwhile refinement (GF-1 + external verification) |
| A4 uses reconstruction-contract framing | Pass — evidence taxonomy; no mandatory “6+ durable writes per turn” claim |
| A5 distinguishes centralized inference from phase-local policy | Pass |
| Writers actually write | Pass — S4 apply and `process_turn` traced |
| Authority matches docs | Pass — matches architecture-overview with A1 documented exception |
| Counterarguments evaluated | Pass — 9 justified separations documented |
| External verification incorporated | Pass — §External verification; dispositions recorded |
| Consolidation labeled candidate | Pass — no pre-authorized fixes |
| Classifications/counts consistent | Pass — 2 architectural debt (A1, A4); 3 worthwhile refinement (A2, A3, A5); 0 actual defect |
| Recommendations non-authorizing | Pass |
| Greptile described as external evidence only | Pass |

**Consolidated refinement revalidation:** PASS (2026-09-02).

**Factual uncertainties:** Live scenario replay not executed at audit anchor. Greptile global negative finding is qualified (“no additional **confirmed material** redundancy”).

---

## No-remediation attestation

This audit cycle performed **investigation and documentation only**. No production code, tests, configuration, or dependencies were modified. Consolidated refinement modified **audit report documentation only**. No remediation Issues were created. No architectural remediation is bundled in audit PR commits. Remediation requires separate Governance authorization and tracked Issues reaching `consensus_reached`.

---

## Related authority

- `governance/sources/audit-semantics.md`
- `governance/sources/architecture-overview.md`
- `MODULE_INDEX.md`
- `docs/forensic-auditability-standard.md`
- `docs/audit-workflows.md`
