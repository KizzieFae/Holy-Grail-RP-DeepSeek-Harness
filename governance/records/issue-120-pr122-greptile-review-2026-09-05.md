# Issue #120 / PR #122 — Greptile Review

**Retrieved:** 2026-09-05  
**PR:** https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/122  
**Reviewed head:** `fc29af2542eaa962a37a3d44334c270e3afce245`  
**Issue:** #120 — Tighten player PVR semantic contract for narration vs cognition

## Check run

| Field | Value |
|-------|-------|
| **Name** | Greptile Review |
| **Check run ID** | 101245558415 |
| **Head SHA** | `fc29af2542eaa962a37a3d44334c270e3afce245` |
| **Status** | completed |
| **Conclusion** | success |
| **Started** | 2026-09-05T04:05:17Z |
| **Completed** | 2026-09-05T04:08:42Z |
| **Duration** | ~3m25s |
| **Summary** | Greptile has reviewed the Pull Request. **7 files reviewed, 1 comment added.** |
| **GitHub run URL** | https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/runs/101245558415 |
| **Greptile app** | https://github.com/apps/greptile-apps |

**Note:** Greptile did not publish a separate confidence-score block or extended PR-summary text on this review (unlike some prior PRs). Authoritative artifacts are the check-run summary above and the inline comment below.

## Files reviewed (7)

| File |
|------|
| `PACKET_CONTRACTS.md` |
| `docs/architecture.md` |
| `v2/domain/modules/narrative_visibility_prompt.py` |
| `v2/domain/modules/player_decomposition_fixtures.py` |
| `v2/domain/tests/test_issue_120_generalized_internal.py` |
| `v2/domain/tests/test_player_decomposition_context.py` |
| `v2/rp_runtime/scripts/issue120-live-validation.mjs` |

## Inline comments (1)

### G-122-01 — Projection metadata is never returned (P2)

| Field | Value |
|-------|-------|
| **Path** | `v2/rp_runtime/scripts/issue120-live-validation.mjs` |
| **Line** | 92 |
| **Severity** | P2 |
| **Review ID** | 5119729952 |
| **Comment ID** | 3939395793 |
| **URL** | https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/122#discussion_r3939395793 |
| **Author** | greptile-apps[bot] |
| **Submitted** | 2026-09-05T04:08:39Z |

**Finding:**

`projectForAyame` reads `perceptual_visibility_projection` from the raw `recordUserTurn` response, but that response contains only the perceptual record and validation audit. The resulting empty projection makes `japanExcluded` false and prevents `semantic_pass` from validating the actual viewer-specific behavior.

**Implementation-cycle disposition (pre-remediation):**

- **Valid finding** on the live harness only; core #120 remediation (prompt/docs/deterministic tests) is unaffected.
- Projection behavior was independently verified via `assemble_perceptual_history_entry_for_viewer` in deterministic tests and Python re-verification on live call #1 decomposition.
- Harness `semantic_pass` / `japan_excluded_from_ayame` fields are therefore **unreliable** until the harness is fixed to project through the domain projector path.

## Review metadata

| Field | Value |
|-------|-------|
| **Review state** | COMMENTED |
| **Review body** | (empty) |
| **New inline comments** | 1 |
| **Annotations on check run** | 0 |

## Governance note

This is external review evidence only. Greptile check **success** with **1 P2 harness finding** is **not** sole merge authorization. Issue #120 remains at **`implemented`** pending disposition of the harness finding (if remediated) and formal `implemented` → `validated` transition per workflow.

## Remediation follow-up (G-122-01)

**Prior reviewed head:** `fc29af2542eaa962a37a3d44334c270e3afce245` (Greptile SUCCESS, finding G-122-01 open)

**Remediation scope:** harness-only — `issue120-live-validation.mjs` now projects via authoritative `assemble_player_user_entry_for_viewer` (`project-player-entry-for-viewer.py` CLI), not `recordUserTurn` metadata.

**Remediation commit:** recorded on Issue #120 implementation comment after push (see execution anchor update).

**Re-review required:** Greptile must review the new exact PR head before integration.
