# Issue #201 LH-1A — Live Campaign Partial Execution Record

**Date:** 2026-09-16  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** `consensus_reached` (unchanged)  
**Subphase:** LH-1A live execution — **PARTIAL / STOPPED**  
**Workflow weight:** `full` / `full`  

## Authorization

Live LH-1A execution authorized by Governance prompt (2026-09-16). Preflight **35/35 PASS**.

## Execution artifacts

| Field | Value |
|-------|-------|
| Apparatus candidate | `708ad05f5155cc1acc824cb8e7dc82d823e85dcb` |
| Live-runner commit | `818afc9a3c9b3e44ab9460ed8558b4c36cb84411` |
| Investigation run | `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-03-03-444Z` |
| Campaign order | `lh1a_live_execution_order_v1` (SEQ-A..H) |

## Outcome

**Campaign failed technically at SEQ-A turn 11.** No sequence retries performed per authorization.

| Sequence | Blind | Arm | Scenario | Status | Turns |
|----------|-------|-----|----------|--------|-------|
| SEQ-A | SEQ-A | LH-A | Ayame | **FAILED T11** | 10/22 committed |
| SEQ-B..H | — | — | — | **NOT STARTED** | 0/22 |

**Total player turns:** 10/176 committed (11 attempted, 1 failed commit).

## Failure classification

- **Type:** Technical infrastructure / beat-commit failure (not methodology drift)
- **Symptom:** Turn 11 `committed: false`, empty `presentation_text`, `retry_count: 3` on character/narrator path
- **Arm:** LH-A (control) — persistent cognition not involved
- **Scene:** `entry_foyer` (pre-T12 transition)
- **Session:** `hg-session-a1bd723c-a81f-42d4-857b-c1ec2191b56b`

## Frozen hashes (verified at preflight)

Unchanged from apparatus validation — all matched.

## Blind evidence

Partial blind packet exported from committed SEQ-A turns only. Answer key generated. **Decode not performed** for architectural conclusions.

## Original failed attempt (Attempt 1) — preserved

This partial record is the permanent forensic disposition for Attempt 1. Do not overwrite with restart evidence.

## Remediation and restart

See `governance/records/issue-201-lh1a-seq-a-structural-correction-remediation-2026-09-15.md`.

## Next Governance decision

Await restart outcome and full campaign disposition per remediation authorization.

## Constraints preserved

- No retries
- No cognition tuning
- No methodology drift
- Issue #201 remains OPEN / not `implemented`
