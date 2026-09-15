# Issue #201 G3-E — Experimental Apparatus Implementation Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Proposal SHA:** `a438635`  
**Phase:** G3-E experimental-apparatus implementation (authorized)  
**Live G3-E execution:** NOT authorized / NOT performed  
**Issue canonical state:** `consensus_reached` (unchanged)

---

## Authorization scope

Implemented apparatus only per Governance authorization:

- corpus builder + fixture source + truth manifest
- frozen K1–K7 policies
- G3-E harness + lib
- A2 indexed-retrieval adapter (harness path)
- K3 forensic instrumentation (7-step)
- K6 R/P/C/S/M adjudicator
- capability-matrix exporter
- blind-packet tooling
- Tier-1 detectors + Librarian ledger schema
- deterministic/mock smoke validation

**Not performed:** 14/28 live comparison runs, live blind decode, production architecture changes, long-horizon testing.

---

## Implementation artifacts

| Component | Path |
|-----------|------|
| Corpus builder | `tools/investigation/issue201-g3e-corpus-build.mjs` |
| Corpus fixtures | `governance/records/issue201-g3e-fixtures/ayame_archive_corpus_v1/` |
| K policies | `governance/records/issue201-g3e-policies/K1.json` … `K7.json` |
| Retrieval probe (read-only) | `tools/investigation/issue201_g3e_retrieval_probe.py` |
| G3-E lib | `v2/rp_runtime/scripts/lib/issue201-g3e-lib.mjs` |
| Harness | `v2/rp_runtime/scripts/issue201-g3-e-massive-retrieval.mjs` |
| A2 indexed adapter | `v2/rp_runtime/src/lib/a2-indexed-retrieval.mjs` |
| A2 orchestrator hook | `v2/rp_runtime/src/lib/a2-beat-orchestration.mjs` (`enableIndexedRetrieval`) |
| Scenario shell | `v2/rp_runtime/scripts/lib/issue201-g3-scenarios.mjs` (`ayame_archive_interview`) |
| Apparatus tests | `v2/rp_runtime/tests/issue201-g3e-apparatus.test.mjs` |

---

## Validation summary (deterministic)

**Corpus:** 307 records; SHA256 `0cb74db3f507e8d4333582da9dec16f5a31f07acb1bdc6e1244c437cfa6f5e7c`; reproducible rebuild verified.

**K3 seven-stage:** production stages 1–5 pass on probe; stages 6–7 demonstrated with mock forensics (live deferred).

**Harness smoke:** `node v2/rp_runtime/scripts/issue201-g3-e-massive-retrieval.mjs --validate-apparatus` → `readiness_for_live_execution: true` (apparatus wiring only).

**Evidence root (local, gitignored):** `data/investigation_runs/issue201-g3e-apparatus-2026-09-15T18-58-10-395Z/`

---

## Production isolation

- No changes to production bootstrap / mount paths.
- `a2-beat-orchestration.mjs` remains harness-only (not imported by production bootstrap).
- Indexed retrieval invokes read-only investigation probe; does not invoke Librarian LLM.
- Plot remains absent (`skipPostCommitPlot: true` on both arms).

---

## Deviations

None from approved proposal `a438635`. K6 projection outcomes in probe-only matrix may show ranking/budget failures until live Primary-RP wiring — expected for apparatus validation without live campaign.

---

## Governance next decisions

1. Authorize live G3-E comparison campaign (14/28 runs) as separate action.
2. Confirm corpus seeding procedure for runtime `data/sessions/_story_knowledge/g3e_ayame_archive_v1/` before live runs.
3. Maintain `consensus_reached` until post-G3-E live synthesis and architecture adjudication.
