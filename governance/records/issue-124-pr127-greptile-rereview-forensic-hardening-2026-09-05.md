# Issue #124 / PR #127 — Greptile Re-review (Forensic Hardening Head)

**Date:** 2026-09-05  
**Reviewed HEAD:** `c70aab147f70141f634bc0bb9d88c98fa706c0b7`  
**Prior reviewed HEAD:** `0d2b3124e769f9a150fe1d6637e3413120c59be2` (5/5 — superseded)

| Field | Value |
|-------|-------|
| **Check** | Greptile Review — **SUCCESS** |
| **Check run ID** | `101286839904` |
| **Started / completed** | 2026-09-05T09:44:23Z → 2026-09-05T09:47:35Z (~3m12s) |
| **Summary** | 22 files reviewed, **1 comment added** |
| **Confidence score** | **Not published** in check summary (unlike prior 5/5 on `0d2b312`) |
| **New inline comments** | **1** |

### New finding (not introduced by forensic hardening commit)

| ID | Severity | Path | Finding |
|----|----------|------|---------|
| G-124-03 | **P1** | `v2/domain/modules/player_semantic_normalization.py` L377–391 | **Search budget misses candidate scans** — DFS node budget counts visited nodes but candidate-list scans and overlap checks outside `nodes_visited` can still consume excessive CPU on long sources with many short-excerpt occurrences; semantic retry repeats work. |

**Forensic hardening changes:** No Greptile inline comments on `player-decomposition-phase.mjs` or new tests.

**Disposition:** Return P1 to Governance — **do not auto-remediate** (out of forensic-hardening scope; touches search-budget semantics).

**Integration:** NOT authorized. PR #127 remains OPEN and unmerged.
