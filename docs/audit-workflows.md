# Audit Workflows

This document turns important audit guidance into a shared repo procedure.

For artifact details, see [`docs/audit-workflows.md`](./audit-workflows.md) and [`docs/rp-data-layout.md`](./rp-data-layout.md). For optional **offline** `fact_spec.v1` post-processing (companion JSON, headless **`--fact-spec`**), see [`SCENARIO_VALIDATION_FRAMEWORK.md`](../SCENARIO_VALIDATION_FRAMEWORK.md) (simulation execution).

For turning audit findings into GitHub Issues (classification **bug** / **behavior** / **limitation**, evidence, re-test loop, heuristic caveats), see the same file → **Audit interpretation and issue tracking**, and `governance/rp-app/issue-tracking-workflow.md` (§A.1, §D).

**User callouts (GitHub #55 / #125 / #126):** In Streamlit, the surface is **minimal**—a callout **trigger** and an optional **operator** **note** only. Operators do **not** select artifact paths. **`artifact_refs`** and optional **`related_artifact_refs`** (same-turn sibling `*_full` links; **#126**) are **system-populated at save**. **Triage**, **review**, **promote**, and **dismiss** are **operator CLI** only, not Streamlit. Record operator findings during audited runs, then **triage in the operator CLI** and **promote to a tracked GitHub issue** (link recorded in `rp_audits` — not from Streamlit). Historical V1 operator CLI (`user_callout_review.py`) was removed M12.4; see **User callout artifacts** below and [`docs/rp-data-layout.md`](./rp-data-layout.md).

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
- **Continuation:** Existing Streamlit/session resume paths are unchanged; legacy `_round_index.json` files without top-level identity are accepted only when `_manifest.json` is present and aligned (see `AUDIT_DOCUMENTATION.md`).

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
- **Authored retrieval (standard eval):** On audited runs, check `_audit_summary.json` → **`retrieval_session`** when present. See [governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md](../governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md) and [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).
- **Perception / audibility:** for whisper or directed beats, compare this character's assembled prompt to the parsed `move` (`audibility`, `audience`, `dialogue`). Non-recipients must not see verbatim private dialogue in transcript or structured history.
- **`metadata.character_audit_v1`:** Derived dimensions are **advisory** and **non-authoritative**. Read **`_narrative.json`** and continuity first. Details: [governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md](../governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md) (*Character Audit v1*).

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
- **Layout reference:** [rp-data-layout.md](./rp-data-layout.md). Full artifact semantics: [governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md](../governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md).

## Relevant code areas for RP audits

Start with these modules under `v2/domain/modules/`:

- `continuity_manager.py`
- `perception_audibility.py`
- `turn_runner.py`, `turn_runner_turn.py`, `turn_runner_updates.py`, `turn_runner_audit.py`
- `app_turn_director.py`
- `orchestration_helpers.py`
- `prompt_builders.py`
- `response_validation.py`
- `audit_logger.py`

## Windsurf-only note

The repo also contains a Windsurf workflow at:

- `.windsurf/workflows/audit-continuity-review.md`

That file can remain as Windsurf automation, but this document is the shared procedure both Windsurf
and Cursor should follow.

## Semantic proposal evaluation (#243) — operator read discipline

**Normative detail:** [governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md](../governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md) → *Semantic proposal evaluation — operator read discipline (Issue #243-D)*.

**What this is:** Offline, observational semantic-proposal alignment evaluation over frozen corpora and replay helpers. Outputs include `corrected_category`, nested `legacy_lane`, and `limitations[]`. **Not** runtime truth. **Not** continuity authority. **Not** written into `_audit_summary.json`. **Not** a runtime gate.

**What this is not:** A substitute for reading `#233` `semantic_proposal_decision`, `scene_state_after`, or continuity commit evidence on live audit rows.

### When to use

- Interpreting #240 frozen corpus rows or #243 regression CLI output
- Explaining why investigation-era F-codes (F0–F7) disagreed with profile-scoped corrected categories
- Calibrating evaluator false-positive alignment — **not** filing runtime bugs from eval alone

### Read order (per judgment)

1. **`corrected_category`** — primary #243 output (`success`, `evaluator_defect`, `contract_limited`, `ambiguous_threshold`, `true_semantic_miss`)
2. **`limitations[]`** — profile scope, mapping caveats, disclaimers
3. **`legacy_lane`** — `legacy_f_code`, `legacy_f_code_label`, `legacy_taxonomy_status` (historical investigation context)
4. **`legacy_classifier_misflag`** — legacy overfire signal; **does not mean runtime failure**
5. **Runtime corroboration** — only if escalation still warranted

### Operator rules

| Rule | Detail |
|------|--------|
| Corrected category is primary | Use `corrected_category` for #243 evaluation; treat `legacy_lane` as secondary |
| Legacy F-codes are historical | F0–F7 explain old tooling; they are **not** primary contract-alignment truth |
| Misflag ≠ runtime bug | `legacy_classifier_misflag: true` means taxonomy/calibration — not automatic regression |
| Eval alone ≠ bug | Do **not** open a runtime defect from evaluator output without committed-state proof |
| Ambiguity is valid | `ambiguous_threshold` and `legacy_taxonomy_status: ambiguous` must not be forced to PASS/FAIL |
| No audit-summary merge | Evaluator judgments stay offline; do not treat them as `_audit_summary.json` fields |

### Runtime escalation checklist

Before treating an eval result as a runtime continuity or semantic-proposal bug, confirm **at least one** committed evidence path:

- [ ] `#233` **`semantic_proposal_decision`** on the relevant character `*_full.json` row
- [ ] **`scene_state_after`** / continuity state shows a durable violation inconsistent with the decision
- [ ] Accepted/rejected **`semantic_proposals`** records match the suspected miss
- [ ] **`_narrative.json`** / turn metadata corroborates net-state or participation change
- [ ] Issue/corpus context documented — calibration anchor, not runtime proof by itself

If offline eval says `true_semantic_miss` but runtime committed `no_covered_change` with coherent continuity, investigate **evaluator/threshold** alignment (#243 scope) — not continuity enforcement — unless committed state proves otherwise.

### CLI (from repository root)

```bash
python scripts/run_issue243_corpus_regression.py --eval
python scripts/run_issue243_corpus_regression.py --eval --summary --corpus willow_v1
python scripts/run_issue243_corpus_regression.py --legacy --corpus willow_v1
```

Baselines and field glossary: `python/data/evaluation/issue243_regression_baselines/README.md`.
