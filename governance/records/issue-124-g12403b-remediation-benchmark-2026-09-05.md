# Issue #124 — G-124-03b Remediation Benchmark

**Date:** 2026-09-05  
**Behavioral HEAD:** (recorded at commit)  
**Budget:** `NORMALIZATION_DETERMINISTIC_WORK_BUDGET = 350_000` (`NORMALIZER_VERSION = 5`)

| Case | Source | Units | Work | Overlap | Mask | Nodes | Stage | ms | Outcome |
|------|--------|-------|------|---------|------|-------|-------|-----|---------|
| ordinary (`Hello everyone.`) | 15 | 1 | 36 | 0 | 15 | 2 | — | <1 | accept |
| `Yes. Yes.` ambiguity | 18 | 2 | ≤20 | low | low | ≤20 | — | <1 | `fragment_assignment_ambiguous` |
| omission (`Alpha Beta`/`Alpha`) | 10 | 1 | low | 0 | 10 | 1 | — | <1 | `sir_substantive_omission` |
| legitimate 7×`a` | 7 | 7 | 296,374 | 221,935 | 14 | 13,700 | — | ~196 | **accept** |
| pathological 9×`a` | 9 | 9 | 350,000 | 280,235 | 18 | 10,404 | `overlap_check` | ~206 | budget exceeded |
| 50k 1-char | 50,000 | 7 | 350,000 | 0 | 0 | 0 | `occurrence_scan` | ~162 | budget exceeded |
| 100k multi-unit | 100,000 | 7 | 350,000 | 0 | 0 | 0 | `occurrence_scan` | <500 | budget exceeded |
| two-attempt 9×`a` | 9 | 9 | — | — | — | — | — | ~412 | retry then terminal |

### Comparison to `30589ed` (80k, v4)

| Case | Before | After (v5) |
|------|--------|------------|
| 7×`a` | failed at 80k (no overlap charge) | **accept** at 296k work |
| 9×`a` | 80k / ~148ms | 350k / ~206ms, overlap_check stage |
| 50k | 80k / ~38ms occurrence_scan | 350k / ~162ms occurrence_scan |
| G-124-03b gap | overlap + span mask unmetered inside probe | **charged** (overlap_check + precomputed span masks) |

**Calibration rationale:** 350k provides ~18% headroom above legitimate 7×`a` (~296k) while terminating 9×`a` and long-source cases within ~200–400ms synchronous bound.
