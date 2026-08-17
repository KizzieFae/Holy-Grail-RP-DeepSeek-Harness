# Checkpoint Report — Holy Grail RP DeepSeek Harness Baseline

**Date:** 2026-03-17  
**Phase:** V2 baseline complete (no DSH migration started)  
**Repository:** https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness  
**Pre-baseline anchor:** `9fb626e50f581931e8ecacb10f9efb91c4a2ce98`  
**Baseline commit:** *(recorded after push — see § Commit below)*

**Boundary statement:** Holy Grail V2 baseline established and architecture mapped; DeepSeek Harness implementation has not begun.

---

## 1. Baseline status

### Repository

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-baseline HEAD | `9fb626e50f581931e8ecacb10f9efb91c4a2ce98` |
| Baseline commit HEAD | *(see commit section below)* |
| Upstream (read-only) | `KizzieFae/Holy_Grail_RP` (remote `upstream`) |
| Working tree | Clean after baseline commit |

### Environment

| Component | Version / path |
|-----------|----------------|
| Python (venv) | 3.12.7 |
| Virtual environment | `autogen_rp/python/.venv` (independent; not shared with upstream checkout) |
| Package manager | `uv 0.10.9` |
| Install command | `uv sync --all-extras` (from `autogen_rp/python`) |
| Packages installed | 502 |
| Streamlit | 1.41.1 (verified import) |
| OS | Windows 10.0.26200 |

**DSH:** Not installed (per baseline constraints).

### Dependency installation

```powershell
cd autogen_rp/python
uv sync --all-extras
.\.venv\Scripts\Activate.ps1
```

Dependencies match upstream lockfile; no arbitrary upgrades performed.

### Smoke checks (final, after local provisioning)

| Check | Command / method | Result |
|-------|------------------|--------|
| Venv isolated | `sys.executable` → harness `.venv` path | Pass |
| Character cards | `CharacterLoader.list_available_characters()` | **17 cards** discovered |
| Core deterministic tests | `pytest tests/test_continuity_manager.py … test_progression_enforcement.py -q` | **107 passed** |
| Full non-LLM suite | `pytest tests/ -m "not llm" -q` | **1361 passed, 1 failed, 2 skipped, 13 deselected** |
| Scene templates loadable | 20 JSON files in `data/scene_templates/` | Pass |
| Scenario manifests | 40 JSON files in `progression_simulation_scenarios/` | Pass |
| Character cards on disk | `data/autogen_characters/` | **22 JSON files** (gitignored; copied from original env) |
| RP audit fixture | `rp_app/data/rp_audits/session_908/` | **Copied locally** (gitignored; required by `test_i251_replay_adjudication`) |
| Path independence | No harness-specific hardcoded paths in code | Pass; historical `validation_runs` JSON still references old checkout paths |

### Application startup

Streamlit verified runnable (`streamlit run rp_app/app.py` from `autogen_rp/python`) with `DEEPSEEK_API_KEY` set. After character-card restoration, the UI can discover characters.

### Local provisioning (not committed)

Copied from original Holy Grail environment at `E:\CascadeProjects\Holy Grail RP\` (copy only; originals untouched):

| Content | Source | Destination | Files |
|---------|--------|-------------|-------|
| Character cards | `…/data/autogen_characters/*.json` | `autogen_rp/python/data/autogen_characters/` | 22 |
| Issue #251 audit fixture | `…/rp_app/data/rp_audits/session_908/` | `autogen_rp/python/rp_app/data/rp_audits/session_908/` | 1 session folder |

Both remain **gitignored** per existing policy (`autogen_rp/.gitignore`).

### Remaining failures (understood, pre-existing)

1. **`test_descriptive_exit_updates_authoritative_presence_state`** — **Pre-existing** on both harness and original checkout at the same code revision. Continuity retains Mira in `present_characters` with delta *"on-stage presence is retained per scene constraints"*; test expects removal to `absent_but_relevant`. This is **test/implementation drift**, not a harness clone or provisioning defect. Not fixed in baseline scope.

2. **Resolved by provisioning:** 11 of 12 character-card-related failures cleared after card restore; `test_merge_matrix_minimal` cleared after `session_908` audit copy.

### Other known limitations

- **Stale absolute paths** in `validation_runs/plan_execution/*.json` and issue249 result JSON — historical pointers to `E:\CascadeProjects\Holy Grail RP\…`; documentation only.
- **LLM-marked tests** (`13 deselected` with `-m "not llm"`) require `DEEPSEEK_API_KEY` for live runs.
- **DSH not installed** — intentional baseline boundary.

### Checkpoint criteria

```text
Holy Grail RP DeepSeek Harness
├── independent repository          ✓
├── independent environment         ✓
├── existing dependencies installed ✓
├── existing application loads      ✓ (API key + local character cards)
├── baseline checks understood      ✓ (1361/1362 non-LLM; 1 pre-existing failure documented)
└── baseline revision committed     ✓
```

---

## 2. V2 authority

| Item | Detail |
|------|--------|
| Document | `governance/rp-app/v2-dsh-replatforming-authority.md` |
| Summary | Establishes behavioral-preservation re-platforming onto DSH; behavioral authority = existing HG semantics; structural freedom for V2; DSH as composition substrate; strict domain truth vs execution history split; knowledge backend independence; migration cost not primary criterion |

---

## 3. Existing behavioral evidence

| Item | Detail |
|------|--------|
| Inventory doc | `governance/rp-app/v2-behavioral-evidence-inventory.md` |
| Strong coverage | Continuity, validation, perception, retrieval seam, progression, scene templates, scenario manifests, deterministic tests |
| Weak / missing | Full historical `rp_audits/session_*` corpus (optional); some issue251 JSON matrices |
| Local provisioning | Character cards (22 files) + `session_908` audit fixture copied from original environment |
| Gaps | No DSH-specific evidence; LLM tests require API key |

---

## 4. DSH revision evaluated

| Field | Value |
|-------|-------|
| Package | `@deepseek-ai/dsh@0.1.0-rc.7` |
| Cordis | `@deepseek-ai/cordis@4.0.1` |
| Commit SHA | Not pinned (preview; evaluate at implementation start) |
| Primary sources | [github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness), [deepseek-harness.github.io](https://deepseek-harness.github.io/deepseek-harness/en/), agent lifecycle, session subsystem, services/events framework docs |
| License | MIT (per public announcements) |
| Maturity | Developer preview — breaking changes expected |

---

## 5. Capability mapping

Full table: `governance/rp-app/v2-capability-dsh-mapping.md`

**Headline mappings:**

- **Round lifecycle** → custom DSH agent-loop plugin + HG RoundOrchestrator (Split)
- **Director / Character / Narrator** → HG domain services + scoped DSH agents (Re-express / Split)
- **Continuity / CharacterState** → HG domain services, preserved (Preserve)
- **Perception / Grounding / Retrieval** → HG projection services → DSH system-prompt contributions (Split)
- **Model invocation** → DSH `ctx.llm` (Replace AutoGen)
- **Audits / Sessions** → split HG domain artifacts vs DSH session log (Split)

---

## 6. Proposed V2 architecture

See `governance/rp-app/v2-capability-dsh-mapping.md` for mermaid diagrams.

**Summary:** External HG UI → RoundOrchestrator → domain services (Continuity, Validation, ContextAssembly) → DSH custom loop + scoped agents + LLM adapter + session event log. Holy Grail commits truth after validation; DSH records execution.

---

## 7. State ownership model

| Class | Examples | Owner |
|-------|----------|-------|
| **Holy Grail domain truth** | SceneState, issues, character state, relationships, canon, committed memories | HG services + domain persistence |
| **DSH execution history** | Model requests/responses, session events, tool activity, token usage, retries | DSH session log + persistence |
| **Derived model-visible context** | Prompt sections, perception-filtered dialogue, retrieval snippets, grounding blocks | HG ContextAssembly → DSH contributions (ephemeral, derived from truth) |

**Principle:** Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 8. Simplification opportunities

- AutoGen `model_client` agent factories → DSH agents + adapters
- Façade re-export modules → collapse under stable V2 API
- Ad-hoc prompt concatenation → DSH system-prompt contribution pipeline
- Manual model I/O audit capture → DSH session/event trace (with HG correlation fields)
- Dual packet/live bundle derivation → single ContextAssembly service

---

## 9. Architectural uncertainties

1. Python (HG domain) ↔ TypeScript (DSH) bridge strategy  
2. Custom loop design vs multi-agent DSH composition  
3. Session model: per-scene vs per-character DSH sessions  
4. Validation retry mapping to DSH lifecycle hooks  
5. Streamlit integration pattern during transition  
6. Audit timeline unification vs dual artifacts  
7. DSH API stability (RC)  
8. Headless driver packaging  

See full list in `v2-capability-dsh-mapping.md`.

---

## 10. Next architectural decision (not implementation)

Before any DSH vertical slice, decide:

> **Determine the optimal Python Holy Grail domain ↔ DeepSeek Harness runtime boundary, including whether the cleanest long-term architecture uses a process/service boundary, progressive TypeScript re-expression, or another DSH-native integration model.**

Evaluate **DSH session topology** (per-scene vs per-character vs per-actor sessions) alongside this decision — the two may constrain each other.

**Deferred (do not implement yet):** single-character DSH vertical slice, custom agent loop, Streamlit/DSH wiring, audit unification.

---

## Operator provisioning reference

New harness checkouts require local copy (not committed):

1. `autogen_rp/python/data/autogen_characters/*.json` from original Holy Grail environment
2. Optionally `rp_app/data/rp_audits/session_908/` for full i251 adjudication test coverage
3. `DEEPSEEK_API_KEY` for LLM-marked tests and live runs

---

## Document index

| Document | Path |
|----------|------|
| V2 authority | `governance/rp-app/v2-dsh-replatforming-authority.md` |
| Evidence inventory | `governance/rp-app/v2-behavioral-evidence-inventory.md` |
| Capability mapping + target arch | `governance/rp-app/v2-capability-dsh-mapping.md` |
| This checkpoint | `CHECKPOINT_BASELINE_DSH.md` |
