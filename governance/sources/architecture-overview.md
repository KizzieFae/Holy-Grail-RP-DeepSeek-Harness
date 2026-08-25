# Architecture overview

Engineering view of **Holy Grail RP**. Authoritative product intent: [holy-grail-prd.md](./holy-grail-prd.md).

Standing architectural boundaries in this document support Governance review. Detailed mechanisms, module maps, and diagnosis procedures live in repository docs and code — retrieved by Implementation on demand.

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
│            RetrievedContextBundle (see ../PACKET_CONTRACTS.md) │
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

- **Ingestion** produces durable knowledge artifacts; it does not call the live turn loop. Today: offline compile of authored sources to a JSON index under `data/retrieval/`. Runtime reads projection fields on chunks; **continuity remains authoritative**.
- **Packaging** reads authoritative runtime state and retrieved candidates; it does not replace continuity as source of truth for what happened.
- **RP runtime** executes turns, updates authoritative state, and logs audits.

### System boundaries

| Concern | Layer |
|--------|--------|
| External lore extraction, graph/vector stores | Ingestion (future) |
| Token-bounded turn context selection | Packaging |
| Turn selection, validation, persistence | RP runtime |
| Authoritative scene/issue/knowledge state | RP runtime (continuity) |
| Settled-scene prompt projection | RP runtime → prompts (Scene Grounding — [spec](../docs/scene-grounding-layer.md)) |

**Turn-time roles:** Character emits the contractual structured move. Director owns turn selection and decision fields. Continuity owns issue lifecycle and committed state. Orchestration merges enriched structured history. Narrator renders prose only.

Vector retrieval is for similarity and suggestions, not authoritative truth (see [holy-grail-prd.md](./holy-grail-prd.md) design principles).

---

## Narrative intelligence and knowledge boundaries (#33)

**Governance status:** Umbrella architecture program **#33** closed after accepted child consensus (**#31** Retrieval, **#34** Librarian, **#32** Storyteller). Full contracts live on those Issues; this section records standing boundaries only.

### Responsibility decomposition (accepted target)

| Responsibility | Owner | Principle |
|----------------|-------|-----------|
| Candidate access | **Retrieval** (#31) | Finds/accesses eligible information candidates under hard constraints |
| Information mediation | **Librarian** (#34) | Semantically mediates information relevance and bundles |
| Narrative cognition | **Storyteller** (#32) | Understands the story; advisory interpretation only |
| Authoritative truth | **Continuity** | Validates and records committed story truth |
| Manifest assembly | **Packaging** (Host `prepare_*`) | Assembles per-consumer runtime context |

**Contextual intelligence proposes meaning; deterministic authority decides what is legal and records what becomes true.** Use contextual interpretation where meaning genuinely requires context; retain deterministic rules where objective rules are sufficient. Existing Continuity heuristics may be **augmented** where context matters; they are not categorically deprecated.

### Accepted interface flows (target)

```text
Read:   consumer → KnowledgeAccessRequest → Librarian → (live state + #31 candidates) → bundle → reasoning
Write:  commit → Librarian interpretation → LibrarianSemanticProposal → Continuity validate → state
Narrative: state + bundle → Storyteller → StorytellerAdvisoryPackage → Packaging → suggestive role lanes
```

**Hard rules:** Librarian may interpret committed truth; it may not manufacture truth. Storyteller `PreservationSignal` is an attention hint only—not evidence or a persistence proposal. Invalidated Storyteller advice is ineligible for new downstream consumption.

### Implementation status (current vs deferred)

| Capability | At `main` today | Deferred / optional extensions |
|------------|-----------------|--------------------------------|
| **Retrieval** (#31, closed) | **S0+S1 validated** (`58478a1`): role-agnostic `RetrievalAccessRequest` → `RetrievalService` → bounded `RetrievalCandidate[]`; Layer A hard access + Layer B generation hints; backends: authored snapshot, compiled index, scope knowledge (`promoted_learned_world`, `user_profile`); Character compatibility adapter; **no semantic relevance** | Episodic/cross-scope memory behind façade; vector/graph/hybrid backends; round-local cache; formal backend registry |
| **Librarian** (#34, closed) | Read mediation (S2a), Packaging mapper (S2b), grounded proposal seam (S4a), per-knower `knowledge_revelation_significance` (S4b) | Additional proposal-class migrations; Character direct `prepare_context` wiring; cache/scheduling |
| **Storyteller** (#32, closed) | Model A advisory cognition (S3a/S3b/S3c); consumes Librarian bundles; suggestive `storyteller_*` lanes | Narrator policy socket; post-commit refresh |
| **Packaging** | `kernel.prepare_*` deterministic assembly; Librarian bundle mapper; Storyteller lane projection | Character adapter retirement (future integration decision) |

Recommended implementation sequencing (child Issues): **S0** shared contracts → **S1** #31 façade → **S2** #34 read + Packaging mapper → **S3** #32 advisory → **S4** #34 write/proposals → **S5** selective Continuity heuristic migrations. **S4 does not block S3.**

---

## Standing architectural invariants (Governance-critical)

These principles are stable boundaries Governance must protect when reviewing proposals. Implementation retrieves module-level detail when evidence is needed.

### Call direction and ownership

- **Presentation UI** (`v2/ui/`) is a client of the Node application API — not a domain authority.
- **Node / DSH runtime** (`v2/rp_runtime/`) orchestrates inference rounds and calls the Domain Host over HTTP.
- **Domain Host** (`v2/domain_api/`) is the authoritative Python kernel for prepare, validate, commit, and context projection.
- **Domain library** (`v2/domain/modules/`) holds continuity, validation, prompts, memory, and retrieval logic consumed by the Host.
- **Node calls the Domain Host. Python domain code does not call DSH.** Keep the Domain Host the composition boundary.

### Continuity and evidence lanes

- **`ContinuityManager`**, **`SceneState`**, and the commit path (`process_turn` / Host `commit_move`) define **committed** narrative truth.
- Distinguish **intent**, **interpretation**, **commit**, and **observation** ([GitHub #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224)).
- **Narrator rendered prose**, classifier tags, audit mirrors, and orchestration **consequences** are **observational or auxiliary** unless they reflect already-committed facts. They do **not** override committed continuity.

### Advisory vs authoritative mechanisms

- **Progression advisory** (pressure/progression guidance) is **advisory only** — it must **not** write continuity truth or mutate `CharacterState` outside its intended ownership.
- **Scene Grounding** is a **read-only projection** of settled scene facts into prompts — **not** a second source of truth ([product spec](../docs/scene-grounding-layer.md)).
- **Retrieval** and **memory-derived prompt material** are **non-authoritative** relative to canonical continuity unless explicitly documented otherwise.

### Validation and Director boundaries

- **Validators** (`response_validation_*.py`, Host `validate_move` / `validate_director_decision`) may **reject or annotate**; they do **not** replace Director selection or continuity commits.
- **Director prompt edits** are **not** the default substitute for correcting authoritative continuity, orchestration, or state defects.
- Do not move long-horizon truth into prompts or unbounded transcripts.

### Behavioral validation expectation

Major **behaviorally meaningful** changes should be evidenced with **scenario-grade validation** appropriate to the change — not unit tests alone. Canonical scenario framework (Implementation retrieval): [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

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

### Major subsystems (summary)

- **Characters / scenes:** authored JSON under `data/`; Host session setup + DSH opening phase
- **State / turn flow:** DSH phase plugins around Host prepare / validate / commit
- **Memory:** commit-time writes; episodic read/format for prompts (`memory_layer/`, Host `memory_service.py`)
- **Retrieval:** non-authoritative; **#31 S0+S1 façade implemented** (`retrieval_contract.py`, `retrieval_service.py`, `character_retrieval_adapter.py`); episodic/cross-scope memory remains on parallel `memory_service` path (not yet routed through façade)
- **Librarian / Storyteller:** **#34 / #32 implemented and closed**; Librarian owns contextual semantic mediation; Storyteller owns advisory narrative cognition; neither performs Retrieval candidate access or Continuity commits
- **Scene Grounding:** read-only settled-facts projection after continuity commit
- **Validation:** reject/annotate only at Host call sites
- **Sessions / audits:** Host `SessionRepository`; DSH trace emitter; optional `data/rp_audits/`

Implementation detail and diagnosis order: [docs/architecture.md](../docs/architecture.md), [DEBUGGING_GUIDE.md](../DEBUGGING_GUIDE.md), [MODULE_INDEX.md](../MODULE_INDEX.md).

---

## Future direction

- Cards remain practical source until ingestion + packaging mature.
- Packaging becomes the single merge point for identity, dynamic state, relationships, and retrieved snippets.

Provisional sequencing references (not current authority): [governance/records/narrative-memory-evolution-roadmap.md](../governance/records/narrative-memory-evolution-roadmap.md), GitHub Issues.

---

## Related docs (Implementation retrieval)

- [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md)
- [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md)
- [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md)
- [GLOSSARY.md](../GLOSSARY.md)
- [docs/rp-data-layout.md](../docs/rp-data-layout.md)
