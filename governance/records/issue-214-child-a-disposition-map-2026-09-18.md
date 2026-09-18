# Issue #214 — Child A migration / legacy disposition map (Governance accepted 2026-09-18)

**Issue:** [#214](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/214) — NG-RP Child A  
**Parent / program:** [#213](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/213) — next-generation RP architecture migration  
**Evidence predecessor:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201) (historical assessment; see records under `governance/records/issue-201-*`)  
**Governance weight:** Assigned **full**; effective **full**; bootstrap **Full** (`docs/issue-bootstrap-profiles.md`)  
**Repository evidence anchor:** `75aa1fc0bd277f7944935a44a66716463fb0c53d` (HEAD at consensus recording)  
**Supplementary evidence (not sole retirement proof):** `governance/records/issue-201-current-vs-a2-scene-data-pathway-matrix.md` (matrix SHA `968ba2a`), `governance/records/issue-201-final-architecture-decision-2026-09-17.md`, `v2/rp_runtime/src/application/llm-call-catalog.mjs`

**Authority of this record:** Canonical **Child A** responsibility/disposition map at **`consensus_reached`**.  
**This record does NOT authorize:** runtime implementation, production orchestration changes, inference behavior changes, deletion of code, or Child **J** retirement execution.

---

## 1. Next-generation primary agents

Three **primary agents**:

| Agent | Role |
|-------|------|
| **Character** | Primary agency: structured move cognition within knowledge, perception, and world bounds; commits through validated Host path. |
| **Narrator** | Primary presentation: player-facing narrative from committed truth and bounded scene context; does not own authoritative state. |
| **Storyteller** | Primary **story-driving intelligence**: absorbs/reorganizes much narrative-driving responsibility historically distributed across Director and Scribe/Plot. **Not** a conditional-tool family label—Storyteller is a primary agent; many former agent-stage duties become **tools** invoked on its behalf or on behalf of other agents. |

**Director is not a primary agent** in the target architecture (see §4).

---

## 2. Scenario default turn order

Normal actor progression follows the **default turn order established by the scenario**. Deterministic routing advances that order unless deterministic conditions establish that **semantic routing judgment** is required. Exact scheduler and exception semantics are **downstream** (Children **C**, **D**). Child A does not specify trigger algorithms.

---

## 3. Responsibility disposition taxonomy (authoritative)

| Class | Meaning |
|-------|---------|
| **`Retain`** | Responsibility belongs directly in next-gen architecture as **primary-agent** or **deterministic substrate** responsibility. Does **not** require preserving current implementation; code may be rewritten substantially. |
| **`Convert to tool`** | Preserve the **useful capability** as an **independently triggerable and independently testable** tool responsibility—not a standing agent responsibility or mandatory orchestration stage. The tool runs under deterministic trigger/eligibility logic. **Conversion does not promise permanent retention:** after isolation and appropriate validation, evidence may support retaining the tool, refining it, consolidating it with another tool, replacing it, or **deleting** it if it does not demonstrate sufficient value. Does **not** require preserving the old implementation, old inference identity, old component boundary, one-to-one old→new mapping, or compatibility infrastructure. Old implementation may be **completely deleted** once the responsibility has migrated and Child **J** gates pass. |
| **`Delete`** | The **responsibility itself** is unnecessary in next-gen architecture. Do not assign a new owner merely because the old stack contained it. Delete implementation after consumers, forensics, documentation, tests, and Child **J** gates permit. |

**Map responsibilities first; implementations second.** Many-to-many mapping is expected (§8).

---

## 4. Director disposition

**`Convert to tool`** — semantic routing judgment when deterministic policy and scenario turn order are insufficient.

- No standing **Director-agent** execution path for compatibility.
- Participation-direct deterministic bypass (**`Retain`** substrate behavior) remains.
- Standing Director semantic QA: **`Delete`** (§6).
- Trigger and routing-exception design: Children **C**, **D**; gated per #213 before treating Director fallback as retired in production.

---

## 5. Storyteller long-horizon memory / narrative curation

**`Convert to tool`** (decision final for Child A—not an open Retain-vs-tool placement question).

- Conditional, not an intrinsic every-turn Storyteller operation.
- Conversion **preserves the capability for downstream evaluation**; it does **not** presume permanent retention in the architecture.
- Downstream tool contract **unresolved** (Children **E**, **I**).

**Expected characteristics (non-normative; Child A must NOT invent or freeze these):** multiple deterministic triggers; transcript/context-length or comparable state-dependent eligibility; other state-dependent eligibility; different triggers for different long-horizon obligations.

**Downstream investigation must determine:** which historical Storyteller long-horizon duties remain genuinely useful; which are already adequately covered by Plot/Scribe-derived persistent state and other retained or converted capabilities; one vs several tools; trigger conditions and thresholds; inputs/outputs/persistence; interaction with Storyteller primary cognition and Plot/Scribe-derived state; forensic evidence; validation including genuinely long-horizon RP evidence—specifically whether the capability adds **independent narrative value** beyond core Storyteller cognition, deterministic substrate, Plot/Scribe-derived state, and other tools.

If evidence shows **insufficient independent value**, the architecture **must permit deleting the tool** without destabilizing unrelated Storyteller primary-agent behavior. Do not duplicate Storyteller/Plot-Scribe responsibilities for historical compatibility; do not assume Plot/Scribe equivalence to full long-horizon ST charter.

---

## 6. No legacy compatibility

Holy Grail has **no production user base** and **no production deployment** requiring compatibility. Do **not** design compatibility APIs, old execution modes, indefinite bridges, or dual architectures. Temporary internal sequencing is allowed only where technically necessary for bounded migration. Prefer **direct consumer migration**.

---

## 7. Many-to-many migration principle

- Multiple old responsibilities → one tool.
- One old component → multiple tools/responsibilities.
- Responsibilities from different old agents may consolidate under Storyteller and tools.
- One old component may split: part **`Retain`** / **`Convert to tool`**, part **`Delete`**.
- Old implementation may disappear while responsibility survives elsewhere.

---

## 8. Responsibility map

### 8.1 `Retain` (primary agent or substrate)

| Responsibility | Role | Notes |
|----------------|------|-------|
| Continuity / authoritative commit | Substrate | `commit_move` / `process_turn` authority; mutation seams per architecture-overview |
| PVR / entitlement | Substrate | Fail-closed visibility; tier-1 player authority |
| Structural deterministic validation | Substrate | Parse/shape gates before commit |
| Scenario / session / character binding | Substrate | AS scenario contract |
| Retrieval hard-access substrate | Substrate | Candidates under constraints (#31); not semantic ranking |
| Participation / eligibility / forced speaker | Substrate | Includes participation-direct bypass without Director LLM |
| **Character** primary cognition | **Primary agent** | Structured move / agency |
| **Narrator** presentation | **Primary agent** | RO from committed truth |
| **Storyteller** primary story-driving cognition | **Primary agent** | Dramatic/narrative intelligence when architecture requires it—not mandatory sync preamble duty |
| Forensic reconstruction | Substrate + cross-cutting | Meaning ≥ A4; extended for tools (§10) |
| Authoritative architecture/documentation | Cross-cutting | Must track runtime; historical records stay historical |

### 8.2 `Convert to tool`

| Responsibility | Typical invocation | Downstream owner |
|----------------|-------------------|------------------|
| Director semantic routing judgment | After eligibility/trigger (C/D) | **C**, **D**, **B** (envelope) |
| Librarian / knowledge mediation | Obligation-driven | **F** |
| Character orientation (where still useful) | Obligation-driven | **F**, **B** |
| Character semantic validation / repair (where still useful) | Failure-class / uncertainty | **H** |
| Narrator environmental resolution | Material env obligation | **G** |
| Conditional semantic repair (incl. former standing QA duties where replaced) | Genuine failure classes | **H** |
| Plot/Scribe-derived overlay maintenance (R0–R4 capability) | Obligation-driven; not default sync preamble | **E** |
| Issue-pressure assessment | Obligation-driven; not universal post-commit topology | **E**, **H** |
| **Storyteller long-horizon memory / narrative curation** | State/transcript-dependent triggers (TBD) | **E**, **I** |

### 8.3 `Delete` (responsibility)

| Responsibility | Rationale (#201 / #213 / evidence) |
|----------------|-----------------------------------|
| Mandatory Storyteller **preamble** duty (round-start orientation/assessment as standing choreography) | Rejected always-on sync ST stack |
| Mandatory **synchronous Plot preamble** on default critical path (standing duty) | Topology rejected; overlay capability retained via tools |
| Standing **Director semantic QA** as universal gate | Not earned as default |
| Standing **Narrator semantic QA** as universal gate | Not earned as default |
| **Universal post-commit pressure** as mandatory topology | Capability may survive as tool; standing duty deleted |
| Standing **Librarian-agent** / default mediation **fan-out** as architectural requirement | Mediation **`Convert to tool`**; persona/topology deleted |
| **Always-on multi-agent / multi-inference choreography** as architectural requirement | A4 baseline, not target |

**Distinction:** **`Delete`** rows are **duties/topologies**. Implementations (`director_semantic_qa.mjs`, fixed orchestrator preamble, etc.) are removed under Child **J** after §12 gates—not because the **capability** never returns, but because the **responsibility as a standing stage** is gone.

---

## 9. Implementation mapping (migration safety; HEAD `75aa1fc`)

| Surface (current) | Responsibilities | Disposition of responsibility | Implementation fate (after gates) |
|-------------------|------------------|------------------------------|-----------------------------------|
| `hg-round-orchestrator/service.mjs` fixed preamble + joins | Deleted standing duties + substrate orchestration | Mixed | Refactor sequencing; no compat mode |
| `runStorytellerCognition` at round start | Delete preamble duty; Retain ST agent cognition via tools | Mixed | Remove unconditional call; modules may be rewritten |
| `runPlotCognitionPendingWorkLifecycle` at round start | Delete sync preamble duty; Convert overlay maintenance | Mixed | Remove critical-path placement |
| `director-phase` / `director_turn` | Convert routing judgment | Tool | Rewrite behind scheduler + tool |
| `director_semantic_qa` | Delete standing QA | Delete impl when H + J | |
| `narrator_semantic_qa` | Delete standing QA | Delete impl when H + J | |
| `character_orientation`, `librarian-mediation-substrate` | Convert to tool | Rewrite / replace | |
| `character_semantic_evaluation` | Convert to tool | Rewrite | |
| `narrator_environment_cognition` | Convert to tool | Rewrite | |
| `runPostCommitLibrarianLifecycle` / issue pressure | Convert capability; Delete mandatory topology | Refactor | |
| Plot cognition modules | Convert overlay; Delete sync preamble duty | Refactor | |
| Host `kernel` / projectors | Retain assembly authority | Adapt in place per child | |
| `execution-evidence/*`, trace | Retain forensic meaning | Extend for tool trigger/skip | **B** |
| `llm-call-catalog.mjs` | Retain catalog discipline | Refactor taxonomy | **B**, **J** |
| `prompt_builders.py` | No live consumers at HEAD | Delete impl | **J** after doc migration |

---

## 10. Forensic migration matrix (obligations)

For each **`Retain`** / **`Convert to tool`** responsibility, downstream children must preserve or improve reconstruction of:

- primary-agent activity;
- tool eligibility consideration;
- deterministic trigger decision;
- trigger evidence/state;
- fired vs skipped;
- inference lineage;
- inputs/outputs;
- retries/repairs/corrections;
- authoritative commit and derived-state relationships;
- timing/token accounting where applicable;
- downstream consumption;
- failure/degraded paths;
- causal ordering and joins.

**Tools with multiple triggers:** forensics must identify which trigger/eligibility path caused execution.  
**Transcript/state-dependent tools (incl. long-horizon):** eligibility decision must be reconstructable without relying on obsolete A4-only schemas.  
Preserve **meaning**, not legacy event names for compatibility.

| Area | Current surfaces (examples) | Next-gen owner |
|------|----------------------------|----------------|
| Global turn/commit | `execution-evidence`, `hg-trace-emitter`, commit spans | **B** + each child |
| Tool dispatch | (to be introduced) | **B** |
| Routing tool | `director_turn` attempts today | **C**, **D** |
| Mediation tools | `librarian_mediation@*` | **F** |
| Repair tools | semantic eval / QA patches today | **H** |
| Plot/pressure tools | plot forensics, S4 audit log | **E**, **F**, **H** |
| Long-horizon tool | (not in prod as unified surface) | **E**, **I** |

---

## 11. Documentation migration matrix

Each child **B–I** updates authoritative docs it touches: `docs/architecture.md`, `MODULE_INDEX.md`, contracts (`PACKET_CONTRACTS.md`, plot/librarian docs), `llm-call-catalog` / JSON, `docs/audit-workflows.md`, `docs/testing.md`, testing/validation docs. **Do not rewrite** historical `governance/records/issue-201-*` or closed Issue narratives as if next-gen always existed.

| Transition | Primary docs today | Owner |
|------------|-------------------|-------|
| A4 → three-agent + tools | `docs/architecture.md`, pathway matrix (historical) | Each child + this record |
| Director phase → routing tool | `MODULE_INDEX`, architecture | **C**, **D** |
| ST Model A preamble | architecture §#33, #32 records (historical) | **E** |
| Catalog as tool taxonomy | `llm-call-catalog.mjs`, `docs/llm-call-catalog.json` | **B** |
| Forensic trigger/skip | `docs/audit-workflows.md`, `docs/rp-data-layout.md` | **B** + children |

**Child J:** verifies documentation and forensic completeness; terminal cleanup only.

---

## 12. Runtime + forensics + documentation child invariant

> **runtime change + forensic migration + documentation migration = one complete child obligation**

Child **J** verifies; it does not reconstruct omitted B–I forensic or doc work.

---

## 13. Child J safe-removal rule

Obsolete implementation removable only when **all** apply:

1. responsibilities classified;
2. surviving responsibility migrated or responsibility is **`Delete`**;
3. replacement runtime validated where applicable;
4. consumers migrated;
5. no technical sequencing dependency remains;
6. forensic meaning migrated and validated;
7. tool trigger/skip evidence exists where applicable;
8. authoritative documentation describes new architecture;
9. tests migrated or deliberately retired;
10. repository evidence shows no remaining required consumer.

**No compatibility requirement** is a removal blocker.

---

## 14. Downstream dependency gates (requirements only)

| Gate | Requirement |
|------|-------------|
| **A** (this record) | `consensus_reached` on disposition map |
| **B** | Conditional invocation + forensic envelope before trustworthy tool forensics |
| **C** / **D** | Routing hypothesis validated before Director-tool-only production reliance |
| **E** | Plot/overlay and pressure tools off deleted mandatory topologies |
| **F** | Shared mediation tools |
| **G** | Narrator environmental tool |
| **H** | Conditional semantic repair; standing QA duties deleted |
| **I** | Long-horizon tool investigation (non-blocking for B–H) |
| **J** | Terminal verification and deletion per §13 |

Parallel after **A** + **B** baselines per #213: **C**, **E**, **F**, **G**, **H** where contracts allow; **D** after **C**; **I** experimental; **J** last.

---

## 15. Unresolved downstream questions (explicit)

- Long-horizon tool: trigger set, state thresholds, one vs many tools, Plot/Scribe overlap (§5).
- Post-commit execution topology for pressure/plot tools (not selected in Child A).
- Physical consolidation of cognition (#201 foundation hypothesis)—not approved.
- Obligation router placement and schema (**B**).

---

## 16. Child A validation criteria (#214 Issue body)

At **`consensus_reached`**, Child A deliverable **(1)** is satisfied by **this record** (disposition map with matrix/catalog cross-refs). Items **(2)–(4)** (retirement order detail, forensic risk register execution, blocking Child **J**) remain **program execution** artifacts refined during **investigating → consensus** investigation and downstream children; gates in §13–§14 govern **J**. Further #214-specific **implementation** work is **not** authorized until **`implemented`** stage for any runtime tract—this consensus records **design agreement only**.

---

*Recorded at GitHub `consensus_reached` for Issue #214, 2026-09-18.*
