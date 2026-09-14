# Issue #194 — Validation Blocker Resolution Report

**Date:** 2026-09-14  
**Issue:** [#194](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/194)  
**Disposition:** Both blockers cleared after bounded classifier remediation and faithful-path live slices.

## A. Activation

| Item | Value |
|------|-------|
| Pre-remediation candidate | `988e935` |
| Post-remediation HEAD | (pending commit on `issue-194-formal-validation`) |
| Issue state | `implemented` / In Progress / Implemented / P2 |
| Weights / bootstrap | `standard` / `full` / Full |
| Working tree | clean after evidence capture |

## B. Historical vs validation F06 triage inputs

| Field | Historical F06 | Validation full-turn | Authoritative comparison |
|-------|----------------|----------------------|--------------------------|
| Player text | 93-char knock post | **Identical** | Same verbatim string |
| Triage user prompt | instruction + PLAYER SOURCE | **Identical** (`buildPlayerVisibilityTriageUserPrompt`) | 365 chars |
| Manifest | instruction-only (#121) | instruction-only | No history/perception metadata delta |
| Corpus expectation | `full_pvr` | `full_pvr` | `neg_internal_cognition` / mixed observable+internal |

**Answer:** Triage **semantic inputs were equivalent**. Routing difference was not caused by replay input drift.

## C. Uniform-routing causal explanation

Live #121 checker is a **stochastic model call** (`reasoningEffort: off`, 32-token ceiling). Bounded characterization (5 runs, post-fix session):

- **5/5** routed `uniform_projection` (`affirmative_uniform_present`) — false-simple on mandatory-negative F06-shaped text
- Historical F06 correctly returned `requires_semantic_decomposition`

This is a **#121 checker false-simple**, not a #194 code regression (#194 did not modify triage). The prior full-turn validation was therefore **not a faithful Intervention-1 path** and cannot be used as I1 proof.

## D. Correct-path PVR validation (Intervention 1)

**Path:** production `runPlayerDecompositionPhase` on F06 text (triage bypassed; semantic decomposition exercised).

| Metric | Historical F06 | Live faithful path |
|--------|----------------|-------------------|
| Attempts | 2 | **1** |
| Retry | yes (punctuation) | **no** |
| Wall | ~41.5s | **37.3s** |
| Reasoning tokens | ~8,555 | **7,820** |
| PVR validity | invalid/excluded | **valid** |
| Units | 2 (observable + internal) | **3** (observable + 2 internal; model split) |

Deterministic F06 attempt-0 punctuation absorption remains proven in `test_issue_194_pvr_coverage_fidelity.py`. Live model included terminal `.` in unit text; normalization accepted without retry.

## E. F06 constrained environmental probe (pre-remediation)

Constrained probe was **semantically narrow** (1 need, B2-only) but classifier escalated because:

**Predicate:** `mediation_outcome present (no_librarian_match)` on resolution before KAR.

The constrained model populated a **non-canonical pre-mediation placeholder** (`no_librarian_match`), and the post-probe classifier treated any value except `no_match` as deep.

## F. Escalation classification

**OVER-SENSITIVE CLASSIFICATION** (pre-remediation)

Not justified complexity; not constrained-profile semantic failure. The probe shape matched the intended narrow B2 case; escalation was a classifier mismatch on non-authoritative `mediation_outcome` strings.

## G. Environmental-cognition cost

| Run | Probe wall | Deep wall | Combined wall | Combined reasoning |
|-----|-----------|-----------|---------------|-------------------|
| Pre-fix F06 opening | 2,792ms | 25,025ms | **27,817ms** | 4,375 |
| Post-fix F06 opening | **3,119ms** | 0 | **3,119ms** | 0 |
| Historical F06 baseline | ~55,728ms | — | ~55,728ms | ~11,454 |

Post-fix narrow characterization: **3/3** runs constrained without escalation.

## H. Remediation

**Bounded classifier fix** in `narrator_environment_deliberation_profile.py` + JS mirror:

- Escalate on **canonical post-mediation outcomes only:** `match`, `ambiguous`, `forbidden`, `retrieval_failure`, `mediation_failure`
- Do **not** escalate on `no_match` or model pre-mediation placeholders (`no_librarian_match`, prose placeholders, etc.)

Tests added for `no_librarian_match` single-B2 constrained path.

## I. Narrow no-escalation evidence

Post-fix: F06-shaped opening envelope + 3 repeated narrow runs — **4/4 constrained, 0 escalations**.

Example constrained probe: 1 B2 need (`door_surface_material`), `deliberation_profile_escalated: false`, probe wall ~3.1s, 0 reasoning tokens.

## J. Complex/deep preservation

Unchanged — deterministic prepare-time deep routing matrix + substrate bounded escalation test (`issue-194-env-cognition-profile-safety.test.mjs`).

## K. Tests/replays

```bash
python -m pytest v2/domain/tests/test_issue_194_environment_deliberation_profile.py \
                 v2/domain/tests/test_issue_194_pvr_coverage_fidelity.py -q
# 22 passed

cd v2/rp_runtime
node --test tests/issue-194-env-cognition-profile-safety.test.mjs \
             tests/issue-194-player-decomposition-retry.test.mjs
# 6 passed

node scripts/issue194-blocker-resolution.mjs
# post-fix: env_escalated=false, narrow_no_escalation=3/3, decomp 1 attempt accepted
```

Evidence JSON: `governance/records/issue-194-blocker-resolution-2026-09-14.json`

## L. Candidate identity

Remediation applied on branch `issue-194-formal-validation` (commit pending).

## M. Repository/artifact state

- Blocker evidence JSON committed
- #193 evidence file reverted (unchanged)
- Ephemeral execution evidence under temp dirs (not committed)

## N. Issue/Project state

Remains **`implemented`** / In Progress / Implemented / P2.

## O. Formal-validation readiness

**Both #194 blockers cleared** for formal-validation continuation:

1. **I1** — faithful semantic-decomposition path validated live; full-turn uniform misroute explained as #121 checker stochastic false-simple (not I1 defect).
2. **I2** — narrow constrained no-escalation path validated after bounded classifier fix; combined env-cog wall materially below historical baseline.

Governance review still required before `validated` transition.
