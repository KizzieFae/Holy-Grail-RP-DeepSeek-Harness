# Fresh-Start M14.2 — Migration Compatibility Sunset

**Status:** Complete  
**Date:** 2026-08-18  
**M14 investigation anchor:** `d32664a`  
**M14.1 anchor:** `6f17286`  
**Pre-slice HEAD:** `6f17286`  
**M14.2 implementation HEAD:** *(set at commit)*

**Assigned workflow weight:** standard  
**Effective workflow weight:** full

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Branch | `main` |
| Pre-slice HEAD | `6f17286` |
| Working tree | clean at activation |

---

## 2. Prior migration architecture (removed)

| Component | Behavior |
|-----------|----------|
| `legacy_data_dir()` | `repo_root/autogen_rp/python/data` |
| `run_data_migration()` | Copy empty canonical categories from legacy; write `.hg_data_migration_v1.json` marker |
| `ensure_data_migrated()` | Called on every `characters_data_dir()`, `scene_templates_data_dir()`, `fixtures_data_dir()`, and `sessions_data_dir()` (unless `HG_SESSIONS_DIR` set) |
| Precedence | Skip category if canonical already has entries; never overwrite |
| Idempotency | Marker `version >= 1` short-circuits |

**Startup path probed legacy on every data accessor** — removed in M14.2.

---

## 3. Canonical data inventory (operator workstation)

| Category | Files (approx) |
|----------|----------------|
| `data/characters/` | 22 |
| `data/scene_templates/` | 20 |
| `data/retrieval/` | 4 |
| `data/fixtures/` | 77 |
| `data/sessions/` | 1730 (1729 session ids + index) |
| `data/rp_audits/` | 0 (canonical) |
| Migration marker | `.hg_data_migration_v1.json` present (v1) |

---

## 4. Operator-local legacy inventory

`autogen_rp/python/data/` exists (ignored, not tracked).

| Category | Legacy files |
|----------|--------------|
| `autogen_characters/` | 22 |
| `sessions/` | 1451 |
| `progression_simulation_scenarios/` | 40 |
| `rp_audits/` | 82 (historical evidence) |
| `_cross_scope_memory/` | 0 |
| `_scope_knowledge/` | 0 |

---

## 5. Canonical-vs-legacy comparison

| Category | Legacy | Canonical | Legacy-only | Hash mismatch | Safe |
|----------|--------|-----------|-------------|---------------|------|
| characters | 22 | 22 | 0 | 0 | Yes |
| scene_templates | 0 | 20 | 0 | 0 | Yes |
| retrieval | 0 | 4 | 0 | 0 | Yes |
| fixtures/* | 40–0 | populated | 0 | 0 | Yes |
| sessions | 1451 | 1730 | 0 | 1 (`_session_index.json` only) | Yes |
| rp_audits | 82 | 0 | 82 | — | Historical only |
| cross-scope / scope knowledge | 0 | 0 | 0 | 0 | Yes |

**Sessions:** 1450 legacy ids; **0** missing in canonical; **279** canonical-only (newer work).

---

## 6–8. Session / memory / knowledge verification

- **Sessions:** Every legacy session id present in canonical `data/sessions/`.
- **`_session_index.json`:** Canonical copy newer/larger (expected; superset index).
- **Cross-scope memory / scope knowledge:** No legacy-only files; stores live under session paths when present.

---

## 9. Character/template verification

22 legacy character files; 22 canonical — **0 legacy-only**, **0 hash mismatches**.

---

## 10. Other legacy data

| Item | Classification |
|------|----------------|
| `rp_audits/` (82 legacy files) | Historical investigation evidence — not production blocker |
| Local `autogen_rp/` tree (~68k files incl. caches) | Operator-local residue |

---

## 11. Migration status table

**`compatibility_retirement_safe: true`** per `tools/maintenance/hg_data_migration_check.py --check`.

---

## 12. Final migration/check mechanism

**`tools/maintenance/hg_data_migration_check.py`**

- `--check` (default): structural comparison report; exit 0 when safe
- `--migrate`: final idempotent copy for empty canonical categories only
- Does not delete legacy source

---

## 13. Migration actions performed

No additional `--migrate` required this slice (marker v1 already present; canonical superset verified).

---

## 14. Compatibility sunset decision

**A — Compatibility sunset approved.** All required legacy session/character data represented in canonical `data/`.

---

## 15. Code removed

| Removed | Notes |
|---------|-------|
| `v2/domain/data_migration.py` | Entire module |
| `legacy_data_dir()` | From `paths.py` |
| `ensure_data_migrated()` | From `paths.py` |
| `autogen_python_data_dir()` | From `paths.py` |
| `MIGRATION_MARKER_NAME` | From production paths (marker file remains on disk) |
| `v2/tests/test_data_migration_m13_1.py` | 13 migration tests |

---

## 16. Startup migration hook

**Removed.** Data accessors resolve `HG_DATA_DIR` / `HG_SESSIONS_DIR` directly with no legacy probe.

---

## 17. Test changes

| Change | Count |
|--------|-------|
| Deleted `test_data_migration_m13_1.py` | −13 |
| Added `test_canonical_data_paths_m14_2.py` | +6 |
| Updated `test_autogen_rp_container_retirement_m13_7.py` | migration hook test replaced |

---

## 18. `.gitignore autogen_rp/` decision

**RETAINED.** Operator local `autogen_rp/` still exists (~68k files). Removing the ignore rule would expose private/local residue in `git status`. Remove only after operator deletes the local tree.

---

## 19. Local `autogen_rp/` deletion readiness

**Safe to delete for this operator** after optional manual confirmation:

```text
E:\CascadeProjects\Holy Grail RP DeepSeek Harness\autogen_rp\
```

Evidence: all 1450 legacy session ids in canonical; characters matched; no unique memory/knowledge; production paths no longer read legacy tree; repo-root `.venv` is canonical.

**Historical `rp_audits/` under legacy** are investigation artifacts only (82 files) — not required for runtime.

---

## 20. Production path audit

`v2/domain/paths.py` and `v2/domain_api/session_repository.py`: **0** `autogen_rp` references.

---

## 21. Validation

| Suite | Result |
|-------|--------|
| `v2/domain/tests` | **358 passed** |
| `v2/tests` | **147 passed, 1 xfailed** |
| `v2/rp_runtime npm test` | **70 passed** |

---

## 22. Fresh-start data-path proof

- Production `autogen_rp` data path references: **0**
- Startup migration probes: **0**
- Default data root: `data/`
- `HG_DATA_DIR` / `HG_SESSIONS_DIR` overrides: tested in `test_canonical_data_paths_m14_2.py`

---

## 23. Remaining M14 work

| Slice | Scope |
|-------|-------|
| **M14.3** | `LEGACY_RP_APP` investigation tooling + retirement tests |
| **M14.4** | Comprehensive doc fresh-start rewrite |
| **M14.5** | Optional `v2/` promotion |

Operator action: delete local `autogen_rp/` when ready; then optionally remove `.gitignore autogen_rp/` in a later slice.

---

## 24. Architecture verdict

**Migration compatibility sunset complete with one operator-local deletion step remaining** (physical removal of ignored `autogen_rp/` directory).

---

## 25. Repository state

*(Updated at commit.)*
