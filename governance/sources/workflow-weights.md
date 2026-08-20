# Workflow weights (Holy Grail RP)

Canonical vocabulary for **workflow weight** as used by Issue **[#145](https://github.com/KizzieFae/Holy_Grail_RP/issues/145)** (Governance + Activation Bundle), historical programme provenance in [governance/records/token-efficiency-plan-issue-145.md](../records/token-efficiency-plan-issue-145.md), and `.github/ISSUE_TEMPLATE/holy_grail_rp.yml`.

Authority for Issues and Projects metadata remains **`governance/sources/issue-tracking-workflow.md`**. This document defines weights **only**—not **`Current status:`**, filing gates, or validation substitutes.

**Orchestration vs execution (parity — authoritative Governance AI instruction set, supplied separately):** Orchestration AI (**GPT**) **assigns** workflow weight before substantive Issue work begins. Implementation AI (**Cursor**) inherits **assigned** / **effective** weight and MUST NOT independently reinterpret bootstrap depth or consensus rigor. **Assigned** and **effective** weights MUST persist where orchestration directs—in prompts to implementation AI; Issue **Execution snapshot** (and related Issue body fields); new-chat bootstrap context (**including `SYSTEM UNDERSTANDING REPORT`** discipline under **`governance/execution/cursor-workflow-layer.md`**).

---

## Activated defaults (Issue #145 Stage 3)

Issue **#145** Stage **3** is **activated** in-repo:

- **Routine default assigned workflow weight** for **new** Issues filed via `.github/ISSUE_TEMPLATE/holy_grail_rp.yml`: **`standard`** (template presents **`standard`** first; see template).
- **`docs/issue-bootstrap-profiles.md`** is **authoritative** for mandatory-read sets mapped from **effective** workflow weight (**assigned** on the Issue unless escalation forces **`full`** — see **Escalation triggers** below).
- **`standard`** and **`light`** consensus and bootstrap paths documented in **`issue-tracking-workflow.md` §B.0.1** and **`governance/execution/cursor-workflow-layer.md`** apply when **effective** weight is **`standard`** or **`light`** respectively.

Instruction-layer procedures (**weight-aware bootstrap**, **anchor-first retrieval**, **compressed reporting** defaults for Issue-facing notes) remain in **`governance/execution/cursor-workflow-layer.md`** and **`governance/execution/github-issues.md`**; they **cite this file** for meanings and triggers and **do not** redefine weights.

No automation substitutes for **`§H`** / **`§B.3`** execution-stage discipline.

---

## Values

| Weight | Meaning |
|--------|---------|
| **`full`** | Maximum bootstrap depth and consensus rigor per **`issue-tracking-workflow.md`** / **`governance/execution/cursor-workflow-layer.md`**. |
| **`standard`** | Mid tier: reduced replay overhead while preserving **`§B`** metadata discipline and verification proof requirements (no shortcuts around **`§B.2`**). |
| **`light`** | Minimal tier: smallest mandatory-read surface permitted by **`docs/issue-bootstrap-profiles.md`** (still **no** relaxed Issue authority). |

**Routine default assigned workflow weight (new template filings):** **`standard`**.

---

## Escalation triggers (force **`full`** discipline)

These situations **require full-weight rigor** even when **`standard`** or **`light`** was **assigned**:

- Ambiguity or disagreement blocks safe execution or consensus.
- Architecture-sensitive or multi-package changes; continuity / Director / audit semantics touched.
- Governance, template, or policy edits that affect **`§B`** filing, verification, or Cursor routing.
- Validation or **`§B.2`** proof requires expanded determinism (cannot honestly compress).

**Escalation authority:** When any criterion above applies, **GPT escalates effective workflow weight to `full`** per the **authoritative Governance AI instruction set** evaluated against this section. Implementation AI inherits **`full`** and MUST NOT independently narrow bootstrap reads or consensus rigor; it MAY surface the suspected trigger category on the Issue (**§B.5**) without copying definitions out of this file. **User** resolves material disagreement—still reconciled on the Issue thread, never chat-only.

---

## Related documents

- `governance/sources/issue-tracking-workflow.md` — **`§D`** body contract, **`§H`** execution stages, **`§B`** Projects synchronization, **§B.0.1** consensus shapes.
- `docs/issue-bootstrap-profiles.md` — Light / Standard / Full required reads (**authoritative**).
- `governance/execution/github-issues.md` — retrieval discipline; compressed reporting defaults (does not relax Issue bodies).
- Authoritative Governance AI instruction set (supplied separately; orchestration obligations — weight assignment, escalation, prompts)
- `.github/ISSUE_TEMPLATE/holy_grail_rp.yml` — workflow weight + execution anchor fields.

