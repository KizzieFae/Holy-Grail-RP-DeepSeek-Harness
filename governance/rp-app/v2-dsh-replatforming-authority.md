# Holy Grail V2 — DeepSeek Harness Re-platforming Authority

**Status:** Baseline / governing document (not implementation spec)  
**Repository:** `Holy-Grail-RP-DeepSeek-Harness`  
**Supersedes for V2 work:** module layout and AutoGen coupling as architectural goals  
**Does not supersede:** Holy Grail behavioral semantics, PRD product intent, or continuity authority doctrine

---

## 1. Purpose

Holy Grail RP DeepSeek Harness is a **behavioral-preservation re-platforming** of Holy Grail onto **DeepSeek Harness (DSH)**.

The goal is **not** merely to replace Microsoft AutoGen calls with DSH calls.

The goal is to determine and implement the **best long-term Holy Grail architecture** when DeepSeek Harness is available as the runtime / composition substrate.

This repository exists specifically to allow **substantial redesign** where DSH provides a materially better long-term architecture. Migration effort is documented but is **not** the primary decision criterion.

The upstream Holy Grail repository (`KizzieFae/Holy_Grail_RP`) remains the reference lineage for product semantics and historical evidence. It must **not** be modified by harness work.

---

## 2. Behavioral authority

Existing Holy Grail RP behavior and domain semantics are the **reference implementation**.

Important behavioral contracts include (non-exhaustive):

| Domain | Authoritative sources |
|--------|----------------------|
| Director orchestration | `rp_app/ARCHITECTURE.md`, `orchestration_helpers.py`, `app_turn_director.py` |
| Character execution | `turn_runner*.py`, `model_client.py`, structured move contract |
| Structured character moves | `response_validation_*.py`, prompt topology (#240/#249) |
| Validation and bounded retry | `turn_runner_character_attempt.py`, `semantic_validation.py` |
| Narrator behavior | `app_turn_rendering.py`, verbatim dialogue preservation |
| Continuity authority | `continuity_manager.py`, GitHub #224 doctrine |
| Perception / information boundaries | `perception_audibility.py`, `continuity_knowledge_helpers.py` |
| Character fidelity | `character_state_model.py`, `response_validation_drift.py` |
| User-character agency | `ARCHITECTURE.md` operating rules, Streamlit control model |
| Scene grounding | `scene_grounding.py`, `autogen_rp/docs/scene-grounding-layer.md` |
| Relationship state | `character_state_manager.py`, cross-session memory policy |
| Memory | `memory_layer/`, episodic write/read policy |
| Knowledge retrieval | `retrieved_context_select.py`, `CANONICAL_KNOWLEDGE_MODEL.md` |
| Knowledge authority rules | Continuity + perception; retrieval is non-authoritative |
| Session / resume semantics | `session_manager.py`, `session_lifecycle_*.py`, audit identity (#106/#109) |

These behaviors should be **preserved** unless a later **explicit architectural or product decision** intentionally changes them.

V2 changes require: documented rationale, evidence review, and (when product-facing) PRD alignment.

---

## 3. Structural freedom

The existing Python module / file organization is **not authoritative** for V2.

Do **not** perform a one-for-one translation such as:

```text
old Python module → equivalent DSH module
```

Instead:

1. Preserve the **capability / invariant**.
2. Determine its cleanest **DSH-native representation**.
3. Reuse existing implementation **only where it remains architecturally appropriate**.

Preservation of old structure is **not** itself a goal.

Façade modules (`app_turn_helpers.py`, `orchestration_helpers.py`, etc.) exist for compatibility and test stability in V1; they are **not** targets for V2 structure.

---

## 4. DSH posture

Treat DeepSeek Harness as a potential **runtime / microkernel / composition substrate** (Cordis plugin system).

Take seriously DSH native concepts, including:

- Plugins and plugin lifecycle (Fiber state machine, reversible effects)
- Services (`ctx.llm`, `ctx.tools`, `ctx.agents`, `ctx.sessions`, `ctx.systemPrompt`, …)
- Typed Cordis events (`agent/*`, `session/event`, waterfall / bail / serial modes)
- Replaceable agent loops (`agent-loop` swappable; extensions depend on `agent`, not loop)
- Model / provider adapters (`ctx.llm`)
- System-prompt / context contribution (`ctx.systemPrompt`)
- Lifecycle interception (`agent/pre-step`, request construction, steering)
- Session events (append-only durable log; derived LLM history)
- Tools and agent scoping (`scope/`, per-agent `Agent.ctx`)
- Traceability (session replay, trajectory inspection)

Do **not** force Holy Grail into DSH's default **coding-agent** workflow.

Holy Grail defines its own **RP execution semantics** and will likely require a **custom DSH composition and/or agent loop** (multi-agent round orchestration, Director-mediated turns, structured JSON moves, Narrator rendering).

---

## 5. State ownership

Maintain a strong distinction between:

### Holy Grail domain truth

Examples: characters, character state, relationships, scene state, continuity, canon, lore, memories, authoritative knowledge, scene grounding facts, issue/pressure state, session domain payloads.

**Owner:** Holy Grail domain services and persistence.  
**Authority:** `ContinuityManager` / `SceneState` commit path (#224).

### DSH execution history

Examples: model-visible messages, context contributions, model requests/responses, reasoning (where exposed), tool activity, agent activity, retries, timing, token usage, execution provenance, compaction surfaces.

**Owner:** DSH session log and execution telemetry.  
**Authority:** append-only `session/event` records and derived projections.

### Derived / model-visible context

Examples: assembled prompts, perception-filtered dialogue excerpts, retrieved snippets, grounding blocks, advisory hints.

**Owner:** Holy Grail projection layer (packaging seam).  
**Authority:** explicit assembly from domain truth; **not** a second world database.

**Core principle:**

> **Holy Grail determines what is true. DeepSeek Harness records what happened.**

Do not accidentally turn the DSH session / event log into a second authoritative world / knowledge database.

---

## 6. Knowledge architecture

Holy Grail's knowledge system must remain **conceptually independent** of its storage backend.

Current JSON-backed knowledge may eventually be supplemented or replaced by relational, graph, vector, document, or hybrid stores.

The runtime must consume knowledge through **explicit interfaces / services**, not direct coupling to a particular persistence technology.

Retrieval and vectors remain **non-authoritative** (PRD §7, `CANONICAL_KNOWLEDGE_MODEL.md`).

---

## 7. Architecture-over-migration-cost

Do not preserve the current architecture merely because changing it requires substantial work.

Where a DSH-native design provides a materially more **modular, stable, observable, extensible, or maintainable** long-term architecture, evaluate that design on its merits.

Document migration cost separately; do not let cost alone veto a better design.

---

## 8. Evidence and validation discipline

- Use **existing** audits, scenarios, regression baselines, and deterministic tests as behavioral evidence (see `v2-behavioral-evidence-inventory.md`).
- Do **not** treat structural similarity to V1 as proof of behavioral preservation.
- New lengthy RP scenario generation is **not** required for baseline; use historical artifacts first.
- Scenario validation framework remains the canonical behavioral validation layer for substantive changes.

---

## 9. Scope boundaries for this repository

| In scope | Out of scope (unless explicitly decided) |
|----------|------------------------------------------|
| DSH-native Holy Grail V2 design | Modifying upstream `Holy_Grail_RP` |
| Behavioral preservation analysis | Blind 1:1 module port |
| Independent harness environment | Installing DSH before V1 baseline validation |
| Governance and mapping docs | Removing AutoGen before replacement exists |

---

## 10. Related documents

| Document | Role |
|----------|------|
| `v2-behavioral-evidence-inventory.md` | Existing evidence by capability |
| `v2-capability-dsh-mapping.md` | Capability → DSH mapping and target architecture |
| `CHECKPOINT_BASELINE_DSH.md` | Baseline checkpoint report |
| `../../Holy Grail PRD.md` | Product intent |
| `../../ARCHITECTURE_OVERVIEW.md` | V1 three-layer model |
| `../../autogen_rp/python/rp_app/ARCHITECTURE.md` | V1 runtime architecture |
