# Issue #142 — Storyteller Finalize Transport Repair

**Date:** 2026-09-06  
**Issue:** #142 OPEN → `implemented` (implementation cycle)  
**Base:** `9baf987cc3b29146e863447427b87379af94e4e0` (`main`)  
**Implementation branch:** `issue-142-storyteller-finalize-transport`

## Root cause

Storyteller orientation/assessment cognition forwards raw model strings to Host finalize when DSH parse fails (Character-parity pattern). Storyteller-only HTTP transport coerced those fields with `dict(...)`, causing `ValueError` → HTTP 400 before domain parsers could return structured `{ accepted: false, reason: ... }`.

## Transport invariant

For `POST /v1/storyteller/orientation/finalize` and `POST /v1/storyteller/assessment/finalize`, pass `orientation_result` / `assessment_result` through without `dict()` coercion. Missing/null/falsy values use Character-parity `body.get(field) or {}`. Semantic validation remains in `parse_storyteller_orientation` / `parse_storyteller_assessment`.

## Scope

| In scope | Out of scope |
|----------|--------------|
| `http_transport.py` orientation + assessment result pass-through | DSH parser / prompts / schema-wrapper adherence |
| Kernel type hints `dict \| str` | #136 Character response-contract |
| Deterministic HTTP + integration tests | Forensic enrichment (existing path sufficient) |
| Bounded live validation | #136 campaign rerun |

## Relationship to #136

#142 removes the Storyteller infrastructure blocker (HTTP 400 on parse-failure finalize). It does **not** validate #136 semantic behavior or authorize #136 implementation.

## Deterministic validation

| Command | Result |
|---------|--------|
| `python -m pytest v2/domain/tests/test_storyteller_finalize_transport.py v2/domain/tests/test_storyteller_s3a.py -q` | **26 passed** |
| `python -m pytest v2/domain/tests/test_storyteller_s3c_integration.py v2/tests/ -q --ignore=v2/tests/test_presence_descriptive_exit_regression.py` | **276 passed** |
| `node --test tests/storyteller-orientation-parse-failure.test.mjs tests/storyteller-round-integration.test.mjs tests/storyteller-c6-sequencing.test.mjs` (from `v2/rp_runtime/`) | **6 passed** |

## Live validation

| Field | Value |
|-------|-------|
| Test | `v2/rp_runtime/tests/storyteller-orientation-live-142.test.mjs` |
| Provider / model | `deepseek-official` / `deepseek-v4-flash` |
| Reasoning | `low` |
| Command | `node --test tests/storyteller-orientation-live-142.test.mjs` |
| Result | **pass** — no `dict(string)` / HTTP 400 transport signature |

## Forensic behavior (no enrichment required)

After pass-through fix, existing path records:

- Host `accepted: false` + authoritative `reason` (e.g. `schema_mismatch`)
- `buildStorytellerOrientationDecisionPatch` / advisory patch on assessment path
- Raw attempt text in execution evidence
- Round-level `hg/storyteller-skipped` with stage/reason
- No KAR / advisory package on orientation failure

## Greptile

Recorded separately in `governance/records/issue-142-pr*-greptile-review-2026-09-06.md` after PR open.

## Workflow

| Field | Value |
|-------|-------|
| Assigned | `standard` |
| Effective | `full` |
| Priority | P3 (unchanged) |
| Merge / close | NOT performed — await Governance validation authorization |
