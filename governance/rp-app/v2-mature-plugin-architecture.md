# V2 Mature Plugin/Service Architecture — Investigation Report

**Status:** Investigation complete (design only — no implementation authorized)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Real full-round anchor:** `17c210d`  
**Investigation HEAD:** `17c210d`

---

## 1. Activation / bootstrap state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD | `17c210d` |
| `origin/main` | aligned |
| Working tree | clean |
| Assigned workflow weight | standard |
| Effective workflow weight | full |
| Bootstrap profile | full V2 architecture |

**Validated runtime evidence (implementation HEAD `17c210d`):**

| Slice | Anchor | Proof |
|-------|--------|-------|
| Generic cast round | `generic-cast-round` docs | Multi-actor `runRound()` |
| ParticipationDecision | `baf507e` | Policy seam + tests |
| Real DeepSeek provider | `1503060` | `dsh-llm-deepseek` integration |
| Real full round | `17c210d` | Director → Character → commit → Narrator live |

**Test baseline at investigation:** 37 Python + 26 Node (24 deterministic + 2 live).

---

## 2. DSH/Cordis abstraction definitions

Sources: pinned `@deepseek-ai/dsh-*@0.1.0-rc.7`, `@deepseek-ai/cordis@4.0.1`, installed package READMEs, V2 runtime usage.

| Abstraction | Meaning | When to use |
|-------------|---------|-------------|
| **Cordis plugin** | Composition unit loaded via `ctx.plugin()`; registers services, listeners, adapters; disposed with fiber | Replaceable capability with independent lifecycle (provider adapter, optional narrator renderer, retrieval backend) |
| **Cordis service** | Stable `ctx.*` interface consumed by other components (`llm`, `agents`, `systemPrompt`, `tools`, `agentLoop`) | Shared runtime capability with a contract (orchestrator, context bridge, trace emitter, inference profiles) |
| **Scoped registration** | `agent.ctx.*` — contributions visible only to one agent/session | Per-inference isolation (character-private context, role-specific tools) — **not** one plugin per character |
| **Event / waterfall** | `ctx.on('agent/pre-step')`, `system-prompt/assemble`, `llm/stream` | Cross-cutting interception (retry, logging, prompt mutation) — not domain authority |
| **System-prompt contribution** | `ctx.systemPrompt.context()` / `.section()` | Deterministic model-visible context with ordering and provenance |
| **Agent lifecycle hook** | `agent/pre-step`, `agent/request`, `agent/request-error`, `agent/inbox/*` | Inference-step policy; DSH retry lives here — domain validation stays Python |
| **Tool** | `ctx.tools.register()` — model **chooses** to invoke | Optional model-initiated capabilities only |
| **Skill** | Not a separate DSH primitive | In practice: tool + prompt guidance; do not use for mandatory RP correctness |
| **Agent** | `ctx.agentLoop.create(SessionId, options)` — ephemeral inference session | One per Director/Character/Narrator inference (validated) |
| **Agent loop** | `dsh-agent-loop` — only concrete loop driver in DSH | Holy Grail uses it for inference substrate; RP round semantics live **above** it |
| **Bundle/profile** | `cordis.yml` composition + plugin config | Deployment wiring (DeepSeek adapter, inference profiles, optional components) |

**Critical distinction:** Plugins register *behavior into the runtime*. Services expose *stable interfaces*. Python Domain API exposes *authoritative truth*. Do not collapse these layers.

---

## 3. Holy Grail capability inventory

| Domain | Capabilities |
|--------|--------------|
| **RP orchestration** | Round lifecycle, Director phase, eligibility projection, participation policy, Character phase, retry control, Narrator phase, completion/failure semantics |
| **Domain/state** | Continuity, SceneState, CharacterState, relationships, presence, canonical facts, authoritative commit |
| **Context/projection** | Perception, scene grounding, identity/personality, relationship projection, conversational history, context assembly, prompt contributions, token budgeting |
| **Knowledge/memory** | Authored retrieval, world lore, character-local knowledge, episodic memory, summaries, future vector/graph/DB retrieval |
| **Validation/control** | Structured move parsing, move validation, Director validation, user-character agency, behavioral constraints, character-fidelity |
| **Infrastructure** | Provider/model profiles, DSH execution trace, HG domain audit, session/resume, UI/API, transport, configuration |

**V2 implementation mapping (current):**

| Capability | Current home |
|------------|--------------|
| Round orchestration | `HolyGrailRpRuntime.runRound()` (monolithic Service) |
| Participation policy | Python `participation_policy.py` |
| Eligibility | Python `kernel._eligibility_projection()` |
| Context assembly | Python `kernel.prepare_*_context()` → manifest |
| Validation/commit | Python `kernel.validate_*`, `commit_move()` |
| Inference execution | DSH `AgentLoop` + `_runEphemeralInference` |
| Provider config | `inference-profile.mjs` |
| HG trace | `events.mjs` + scene session append |
| DSH trace | DSH session events per inference agent |

---

## 4. Capability classification matrix

| Capability | Mature form | Rationale |
|------------|-------------|-----------|
| Round lifecycle orchestration | **Cordis service** (`HgRoundOrchestrator`) | Coordinates phases; no domain truth |
| Participation policy | **Python domain service** | Authoritative actor-selection policy; not model-optional |
| Eligibility projection | **Python domain service** | Hard floor; derived from SceneState |
| Director inference | **Phase executor module/service** | Ephemeral DSH agent + Domain API manifest |
| Director validation | **Python domain service** | Authoritative; must not be tool/hook-only |
| Character inference | **Phase executor module/service** | Generic executor; character = domain identity |
| Move validation | **Python domain service** | Guards commit |
| Continuity commit | **Python domain service** | Sole world-truth mutation |
| Narrator inference | **Phase executor** (optional plugin wrapper) | Presentation-only; replaceable renderer |
| Context projection | **Python domain** + **ContextBridge service** | Python computes; DSH registers contributions |
| Perception | **Python projection function** | Deterministic; not a model tool |
| Retrieval (authored/vector/graph) | **Python service** + **optional retrieval plugin** | Storage swappable; merge policy stays Python |
| Episodic memory | **Python memory service** | Authoritative state + derived read models |
| Provider/model profiles | **Cordis service / plugin config** | Orthogonal to RP semantics (validated) |
| DSH execution trace | **DSH native** (`Session` events) | Already owned by DSH |
| HG domain trace | **Cordis service** (`HgTraceEmitter`) | Correlates domain decisions to DSH sessions |
| Session/resume | **Split:** HG domain store + DSH session persistence | Different lifecycles |
| UI/Streamlit | **External surface** | Not Cordis plugin |
| Transport (HTTP Domain API) | **Transitional boundary** | Replace with in-process or stable RPC |

---

## 5. Mature RP runtime responsibility

**`HolyGrailRpRuntime` should become a thin round orchestrator**, not a domain kernel.

### Retains
- Phase sequencing: eligibility → participation → director → character → commit → narrator
- Domain API invocation order
- Correlation IDs across phases
- Delegation to phase executors

### Does NOT retain (move out)
- Participation/eligibility logic (already Python; runtime only consumes)
- Validation rules
- Context assembly logic
- Provider adapter details (beyond passing `InferenceProfile`)
- Inline prompt strings (live prompts → config or phase executors)

### Target shape

```text
HgRoundOrchestrator (Cordis service, ~200–400 LOC)
    ├── calls Domain API (authority)
    ├── ParticipationDecision (read)
    ├── DirectorPhaseExecutor
    ├── CharacterPhaseExecutor
    ├── NarrationPhaseExecutor
    └── HgTraceEmitter
```

**Not** a custom DSH agent-loop replacement. The validated pattern uses standard `AgentLoop` for ephemeral inference inside phase executors. A custom loop plugin is only justified if DSH default step semantics become obstructive — current evidence says **no**.

---

## 6. Director architecture

| Concern | Owner |
|---------|-------|
| Participation policy (forced, continuation) | Python `participation_policy` |
| Actor eligibility | Python eligibility projection |
| Director inference | Phase executor + ephemeral DSH agent |
| Director JSON parsing | Runtime utility (thin) |
| Director domain validation | Python `validate_director_decision` |
| Director trace | DSH session + `hg/director-*` events |

**Mature form:** Orchestration **phase** + Python **policy/validation** — not a monolithic "Director plugin" that owns selection policy.

Director is **not** the only actor-selection authority (participation policy can bypass Director — validated).

---

## 7. Character architecture

| Concern | Owner |
|---------|-------|
| Character identity | Python domain (cast, CharacterState) |
| Character-private projection | Python `prepare_context` |
| Character inference | Generic `CharacterPhaseExecutor` |
| Move validation/commit | Python |

**No per-character Cordis plugin.** One generic executor; character differentiation via Domain API manifests and `InferenceProfile`.

Per-inference scoped DSH agent (validated) provides isolation without per-character plugin installation.

---

## 8. Narrator architecture

| Concern | Owner |
|---------|-------|
| Narrator context | Python `prepare_narrator_context` (committed state only) |
| Narrator inference | `NarrationPhaseExecutor` |
| Presentation output | Non-authoritative prose |
| Failure after commit | `hg/narrator-failed`, `canon_preserved: true` (validated) |

**Strong optional-plugin boundary:** `NarrationRenderer` plugin interface allowing:
- enable/disable narrator
- replace prose style/renderer
- no-narrator mode

Domain commit must not depend on narrator success.

---

## 9. Validation architecture

| Layer | Owner | Mechanism |
|-------|-------|-----------|
| JSON parse (transport) | Runtime utility | `parseJsonObject` |
| Structural/domain validation | **Python** | `validate_move`, `validate_director_decision` |
| Semantic LLM validation (if any) | Python policy service | Not DSH hook alone |
| Provider retry | DSH `agent/request-error` + adapter policy | Transient failures |
| Inference retry (validation reject) | Round orchestrator loop | `liveMaxAttempts` / mock retry arrays |

**Rule:** Validation that guards commit must remain Python-authoritative. DSH hooks may assist logging/retry but cannot be the sole enforcement.

---

## 10. Context contribution architecture

**Mature pattern (validated prototype):**

```text
Python Domain API
    → PromptContributionManifest (typed, role-filtered)
        → ContextBridge registers ctx.systemPrompt.context() per contribution
            → DSH assembles per ephemeral agent
```

**Independent projection functions (Python), not separate Cordis plugins each:**

| Contributor | Visibility | Deterministic |
|-------------|------------|---------------|
| Scene state | Role-filtered | Yes |
| Identity/personality | Character only | Yes |
| Perception | Character only | Yes |
| Relationships | Character/director as policy dictates | Yes |
| Knowledge retrieval | Role-filtered | Yes (selection); content from providers |
| Memory | Character only | Yes |
| Conversation history | Role-filtered | Yes |
| Director scratch | Director only | Yes |
| Committed move | Narrator only | Yes |

**Coordinator:** Python `ContextAssembly` inside Domain Kernel (single place for ordering, budgeting, provenance). **ContextBridge** (Cordis service) only transports manifests to DSH.

Token budgeting stays Python — DSH does not own Holy Grail context policy.

---

## 11. Knowledge/retrieval architecture

```text
KnowledgeService (Python, authoritative merge policy)
    ↓
RetrievalProvider interface
    ├── AuthoredDeterministicProvider (permanent)
    ├── RelationalDbProvider (future plugin)
    ├── VectorProvider (future plugin)
    └── GraphProvider (future plugin)
        ↓
Context contributor (deterministic injection, not model tool)
```

- Retrieved knowledge **informs** inference; does not auto-commit as canon
- Model tools for ad-hoc lookup only where user/agent agency requires optional exploration
- Storage backends = replaceable plugins; merge/ranking/budgeting = Python

---

## 12. Memory architecture

| Layer | Owner |
|-------|-------|
| Authoritative character memory state | Python CharacterState / Continuity |
| Episodic write policy | Python (on commit hooks) |
| Interpretation memory | Python derived state |
| Conversation history | Python projection from continuity |
| Summaries | Python derived artifacts |
| Semantic search index | Replaceable persistence plugin |

**MemoryService** (Python) exposes stable read/write API. Character execution unchanged when persistence backend swaps.

---

## 13. Provider/model architecture

**Validated seam:** `InferenceProfile` + `resolveRoleProfiles()` + DSH `dsh-llm-deepseek`.

| Concern | Mature home |
|---------|-------------|
| Adapter registration | DSH plugin (`dsh-llm-deepseek`) |
| Role→model mapping | `InferenceProfileService` (Cordis service or composition config) |
| Per-call overrides | `roleProfiles` on round options |
| Credentials | DSH credential seam / env |

Not embedded in Director/Character/Narrator phase logic. Future routing policy = configuration layer only.

---

## 14. Trace/audit architecture

| Evidence class | Store | Contents |
|----------------|-------|----------|
| **DSH execution** | DSH `Session` per inference | request/header, chunks, assistant/message, usage, reasoning |
| **HG domain** | Scene session `hg/*` events + Python audit | participation, validation, commit, eligibility |
| **Correlation** | Shared IDs in both | `hg_scene_id`, `hg_round_id`, `inference_id`, `domain_commit_id`, DSH session IDs |

**HgTraceEmitter** (Cordis service): append-only `hg/*` on scene correlation session.

**No duplicate full prompt storage** in Python when DSH session already records model-visible history. Python stores authoritative manifests + decisions, not opaque re-serialized prompts.

Reconstructability = join Domain API manifests + DSH session events + HG events.

---

## 15. Required vs optional capabilities

### Required (Holy Grail invalid without)

| Component | Form |
|-----------|------|
| Python Domain Kernel | Authoritative service |
| Eligibility projection | Python |
| Participation policy | Python |
| Move/Director validation | Python |
| Continuity commit | Python |
| Round orchestrator | Cordis service |
| Context bridge | Cordis service |
| Phase executors (Director, Character) | Service/modules |
| DSH LLM adapter | DSH plugin |
| HG trace correlation | Cordis service |

### Optional / replaceable

| Component | Disable/replace? |
|-----------|------------------|
| Narrator | Yes — no-narrator mode; canon unaffected |
| Narrator renderer style | Yes — plugin |
| Retrieval backend | Yes — provider plugins |
| Memory persistence backend | Yes — behind MemoryService |
| Mock adapter | Test only |
| Specific model/provider | Yes — InferenceProfile |
| Streamlit UI | Yes — any surface over same API |

### Must NOT be disable-able

- Eligibility floor
- Participation policy (may return "normal director" but policy must run)
- Python validation before commit
- Commit authority separation

---

## 16. V1 retirement map

| V1 responsibility | V2 replacement | Removal condition |
|-------------------|----------------|-----------------|
| `model_client.py` AutoGen clients | DSH `dsh-llm-deepseek` + `InferenceProfile` | V2 surfaces fully on DSH; V1 paths unused in CI |
| `turn_runner.py` orchestration | `HgRoundOrchestrator` + Domain API | V2 round parity signed off per scenario class |
| `app_turn_director.py` | Director phase executor + Python validation | V2 Director behavior validated |
| `app_turn_prompting.py` / `prompt_builders.py` | Python ContextAssembly + ContextBridge | Packet migration complete; V1 bundle unused |
| `pending_forced_speaker` session flags | `ParticipationDecision` + request-scoped designation | V2 transport ingress complete |
| AutoGen selector callbacks | Participation policy | V2 participation fairness complete |
| `ReplayChatCompletionClient` | `HgMockLlmAdapter` (test-only) | V1 tests retired or ported |
| Streamlit runtime state for routing | Request-scoped inputs | V2 API boundary stable |
| Duplicate audit capture of model I/O | DSH session + HG correlated events | Trace join validated |
| `session_manager.py` dual duty | Split HG domain store + DSH persistence | Resume slice complete |

**Do not delete V1 until:** V2 replacement validated + V1 path unreachable + tests/docs updated.

---

## 17. Current V2 transitional map

| Component | Class | Replacement / condition |
|-----------|-------|------------------------|
| `HolyGrailRpRuntime` monolith | **Transitional** | Split into orchestrator + phase executors |
| HTTP Domain API (`http_transport.py`) | **Transitional** | In-process Python binding or stable RPC |
| `FixtureStore` | **Transitional** | Real persistence + ContinuityManager integration |
| `HgMockLlmAdapter` | **Test-only** | Permanent for deterministic CI |
| `syntheticDirectorDecision()` | **Transitional** | Keep as orchestration adapter until participation direct-path models formal request shape |
| `mount-deepseek-provider.mjs` | **Permanent** | Dynamic DSH plugin load |
| `inference-profile.mjs` | **Permanent** | |
| `inference-trace.mjs` | **Permanent** | |
| `live-inference-prompts.mjs` | **Transitional** | Move to composition config / prompt registry |
| `domain-api-client.mjs` | **Transitional** | Becomes ContextBridge + Domain binding |
| `bootstrap.mjs` test harness | **Test-only** | |
| `registerManifestContributions` | **Permanent** | Part of ContextBridge |

---

## 18. Mature architecture diagram

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Surfaces (Streamlit, CLI, API, SDK)                                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  DSH / Cordis composition (cordis.yml)                                   │
│                                                                          │
│  Plugins:                                                                │
│    dsh-llm-deepseek          (provider)                                    │
│    dsh-agent-loop            (inference substrate)                         │
│    [optional] hg-narrator-renderer                                        │
│    [future] hg-retrieval-*   (vector/graph/db providers)                  │
│                                                                          │
│  Services:                                                               │
│    HgRoundOrchestrator       (round lifecycle only)                       │
│    HgPhaseExecutors          (director / character / narrator)            │
│    HgContextBridge           (manifest → systemPrompt.context)          │
│    HgTraceEmitter            (hg/* correlated events)                     │
│    InferenceProfileService   (role → provider/model)                      │
│                                                                          │
│  Per inference: ephemeral Agent (Director | Character | Narrator)         │
│  Per round: one scene correlation Agent/session                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Domain API (batched, typed)
┌───────────────────────────────▼─────────────────────────────────────────┐
│  Holy Grail Authoritative Domain Kernel (Python)                          │
│                                                                          │
│    ContinuityManager · SceneState · CharacterState · Relationships       │
│    EligibilityProjection · ParticipationPolicy                           │
│    ContextAssembly (perception, identity, scene, memory, retrieval)      │
│    Validation (move, director) · Commit                                  │
│    KnowledgeService · MemoryService                                      │
│                                                                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  Authoritative store (future: DB, files, graph — behind kernel interfaces) │
└─────────────────────────────────────────────────────────────────────────┘

DSH Session logs (per inference)          HG events (per scene)
  request/header, chunks, usage    ←correlate→  participation, validation, commit
```

---

## 19. Plugin composition / configuration model

**Composition file (`cordis.yml`) declares:**

```yaml
plugins:
  - dsh-llm-deepseek
  - dsh-agent-loop
  - hg-rp-round
  # optional:
  - hg-narrator-prose-default
  # future:
  # - hg-retrieval-vector

config:
  hg-rp-round:
    liveMaxAttempts: 3
  hg-inference-profiles:
    director: { provider: deepseek-official, model: deepseek-v4-flash, reasoningEffort: low }
    character: { ... }
    narrator: { reasoningEffort: off }
  hg-narrator:
    enabled: true
```

**Operators can:**
- Replace narrator renderer plugin
- Swap retrieval/memory provider plugins (future)
- Configure per-role models
- Disable narrator without breaking canon

**Operators cannot:**
- Disable eligibility or participation policy
- Bypass Python validation
- Commit from DSH trace

---

## 20. Migration sequence (with cleanup gates)

| Stage | Capability | Target | Validation | Supersedes | Cleanup gate |
|-------|------------|--------|------------|------------|--------------|
| **M1** | Context bridge | Extract `HgContextBridge` service from runtime | Context isolation tests green | Inline `registerManifestContributions` in service.mjs | Bridge is sole manifest→DSH path |
| **M2** | Phase executors | Extract Director/Character/Narrator executors | All round tests green | `_runDirectorPhase` etc. inlined in monolith | Orchestrator delegates only |
| **M3** | Trace service | Extract `HgTraceEmitter` | Event correlation tests | Inline `appendHgEvent` scatter | Single trace API |
| **M4** | Orchestrator slim | `HolyGrailRpRuntime` → `HgRoundOrchestrator` | Full suite green | Monolithic service.mjs domain-free | <400 LOC orchestrator |
| **M5** | Domain binding | Replace HTTP with in-process Python binding | Latency + parity tests | `http_transport.py`, `fixture_store` for prod | HTTP test-only or removed |
| **M6** | Narrator optional | `NarrationRenderer` plugin boundary | no-narrator mode test | Hard-coded narrator in orchestrator | Configurable enable/disable |
| **M7** | Knowledge providers | Retrieval plugin interface | Retrieval parity vs V1 | V1 `retrieved_context_select` direct calls | V1 retrieval path removed |
| **M8** | Memory persistence | MemoryService + pluggable store | Memory scenario tests | V1 episodic direct file access | V1 memory path removed |
| **M9** | V1 orchestration retirement | — | Full behavioral inventory | `turn_runner.py`, AutoGen agents | V1 orchestration deleted |

Each stage: **validate → remove superseded path → update governance → simplify**.

---

## 21. Challenge / refinement pass

| Question | Finding |
|----------|---------|
| Plugins because DSH allows it? | **No** — only optional boundaries (narrator, retrieval, provider) |
| Service boundaries meaningful? | **Yes** — orchestrator, context bridge, trace, profiles are distinct concerns |
| RP loop simpler or fragmented? | Risk if over-split; mitigate with **one orchestrator + phase executor module** |
| Deterministic mechanisms mandatory? | **Yes** — stay Python; never model tools |
| Domain truth outside runtime? | **Yes** — validated and non-negotiable |
| Knowledge/memory replaceable? | **Yes** — via provider interfaces behind Python services |
| Tools only where model chooses? | **Yes** — ad-hoc lookup only |
| Independently testable? | Python kernel unit tests + DSH phase integration tests |
| Optional components safely disabled? | Narrator yes; validation/eligibility no |
| Reduces clutter vs V1? | **Yes** — if retirement map executed; risk if V1+V2 coexist indefinitely |
| Avoid micro-plugin sprawl? | **Yes** — ~4–6 Cordis units, not per-character plugins |
| DB/vector/graph future? | Retrieval provider plugins behind Python KnowledgeService |
| Per-role models? | **Validated** — InferenceProfile sufficient |
| Full reconstructability? | Join manifest + DSH session + hg events — validated |
| Clear deletion path? | Retirement map + cleanup gates per migration stage |

**Refinement:** Do **not** create a custom DSH agent-loop plugin yet. Do **not** create one Cordis plugin per context contributor. Bundle phase executors as one service until independent lifecycle is needed.

---

## 22. Architecture verdict

**Architecture established with unresolved boundary decisions**

The mature decomposition is clear: thin DSH orchestration + authoritative Python kernel + optional replaceable plugins at narrator/retrieval/provider boundaries.

**Unresolved (need focused experiments, not broad rewrite):**
- Exact Domain API transport for production (in-process vs RPC)
- Narrator plugin interface shape
- Retrieval provider plugin contract
- Whether phase executors remain one service or split into three

**Not rejected:** Current validated runtime is the correct foundation. Decomposition is evolutionary, not replacement.

---

## 23. Recommended next migration slice

**M1: Extract `HgContextBridge` Cordis service** — move manifest→`systemPrompt.context()` registration out of `HolyGrailRpRuntime` into a dedicated service; no behavior change; proves context transport is independent of round orchestration.

Do not implement without Governance review.
