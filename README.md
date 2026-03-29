# Holy Grail RP

Multi-agent roleplay system: **persistent scenes**, **continuity-aware state**, and **Director-mediated turn flow**, implemented on an AutoGen-based runtime. The product evolves from **card-based, scene-forward** operation toward a **knowledge-driven, packet-based** architecture (see PRD).

## Start here

| If you need… | Read |
|--------------|------|
| Product goals, layers, non-goals (incl. **Progression Advisory** §5.7, **Scene Grounding** §5.8) | [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) |
| Three-layer model (ingestion → packaging → runtime) and boundaries | [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) |
| **Where to change code** (symptom → module) | [MODULE_INDEX.md](./MODULE_INDEX.md) |
| **Persistence, files on disk, audits** | [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md) |
| Debugging order / avoid wrong-layer fixes | [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) |
| Future runtime input shapes (packets) | [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) |
| Shared vocabulary | [GLOSSARY.md](./GLOSSARY.md) |
| **Scene Grounding** (settled facts / prompt contract; implementation spec) | [autogen_rp/docs/scene-grounding-layer.md](./autogen_rp/docs/scene-grounding-layer.md) |

## Repository layout

- **`autogen_rp/`** — AutoGen monorepo fork. Active RP work lives under **`autogen_rp/python/rp_app/`** (Streamlit app, continuity, validation, audits).
- **`autogen_rp/AGENTS.md`** — AI assistant working rules for this subtree.
- **`autogen_rp/docs/`** — Shared technical docs (repo map, testing, audit workflows, [rp-data layout](./autogen_rp/docs/rp-data-layout.md), [scene-grounding-layer](./autogen_rp/docs/scene-grounding-layer.md)).
## RP app quick pointers

- Run (from `autogen_rp/python`): `streamlit run rp_app/app.py` (see `autogen_rp/python/rp_app/README.md` for setup).
- Deep runtime architecture: `autogen_rp/python/rp_app/ARCHITECTURE.md`
- Audit artifacts: `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`
- Engineering roadmap / packet-layer checklist: `autogen_rp/python/RP_SETUP_TODO.md`
- **Tests:** default `pytest` from `autogen_rp/python` runs `tests/` only; optional vendored-package deps: [autogen_rp/docs/testing.md](./autogen_rp/docs/testing.md)

## Dependency direction (summary)

**Ingestion** (future) → **packaging** (bridge; packets + retrieval) → **RP runtime** (current `rp_app`; AutoGen execution). Retrieval and vectors are **not** authoritative truth; continuity and orchestration remain runtime responsibilities. Details: [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md).
