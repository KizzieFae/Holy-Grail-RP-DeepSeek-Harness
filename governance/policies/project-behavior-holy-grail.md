# Project Behavior



Use repo files as the source of truth.



Start with:



- `AGENTS.md`

- `docs/repo-map.md`

- `docs/code-style.md`



Follow these rules:



- preserve existing architecture and patterns unless the user explicitly requests a redesign

- prefer small, reviewable diffs over broad rewrites

- focus on files relevant to the task

- do not rely on tool memory as the only source of important behavior

- prefer extending existing modules and workflows before inventing new ones

- update shared docs when behavior, architecture constraints, or testing expectations materially change



If the task is multi-file, architecture-sensitive, or workflow-sensitive, read the relevant shared docs before editing.



---



## Work Tracking Authority



GitHub Issues are the authoritative record of:



- all active work

- investigation state

- validation results

- resolution status



No work may progress beyond initial exploration unless it is:



- linked to an existing Issue, or

- recorded as a new Issue



Chat reasoning is not considered persistent state.



## GitHub Projects metadata (mandatory)



For Holy Grail RP issues, **labels**, **RP System Workflow** membership, and **Project Status** / **Workflow** are **required** and must stay aligned with issue-body **`Current status:`** (**§H**). When **Priority** exists on the project, maintain a **non-empty** value (P0–P3) per **§B.5**; it does **not** replace **`Current status:`** or **Workflow**. Missing **Priority** or proof that relies only on **`gh issue view --json projectItems`** for Priority fails **§B.2**. Source of truth: `governance/rp-app/issue-tracking-workflow.md` **§B.1**–**§B.6**, **§C**.



- **Verification:** Run `gh issue view <N> --json number,state,labels,projectItems` **and** prove **Priority** with **`gh project item-list`**, the **Projects** UI, or **GraphQL** (see **§B.2**). Tracked issues must show **non-empty** `labels` and `projectItems` unless a **§B.1** exception is documented. When **Priority** is **material** to the task, include the **§B.2** **one-line** acknowledgment or update in the completion record.



- **Rejection:** Do **not** treat filing, transition, or closure as complete without passing verification and **§B.3** mapping, when **Priority** is missing or unproven per **§B.2**, when **§B.2** material **Priority** acknowledgment is missing, or when **§B.5** requirements (comments, handoffs, **Active Context** alignment) are violated.



---



## Issue State Transitions



All Issues must move through explicit states:



Investigating  

→ Awaiting consensus  

→ Ready to implement  

→ Implemented  

→ Validating  

→ Closed  



Before transitioning state, the following must be recorded:



- Investigating → evidence logged

- Awaiting consensus → classification + system layer

- Ready to implement → consensus block

- Implemented → summary of changes

- Validating → simulation or test results



---



## Evidence Requirement



An Issue is not valid without:



- scenario or reproduction context

- audit path or test reference

- specific observed behavior



Evidence must allow the issue to be understood without chat context.



Vague descriptions are not acceptable.



---



## Investigation workflow



### Multi-scenario default



- Investigations default to **multiple scenarios**: include at least **one baseline**, **one stress**, and **one variant** (pick from existing scenario definitions; orientation: `SCENARIO_VALIDATION_FRAMEWORK.md` at repository root, also linked from `autogen_rp/AGENTS.md`).

- **Single-scenario** evidence is **not** enough to **confirm** a pattern; it may support observations only (see `governance/policies/github-issues.md` for Issue-level wording).



### Evidence collection order



1. Run **simulations** (production-path / framework-aligned runs).

2. Extract **quantitative metrics** from runs and audits.

3. **Identify patterns** from those metrics across scenarios.

4. Only if still needed: **qualitative review** (human or AI), subject to the advisory rules below.



### AI assessment (advisory only)



- AI qualitative judgment is **advisory**: it does **not** replace audit artifacts, metrics, or deterministic system outcomes.

- It must **reference exact turns and artifacts** (paths, turn ids, audit files); it **must not override** deterministic behavior or logged facts.

- Use it **only after** simulation + metrics + pattern identification—suited to “**was this the right design/layer choice?**”, not “**did this happen?**” (the latter comes from simulations and artifacts).



---



## Consensus Gate



No implementation may begin unless the Issue contains:



- root cause

- correct system layer

- justification for that layer

- what will change

- what will NOT change



This must be written before any implementation begins.

Weight-aware **recording shape** (not a substitute for these bullets): **`issue-tracking-workflow.md` §B.0.1** and canonical weights **`governance/rp-app/workflow-weights.md`**.



---



## Validation Logging Requirement



After implementation, the Issue must include:



- scenario rerun or test execution

- audit session or test reference

- result (pass/fail)

- confirmation that the original failure is resolved

- regression check



An Issue cannot be closed without validation evidence.



---



## Retroactive Issue Handling



If an Issue is created after implementation has already occurred, it must still reflect the full workflow state progression.



Retroactive Issues must include an explicit execution-state summary covering:



- Investigating

- Awaiting consensus

- Ready to implement

- Implemented

- Validating



This summary must:



- indicate that each phase was completed

- reference evidence where applicable

- preserve traceability of reasoning and validation



Retroactive Issues must NOT:



- skip directly to Closed without documenting prior states

- omit validation evidence

- bypass the workflow model



GitHub Issues remain the authoritative record and must reflect the full lifecycle even when recorded after the fact.



---



## Workflow Drift Check



If an Issue remains in one state for an extended period:



- Investigating → likely missing evidence

- Awaiting consensus → unclear reasoning

- Implemented → validation not performed



Resolve drift before continuing new work.



---



## Active Context Requirement



**Authoritative record:** The GitHub **Issue body**, **Issue comments**, and **RP System Workflow** project fields (**Project Status**, **Workflow**, **Priority** when present) are the source of truth for execution state and decisions.



**Active Context** in chat is a **derived summary** of that record—helpful for orientation, **not** a substitute for it. Before starting a **new** chat or handoff, add a **session boundary** comment on the Issue (per `governance/rp-app/issue-tracking-workflow.md` **§B.5**); the new chat’s Active Context should **reflect** that comment and the latest Issue state, **not replace** them.



Every new chat must begin with an Active Context block containing:



- current Issue

- current **execution stage** / selection context (aligned with **`Current status:`** and project fields)

- current status

- current hypothesis

- key evidence

- open questions



This is the required mechanism for maintaining continuity across chats **when used as a mirror of GitHub**, not as independent state.



---



## Minimal System Constraint



Do not:



- introduce unnecessary workflow complexity

- create redundant tracking systems

- duplicate state across multiple tools



GitHub is the single source of truth for execution state.



---



## Subsystem Scope Clarification



Root-level rules and documentation define cross-project behavior and shared constraints.



Subsystem-specific guidance must live in subtree-local rules and documents.



Examples:



- RP (AutoGen / runtime / scene system) rules belong under the RP subtree

- Knowledge ingestion (future pipeline, graph/vector systems) rules will belong under their own subtree



Do not apply subsystem-specific assumptions globally.



Do not move subsystem-specific rules into root-level guidance.



Root-level guidance must remain valid across all subsystems.

