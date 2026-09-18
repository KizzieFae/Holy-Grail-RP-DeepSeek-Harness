# Governance

Project-owned governance for **Holy Grail RP**: workflow authority, issue tracking, and operating rules.

## Physical layout (A/B/C/D)

| Class | Location | Role |
|-------|----------|------|
| **A — System/bootstrap** | Repository root (`AGENTS.md`), `bindings/`, `docs/issue-bootstrap-profiles.md`, `.cursor/rules/`, `.github/ISSUE_TEMPLATE/`, `governance/project-sync.toml` | Structurally required adapters, late-bound identity, Implementation bootstrap read profiles, template sync manifest — **not** the Governance upload corpus |
| **B — Governance-AI source corpus** | `governance/sources/` | **Minimum sufficient standing** project sources Governance AI uploads after the universal instruction set |
| **C — Implementation execution policies** | `governance/execution/` | Canonical policies primarily governing Implementation-AI / repository execution |
| **D — Records / supporting** | `governance/records/` | Historical, workshop, program-record, or governance-meta material that is **not** current Governance-AI authority (see **active program disposition map** exception below) |

Product operation and Implementation navigation: repository root `README.md`, `AGENTS.md`, `docs/`, and subsystem docs under `v2/`.

## Governance source corpus rule

> `governance/sources/` contains the **minimum sufficient standing** project source corpus for Governance AI. A document belongs there only when its **persistent contents** provide a Governance capability that cannot reasonably be supplied through on-demand Implementation evidence retrieval.
>
> **Placement does not imply exclusive readership.** Shared authorities retain **one canonical copy** and may be routed to Implementation through bootstrap profiles, `AGENTS.md`, bindings, and adapters.
>
> Do **not** add files to `sources/` merely because they are important or authoritative elsewhere in the repository.

**Human upload invariant:** Supply the **authoritative universal Governance AI instruction set** maintained **outside this repository** (versioned in the reusable development-system template; supplied separately at Governance session start). Then upload **all** files in `governance/sources/` — currently **six** Holy-Grail **project-specific standing sources**. This repository **intentionally does not** store a duplicate universal instruction-set copy. Project sources specialize Holy Grail workflow; they do **not** redefine universal Governance/Implementation role separation.

**Template sync note:** Reusable template sync must **not** reintroduce the universal instruction set into `governance/sources/` merely because the template versions it.

## `sources/` — Governance upload corpus (six project-specific files)

| File | Role |
|------|------|
| `workflow-weights.md` | Canonical `light` / `standard` / `full` definitions and escalation triggers |
| `issue-tracking-workflow.md` | GitHub Issues / Projects workflow (§A–§K); bound in `bindings.toml` |
| `audit-semantics.md` | Program / system quality audit semantics; read-only investigation authority |
| `project-behavior-holy-grail.md` | Work tracking authority, consensus gate, Active Context rules |
| `holy-grail-prd.md` | Product purpose, requirements, and intent |
| `architecture-overview.md` | Current system topology and standing architectural invariants |

For RP session-audit **procedure** (Implementation retrieval): `docs/audit-workflows.md`.

## Creating governance documents

Before adding a new governance file, classify it:

1. **Governance standing source** → `governance/sources/`  
   Only when persistent Governance capability requires it and on-demand Implementation evidence is insufficient.

2. **Implementation/repository execution policy** → `governance/execution/`  
   Cursor bootstrap layer, GitHub CLI discipline, architecture/testing guardrails for implementers.

3. **Historical/workshop/program/meta record** → `governance/records/`  
   Non-authoritative history. Add or preserve a **HISTORICAL WORKSHOP** banner when not current authority.

4. **System/bootstrap surface** → designated root/docs/bindings/Cursor/template/sync locations  
   Do **not** move bootstrap machinery into `sources/` for folder purity.

Do **not** create authorities under retired paths (`governance/policies/`, `governance/rp-app/`, `governance/github/`).

### Active program disposition map (narrow exception)

An **active program disposition map** accepted at Issue **`consensus_reached`** may remain the **single canonical detailed copy** under `governance/records/` when **explicitly routed** from a standing source in `governance/sources/` (currently: next-gen migration anchors in `architecture-overview.md`) and from scoped rules in `docs/issue-bootstrap-profiles.md`. Such a record is **migration-program authority** for its program; it is **not** part of the six-file Governance-AI upload corpus and does **not** make `governance/records/` generally current authority. Importance alone does **not** qualify other Issue records for this exception.

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
| `runtime-narrative-memory-prd1.md` | Historical PRD1 (narrative memory programme) |
| `narrative-knowledge-ingestion-prd2.md` | Historical PRD2 (ingestion programme) |
| `narrative-memory-evolution-roadmap.md` | Historical evolution roadmap (RTF body preserved) |
| `registry-validation-report.md` | Completed registry validation snapshot |
| `token-efficiency-plan-issue-145.md` | Issue #145 programme provenance (not live workflow authority) |
| `operational-retrieval-pilot.md` | Closed retrieval pilot runbook |
| `issue-112-player-pvr-architectural-assessment.md` | Issue #112 player PVR architectural assessment (SQA-03) |
| `progression-layer-validation-status-v1.md` | Completed progression v1 checkpoint |
| `issue-214-child-a-disposition-map-2026-09-18.md` | **Active program disposition map** (#213 ng-rp migration; Child A #214) — single canonical detailed copy; routed via `architecture-overview.md` + bootstrap profiles |

## Separation rules

- **Bindings** → `bindings/bindings.toml` (late-bound repository, upstream, and GitHub Project identity)
- **Governance sources** → `governance/sources/`; edit canonical Governance standing authorities here
- **Cursor adapters** → repository-root `.cursor/rules/*.mdc` (four-file portable set)
- **Implementation docs** → `docs/`, contracts at repository root, `v2/`

## Related

- `../bindings/bindings.toml` — canonical entrypoints for agents/tools
- `../AGENTS.md` — Implementation bootstrap and navigation (not Governance upload corpus)
