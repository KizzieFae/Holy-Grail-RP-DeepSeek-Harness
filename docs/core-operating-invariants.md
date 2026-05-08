# Core operating invariants

Stable truths operators and agents rely on when working in **Holy Grail RP**. This document **summarizes** invariants and points to **authoritative** specs; it does **not** replace them.

Cross-issue reference for Issue **[#145](https://github.com/KizzieFae/Holy_Grail_RP/issues/145)** governance bundle (substrate, instruction alignment, activation).

---

## Scene startup

- Scene lifecycle, Director-facing behavior, and RP workflow expectations live under **`autogen_rp/python/rp_app/ARCHITECTURE.md`** and **`autogen_rp/docs/architecture.md`**.
- Product intent and MVP boundaries: **`Holy Grail PRD.md`** (repository root).

---

## Authored source

- Boundaries for Character / Template / Bootstrap / Opener payloads: **`AUTHORED_SOURCE_CONTRACT.md`** (repository root).
- Packet contracts and glossaries: **`PACKET_CONTRACTS.md`**, **`GLOSSARY.md`**.

---

## Audit

- Audit interpretation, signals, and issue-tracking ties: **`autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`**.
- Operational audit workflows: **`autogen_rp/docs/audit-workflows.md`**.
- Scenario validation framing (when applicable): **`SCENARIO_VALIDATION_FRAMEWORK.md`** (repository root).

---

## Continuity

- **`ContinuityManager`** and committed narrative truth are authoritative at runtime per **`autogen_rp/python/rp_app/ARCHITECTURE.md`**.
- Retrieval, prompts, and audits are **non-authoritative** versus continuity unless explicitly documented otherwise.

---

## Governance

- **GitHub Issues** are the system of record for tracked work; **`§D`** body contract and **`§H`** execution stages: **`governance/rp-app/issue-tracking-workflow.md`**.
- Filing, verification, and safe body mutation: **`governance/policies/github-issues.md`**.
- Cursor bootstrap / delegation / anchoring: **`governance/policies/cursor-workflow-layer.md`**.
- Active Context vs Issue truth: **`governance/policies/project-behavior-holy-grail.md`**.
- Workflow weights, filing default (**`standard`**), and authoritative bootstrap profiles: **`governance/rp-app/workflow-weights.md`** and **`docs/issue-bootstrap-profiles.md`**.
