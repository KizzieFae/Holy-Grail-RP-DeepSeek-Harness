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

## Operator quick start

From a **clean clone**, provision once then launch. Prerequisites: **Python 3.10+**, **Node.js** (LTS recommended), and a terminal at the repository root.

### 1. Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

POSIX:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Python application dependencies

Installs Streamlit for the UI and registers this repo as a dependency-only meta package (Domain Host code is loaded via `PYTHONPATH`, not packaged):

```bash
pip install -e ".[app]"
```

Contributors running tests also need dev dependencies:

```bash
pip install -e ".[app,dev]"
```

### 3. Node dependencies

```bash
cd v2/rp_runtime
npm ci
cd ../..
```

Use `npm ci` on clean clones (committed `package-lock.json`). `npm install` works but is not the preferred reproducible path.

### 4. Inference configuration

Choose **one**:

| Mode | Setup |
|------|--------|
| **Live DeepSeek** (default) | Set `DEEPSEEK_API_KEY` to your API key. Leave `HG_INFERENCE_MODE` unset. |
| **Mock** (no API key) | Set `HG_INFERENCE_MODE=mock` before launch — useful for first-run smoke tests without live inference. |

Optional: `HG_SKIP_STREAMLIT=1` starts the application API only (no Streamlit process).

### 5. Character cards on a clean clone

`data/characters/` is **local and gitignored**. A fresh clone has an **empty catalog**. The UI shows a warning and uses **prototype cast** mode (default cast name `Alice`). You can create a session and explore without adding cards.

To use character cards, add JSON files under `data/characters/` per [docs/rp-data-layout.md](./docs/rp-data-layout.md). Scene templates under `data/scene_templates/` are tracked in-repo when present.

### 6. Launch (Windows)

From the repository root:

```powershell
Launch-Holy-Grail-RP.bat
```

This runs `npm run app` in `v2/rp_runtime`, which starts the Node supervisor, Domain Host, DSH runtime, and Streamlit.

### 7. Readiness

When startup succeeds, the console prints JSON including:

- `application_api_url` — Node application API base URL
- `"streamlit": "started"` when the UI process launched

You should also see `[hg-app] press Ctrl+C to stop`.

### 8. UI access

Open **http://localhost:8501** in a browser (Streamlit default). Use the sidebar to create a session (prototype cast works on a clean clone) or resume an existing session id.

### 9. Shutdown

Press **Ctrl+C** in the terminal running the application. The supervisor stops Streamlit, the application API, and the Domain Host.

### 10. Launch (POSIX / direct)

From the repository root (with inference env vars set as above):

```bash
cd v2/rp_runtime
npm run app
```

There is no POSIX shell launcher at the repository root; this is the supported cross-platform entry point.

### Development commands

| Task | Command |
|------|---------|
| Domain tests | `python -m pytest v2/domain/tests/ -q` |
| Integration / architecture tests | `python -m pytest v2/tests/ -q` |
| RP runtime tests | `cd v2/rp_runtime && npm test` |

Implementation-tree detail: [v2/README.md](./v2/README.md).

**Environment overrides (optional):**

| Variable | Purpose |
|----------|---------|
| `HG_PYTHON_EXECUTABLE` | Domain Host Python (default: repo-root `.venv`) |
| `HG_DATA_DIR` | Product data root (default: `data/`) |
| `HG_SESSIONS_DIR` | Session persistence root (default: `data/sessions/`) |
| `DEEPSEEK_API_KEY` | Live DeepSeek inference (required unless `HG_INFERENCE_MODE=mock`) |
| `HG_INFERENCE_MODE` | Set to `mock` for mock inference (no API key) |
| `HG_SKIP_STREAMLIT` | Set to `1` to skip spawning Streamlit |
| `HG_APP_PORT` | Application API listen port (default: ephemeral) |

---

## Start here (documentation)

| If you need… | Read |
|--------------|------|
| Product goals and MVP boundaries | [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md) |
| Three-layer model and runtime boundaries | [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md) |
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
governance/         # Governance upload corpus, execution policies, program records
```

**Investigation output:** write under `data/investigation_runs/` (gitignored), not the repository root.

---

## Dependency direction (summary)

**Ingestion** (offline compile of authored sources) → **packaging** (bounded turn context / packets) → **RP runtime** (turn execution, continuity commits, audits).

Retrieval and vectors are **not** authoritative truth; continuity and orchestration remain domain responsibilities. Details: [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md).

---

## Governance

Tracked work, workflow weights, and bootstrap profiles: [governance/README.md](./governance/README.md), [docs/issue-bootstrap-profiles.md](./docs/issue-bootstrap-profiles.md).
