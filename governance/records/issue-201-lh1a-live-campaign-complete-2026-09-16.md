# Issue #201 LH-1A — Live Campaign Complete (Restart Attempt 2)

**Date:** 2026-09-16  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** `consensus_reached` (unchanged — not `implemented`)  
**Subphase:** LH-1A live execution — **COMPLETE** after structural-correction remediation  
**Workflow weight:** `full` / `full`

## Remediation reference

`governance/records/issue-201-lh1a-seq-a-structural-correction-remediation-2026-09-15.md`

Bounded correction-context enrichment in `character-structural-correction.mjs` + `character-phase.mjs` wiring. Ingress validation unchanged.

## Original failed attempt (Attempt 1) — preserved

| Field | Value |
|-------|-------|
| Session | `hg-session-a1bd723c-a81f-42d4-857b-c1ec2191b56b` |
| Evidence | `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-03-03-444Z/` |
| Outcome | SEQ-A failed T11 (10/22 committed) — character schema exhaustion |
| Record | `governance/records/issue-201-lh1a-live-campaign-partial-2026-09-16.md` |

## Restart campaign (Attempt 2)

| Field | Value |
|-------|-------|
| Investigation run | `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z/` |
| Apparatus candidate | `708ad05f5155cc1acc824cb8e7dc82d823e85dcb` |
| Base execution SHA | `818afc9a3c9b3e44ab9460ed8558b4c36cb84411` |
| Remediation | Working-tree atop base (uncommitted at run time) |
| Preflight | 35/35 PASS |
| Campaign outcome | **176/176 turns committed — SUCCESS** |

### Replacement SEQ-A

| Field | Value |
|-------|-------|
| Session | `hg-session-f6a88ae0-176e-475f-9342-351ce53183d4` |
| Sequence artifact | `LH1A-LIVE-lh_a-ayame_controlled-1789525555444-sequence.json` |
| Turns | 22/22 committed |
| T11 | **Committed** (`retry_count: 0`, narrator invoked) |

### All sequences

| Seq | Arm | Scenario | Session | Turns | Failed |
|-----|-----|----------|---------|-------|--------|
| SEQ-A | LH-A | Ayame | `hg-session-f6a88ae0-176e-475f-9342-351ce53183d4` | 22/22 | no |
| SEQ-B | LH-B | Ayame | `hg-session-d37e42ba-ea5c-4dd7-bf34-55eeb67dfbcd` | 22/22 | no |
| SEQ-C | LH-C | Ayame | `hg-session-2ccc78a0-2abb-4fbd-805a-6d9257dee100` | 22/22 | no |
| SEQ-D | LH-D | Ayame | `hg-session-a75b0ac7-bf39-494d-bb2c-0a01f907a83f` | 22/22 | no |
| SEQ-E | LH-A | Arkham | `hg-session-50402afe-d8cc-4a2a-bf32-30563c35ae09` | 22/22 | no |
| SEQ-F | LH-B | Arkham | `hg-session-3660aca9-607f-48ff-90cb-d7c5705509af` | 22/22 | no |
| SEQ-G | LH-C | Arkham | `hg-session-f81a7554-100f-4e69-8eaf-f980e88e409c` | 22/22 | no |
| SEQ-H | LH-D | Arkham | `hg-session-227959da-16cc-47a9-9aa5-26afa424a611` | 22/22 | no |

## Schema-compliance recurrence

Structural rejections **recurred** during Attempt 2 (24 character `parse_error` rejections for `move_schema_version` / `invalid beat type` across sequences). Structural correction guidance was invoked on matching retries. **No beat terminated with `character_failure` after budget exhaustion.** All 176 turns committed.

## Blind evidence

- `issue201-lh1a-blind-sequence-packet.json` (frozen pre-decode)
- `issue201-lh1a-blind-sequence-answer-key.json` (separate)
- `issue201-lh1a-campaign-plan-locked.json`
- `issue201-lh1a-live-campaign-report.json`

Blind decode and rubric scoring **not performed** — await Governance authorization.

## Next Governance decision

1. Authorize blind evaluation with frozen rubric (`f533cc60…`)  
2. Decode arm mapping and produce archaeology/lifecycle/seam/cost analyses  
3. Decide LH-1B authorization vs. architectural selection from LH-1A evidence  
4. Commit remediation changes and record post-remediation execution SHA  
5. Keep #201 OPEN until Phase-5 disposition complete
