# V2 Repository Retirement — M13.3 Delete Obsolete .NET / Upstream AutoGen Residue

**Status:** Complete  
**Date:** 2026-08-18  
**M13 investigation anchor:** `05dd758`  
**M13.3 completion HEAD:** `c7beebf`

**Objective:** Remove Microsoft AutoGen .NET vendor tree and upstream monorepo infrastructure with zero Holy Grail consumers. No runtime behavior change.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `05dd758` |
| `origin/main` | aligned at activation |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

### Pre-deletion validation

| Suite | Result |
|-------|--------|
| V2 Python | **133 passed, 1 xfailed** |
| V2 Node | **63 passed** |
| Neutral domain | **358 passed** |

---

## 2. Pre-deletion .NET/vendor inventory

| Path | Tracked files | Role |
|------|---------------|------|
| `autogen_rp/dotnet/` | 745 | Microsoft AutoGen .NET SDK, samples, tests, website |
| `autogen_rp/.github/` | 18 | Upstream AutoGen CI workflows (dotnet-build, codeql, python-package, etc.) |
| `autogen_rp/.devcontainer/` | 4 | Upstream AutoGen devcontainer |
| `autogen_rp/.azure/` | 3 | Upstream Azure pipeline templates |
| `autogen_rp/docs/dotnet/` | 16 | Upstream .NET docfx site |
| `autogen_rp/docs/design/` | 7 | Upstream AutoGen agent programming-model docs |
| `autogen_rp/protos/` | 2 | gRPC protos for .NET agent worker |
| `autogen_rp/.cursor/` | 6 | Duplicate Cursor rules (repo root `.cursor/` is authoritative) |
| `autogen_rp/.windsurf/` | 1 | Upstream Windsurf workflow |
| Root upstream files | 8 | `CONTRIBUTING.md`, `FAQ.md`, `LICENSE*`, `codecov.yml`, `autogen-landing.jpg`, etc. |

**Total `autogen_rp` tracked before:** 1,065 files.

---

## 3. Consumer verification

Repository-wide search before deletion:

| Search target | V2 / production consumers |
|---------------|---------------------------|
| `autogen_rp/dotnet` path | **0** (governance historical only) |
| `v2/**` dotnet references | **0** |
| Root `.github/workflows/` | **None** (only Holy Grail issue templates at repo root) |
| `Launch-Holy-Grail-V2.bat` | No dotnet dependency |
| `runtime-config.mjs` | No dotnet dependency |
| Neutral-domain tests | **0** dotnet imports |

**Verdict:** No active Holy Grail consumer. Safe to delete.

---

## 4. Holy Grail modification/value assessment

| Check | Result |
|-------|--------|
| `Holy Grail` / `KizzieFae` in `autogen_rp/dotnet` | **0 matches** |
| Custom RP C# code | **None** |
| Unique generated artifacts required by V2 | **None** |

**Verdict:** Pure upstream Microsoft AutoGen material. No extraction/archive required.

---

## 5. .NET tree deletion

**Removed entirely:** `autogen_rp/dotnet/` (745 files).

Not moved to `legacy/`. Recoverable from upstream AutoGen if ever needed.

---

## 6. Upstream CI/config/devcontainer cleanup

| Removed | Notes |
|---------|-------|
| `autogen_rp/.github/` | All upstream workflows (dotnet-build, release, codeql, python-package-0.2, etc.) |
| `autogen_rp/.devcontainer/` | Upstream dev environment |
| `autogen_rp/.azure/` | Upstream pipeline templates |
| `autogen_rp/docs/dotnet/` | Upstream docfx .NET docs |
| `autogen_rp/docs/design/` | Upstream agent protocol design docs |
| `autogen_rp/protos/` | .NET gRPC protos (no Python/V2 consumer) |
| `autogen_rp/.cursor/` | Duplicate of repo-root `.cursor/rules/` |
| `autogen_rp/.windsurf/` | Upstream workflow |
| Upstream root files | `CONTRIBUTING.md`, `FAQ.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, `LICENSE-CODE`, `codecov.yml`, `autogen-landing.jpg` |

**Preserved:** Repo-root `.github/ISSUE_TEMPLATE/` (Holy Grail templates).

---

## 7. Material intentionally preserved

| Path | Reason |
|------|--------|
| `autogen_rp/python/data/` | Product data — M13.1 |
| `autogen_rp/python/tests/` | 358 neutral-domain tests — M13.2 |
| `autogen_rp/python/validation_runs/` | Historical evidence — later archive |
| `autogen_rp/python/scripts/` | Investigation utilities |
| `autogen_rp/python/pyproject.toml` | Pytest harness |
| `autogen_rp/docs/` (non-dotnet) | HG docs (`rp-data-layout.md`, `scene-grounding-layer.md`, etc.) |
| `autogen_rp/tools/` | HG issue inventory scripts |
| `autogen_rp/.gitignore` | Data gitignore rules |
| `autogen_rp/AGENTS.md`, `README.md` | HG pointers |

---

## 8. Dependency/path residue audit

Post-deletion grep for live references to deleted paths:

- **Only matches:** historical governance records (M12.5, M13 investigation) — allowed.
- **No updates required** to `v2/` code, launcher, or active tests.

Root `README.md` still mentions V1 `rp_app` — deferred to M13.5 docs hygiene.

---

## 9. Post-cleanup `autogen_rp` inventory

| Subtree | Tracked files |
|---------|---------------|
| `python/` | 250 |
| `docs/` | 9 |
| `tools/` | 3 |
| Root (`AGENTS.md`, `README.md`, `.gitignore`) | 3 |
| **Total** | **265** |

**Reduction:** 1,065 → 265 tracked files (**800 files removed**, ~75% of tracked `autogen_rp`).

---

## 10. V2 production architecture proof

Unchanged:

```text
Launch-Holy-Grail-V2.bat
    → v2/rp_runtime (npm run app)
    → HolyGrailRuntimeSupervisor
    → Domain Host (Python, v2/domain_api)
    → DSH orchestrator
```

Supervisor startup smoke: **ready** (mock mode, post-deletion).

---

## 11. Behavioral validation

| Command | Post-deletion result |
|---------|---------------------|
| `python -m pytest v2/tests/ -q` | **133 passed, 1 xfailed** |
| `cd v2/rp_runtime && npm test` | **63 passed** |
| `python -m pytest autogen_rp/python/tests/ -q` | **358 passed** |

No intentional behavioral changes.

---

## 12. Launcher smoke

`HolyGrailRuntimeSupervisor` start/stop in mock mode: **success** (`supervisor_ready true`).

---

## 13. Repository hygiene

- No empty tombstone directories left staged.
- No accidental changes to `autogen_rp/python/data/`, `tests/`, or `validation_runs/`.
- No V2 runtime code modified.
- Root Holy Grail `.github/` issue templates untouched.

---

## 14. Cleanup metrics

| Metric | Value |
|--------|-------|
| Files removed | **810** |
| Lines deleted | **~62,283** |
| .NET files removed | **745** |
| Upstream CI/devcontainer/config | **~65** additional files |
| Residual `autogen_rp` tracked | **265** |
| Remaining executable .NET references in V2 | **0** |

---

## 15. Functional-completion guardrail

Confirmed unchanged: DSH orchestration, Domain Host, MemoryService, KnowledgeService, retrieval, opening, player/settings, session behavior.

**Hygiene only.**

---

## 16. M13.1 readiness

| Criterion | Status |
|-----------|--------|
| Vendor residue mixed with data? | **No** — `python/data/` is clearly isolated |
| .NET dependency constrains data move? | **No** |
| `autogen_rp` conceptually simpler? | **Yes** — only python + docs + tools remain |

**M13.1 (`HG_DATA_DIR` + physical data rehome + session migration) is unblocked.**

---

## 17. Challenge/refinement

| Question | Answer |
|----------|--------|
| Zero consumers verified? | **Yes** — repo-wide search |
| Unique HG code in .NET? | **No** |
| Product data/tests/evidence preserved? | **Yes** |
| Useful Holy Grail CI deleted? | **No** — only upstream `autogen_rp/.github` |
| Remaining `autogen_rp` simpler? | **Yes** — 75% file reduction |
| M13.1 safer? | **Yes** |
| Optional features mixed in? | **No** |

---

## 18. Architecture verdict

**Validated as designed** — complete vendor deletion with zero production impact.

---

## 19. Next recommended slice

**M13.1 — `HG_DATA_DIR` + physical data rehome + existing-session migration.**

Do not implement without Governance review.
