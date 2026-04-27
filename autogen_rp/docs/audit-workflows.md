# Audit Workflows

This document turns important audit guidance into a shared repo procedure.

For artifact details, see `python/rp_app/AUDIT_DOCUMENTATION.md`. For optional **offline** `fact_spec.v1` post-processing (companion JSON, headless **`--fact-spec`**, **`run_fact_track_postprocess`**), see that file → **Offline fact tracking** and the repo-root **`SCENARIO_VALIDATION_FRAMEWORK.md`** (simulation execution).

For turning audit findings into GitHub Issues (classification **bug** / **behavior** / **limitation**, evidence, re-test loop, heuristic caveats), see the same file → **Audit interpretation and issue tracking**, and `governance/rp-app/issue-tracking-workflow.md` (§A.1, §D).

**User callouts (GitHub #55 / #125 / #126):** In Streamlit, the surface is **minimal**—a callout **trigger** and an optional **operator** **note** only. Operators do **not** select artifact paths. **`artifact_refs`** and optional **`related_artifact_refs`** (same-turn sibling `*_full` links; **#126**) are **system-populated at save**. **Triage**, **review**, **promote**, and **dismiss** are **operator CLI** only, not Streamlit. Record operator findings during audited runs, then **triage in the operator CLI** and **promote to a tracked GitHub issue** (link recorded in `rp_audits` — not from Streamlit). From `autogen_rp/python/`, run `python scripts/user_callout_review.py`. Authoritative contract (not restated here): `python/rp_app/AUDIT_DOCUMENTATION.md` **§6–§8**.

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

- **Audit artifacts are optional for runtime:** The live turn loop and **session save/resume** do not require `python/rp_app/data/rp_audits/` to exist. Treat **`python/data/sessions/*.json`** as the persistence bundle for continuity-backed resume (`continuity_state`, etc.); see [`docs/rp-data-layout.md`](./rp-data-layout.md) → **Persistence vs Audit Artifacts**.
- **Cleanup of `rp_audits/`** is permitted under agreed policy (see **Archival & retention policy** below and GitHub **[#86](https://github.com/KizzieFae/Holy_Grail_RP/issues/86)**). Deleting audit sessions does not corrupt saved UI sessions.
- **When diagnosing:** Confirm what **`ContinuityManager`** / persisted **`continuity_state`** actually committed (or what session JSON contains) **before** treating audit-only signals as proof of a runtime bug. Interpret audit files **after** that truth layer is clear.

## Artifact reading order

For session audits, read in this order:

1. `python/rp_app/data/rp_audits/session_{###}/_audit_summary.json`
2. `python/rp_app/data/rp_audits/session_{###}/_narrative.json`
3. `python/rp_app/data/rp_audits/session_{###}/_round_index.json`
4. relevant per-turn `_full.json` artifacts

## What to inspect first

- whether turns produce meaningful `state_changes`
- whether `actionable_implications` describe actual next pressure or opportunity
- whether `issue_updates` reflect pressure movement rather than dialogue paraphrase
- whether `presence_changes` match true entries, exits, and absences
- whether summary blocks preserve important context or hide it
- **Authored retrieval (standard eval):** On **audited** runs (Streamlit with audit enabled **or** headless `--audit`), check `_audit_summary.json` → **`retrieval_session`** (`retrieval_mode`, `retrieval_verified_active`, index path/fingerprint) when present; it is merged after **`write_summary_report`** via **`apply_retrieval_session_to_audit_summary`** (same helper for UI `refresh_audit_summary_report` and headless `run_headless_llm_scene`). On **any** audited character turn, `metadata` may include **`retrieval_summary`** (counts/refs only). See `python/rp_app/AUDIT_DOCUMENTATION.md` (*Authored index retrieval*) and repo-root `SCENARIO_VALIDATION_FRAMEWORK.md`.
- **Perception / audibility:** for whisper or directed beats, compare **this character’s** assembled prompt (or audit snapshot) to the **parsed `move`** (`audibility`, `audience`, `dialogue`). Non-recipients must not see verbatim private **`dialogue`** in transcript, structured moves, `PublicEvent.summary`, or interpretations; Director payload must use the same redaction rules.
- **`metadata.character_audit_v1`:** All **`derived`** dimensions (including **CA3** `issue_engagement` and **CA7** `pressure_move`) are **advisory** and **non-authoritative**. They measure **move-level expression / observability**, not story-truth: optional move fields drive the heuristics, so weak CA3 / CA7 readings are **expected** when structure is implicit on the move. Read **`_narrative.json`** and continuity **first**, then compare CA signals for **explicit vs implicit** encoding; mismatches **require cross-layer verification** (see `python/rp_app/AUDIT_DOCUMENTATION.md` → *Character Audit v1* → **Interpretation and Intended Use**).

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
- **Regenerate:** Produce new **`session_*`** trees by re-running headless simulation with **`--audit`** when baselines are missing or stale—do not edit existing audit JSON in place for that purpose (**#89**).
- **Delete-eligible:** Remove audit session directories only under explicit verification, backups, and policy (e.g. duplicate resolution with a retained canonical row, per **#86** / **#88**). **Do not** delete **`python/data/sessions/*.json`** as part of audit corpus cleanup.
- **Layout reference:** On-disk prefixes: [`docs/rp-data-layout.md`](./rp-data-layout.md) — **Persistence vs Audit Artifacts** and **Audit outputs**. Full semantics: [`python/rp_app/AUDIT_DOCUMENTATION.md`](../python/rp_app/AUDIT_DOCUMENTATION.md).

## Relevant code areas for RP audits

Start with these files when the audit points to runtime behavior:

- `python/rp_app/continuity_manager.py`
- `python/rp_app/perception_audibility.py`
- `python/rp_app/turn_runner.py`
- `python/rp_app/turn_runner_turn.py`
- `python/rp_app/turn_runner_updates.py`
- `python/rp_app/turn_runner_audit.py`
- `python/rp_app/app_turn_director.py`
- `python/rp_app/orchestration_helpers.py`
- `python/rp_app/prompt_builders.py`
- `python/rp_app/response_validation.py`
- `python/rp_app/audit_logger.py`

## Windsurf-only note

The repo also contains a Windsurf workflow at:

- `.windsurf/workflows/audit-continuity-review.md`

That file can remain as Windsurf automation, but this document is the shared procedure both Windsurf
and Cursor should follow.
