# Repository-Wide Architectural Efficiency & Redundancy Audit

**Audit parent Issue:** [#98 — Repository-wide architectural efficiency and redundancy audit](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/98)  
**Audit dates:** 2026-09-01 (investigation and report at repository anchor)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full (`docs/issue-bootstrap-profiles.md`)  
**Remediation authorization this cycle:** NONE  
**Report commit:** `10289f8d8eb0959005b2f6332dc4f8e5e315aeeb` (initial); refined per GF-1 — see audit PR #99 head  
**External review:** PR [#99](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99); Greptile GF-1 accepted by Governance (see §External review disposition)

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
- **Greptile PR review** — GF-1 incorporated (Governance-accepted correction to A3); see §External review disposition. Other audit conclusions unchanged by external review.
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
| A4 | Multi-channel forensic reconstruction cost | architectural debt | moderate | moderate |
| A5 | Phase-local retry/reasoning policy fragmentation (drift risk) | worthwhile refinement | moderate | moderate |

**Total material findings:** 5 — `architectural debt`: 2 (A1, A4); `worthwhile refinement`: 3 (A2, A3, A5); `actual defect`: 0

---

## Material findings (detail)

### A1 — Post-commit Librarian S4 as bounded second continuity mutation seam

| Field | Value |
|-------|-------|
| **Classification** | architectural debt |
| **Severity / architectural significance** | high — affects continuity authority model and audit reconstruction |
| **Confidence** | high |
| **Responsibility** | continuity state mutation |
| **Components** | `v2/domain_api/commit_move_transaction.py` (`process_turn`); `v2/domain_api/librarian_proposal_service.py` (`finalize_proposals`); `v2/domain/modules/continuity_librarian_issue_pressure.py` (`apply_accepted_librarian_proposals`); `v2/domain/modules/continuity_librarian_knowledge_significance.py` (`apply_knowledge_revelation_significance`) |
| **Execution/data-flow** | Production turn commit: DSH → Host `commit_move` → `execute_commit_move` → `ContinuityManager.process_turn` (sole turn-commit path; production caller grep confirms only `commit_move_transaction.py:237`). **Separately**, post-commit S4: DSH orchestrator joins Librarian proposal batch → Host `finalize_proposals` → `apply_accepted_librarian_proposals` mutates manager state for accepted `knowledge_revelation_significance` and issue-pressure overlays **outside** `process_turn`. |
| **Overlap evidence** | Two durable mutation entry points on `ContinuityManager` for committed narrative state within one round lifecycle. S4b explicitly does **not** mutate `known_by` (module header in `continuity_librarian_knowledge_significance.py`). |
| **Architectural authority** | `governance/sources/architecture-overview.md` — `process_turn` sole turn-commit authority; Librarian S4 documented as post-commit bounded apply (#39, #34). `docs/architecture.md` — bounded commit transaction; Librarian audit log persisted in session. |
| **Legitimate reason** | Post-commit semantic interpretation must not block turn commit; proposal evaluate→apply→audit chain is anchor-bound; revelation significance is annotation overlay, not full turn replay. |
| **Counterargument assessment** | **Partially stronger than redundancy case** — separation is intentional for latency and commit atomicity. **Debt remains** because operators auditing continuity must know two mutation seams exist and which forensic surfaces record each (`librarian_proposal_audit_log` vs `process_turn` audit origin). |
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
| **Execution/data-flow** | Constant defined; **zero references** in repository (grep sole hit is definition). `assemble_character_upstream_contributions` does not consult it. |
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
| **External review** | Greptile GF-1 (P2, PR #99 @ `10289f8...`) — **accepted by Governance**; corrected manifest-migration mischaracterization. |

---

### A4 — Multi-channel forensic reconstruction cost

| Field | Value |
|-------|-------|
| **Classification** | architectural debt |
| **Severity / architectural significance** | moderate |
| **Confidence** | moderate |
| **Responsibility** | evidence recording / forensic reconstruction |
| **Components** | `v2/rp_runtime/src/lib/execution-evidence/`; `hg-trace-emitter/service.mjs`; `v2/domain_api/session_history.py`; session `librarian_proposal_audit_log`; `plot_cognition_forensics_repository`; `audit-tags/service.mjs`; `continuity_audit_origin` / occurrence evidence (#51) |
| **Execution/data-flow** | Per character turn, observational writes may occur across 6+ stores. Correlation mitigated by shared IDs (`domain_commit_id`, `evidence_id`, `inference_id`, `rp_history_entry_id`) per `docs/forensic-auditability-standard.md` intent. |
| **Overlap evidence** | Similar *events* appear in trace + execution evidence + rp_history; not duplicate *authority* — different retention/query purposes. |
| **Architectural authority** | `docs/forensic-auditability-standard.md`, `docs/rp-data-layout.md`, `docs/audit-workflows.md`. |
| **Legitimate reason** | Restart-durable session history vs ephemeral inference evidence vs human audit tags serve distinct consumers (operator UI, investigator CLI, Greptile/audit). |
| **Counterargument assessment** | **Strong for retention** — not redundant records. **Debt** is aggregate operator burden reconstructing one turn without a single indexed view (investigation tools partially compensate: `tools/investigation/list_execution_evidence.py`). |
| **Likely authoritative owner** | Per-surface owners; no single forensic aggregator at `main`. |
| **Candidate consolidation surface** | Investigation tooling / correlation index (not merge stores). |
| **Efficiency impact** | High for human auditors; low for runtime. |
| **Stability/auditability impact** | Moderate risk if correlation IDs drift between surfaces. |
| **Scalability/maintenance impact** | Moderate — each new phase adds trace types. |
| **Recommended disposition** | `monitor` / `investigate further` for unified turn-reconstruction CLI — recommendation only. |
| **Evidence** | `MODULE_INDEX.md` forensic routing; `execution-evidence/recorder.mjs` observational comment; `docs/rp-data-layout.md` artifact classes table. |

---

### A5 — Phase-local retry/reasoning policy fragmentation (drift risk)

| Field | Value |
|-------|-------|
| **Classification** | worthwhile refinement |
| **Severity / architectural significance** | moderate |
| **Confidence** | moderate |
| **Responsibility** | retry/correction; provider invocation defaults |
| **Components** | `narrator-phase.mjs` (`narratorRetryDecision`, fidelity retry loops); `character-phase.mjs`; `director-phase.mjs`; `reasoning-provider-options.mjs`; `assembled-request.mjs` |
| **Execution/data-flow** | Each phase executor implements retry/regen policy locally with shared substrates for inference but **not** a single retry budget registry. Reasoning effort mapped in `assembled-request.mjs` from profile fields with multiple key aliases (`reasoningEffort` / `reasoning_effort`). |
| **Overlap evidence** | Repeated retry decision patterns across phases — similar structure, independent constants/thresholds. |
| **Architectural authority** | `docs/architecture.md` — DSH owns semantic QA judgment; no central retry policy doc located. |
| **Legitimate reason** | Phase-specific failure modes (narrator fidelity vs character move validity) warrant different retry semantics. |
| **Counterargument assessment** | Partial — semantic differences justify separation; **drift risk** remains for shared limits (max attempts, reasoning ceilings). |
| **Likely authoritative owner** | DSH phase executors collectively; no documented single owner. |
| **Candidate consolidation surface** | Shared `retry-policy.mjs` registry with phase-specific profiles (not single global retry). |
| **Efficiency impact** | Low today; higher when tuning provider behavior globally. |
| **Stability/auditability impact** | Moderate — inconsistent retry caps could confuse forensic replay. |
| **Scalability/maintenance impact** | Moderate. |
| **Recommended disposition** | `investigate further` — config centralization audit — recommendation only. |
| **Evidence** | `narrator-phase.mjs` multiple `narratorRetryDecision` call sites; `assembled-request.mjs:39-46` reasoning field aliasing. |

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
| **Apparent overlap** | `perception_audibility`, `PublicEvent.known_by`, `character_may_know_candidate`, Librarian bundle validity, PVR |
| **Why redundant-looking** | Multiple "can character X know Y?" checks |
| **Traced relationship** | Audibility filters **verbatim dialogue** in structured moves; `known_by` gates **event knowledge** at continuity; retrieval gates **candidate provenance** before Librarian mediation; PVR filters **history projection** |
| **Distinct boundary** | Different objects (dialogue vs event vs candidate vs transcript view) |
| **Counterevidence** | `perception_audibility.py` module contract; `architecture-overview.md` #33 decomposition |
| **Conclusion** | Justified — not redundant enforcement of one rule |
| **Disposition** | `retain as intentional` |

### J3 — Deterministic validation vs semantic QA

| Field | Detail |
|-------|--------|
| **Responsibility** | validation / semantic QA |
| **Apparent overlap** | `validate_move`, `validate_bot_response_for_runtime`, character semantic evaluation, director/narrator semantic QA |
| **Traced relationship** | Ingress → parse → runtime rules → Host validate (deterministic) → DSH semantic eval (LLM judgment for deferred rules per `response_validation_content.py` header) |
| **Distinct boundary** | Deterministic rejects illegal shapes; semantic QA handles interpretive rules (#19) |
| **Counterevidence** | `response_validation_content.py` documents R02b/R11–R15 deferral to semantic evaluation |
| **Conclusion** | Justified pipeline, not duplicate contract |
| **Disposition** | `retain as intentional` |

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
| **Apparent overlap** | Six+ stores per turn |
| **Traced relationship** | rp_history = durable transcript; execution evidence = per-inference payloads; trace = event bus for tooling; audit tags = human anchors |
| **Distinct boundary** | Retention scope, restart durability, query consumers differ |
| **Conclusion** | Justified multi-surface architecture; cost is operational (see A4), not authority duplication |
| **Disposition** | `accepted` |

### J6 — DSH custom orchestration over Cordis

| Field | Detail |
|-------|--------|
| **Responsibility** | runtime orchestration |
| **Apparent overlap** | Cordis `Service` lifecycle vs `HgRoundOrchestrator` |
| **Traced relationship** | Cordis provides plugin mounting, inference sessions; HG custom provides domain round state machine, phase executors, Host HTTP client |
| **Distinct boundary** | Framework vs Holy Grail domain semantics; Python never calls DSH |
| **Conclusion** | Required custom layer — native Cordis does not encode participation policy, Librarian S4 join, or Host contract |
| **Disposition** | `retain as intentional` |

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
| Evidence recording | multiple | execution-evidence, trace, rp_history, audit tags | 6+ | observational | — | multiple gitignored dirs | Operational cost | A4, J5 |
| Forensic reconstruction | investigation tools | `tools/investigation/*` | N projections | none | reports | — | Tooling gap | A4 |
| Session/round identity | Host + DSH | `session_state.py`, round orchestrator | 2 (coordination) | round bookkeeping on commit | — | session + evidence | No | — |
| Provider invocation | DSH + Cordis | `assembled-request.mjs`, provider mount | 1 | none | profiles | execution evidence | No | — |
| Runtime defaults/config | split | phase executors, env, bindings | many | — | — | — | Drift risk | A5 |

---

## Whole-system assessment

### Strongest confirmed architectural inefficiencies

1. **A1** — Second continuity mutation seam (Librarian S4) increases audit cognitive load despite intentional design (unchallenged by external review).
2. **A4** — Forensic fragmentation imposes reconstruction cost on operators (mitigated partially by investigation tooling; unchallenged by external review).

**Note:** Initial A3 characterization overstated Narrator as a parallel assembly path; corrected per GF-1. Formatter ownership (A3) is a lower-significance refinement, not a primary inefficiency.

### Highest-risk ownership/authority overlaps

- **Continuity mutation (A1)** — highest authority risk; currently bounded and audited, but expansion of S4 proposal classes without discipline would compound debt.
- **No confirmed duplicate continuity truth writers** beyond documented S4 seam at `main`.

### Legacy/superseded residue

| Item | Status |
|------|--------|
| v1 character move ingress | Removed (#143) |
| `perceptual_visibility_legacy` | Active read adapter (J9) |
| `character_move_adapters` | Active read projection |
| `prompt_builders` | Active formatter module — `build_narrator_render_prompt` called from `narrator_context.py`; output wrapped in manifest `inference_instruction` (A3). Other formatters in module have no `v2/` production callers at anchor. |
| `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` | Dead code (A2) |
| `FixtureStore` | Test-only |
| `validate_bot_response_for_scenario` | Tests/offline only |

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

**Appropriate** — custom orchestration encodes domain rules absent from Cordis primitives (J6). No spurious reimplementation of Cordis Service lifecycle.

### Forensic/evidence architecture health

**Functionally sound**, **operationally heavy** (A4). Correlation IDs exist; unified turn view is tooling gap not authority bug.

### Configuration/contract centralization health

**Moderate drift risk** (A5) for retry/reasoning across phases; packet contracts centralized in `PACKET_CONTRACTS.md`.

### Overall architectural efficiency

The system exhibits **substantial intentional layering** from incremental Issue-driven delivery (#31–#55, Librarian S4, forensic standard). **True redundant authority is rare** at `main`; the dominant costs are **audit surface area** (forensic channels, S4 mutation seam) and **residual module indirection** (`prompt_builders` formatter ownership, dead legacy constant A2).

### Aggregate accidental complexity

Incremental additions (validation depth, forensic surfaces, S4 post-commit join, plot cognition overlay) create a **whole greater than the sum of individually justified parts**. Maintenance burden is **measurable in operator/investigator time**, not runtime failure rate.

### Focused follow-up audits warranted?

- **S4 continuity mutation playbook** (narrow) — recommended after this report.
- **Retry/reasoning policy registry** (DSH config) — optional.
- **Not warranted:** broad re-audit of Retrieval/Librarian/Storyteller decomposition — found healthy.

### Candidate successor Issue packages (recommendations only — NOT authorized)

1. **Doc/tooling:** Operator guide correlating forensic surfaces per turn (addresses A4).
2. **Cleanup:** Wire or remove `LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS` (A2).
3. **Optional review:** Narrator render-instruction formatter ownership — retain in `prompt_builders` vs colocate nearer `narrator_context.py`; must preserve live dialogue, visibility, and manifest contracts (A3; not pre-authorized).
4. **Architecture record:** Formal S4-vs-process_turn mutation matrix on audit parent or architecture doc (A1).

---

## External review disposition

| Field | Value |
|-------|-------|
| **PR** | [#99](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/99) |
| **Greptile review head (GF-1)** | `10289f8d8eb0959005b2f6332dc4f8e5e315aeeb` |
| **Finding** | GF-1 (P2) — Narrator migration mischaracterized |
| **Governance disposition** | **Accepted** |
| **Nature of correction** | A3 incorrectly claimed Narrator used a parallel assembly path and still required migration into `PromptContribution` lanes. Evidence shows `prepare_narrator_context` already wraps `build_narrator_render_prompt` output as `inference_instruction` in the returned manifest. |
| **A3 reclassification** | `architectural debt` → `worthwhile refinement`; reframed as formatter ownership/indirection, not manifest migration. |
| **Remediation performed** | None — audit report documentation correction only. |
| **Authority note** | Greptile supplied independent review evidence; Governance determined disposition. Absence of Greptile comments on other findings is **not** external validation of those conclusions. |

---

## Internal report validation

| Check | Result |
|-------|--------|
| Cited files exist at anchor | Pass — spot-checked paths at `ba54016` |
| Callers/execution paths supported | Pass — `process_turn` production caller verified; narrator manifest integration verified |
| A3 accurately represents execution flow | Pass — Narrator manifest-first; formatter delegated (GF-1 correction applied) |
| Writers actually write | Pass — S4 apply and `process_turn` traced |
| Authority matches docs | Pass — matches architecture-overview with A1 documented exception |
| Counterarguments evaluated | Pass — 9 justified separations documented |
| Consolidation labeled candidate | Pass — no pre-authorized fixes |
| Classifications supported | Pass — A3 reclassified per evidence |
| Dependent summaries consistent | Pass — counts and whole-system assessment updated |
| Recommendations non-authorizing | Pass |

**GF-1 revalidation:** PASS (2026-09-01 refinement cycle).

**Factual uncertainties:** Live scenario replay not executed at audit anchor. Greptile re-review on refined head pending at commit time.

---

## No-remediation attestation

This audit cycle performed **investigation and documentation only**. No production code, tests, configuration, or dependencies were modified. GF-1 refinement modified **audit report documentation only**. No remediation Issues were created. No architectural remediation is bundled in audit PR commits. Remediation requires separate Governance authorization and tracked Issues reaching `consensus_reached`.

---

## Related authority

- `governance/sources/audit-semantics.md`
- `governance/sources/architecture-overview.md`
- `MODULE_INDEX.md`
- `docs/forensic-auditability-standard.md`
- `docs/audit-workflows.md`
