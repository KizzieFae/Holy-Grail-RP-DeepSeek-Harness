# Architecture overview

Engineering view of **Holy Grail RP**. Authoritative product intent: [Holy Grail PRD.md](./Holy%20Grail%20PRD.md).

---

## Three layers

```text
┌─────────────────────────────────────────────────────────────┐
│  Ingestion (static today at the packaging boundary edge)     │
│  Authored JSON → offline canonical compile → index artifact  │
│  (future: entities, relationships, graph/vector stores)      │
└───────────────────────────────┬─────────────────────────────┘
                                │ structured knowledge outputs
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Packaging (bridge — integration seam)                      │
│  Knowledge + authoritative state → per-turn runtime inputs  │
│  Outputs: RuntimeCharacterPacket, RuntimeScenePacket,       │
│            RetrievedContextBundle (see PACKET_CONTRACTS.md)   │
└───────────────────────────────┬─────────────────────────────┘
                                │ bounded prompts / structured context
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  RP execution (Domain Host + DSH runtime)                   │
│  Director phase, character phase, Narrator, validation,     │
│  continuity engine, Scene Grounding, trace/audit           │
└─────────────────────────────────────────────────────────────┘
```

### Dependency direction

- **Ingestion** produces durable knowledge artifacts; it does not call the live turn loop. Today: offline compile of authored sources to a JSON index (`authored_index_compile`, `schema_version` 2 or 3). Runtime reads legacy projection fields on chunks; continuity remains authoritative.
- **Packaging** reads authoritative runtime state and retrieved candidates; it does not replace continuity as source of truth for what happened.
- **RP runtime** executes turns, updates authoritative state, and logs audits.

### System boundaries

| Concern | Layer |
|--------|--------|
| External lore extraction, graph/vector stores | Ingestion (future) |
| Token-bounded turn context selection | Packaging |
| Turn selection, validation, persistence | RP runtime |
| Authoritative scene/issue/knowledge state | RP runtime (continuity) |
| Settled-scene prompt projection | RP runtime → prompts (Scene Grounding — [spec](./docs/scene-grounding-layer.md)) |

**Turn-time roles:** Character emits the contractual structured move. Director owns turn selection and decision fields. Continuity owns issue lifecycle and committed state. Orchestration merges enriched structured history. Narrator renders prose only.

**Continuity authority** ([GitHub #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224)): distinguish intent, interpretation, commit, and observation. See `docs/architecture.md`.

Vector retrieval is for similarity and suggestions, not authoritative truth (PRD §7).

---

## Current system

### Implementation map

| Component | Location |
|-----------|----------|
| Domain library | `v2/domain/modules/` |
| Domain Host | `v2/domain_api/` |
| RP runtime (DSH) | `v2/rp_runtime/` |
| Presentation UI | `v2/ui/streamlit_app.py` |
| Domain tests | `v2/domain/tests/` |
| Product data | `data/` (`HG_DATA_DIR`, `HG_SESSIONS_DIR`) |

### Runtime flow

```text
Presentation (v2/ui/streamlit_app.py)
        ↓ HTTP (Node application API)
RP runtime / DSH (v2/rp_runtime/)
        ↓ HTTP (domain-api-client → Domain Host)
Domain Host (v2/domain_api/)
        ↓
domain modules + SessionManager (v2/domain/modules/)
        ↓
data/  (HG_DATA_DIR)
```

Node calls the Domain Host. Python does not call DSH. The UI is presentation-only.

### Major subsystems

- **Characters:** JSON cards in `data/characters/`; loaded by `v2/domain/character_cards.py` during Host session setup
- **Scenes:** templates in `data/scene_templates/`; openers via `scene_opener.py` and Host `session_setup.py` / DSH opening phase
- **State:** `ContinuityManager`, `SceneState`, excursion pipeline via `continuity_mutation_pipeline` / `process_turn`, committed through Host `commit_move`
- **Turn flow:** DSH round orchestrator and phase plugins (Director → character → Narrator) around Host prepare / validate / commit
- **Memory:** `memory_layer/` plus Host `memory_service.py` — commit-time writes, episodic read/format for prompts
- **Retrieval:** Host `retrieval_selection.py` / `authored_knowledge.py`; env `RP_RETRIEVED_CONTEXT_INDEX`
- **Scene Grounding:** read-only settled-facts projection after continuity commit ([spec](./docs/scene-grounding-layer.md))
- **Packets:** runtime packet seam at the character prompt boundary ([PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)); production assembly is Host projection + `prompt_builders.py`
- **Validation:** `response_validation_*.py` — reject/annotate only; Host `validate_move` / `validate_director_decision` are the call sites
- **Sessions:** Host `SessionRepository` + `session_manager.py`, `data/sessions/`
- **Audits / traces:** DSH `hg-trace-emitter`; optional trees under `data/rp_audits/`

Details and diagnosis order: `docs/architecture.md`, [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md), [MODULE_INDEX.md](./MODULE_INDEX.md).

### Behavioral validation

Scenario manifests (`data/fixtures/progression_simulation_scenarios/`), domain manifest tests, integration tests, and offline audit analysis. Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Future direction

- Cards remain practical source until ingestion + packaging mature; packet contracts describe the runtime-facing shape.
- Canonical compile `schema_version` 3 adds fields at compile time without changing runtime authority.
- Packaging becomes the single merge point for identity, dynamic state, relationships, and retrieved snippets.

Roadmap: `roadmap.md`, GitHub Issues.

---

## Where not to fix things

- Do not move long-horizon truth into prompts or unbounded transcripts.
- Do not treat Director prompt tweaks as the default fix for continuity or orchestration bugs.
- Keep application composition layers thin unless the task explicitly expands them.

---

## How to approach problems

Prefer **continuity → scene grounding → orchestration → summaries → validation → Director → Narrator** before changing prompt copy. Symptom routing: [MODULE_INDEX.md](./MODULE_INDEX.md). Full rules: [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md).

---

## Related docs

- [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)
- [CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md)
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md)
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md)
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)
- [GLOSSARY.md](./GLOSSARY.md)
- [docs/rp-data-layout.md](./docs/rp-data-layout.md)
- [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md)
- [MODULE_INDEX.md](./MODULE_INDEX.md)
- [data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md](./data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md)
