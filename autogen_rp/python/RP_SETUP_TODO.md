# RP App – Consolidated Step-by-Step Roadmap

**Goal**: Multi-agent RP system with persistent, resumable scenes, structured character output, continuity engine, and Director/Narrator orchestration.

This checklist reflects the canonical plan. All items are actionable and structured to avoid circular testing loops.

---

## 0. Scope & Core Rules

- [x] Define scene and turn rules: user present, bots act, turn limits, must-remain characters  
- [x] Character success criteria: in-character behavior, knowledge boundaries, voice preservation  
- [x] Session termination rules: explicit end, scene replacement, or interrupted session finalization  

---

## 1. Core System Foundations

- [x] Load character cards (`python/data/autogen_characters/`) and create agents  
- [x] Streamlit RP scenes with session save/load  
- [x] Director-controlled turn selection  
- [x] Narrator rendering with verbatim dialogue preservation  
- [x] Structured character output: `action`, `dialogue`, `motivation`  
- [x] Track per-character private state and identity anchors  
- [x] Add audit logging and repeatable Director scenario validation  

---

## 2. Continuity & Memory Engine

- [x] Model durable structures: scene state, issue/pressure state, public events, character interpretations, canon anchors  
- [x] Strengthen scene state: participants, environment, phase, recent delta  
- [x] Track issue/pressure lifecycles: active, escalating, stalled, resolved  
- [x] Canon anchors for stable character/world truths  
- [x] Continuity manager responsibilities:
  - [x] Promote key dialogue/actions to events
  - [x] Update issue/pressure and scene state
  - [x] Update character interpretation memory
  - [x] Enforce knowledge boundaries  
- [x] Separate persistent facts from temporary beat state  
- [x] Layered prompt assembly:
  - [x] Scene state
  - [x] Issue/pressure
  - [x] Recent moves
  - [x] Dialogue window
  - [x] Memory  
- [x] Simple memory buckets:
  - [x] Session summary
  - [x] World facts
  - [x] User preferences  
- [x] Deterministic retrieval with filters (participant, issue, recency, location, significance)  

---

## 3. Refactor & Safety Net (Development-Focused)

### 3A. Core app refactor

- [x] `app.py` reduced to composition/compatibility facade  
- [x] Extract helpers by concern:
  - [x] validation/parsing
  - [x] summary/audit
  - [x] Director/character prompts
  - [x] orchestration
  - [x] turn runner
  - [x] scene lifecycle
  - [x] UI rendering  
- [x] Keep helper files focused and reasonably sized  
- [x] Re-run RP app tests after each extraction  

### 3B. Module decomposition

- [x] Split major helper modules by responsibility  
- [x] Re-evaluate cohesion for:
  - [x] memory helpers
  - [x] sidebar/UI
  - [x] session lifecycle
  - [x] response validation
  - [x] character state  
- [x] Refactor `continuity_manager.py` in phases:
  - [x] scene bootstrap
  - [x] issue lifecycle
  - [x] summary/compression
  - [x] knowledge propagation  
- [x] Refactor `audit_logger.py` in phases:
  - [x] path/naming
  - [x] serialization
  - [x] artifact writers
  - [x] summary aggregation  

### 3C. Regression coverage

- [x] Scenario coverage:
  - [x] one-on-one
  - [x] emotional
  - [x] 3-character
  - [ ] long-session
  - [ ] reload-after-save  
- [x] Track recurring failures:
  - [x] character drift
  - [x] memory drift
  - [x] turn-selection mistakes
  - [x] repetitive phrasing  
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
- [ ] Tune:
  - [ ] canon
  - [ ] tone
  - [ ] knowledge
  - [ ] issue lifecycle
  - [ ] summary retrieval  
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

## 6. Narrative & Setting Enhancements

- [ ] Evaluate reasoning models for multi-character scenes  
- [ ] Add reusable setting/location-context assets  
- [ ] Inject setting guidance into Director flow  
- [ ] Evaluate lightweight narrator bridge beats  
- [ ] Improve repetitive phrasing detection  

---

## 7. Scale-Up & Expansion

- [ ] Stabilize 3–4 character scenes  
- [ ] Expand regression coverage from real-session failures  
- [ ] Feed audit findings into permanent tests  
- [ ] Defer frontend/API/image/TTS until core stability  

---

## 8. Post-Core Persistence Upgrade

- [ ] Evaluate need for graph persistence
- [ ] Design graph model:
  - [ ] event nodes
  - [ ] issue nodes
  - [ ] character nodes
  - [ ] relationships  
- [ ] Prototype Neo4j-backed persistence  
- [ ] Validate before migration  

---

## 9. Post-Core Retrieval Upgrade

- [ ] Evaluate embedding-based retrieval after deterministic system stabilizes  
- [ ] Score memory candidates:
  - [ ] relevance
  - [ ] recency
  - [ ] importance
  - [ ] character alignment
  - [ ] source confidence  
- [ ] Use shadow mode before enabling  
- [ ] Keep deterministic filters as hard gates  

---

## Guiding Principles (Prevent Endless Testing Loops)

- Test after **changes**, not continuously  
- Separate **refactor work** from **behavior changes**  
- Use **audit/shadow mode** instead of blocking development  
- Convert repeated failures into **regression tests**, not manual reruns  
- Only move to later phases once core continuity + Director behavior is stable  