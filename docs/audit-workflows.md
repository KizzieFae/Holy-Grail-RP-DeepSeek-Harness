# Audit Workflows

RP **session-audit procedure** for Holy Grail RP: how to read canonical session state, V2 `data/execution_evidence/` artifacts, and legacy `data/rp_audits/session_*` trees; diagnose layer ownership; and follow retention policy.

**Not in scope:** program/system quality audit semantics (finding classes, disposition, audit closure) — see **`governance/sources/audit-semantics.md`**. Remediation Issue filing — see **`governance/sources/issue-tracking-workflow.md`** (§A.1, §D–§I).

For artifact layout, see [`docs/rp-data-layout.md`](./rp-data-layout.md). For optional **offline** `fact_spec.v1` post-processing, see [`SCENARIO_VALIDATION_FRAMEWORK.md`](../SCENARIO_VALIDATION_FRAMEWORK.md).

## When to use this

Use this workflow for:

- RP continuity drift
- weak story progression
- stalled scenes
- selection or soft-dropout issues
- false validation or presence behavior
- render-layer anomalies

## Audit posture

- Start from the assumption that visible failure may be downstream of earlier signal loss.
- Do not default to Director prompt edits.
- Prefer the smallest correct fix at the correct layer.
- Do not propose new subsystems unless the user explicitly asks for them.

### Canonical truth vs forensic evidence

1. Read `data/sessions/<hg_session_id>.json` — continuity and `rp_history` define **what is true**.
2. Read `data/audit_tags/<hg_session_id>/` when the operator flagged moments during play — defines **which visible outputs warrant investigation** (`hg_audit_tag_v1`, optional human comment).
3. Read `data/execution_evidence/<hg_session_id>/index.json`, then relevant `attempts/<evidence_id>.json` files — define **how inference/decisions produced that truth**.
4. Legacy V1 trees under `data/rp_audits/session_*` are historical only; they are **not** the live V2 forensic mechanism.

### V2 human audit-tag workflow

During RP, the operator tags specific visible transcript entries (Streamlit **Tag** control). Tag creation is immediate and does not require a comment. Optional notes are added afterward.

**Reading order for a flagged moment:**

1. `data/audit_tags/<hg_session_id>/index.json` → locate `tag_id` / `tags_by_entry_id`
2. `tags/<tag_id>.json` → read `anchor.entry_id`, optional `comment`
3. Resolve `anchor.entry_id` in session JSON `rp_history`
4. Use `anchor.hg_round_id` / `anchor.domain_commit_id` to join #15 execution evidence (when present)

CLI helper: `python tools/investigation/list_audit_tags.py <hg_session_id>`

**Idempotency:** Normal create is one tag per transcript entry per session. Repeated Tag clicks return the existing tag.

**Evidence-disabled:** Tags remain valid pointers to canonical history when execution evidence is off or manually deleted; `list_execution_evidence.py` reports absence without invalidating the tag.

### V2 execution evidence reading order

For post-hoc model/orchestration reconstruction:

1. `data/execution_evidence/<hg_session_id>/index.json`
2. Round-filtered attempt ids from `rounds[<hg_round_id>]`
3. Each `attempts/<evidence_id>.json`:
   - `request` (`hg_assembled_request_v1`) — exact Holy-Grail-assembled model request
   - `response` (`hg_model_response_v1`) — final assembled model output
   - `decision` — parse/validation/accept/reject/retry outcome
   - `correlation` / `associations` — join to commits and presentation

CLI helper: `python tools/investigation/list_execution_evidence.py <hg_session_id>`

**Causal-chain investigation (#28):** Prefer role workflow flags over raw index topology:

| Path | CLI starting point |
|------|-------------------|
| Character | `--chain character --round <hg_round_id>` |
| Director | `--chain director --round <hg_round_id>` or `--inference-id <id>` |
| Narrator | `--chain narrator --round <hg_round_id>` |
| Participation-direct | `--chain participation --round <hg_round_id>` or `--participation --round <hg_round_id>` |

Use `--summary` for human-readable blocks and `--cite <evidence_id>` to resolve finding `ref_id` → bounded authority-reference text from evaluator `request.contributions`.

**Director/Narrator semantic QA on attempts:** read `decision.semantic_qa` (includes `policy_action`). Follow `evaluator_evidence_id` for evaluation-time authority-reference snapshots.

**Participation-direct:** read `correlation.role = participation` records before inferring Director chains. No Director or semantic-evaluator attempts should exist for that selection.

**Retention:** Local forensic store only. Default-on capture; opt out with `HG_EXECUTION_EVIDENCE=off`. No streaming-chunk or mandatory reasoning capture. Reasoning is optional when the provider supplies it. Manual evidence deletion is supported; there is no automatic pruning and no production session-delete hook that removes evidence trees.

**NI lineage (#45, post-`hg_ni_forensics_v1` evidence only):**

1. Tag → `forensic_scope.evidence_entry_points` (or intrinsic anchors → `index.ni.by_round` / `by_commit`)
2. Character chain: `character_orientation` → `librarian_mediation` → `character_move` (via `associations` / `index.ni`)
3. Mediation disposition: `decision.librarian_mediation.catalog_source_ids` vs `selected_source_ids` (omission = set difference; catalog text in `request`)
4. Retrieval boundary: `decision.librarian_mediation.retrieval_disposition[*].candidate_ids_returned`
5. Consumer packaging: `associations.packaging_disposition` on Director/Character attempts
6. S4: `librarian_proposal` decision + `index.ni.by_commit[domain_commit_id]`

**Package B CLI (#46):** `python tools/investigation/trace_ni_forensics.py <hg_session_id> <view>`

| View | Command |
|------|---------|
| Whole-run map | `session` |
| Round NI activity | `round <hg_round_id>` |
| Tag-driven | `tag <tag_id> [--resolve]` |
| Mediation disposition | `mediation [--evidence-id <id>]` |
| Storyteller influence | `storyteller [--round <id>]` |
| Character context | `character` |
| S4 chain | `s4 <domain_commit_id>` |
| Source lineage (disposition discovered) | `lineage --source-id <id>` |

Use `--json` for `hg_ni_investigator_v1` machine output. Use `--rebuild-index` for in-memory `index.ni` rebuild (never persisted).

Handoffs: `list_execution_evidence.py --ni`; `list_audit_tags.py --tag <id>`.

Pre-#45 sessions: best-effort only; NI views report `ni_contract_unavailable`.

### Audit artifacts vs runtime (operational note)

- Audit artifacts are optional for runtime. Session persistence: `data/sessions/*.json` — see [rp-data-layout.md](./rp-data-layout.md).
- **Cleanup of `rp_audits/`** is permitted under agreed policy (see **Archival & retention policy** below and GitHub **[#86](https://github.com/KizzieFae/Holy_Grail_RP/issues/86)**). Deleting audit sessions does not corrupt saved UI sessions.
- **When diagnosing:** Confirm what **`ContinuityManager`** / persisted **`continuity_state`** actually committed (or what session JSON contains) **before** treating audit-only signals as proof of a runtime bug. Interpret audit files **after** that truth layer is clear.

### Audit paths and search tools (false-negative guard)

Session audits live under `data/rp_audits/session_*` and are **gitignored generated artifacts**. **Do not use Cursor Glob / default codebase search alone** to decide whether `session_{NNN}` exists: those tools often **omit gitignored trees**, which produces **false negatives**.

**Required habit:** confirm existence with a **filesystem listing** or a **direct read** of a known file path (e.g. from callout `artifact_refs` or an investigation brief). Only after that should investigations report that an audit tree is missing.

### Session folder integrity (Issue [#212](https://github.com/KizzieFae/Holy_Grail_RP/issues/212))

- **Exclusive claim:** New audited runs allocate `session_{###}` with an atomic folder claim under `rp_audits/` (parallel processes cannot share the same new folder).
- **Identity agreement:** `_manifest.json`, `_narrative.json`, and `_round_index.json` must carry matching **`session_owner`** and **`session_number`** before writes append; mismatch raises **`AuditSessionIntegrityError`** (fail loud).
- **No silent repair:** Corrupted or mismatched trees are **not** auto-healed—operators archive or delete bad folders and re-run.
- **Continuation:** Existing Streamlit/session resume paths are unchanged; legacy `_round_index.json` files without top-level identity are accepted only when `_manifest.json` is present and aligned (see **Artifact reading order** below).

## Artifact reading order

For session audits, read in this order:

1. `data/rp_audits/session_{###}/_audit_summary.json`
2. `data/rp_audits/session_{###}/_narrative.json`
3. `data/rp_audits/session_{###}/_round_index.json`
4. relevant per-turn `_full.json` artifacts

## What to inspect first

- whether turns produce meaningful `state_changes`
- whether `actionable_implications` describe actual next pressure or opportunity
- whether `issue_updates` reflect pressure movement rather than dialogue paraphrase
- whether `presence_changes` match true entries, exits, and absences
- whether summary blocks preserve important context or hide it
- **Authored retrieval (standard eval):** On audited runs, check `_audit_summary.json` → **`retrieval_session`** when present. See [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).
- **Perception / audibility:** for whisper or directed beats, compare this character's assembled prompt to the parsed `move` (`audibility`, `audience`, `dialogue`). Non-recipients must not see verbatim private dialogue in transcript or structured history.
- **`metadata.character_audit_v1`:** Derived dimensions are **advisory** and **non-authoritative**. Read **`_narrative.json`** and continuity first. Do not treat missing or noisy CA dimensions as continuity defects without corroboration.

For issue updates, pay special attention to:

- `pressure_kind`
- `blocked_what`
- `required_next_step`
- `status_reason`

## Diagnosis order

Use the same layer order as `docs/architecture.md`:

1. continuity and state representation
2. **perception / audibility** (`perception_audibility.py` and prompt assembly) when the failure is impossible knowledge or leaked private lines
3. **scene grounding** (settled-facts projection vs continuity) when the failure is repeated logistics or missing/stale SETTLED SCENE FACTS
4. issue lifecycle and orchestration state
5. summary retrieval and compression
6. validation and enforcement
7. Director logic
8. Narrator rendering

## Archival & retention policy

**Authoritative policy thread:** [GitHub #86](https://github.com/KizzieFae/Holy_Grail_RP/issues/86). This section does not duplicate the full policy text; it aligns documentation with that issue and with operational execution tracked on **[#88](https://github.com/KizzieFae/Holy_Grail_RP/issues/88)** / **[#89](https://github.com/KizzieFae/Holy_Grail_RP/issues/89)**.

- **Baseline matrix:** Scenario coverage and **OFF** / **ON** (where applicable) / **post-contract** audit-summary expectations for validation live in **[`SCENARIO_VALIDATION_FRAMEWORK.md`](../../SCENARIO_VALIDATION_FRAMEWORK.md)** (repo root). Post-contract rows should include **`continuity_observability_summary_v1`** in **`_audit_summary.json`** when continuity-backed rollup is emitted (Issue **#79**), not **`continuity_observability_status_v1`** alone.
- **Baseline registry:** Pre- and post-cleanup inventories use a **baseline registry** artifact and slot verification so **delete-eligible** work does not remove sole remaining scenario coverage or referenced sessions (per **#86** consensus and **#88** execution records).
- **Regenerate:** Produce new **`session_*`** trees by re-running supervised simulation with audit enabled when baselines are missing or stale.
- **Delete-eligible:** Remove audit session directories only under explicit verification and policy. **Do not** delete **`data/sessions/*.json`** as part of audit corpus cleanup.
- **Layout reference:** [rp-data-layout.md](./rp-data-layout.md). Per-turn file meanings: **Artifact reading order** and **Relevant code areas** in this document.

## Relevant code areas for RP audits

Start with:

- `v2/domain/modules/continuity_manager.py`
- `v2/domain/modules/perception_audibility.py`
- `v2/domain_api/kernel.py` (`commit_move`, `prepare_*`)
- `v2/domain_api/session_history.py`
- `v2/rp_runtime/src/plugins/hg-round-orchestrator/`
- `v2/rp_runtime/src/plugins/hg-phase-executors/`
- `v2/rp_runtime/src/plugins/hg-trace-emitter/`
- `v2/domain/modules/prompt_builders.py`
- `v2/domain/modules/response_validation.py`

## Windsurf-only note

The repo also contains a Windsurf workflow at:

- `.windsurf/workflows/audit-continuity-review.md`

That file can remain as Windsurf automation, but this document is the shared procedure both Windsurf
and Cursor should follow.

## Historical offline eval baselines (#243)

Frozen investigation corpora and baseline JSON under `data/fixtures/evaluation/` may include **historical** semantic-proposal evaluation artifacts. Those are **not** runtime gates and **not** current bootstrap paths. When interpreting such rows offline: treat `corrected_category` as the primary eval output; require committed-state corroboration before filing runtime defects. See `governance/sources/audit-semantics.md` for program-audit finding rules when promoting conclusions to tracked work.
