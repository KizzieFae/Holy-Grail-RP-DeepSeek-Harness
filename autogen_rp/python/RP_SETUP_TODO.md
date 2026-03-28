# RP App – PRD-Aligned Step-by-Step Roadmap

**Goal**: Multi-agent RP system with persistent, resumable scenes, structured character output, continuity engine, and Director/Narrator orchestration — evolving toward a knowledge-driven architecture with dynamic character packets.

This roadmap preserves the current working system while introducing a **Packet Layer** to enable future integration with retrieval, graph storage, and knowledge extraction.

---

## 0. Scope & Core Rules

- [x] Define scene and turn rules: user present, bots act, turn limits, must-remain characters  
- [x] Character success criteria: in-character behavior, knowledge boundaries, voice preservation  
- [x] Session termination rules: explicit end, scene replacement, or interrupted session finalization  

---

## 0.5 Packet Layer (NEW – CRITICAL)

**Purpose**: Introduce a clean interface between data and runtime.

- [ ] Define `RuntimeCharacterPacket` schema
- [ ] Define `RuntimeScenePacket` schema
- [ ] Define `RetrievedContextBundle`
- [ ] Create `packet_builder` module
- [ ] Route all character input through packet builder
- [ ] Map existing character cards → packet format (no behavior change yet)
- [ ] Ensure packet structure separates:
  - identity (stable)
  - state (dynamic)
  - relationships
  - context
- [ ] Add tests for packet construction

---

## 1. Core System Foundations

- [x] Load character cards (`python/data/autogen_characters/`) and create agents  
- [x] Streamlit RP scenes with session save/load  
- [x] Director-controlled turn selection  
- [x] Narrator rendering with verbatim dialogue preservation  
- [x] Structured character output: `action`, `dialogue`, `motivation`  
- [x] Track per-character private state and identity anchors  
- [x] Add audit logging and repeatable Director scenario validation  

### Adjustments

- [ ] Ensure character agents consume **RuntimeCharacterPacket**, not raw cards  
- [ ] Separate system prompt scaffolding from character data  

---

## 2. Continuity & State Engine (Reframed)

**Purpose**: Maintain authoritative structured state.  
No longer responsible for direct prompt injection.

- [x] Model durable structures:
  - scene state
  - issue/pressure state
  - public events
  - character interpretations
  - canon anchors  

- [x] Strengthen scene state:
  - participants
  - environment
  - phase
  - recent delta  

- [x] Track issue/pressure lifecycles:
  - active
  - escalating
  - stalled
  - resolved  

- [x] Canon anchors for stable character/world truths  

### Continuity Manager Responsibilities

- [x] Promote key dialogue/actions to events  
- [x] Update issue/pressure and scene state  
- [x] Update character interpretation memory  
- [x] Enforce knowledge boundaries  

---

### New Additions

- [ ] Distinguish:
  - authoritative state (truth)
  - retrievable context (candidate input)
- [ ] Tag memory with:
  - participants
  - issue linkage
  - recency
  - emotional weight
  - significance
- [ ] Prepare memory for **selection by packet builder**, not direct prompt use  

---

## 3. Refactor & Safety Net (Development-Focused)

### 3A. Core app refactor

- [x] `app.py` reduced to composition/compatibility facade  
- [x] Extract helpers by concern:
  - validation/parsing
  - summary/audit
  - Director/character prompts
  - orchestration
  - turn runner
  - scene lifecycle
  - UI rendering  
- [x] Keep helper files focused and reasonably sized  
- [x] Re-run RP app tests after each extraction  

### 3B. Module decomposition

- [x] Split major helper modules by responsibility  
- [x] Re-evaluate cohesion for:
  - memory helpers
  - sidebar/UI
  - session lifecycle
  - response validation
  - character state  

- [x] Refactor `continuity_manager.py` in phases:
  - scene bootstrap
  - issue lifecycle
  - summary/compression
  - knowledge propagation  

- [x] Refactor `audit_logger.py` in phases:
  - path/naming
  - serialization
  - artifact writers
  - summary aggregation  

### 3C. Regression coverage

- [x] Scenario coverage:
  - one-on-one
  - emotional
  - 3-character
  - [ ] long-session
  - [ ] reload-after-save  

- [x] Track recurring failures:
  - character drift
  - memory drift
  - turn-selection mistakes
  - repetitive phrasing  

- [x] Convert audit findings into regression tests  
- [x] Keep context bounded (token limits / buffered dialogue)  
- [x] Use shadow/audit mode for new systems  

---

## 4. Phase 4 Stabilization & Calibration

- [ ] Run audited scenarios:
  - [x] 2-character emotional
  - [x] 3-character confrontation
  - [x] long session (20+ turns)
  - [x] reload-after-save  

- [ ] Review validator false positives and enforcement boundaries  
- [ ] Validate summary blocks for prompt quality  

### New Additions

- [ ] Validate packet quality:
  - completeness
  - correctness
  - token size
  - relevance  

- [ ] Tune:
  - canon
  - tone
  - knowledge
  - issue lifecycle
  - packet composition  

- [x] Implement persistent scene-priority hierarchy  
- [ ] Add reconciliation rules for persistent vs local priorities  
- [ ] Validate long-term behavior across turns and reloads  

---

## 5. UX & Workflow Polish

- [ ] Character portraits  
- [ ] Export conversation logs  
- [ ] Delete session flow  
- [ ] Improve error messages  
- [ ] Improve session management UI  
- [ ] Manual speaker override  
- [ ] Prompt/context tuning controls  
- [ ] Drift severity scoring  

---

## 6. Narrative & Setting Enhancements (Updated)

- [ ] Evaluate reasoning models for multi-character scenes  
- [ ] Add reusable **location/context assets**
- [ ] Inject setting guidance into **scene packets**, not prompts  
- [ ] Evaluate lightweight narrator bridge beats  
- [ ] Improve repetitive phrasing detection  

---

## 7. Scale-Up & Expansion

- [ ] Stabilize 3–4 character scenes  
- [ ] Expand regression coverage from real-session failures  
- [ ] Feed audit findings into permanent tests  
- [ ] Defer frontend/API/image/TTS until core stability  

---

## 8. Graph Persistence (Reframed as Upstream Layer)

- [ ] Evaluate need for graph persistence  
- [ ] Design graph model:
  - event nodes
  - issue nodes
  - character nodes
  - relationships  

- [ ] Prototype Neo4j-backed persistence  
- [ ] Validate before migration  

---

## 9. Retrieval & Packaging Integration (Replaces Old Retrieval Section)

**Purpose**: Feed dynamic context into packet builder.

- [ ] Add retrieval hooks to `packet_builder`  
- [ ] Start with manual/static retrieval sources  
- [ ] Add vector retrieval (shadow mode)  
- [ ] Combine:
  - deterministic filters
  - semantic retrieval  

- [ ] Score candidates:
  - relevance
  - recency
  - importance
  - character alignment
  - confidence  

- [ ] Limit retrieval per packet (strict token budget)  
- [ ] Validate:
  - relevance
  - non-redundancy
  - consistency  

---

## 10. Future: Knowledge Ingestion Pipeline (NEW)

**Separate system feeding into packets**

- [ ] Text ingestion (books, lore, etc.)
- [ ] Entity extraction
- [ ] Relationship extraction
- [ ] Event extraction
- [ ] Evidence linking
- [ ] Trait inference (confidence-based)
- [ ] Character compilation
- [ ] Relationship profile generation
- [ ] Voice modeling

Output feeds:
→ graph  
→ vector store  
→ compiled packet inputs  

---

## Guiding Principles (Updated)

- Test after **changes**, not continuously  
- Separate **refactor work** from **behavior changes**  
- Use **audit/shadow mode** instead of blocking development  
- Convert repeated failures into **regression tests**, not manual reruns  
- Only move to later phases once core continuity + Director behavior is stable  

### New Principles

- **Runtime consumes packets, not raw data**
- **State is authoritative; retrieval is advisory**
- **Precompute where possible; retrieve where necessary**
- **Avoid interpreting meaning from raw text repeatedly**
- **Keep AutoGen as execution layer, not knowledge layer**