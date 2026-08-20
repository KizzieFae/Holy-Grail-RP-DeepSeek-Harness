# Repository map

Quick orientation for humans and AI tools working in **Holy Grail RP**.

---

## Top level

| Path | Role |
|------|------|
| `README.md` | Product overview, quick start, doc index |
| `AGENTS.md` | Repo-level AI working rules and instruction priority |
| `governance/sources/architecture-overview.md` | Product architecture and layer boundaries |
| `governance/sources/holy-grail-prd.md` | Product requirements and intent |
| `MODULE_INDEX.md` | Symptom → current implementation owner |
| `docs/` | Shared technical documentation |
| `v2/` | Production implementation (domain, Domain Host, RP runtime, UI) |
| `data/` | Canonical product data (`HG_DATA_DIR`) |
| `tools/` | Offline investigation and maintenance utilities |
| `governance/` | Governance sources, execution policies, and records (`governance/README.md`) |

---

## Production code (`v2/`)

| Path | Role |
|------|------|
| `v2/domain/modules/` | Domain library — continuity, prompts, validation, memory, retrieval |
| `v2/domain_api/` | Domain Host — authoritative kernel and Domain API transport |
| `v2/domain/tests/` | Framework-neutral domain contract tests |
| `v2/rp_runtime/` | DSH/Cordis orchestration (`HgRoundOrchestrator`, phase executors, inference wiring) |
| `v2/ui/` | Presentation client (`streamlit_app.py` — HTTP to the Node application API) |
| `v2/tests/` | Integration and repository architecture tests |
| `v2/README.md` | Implementation tree layout and local run commands |

**Launch:** `Launch-Holy-Grail-RP.bat` → `v2/rp_runtime` supervisor.

---

## Data (`data/`)

| Path | Role |
|------|------|
| `data/characters/` | Character cards |
| `data/scene_templates/` | Scene template definitions and template-associated assets |
| `data/retrieval/` | Authored retrieval manifests and compiled index examples |
| `data/fixtures/` | Tracked investigation and evaluation fixtures (includes scenario manifests) |
| `data/sessions/` | Persisted RP sessions |
| `data/rp_audits/` | Optional per-turn audit trees (local, gitignored) |

Details: [rp-data-layout.md](./rp-data-layout.md).

---

## Tools

| Path | Role |
|------|------|
| `tools/investigation/` | Offline audit readers and experiment comparators — [README](../tools/investigation/README.md) |
| `tools/maintenance/` | Local inventory and hygiene — [README](../tools/maintenance/README.md) |
| `tools/_repo_paths.py` | Neutral path helpers for tooling |

---

## First files for common tasks

| Task | Start here |
|------|------------|
| Continuity / scene state bug | `v2/domain/modules/continuity_manager.py`; Host `v2/domain_api/kernel.py` (`commit_move`) |
| Turn selection / who acts next | `v2/domain_api/participation_policy.py`, `v2/rp_runtime/src/plugins/hg-round-orchestrator/`, `v2/rp_runtime/src/plugins/hg-phase-executors/director-phase.mjs` |
| Character / Director / Narrator prompts | `v2/domain_api/continuity_context_projector.py`, `v2/domain/modules/prompt_builders.py`; transport `v2/rp_runtime/src/plugins/hg-context-bridge/` |
| Validation failures | `v2/domain/modules/response_validation*.py`; Host `validate_move` / `validate_director_decision` |
| Session save/load | `v2/domain_api/session_repository.py`, `v2/domain/modules/session_manager.py` |
| Domain API / Host | `v2/domain_api/` |
| DSH round orchestration | `v2/rp_runtime/src/plugins/hg-round-orchestrator/` |
| UI-only behavior | `v2/ui/streamlit_app.py` |
| Audits / traces | `v2/rp_runtime/src/plugins/hg-trace-emitter/`, Host `session_history.py`, [audit-workflows.md](./audit-workflows.md) |

Full symptom routing: [MODULE_INDEX.md](../MODULE_INDEX.md).

---

## Governance

| Path | Role |
|------|------|
| `governance/sources/` | Governance-AI source authorities (workflow, weights, Issue/Project, audit semantics) |
| `governance/execution/` | Implementation-AI execution policies (Cursor `@`-included) |
| `governance/records/` | Historical, workshop, and program records (not current authority) |
| `governance/README.md` | A/B/C/D layout and **Creating governance documents** placement rules |

Program closure record: `governance/records/fresh-start-m14-5-program-closure.md`. Removed migration-era records live in Git history only.
