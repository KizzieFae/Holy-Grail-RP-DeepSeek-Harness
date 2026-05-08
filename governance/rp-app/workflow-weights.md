# Workflow weights (Holy Grail RP)

Canonical vocabulary for **workflow weight** as used by Issue **[#145](https://github.com/KizzieFae/Holy_Grail_RP/issues/145)** (Governance + Activation Bundle), `Token efficiency plan.md`, and `.github/ISSUE_TEMPLATE/holy_grail_rp.yml`.

Authority for Issues and Projects metadata remains **`governance/rp-app/issue-tracking-workflow.md`**. This document defines weights **only**—not **`Current status:`**, filing gates, or validation substitutes.

---

## Activated defaults (Issue #145 Stage 3)

Issue **#145** Stage **3** is **activated** in-repo:

- **Routine default workflow weight** for **new** Issues filed via `.github/ISSUE_TEMPLATE/holy_grail_rp.yml`: **`standard`** (template presents **`standard`** first; see template).
- **`docs/issue-bootstrap-profiles.md`** is **authoritative** for mandatory-read sets mapped from declared weight (still subject to escalation below).
- **`standard`** and **`light`** consensus and bootstrap paths documented in **`issue-tracking-workflow.md` §B.0.1** and **`governance/policies/cursor-workflow-layer.md`** apply **when that weight is declared**, unless escalation forces **`full`**.

Instruction-layer procedures (**weight-aware bootstrap**, **anchor-first retrieval**, **compressed reporting** defaults for Issue-facing notes) remain in **`governance/policies/cursor-workflow-layer.md`** and **`governance/policies/github-issues.md`**; they **cite this file** for meanings and triggers and **do not** redefine weights.

No automation substitutes for **`§H`** / **`§B.3`** execution-stage discipline.

---

## Values

| Weight | Meaning |
|--------|---------|
| **`full`** | Maximum bootstrap depth and consensus rigor per **`issue-tracking-workflow.md`** / **`governance/policies/cursor-workflow-layer.md`**. |
| **`standard`** | Mid tier: reduced replay overhead while preserving **`§B`** metadata discipline and verification proof requirements (no shortcuts around **`§B.2`**). |
| **`light`** | Minimal tier: smallest mandatory-read surface permitted by **`docs/issue-bootstrap-profiles.md`** (still **no** relaxed Issue authority). |

**Routine default workflow weight (new template filings):** **`standard`**.

---

## Escalation triggers (force **`full`** discipline)

These situations **require full-weight rigor** even when **`standard`** or **`light`** is declared:

- Ambiguity or disagreement blocks safe execution or consensus.
- Architecture-sensitive or multi-package changes; continuity / Director / audit semantics touched.
- Governance, template, or policy edits that affect **`§B`** filing, verification, or Cursor routing.
- Validation or **`§B.2`** proof requires expanded determinism (cannot honestly compress).

**Escalation authority:** Implementation MAY recommend escalation to **`full`**. Oversight evaluates; **user decides**. Recommendations MUST remain reconciled to the Issue thread (**`§B.5`** handoff rule)—never chat-only authority.

---

## Related documents

- `governance/rp-app/issue-tracking-workflow.md` — **`§D`** body contract, **`§H`** execution stages, **`§B`** Projects synchronization, **§B.0.1** consensus shapes.
- `docs/issue-bootstrap-profiles.md` — Light / Standard / Full required reads (**authoritative**).
- `governance/policies/github-issues.md` — retrieval discipline; compressed reporting defaults (does not relax Issue bodies).
- `.github/ISSUE_TEMPLATE/holy_grail_rp.yml` — workflow weight + execution anchor fields.
