# Issue #201 — LH-1A SEQ-A Structural Correction Remediation

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** `consensus_reached` (unchanged)  
**Subphase:** LH-1A execution-blocker remediation and SEQ-A restart  
**Workflow weight:** `full` / `full`

## T11 forensic conclusion (accepted)

Original SEQ-A Attempt 1 failed at T11 after three Character candidate attempts exhausted deterministic ingress validation. Character inference completed normally; Narrator never invoked. Classification: repeated model output-schema non-compliance with correct deterministic rejection.

**Forensic session (preserved, unchanged):** `hg-session-a1bd723c-a81f-42d4-857b-c1ec2191b56b`  
**Evidence root:** `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-03-03-444Z/`

| Attempt | Failure |
|---------|---------|
| 0 | Missing `move_schema_version` → `parse_error` |
| 1 | Added `move_schema_version: 2`; beats missing `type` → `invalid beat type: None` |
| 2 | Same missing beat `type` |

## Governance remediation decision (accepted)

Authorize **bounded correction-context enrichment only** on Character validation-driven retries. Do not relax ingress validation, normalize malformed moves, or infer missing beat types deterministically.

## Implementation

**Narrowest hook:** `v2/rp_runtime/src/plugins/hg-phase-executors/character-phase.mjs` — objective validation retry path only.

**New module:** `v2/rp_runtime/src/lib/character-structural-correction.mjs`

When `validation_class === 'parse_error'` and `retryable === true`, and the rejection reason matches:

- missing/invalid `move_schema_version`
- missing/invalid beat `type` (`invalid beat type`)

…the retry `correction_context` now includes canonical v2 repair guidance derived from `character_move_response_contract.py` (`CANONICAL_EXEMPLAR` field names):

- `required_move_schema_version: { "move_schema_version": 2 }`
- `required_beat_structure_examples.action: { "type": "action", "action": "..." }`
- `required_beat_structure_examples.speech: { "type": "speech", "dialogue": "..." }`
- `structural_repair_instruction` / `structural_repair_guidance` (repair-only; no narrative/story/evaluator content)

Successful first attempts unchanged. Retry budget unchanged (`liveMaxAttempts: 3`). Ingress validator unchanged.

**Tests:** `v2/rp_runtime/tests/character-structural-correction.test.mjs` (13 assertions covering all authorized minimums).

## Pre-restart verification

| Check | Result |
|-------|--------|
| LH-1A preflight | **35/35 PASS** |
| Structural correction tests | **13/13 PASS** |
| Character retry regressions | **PASS** (`semantic-evaluation-orchestration.test.mjs`) |
| A2 orchestration regressions | **PASS** (`a2-beat-orchestration-g3a.test.mjs`) |
| Frozen fixture hashes | Unchanged |
| Frozen policy hashes | Unchanged |
| Rubric hash | Unchanged |
| Arm definitions | Unchanged |
| Apparatus candidate SHA | `708ad05f5155cc1acc824cb8e7dc82d823e85dcb` |
| Base commit SHA | `818afc9a3c9b3e44ab9460ed8558b4c36cb84411` |
| Remediation diff scope | `character-phase.mjs` wiring + new correction module + tests |

Remediation executes from working tree atop base commit (uncommitted at record time). Runtime loads corrected source; `gitSha()` reports base HEAD until committed.

## Original failed SEQ-A disposition

Attempt 1 remains the forensic record. Restart uses a **fresh independent session** from T1; does not resume T11.

## Restart disposition

**Attempt 2 campaign COMPLETE.** See `governance/records/issue-201-lh1a-live-campaign-complete-2026-09-16.md`.

- Replacement SEQ-A session: `hg-session-f6a88ae0-176e-475f-9342-351ce53183d4` — 22/22 committed; T11 committed on first character attempt.
- Full campaign: 176/176 turns across eight sequences; `campaign_failed: false`.
- Evidence root: `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z/`
