# Workflow Efficiency Optimization Roadmap (Final)

## Objective

Reduce token overhead and workflow friction while preserving:

- issue-driven work authority
- architectural rigor
- validation reliability
- resumability
- auditability

Primary optimization target:

**Context replay overhead**

Not model output volume.

Empirical usage analysis showed cache/context replay is the dominant token sink.

---

# Core Principles

## Principle 1 — Reliability Remains Primary

Efficiency must not degrade:

- implementation accuracy
- validation quality
- issue integrity

---

## Principle 2 — No New Governance Framework

All efficiency changes integrate into the existing workflow system.

No parallel governance model.

---

## Principle 3 — Install Before Activate

Governance substrate must exist before instruction-set activation.

This prevents behavioral mismatch.

---

## Principle 4 — Optimize Replay, Not Authority

Reduce repeated issue interpretation.

Do not reduce issue authority.

Issue bodies remain canonical work truth.

---

# Phase 0 — Governance Substrate Installation (Inactive)

## Goal

Install optimization infrastructure without changing active workflow behavior.

Purpose:

Prepare activation safely.

---

## Scope

Implement:

- workflow weights
- bootstrap profiles
- core operating invariants
- execution anchors
- execution snapshots
- output compression standards
- baseline metrics

Behavior remains unchanged.

---

## Deliverable 1 — Workflow Weight System (Inactive)

Update:

`governance/rp-app/issue-tracking-workflow.md`

Add:

    ## Workflow weight
    light | standard | full

Definitions:

### Light

Use for:

- issue closure
- checklist sync
- labels
- metadata maintenance

---

### Standard

Use for:

- bug fixes
- UI fixes
- tests
- docs
- localized behavior changes

---

### Full

Use for:

- architecture changes
- migrations
- continuity contracts
- audit architecture
- destructive cleanup
- schema changes
- governance foundation changes

---

## Initial Default

`full`

Important:

Do not activate standard-by-default yet.

That happens in Phase 1.

---

## Escalation Triggers

Force full:

- continuity layer mutation
- authored contract mutation
- audit contract mutation
- runtime schema mutation
- scene lifecycle mutation

---

## Deliverable 2 — Workflow Weight Template Support

Update issue template:

Add:

    ## Workflow weight
    full

Inactive default.

---

## Deliverable 3 — Bootstrap Profiles

Create:

`docs/issue-bootstrap-profiles.md`

Define:

### Light Bootstrap

Required:

- AGENTS.md
- issue-tracking-workflow.md
- target issue body

---

### Standard Bootstrap

Required:

- light bootstrap
- directly affected modules
- module dependency chain via MODULE_INDEX

---

### Full Bootstrap

Required:

- standard bootstrap
- architecture docs
- contract docs
- audit docs
- governance docs relevant to scope

---

Status:

Advisory only (not enforced yet)

---

## Deliverable 4 — Core Operating Invariants

Create:

`docs/core-operating-invariants.md`

Compressed doctrine.

Required sections:

### Scene Startup Invariants

- unified scene-start spine
- UI/headless parity

---

### Authored Source Invariants

- opener assets are sole opening authority
- template prose is non-canonical

---

### Audit Invariants

- audit_session_owner canonical
- audit artifacts observational only

---

### Continuity Invariants

- continuity remains authoritative truth

---

### Governance Invariants

- issue body remains source of work truth

---

## Deliverable 5 — Execution Anchor

Update issue template:

Add:

    ## Execution anchor
    Current phase:
    Next required step:
    Locked scope:
    Active blocker:

Purpose:

Reduce full issue replay.

---

## Deliverable 6 — Execution Snapshot

Update issue template:

Add:

    ## Execution snapshot
    Validated current state:
    Current scope boundary:
    Known open risks:

Purpose:

Reduce semantic reconstruction.

---

## Deliverable 7 — Output Compression Standard

Update:

`governance/policies/github-issues.md`

Standardize implementation reports.

Required:

- files changed
- behavior changed
- tests run
- issue changes
- remaining work

Expand only when needed.

---

## Deliverable 8 — Baseline Capture

Capture previous 30 days.

Metrics:

- total tokens
- total cost
- total events
- cache reads
- cache writes
- average cost/day
- cost per successful issue

Store in issue comment.

---

## Validation Criteria

- substrate exists
- no active behavior changed

---

# Phase 1 — Instruction Set Alignment + Activation

## Goal

Synchronize operator behavior with new governance substrate.

This is the activation phase.

---

## Scope

Implement:

- instruction set refactor
- workflow-weight activation
- bootstrap enforcement
- anchor-first retrieval
- compressed reporting
- escalation authority

---

## Deliverable 1 — Bootstrap Selection Refactor

New flow:

1. determine workflow weight  
2. select bootstrap profile  
3. ingest required scope  
4. escalate if needed  

---

## Deliverable 2 — Consensus Refactor

### Light

No consensus unless design change emerges.

---

### Standard

Single consensus checkpoint.

---

### Full

Full consensus loop.

---

## Deliverable 3 — Retrieval Refactor

Priority order:

1. execution snapshot  
2. execution anchor  
3. issue body  

Not full issue replay first.

---

## Deliverable 4 — Reporting Refactor

Default compressed output.

Expanded output only for:

- architectural work
- ambiguity
- explicit request

---

## Deliverable 5 — Activate Workflow Weights

Change default:

from:

`full`

to:

`standard`

Activation starts here.

---

## Deliverable 6 — Activate Bootstrap Profiles

Profiles become authoritative.

No advisory mode.

---

## Deliverable 7 — Escalation Authority

Authority chain:

- Implementation AI may recommend escalation
- Oversight AI evaluates
- User decides

---

## Validation Criteria

- instructions match governance
- no contradictions
- activation successful

---

# Phase 2 — Stabilization Window

## Duration

14 days minimum

---

## Goal

Observe real-world behavior under new workflow.

No structural changes.

---

## Track

- under-bootstrap failures
- escalations
- confusion points
- issue reversals
- validation failures

---

## Required Output

Stabilization report.

Stored in issue comment.

---

# Phase 3 — 30-Day Efficiency Audit

## Goal

Measure actual operational improvement.

---

## Deliverable 1 — Usage Capture

Capture:

30 days post-activation

Required:

- total tokens
- total events
- total cost
- cache reads
- cache writes

---

## Deliverable 2 — Baseline Comparison

Compare:

pre-rollout vs post-rollout

Metrics:

- total token delta
- total cost delta
- cache ratio delta
- average cost/day delta
- cost per successful issue delta

---

## Deliverable 3 — Reliability Audit

Measure:

- reopened issues
- implementation reversals
- failed validations
- unexpected escalations

---

## Deliverable 4 — Workflow Audit

Evaluate:

- workflow-weight correctness
- bootstrap effectiveness
- execution anchor usefulness
- execution snapshot usefulness
- reporting compression usefulness

---

## Deliverable 5 — Recommendations

Per optimization:

- keep
- refine
- rollback

---

## Success Criteria

Lower:

- total token usage
- actual cost
- average daily cost

Stable:

- reliability
- validation quality
- issue integrity

Primary KPI:

**Cost per successful issue**

Secondary KPI:

**Token volume per successful issue**

Reliability remains the controlling metric.

---

# Phase 4 — Structural Refactor (Optional Future)

Separate from governance optimization.

Not part of this rollout.

Includes:

- long-file audit
- seam maps
- hotspot modularization

Only after efficiency audit.

---

# Rollout Order

1. Governance substrate installation  
2. Instruction alignment + activation  
3. Stabilization window  
4. 30-day audit  
5. Optional structural refactor  

---

# Explicit Exclusions

Not included:

- runtime architecture changes
- continuity refactors
- prompt architecture redesign
- retrieval architecture redesign
- modularization work
- new governance framework

These remain separate workstreams.