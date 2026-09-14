# Issue #204 — System-Wide Documentation & Forensic Adequacy Audit

**Issue:** [#204](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/204)  
**Type / Layer:** `design_gap` / `audit_simulation`  
**Repository anchor:** `ce761ec0763a27b27248afbd94ad442cc3dd2775`  
**Assessment date:** 2026-09-14  
**Workflow weight:** assigned `standard`, effective `full`  
**Bootstrap profile:** Full  
**Mode:** read-only assessment (no remediation implemented)

**Governing question:**

> Does the repository accurately document the system that actually exists, and can its forensic/audit infrastructure reliably reconstruct the material runtime decisions, authority flows, information handoffs, validation outcomes, and state transitions needed for architectural analysis without relying on chat history or undocumented repository archaeology?

---

## A. Activation

| Item | Value |
|------|--------|
| Issue state | OPEN, `Current status: investigating` |
| Project #10 | Status **In Progress**, Workflow **Investigating**, Priority **P1** |
| Gated successor #201 | OPEN, Todo / Ready / P1 — **not mutated** |
| Local data | `data/execution_evidence/` (~10.8k session trees), `data/sessions/` (~10.5k files) present |
| Assessment artifacts | This report; temporary body/comment drafts deleted after filing |

---

## B. Audit authorities and methodology

### Authoritative vs derivative (read order)

| Tier | Documents | Role |
|------|-----------|------|
| **Governance standing sources** | `governance/sources/*.md` (six files) | Product intent, architecture invariants, issue workflow, audit semantics, workflow weights, project behavior |
| **Implementation bootstrap** | `AGENTS.md`, `docs/issue-bootstrap-profiles.md`, `governance/execution/*` | Implementation AI routing and execution policy |
| **Architectural contracts (shared)** | Root `PACKET_CONTRACTS.md`, `AUTHORED_SOURCE_CONTRACT.md`, `CANONICAL_KNOWLEDGE_MODEL.md`, `SCENARIO_VALIDATION_FRAMEWORK.md` | Runtime seam and validation contracts |
| **Implementation guardrails** | `docs/architecture.md`, `docs/rp-data-layout.md`, `docs/forensic-auditability-standard.md`, subsystem contracts under `docs/plot-cognition-*.md`, `docs/player-authorship-authority.md`, etc. | Deep runtime/integration detail |
| **Navigation / symptom routing** | `MODULE_INDEX.md`, `docs/repo-map.md`, `DEBUGGING_GUIDE.md`, `GLOSSARY.md` | Non-canonical routing |
| **Forensic procedure** | `docs/audit-workflows.md`, `tools/investigation/README.md` | How to read retained evidence |
| **Governance records** | `governance/records/*` | Historical/program evidence — not current authority |

**Methodology:** Full bootstrap reads; implementation inventory from code; documentation corpus classification; architecture-to-doc matrix; anchor-based forensic CLI exercises on (1) live F06 session `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311`, (2) committed fixture `data/fixtures/audit_sqa_e2e_9065f006/`; drift-test inventory; finding classification per `governance/sources/audit-semantics.md`.

**Implementation evidence controls truth** — documentation evaluated against code and persisted artifacts.

---

## C. Documentation authority map

### Canonical authorities (normative)

| Document | Scope |
|----------|--------|
| `governance/sources/holy-grail-prd.md` | Product requirements |
| `governance/sources/architecture-overview.md` | Standing architectural invariants, three-layer model |
| `governance/sources/issue-tracking-workflow.md` | Issues/Projects workflow |
| `governance/sources/audit-semantics.md` | Program audit finding model |
| `governance/sources/workflow-weights.md` | Workflow weight vocabulary |
| `governance/sources/project-behavior-holy-grail.md` | Work tracking, consensus gate |
| `SCENARIO_VALIDATION_FRAMEWORK.md` | Behavioral validation canon |
| `docs/forensic-auditability-standard.md` | Forward forensic reconstructability requirement |
| `docs/rp-data-layout.md` | On-disk artifact contracts |
| `PACKET_CONTRACTS.md` | Runtime packet/manifest seams |

### Architectural contracts (subsystem)

| Cluster | Key files |
|---------|-----------|
| Player authorship / PVR | `docs/player-authorship-authority.md`, `docs/architecture.md` § perceptual |
| Story knowledge (#50) | `docs/story-knowledge.md` |
| Scene grounding | `docs/scene-grounding-layer.md` |
| Plot cognition (#58–#64) | Seven `docs/plot-cognition-*.md` files |
| Core invariants (summary) | `docs/core-operating-invariants.md` (derivative summary) |

### Navigation / indexes (non-canonical)

`AGENTS.md`, `README.md`, `MODULE_INDEX.md`, `docs/repo-map.md`, `docs/llm-call-catalog.json` (generated view), `DEBUGGING_GUIDE.md`, `GLOSSARY.md`.

### Forensic guides

`docs/audit-workflows.md` (procedure), `tools/investigation/README.md`, `docs/plot-cognition-forensics-contract.md`.

### Governance records / historical

`governance/records/` (~80+ files), `docs/story-knowledge-embedding-evaluation.md` (dated gate snapshot).

### Duplication / tension (intentional but drift-prone)

| Topic | Primary | Secondary | Risk |
|-------|---------|-----------|------|
| Architecture | `governance/sources/architecture-overview.md` | `docs/architecture.md` (much deeper) | Overview can lag implementation detail |
| Audits | `audit-semantics.md` | `audit-workflows.md`, `forensic-auditability-standard.md` | Three entry points — boundaries are documented |
| PRD | `governance/sources/holy-grail-prd.md` | Stale link target `Holy Grail PRD.md` in `docs/architecture.md` | **Broken link** |

---

## D. Actual system/runtime inventory

### Topology (verified in code)

```
Streamlit UI (v2/ui/streamlit_app.py)
  → Node app-server / hg-application-client.mjs
    → hg-round-orchestrator (Cordis)
      → hg-phase-executors (Director, Character, Narrator, Player phases)
      → hg-context-bridge + inference-substrate (LLM transport)
      → hg-trace-emitter (log-only events)
    → domain-api-client.mjs → Domain Host http_transport.py / kernel.py
      → v2/domain/modules/* (continuity, validation, memory, perception, …)
```

### Major runtime surfaces

| Surface | Primary implementation | Documented in MODULE_INDEX | Documented in docs/architecture.md |
|---------|------------------------|:--------------------------:|:--------------------------------:|
| Player / PVR / triage | `hg-application-client.mjs`, `player-*-phase.mjs`, `player_perceptual_*`, `player_pvr_entitlement_context.py` | Yes | Yes |
| Director | `director-phase.mjs`, `director_context.py`, `response_validation_selection.py` | Yes | Yes |
| Character | `character-phase.mjs`, `character_context*.py`, `character-semantic-evaluation.mjs` | Yes | Yes |
| Continuity / commit | `continuity_manager.py`, `commit_move_transaction.py`, `kernel.commit_move` | Yes | Yes |
| Librarian S2a/S4 | `librarian_*` (Host + DSH substrates) | Yes | Yes |
| Storyteller S3 | `storyteller_*`, `storyteller-cognition-substrate.mjs` | Yes | Yes |
| Narrator / env cognition | `narrator-phase.mjs`, `narrator_environment_*` | Yes | Yes |
| Semantic eval / QA | `character-semantic-evaluation.mjs`, `semantic_evaluation_context.py`, `*-semantic-qa.mjs` | Yes | Yes |
| Plot cognition | `plot_cognition_*` (Host), `plot-cognition-*.mjs` (DSH) | **No** | **No** |
| Inference transport | `domain-api-client.mjs`, `inference-substrate.mjs`, `hg-context-bridge` | Partial | Partial |
| Execution evidence | `execution-evidence/store.mjs`, `recorder.mjs` | Yes (forensics row) | Partial |
| Application server layer | `app-server.mjs`, `application-turn-lifecycle.mjs` | Partial | Partial |

### Governance / evidence stores

| Store | Path | Git policy |
|-------|------|------------|
| Session truth | `data/sessions/*.json` | Gitignored (operator-local) |
| Execution evidence | `data/execution_evidence/<hg_session_id>/` | Gitignored |
| Audit tags | `data/audit_tags/` | Gitignored |
| Plot cognition forensics | `data/plot_cognition_forensics/` | Gitignored |
| Legacy rp_audits | `data/rp_audits/session_*` | Gitignored |
| Committed audit fixtures | `data/fixtures/audit_sqa_e2e_9065f006/` | **Committed** |
| Tool acceptance fixtures | `tools/investigation/fixtures/` | **Committed** |

---

## E. Architecture-to-documentation coverage matrix

| Runtime surface | Actual implementation | Canonical docs | Navigation | Accurate? | Complete? | Contradictions? | Hidden behavior? |
|-----------------|----------------------|----------------|------------|-----------|-----------|-----------------|------------------|
| Three-layer topology | DSH / Host / domain | architecture-overview, architecture.md | AGENTS, repo-map | Yes | Yes | Minor terminology drift | Low |
| Player PVR stack | player phases + Host entitlement | player-authorship-authority, architecture.md, audit-workflows §#91/#199 | MODULE_INDEX | Yes | Good | None material | Join recipes documented |
| Director + semantic QA | director-phase + Host | architecture.md, audit-workflows | MODULE_INDEX | Yes | Good | None | — |
| Character + semantic eval | character-phase + Host | architecture.md, audit-workflows §#199 | MODULE_INDEX | Yes | Good | None | — |
| Continuity / commit | continuity_manager, commit_move_transaction | architecture.md, rp-data-layout | MODULE_INDEX | Yes | Good | None | — |
| Librarian S2a/S4 | librarian_* modules | architecture.md, story-knowledge | MODULE_INDEX | Yes | Good | None | — |
| Storyteller S3 | storyteller_* | architecture.md | MODULE_INDEX | Yes | Adequate | None | — |
| Narrator + env cognition | narrator-phase, narrator_environment_* | architecture.md, audit-workflows §#49 | MODULE_INDEX | Yes | Good | None | — |
| Plot cognition | plot_cognition_* + DSH orchestration | **plot-cognition contract cluster only** | rp-data-layout, audit-workflows | Accurate in contracts | **Gap: not in MODULE_INDEX or architecture.md** | None | **Discoverable only via contracts/code** |
| Inference transport / bridge | context-bridge, inference-substrate | architecture.md (partial) | live-inference-prompts row | Partial | **Thin** | None | Medium |
| Execution evidence | EE store + indexes | rp-data-layout, forensic standard, audit-workflows | tools README | Yes | Good post-#28/#45 | None | Pre-contract sessions lack fields |
| Scene pressure freshness (#200) | continuity_scene_pressure_projection, overlays | audit-workflows §#200 join recipe | MODULE_INDEX (#200 row) | Yes | Join documented; no first-class navigator | None | Manual cross-read required |
| Session JSON shape | `metadata.v2_host_state.rp_history` | rp-data-layout § v2_host_state | audit-workflows | Yes | **Easy to miss** (not top-level `rp_history`) | None | Investigators may search wrong path |
| rp_history entry typing | entries often lack `entry_type` | Not prominently documented | — | N/A | **Undocumented quirk** | None | Filter by `domain_commit_id` instead |

---

## F. Documentation drift findings

| ID | Finding | Evidence |
|----|---------|----------|
| F1 | Broken PRD link in `docs/architecture.md` line 115 → `../Holy Grail PRD.md` (file absent) | File glob; canonical PRD is `governance/sources/holy-grail-prd.md` |
| F2 | Broken relative link in `docs/audit-workflows.md` → `../../SCENARIO_VALIDATION_FRAMEWORK.md` (escapes repo root from `docs/`) | Path resolve |
| F3 | Plot cognition live subsystem absent from `MODULE_INDEX.md` and `docs/architecture.md` | Code inventory vs index grep |
| F4 | Several substantial contract families not on AGENTS/README surface (plot cognition, `CANONICAL_KNOWLEDGE_MODEL.md`, `forensic-auditability-standard.md`, `player-authorship-authority.md`) | AGENTS.md read set vs docs/ inventory |
| F5 | `docs/architecture.md` can run ahead of `governance/sources/architecture-overview.md` | Length/completeness comparison |
| F6 | `rp_history` nested under `metadata.v2_host_state` — documented in rp-data-layout but not obvious from older mental model | Fixture session JSON structure |
| F7 | `rp_history` entries may omit `entry_type`; investigators must use `domain_commit_id` / `entry_id` | Fixture session analysis |

---

## G. Documentation navigation assessment

### Successful routes (first-class)

`AGENTS.md` → `MODULE_INDEX.md` → domain module path (continuity, perception, validation, Librarian, Storyteller).  
`AGENTS.md` → `docs/architecture.md` → subsystem sections.  
`AGENTS.md` → `docs/audit-workflows.md` → `trace_turn_forensics.py` quick start.  
`docs/repo-map.md` → `v2/` layout → subsystem docs.

### Adequate with linked docs

Plot cognition → `docs/rp-data-layout.md` → `docs/plot-cognition-*.md`.  
Player authorship → `MODULE_INDEX.md` symptom rows → `docs/player-authorship-authority.md`.  
Forensic standard → cited from `audit-workflows.md` / `architecture.md`.

### Requires repository archaeology

Inference transport plumbing (`inference-substrate.mjs`, `contract-correction-substrate.mjs`, `domain-api-client.mjs`) without MODULE_INDEX rows.  
Application server orchestration before `runRound` (partial coverage).

### Broken / misleading

`docs/architecture.md` PRD link (F1).  
`docs/audit-workflows.md` scenario framework link (F2).

**Overall navigation classification:** **adequate with linked docs** — workable for experienced maintainers; plot cognition and inference-transport gaps increase archaeology cost for #201.

---

## H. Expected forensic decision coverage

Derived from `docs/forensic-auditability-standard.md`, `docs/rp-data-layout.md`, `docs/audit-workflows.md`.

| Decision class | Minimum forensic answer expected |
|----------------|----------------------------------|
| Session / round / operation | Stable IDs in session + EE correlation |
| Inference attempt | `evidence_id`, `inference_id`, assembled request, response, health |
| Player / PVR | PVR metadata on history + EE player phases + perceptual inventory contribution |
| Director selection | EE Director attempts + validation + semantic QA chain |
| Character move | EE Character attempts + semantic eval + commit id |
| Continuity mutation | Session continuity_state + commit correlation |
| Librarian / NI | `hg_ni_forensics_v1`, `trace_ni_forensics.py`, mediation disposition |
| Storyteller | EE storyteller attempts + round package invalidation on commit |
| Narrator | EE narrator attempts + `narrator_environment_audit` in turn metadata |
| Semantic QA | `decision.semantic_qa` on attempts; index chains |
| Plot cognition | `data/plot_cognition_forensics/` + `trace_plot_cognition_forensics.py` |
| Retry / correction | `prior_attempt_id`, contract-correction attempts, recovery dimension |
| Provider / tokens / timing | `request.inference_profile`, `inference_health`, `execution_span` + orchestration graph (#173) |
| Validation disposition | `decision.*`, semantic eval `overall_result`, post_commit_semantic_disposition |
| Pressure freshness (#200) | Documented join across overlay + rp_history sequence_index — **no dedicated event** |

---

## I. Actual forensic/evidence inventory

### Schemas (live)

- `hg_execution_evidence_index_v1` — per-session index with derived navigation keys
- `hg_execution_evidence_attempt_v1` — request/response/decision/correlation/associations/inference_health
- `hg_turn_investigator_v1` — navigator output
- `hg_ni_forensics_v1` — NI forensic contract (#45)
- `hg_audit_tag_v1` — human observational tags
- Plot cognition forensics records under `data/plot_cognition_forensics/`

### CLI tools

| Tool | Anchors supported |
|------|-------------------|
| `trace_turn_forensics.py` | session, commit, round, turn, entry, tag (+ root overrides for fixtures) |
| `list_execution_evidence.py` | session, round, role, chain, inference-id, inference-health |
| `trace_ni_forensics.py` | session, tag, lineage |
| `trace_plot_cognition_forensics.py` | scope, commit, timeline, integrity |
| `reconstruct_round_latency.py` | session, round, commit, operation (timing) |
| `list_audit_tags.py` | session, tag |

**Gap:** `list_execution_evidence.py` lacks `--evidence-root` override (fixture sessions require default data path or env). `trace_turn_forensics.py` supports overrides.

### Issue-specific forensic scripts (accumulation)

`_issue240_*.py` (5 modules) — offline Issue #240 analysis; not consolidated into general navigator.

---

## J. Decision reconstruction coverage matrix

| Decision class | Evidence class | Stable ID | Joins | Durable | Navigator |
|----------------|---------------|-----------|-------|---------|-----------|
| Director selection | Structured + linked | Yes | Round, QA chain | Gitignored EE | First-class chain |
| Character semantic eval (#199) | Structured | Yes | Character attempt, authority refs | EE + governance JSON fixture | Documented join recipe |
| Continuity commit | Structured (session) + linked EE | `domain_commit_id` | turn_metadata, public_events | Session JSON | commit view |
| Librarian mediation | Structured (NI contract) | Yes | tag, lineage | EE + NI indexes | `trace_ni_forensics.py` |
| Storyteller cognition | Structured | Yes | Round | EE | Round view + chains |
| Narrator + env cognition | Structured + session metadata | Yes | commit, turn index | EE + `narrator_environment_audit` | audit-workflows §#49 |
| Plot cognition | Structured (separate store) | scope_id | commit, batch | plot_cognition_forensics | Specialist CLI |
| Pressure freshness (#200) | **Linked structured only** | overlay fields | sequence_index recompute | Session JSON | **Manual cross-read** |
| Player → Continuity promotion | **Missing** (by design today) | — | — | — | Impossible |
| Timing / critical path | Structured spans | operation_id (when present) | EE spans | EE | `reconstruct_round_latency.py` |
| Retry / correction | Structured | prior_attempt_id | inference_id chains | EE | list chains |
| Pre-#28 / pre-#45 sessions | Partial / missing contracts | Varies | Limited | May exist | Report limitations |

---

## K. Anchor-based forensic navigation results

### Sessions exercised

1. **Live F06** `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311` — 108 EE attempts; timing reconstruction succeeded (round_internal ~82s, post_commit ~149s); Director QA chains listed; session JSON has no top-level `rp_history` (EE-rich, session-truth-poor locally).
2. **Committed fixture** `hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa` — full session under `metadata.v2_host_state`; commit-view navigator returned 7 surfaces, 3 handoffs, 1 limitation (`contract_unavailable`).

### Path classifications

| Path | Classification |
|------|----------------|
| session → Director → Character → commit (fixture) | **First-class** (`trace_turn_forensics.py commit`) + linked EE |
| session → Player PVR → Character inventory (#199) | **Linked structured** (documented recipe; governance JSON fixture for validation) |
| session → pressure overlay → Character manifest (#200) | **Manual cross-read** (documented; no navigator surface) |
| session → Plot cognition | **Specialist CLI** (`trace_plot_cognition_forensics.py`) |
| session → timing / #201 latency | **First-class** (`reconstruct_round_latency.py`) when spans present |
| Player contribution → Continuity world promotion | **Impossible** (no mechanism) |

---

## L. Representative end-to-end reconstruction exercises

### L1 — Player/perception (#199 strain)

**Source:** `governance/records/issue-199-supplemental-semantic-validation-2026-09-14.json`  
**Decision:** Semantic evaluator `reject_hard` on R02b+R14 for unsupported Player sensory claims against empty `authoritative_perceptual_inventory`.  
**Evidence:** Structured eval result with `perception_fact:authorized_inventory:*` authority ref, entitled_count 0, beat-level candidate_evidence.  
**Reconstructable without chat?** **Yes** (committed governance record + documented join recipe).  
**Tooling:** Recipe in `audit-workflows.md`; live session join requires EE + session JSON.

### L2 — Character semantic validation (live Director/Character chains)

**Source:** F06 session `list_execution_evidence.py --chain director`  
**Decision:** Director semantic QA `policy_action: pass` with paired candidate/evaluator evidence IDs.  
**Reconstructable?** **Yes** for pass/fail disposition; full rationale requires reading evaluator attempt content.  
**Tooling:** First-class chain listing.

### L3 — Continuity/state (fixture commit)

**Source:** Fixture session `commit_ids[0]` = `hg-commit-5911e5b7-419f-41aa-be67-63954276544b`  
**Decision:** Committed turn promoted into `metadata.v2_host_state.rp_history` with `domain_commit_id`.  
**Reconstructable?** **Yes** for what committed; promotion metadata via `turn_metadata_by_index` (when present).  
**Tooling:** commit view + session JSON.

### L4 — Librarian/Storyteller orchestration

**Source:** Fixture navigator handoffs include `trace_plot_cognition_forensics.py`; audit-workflows documents S3/S4 paths.  
**Reconstructable?** **Yes** with specialist tools; not unified in single turn navigator for all post-commit lanes.  
**Classification:** Linked structured + specialist CLI.

### L5 — Narrator/postcommit

**Source:** `audit-workflows.md` §#49 recipe; fixture includes Narrator chains in manifest mapping SQA-03.  
**Reconstructable?** **Yes** for post-#49 sessions with `narrator_environment_audit` + EE.  
**Tooling:** Documented join + EE.

### L6 — Retry/correction (Plot/Librarian)

**Source:** Fixture manifest SQA-04b — 20 contract-correction attempts published.  
**Reconstructable?** **Yes** (correction attempts identifiable by inference_kind).  
**Tooling:** list_execution_evidence / manifest.

### L7 — Timing/token critical path

**Source:** F06 `reconstruct_round_latency.py --attribution`  
**Decision:** Round internal critical path 81986ms (proven), post-commit section 149002ms (proven); player_visible unavailable (`no_application_operation_id`).  
**Reconstructable?** **Partial** — strong round-internal/post-commit; player-visible gap documented.  
**Tooling:** First-class for available scopes.

---

## M. Evidence durability assessment

| Class | Examples | Assessment |
|-------|----------|------------|
| Committed fixtures | `data/fixtures/audit_sqa_e2e_9065f006/` | Durable for CI/review; curated subset |
| Runtime-persistent gitignored | `data/sessions/`, `data/execution_evidence/` | Intended policy; operator-local |
| Governance validation JSON | `issue-199-*.json`, `issue-200-*.json` | Durable committed proof for specific gates |
| Transient | `LiveSession.rounds[]`, in-memory freshness index | Not durable — documented |
| Test-only | `tools/investigation/fixtures/` | Committed acceptance |

**Risk:** Important conclusions about live F06 depend on local gitignored trees (~10k sessions) — **not reproducible on clone without export**. Committed fixture mitigates for audit methodology, not all live sessions.

**Policy alignment:** Gitignored EE is **correct as-is** per `rp-data-layout.md`; not classified defective.

---

## N. Documentation ↔ forensic agreement

| Claim | Reality | Gap type |
|-------|---------|----------|
| Unified turn navigator (#101) | Works for commit/round/entry/tag with limitations | **Agreement** with declared `limitations[]` |
| Pressure freshness reconstructable | Join recipe documented; no navigator surface | **Documentation accurate**; tooling debt |
| `authoritative_perceptual_inventory` in Character manifests | Present post-#199; recipe documented | **Agreement** |
| Plot cognition forensics | Specialist CLI + contracts; not in main architecture doc | **Documentation drift** (navigation) |
| LLM call catalog drift-protected | `llm-call-catalog-consistency.test.mjs` | **Agreement** |
| Module index completeness | No plot cognition / inference-transport rows | **Documentation drift** |
| `list_execution_evidence` works on fixtures | No `--evidence-root`; trace_turn_forensics has overrides | **Tooling inconsistency** |

---

## O. Drift-detection/test assessment

### Protected (machine-verified)

- LLM inference catalog ↔ runtime policy (`llm-call-catalog-consistency.test.mjs`, quota test)
- Execution evidence forensic completeness (`execution-evidence-forensic.test.mjs`, NI acceptance, post-commit semantic, orchestration timing)
- Turn navigator acceptance (`test_turn_forensics.py`)
- Plot cognition domain tests (`test_plot_cognition_forensics.py`)
- Issue-specific deterministic tests (#199 inventory, #200 pressure freshness)

### High-value unprotected

- `MODULE_INDEX.md` row coverage vs new subsystems (plot cognition, inference transport)
- Markdown link integrity (F1, F2)
- `docs/architecture.md` ↔ `architecture-overview.md` topical parity
- `list_execution_evidence.py` fixture-root parity with `trace_turn_forensics.py`

### Inappropriate to machine-test

- Full prose architecture narratives
- Governance records historical accuracy

---

## P. Documentation/forensic complexity assessment

| Question | Finding |
|----------|---------|
| Duplicate truth? | Architecture split (overview vs architecture.md); audit triple-entry (semantics/workflows/standard) — justified but heavy |
| Redundant indexes? | EE `index.json` derived keys + multiple specialist navigators — functional, join-heavy |
| Fragmented decisions? | Post-commit parallel lanes (Librarian S4, Plot, Narrator) require multiple tools |
| Issue-specific scripts? | `_issue240_*` (5 files) alongside general tools — consolidation opportunity |
| Specialist knowledge? | **Moderate-high** for pressure freshness, plot cognition, NI lineage |
| Runtime audit cost? | F06: 108 attempts/round slice; post-commit ~149s wall — instrumentation contributes to latency (#201 input) |
| Historical mechanisms? | Legacy `rp_audits/` documented as historical; V1 `#59` inventory explicitly not live |

**Input to #201:** Documentation/forensic stack complexity is itself a candidate for efficiency analysis; not blocking readiness.

---

## Q. Known blind spots and confidence limits

1. **Player → Continuity world-state promotion** — does not exist; #201 must not assume it.
2. **Pressure freshness** — reconstructable only via manual join; no structured `pressure_freshness_decision` event.
3. **Narrative door-open vs authoritative portal state** — known assessment item for #201; not fully instrumented.
4. **Pre-contract sessions** — incomplete EE fields; report `not observable`.
5. **Local-only evidence** — clone without `data/` cannot replay most live sessions.
6. **Player-visible latency** — `reconstruct_round_latency` may return unavailable without `application_operation_id`.
7. **Plot cognition** — weak navigation from primary entry points despite strong contracts.
8. **`rp_history` location/typing** — investigators may miss `metadata.v2_host_state` or filter on absent `entry_type`.

---

## R. Material findings

| ID | Finding | Class | Disposition | Threatens #201? |
|----|---------|-------|-------------|-----------------|
| R-F1 | Broken PRD link in `docs/architecture.md` | worthwhile refinement | remediation_tracked | Low |
| R-F2 | Broken SCENARIO_VALIDATION link in `audit-workflows.md` | worthwhile refinement | remediation_tracked | Low |
| R-F3 | Plot cognition absent from MODULE_INDEX and architecture.md | architectural debt | deferred | Medium (navigation) |
| R-F4 | Inference-transport subsystem thinly documented | architectural debt | deferred | Medium |
| R-F5 | Dual architecture doc homes drift risk | architectural debt | monitor | Low |
| R-F6 | Pressure freshness lacks first-class navigator | architectural debt | accepted | Low (recipe exists) |
| R-F7 | `list_execution_evidence` lacks fixture root override | worthwhile refinement | deferred | Low |
| R-F8 | Post-#28 forensic stack meets forward standard for modern sessions | correct as-is | accepted | — |
| R-F9 | Committed audit fixture enables independent verification | correct as-is | accepted | — |
| R-F10 | No Player→Continuity promotion path | correct as-is (missing capability) | accepted | Medium (scope clarity) |
| R-F11 | Issue-specific `_issue240_*` forensic scripts | architectural debt | monitor | Low |
| R-F12 | `rp_history` under `v2_host_state` easy to miss | worthwhile refinement | remediation_tracked | Low |

---

## S. Complete remediation map

| ID | Surface | Impact | #201 threat | Remediation type | Scope | Separate Issue? | Priority | Proof |
|----|---------|--------|-------------|------------------|-------|-----------------|----------|-------|
| R-F1 | `docs/architecture.md` link | Misroute to PRD | Low | documentation | 1-line link fix | No (or doc hygiene Issue) | P3 | Link check |
| R-F2 | `docs/audit-workflows.md` link | Broken validation doc route | Low | documentation | 1-line path fix | No | P3 | Link check |
| R-F3 | MODULE_INDEX + architecture.md | Harder plot cognition discovery | Medium | documentation | Add rows/section | Yes if large | P2 | Index review |
| R-F4 | docs/architecture.md | Inference transport opaque | Medium | documentation | New subsection | Defer to #201 | P2 | Peer review |
| R-F6 | trace_turn_forensics | Manual pressure joins | Low | forensic tooling | New navigator surface | Yes | P3 | Fixture #200 cases |
| R-F7 | list_execution_evidence.py | Fixture ergonomics | Low | tooling | Add `--evidence-root` | No | P3 | CLI test |
| R-F12 | audit-workflows / rp-data-layout | Wrong JSON path assumed | Low | documentation | Callout box | No | P3 | Doc review |

**Not authorized in this cycle** — map only.

---

## T. #201 readiness assessment

### Documentation

**Sufficient with declared limits.**

Dependable sources for #201:
- `governance/sources/architecture-overview.md` + `docs/architecture.md` (primary, with drift awareness)
- `MODULE_INDEX.md` for symptom routing (except plot cognition gap)
- `docs/audit-workflows.md` + `docs/rp-data-layout.md` + `forensic-auditability-standard.md`
- Plot cognition: `docs/plot-cognition-*.md` cluster (secondary navigation)
- Issue records for #199/#200 boundaries

Limits: F1/F2 links; plot cognition not on primary spine; inference-transport thin.

### Forensics

**Sufficient with declared limits.**

Dependable for #201:
- `data/execution_evidence/` + session JSON (when present locally)
- `trace_turn_forensics.py`, `list_execution_evidence.py`, `reconstruct_round_latency.py`
- Committed fixture `audit_sqa_e2e_9065f006` for independent challenge
- Documented join recipes for #199/#200

Limits: pressure freshness manual; no Player→Continuity promotion; player-visible latency gap; pre-contract sessions; local-only evidence.

### Remediation before #201

**No remediation required before #201.**

Bounded documentation fixes (R-F1, R-F2, R-F12) are **recommended but not blocking** — #201 can proceed with explicit blind spots (Section Q). Plot cognition navigation debt (R-F3) should be **carried into #201** as known architectural surface area, not a gate.

### Explicit determination

| Criterion | Result |
|-----------|--------|
| Documentation sufficient? | **Yes, with declared limits** |
| Forensics sufficient? | **Yes, with declared limits** |
| Blocking remediation before #201? | **No** |
| Deferrable debt for #201 analysis? | Plot cognition doc gap, forensic complexity, manual joins, inference-transport opacity |

---

## U. Mutation confirmation

| Action | Done? |
|--------|-------|
| Issue #204 → `investigating` | Yes |
| Project Status → In Progress, Workflow → Investigating | Yes |
| §B.5 transition comment | Yes |
| Durable report filed | This file |
| Runtime/docs/tests modified | **No** |
| Remediation Issues created | **No** |
| #201 mutated | **No** |

---

## V. Artifact disposition

| Artifact | Disposition |
|----------|-------------|
| `governance/records/issue-204-system-wide-doc-forensic-audit-2026-09-14.md` | **Retained** (durable deliverable) |
| `_issue204-body-temp.md` | Delete after issue body verified |
| `_issue204-transition-comment.md` | Delete (content on Issue comment) |

---

## W. Recommended next governance action

1. **Review** this report and finding classifications (Section R).
2. **Accept** #201 readiness determination (Section T) or dispute specific blind spots.
3. **Optionally authorize** narrow documentation hygiene (R-F1, R-F2, R-F12) without expanding #204 scope.
4. On acceptance: transition #204 toward consensus on findings; **then** authorize #201 investigation phase.
5. Track R-F3/R-F4/R-F6 as separate remediation Issues if Governance wants navigation fixes before or parallel to #201.

---

**READY FOR GOVERNANCE AUDIT FINDINGS REVIEW**

---

## X. Governance findings refinement (2026-09-14)

Governance accepted the investigation with disposition refinements:

| Finding | Class | Prior disposition | Final disposition |
|---------|-------|-------------------|-------------------|
| R-F3 Plot cognition navigation gap | architectural debt | deferred | **remediation_tracked** |
| R-F4 Inference transport thin docs | architectural debt | deferred | **remediation_tracked** |
| R-F1, R-F2, R-F12 | worthwhile refinement | remediation_tracked | **remediated in #204** |
| R-F5 | architectural debt | monitor | monitor (unchanged) |
| R-F6, R-F7 | architectural debt / refinement | accepted/deferred | unchanged |
| R-F8, R-F9 | correct as-is | accepted | unchanged |
| R-F10 | correct as-is (capability gap) | accepted | unchanged |
| R-F11 | architectural debt | monitor | monitor (unchanged) |

Forensic readiness for #201: **accepted sufficient with declared limits** (no new tooling required pre-#201).

---

## Y. Bounded documentation remediation (2026-09-14)

**Repository anchor:** `ce761ec0763a27b27248afbd94ad442cc3dd2775` (pre-remediation); remediation uncommitted at validation time.

| Finding | Change |
|---------|--------|
| **R-F1** | `docs/architecture.md` — PRD link → `governance/sources/holy-grail-prd.md` |
| **R-F2** | `docs/audit-workflows.md` — scenario framework link → `../SCENARIO_VALIDATION_FRAMEWORK.md` |
| **R-F12** | `docs/rp-data-layout.md` — `metadata.v2_host_state.rp_history` discoverability + `entry_type` limitation |
| **R-F3** | `docs/architecture.md` — Plot Cognition section; `MODULE_INDEX.md` row; `docs/repo-map.md` route |
| **R-F4** | `docs/architecture.md` — Inference transport section |

**Files touched (documentation only):** `docs/architecture.md`, `docs/audit-workflows.md`, `docs/rp-data-layout.md`, `MODULE_INDEX.md`, `docs/repo-map.md`, this record (§X–Y).

**Validation (2026-09-14):** link targets exist; named module paths exist; no runtime/test/tooling changes.

---

## Z. Post-remediation #201 readiness

| Dimension | Determination |
|-----------|---------------|
| Documentation | **Sufficient with declared limits** |
| Forensics | **Sufficient with declared limits** |
| Blocking remediation before #201 | **None** |

Remaining known limitations (not blockers): R-F6 pressure freshness manual join; R-F7 fixture-root EE listing; R-F11 issue-specific scripts; local-only evidence; pre-contract gaps; player-visible latency gaps; R-F10 no Player→Continuity promotion; narrative/portal divergence (#201 input).

---

**READY FOR GOVERNANCE #204 CLOSURE REVIEW**
