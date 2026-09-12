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

## Local artifact classes (repository hygiene)

Operators should distinguish four classes of local artifacts. This table records **repository treatment** only; it does not redefine forensic or audit semantics (see [audit-workflows.md](./audit-workflows.md) and upstream **Holy_Grail_RP #86** for `rp_audits/` retention).

| Class | Typical location | Git | Durable record |
|-------|------------------|-----|----------------|
| **Disposable workflow drafts** | `/tmp/` (Issue body/comment staging), `.github/issue_drafts/`, `.tmp_*` | Ignored | None — delete when done |
| **Reproducible harness summaries** | `v2/rp_runtime/tmp/` (Storyteller harness default); optional `data/investigation_runs/` via CLI path | Ignored | Governing GitHub Issue validation comment |
| **Final validation decisions** | Governing GitHub Issue thread | N/A (Issue) | Issue closure / validation record |
| **Raw campaign / runtime / forensic evidence** | `data/storyteller_tier1_campaign/`, `data/execution_evidence/`, `data/plot_cognition_forensics/`, `data/sessions/`, `data/rp_audits/` | Ignored (`data/*` with fixture whitelists) | On-disk trees under existing `data/*` policies |

**Agreed treatment (#69):** `/tmp/` is local disposable workflow staging (ignored). `v2/rp_runtime/tmp/` holds reproducible harness aggregate JSON (ignored; superseded copies may be deleted locally). Authoritative validation conclusions belong on the governing Issue, not in tracked repository files.

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

**`metadata.v2_host_state`:** `rp_history`, `commit_ids`, and per-entry `domain_commit_id` correlate producer inputs to promoted occurrences. **#164 runtime provenance** (durable after session save/reopen):

| Field | Schema | Role |
|-------|--------|------|
| `runtime_build_provenance` | `hg_runtime_build_provenance_v1` | Descriptive build/source metadata (repository slug/commit SHA, capture time, commit SHA source). Secrets excluded. |
| `runtime_effective_configuration` | `hg_runtime_effective_configuration_v1` | Append-only `epochs[]` of resolved effective configuration snapshots + `current_epoch_id`. Each epoch carries `epoch_id`, `effective_from` (`session_open` \| `settings_update` \| `round_options_override`), `effective_configuration_fingerprint` (SHA-256 over canonical resolved snapshot), `capture_status`, `unavailable_fields`, and bounded `resolved` settings. |
| `librarian_proposal_audit_log` | *(legacy container name)* | Terminal post-commit semantic audit entries keyed by `domain_commit_id`; canonical fields use `post_commit_semantic_*` + `semantic_producer_role`. Historical Librarian-era field names remain readable. |

Per-attempt **`request.inference_profile`** in execution evidence remains authoritative for actual model/provider/reasoning used. Session provenance epochs supply surrounding effective-configuration context; they do not override per-attempt inference truth.

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

**Continuity audit (#49; #89 sufficiency; #151 status):** `turn_metadata_by_index[turn].narrator_environment_audit` stores cognition status/reason, N1/N2/Librarian outcomes, post-mediation **`sufficiency_evaluations`**, **`environmental_response_obligations`**, Host establishment decisions (`decision_id`), and hard cognition failure records (`cognition_failed`) when the pipeline is unavailable. `baseline_sufficient` is authoritative only when `cognition_status=determined`.

### Plot Cognition Overlay (`_plot_cognition_overlay`) — #59

**Path:** `data/sessions/_plot_cognition_overlay/{plot_cognition_scope_id}.json`

**Authority:** Advisory Storyteller plot cognition **current state** only. **Not** Continuity truth, **not** round-local Model A, **not** forensic history. Session metadata persists `plot_cognition_scope_id` (defaults to `memory_scope_id` when not explicitly supplied).

**Contract:** [plot-cognition-overlay-persistence-contract.md](./plot-cognition-overlay-persistence-contract.md) (semantic types: [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md); initialization: [plot-cognition-initialization-contract.md](./plot-cognition-initialization-contract.md)).

**Blocked marker:** `{plot_cognition_scope_id}.blocked.json` records corrupt/unsupported blocked state after quarantine or schema failure so the scope is not silently treated as absent.

### Plot Cognition Forensic Chronicle (`plot_cognition_forensics`) — #64

**Path:** `data/plot_cognition_forensics/{plot_cognition_scope_id}/`

**Authority:** Append-only **historical** Plot Cognition semantic decisions and mutation forensics. **Not** operational Overlay truth, **not** Continuity, **not** a substitute for DSH execution evidence. Lifetime follows `plot_cognition_scope_id` (session delete does not remove the chronicle).

**Contract:** [plot-cognition-forensics-contract.md](./plot-cognition-forensics-contract.md)

**Layout:**

```text
data/plot_cognition_forensics/{plot_cognition_scope_id}/
  scope_manifest.json
  index.json                 # derived / rebuildable
  records/{record_id}.json   # authoritative append-only
  content/{artifact_id}.json
```

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
  .index-write.lock             # ephemeral exclusive lock for concurrent index mutations (#165)
  attempts/<evidence_id>.json
```

**Index concurrency (#165):** `index.json` mutations are serialized per session via an exclusive lock file at the mutation boundary so concurrent inference completions cannot lose entries or corrupt the derived index.

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
| `plot_cognition.by_round` / `by_commit` / `by_inference_kind` | Derived Plot Cognition inference navigation (#64; rebuildable) |
| `inference_health` (#114) | Rebuildable Level-2 inference-health aggregates (counts + rates by `inference_kind` else `role`; utilization only when configured ceiling exists) |
| `timing` (#158) | Rebuildable indexes: `by_operation`, `by_round` — evidence ids for lifecycle, spans, and inference attempts |
| `round_activity` (#158) | Per-round rollups: roles, inference kinds, token totals, ordered evidence references (no payload duplication). **Derived from authoritative attempts** — counts and token totals must reconcile with unique `evidence_ids`; re-indexing must be idempotent. |

**Inference timing (#158, observational):** Authoritative LLM duration lives on `inference_health.timing` with `measurement: dsh_session_turn_boundary` — elapsed wall time between paired DSH session events `turn/start` and `turn/end` for the turn opened by the ephemeral inference `followup()`. `timing_observed: false` records `unavailable_reason` and **must not** include `inference_wall_clock_ms`. Observed zero (`timing_observed: true`, `inference_wall_clock_ms: 0`) is valid only when both boundaries exist with identical event times. Substrate idle/`agent/status: idle` timing may appear only under `timing.diagnostics.idle_boundary` and is **not** authoritative. Forensic association fields: `dsh_turn`, `dsh_inference_session_id`, `turn_start_seq`, `turn_end_seq`, `started_at`, `ended_at` (DSH event times; distinct from `recorded_at` / `updated_at`).

**Execution spans (#158, #173):** Non-LLM orchestration intervals are stored as attempts with `correlation.role: execution_span` (`phase_id`, `span_id`, `parent_span_id`, `operation_id`, `hg_round_id`, `execution.started_at` / `ended_at` / `wall_ms`, optional `evidence_ids[]`). LLM duration is not duplicated on spans; link via `evidence_ids` to inference attempts.

**Orchestration causal graph (#173):** Round orchestration is expressed on **existing** `execution_span` records via additive `decision.orchestration_graph` (`hg_orchestration_graph_v1`): `node_kind` (`serial_phase` | `parallel_group` | `lane` | `join_barrier`), `graph_id`, optional `lane`, `barrier_index`, `predecessor_span_ids[]`, `join_member_span_ids[]`, `domain_commit_id`, `character_turn_index`. **Serial phases** cover round preamble (Storyteller cognition, Plot pending-work resume when executed), per-turn Director → Character prep → commit boundary, and turn-to-turn chaining. **Post-commit** fan-out/join (parallel lanes + join barriers) links from the commit boundary via authored `predecessor_span_ids`. Causal edges are **authored at execution time** — investigators must not infer causality from timestamp ordering alone. Critical path is **derived** from the graph plus authoritative timings with explicit `attribution_scope` (`post_commit_section` | `character_turn` | `round_internal` | `player_visible_operation`) and attribution confidence (`proven` | `bounded_partial` | `unavailable`). A `proven` result applies only to the named scope; larger scopes downgrade when the graph is incomplete (e.g. post-commit-only evidence cannot yield `proven` `character_turn`). **Player-visible latency** remains separate from `application_lifecycle` milestones (`operation_began` → `round_terminal_*`) for a real `operation_id`; direct `orchestrator.runRound` paths do not synthesize `operation_id`. Historical sessions without orchestration spans remain `bounded_partial` on timing alone. `round_timing_ms` on round results remains **ephemeral diagnostic** only — not EE authority and not persisted by #173.

**Application lifecycle (#158):** `correlation.role: application_lifecycle` records milestones including `operation_began` (Player-wait start: operation accepted and processing began, correlated by `operation_id`) through `round_terminal_succeeded` / `round_terminal_failed`.

**Inference health (#114, observational):** New inference attempts may include additive `inference_health` (`hg_inference_health_v1`) derived from the assembled request profile (`inference_profile.max_tokens`), model response usage/finish, and existing decision structural/lineage fields. **Utilization** is generation tokens constrained by the configured output ceiling (`outputTokens` + `reasoningTokens` when present) ÷ `max_tokens`; prompt/`inputTokens` and mixed `totalTokens` numerators are not used. Recovery is a **separate** dimension (`none` / `attempted` / `recovered` / `unrecovered`) and does not overwrite primary hard-exhaustion or structural-failure evidence when a later correction succeeds. A successful correction’s own `structural_valid` reflects the correction attempt only — primary parse errors remain lineage/recovery context. Continuity remains authoritative narrative truth; inference health never writes Continuity. Pre-#114 attempts lack `max_tokens` / `inference_health`; index rebuild treats missing ceilings as non-observable for utilization and does not fabricate classifications. Threshold/near-ceiling policy semantics are **out of scope** for v1.

Query via `python tools/investigation/list_execution_evidence.py <hg_session_id>` with `--chain`, `--role`, `--qa-target-role`, `--participation`, `--summary`, `--cite`, and `--inference-health` (see [audit-workflows.md](./audit-workflows.md)).

Plot Cognition chronicle (scope-keyed, not session-keyed): `python tools/investigation/trace_plot_cognition_forensics.py <plot_cognition_scope_id> timeline` — see [plot-cognition-forensics-contract.md](./plot-cognition-forensics-contract.md).

### Ephemeral round summary (`role_inference_summary`, #94)

`hg-round-orchestrator` `runRound` returns a bounded per-role summary (`director`, `character`, `narrator`) separating **provider inference execution** from **phase orchestration outcome**. Each entry is scoped to the **most recent role activity in the round**, not whole-round aggregate history; earlier activity remains in `scene_events` and durable execution evidence. The legacy `director_inference_session_id` round field may retain the last observed Director inference session even when the summary's latest Director activity was a bypass. Contract: [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md) → **DSH round result — `role_inference_summary`**.

Session JSON may include a lightweight pointer under `metadata.execution_evidence` when a store exists for that session.

**Default:** enabled for normal RP operation. Opt out with `HG_EXECUTION_EVIDENCE=off` (diagnostic loss). Override root with `HG_EXECUTION_EVIDENCE_DIR`.

**Interpretation:** [audit-workflows.md](./audit-workflows.md)

**Cleanup / retention:** Evidence trees are keyed by `hg_session_id` under `execution_evidence/`. Operators may delete a session's evidence tree manually (`ExecutionEvidenceStore.deleteSession()` exists; **not** wired to production session-delete). Deleting evidence does not corrupt canonical session JSON. No automatic pruning or session-delete-triggered cleanup. Pre-#15 sessions have no evidence (non-fatal).

**NI forensic contract (#45, forward-only):** Post-#45 attempts that participate in narrative-intelligence lineage carry `evidence_contract: hg_ni_forensics_v1` and `correlation.inference_kind` (additive; `role` unchanged). Structured NI outcomes live in `decision.character_orientation`, `decision.librarian_mediation`, `decision.storyteller_advisory`, and `decision.post_commit_semantic` (historical read: `decision.librarian_proposal`). Candidate disposition uses the complete mediation catalog in the attempt `request` plus ID-level fields in `decision.librarian_mediation` (`catalog_source_ids`, `selected_source_ids`, `retrieval_disposition`, `source_id_to_entry_id`); Librarian omission is derived as set difference — no arbitrary evidence-layer truncation. Derived navigation: `index.ni.by_round`, `index.ni.by_commit`, `index.ni.by_tag` (rebuildable; non-authoritative). Pre-#45 evidence is not backfilled.

**#164 post-commit semantic forensics:** Canonical writes use `decision.post_commit_semantic` on inference attempts. Eligibility skips without semantic LLM produce deterministic `post_commit_semantic_disposition` attempts (`correlation.role: post_commit_semantic_disposition`, `record_class: deterministic_disposition`, no `request`/`response`, excluded from utilization rollups). `index.ni.by_commit[domain_commit_id].semantic_disposition_evidence_id` links skip evidence; producer inference ids remain on the commit bucket when present.

**#164 effective-configuration correlation:** LLM inference attempts and deterministic disposition records may carry `correlation.effective_configuration_epoch_id` referencing `metadata.v2_host_state.runtime_effective_configuration.epochs[].epoch_id` that governed the round/attempt. Join session epoch snapshots for resolved settings fingerprint/context; join attempt `request.inference_profile` for actual model usage.

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
| `data/plot_cognition_forensics/` | No | Yes |
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
