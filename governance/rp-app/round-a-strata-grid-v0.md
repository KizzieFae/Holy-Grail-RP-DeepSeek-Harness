# Round A Strata Grid v0

> **Status: HISTORICAL WORKSHOP** — Not current program-audit authority. See `governance/rp-app/audit-semantics.md`.

<!--
  Operational workshop steering only — NOT FT1/ACP normative semantics.
  Ephemeral v0: revise or retire after Round A / S1 gate (#186).
  Related: failure-taxonomy-spec-v1.md (FT1), audit-classification-protocol.md (ACP).
-->

## Document posture

| Aspect | Position |
|--------|----------|
| **Authority** | **Operational / facilitative** — corpus balancing and `scenario_tags` stabilization for Round A. **Does not** define FTC meaning, runtime behavior, detectors, CI, or audit applicability truth. |
| **Normativity** | **Process recommendation** for facilitators. **Not** ‖N‖ law like FT1; teams may document conscious deviations on the tracking Issue. |
| **Lifespan** | **v0 Round A only** — expect replacement or merge into a post-workshop note after S2 spec patch. |
| **ACP coupling** | Maps to `scenario_tags` in **ACP §5** (`audit-classification-protocol.md`). Tags below are the **canonical v0 vocabulary** for Round A. |

---

## Corpus size target

- **Round A target band:** **40–60** exemplar units (one `exemplar_unit_id` per **ACP §5** package).
- Quotas below are **percentage bands** of **actual N** (round to nearest integer; **±1** unit slack per stratum row allowed).

---

## Primary strata (mutually exclusive)

Each unit receives **exactly one** `primary_stratum` tag (record in facilitator ledger + ACP `scenario_tags`).

| `primary_stratum` | Purpose | Stress target | Quota (% of N) | Anti-overrepresentation |
|-------------------|---------|---------------|----------------|-------------------------|
| **`audit_clean`** | Healthy audit read path | Applicability + read-order discipline without artifact chaos | **22–30%** | Do not exceed **32%** without recording rationale on tracking Issue. |
| **`audit_stressed`** | Noisy / missing / confusing audit path | Same read-order rules under poor artifact hygiene — **without** using FTC as applicability substitute | **18–26%** | Do not exceed **30%**; avoid picking **only** "worst" sessions. |
| **`continuity_narrow`** | Tight excerpt scope | `FR4` boundary: labels **hypothesize** from narrow slice | **18–26%** | Must not be **>35%** of corpus (prevents over-narrowing workshop). |
| **`continuity_arc`** | Multi-turn / session-dependent reading | Temporal + narrative arc — still **no** continuity authority in labels | **14–22%** | Cap **26%** — arc-heavy corpora tempt narrative overfitting. |
| **`orchestration_progression`** | Turn structure, progression, issue-layer pressure | `hypothesis_subsystem` spread; **not** Director-as-default-root-cause stories | **14–22%** | Cap **26%**; pair with diverse subsystems in dimensions. |

**Slack rule:** If **primary** quotas cannot be met from eligible material, **document** shortfall on `#186` (or child) **before** relaxing caps **>3** units total **or** extending harvest window.

---

## Cross-cutting flags (non-exclusive)

Record on facilitator ledger; **also** append to ACP `scenario_tags` when used.

| Flag | Purpose | Quota / cap |
|------|---------|-------------|
| **`ambiguity_expected`** | Unit pre-selected to surface honest coder disagreement or dual plausible primaries | **18–28%** of N **must** carry this flag. **Not** a failure if disagreement occurs **outside** flagged units. |
| **`unknown_leaning`** | Thin evidence / early investigation — **likely** `unknown.insufficient_evidence` but not required | **12–20%** of N. **Do not** push raters to force UNKNOWN. |
| **`instrumentation_192`** | Instrumentation or audit-reliability stress — **#192 routing** boundary | **≤22%** of N **with** this flag (hard cap). **Does not** authorize narrative FTC from noise alone (**ACP §13** / FT1 §13). |
| **`famous_thread`** | Known high-recognition / emotionally salient thread | **≤4** units **total** in Round A; **≤2** from the **same** root Issue **unless** strata differ **and** rationale is logged. |

---

## Subsystem spread (facilitator ledger check)

- Across the **full** Round A corpus, **`dimensions.hypothesis_subsystem`** (after labeling) should show **≥4** distinct values **among** narrow primaries **and** justified `other` — **not** a quota per value, a **diversity floor** to avoid "all memory" collapse.
- Tracked **post hoc** after first blind pass if needed; **selection** should **aim** for candidate Issues that **plausibly** touch different workflow layers.

---

## Source distribution (balancing)

| Source type | Guidance |
|-------------|----------|
| **GitHub Issues / comments** | **Primary** anchor — **≥70%** of units must have a **stable** Issue or comment URL (**ACP §5** `sources[]`). |
| **Audit session pointers** | **≤30%** of units may be **primarily** indexed via session paths **if** a **public** Issue/comment anchor still exists **or** a **team-accessible** archival pointer is documented **on the tracking Issue**. |
| **Synthetic / reconstructed** | **≤10%** of N **only** to fill stratum gaps **after** good-faith historical harvest; log each on tracking Issue. |

---

## UNKNOWN allocation guidance

- **Target:** **10–18%** of blind submissions **may** end as `unknown.insufficient_evidence` — **observed** metric, **not** a quota to game.
- **Selection:** **`unknown_leaning`** flag covers **12–20%** of **selected** units (candidates where evidence is thin); raters **still** choose narrow FTC when responsible.
- **Forbidden:** selecting units **solely** to "pump UNKNOWN rate" **or** avoiding UNKNOWN to look decisive.

---

## Ambiguity allocation guidance

- **`ambiguity_expected`** on **18–28%** of units **before** blind pass.
- Facilitator **does not** reveal **which** ambiguity type is anticipated during blind labeling.
- **Collision records** (**ACP §9**) **required** when **primary** disagreement or UNKNOWN usage disagreement surfaces — especially on **`ambiguity_expected`** units.

---

## #192 instrumentation allocation

- **`instrumentation_192`:** **≤22%** of N (hard cap).
- **Purpose:** practice **routing** and **collision_kind** `routed_192_instrument_anomaly` **without** expanding FTC registry.
- **Exclusion:** pure infra flake **with** **no** Issue narrative anchor **→** **exclude** unless **explicit** workshop sub-exercise (log exception).

---

## Famous-incident anti-overfitting

- **Max 2** units per **root** Issue number **unless** **documented** exception (different `primary_stratum` + different stress thesis).
- **Max 4** units with **`famous_thread`** flag **for the whole** Round A.
- **Spread** salient historical threads across **strata**; **do not** let one saga dominate **audit_stressed** or **`ambiguity_expected`**.

---

## Facilitator operational instructions

1. **Pre-commit** target N and stratum table **empty row** on spreadsheet **before** deep Issue trawling.
2. For each candidate, assign **provisional** `primary_stratum` + flags **before** locking the **ACP exemplar package**.
3. **Fill** stratum **shortfalls** first by **broadening** search, **not** by **relaxing** famous-thread caps.
4. After **each** batch of **~10** packages, **reconcile** observed % vs bands; **stop** adding to overfull strata.
5. **Never** use strata to **prescribe** FTC — only **balance** inputs.
6. **Link** each package’s `scenario_tags` to this grid’s tags **for** reproducibility.

---

## Revision

| Version | Note |
|---------|------|
| **round-a-strata-v0.1** | Initial operational grid (pre-harvest). |

**Bump** minor version when quotas or tag vocabulary changes mid-Round A; **archive** superseded table on the **same** tracking Issue thread.

---

## Relationship summary

| Artifact | Role |
|----------|------|
| **FT1** | Semantic authority for FTCs, dimensions, UNKNOWN canon. |
| **ACP** | Interchange envelopes; `scenario_tags` **consumes** this grid’s vocabulary. |
| **This grid (v0)** | **Selection balance** and facilitator discipline **only**. |

**End Round A Strata Grid v0**
