# Repository map

Quick orientation for humans and AI tools working in **Holy Grail RP**.

---

## Top level

| Path | Role |
|------|------|
| `README.md` | Product overview, quick start, doc index |
| `AGENTS.md` | Repo-level AI working rules and instruction priority |
| `ARCHITECTURE_OVERVIEW.md` | Product architecture and layer boundaries |
| `MODULE_INDEX.md` | Symptom → module map (`v2/domain/modules/`) |
| `docs/` | Shared technical documentation |
| `v2/` | Production implementation (domain, Domain Host, RP runtime) |
| `data/` | Canonical product data (`HG_DATA_DIR`) |
| `tools/` | Offline investigation and maintenance utilities |
| `governance/` | Issue workflow, policies, program records |

---

## Production code (`v2/`)

| Path | Role |
|------|------|
| `v2/domain/modules/` | Domain library — continuity, orchestration, prompts, validation, memory, retrieval |
| `v2/domain_api/` | Domain Host — authoritative kernel and Domain API transport |
| `v2/domain/tests/` | Framework-neutral domain contract tests |
| `v2/rp_runtime/` | DSH/Cordis orchestration (HgRoundOrchestrator, inference wiring) |
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
| Continuity / scene state bug | `v2/domain/modules/continuity_manager.py` |
| Turn selection / orchestration | `v2/domain/modules/orchestration_helpers.py`, `app_turn_director.py` |
| Character prompts | `v2/domain/modules/app_turn_prompting.py`, `prompt_builders.py` |
| Validation failures | `v2/domain/modules/response_validation*.py` |
| Session save/load | `v2/domain/modules/session_manager.py`, `session_lifecycle_*.py` |
| Domain API / Host | `v2/domain_api/` |
| DSH round orchestration | `v2/rp_runtime/src/plugins/hg-round-orchestrator/` |
| Audits | `v2/domain/modules/audit_logger*.py`, [audit-workflows.md](./audit-workflows.md) |

Full symptom routing: [MODULE_INDEX.md](../MODULE_INDEX.md).

---

## Governance

| Path | Role |
|------|------|
| `governance/policies/` | Canonical policy corpus (Cursor rules `@`-include these) |
| `governance/rp-app/` | Issue tracking workflow and program records |
| `governance/README.md` | Governance layout; distinguishes current authorities from historical records |

Program closure record: `governance/rp-app/fresh-start-m14-5-program-closure.md`. Removed migration-era records live in Git history only.
