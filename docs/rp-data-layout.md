# RP data layout

On-disk **data** for Holy Grail RP. Canonical root: **`data/`** at repository root (`HG_DATA_DIR`). Override with `HG_DATA_DIR`; sessions may use `HG_SESSIONS_DIR`.

Artifact semantics (especially audits): [audit-workflows.md](./audit-workflows.md). Product strategy: [governance/sources/holy-grail-prd.md](../governance/sources/holy-grail-prd.md).

---

## Layout summary

```text
data/                           # HG_DATA_DIR
├── characters/                 # character cards (+ optional opener JSON)
├── scene_templates/            # scene template definitions
├── retrieval/                  # authored retrieval manifests; compiled index path is env-defined
├── fixtures/                   # tracked investigation / eval fixtures
│   └── progression_simulation_scenarios/   # scenario validation manifests
├── sessions/                   # persisted RP sessions (+ _session_index.json)
├── execution_evidence/         # V2 durable inference/decision evidence (local, gitignored)
├── audit_tags/                 # V2 human observational audit tags (local, gitignored)
└── rp_audits/                  # optional legacy/V1 per-turn audit trees (local, gitignored)
```

Local investigation output: `data/investigation_runs/` (gitignored).

---

## Character cards

**Path:** `data/characters/*.json`

**Contract:** [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md)

**Role:** Persona definitions — system prompt, personality, identity anchors, relationships, lore facts.

**Read by:** `v2/domain/character_cards.py`, `v2/domain/modules/scene_opener.py`, Host `session_setup.py`. The UI lists catalog entries via the Node application API; it does not load cards from disk.

**Written by:** Content authors / tooling outside the runtime turn loop. Cards are **operator-local** (gitignored); the repository does not ship private character data.

**Clean clone:** `data/characters/` is empty. The Streamlit UI warns that the catalog is unavailable and falls back to **prototype cast** mode (default cast name `Alice`) so you can create a session without adding cards. Add `*.json` files here when you want catalog-driven cast selection.

---

## Scene templates

**Path:** `data/scene_templates/*.json` plus template-associated support files per [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md) (openers, progression payloads).

**Role:** Premise, `role_slots`, `anchor_role_name`, logistics anchors (`sleeping_surface_slots`, `location_entry_slots`), optional `opening_text`.

**Read by:** `scene_template.py`, `scene_opener.py`, Host `session_setup.py`, `prompt_builders.py`.

Host `session_setup.py` is the production scene-start spine (same templates/openers as the UI, which only posts setup through the Node application API).

---

## Authored retrieval (offline)

**Manifest example:** `data/retrieval/authored_manifest.example.json`

**Compiled index:** Checked-in reference artifact `data/retrieval/compiled/operational_pilot_v3.json` (from `data/retrieval/manifests/operational_pilot.json`). Activate at runtime with `RP_RETRIEVED_CONTEXT_INDEX` or `HG_RETRIEVAL_INDEX_PATH`. There is **no** in-repository compile CLI today; regenerate indexes with external tooling if needed.

**Scope:** Pre-packaging ingestion only. Does not change continuity authority.

Historical pilot runbook (closed): [governance/records/operational-retrieval-pilot.md](../governance/records/operational-retrieval-pilot.md). Current validation procedure: [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Sessions

**Path:** `data/sessions/` (or `HG_SESSIONS_DIR`)

| Item | Description |
|------|-------------|
| `*.json` | One file per session id — team state, chat history, `character_states`, `continuity_state`, metadata |
| `_session_index.json` | Cached listing index (`SessionManager`) |

**Read by:** Host `SessionRepository` via domain `SessionManager`

**Written by:** `SessionManager.save_session` through Host `SessionRepository`

New sessions use opaque UUIDv4 filenames. Exact JSON keys follow code-defined serialization — not a stable public API.

**`continuity_state` (authoritative truth):** includes `public_events[]` (optional `occurrence_evidence` companion per Issue #51), `turn_metadata_by_index` (classifier/promotion observational record including `summary_selection_source`), `resolved_outcomes`, and related Continuity structures. This is the primary forensic substrate for occurrence-evidence lifecycle reconstruction — not a separate #51 audit log.

**`metadata.v2_host_state`:** `rp_history`, `commit_ids`, and per-entry `domain_commit_id` correlate producer inputs to promoted occurrences.

### Audit identity in `metadata`

| Subfield | Role |
|----------|------|
| `audit_session_owner` | Canonical audit identity for audit-supported sessions |
| `scene_owner` | UI / display context only — not a substitute for `audit_session_owner` |

Saves lacking `audit_session_owner` cannot be audited on load (no backfill from `scene_owner`).

When Scene Grounding is active, expect prompt-facing derived facts in metadata or continuity blobs per [scene-grounding-layer.md](./scene-grounding-layer.md).

### Story knowledge corpus (`_story_knowledge`) — #50

**Path:** `data/sessions/_story_knowledge/{memory_scope_id}/`

**Authority:** Searchable **derived evidence** projected from authoritative `PublicEvent` occurrences (and separately authorized derived records). **Not** continuity truth and **not** authored canon. Story execution does not mutate character/scenario authored sources.

| File | Role |
|------|------|
| `records.jsonl` | Append-oriented durable occurrence/derived records (`event_id` or `story_record_id`); occurrence rows may include `evidence_projection` (#51) |
| `manifest.json` | Record index offsets, schema version, index metadata (non-authoritative) |
| `semantic_index_v1.json` | Rebuildable TF-IDF semantic index (candidate discovery only) |

**Full architecture:** [story-knowledge.md](./story-knowledge.md). **Forensic record:** [governance/records/issue-50-story-knowledge-forensic-record.md](../governance/records/issue-50-story-knowledge-forensic-record.md).

**Lifecycle:** authoritative commit → session persist → occurrence projection → JSONL append → best-effort index update. Index failure is auditable and surfaces as Librarian `retrieval_failure`, not `no_match`.

**Precedence at mediation:** authored canon is the baseline where no applicable authoritative story knowledge supersedes it; legitimate story progression may govern current-state answers without rewriting authored sources.

**Environmental descriptor derived rows (#49):** `record_kind=derived`, `event_type=environmental_descriptor`, `grounding_markers` includes `environmental_descriptor`. Payload `committed_text` JSON carries `property_key`, `value`, `stable_refs`, optional `supersedes`. `epistemic_authority_ref` uses `establishment_decision` with Host `decision_id` (orchestration-only visibility by default). `related_refs` may include `supersedes` → prior `story_record_id`.

**Continuity audit (#49):** `turn_metadata_by_index[turn].narrator_environment_audit` stores N1/N2/Librarian outcomes, Host establishment decisions (`decision_id`), and cognition failure records (`cognition_failed`) when pre-finalize cognition is unavailable.

### Plot Cognition Overlay (`_plot_cognition_overlay`) — #59

**Path:** `data/sessions/_plot_cognition_overlay/{plot_cognition_scope_id}.json`

**Authority:** Advisory Storyteller plot cognition **current state** only. **Not** Continuity truth, **not** round-local Model A, **not** forensic history. Session metadata persists `plot_cognition_scope_id` (defaults to `memory_scope_id` when not explicitly supplied).

**Contract:** [plot-cognition-overlay-persistence-contract.md](./plot-cognition-overlay-persistence-contract.md) (semantic types: [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md)).

**Blocked marker:** `{plot_cognition_scope_id}.blocked.json` records corrupt/unsupported blocked state after quarantine or schema failure so the scope is not silently treated as absent.

---

## Execution evidence (`execution_evidence`)

**Path:** `data/execution_evidence/<hg_session_id>/` (gitignored generated trees)

**Role:** V2 durable forensic store for inference attempts. Each attempt records the **exact Holy-Grail-assembled model request** (`hg_assembled_request_v1`), final model response (`hg_model_response_v1`), decision/validation outcomes, retry chains, and correlation identifiers.

**Forward standard:** Normative forensic auditability requirements for new decision seams and information-flow architecture — [forensic-auditability-standard.md](./forensic-auditability-standard.md). This section records **retained-artifact contracts** only; it does not replace that standard.

**Authority:** Observational only. Canonical RP truth remains `data/sessions/*.json` (`rp_history`, continuity). Execution evidence explains **how** execution produced committed/presented state; it must not be treated as continuity authority.

**Layout:**

```text
data/execution_evidence/<hg_session_id>/
  index.json                    # semantic + participation navigation indexes
  attempts/<evidence_id>.json
```

**Forensic completeness contract (#28):** Sessions produced **after #28 lands** are expected to satisfy the post-#28 forensic contract below. Older pre-#28 session trees may remain on disk in historical form and are **not** required to satisfy this contract. There is no schema version gate and no historical migration/backfill.

**Canonical Director/Narrator semantic QA placement:** `decision.semantic_qa` on candidate attempts (not root-level `semantic_qa`). Includes `policy_action`, `evaluator_evidence_id`, findings, citation sidecars, and evaluation pass correlation.

**Character semantic evaluation:** unchanged — `decision.semantic_evaluation` (no `policy_action` symmetry).

**Participation-direct:** non-inference attempts with `correlation.role = participation`, bounded `decision.participation`, and bidirectional links to Character attempts (`associations.participation_evidence_id` / `associations.character_evidence_id`).

**Director eligibility:** bounded `decision.director.eligibility` on all Director candidate attempts; `decision.director.constraints` remains separate participation-policy input on accepted paths.

**Index navigation (derived, non-authoritative where noted):**

| Index key | Role |
|-----------|------|
| `semantic.evaluation_chains[inference_id]` | Candidate attempt ids per inference (all roles) |
| `semantic.qa_pass_chains[inference_id]` | Derived QA pass tuples `{candidate_evidence_id, evaluator_evidence_id, evaluation_pass_id, policy_action}` |
| `semantic.qa_by_target_role[role]` | Flat discovery of Director/Narrator QA candidate ids |
| `participation_by_round[hg_round_id]` | Participation-direct decision record ids |

Query via `python tools/investigation/list_execution_evidence.py <hg_session_id>` with `--chain`, `--role`, `--qa-target-role`, `--participation`, `--summary`, and `--cite` (see [audit-workflows.md](./audit-workflows.md)).

Session JSON may include a lightweight pointer under `metadata.execution_evidence` when a store exists for that session.

**Default:** enabled for normal RP operation. Opt out with `HG_EXECUTION_EVIDENCE=off` (diagnostic loss). Override root with `HG_EXECUTION_EVIDENCE_DIR`.

**Interpretation:** [audit-workflows.md](./audit-workflows.md)

**Cleanup / retention:** Evidence trees are keyed by `hg_session_id` under `execution_evidence/`. Operators may delete a session's evidence tree manually (`ExecutionEvidenceStore.deleteSession()` exists; **not** wired to production session-delete). Deleting evidence does not corrupt canonical session JSON. No automatic pruning or session-delete-triggered cleanup. Pre-#15 sessions have no evidence (non-fatal).

**NI forensic contract (#45, forward-only):** Post-#45 attempts that participate in narrative-intelligence lineage carry `evidence_contract: hg_ni_forensics_v1` and `correlation.inference_kind` (additive; `role` unchanged). Structured NI outcomes live in `decision.character_orientation`, `decision.librarian_mediation`, `decision.storyteller_advisory`, and `decision.librarian_proposal`. Candidate disposition uses the complete mediation catalog in the attempt `request` plus ID-level fields in `decision.librarian_mediation` (`catalog_source_ids`, `selected_source_ids`, `retrieval_disposition`, `source_id_to_entry_id`); Librarian omission is derived as set difference — no arbitrary evidence-layer truncation. Derived navigation: `index.ni.by_round`, `index.ni.by_commit`, `index.ni.by_tag` (rebuildable; non-authoritative). Pre-#45 evidence is not backfilled.

---

## Human audit tags (`audit_tags`)

**Path:** `data/audit_tags/<hg_session_id>/` (gitignored generated trees)

**Role:** V2 durable **human observational** markers for suspicious or interesting RP moments during play. Each tag (`hg_audit_tag_v1`) anchors to a visible transcript entry (`anchor.entry_id`) enriched with stable history correlation (`sequence_index`, `hg_round_id`, `domain_commit_id`, role/speaker flags). Optional forensic comments are stored separately from tag creation (tag-first, note-second).

**Authority:** Observational only. Tags must never enter `rp_history`, continuity, memory, perception, or model request assembly. Canonical RP truth remains `data/sessions/*.json`.

**Layout:**

```text
data/audit_tags/<hg_session_id>/
  index.json                    # hg_audit_tags_index_v1; tags_by_entry_id for idempotency
  tags/<tag_id>.json
```

**Idempotency:** At most one active tag per `(hg_session_id, entry_id)` through normal UI/API create. Repeated create returns the existing tag.

**Forensic enrichment (#45):** Optional `forensic_scope` on `hg_audit_tag_v1` records best-effort execution-evidence entry pointers at tag creation. Tag creation remains successful when evidence is disabled, unavailable, partial, or lookup fails; intrinsic anchors (`entry_id`, `hg_round_id`, `domain_commit_id`, `sequence_index`) remain authoritative. Dynamic re-resolution is Package B scope.

**Interpretation:** [audit-workflows.md](./audit-workflows.md)

**Cleanup / retention:** Tags persist until manually removed (`DELETE /api/audit-tags/{tag_id}` or delete tag files). No automatic pruning. Deleting execution evidence does not invalidate tags as pointers to canonical history. Tags remain meaningful when `HG_EXECUTION_EVIDENCE=off`.

**Historical note:** V1 **User Callouts** lived under `data/rp_audits/`; V2 audit tags use this separate store and join to #15 execution evidence instead of V1 `*_full.json` artifacts.

---

## Audit artifacts (`rp_audits`)

**Path:** `data/rp_audits/session_*` (gitignored generated trees)

**Role:** Optional per-turn investigation artifacts (`*_full.json`, summaries, manifests). **Not required** for session save/resume.

**Interpretation:** [audit-workflows.md](./audit-workflows.md)

**Cleanup:** permitted under agreed policy (GitHub #86). Deleting audit sessions does not corrupt saved UI sessions.

**Search tip:** gitignored trees may not appear in IDE search — confirm paths with filesystem listing.

---

## Fixtures

**Path:** `data/fixtures/`

Tracked JSON for investigation, evaluation, and scenario manifests. Scenario validation manifests: `data/fixtures/progression_simulation_scenarios/`.

---

## Environment variables

| Variable | Default | Role |
|----------|---------|------|
| `HG_DATA_DIR` | `<repo>/data` | Product data root |
| `HG_SESSIONS_DIR` | `<HG_DATA_DIR>/sessions` | Session persistence |
| `HG_EXECUTION_EVIDENCE` | `on` | Durable execution evidence (`off` disables writes) |
| `HG_EXECUTION_EVIDENCE_DIR` | `<HG_DATA_DIR>/execution_evidence` | Execution evidence root |
| `HG_AUDIT_TAGS_DIR` | `<HG_DATA_DIR>/audit_tags` | Human audit-tag store root |
| `RP_RETRIEVED_CONTEXT_INDEX` | unset | Compiled retrieval index path |
| `RP_EPISODIC_MEMORY` | product default | Episodic memory feature flag |

---

## Persistence vs audit artifacts

| Store | Required for resume | Gitignored |
|-------|---------------------|------------|
| `data/sessions/*.json` | Yes | No (tracked or local per operator) |
| `data/execution_evidence/` | No | Yes |
| `data/audit_tags/` | No | Yes |
| `data/rp_audits/` | No | Yes |

Trust **`continuity_state`** in session JSON and **`ContinuityManager`** at runtime before treating audit-only signals as proof of bugs.

---

## Related

- [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md)
- [MODULE_INDEX.md](../MODULE_INDEX.md) — session/Host persistence and symptom routing
- [governance/sources/audit-semantics.md](../governance/sources/audit-semantics.md) — program audit semantics
- [audit-workflows.md](./audit-workflows.md) — RP session-audit procedure and artifact layout
- [forensic-auditability-standard.md](./forensic-auditability-standard.md) — forward forensic auditability standard
