# Issue #124 / PR #127 — Integration & Closure

**Date:** 2026-09-05  
**Governance phase:** integration and closure (authorized)

## Integration SHAs

| Role | SHA |
|------|-----|
| Pre-merge `main` | `14bbc3c11353c136ed8000395dfae1e37b7e22e0` |
| PR #127 HEAD | `73bf768663345dcef8d878d109a838d9cfe6fbf9` |
| Behavioral candidate | `37b1f7e188bcc0f39d464851df998c957044d86b` |
| Merge commit / resulting `main` | `e226cfa2b87ae4e8c1c02221bc74ea6a671c88cf` |

Post-behavioral delta (`37b1f7e`..`73bf768`): governance record only — no production/runtime changes.

## Greptile disposition

| Finding | Status |
|---------|--------|
| G-124-03 (occurrence/candidate probe unmetered) | Remediated in unified ledger; not re-raised on `37b1f7e` |
| G-124-03b (overlap/span-mask inside probe) | Remediated (overlap_check + precomputed span masks); not re-raised on `37b1f7e` |
| Latest review (`37b1f7e`, run `101368765896`) | SUCCESS, 0 new inline comments |

## Validation anchors

- Live semantic validation: 3/3 representative cases (formal validation record)
- Domain targeted (#124, kernel, #120, #121): 32/32
- Node targeted (decomposition, triage, trace-emitter, forensic): 21/21
- Full `npm test`: **464/464**
- G-124-03 / G-124-03b benchmark matrix: recorded in `issue-124-g12403b-remediation-benchmark-2026-09-05.md`
- Forensic hardening: `issue-124-pr127-forensic-hardening-2026-09-05.md`

## Deterministic-work model (integrated)

- Unified `_DeterministicWorkLedger`
- Charged stages: `occurrence_scan`, `candidates_generated`, `substantive_mask`, `dfs_visit`, `candidate_probe`, `overlap_check`
- `NORMALIZATION_DETERMINISTIC_WORK_BUDGET = 350_000`
- `NORMALIZER_VERSION = 5`
- Resource exhaustion: `normalization_search_budget_exceeded` (distinct from semantic invalidity)

## Token policy (permanent #124 record)

> Issue #124 intentionally leaves `player_decomposition` per-inference token allowance uncapped. Semantic attempts remain bounded at two. Deterministic normalization is independently bounded by the calibrated deterministic-work budget. Any future inference-token runaway-protection cap must be empirically sized and handled separately.

## Documentation

- `docs/architecture.md` — normalizer v5 unified work model
- Obsolete DFS-only budget description superseded

## Closure

- Issue #124: **CLOSED**
- Project: Status **Done**, Workflow **Done**, Priority **P2**
- PR #127: **MERGED**
- Issue #125: not executed (successor boundary)
