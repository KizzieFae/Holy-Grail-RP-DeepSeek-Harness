## Baseline capture complete (#242) — pre-consolidation freeze

**Execution-stage transition:** `open` → `investigating` (baseline observability + live matrix executed; **not** prompt consolidation).

### Execution anchor (frozen)

| Field | Value |
|-------|-------|
| **Commit SHA** | `5b3fc7c251d7ecd850c78827a55c2a68b035c6b3` |
| **Topology env** | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7` (T1/T2); unset (T3 production token arm) |
| **Retrieval** | OFF |
| **Progression enforcement** | ON (default) |

### T0 deterministic gates

- `pytest` (142 tests): **PASS** — includes `test_prompt_topology_manifest.py`, #240 topology, #230–#234, #243
- `python scripts/run_issue243_corpus_regression.py --eval`: **PASS** (willow_v1 + final_viability_v1)

### Live matrix sessions

| Run | Scenario | Session | Turns (audit) | Notes |
|-----|----------|---------|---------------|-------|
| R1a | cert_i234 | session_861 | 6 | overlay F0 aligned 1.0 |
| R1b | cert_i234 | session_862 | 6 | overlay F0 aligned 1.0 |
| R2a | emotional_loop_2char | session_863 | 12 | |
| R2b | emotional_loop_2char | session_864 | 12 | |
| R2c | emotional_loop_2char | session_866 | **4** | **WARN:** early end (<12 requested) |
| E1 | conflict_3char | session_868 | **7** | **WARN:** early end |
| E2 | willow i225 | session_869 | 12 | 0 overlays applied (rotation) — matches #240 FV7 |
| E3 | long_session | session_871 | **10** | **WARN:** early end |
| T3a | cert (production) | session_873 | 6 | token reference arm |
| T3b | emotional (production) | session_875 | 12 | token reference arm |

### Semantic engagement gates (v1_next7)

| Metric | Result | Floor |
|--------|--------|-------|
| `semantic_eval_presence_rate` | **1.0** (all v1_next7 runs) | 100% |
| Overlay-applied omission rate | **0.0** | 0% |
| Cert overlay-aligned F0 (R1a/R1b) | **1.0 / 1.0** | ≥ #240 FV1 floor (0.5) |
| Emotional overlay F0 (conservative) | 0.0–null | informational (#240 conservative) |

### Topology manifest (87 character turns)

| Metric | Value |
|--------|-------|
| **Profile match rate** | **1.0** |
| **Ordering violations** | **0** |
| **Dominant v1_next7 fingerprint** | `opening.dual\|semantic.block\|frame\|eval.required\|eval.examples\|cal.v7\|priorities.comp\|output.slim\|evidence` |
| **Median trigger→semantic block** | **126 chars** |
| **Median OUTPUT RULES tail (v1_next7)** | **1627 chars** |
| **Median OUTPUT RULES tail (production T3)** | **6751–6920 chars** |

Adaptive capsules (expected): arc/active.focus **100%** on 3-char lanes (868, 869); **0%** on 2-char lanes.

### Token summary (v1_next7 vs production)

| Surface | Median `system_chars` | Median OUTPUT RULES tail |
|---------|----------------------|--------------------------|
| **v1_next7** | ~40,295 | ~1,627 |
| **production (T3)** | ~41,000+ | ~6,751 |

Headroom signal: production OUTPUT RULES tail ~**4.1×** v1_next7 slim tail on same scenarios.

### Manual spot-check (PASS/WARN)

| Lane | Verdict | Notes |
|------|---------|-------|
| R1 cert | **PASS** | Distinct voices; semantic_evaluation present; overlay turns honest |
| R2 emotional | **PASS** | Standoff tone maintained; conservative no_covered_change on affect-only overlay turns |
| E1 conflict | **WARN** | Incomplete run length; 3-char arc/focus capsules present when emitted |
| E2 willow | **PASS** | In-room movement; no excursion misflags; overlays not applied (expected) |
| E3 long | **WARN** | Incomplete run length; semantic wire stable on captured turns |

### #240 comparison

- **Not worse** on cert overlay F0 (1/1 vs #240 1/2 floor)
- **100% semantic engagement** on emotional/cert v1_next7 lanes (matches #240 FV4/FV1 engagement)
- Willow **0 overlays applied** — inconclusive regression guard (same as #240 FV7)

### Known nuances

- Cert overlay schedules still reference `semantic_proposals` vocabulary while topology uses `semantic_evaluation` wire — models complied via v1_next7 rules
- Legacy classifier F2 counts on some cert turns are **investigation-era labels**; `semantic_decision` remains `covered_change`/`no_covered_change` (see #243 read discipline)
- `character_loader` system message not in turn audit — dual-surface token map still partial

### Artifact locations (repo-relative)

- `autogen_rp/python/validation_runs/issue242_baseline/5b3fc7c251d7/baseline_run_manifest.json`
- `autogen_rp/python/validation_runs/issue242_baseline/5b3fc7c251d7/baseline_synthesis.json`
- `autogen_rp/python/validation_runs/issue242_baseline/5b3fc7c251d7/topology_rollup.json`
- `autogen_rp/python/data/issue240_runs/issue242_baseline_prompts/5b3fc7c251d7/` (`INDEX.json`, `TOPOLOGY_MANIFEST_session_*.json`)
- Audits: `autogen_rp/python/rp_app/data/rp_audits/session_861`–`875` (listed above)

### Instrumentation added (observability only)

- `autogen_rp/python/rp_app/prompt_topology_manifest.py` — `extract_topology_manifest()`
- Extended `autogen_rp/python/scripts/_issue240_extract_prompts.py` (`--topology-manifest`)
- `autogen_rp/python/scripts/_issue242_topology_rollup.py`
- `autogen_rp/python/scripts/run_issue242_baseline_matrix.py`
- `autogen_rp/python/scripts/_issue242_baseline_synthesis.py`
- `autogen_rp/python/tests/test_prompt_topology_manifest.py`

### Baseline freeze statement

**This evidence bundle is the authoritative pre-consolidation comparison anchor** for #242 prompt-efficiency work at SHA `5b3fc7c`. Post-edit runs must compare against these sessions/metrics/topology fingerprints before claiming improvement.

### Next step (not executed here)

- Consolidation proposal + **`consensus_reached`** before any prompt wording edits
- Coordinate with [#230](https://github.com/KizzieFae/Holy_Grail_RP/issues/230) for production landing strategy
