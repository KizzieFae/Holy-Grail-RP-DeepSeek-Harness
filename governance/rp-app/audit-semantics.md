# Program audit semantics

**Authority:** Canonical semantics for **program / system quality audits** in Holy Grail RP (for example: Documentation & Governance Integrity; Repository / Filesystem Architecture; Runtime & Execution Efficiency; End-to-End Operational Flow).

**Not in scope:** RP session-audit **procedure** (`docs/audit-workflows.md`); Issue/Project workflow mechanics (`governance/rp-app/issue-tracking-workflow.md` §D–§H, §B); workflow weights; V1 `#59` Signal-id inventory (not live).

**Portability:** Reusable 2-AI governance. Holy Grail implements this authority locally; template synchronization may follow separately.

---

## Authority boundary

| Concern | Owner |
|---------|--------|
| Program-audit semantics (this document) | Finding model, material findings, classification, disposition, closure, decomposition, **read-only program audit** pathway |
| RP session-audit procedure | `docs/audit-workflows.md` |
| Remediation Issues (Type, Layer, Pattern, §H, Priority, weights) | `issue-tracking-workflow.md`, `workflow-weights.md`, `project-behavior-holy-grail.md` — **cite only; do not redefine** |
| Continuity vs audit observation | `ARCHITECTURE_OVERVIEW.md`, `docs/architecture.md`, `docs/core-operating-invariants.md` |
| Depth-1 Evaluation Records / incidental findings | `issue-tracking-workflow.md` **§A.2–A.3** only when triggered |
| V1 `#59` RP JSON signal inventory | **Not live** — separate future cycle if needed |
| ACP / FT1 / Round-A workshop specs | **Historical workshop** — not current program-audit authority |

---

## Observation → finding → recommendation → remediation

```text
observation
    ↓ sufficient evidence for evaluative conclusion
finding (material finding only)
    ↓ optional
recommendation
    ↓ explicit Issue/workflow authorization
remediation
```

| Term | Definition |
|------|------------|
| **Observation** | Evidence-bearing information discovered during an audit that does **not** by itself require a material evaluative conclusion. |
| **Finding** | Evidence-supported **evaluative conclusion** (material finding). |
| **Recommendation** | Optional proposed response to a finding. **Not authorization.** |
| **Remediation** | Authorized work performed through normal Issue/workflow authority. |

**Hard rules**

- A recommendation is not authorization.
- Audit findings do **not** authorize repository mutation.
- Remediation requires a tracked Issue reaching **`consensus_reached`** before implementation (per `issue-tracking-workflow.md` §H), unless duplicate/withdrawn intake exceptions apply.

---

## Material finding

A **material finding** is an evidence-supported evaluative conclusion significant enough to affect at least one of:

- the audit's overall assessment or closure;
- the accepted-design / accepted-conclusion record on the audit parent;
- durable debt or risk visible to later audits;
- remediation or explicit deferral;
- how a later audit interprets the same evidence.

**Only material findings** require: evidence, four-way **classification**, and **disposition**.

Incidental **observations** may be logged on the audit parent without classification or disposition.

---

## Material-finding classification

Use exactly one class per material finding:

### `correct as-is`

Examined and supported as appropriate for the current system. No change warranted. May be cited by later audits.

### `worthwhile refinement`

Current state is acceptable and does not violate a current requirement, but a bounded improvement would provide meaningful value. Absence of that improvement is **not** itself a current defect.

### `architectural debt`

Current state functions or is tolerable, but carries material structural/design cost, risk, duplication, drift, maintainability burden, false authority, or future constraint requiring durable disposition.

### `actual defect`

Current state violates an applicable current requirement, invariant, or authority, or prevents a fresh operator from succeeding using current authorities.

**Do not add subtypes** without demonstrated need and Governance agreement.

### Classification does not determine urgency

Program-audit classification does **not** determine:

- Issue **Type** (§E);
- optional Issue **Severity**;
- Project **Priority** (P0–P3);
- **workflow weight**;
- §H **workflow state**.

Illustrations:

- `actual defect` does **not** imply P0/P1.
- `architectural debt` does **not** imply low Priority.
- `worthwhile refinement` does **not** mean permanently optional.
- `correct as-is` may be re-examined if later evidence materially changes.

Urgency and rigor remain governed by existing workflow authorities on **remediation Issues**.

---

## Confidence

- **Evidence is primary.**
- Record **confidence** only when uncertainty is **material** to classification, disposition, or closure.
- Permitted values when recorded: `high` | `moderate` | `low` (inline on the audit parent; not a mandatory Issue/Project field).
- Omitted confidence ⇒ sufficient unless challenged.

---

## Disposition

**Classification** (what kind of conclusion) and **disposition** (what happens next) are **separate**.

| Disposition | Meaning |
|-------------|---------|
| **`accepted`** | No further action on this finding. Normal disposition for **`correct as-is`**. |
| **`remediation_tracked`** | One or more remediation Issues linked from the audit parent. |
| **`deferred`** | Conscious deferral with Issue anchor or explicit “deferred to Audit N / cycle X” on the audit parent. |
| **`monitor`** | Watch; revisit condition stated; no committed remediation. |
| **`blocking`** | Prevents audit closure until resolved or scope formally revised. |

**§A.2 dispositions** (`none` / `monitor` / `defer` / `file_issue`) apply only to depth-1 Evaluation Record incidental findings when **§A.2** triggers. They are **not** program-audit dispositions.

---

## Remediation decomposition

Do **not** require one finding → one Issue.

Group or split remediation Issues by **coherent implementation/governance responsibility**.

| Pattern | Allowed |
|---------|---------|
| Multiple related findings → one remediation Issue | Yes |
| One broad finding → multiple remediation Issues | Yes |
| Finding → no remediation Issue | Yes when disposition is `accepted`, or `monitor` / `deferred` without implementation |

Recommendations remain non-authorizing until normal workflow permits remediation.

When filing remediation Issues, map program-audit class to Issue **Type** (§E) at filing time; do not treat class as Type.

---

## Read-only program audit

A **read-only program audit** is a **Governance-authorized, non-mutating** investigation of repository or work-system state. It uses the finding semantics in this document but **does not** require a GitHub Issue or Project item merely to inspect, evaluate, measure, classify findings, and report conclusions.

**Governing principle:** Issue/workflow rigor attaches to **repository mutation and durable remediation work**, not automatically to read-only investigation.

### Activation (Governance)

Before a read-only program audit begins, Governance must provide:

- **named audit** (for example: Audit 2 — Repository / Filesystem Architecture);
- **scope** (inclusions and exclusions);
- **repository anchor** (commit SHA) or explicit HEAD-at-start instruction;
- **assigned workflow weight** (`light` | `standard` | `full`);
- **effective workflow weight** when escalated;
- explicit designation: **read-only program audit**.

Workflow weight controls investigation rigor and bootstrap depth. It does **not** by itself create an Issue requirement. A substantial read-only audit may be **`standard`** or **`full`** while remaining Issue-free.

### Permitted actions

When conducting an authorized read-only program audit, the actor may:

- inspect and search repository files and history (read-only `git` operations);
- inspect dependency, package, and configuration structure;
- perform read-only GitHub inspection when relevant (`gh issue view`, `gh project item-list`, etc.);
- run existing tests and read-only diagnostics, profiling, or benchmarks that do not modify **tracked** repository state;
- reason about architecture and system behavior;
- classify material findings under this document;
- produce recommendations (non-authorizing);
- create **temporary, untracked** diagnostic artifacts when necessary, provided they are **not committed** and are cleaned up before the audit completes.

### Prohibited actions

A read-only program audit must **not**:

- edit **tracked** repository files;
- create, delete, or move **tracked** repository content;
- commit or push;
- modify git remotes;
- create, edit, or close GitHub Issues or pull requests;
- modify GitHub Project state;
- implement remediation because a finding was discovered;
- leave diagnostic clutter in the repository;
- continue under the read-only designation after mutation becomes necessary.

Discovering a defect does **not** authorize fixing it.

### Escalation boundary

**Stop** the read-only audit and return to Governance before any mutation if:

- a proposed change is discovered;
- investigation cannot safely continue without changing repository or GitHub state;
- evidence reveals a high-risk integrity or architecture problem requiring intervention;
- workflow-weight escalation criteria materially change the work (`workflow-weights.md`);
- the work has become **implementation** rather than investigation.

Governance may then: **(1)** narrow scope and continue read-only; **(2)** authorize normal remediation through tracked Issue/workflow; or **(3)** stop the audit.

Related findings may be grouped into **one coherent remediation Issue**. Do **not** impose one Issue per finding.

### Reporting and durability

A read-only program audit must deliver a **structured report** to Governance (and the user) containing at minimum:

1. audit name, scope, and repository anchor;
2. assigned and effective workflow weight;
3. coverage and explicit gaps;
4. material findings with IDs, evidence, and classifications;
5. **recommended dispositions** for Governance review;
6. overall assessment;
7. recommended coherent remediation packages, if any;
8. **no-mutation attestation**.

**Durability rules:**

- The read-only audit itself does **not** require persistent repository or GitHub state merely for having occurred.
- **Ordinary chat output is not** an authoritative durable project record or system of record.
- During a read-only audit, findings carry **recommended dispositions**; a recommendation is **not** authorization and **not** a final disposition.
- Findings selected for remediation become durable when the corresponding **remediation Issue** is opened and tracked under normal workflow authority.
- If Governance deliberately wants an audit report persisted for later reference, that requires **separate explicit authorization**; persistence is not mandatory to perform the audit.
- Later audits may cite accepted read-only conclusions as **`Audit N report, finding ID`** (for example: “B3 per Audit 2 report”). Historical Audit 1 conclusions remain citeable as **`#1` + finding ID** (parent-Issue model).

### Completion (read-only pathway)

A read-only program audit **completes** when the scoped investigation and structured report are delivered and Governance accepts or otherwise resolves the report. It does **not** acquire a synthetic Issue lifecycle merely so it can be “closed.”

### Relationship to parent-Issue audits

Some program audits (for example Post-Migration Audit 1, DSH **#1**) were conducted using an **audit parent Issue**. That model remains valid when Governance chooses it.

- **§Audit closure** below applies **only** when an audit is conducted using an audit parent Issue.
- **Read-only program audits** use the activation, reporting, and completion rules in **this section** instead.
- Audit 1 (**#1**) is **historical precedent** under the parent-Issue model; do not rewrite its record.

Remediation discovered by either pathway still requires normal Issue/workflow authority before implementation.

---

## Audit closure

**Scope:** This section applies **only** when a program audit is conducted using an **audit parent Issue**. For read-only program audits, see **Read-only program audit** above.

An audit parent Issue may reach terminal **`closed`** (per §H) when **all** hold:

1. **Scope examined** — defined audit scope sufficiently covered; gaps explicit.
2. **Material findings complete** — each has evidence, classification, disposition.
3. **Future work anchored** — action beyond the audit record is Issue-anchored or explicitly `accepted` / `monitor`.
4. **Conclusions durable** — overall assessment and deferred-work index on the audit parent Issue (body and/or comments).
5. **No blocking disposition** — no unresolved `blocking` finding.

**Child remediation Issues need not be `closed`** before the audit parent closes, provided dispositions are `remediation_tracked` or `deferred` with anchors.

This section defines **when substantive audit work is complete**. §H and §B.3 still govern Issue transitions and Project fields. Audit parent Issues typically remain at **`consensus_reached`** while recording findings; they do **not** use **`implemented`** / **`validated`** for product work on the audit Issue itself.

---

## Accepted conclusions

No separate accepted-design registry.

Accepted conclusions and final material-finding dispositions are durable on:

- the **audit parent Issue** (body and/or comments), when an audit uses that model; or
- the **accepted read-only audit report**, when Governance closes a read-only program audit under **Read-only program audit** above.

Later audits cite prior conclusions as **`audit Issue # + finding ID`** (for example: “A10 per #1”) or **`Audit N report, finding ID`** for read-only pathway audits.

---

## §A.2 / #59 boundary

- The V1 **`#59` Signal-id inventory** from deleted `AUDIT_DOCUMENTATION.md` is **not current authority** and is **not** restored or implied by this document.
- Do **not** apply `#59` reading order to program-audit findings.
- **`issue-tracking-workflow.md` §A.2–A.3** remain valid **only** when a depth-1 Evaluation Record trigger fires; completing that methodology does **not** resurrect the V1 inventory.
- Live DSH/Host RP JSON field/signal semantics, if needed later, are a **separate future cycle**.

---

## Related documents

- `docs/audit-workflows.md` — RP session-audit procedure
- `governance/rp-app/issue-tracking-workflow.md` — Issue tracking, §A.1 pipeline, §A.2–A.3 when triggered
- `governance/rp-app/workflow-weights.md` — workflow weight only
- `governance/README.md` — current vs historical governance index
