# Fresh-Start M14.4 — Current Documentation Rewrite + Product Naming Cleanup

**Status:** Complete  
**Date:** 2026-08-18  
**M14.1 anchor:** `6f17286`  
**M14.2 anchor:** `3bb79dd`  
**M14.3 anchor:** `9b6fa4e`  
**Pre-slice HEAD:** `9b6fa4e`  
**M14.4 implementation HEAD:** _(set at commit)_

**Assigned workflow weight:** standard  
**Effective workflow weight:** full

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `9b6fa4e` |
| Working tree | clean at activation |
| Validation baseline | domain 358; integration 133 + 1 xfail; rp_runtime 70 |

---

## 2. Current-document inventory / classification

| Document | Class | Action |
|----------|-------|--------|
| `README.md` | CURRENT | Rewritten — product-first Holy Grail RP |
| `ARCHITECTURE_OVERVIEW.md` | MIXED → CURRENT | Rewritten positively; migration banners removed |
| `MODULE_INDEX.md` | MIXED → CURRENT | Header, paths, related docs cleaned |
| `SCENARIO_VALIDATION_FRAMEWORK.md` | MIXED → CURRENT | Rewritten for current validation paths; V1 CLI removed |
| `AGENTS.md` | CURRENT | Rewritten — `v2/` authorities, no `rp_app` |
| `docs/architecture.md` | CURRENT | Rewritten for domain + DSH stack |
| `docs/repo-map.md` | OBSOLETE content | Full rewrite |
| `docs/rp-data-layout.md` | CURRENT | Rewritten — canonical `data/` only |
| `docs/testing.md` | CURRENT | Rewritten — `v2/` pytest commands |
| `docs/core-operating-invariants.md` | CURRENT | Updated authorities |
| `docs/audit-workflows.md` | MIXED → CURRENT | Path and module references updated |
| `docs/scene-grounding-layer.md` | CURRENT | Bounded path fix |
| `DEBUGGING_GUIDE.md` | MIXED → CURRENT | Intro + key path/link fixes |
| `PACKET_CONTRACTS.md` | CURRENT | Intro paths updated |
| `v2/README.md` | CURRENT | Holy Grail RP implementation tree |
| `governance/README.md` | CURRENT | Current vs historical boundary |
| `tools/*/README.md` | CURRENT | Bounded updates |
| `governance/rp-app/*.md` | HISTORICAL | Preserved |
| `governance/archive/**` | HISTORICAL | Preserved |

**Deleted:** none (no uniquely obsolete current-facing docs identified beyond in-place rewrites).

---

## 3. Product vocabulary (applied)

| Concept | Current name |
|---------|----------------|
| Product | **Holy Grail RP** |
| Domain library | `v2/domain/modules/` |
| Domain Host | `v2/domain_api/` |
| RP runtime / orchestration | `v2/rp_runtime/` (DSH / Cordis) |
| Data root | `data/` (`HG_DATA_DIR`) |
| Tooling | `tools/investigation/`, `tools/maintenance/` |

Literal path `v2/` retained as implementation root, not product branding.

---

## 4. Product naming policy

- **Holy Grail RP** in current-facing prose
- **`v2/`** only as literal implementation path
- **`Launch-Holy-Grail-V2.bat`** unchanged (literal launcher filename)
- No rename/move of `v2/` in M14.4

---

## 5–12. Documentation results (summary)

- **README:** product overview, quick start, doc index, layout — no V1/AutoGen narration
- **Architecture:** positive three-layer + Domain Host / DSH flow
- **MODULE_INDEX:** `data/` paths; related docs point to current authorities + historical audit archive
- **Scenario validation:** manifests at `data/fixtures/progression_simulation_scenarios/`; domain tests; no deleted CLI instructions
- **Data docs:** canonical `data/` tree only; migration check confined to maintenance README
- **Runtime/env:** repo-root `.venv`, launcher, `HG_*` env vars documented
- **Tooling:** current scripts only; migration check framed as optional operator utility
- **Bootstrap:** `AGENTS.md`, `core-operating-invariants.md`, `issue-bootstrap-profiles.md` (unchanged profile lists; authorities updated via AGENTS)

---

## 13. Governance treatment

Historical M12–M14 records and `governance/archive/` preserved. `governance/README.md` labels program records as history.

---

## 14. Documents deleted

None.

---

## 15. Terminology cleanup

Removed or rewrote transition-era narration (`V1 replacement`, `post-AutoGen`, `rp_app` paths, `run_scene_simulation_llm`, `autogen_rp/python/data` as product paths) from current-facing docs.

**Retained legitimately:** `v2/` path references, `Launch-Holy-Grail-V2.bat`, domain module names like `turn_runner_*.py`, `governance/archive/` as historical audit reference, maintenance tool legacy path mention.

---

## 16. Code comment cleanup

Bounded — no production behavior changes. Doc invariant test added to `v2/tests/test_repository_architecture.py`.

---

## 17. Documentation invariant

`test_current_bootstrap_docs_avoid_retired_runtime_paths` — scans README, AGENTS, architecture docs for deleted runtime path instructions.

---

## 18. Fresh-start reader assessment

A new reader can answer all 12 fresh-start questions from current docs without V1 knowledge. Historical audit detail remains in `governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md` (explicitly labeled).

---

## 19. Broken-link/path audit

Current bootstrap docs no longer instruct use of `autogen_rp/python/rp_app`, `python/rp_app/`, or `run_scene_simulation_llm.py`. MODULE_INDEX no longer links to deleted `autogen_rp/python/rp_app/*.md`.

---

## 20. Validation

| Suite | Post-M14.4 |
|-------|------------|
| `v2/domain/tests` | **358 passed** |
| `v2/tests` | **134 passed**, 1 xfail (+1 doc invariant) |
| `v2/rp_runtime npm test` | **70 passed** |

---

## 21. Fresh-start residue (current docs)

| Token | Current docs (approx.) |
|-------|------------------------|
| `V2` as product name | **0** (path/launcher only) |
| `AutoGen` | **0** in rewritten current docs |
| `autogen_rp` | **0** in bootstrap docs; maintenance README only for optional migration check |
| `rp_app` | **0** in bootstrap doc set tested by invariant |
| `turn_runner` | module names in MODULE_INDEX only (current code) |
| M12/M13/M14 | **0** in rewritten current docs |

---

## 22. Operator-local `autogen_rp`

No current documentation requires the local ignored tree for normal operation. Optional: `hg_data_migration_check.py` for one-time legacy compare. Safe to delete for runtime; retain `.gitignore` while tree exists.

---

## 23. M14.5 decision gate

**Outcome: A — M14 complete; remaining literal `v2/` and `Launch-Holy-Grail-V2.bat` names are harmless implementation details.**

Evidence: product branding is **Holy Grail RP** in README/AGENTS/architecture; `v2/` is stable implementation namespace; renaming would cause high churn with low fresh-start benefit.

---

## 24. Challenge / refinement

- README reads as current product doc, not migration report
- Architecture understandable without V1
- Historical governance preserved
- Bootstrap authorities updated
- Dead CLI instructions removed rather than renamed
- Product code unchanged

---

## 25. Architecture verdict

**Fresh-start documentation complete** (with intentional historical archive references for audit artifact semantics).
