# Holy Grail RP

**Holy Grail RP** is a multi-agent roleplay system with **persistent scenes**, **continuity-aware state**, and **Director-mediated turn flow**. Production code lives under **`v2/`**; canonical product data under **`data/`**.

---

## What it is

Holy Grail RP combines:

- a **domain library** (`v2/domain/modules/`) — continuity, orchestration, prompts, validation, memory, retrieval
- a **Domain Host** (`v2/domain_api/`) — authoritative Python kernel and transport-neutral Domain API
- an **RP runtime** (`v2/rp_runtime/`) — DSH/Cordis orchestration for inference rounds
- an **application client** — UI and session wiring (see `v2/ui/` when present)

**Principle:** Holy Grail determines what is true. The runtime records what happened.

---

## Quick start

| Step | Command |
|------|---------|
| Python environment | From repo root: `python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"` |
| Launch | `Launch-Holy-Grail-V2.bat` (starts Node supervisor → Domain Host → DSH) |
| Domain tests | `python -m pytest v2/domain/tests/ -q` |
| Integration tests | `python -m pytest v2/tests/ -q` |
| RP runtime tests | `cd v2/rp_runtime && npm test` |

**Environment overrides (optional):**

| Variable | Purpose |
|----------|---------|
| `HG_PYTHON_EXECUTABLE` | Domain Host Python (default: repo-root `.venv`) |
| `HG_DATA_DIR` | Product data root (default: `data/`) |
| `HG_SESSIONS_DIR` | Session persistence root (default: `data/sessions/`) |
| `DEEPSEEK_API_KEY` | Live inference when using real provider paths |

---

## Start here (documentation)

| If you need… | Read |
|--------------|------|
| Product goals and MVP boundaries | [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) |
| Three-layer model and runtime boundaries | [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) |
| **Where to change code** (symptom → module) | [MODULE_INDEX.md](./MODULE_INDEX.md) |
| Behavioral validation (scenarios, audits, metrics) | [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) |
| **Persistence and on-disk layout** | [docs/rp-data-layout.md](./docs/rp-data-layout.md) |
| Debugging order | [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) |
| Runtime packet contracts | [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) |
| Shared vocabulary | [GLOSSARY.md](./GLOSSARY.md) |
| Scene Grounding (settled facts / prompt contract) | [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md) |
| AI / contributor working rules | [AGENTS.md](./AGENTS.md) |

---

## Repository layout

```text
v2/
  domain/           # Framework-neutral domain library
  domain_api/       # Domain Host (authoritative kernel)
  rp_runtime/       # DSH/Cordis RP orchestration
  tests/            # Integration / architecture tests
data/               # Canonical product data (HG_DATA_DIR)
tools/
  investigation/    # Offline audit analysis and experiment comparators
  maintenance/      # Local hygiene utilities
docs/               # Shared technical documentation
governance/         # Issue workflow, policies, program history
```

**Investigation output:** write under `data/investigation_runs/` (gitignored), not the repository root.

---

## Dependency direction (summary)

**Ingestion** (offline compile of authored sources) → **packaging** (bounded turn context / packets) → **RP runtime** (turn execution, continuity commits, audits).

Retrieval and vectors are **not** authoritative truth; continuity and orchestration remain domain responsibilities. Details: [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md).

---

## Governance

Tracked work, workflow weights, and bootstrap profiles: [governance/README.md](./governance/README.md), [docs/issue-bootstrap-profiles.md](./docs/issue-bootstrap-profiles.md).
