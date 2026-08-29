# Plot Cognition Overlay persistence contract

**Status:** Normative persistence contract — Issue **#59**  
**Semantic contract (preserved):** [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md) (#58)  
**Executable binding:** `v2/domain_api/plot_cognition_overlay_store.py`, `plot_cognition_overlay_repository.py`, `plot_cognition_overlay_service.py`  
**Parent program:** Issue **#48**

This document defines **persistence, lifecycle storage, boundedness enforcement, and load integrity** for Storyteller Plot Cognition Overlay **current state**. It does **not** redefine #58 cognition semantics.

---

## Authority boundary

| Concern | Owner |
|---------|--------|
| Authoritative world truth | **Continuity** |
| Advisory plot cognition (operative semantics) | **#58 contract** |
| Plot cognition **current-state persistence** | **This contract (#59)** |
| Semantic update/replan | **#61** |
| Orchestration / HTTP / post-commit timing | **#63** |
| Forensic evidence plane | **#64** |

The overlay store is **non-authoritative** and **must not** be embedded in `continuity_state` or session authoritative truth.

---

## Scope identity

Sessions persist:

```text
plot_cognition_scope_id
```

Resolution (`plot_cognition_scope.py`):

- Explicit non-blank `plot_cognition_scope_id` → use it.
- Otherwise → use resolved `memory_scope_id`.

**Anti-leak invariant:** A session loads/saves overlay state **only** through its persisted `plot_cognition_scope_id`. Sharing between sessions requires explicit configuration of the same scope id. No heuristic inference from Character, scenario, or text similarity.

Plot cognition scope and memory/knowledge scope are **semantically distinct** even when defaulted to the same value.

---

## Store identity and path

Sidecar file per scope:

```text
data/sessions/_plot_cognition_overlay/{plot_cognition_scope_id}.json
```

Envelope schema: `hg_plot_cognition_overlay_store_v1`

---

## Current-state purity

The store holds **current operative advisory cognition only**:

| Contained | Excluded |
|-----------|----------|
| Active/inactive non-retired goals | Retired goals/pressures |
| Active/inactive non-retired pressures | Tombstones |
| Zero or one current `GlobalPlotFrame` | Historical frame map |
| Sync metadata | Append-only history |
| | Staging / forensic artifacts |

Retired cognition is **not** represented in the current store.

---

## Lifecycle persistence semantics

Uses #58 `activity_state`:

| State | In current store | Operative consumption |
|-------|------------------|----------------------|
| `active` | Yes | Eligible when integrity READY |
| `inactive` | Yes | No |
| `retired` | **No** | No |

#59 provides **snapshot replacement** capability (including removal). It does **not** decide when semantic retirement should occur.

---

## Boundedness policy

Required v1 policy fields (injected — **no production numeric defaults in #59**):

```text
max_active_goals      (> 0)
max_active_pressures  (> 0)
```

Structural invariant: at most **one** active `GlobalPlotFrame` (store shape + validation).

Overflow replacement snapshots are **rejected** (`budget_exceeded`). The repository/service **never** auto-demotes, truncates, or ranks cognition.

---

## Load statuses

| Status | Meaning |
|--------|---------|
| `ABSENT` | No file; valid empty state |
| `READY` | Valid envelope, entries, and policy |
| `DEGRADED` | Loaded but integrity invalid (e.g. over-budget, malformed entry) |
| `CORRUPT` | Unreadable; quarantined; writes blocked |
| `UNSUPPORTED_VERSION` | Unknown envelope schema; fail closed |

Operative reads require `READY`. Degraded/corrupt/unsupported must not silently yield partial narrative authority.

---

## Corruption behavior

Corrupt files are **quarantined** and a sibling **`{scope}.blocked.json` marker** records the blocked load status so subsequent loads do **not** treat the scope as a fresh `ABSENT` store. Normal writes remain blocked until operator recovery (deferred UX).

---

## Atomicity

Overlay saves use atomic temp-write + rename with `store_revision` CAS.

**Continuity commit and overlay persistence are not one transaction.** Continuity remains authoritative if overlay write fails afterward (#39 Continuity rollback semantics unchanged).

---

## Concurrency

Overlay read-modify-write is serialized by a lock keyed on `plot_cognition_scope_id`, with CAS revision as a second guard. Cross-lock ordering with session locks is owned by **#63**.

---

## Assimilation freshness

Store metadata:

```text
assimilated_through_domain_commit_id: str | null
```

Meaning: latest authoritative domain commit whose consequences this snapshot **claims to have incorporated**. `null` = none yet assimilated.

Staleness uses **equality only** against a supplied current commit id (`domain_commit_id` values are opaque UUID-based identifiers — no lexical ordering).

---

## Forensic-preservation gate

> Destructive removal of cognition from current state must not be enabled in a production integration path unless the parent #48 forensic-preservation obligation has been satisfied for the removed semantic state.

#59 does **not** implement forensic events, staging stores, or history. **#64** owns evidence capture. **#63** must gate live destructive integration until that path exists.

---

## Downstream ownership

| Issue | Responsibility |
|-------|----------------|
| **#60** | Initialization inference |
| **#61** | Semantic update/replan |
| **#62** | Consumer projection |
| **#63** | Orchestration, policy wiring, post-commit timing |
| **#64** | Forensic evidence plane |
| **#65** | Scenario validation / policy tuning |

---

## Composition

`PlotCognitionOverlayRepository` is a **sibling** sidecar repository (constructed alongside session repos). `PlotCognitionOverlayService` is exposed through **`CognitionComposition`**. `DomainKernel` must not own boundedness or lifecycle policy.
