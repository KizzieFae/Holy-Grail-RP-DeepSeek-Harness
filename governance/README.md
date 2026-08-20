# Governance

Project-owned governance for **Holy Grail RP**: workflow authority, issue tracking, and operating rules.

## Physical layout (A/B/C/D)

| Class | Location | Role |
|-------|----------|------|
| **A — System/bootstrap** | Repository root, `bindings/`, `docs/issue-bootstrap-profiles.md`, `.cursor/rules/`, `.github/ISSUE_TEMPLATE/`, `governance/project-sync.toml` | Structurally required adapters, late-bound identity, bootstrap read profiles, template sync manifest — **not** the governance-source corpus |
| **B — Governance-AI source authorities** | `governance/sources/` | Canonical project authorities Governance AI relies on for **governance/workflow decisions** (authority function, not mere readership) |
| **C — Implementation execution policies** | `governance/execution/` | Canonical policies primarily governing Implementation-AI / repository execution |
| **D — Records / supporting** | `governance/records/` | Historical, workshop, program-record, or governance-meta material that is **not** current Governance-AI source authority |

Product architecture and operation: repository root `README.md`, `ARCHITECTURE_OVERVIEW.md`, `AGENTS.md`, and `docs/`.

## Creating governance documents

Before adding a new governance file, classify it:

1. **Governance/workflow source authority** → `governance/sources/`  
   Use when the document is canonical project authority Governance AI relies on for governance/workflow decisions (Issue/Project mechanics, workflow weights, audit semantics, orchestration rules, work-tracking/consensus rules).

2. **Implementation/repository execution policy** → `governance/execution/`  
   Use when the document primarily governs Implementation-AI behavior (Cursor bootstrap layer, GitHub CLI discipline, architecture/testing guardrails for implementers).

3. **Historical/workshop/program/meta record** → `governance/records/`  
   Use for non-authoritative history, workshop artifacts, program closure records, or governance meta notes. Add or preserve a **HISTORICAL WORKSHOP** (or equivalent) banner when not current authority.

4. **System/bootstrap surface** → keep in designated root/docs/bindings/Cursor/template/sync locations  
   Do **not** place new policy canon in bootstrap adapters or move bootstrap files into `governance/` merely because they participate in governance.

Do **not** create authorities under retired paths (`governance/policies/`, `governance/rp-app/`, `governance/github/`).

## `sources/` — Governance-AI source authorities

| File | Role |
|------|------|
| `gpt-workflow-instruction-set.md` | Orchestration AI obligations (weight assignment, escalation, prompts) |
| `workflow-weights.md` | Canonical `light` / `standard` / `full` definitions and escalation triggers |
| `issue-tracking-workflow.md` | GitHub Issues / Projects workflow (§A–§K); bound in `bindings.toml` |
| `audit-semantics.md` | Program / system quality audit semantics |
| `project-behavior-holy-grail.md` | Work tracking authority, consensus gate, Active Context rules |

For program/system quality audits, use **`sources/audit-semantics.md`**. For RP session-audit procedure, use **`docs/audit-workflows.md`**.

## `execution/` — Implementation execution policies

| File | Role |
|------|------|
| `cursor-workflow-layer.md` | Cursor bootstrap, SYSTEM UNDERSTANDING REPORT, weight-aware bootstrap |
| `github-issues.md` | GitHub CLI filing/retrieval discipline |
| `architecture-protection.md` | Python architecture guardrails |
| `rp-app-guidance.md` | RP runtime implementation guidance |
| `testing-expectations.md` | Python testing expectations |

Cursor rules `@`-include execution policies and route project behavior to `sources/project-behavior-holy-grail.md`.

## `records/` — Historical / supporting (not current Governance-AI authority)

| Path | Role |
|------|------|
| `fresh-start-m14-5-program-closure.md` | M14 fresh-start program closure |
| `audit-classification-protocol.md` | ACP workshop interchange skeleton (#187) |
| `failure-taxonomy-spec-v1.md` | FT1 partial registry (#186) |
| `round-a-*.md` | Round-A workshop facilitation artifacts |
| `github/issue-templates.md` | Issue template ownership meta notes |

## Separation rules

- **Bindings** → `bindings/bindings.toml` (late-bound repository, upstream, and GitHub Project identity)
- **Governance sources** → `governance/sources/`; edit canonical governance authority here, not inside Cursor stubs
- **Cursor adapters** → repository-root `.cursor/rules/*.mdc` (four-file portable set)
- **Product docs** → repository root and `docs/`

## Related

- `../bindings/bindings.toml` — canonical entrypoints for agents/tools
- `../AGENTS.md` — instruction priority and bootstrap pointers
