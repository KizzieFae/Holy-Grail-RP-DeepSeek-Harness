# Issue #124 / PR #127 — Second Remediation Search Budget Benchmark

**Date:** 2026-09-05  
**Prior HEAD:** `7d8d579` (`NORMALIZATION_SEARCH_NODE_BUDGET = 100_000`)  
**Selected production budget:** `15_000` (`NORMALIZER_VERSION = 3`)

Harness: `normalize_player_semantic_decomposition` with budget override for before column.

| Case | Budget | Nodes | ms | Outcome |
|------|--------|-------|-----|---------|
| ordinary (`Hello there.`) | 100k | 2 | 0.2 | accept |
| ordinary | **15k** | 2 | 0.1 | accept |
| ident 7×`a` (legitimate stress) | 100k | 13,700 | 162.2 | accept |
| ident 7×`a` | **15k** | 13,700 | 173.2 | accept |
| ident 9×`a` (pathological) | 100k | 100,001 | 1585.8 | budget fail (retry eligible) |
| ident 9×`a` | **15k** | 15,001 | 315.1 | budget fail (retry eligible) |
| `Yes. Yes.` | 100k / **15k** | 5 | ~0.2 | accept |
| omission (`Hello` only) | 100k / **15k** | 1 | ~0.0 | `sir_substantive_omission` |
| material ambiguity (`abab` / `ab`+`ab`) | 100k / **15k** | 5 | ~0.2 | accept |

**Worst permitted two-attempt deterministic cost (9×`a`, budget 15k):**

| Attempt | Nodes | ms | Retry |
|---------|-------|-----|-------|
| 0 | 15,001 | 246.7 | yes |
| 1 | 15,001 | 229.2 | no (terminal) |
| **Total** | — | **~476 ms** | — |

**Rationale:** 15k exceeds legitimate 7-unit stress (~13.7k nodes) with headroom; pathological 9-unit case fails ~5× faster than 100k bound; worst two-attempt synchronous normalization ~0.48s vs ~3.2s+ at 100k.
