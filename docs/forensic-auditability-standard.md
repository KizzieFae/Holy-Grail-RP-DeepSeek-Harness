# Forensic auditability standard (forward requirement)

**Status:** Established doctrine consolidated from Issues **#14–#28**, **#37**, **#45**, and **#46**; validated in runtime and tooling before this documentation pass (**#47**).

**Authority:** Normative forward architectural requirement for **RP runtime forensic reconstructability** — meaningful runtime decision-making and information-flow seams in Holy Grail RP.

**Not in scope (cite only; do not conflate):**

| Concern | Owner |
|---------|--------|
| Program / system quality audit semantics | `governance/sources/audit-semantics.md` |
| RP session-audit **procedure** (reading retained artifacts) | `docs/audit-workflows.md` |
| Committed narrative truth | Continuity / `data/sessions/*.json` |
| Issue filing, validation gates, workflow weights | `governance/sources/issue-tracking-workflow.md` |

Forensic evidence is **observational**. It explains how execution produced committed or presented state; it is **not** continuity authority.

---

## Historical provenance (consolidated)

This standard is **not** a new forensic architecture proposal. It codifies behavior already established through:

| Period | Issues | What was established |
|--------|--------|----------------------|
| Durable execution evidence | **#14**, **#15** | V2 `data/execution_evidence/` with exact assembled model requests and decision chains |
| Forensic completeness expansion | **#17–#28** (umbrella **#17**; closure **#28**) | Post-#28 forensic contract: semantic QA placement, participation-direct records, Director eligibility, derived navigation indexes |
| Decision provenance audit | **#37** | Gap analysis across decision provenance and manual auditability; remediation packaged as **#45** (evidence parity) and **#46** (investigator tooling) |
| NI forensic parity | **#45** | `hg_ni_forensics_v1` contract: mediation disposition, NI indexes, tag `forensic_scope` enrichment |
| Investigator tooling | **#46** | `trace_ni_forensics.py` and shared NI reconstruction library |

**Sequencing exception (#31–#42):** Some auditability work was **deliberately deferred** while unusually interdependent narrative-intelligence architecture (#31 Retrieval, #32 Storyteller, #34 Librarian, and related programs) was stabilized. That deferral was a **conscious sequencing exception**, not the default development pattern. The #31–#42 period did **not** fully meet the completed standard before **#45**/**#46** remediation; do not read history as if forensic parity existed before those Issues closed.

**Artifact contracts (operational detail, not redefined here):** post-#28 forensic completeness and post-#45 NI contracts in `docs/rp-data-layout.md`. Investigator reading order in `docs/audit-workflows.md` (including unified turn navigator quick start, #101).

---

## Development-time expectation

> **Auditability is normally part of architecture completion, not a later optional enhancement.**

When introducing a new **meaningful** semantic decision, inference path, information-flow seam, or authoritative mutation path, design and review should treat forensic evidence and an investigation path as part of the feature's **normal acceptance contract**.

Future work should **not** routinely require a separate #37-style forensic-parity remediation cycle after architecture delivery.

Implementation guardrails and change strategy: `docs/architecture.md`. Standing invariant pointer: `governance/sources/architecture-overview.md`.

---

## Proportionality

This standard applies to **meaningful** decisions and information-flow seams where later reconstruction matters for:

- behavior diagnosis
- quality analysis
- semantic evaluation
- authority changes
- cross-component influence
- debugging and auditing

**Do not** require heavyweight evidence for every trivial deterministic operation. Evidence depth should be **proportional** to the significance of the decision or seam.

---

## Forward standard

For a **retained** run (artifacts on disk after process restart), an investigator should be able to reconstruct — **where applicable** and **where evidence was captured** — the following dimensions.

### 1. Forensic reconstructability

- what happened
- ordering and causal relationships
- which component invoked or influenced which other component
- what information each relevant component actually received
- what candidates, options, or information were available
- what was selected
- what was omitted
- what was transformed or projected
- what crossed each material architectural seam
- what reached the actual model request / context
- what candidate outputs, evaluations, or corrections occurred
- what final decision or result followed
- what committed to authoritative state
- what relevant post-commit processing occurred

### 2. Decision provenance

Meaningful decisions should preserve enough evidence to determine — where applicable:

- decision identity / type
- inputs / context
- actual decision, result, or disposition
- rationale or semantic output where relevant
- correlations to upstream / downstream activity
- authoritative outcome

**IDs and pointers alone are insufficient** when semantic content is necessary to understand what occurred.

### 3. Positive and negative lineage

Evidence design should support:

- **Positive lineage:** where information propagated.
- **Negative lineage:** where information stopped or was omitted.

Negative lineage should identify the **evidence-backed owning seam** where possible. **Do not infer responsibility merely from downstream absence.**

Example (NI, post-#45): Librarian omission derived as set difference between mediation catalog and selected source IDs — not inferred from missing downstream text alone.

### 4. Actual semantic content

Where semantic information matters to forensic interpretation, preserve or reference the **actual text / content** that participated in the decision.

Avoid replacing semantic evidence with identifiers that cannot reconstruct what the component actually saw (for example assembled model request contributions in `hg_assembled_request_v1`).

### 5. Actual model context

Where model inference is involved, forensic evidence should make it possible to determine what material **actually reached** the retained model request / context.

Distinguish:

- **Recorded presence / absence** (evidence-backed)
from
- **Semantic understanding, adequacy, or appropriate use** (investigator judgment)

The standard requires observability of what reached the model context, not automated judgment of whether that context was "good enough."

### 6. Restart durability

Required forensic reconstruction must **survive process restart** using retained artifacts under `data/` (see `docs/rp-data-layout.md`).

Do not make essential reconstruction depend solely on transient in-memory state.

### 7. Human audit tags

Human scene / audit tags (`data/audit_tags/`) are durable **observations** and useful forensic **entry points**.

- Tag creation must **not** depend on successful forensic enrichment.
- Where evidence exists, investigators should be able to navigate from the observation toward relevant causal / information-flow evidence (`forensic_scope` entry points, round/commit anchors, NI indexes — see `docs/audit-workflows.md`).

### 8. Non-duplication

Forensic completeness does **not** require copying the same semantic payload into every persistence surface.

Prefer:

- one authoritative evidence artifact
- stable associations
- deterministic pointers
- derived / rebuildable indexes (non-authoritative)

Do not create competing semantic truth stores merely for convenience.

### 9. Evidence versus authority

Forensic evidence records what occurred during execution. It must **not** become a competing narrative or Continuity authority merely because it is detailed.

Canonical RP truth remains session JSON and Continuity commits. Evidence explains **how**; continuity defines **what is true**.

### 10. Honest incompleteness

When retained evidence is missing, pre-contract, expired, disabled, or incomplete, investigation tooling and procedures must **report that limitation**.

**Do not convert:**

`not observable`

into:

`did not happen`.

Examples: `HG_EXECUTION_EVIDENCE=off`; pre-#28 or pre-#45 session trees; NI views reporting `ni_contract_unavailable`; tag valid without execution evidence; pre-#114 attempts lacking configured `max_tokens` / `inference_health` (utilization and some recovery classifications are **not observable**, not “healthy”).

---

## Retained artifact surfaces (operational reference)

| Store | Role | Layout detail |
|-------|------|----------------|
| `data/execution_evidence/` | Durable inference / decision forensic store | `docs/rp-data-layout.md` |
| `data/audit_tags/` | Human observational entry points | `docs/rp-data-layout.md` |
| `data/sessions/` | Authoritative committed truth | `docs/rp-data-layout.md` |

### Issue #51 occurrence-evidence reconstruction substrate

No separate #51 audit log is required. Investigators reconstruct the committed-occurrence lifecycle through **stable joins** across existing durable stores:

| Substrate | Category | Join keys |
|-----------|----------|-----------|
| `continuity_state.public_events[]` | **Authoritative truth** | `event_id`, `turn_index` |
| `continuity_state.turn_metadata_by_index` | **Observational audit metadata** | `continuity_turn_index`; includes `summary_selection_source` |
| `metadata.v2_host_state.rp_history` | Producer / user history | `domain_commit_id`, `entry_id`, `sequence_index` |
| `_story_knowledge/.../records.jsonl` | **Derived searchable evidence** | `event_id`, `source_domain_commit_id`, `content_hash` |
| `semantic_index_v1.json` | **Rebuildable index** | `record_id` |

**Explicit audit projections (#51 remediation):**

- **`summary_selection_source`** — which semantic branch selected the promoted `PublicEvent.summary` (`character_action`, `character_dialogue`, `character_action_and_dialogue`, `director_environment`, `state_change_fallback`, `default_fallback`, `grounding_markers`).
- **`evidence_projection`** on occurrence JSONL rows — which globally eligible PublicEvent components composed `committed_text` (`projection_sources`), plus safe flags when scoped evidence existed but was not globally projected.

Procedure: [audit-workflows.md](./audit-workflows.md).

### Issue #49 environmental cognition reconstruction

Distinguish **Narrator proposal**, **Host establishment decision**, **persisted B2 truth**, and **presentation**:

| Stage | Durable artifact | Join keys |
|-------|------------------|-----------|
| EnvironmentalCurrentView | Derived at prepare time; snapshot in manifest lane / audit | `location_ref`, `memory_scope_id` |
| N1 assessment | `turn_metadata_by_index[].narrator_environment_audit.n1` | `cognition_id`, `domain_commit_id` |
| Librarian mediation | audit `librarian_queries[]` (`mediation_outcome`, optional `composed_grounding`); execution evidence `decision.environment_cognition` on Narrator attempts | `need_id`, `request_id` |
| Sufficiency (#89) | audit `sufficiency_evaluations[]` | `need_id`, `response_sufficient`, `sufficiency_state` |
| Presentation obligation (#89) | audit `environmental_response_obligations[]`; manifest `environmental_response_obligation` lane | `obligation_id`, `render_behavior` |
| N2 resolution | audit `n2_resolutions[]` | `need_id`, `category`, `response_sufficient` |
| Host B2 acceptance | audit `establishment_decisions[].authority_decision` | `decision_id`, `authorized` |
| Persisted B2 | `_story_knowledge/.../records.jsonl` | `story_record_id`, `decision_id` (via `epistemic_authority_ref`) |
| Render / QA | execution evidence Narrator attempts; semantic QA `nar_environmental_*` dimensions | `domain_commit_id`, `cognition_id` |

**Cognition failure:** When DSH environmental cognition fails before finalize, `narrator_environment_audit.cognition_failed=true` (via `prepareNarratorContext` failure payload) and `decision.environment_cognition` on the Narrator attempt record the failure without granting invention authority.

**Narrator F1 fidelity retry (#93):** Bounded two-attempt fidelity retry preserves per-attempt request/response, `decision.fidelity_correction` (intended correction), next-attempt `semantic_correction` contribution (consumed correction), and post-persistence `decision.terminal_presentation` join. Investigator procedure: [audit-workflows.md](./audit-workflows.md) → Narrator F1 fidelity retry.

Investigator procedure and CLI helpers: `docs/audit-workflows.md`, `tools/investigation/README.md`.

---

## Related

- `governance/sources/architecture-overview.md` — standing architectural invariants
- `docs/architecture.md` — implementation guardrails and validation modules
- `docs/core-operating-invariants.md` — operator summary
- `SCENARIO_VALIDATION_FRAMEWORK.md` — scenario-grade validation framing (complementary, not a substitute for forensic evidence design)
