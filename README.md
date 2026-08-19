# Holy Grail RP DeepSeek Harness

**Behavioral-preservation re-platforming** of [Holy Grail RP](https://github.com/KizzieFae/Holy_Grail_RP) onto [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness). Production runtime, domain library, and tests live under **`v2/`**; historical V1 material is archived under **`governance/archive/`**.

**Start here for harness work:** [CHECKPOINT_BASELINE_DSH.md](./CHECKPOINT_BASELINE_DSH.md) · [V2 authority](./governance/rp-app/v2-dsh-replatforming-authority.md)

---

Multi-agent roleplay system: **persistent scenes**, **continuity-aware state**, and **Director-mediated turn flow**. Holy Grail V2 runs on the DeepSeek Harness substrate with a framework-neutral domain library (`v2/domain/`).

## Start here

| If you need… | Read |
|--------------|------|
| Product goals, layers, non-goals (incl. **Progression Advisory** §5.7, **Scene Grounding** §5.8) | [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) |
| Three-layer model (ingestion → packaging → runtime) and boundaries | [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) |
| **Where to change code** (symptom → module) | [MODULE_INDEX.md](./MODULE_INDEX.md) |
| **Behavioral validation** (scenarios, headless LLM runs, audits, baseline vs treatment) | [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) |
| **Persistence, files on disk, audits** | [docs/rp-data-layout.md](./docs/rp-data-layout.md) |
| Debugging order / avoid wrong-layer fixes | [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) |
| Future runtime input shapes (packets) | [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) |
| Shared vocabulary | [GLOSSARY.md](./GLOSSARY.md) |
| **Scene Grounding** (settled facts / prompt contract; implementation spec) | [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md) |

## V2 production quick start

| Step | Command |
|------|---------|
| Python environment | From repo root: `python -m venv .venv` then `pip install -e ".[dev]"` |
| Launch V2 | `Launch-Holy-Grail-V2.bat` (Node supervisor → Domain Host → DSH) |
| Domain tests | `python -m pytest v2/domain/tests/ -q` |

## Repository layout

- **`v2/`** — Production runtime, domain API, domain library, and tests.
- **`data/`** — Canonical product data (`HG_DATA_DIR`).
- **`tools/investigation/`** — Offline investigation and validation utilities.
- **`docs/`** — Shared technical docs (architecture, audits, data layout, testing).
- **`governance/archive/`** — Historical evidence and V1 runtime documentation.

- **Headless simulation tee / redirect:** Do not write ad-hoc console captures to the repository root. Historical validation evidence: [`governance/archive/validation-runs/`](./governance/archive/validation-runs/README.md) — see [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) (*Console captures*).

## Quick pointers

- **Launch V2:** `Launch-Holy-Grail-V2.bat`
- **Investigation tooling:** [`tools/investigation/`](./tools/investigation/README.md)
- **V1 runtime archive:** [`governance/archive/v1-runtime/`](./governance/archive/v1-runtime/README.md)
- **Tests:** `python -m pytest v2/domain/tests/ -q` and `python -m pytest v2/tests/ -q`; see [docs/testing.md](./docs/testing.md)

## Dependency direction (summary)

**Ingestion** (future) → **packaging** (bridge; packets + retrieval) → **RP runtime** (`v2/rp_runtime` + `v2/domain`). Retrieval and vectors are **not** authoritative truth; continuity and orchestration remain domain responsibilities. Details: [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md).
