# Issue #201 — Post-Commit Storyteller Durable-Pressure Causal-Gap Investigation

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**Investigation type:** Read-only causal-gap adjudication (no production mutation, no live rerun)

**Anchors:** D-10 execution `1b8ff16` · blind lock `d36a023` · decode `64dff5f`

**Related records:**
- `governance/records/issue-201-package-d-d10-primary-decode-synthesis-2026-09-15.md`
- `governance/records/issue-201-package-d-d01l-consensus-refinement-2026-09-14.md`
- `PACKET_CONTRACTS.md` (#164, #40 B2)
- `docs/architecture.md` (S4 durable mutation allowlist)

---

## 1. Activation / state / weights

| Field | Value |
|-------|-------|
| Assigned / effective weight | `full` |
| Bootstrap profile | Full |
| D-10 execution | Complete |
| D-10 blind scoring / decode | Complete |
| D-10 architectural verdict | **Accepted** (recorded §2) |
| Additional live D-10 | NOT authorized |
| EXP-3 | Deferred |
| #201 synthesis | Deferred pending this investigation → **unblocked per §21** |
| Production remediation | NOT authorized |

---

## 2. Accepted D-10 Governance verdict (durable)

> **Post-commit Storyteller issue-pressure cognition has not demonstrated sufficient marginal value to justify its current implemented inference path. It is a strong remove/consolidate candidate in its current architecture.**

**Blind endpoint (locked scores; not rescored):**

| Slice | Control (post-commit ON) | Ablated (post-commit OFF) | Δ (control − ablated) |
|-------|-------------------------:|--------------------------:|----------------------:|
| Overall | 4.40 | 4.63 | **−0.23** |
| Arkham | 4.55 | 4.65 | **−0.10** |
| Ayame | 4.10 | 4.60 | **−0.50** (n=1/arm) |

Largest per-dimension ablated advantages: scene momentum, cross-turn initiative, reactive-loop avoidance (**−0.67** each). Thread persistence and agenda persistence remained **5/5** both arms — no narrative-memory-collapse population on removal.

**Critical qualification (also durable):** D-10 does **not** prove Storyteller pressure is semantically redundant with Plot. It proves the **current implemented post-commit path** did not improve blind RP quality while incurring inference cost.

---

## 3. Governing causal-gap question

> What exactly happens to an accepted `issue_tension_pressure` proposal after post-commit Storyteller produces it, and is `durable_mutation_applied: false` with zero observed overlays expected architecture, an observability gap, or an implementation defect?

**Answer summary:** Accepted proposals **do** become durable Continuity derived state under the authoritative contract. D-10's zero-overlay observation and universal `durable_mutation_applied: false` in execution-evidence attempts are **observability/instrumentation gaps**, not evidence that the apply path is broken.

---

## 4. H1 / H2 / H3 adjudication

| Hypothesis | Result | Confidence |
|------------|--------|------------|
| **H1 — Expected transient/advisory (no durable mutation)** | **Rejected** | High |
| **H2 — Observability / instrumentation gap** | **Primary** | High |
| **H3 — Implementation defect (apply/persist broken)** | **Rejected for pressure mechanism** | High |

### H1 rejected

Authoritative contracts designate `issue_tension_pressure` as a **durable derived overlay** on `ContinuityManager.issue_pressure_semantic_overlays`, joined into `scene_pressures` on subsequent rounds. Overlays are **derived/advisory** (not authoritative `IssueState` mutation) but **persist cross-turn** when applied.

### H2 confirmed (two distinct gaps)

1. **D-10 harness forensic reader** (`issue201-package-d-d10-post-commit.mjs` → `extractContinuityForensics`) reads `session.continuity_manager` / top-level `session.manager`. Authoritative persisted state lives at **`metadata.continuity_state`** in V1 session JSON (`SessionRepository._build_session_payload`). This caused `overlay_count_after: 0` in D-10 turn forensics despite live overlays.

2. **Execution-evidence patch** (`buildPostCommitSemanticDecisionPatch` in `ni-evidence.mjs`) sets `durable_mutation_applied` from `batch.durable_mutation_applied` / `batch.post_commit_semantic_durable_mutation_applied`. The finalize API returns `batch.continuity_decision.item_decisions[].durable_mutation_applied` but **does not** populate top-level batch flags. Evidence attempts therefore show `durable_mutation_applied: false` even when apply succeeded.

### H3 rejected (pressure mechanism)

Session audit logs and `metadata.continuity_state.issue_pressure_semantic_overlays` demonstrate successful apply/persist in D-10 control sessions. Repository tests (`test_librarian_proposal_b2_issue_pressure.py`) confirm end-to-end overlay creation, projection, and round-trip persistence.

**Residual forensics defect (non-blocking):** `ni-evidence.mjs` patch omission is an observability bug, not the pressure apply defect H3 contemplated.

---

## 5. Authoritative contract evidence

| Source | Intended semantics |
|--------|-------------------|
| `PACKET_CONTRACTS.md` #40 B2 | Accepted proposals persist derived overlays on `issue_pressure_semantic_overlays`; `scene_pressures` consumers unchanged |
| `docs/architecture.md` S4 allowlist | `issue_tension_pressure` → `ContinuityManager.issue_pressure_semantic_overlays` |
| `librarian_proposal_contract.py` | `S4A_ACTIVE_PROPOSAL_KINDS = {issue_tension_pressure}`; mutation surfaces enumerated |
| `issue-201-package-d-d01l-consensus-refinement` | Overlays are **Continuity durable derived state**, cross-turn when applied |
| `docs/architecture.md` #200 | Overlays are **derived/advisory** dramatic pressure; freshness-bound to Player authority |
| `continuity_librarian_issue_pressure.py` module doc | Persists semantics **separately from IssueState** |

**Classification:** `issue_tension_pressure` is **durable derived overlay state** — not transient proposal text, not authoritative issue mutation, not Plot overlay.

---

## 6. Complete proposal lifecycle

```text
Character commit (authoritative)
  → DSH hg-round-orchestrator: runPostCommitLibrarianLifecycle (parallel with Narrator)
      → domainApi.prepareLibrarianProposalContext
          → evaluate_post_commit_semantic_eligibility (ACTIVE/ESCALATING issues)
          → build evidence catalog + inference_kind storyteller_post_commit_issue_pressure
      → runLibrarianProposalGeneration (DSH)
          → storyteller_post_commit_issue_pressure LLM (0–1 per eligible commit)
          → proposals[] with proposal_kind issue_tension_pressure
      → domainApi.finalizeLibrarianProposals
          → validate_host_proposal_batch (structural/host)
          → evaluate_librarian_proposal_batch (continuity semantic accept/reject)
          → apply_accepted_librarian_proposals
              → apply_issue_tension_pressure → issue_pressure_semantic_overlays[issue_id]
          → librarian_proposal_audit_log entry (v2_host_state)
          → SessionRepository.persist → metadata.continuity_state
  → per-commit join before next Director/eligibility cycle
Subsequent round:
  → project_scene_pressures_digest / project_character_scene_pressures
      → get_active_issues + get_projectable_issue_pressure_overlay
      → build_scene_pressure_entry (authoritative issue fields + optional overlay semantics)
  → Director / Character / Storyteller orientation manifests
```

### Per-transition detail

| Step | Producer | Acceptance / mutation | State destination | Lifetime | Next consumer |
|------|----------|----------------------|-------------------|----------|---------------|
| Proposal generated | Storyteller LLM via DSH | — | ephemeral inference output | attempt record | finalize |
| Host structural validation | Host `validate_host_proposal_batch` | per-proposal `accepted` | — | — | continuity eval |
| Continuity semantic accept | `evaluate_librarian_proposal_continuity` | `outcome: accept`, `reason_code: accepted` | — | — | apply |
| Apply / durable write | `apply_issue_tension_pressure` | `applied: true`, `reason_code: applied|unchanged|already_applied` | `issue_pressure_semantic_overlays` | cross-turn until stale/resolved/superseded | scene_pressures projection |
| Persist | `SessionRepository.persist` | blocking on failure | `metadata.continuity_state` + audit in `v2_host_state` | session lifetime | Host reload |
| Project | `continuity_scene_pressure_projection` | freshness + fingerprint gates | manifest `scene_pressures` contribution | per inference call | Director/Character |

### Distinction map (do not collapse)

| Concept | Meaning |
|---------|---------|
| Proposal produced | LLM emitted `issue_tension_pressure` payload |
| Structurally accepted | Host validation passed |
| Semantically accepted | Continuity boundary `outcome: accept` |
| Mutation authorized | Continuity accept + apply path entered |
| Mutation applied | `apply_issue_tension_pressure.applied == true` |
| **Durable mutation (audit flag)** | `reason_code == "applied"` only (first material write this batch) |
| State persisted | `SessionRepository.persist` after finalize |
| State projected | `scene_pressures` includes overlay fields when projectable |
| State consumed | Downstream cognition uses projected fields (causal link hard to isolate per pressure) |

---

## 7. Forensic-field semantics

| Field | Authoritative meaning | Source |
|-------|----------------------|--------|
| `host_accepted` | Host `validate_host_proposal_batch.accepted` for batch | finalize result → evidence patch |
| `continuity_accepted_count` | Count of items with Continuity `outcome: accept` | `continuity_decision.accepted_count` |
| `durable_mutation_applied` | **Any** item with apply `reason_code == "applied"` (first material overlay write, not idempotent replay) | `apply_accepted_librarian_proposals` updates item decisions; audit metadata `post_commit_semantic_durable_mutation_applied` |
| `overlay_count_before/after` | Count of keys in `issue_pressure_semantic_overlays` | D-10 harness (when read from correct path) |

### Can `host_accepted: true` + `continuity_accepted_count: 1` coexist with `durable_mutation_applied: false`?

**Yes — legitimately in two cases:**

1. **Idempotent apply:** `reason_code: already_applied` or `unchanged` → `applied: true` but `durable_mutation_applied: false` (no new material write).
2. **Evidence patch gap:** apply returned `applied` with `reason_code: applied` but execution-evidence patch failed to read `continuity_decision` item flags (observed in D-10 attempts).

**Not** a violated invariant when (1) applies. D-10 universal false was primarily (2) plus harness read-path error, not proof of non-persistence.

---

## 8. `issue_tension_pressure` intended vs actual semantics

| Aspect | Intended (contract) | Actual (D-10 control sessions) |
|--------|---------------------|--------------------------------|
| Storage | `issue_pressure_semantic_overlays[issue_id]` | **Confirmed** in `metadata.continuity_state` |
| Durability | Cross-turn derived overlay | **Confirmed** — overlays survive session persist |
| Authority class | Derived/advisory (#200) | **Confirmed** — `semantic_authority.authority_class: derived` in projection tests |
| IssueState mutation | **Forbidden** | **Confirmed** — `IssueState` unchanged by apply |
| Plot store | Separate | **Confirmed** — Plot pressures in `_plot_cognition_overlay` sidecar |

---

## 9. `scene_pressures` provenance

**Creation path:** `project_scene_pressures_digest` / `project_character_scene_pressures` → `get_active_issues` → `get_projectable_issue_pressure_overlay` → `build_scene_pressure_entry`.

| Question | Answer |
|----------|--------|
| Reads `issue_pressure_semantic_overlays`? | **Yes** — via `get_projectable_issue_pressure_overlay` |
| Where populated? | `apply_issue_tension_pressure` during `finalize_librarian_proposals` |
| Persisted across commits? | **Yes** — in `metadata.continuity_state` |
| Regenerated? | Projection recomputed each manifest build; overlay store persists until stale/superseded |
| Derived from issues without Storyteller? | **Yes** — deterministic fallback: `blocked_what`, `required_next_step`, etc. without `semantic_unmet_condition` |
| Plot contributes to same projection? | **No direct join** — Plot uses separate overlay store; indirect via shared continuity/issues |
| Populated when post-commit ST disabled? | **Yes** — authoritative issue fields still appear; **LLM semantic overlay fields absent** |
| Unique ST information | `semantic_unmet_condition`, `stakes_summary` per issue (derived dramatic framing) |

---

## 10. Persistence / lifetime analysis

| Mechanism | Lifetime | Invalidation |
|-----------|----------|----------------|
| `issue_pressure_semantic_overlays` | Session-persistent | Issue resolved/not projectable; material fingerprint mismatch; Player authority freshness (#200); superseding proposal |
| `librarian_proposal_audit_log` | Session-persistent (`v2_host_state`) | Append-only per commit |
| Execution-evidence attempts | Investigation run | Not authoritative runtime state |
| Plot `unresolved_narrative_pressures` | Scope sidecar | Plot cognition update replan |

---

## 11. Consumer / projection analysis

| Consumer | Receives overlay semantics? | Evidence |
|----------|----------------------------|----------|
| Director | Yes — `scene_pressures` digest | `test_director_character_storyteller_receive_augmented_pressure` |
| Character | Yes — `scene_pressures` lane + precedence note (#200) | same test |
| Storyteller orientation | Yes — reads projected `scene_pressures` | same test |
| Plot cognition | **No direct read** of ST overlays | architecture consensus §4.4 |
| Narrator | **No** post-commit overlay lane in normal flow | architecture |

**Causal consumption:** Tests prove projection path exists. Per-pressure downstream decision attribution in live D-10 remains **indeterminate** (confounded by Plot, issue state, branch divergence).

---

## 12. Successful end-to-end historical examples

### Repository tests (authoritative)

- `test_valid_proposal_creates_active_overlay_outside_issue_state`
- `test_director_character_storyteller_receive_augmented_pressure`
- `test_service_finalize_records_issue_pressure_audit`
- `test_overlay_persists_round_trip`

### D-10 session files (existing evidence; read-only re-check)

| Session | Label | Overlays persisted | Audit `durable: true` entries | Apply `reason_code: applied` |
|---------|-------|-------------------:|------------------------------:|-----------------------------|
| `hg-session-b09c6fd7-…` | SEQ-D | **3** | **5** / 10 audits | 9 apply results (mix applied/already_applied) |
| `hg-session-a725b12d-…` | SEQ-E | **1** | **7** / 10 | 8 apply results |
| `hg-session-2a788143-…` | SEQ-C | **1** | **1** / 4 | 1 apply result |

**Conclusion:** Successful end-to-end apply → persist → overlay store **exists** in D-10 control evidence. Prior decode report's "zero durable overlays" conclusion was **forensically incorrect** due to read-path and evidence-patch gaps.

---

## 13. Why D-10 observed zero durable overlays (corrected)

| Observation | Actual cause |
|-------------|--------------|
| `overlay_count_after: 0` all turns | Harness read `session.continuity_manager` (absent) instead of `metadata.continuity_state` |
| `durable_mutation_applied: false` all 18 attempts | `buildPostCommitSemanticDecisionPatch` does not aggregate `continuity_decision.item_decisions[].durable_mutation_applied` |
| Decode "no durable mutation" narrative | Forensic interpretation error — **not** mechanism failure |

---

## 14. D-10 validity (two levels)

### Current-implementation validity — **VALID**

D-10 validly tested whether the **currently implemented** post-commit Storyteller pathway (produce → accept → apply → project) improves blind RP quality. Arms were correctly isolated (`skipLibrarianProposalGeneration` on ablated). Blind scores are unaffected by forensic misread.

**Result stands:** ablated arm scored higher (−0.23 overall) despite control arm successfully persisting overlays in several commits.

### Intended-function validity — **VALID (with interpretation shift)**

The **intended function** (durable derived issue-pressure semantics via post-commit assessment) **was operational** in control sessions. D-10 therefore tested whether that functioning mechanism improves RP — not merely a broken stub.

**Implication:** Negative marginal value is **not** explained by "pressure never persisted." It is explained by: functioning overlay path + Plot/authoritative issue pressure baseline **still** produced equal-or-better blind quality without post-commit ST inference.

---

## 15. Architectural-value consequence

| Finding | Consequence for #201 |
|---------|---------------------|
| Mechanism works as designed | Removes "broken stub" escape hatch — verdict targets **topology/value**, not accidental non-function |
| Overlays distinct from Plot | Does **not** support "semantically redundant" claim on schema alone |
| Ablated arm higher blind scores | Strengthens **remove/consolidate current topology** — incremental LLM overlay did not pay off in sample |
| Deterministic `scene_pressures` baseline remains without ST | Ablated arm retains issue-pressure digest minus LLM semantic overlay fields |
| Forensic gaps | Weakens **causal consumption** claims from D-10 evidence alone; does **not** invalidate blind endpoint |

**Governance framing:** Distinguish **remove broken current topology** (not indicated) from **remove low-marginal-value current topology** (indicated by blind endpoint + cost accounting).

---

## 16. Proposed component classifications (not final-selected)

| Component | Proposed classification | Notes |
|-----------|------------------------|-------|
| Storyteller preamble | Low demonstrated value (D-01-L); movable/deferrable candidate | Separate causal path |
| Storyteller post-commit **current mechanism** | **Strong remove/consolidate candidate** | Governance verdict §2; mechanism functions but did not help |
| Abstract post-commit narrative-pressure **function** | **Reassignable / optional** — not proven worthless, proven **low marginal value in current form** | Could be absorbed by Plot or deterministic continuity packaging |
| Plot cognition | Retained; session-persistent strategic pressures | Active both D-10 arms |
| Continuity pressure projection | **Core** — authoritative issues + optional derived overlay join | Survives ST removal with reduced semantic richness |

**Separation preserved:** valuable function ≠ historical component ≠ current mechanism ≠ current topology.

---

## 17. Production defect assessment

| Defect | Exists? | Materiality | Disposition |
|--------|---------|-------------|-------------|
| `apply_issue_tension_pressure` / persist broken | **No** | — | — |
| D-10 harness overlay read path | **Yes** (investigation artifact) | Invalidated D-10 pressure forensics only | Document; no fix authorized |
| `ni-evidence.mjs` durable flag patch | **Yes** (forensics) | Misreports `durable_mutation_applied` on inference attempts | Diagnose only; **no remediation Issue** unless Governance authorizes |
| Post-commit ST marginal value | Design outcome, not defect | Architectural | Governance verdict |

---

## 18. Remediation disposition

- **No production remediation authorized.**
- **No remediation Issue created** (per activation constraints).
- Forensic gaps may be noted in synthesis as investigation limitations; optional future hygiene work is Governance's call.

---

## 19. Synthesis-readiness recommendation

### **A. Evidence resolves the gap sufficiently — begin #201 synthesis.**

**Rationale:** The governing question is answered. H1 and H3 are rejected with high confidence. H2 explains D-10 forensic anomalies without invalidating the blind endpoint. Corrected understanding (overlays **did** persist; mechanism **did** function) **strengthens** the architectural verdict against the current topology rather than weakening it.

**Synthesis must incorporate:**
1. Accepted D-10 verdict (§2) with corrected causal mechanism understanding.
2. Distinction: functioning durable overlays ≠ demonstrated RP benefit.
3. Forensic limitations on per-pressure consumption claims.
4. No automatic repair-and-rerun requirement.

---

## 20. Unresolved uncertainty

| Item | Status |
|------|--------|
| Per-pressure causal consumption in live D-10 | Indeterminate |
| Whether overlay semantic fields changed Director/Character choices | Not isolatable from branch/Plot confounds |
| Ayame n=1 confirmatory weight | Low |
| Whether reassigned function (e.g., Plot-absorbed) would outperform ablated baseline | **Not tested** — out of D-10 scope |

---

## 21. Artifact disposition / durable record / Governance decision

| Artifact | Action |
|----------|--------|
| This record | Committed; Issue #201 comment |
| D-10 blind scores | Unchanged (`d36a023`) |
| D-10 decode synthesis | Superseded **only** for §13–§15 forensic conclusions; blind aggregates unchanged |
| Production code | Unchanged |

### Exact Governance decision required

1. **Accept** causal-gap adjudication (H2 primary; mechanism functional).
2. **Authorize #201 Package D synthesis** incorporating corrected durable-pressure understanding + accepted D-10 verdict.
3. **Decline or defer** forensic-hygiene remediation (harness read path, evidence patch) unless separately prioritized.
4. **Confirm** issue remains `investigating` until synthesis complete.

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
