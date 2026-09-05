# Issue #124 — G-124-03 Remediation Benchmark

**Date:** 2026-09-05  
**Behavioral HEAD:** (recorded at commit)  
**Budget:** `NORMALIZATION_DETERMINISTIC_WORK_BUDGET = 80_000` (`NORMALIZER_VERSION = 4`)

| Case | Source len | Units | Work consumed | DFS nodes | Stage | ms | Outcome |
|------|-----------|-------|---------------|-----------|-------|-----|---------|
| ordinary (`Hello everyone.`) | 15 | 1 | ~20 | ≤5 | — | <1 | accept |
| `Yes. Yes.` material ambiguity | 18 | 2 | ≤20 | ≤20 | — | <1 | `fragment_assignment_ambiguous` |
| substantive omission (`Alpha Beta` / `Alpha`) | 10 | 1 | low | 1 | — | <1 | `sir_substantive_omission` |
| legitimate 7×`a` | 7 | 7 | 74,432 | 13,700 | — | ~133 | accept |
| pathological 9×`a` | 9 | 9 | 80,000 | 11,936 | `dfs_visit`/`candidate_probe` | ~148 | `normalization_search_budget_exceeded` |
| long 1-char excerpt | 50,000 | 7 | 80,000 | 0 | `occurrence_scan` | ~38 | budget exceeded (not omission) |
| long multi-unit | 10,000 | 7 | 80,000 | 0 | `occurrence_scan` | ~35 | budget exceeded |
| two-attempt 9×`a` | 9 | 9 | — | — | — | ~300–750 | retry then terminal |

**Prior baseline (node-only budget 15k):** 50k-source omission path ~1,016ms (two attempts), DFS nodes=1.
