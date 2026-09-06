# Issue #136 Tier-2 Campaign Execution Evidence

**Date:** 2026-09-06  
**Issue:** #136 OPEN (`implemented`)  
**PR:** #137 OPEN  
**Pre-tooling head:** `b2c245cafd0635dbb4966137e11e7c5a9990efc9`  
**Tooling-bearing SHA:** `9d5d3277e7a5a80afb545d69df2563751fdb1757`  
**Execution SHA:** `9d5d3277e7a5a80afb545d69df2563751fdb1757` (no post-campaign code mutation)  
**#136 implementation SHA:** `f3852196395505b8077ab817a736c7e7eddef099`  
**Main anchor:** `9baf987cc3b29146e863447427b87379af94e4e0`

## Workflow

| Field | Value |
|-------|-------|
| Assigned weight | `standard` |
| Effective weight | `full` |
| Bootstrap | Full |
| Campaign design | AGREED / executed |
| `validated` transition | NOT performed |
| Merge / closure | NOT performed |

## Tooling delivered (`9d5d327`)

- `data/fixtures/issue136_tier2_fidelity/` — six truth fixtures, four validation cards, README
- `v2/rp_runtime/src/scenario-harness/issue136-fixture-truth.mjs`
- `v2/rp_runtime/src/scenario-harness/issue136-tier2-campaign.mjs`
- `v2/rp_runtime/scripts/run-issue136-tier2-campaign.mjs`
- `v2/rp_runtime/tests/issue136-tier2-fixture-truth.test.mjs`
- `v2/rp_runtime/tests/issue136-tier2-campaign-smoke.test.mjs`
- `governance/records/issue-136-tier2-campaign-spec.md`

Production inference proof (`f385219..HEAD`): **unchanged** for `character_context.py`, `director_context.py`, `live-inference-prompts.mjs`.

## Deterministic verification

- `issue136-tier2-fixture-truth.test.mjs` — **11/11 pass** (including smoke subset)
- `issue136-tier2-campaign-smoke.test.mjs` — **pass** (mock path, entitlement 3-round session sequence)

## Greptile gate (tooling SHA)

| Field | Value |
|-------|-------|
| Check run | `101559037892` |
| Head | `9d5d327` |
| Result | **SUCCESS** |
| Files reviewed | 31 |
| PR comments | 1 (P1 on pre-existing `governance/records/issue-136-llm-inference-prompt-corpus-evidence.md` stale evidence — **out of tooling scope**, not remediated) |
| Implementation findings on tooling | 0 actionable within authorized scope |

Historical Greptile on `b2c245c` superseded for final-candidate purposes.

## Safety guard

Derived ceiling (not hard-coded):

| Component | Value |
|-----------|-------|
| Campaign runs | 16 (15 controlled + sentinel) |
| Live character turns | 19 |
| Orchestrator rounds (incl. entitlement multi-round) | 19 |
| Base inference estimate | 266 |
| Margin (25%) | 69 |
| **max_inferences** | **343** |
| **max_runs** | **18** |

**Actual usage:** 16 runs, **116** live inferences, **stopped: false** (well under ceiling).

## Live execution configuration

| Role | Provider | Model | Reasoning |
|------|----------|-------|-----------|
| All live roles | `deepseek-official` | `deepseek-v4-flash` | `low` |

Campaign data: `data/issue136_tier2_campaign/live/2026-09-06T21-13-51-760Z/`  
Aggregate report: `v2/rp_runtime/tmp/issue136-tier2-live-report.json`

## Repetitions executed

All authorized repetitions attempted (16 runs total):

| Fixture | Reps executed |
|---------|---------------|
| A Stability | 3 |
| B Positive change | 2 |
| C Negative change | 2 |
| D Inaction | 3 |
| E Entitlement | 2 |
| F Action required | 3 |
| Sentinel | 1 |

## Stop conditions / infrastructure blockers

**Campaign-level stop triggered forensically (harness did not auto-halt):**

1. **Storyteller absent/degraded on every run** — `storyteller/orientation/finalize` HTTP 400: `dictionary update sequence element #0 has length 1; 2 is required` (same class of error as validation-card profile fields before fix; Storyteller path still fails with validation cards in live path).
2. **Character phase failures (15/16 fixture runs)** — `completion_reason: character_failure`; dominant audit: `character-knowledge-cognition` `orientation_finalize` → `schema_mismatch` (live model output omitted `move_schema_version: 2` and used non-canonical beat fields).
3. **Only partial success:** `136-T2-B-POS-CHANGE` repetition 2 completed 2 character turns (`no_eligible_actors`); seed turn + live Mara path. Storyteller still degraded.

**Not observed:** entitlement digit leaks (`9999`), safety-guard breach, production prompt mutation.

## Per-fixture summary (live)

| Fixture | Rep | Char turns | Completion | ST | Auto judgment |
|---------|-----|------------|------------|-----|---------------|
| A Stability | 1–3 | 0 | character_failure | degraded | ambiguous |
| B Pos change | 1 | 0 | character_failure | degraded | ambiguous |
| B Pos change | 2 | 2 | no_eligible_actors | degraded | ambiguous |
| C Neg change | 1–2 | 0 | character_failure | degraded | ambiguous |
| D Inaction | 1–3 | 0 | character_failure | degraded | ambiguous |
| E Entitlement | 1–2 | 0 | character_failure | degraded ×3 rounds | ambiguous |
| F Action required | 1–3 | 0 | character_failure | degraded | ambiguous |
| Sentinel | 1 | 0 | character_failure | degraded | n/a |

## Partial forensic anchor (B Pos change rep 2)

- Session: `hg-session-*` (see report JSON)
- Presentation excerpt preserved in `issue136-tier2-live-report.json`
- Storyteller: attempted, **not bound**
- Semantic QA / QA chains: not reliably captured due to early character_failure on most runs

## Campaign conclusion

Live Tier-2 semantic evidence is **insufficient for `validated` transition**. Infrastructure failures (Storyteller finalize 400, Character orientation schema mismatch) prevented the planned production-like path on nearly all runs. One partial fixture completion cannot support forensic campaign-level conclusions for #136 fidelity dimensions.

## Recommendation

**Remain `implemented`.** Return to Governance for:

- Infrastructure remediation (Storyteller orientation finalize with validation cards; Character live schema compliance) before re-authorizing live Tier-2 rerun.
- Do **not** merge PR #137 or transition #136 to `validated` on this evidence alone.

## #140 / #141

Not implemented (per authorization).

## Post-campaign drift

None — documentation-only record; no fixture/runner/production mutation after results.
