# Core operating invariants

Stable truths operators and agents rely on when working in **Holy Grail RP**. This document **summarizes** invariants and points to **authoritative** specs; it does **not** replace them.

---

## Scene startup

- Scene lifecycle, Director-facing behavior, and RP workflow: **`ARCHITECTURE_OVERVIEW.md`**, **`docs/architecture.md`**
- Product intent and MVP boundaries: **`Holy Grail PRD.md`**
- **Current location:** committed scene/continuity truth is Python domain (`continuity_manager.py`) applied through Domain Host `commit_move`. Director **execution** is DSH phase plugins under `v2/rp_runtime/`. Director **context prepare / decision validate** is Domain Host (`v2/domain_api/`).

---

## Authored source

- Character / Template / Bootstrap / Opener payloads: **`AUTHORED_SOURCE_CONTRACT.md`**
- Packet contracts and glossaries: **`PACKET_CONTRACTS.md`**, **`GLOSSARY.md`**

---

## Audit

- Audit interpretation and workflows: **`docs/audit-workflows.md`** (canonical artifact and workflow reference)
- Scenario validation framing: **`SCENARIO_VALIDATION_FRAMEWORK.md`**

---

## Continuity

- **`ContinuityManager`** and committed narrative truth are authoritative at runtime.
- Retrieval, prompts, and audits are **non-authoritative** versus continuity unless explicitly documented otherwise.
- **Continuity authority doctrine** ([GitHub #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224)): **`SceneState`** / **`process_turn`** define **committed** truth; distinguish **intent**, **interpretation**, **commit**, and **observation**. Narrator prose and classifier/audit signals **do not** override **`SceneState`**.

Implementation: `v2/domain/modules/continuity_*.py`, `continuity_manager.py`.

---

## Data

- Canonical product data root: **`data/`** (`HG_DATA_DIR`)
- Layout: **`docs/rp-data-layout.md`**

---

## Governance

- **GitHub Issues** are the system of record for tracked work: **`governance/rp-app/issue-tracking-workflow.md`**
- Filing and verification: **`governance/policies/github-issues.md`**
- Cursor bootstrap: **`governance/policies/cursor-workflow-layer.md`**
- Workflow weights and bootstrap profiles: **`governance/rp-app/workflow-weights.md`**, **`docs/issue-bootstrap-profiles.md`**

Historical execution records under `governance/rp-app/` are program history, not current architecture authorities.
