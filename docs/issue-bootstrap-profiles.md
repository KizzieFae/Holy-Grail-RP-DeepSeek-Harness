# Issue bootstrap profiles

Defines **required reads** for starting Issue-driven work at three depths. Paths are **repo-relative from the Holy Grail RP repository root** unless noted.

**Authority:** This document is **authoritative** for bootstrap read sets mapped from **effective** workflow weight (**assigned** on the Issue unless escalation forces **`full`**) after Issue **#145** Stage **3** activation. Canonical weight meanings and escalation triggers: **`governance/sources/workflow-weights.md`** only. Selection procedure: **`governance/execution/cursor-workflow-layer.md`** → **Weight-aware bootstrap**.

---

## Full

Use when weight is **`full`**, or whenever **`workflow-weights.md`** escalation forces **`full`** rigor.

**Always**

- `AGENTS.md`
- `governance/sources/issue-tracking-workflow.md` (**`§B`** Projects + **`§D`** body contract + **`§H`** stages)
- `governance/execution/github-issues.md`
- `governance/sources/project-behavior-holy-grail.md`
- `governance/execution/cursor-workflow-layer.md`

**When task touches RP runtime / domain modules**

- `MODULE_INDEX.md`
- `docs/architecture.md`
- `ARCHITECTURE_OVERVIEW.md`
- `docs/testing.md`
- `Holy Grail PRD.md` (as applicable)

**When auditing / continuity debugging**

- `governance/sources/audit-semantics.md` (program audits)
- `docs/audit-workflows.md` (RP session-audit procedure)
- `docs/rp-data-layout.md`

---

## Standard

Mid-depth bootstrap when **effective** weight is **`standard`** (routine **assigned** default per **`workflow-weights.md`**).

**Baseline**

- `AGENTS.md`
- `governance/sources/issue-tracking-workflow.md` (**`§B`**, **`§D`**, **`§H`**)
- `governance/execution/github-issues.md`

**Add per task class from `AGENTS.md` → Minimum guidance reads** (architecture, scenario validation, repo map, etc.) without replaying the entire Full list unless escalation triggers apply.

---

## Light

Minimal reads when **effective** weight is **`light`** (**assigned** unless escalation forces **`full`**; still **no** shortcuts on Issue mandatory fields or **`§B.2`** verification).

**Minimum**

- `AGENTS.md` (including Instruction priority and Repo working rules)
- `governance/sources/issue-tracking-workflow.md` — at minimum **`§B.1`–`§B.5`**, **`§D`**, **`§H`**, **`§F`** Layer appendix as needed
- `governance/execution/github-issues.md`

Expand immediately if ambiguity, architecture risk, or audit/evidence work appears (**`governance/sources/workflow-weights.md`** escalation).

