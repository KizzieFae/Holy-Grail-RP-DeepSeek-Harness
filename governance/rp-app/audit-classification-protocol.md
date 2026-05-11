# Audit Classification Protocol (ACP)

<!--
  Skeleton: interchange and process envelope only (#187 lineage).
  Not runtime, detectors, CI gates, or audit/continuity authority.
  FTC semantics authoritative in governance/rp-app/failure-taxonomy-spec-v1.md (FT1 / #186).
-->

## §0 Document control ‖N‖

| Field | Value |
|-------|-------|
| **Protocol ID** | **ACP** (audit classification protocol) |
| **Lineage** | GitHub `#187` |
| **Canonical path** | `governance/rp-app/audit-classification-protocol.md` |
| **Document state** | **SKELETON** — operational interchange structure only |
| **Authority posture** | **Human‑governed process completeness for classification *bundles*.** Does **not** adjudicate continuity truth (`FR4`), audit applicability predicates (`AUDIT_DOCUMENTATION` / `#59` lane), `outcome_record` meaning, `detector` judgments, **or** runtime outcomes. |

**Current revision:** **ACP-doc-0.2-governance-freeze-v0-crossref**

**Separation markers**

| Tag | Meaning |
|-----|---------|
| **‖N‖** | Normative for Issues or workshop artifacts that claim **ACP‑conforming** interchange. |
| **‖I‖** | Guidance, facilitation, rationale — **not** a substitute for FT1 **‖N‖** or audit inventory semantics. |

---

## §1 Purpose and non‑goals ‖N‖

**Purpose**

Provide a minimal, paste‑friendly **interchange** so exemplar workshops (`#186`) and Issue discussions can serialize **FT1 labels**, **evidence pointers**, **and** collision records **without** defining tooling semantics, enforcing CI, **or** replacing upstream audit/read truth.

**Non‑goals**

- Runtime validation, Director gates, automated rejection of bundles.
- Detector contracts (`#66` lineage) **or** interpretation of detector output as authority.
- Continuity authoritative state (`FR4`) — excerpts **as pointers only**.
- Replacement for applicability / predicate reading in `AUDIT_DOCUMENTATION.md`; **reading order unchanged** (*Signal id* → applicability → predicate, before heuristic/severity shorthand).
- Normative YAML lint **in pipelines** (**no CI mandate here**).
- `#192` does **not** own FTC meanings; orchestrates **routing** for instrumentation/reliability stress (**§13**).

---

## §2 Protocol scope ‖N‖

**In scope ‖N‖**

- Exemplar **package** (immutable corpus unit **+** anchored sources).
- **FT1 label bundle** operational shape (**§6**).
- **Collision/adjudication record** (**§9**).
- Protocol **versioning** and **pointer** to FT1 revision.
- Process **completeness** expectations (**§10**).
- Evidence **reference** posture (**§8**).
- `#192` **routing boundaries** (**§13**).

**Out of scope**

- FTC registry expansion or new slug definitions (**FT1 §12 / §13** only).
- Workshop corpus loading/curation playbook (**‖I‖** only in §11).
- Implementation of validators/lints (**explicitly deferred** unless a future governance Issue adopts tooling).

---

## §3 Authority boundaries ‖N‖

| Authority | ACP relationship |
|-----------|-------------------|
| **FT1** (`failure-taxonomy-spec-v1.md`) | **Semantic authority** for `ftc_primary`, reserved `unknown` family, UNKNOWN pairing (`unknown.insufficient_evidence` ⇔ `evidence_grade: unknown`), interpretive guardrails. **ACP does not redefine these.** |
| **`AUDIT_DOCUMENTATION.md`** | **Semantic authority** for signals, applicability, inventory. **ACP records pointers and dispute summaries — never substitutes predicate truth.** |
| **`issue-tracking-workflow.md`** (§§D, E, F, I) | Issue Type/Layer/evidence discipline **stay authoritative.** ACP **cites**; does **not** assign bug/quality/defect verdicts **from FTC alone.** |
| **`FR4`** (`runtime_narrative_memory_prd1.md`) | Continuity truth **upstream**. Bundles **may reference** excerpts; **must not assert replacement continuity.** |
| **#192** | Instrumentation / audit‑reliability bridge. **ACP tags and routes only**; substantive design stays on `#192`. |

---

## §4 Relationship to FT1 ‖N‖

1. Every ACP‑conforming bundle that asserts FTC semantics **shall align** with the current **`failure-taxonomy-spec-v1.md`** (carry **`ft1_doc_pointer`** **and** **`ft1_doc_revision_hint`** in the bundle skeleton **§6**).
2. **Canonical operational field list** for workshop/Issue interchange **lives in this protocol**; **FT1 Annex B stays a thin pointer**, not a competing schema source.
3. **Non‑UNKNOWN** registry publication **remains gated** by FT1 exemplar lifecycle (**§13** there); **ACP does not add registry rows.**

---

## §5 Exemplar package structure ‖N‖

**‖N‖ Definition:** immutable **input** unit for **one labeled slice** per workshop selection.

```yaml
# acp-exemplar-package — normative keys (skeleton)
protocol_id: acp
protocol_doc_revision: acp-doc-0.2-governance-freeze-v0-crossref

exemplar_unit_id: eu-XXXX                 # REQUIRED — stable opaque id
sources:                                  # REQUIRED — ≥1 anchor
  - kind: github_issue
    url: "https://github.com/org/repo/issues/NNN#issuecomment-..."  # Issue or comment URL

exemplar_package_version: 1               # REQUIRED int; bump on source/unit change

scenario_tags: []   # Round A v0 tags: governance/rp-app/round-a-strata-grid-v0.md
instruments_flag: "none|TBD|routed_to_192"    # OPTIONAL — see §13

constraints:
  interpretive_labels_only: true          # FIXED for ACP

notes_facilitator: ""                     # OPTIONAL ‖I‖
```

---

## §6 FT1 label bundle structure ‖N‖

**‖N‖ Definition:** one operator/rater **submission** for an exemplar unit (blind pass **or** merged adjudication outcome).

```yaml
# acp-ft1-label-bundle — normative keys (skeleton)
protocol_id: acp
protocol_doc_revision: acp-doc-0.2-governance-freeze-v0-crossref

ft1_doc_pointer: governance/rp-app/failure-taxonomy-spec-v1.md
ft1_doc_revision_hint: FT1-doc-0.4-governance-freeze-v0  # UPDATE when FT1 changelog bumps

failure_taxonomy_ft1:
  ftc_primary: "<family.subtype>"         # REQUIRED — FT1 §3 / §11
  dimensions:
    hypothesis_subsystem: "<enum|TBD>"
    evidence_grade: "<enum|TBD>"
    temporal_scope: "<enum|TBD>"
  secondary_symptoms: []                  # OPTIONAL — ≤2 symptom-only adjuncts (FT1 §5)

  evidence_gap:                         # REQUIRED if ftc_primary == unknown.insufficient_evidence
    attempted:
      continuity_excerpts: false
      audit_signal_resolution: false
      issue_workflow_section_d_digest: false
      issue_workflow_section_f_digest: false
      in_scope_logs: false
      other_attempts: []
    blocker_summary: ""                   # REQUIRED for UNKNOWN primary; else if gaps declared

  evidence_references:                  # RECOMMENDED; extend kinds via TODO‑ACP‑02 ‖I‖
    - kind: continuity_excerpt_ref
      ref: ""
    - kind: audit_signal_id
      signal_id: ""

  notes_operator:
    primary_rationale: ""                  # REQUIRED in workshop exports
    ambiguity_notes: ""

workshop_meta:                            # OPTIONAL on Issues — REQUIRED on blind exports
  rater_id: ""
  pass: "blind_A|blind_B|adjudicated_merge"
```

**Forbidden combinations ‖N‖** (process completeness mirrors FT1 §4 / §11)

- `ftc_primary: unknown.insufficient_evidence` with `dimensions.evidence_grade` **≠** `unknown`.
- Narrow `family.subtype` **with** `evidence_grade: unknown` **instead of** canonical UNKNOWN **when FT1 would forbid that pairing** (**insufficient evidence for any narrow primary**).
- More than **two** secondary symptoms **or** secondary tags **presented without explicit symptom‑only semantics** (**syntax finalized post‑Round A — TODO**).
- UNKNOWN primary **with absent or vacuous `evidence_gap`** (must show **attempted** lookups **or** honest **`blocker_summary`** consistent with UNKNOWN).

---

## §7 UNKNOWN operational handling ‖N‖

Canonical insufficient‑evidence **primary FTC** (semantic authority: **FT1 §11 / §9**):

```text
unknown.insufficient_evidence
```

- **Pairing ‖N‖:** `dimensions.evidence_grade` **must** be `unknown` when this slug is primary.
- **`evidence_gap.attempted`:** operators declare **which lookups were tried** — **honesty about evidence**, **not** a substitute for applicability resolution (**§8** **/** collision record).
- Any change to UNKNOWN meaning or slug routes through **FT1** governance (`#186` lineage), **not** this protocol.

---

## §8 Evidence‑reference guidance

**‖N‖**

- Prefer **typed pointers** (permalink + optional `audit_signal_id` + short anchor IDs) **over** pasting massive logs verbatim.
- If applicability/heuristic interpretation is disputed, cite **which Signal id** and summarize **hypothesis readings** **`as hypotheses`** — escalate substance **via** **`§9`** **audit_dispute appendix** (inventory remains authoritative).
- **Do not assert applicability truth** inside the label bundle beyond **citations + hypothetical readings**.

**‖I‖**: Optional links into `AUDIT_DOCUMENTATION.md` playbook sections (**TBD**).

---

## §9 Collision and adjudication record ‖N‖

```yaml
# acp-collision-record — normative keys (skeleton)
protocol_id: acp
protocol_doc_revision: acp-doc-0.2-governance-freeze-v0-crossref

exemplar_unit_id: eu-XXXX

collision_kind: |-
  primary_disagreement |
  dimension_disagreement |
  unknown_usage_disagreement |
  audit_applicability_dispute |
  routed_192_instrument_anomaly

per_rater_digests: []           # OPTIONAL — embed hashes or payloads (TODO‑ACP‑03)
discussion_summary: ""

resolution:
  status: unresolved | consensus_label | defer_ft1_patch | defer_acp_revision | routed_192
  merged_ft1_label_bundle: {}   # OPTIONAL YAML subset agreeing with §6

audit_dispute:                  # OPTIONAL — does NOT redefine predicates
  signal_ids_in_dispute: []
  claimed_reading_order_ok: bool
  cites_audit_inventory: ""

routed_192:                     # OPTIONAL — escalation narrative for #192
  synopsis: ""
  forbids_narrative_ftc_without_evidence: true

notes: ""
```

---

## §10 Process completeness expectations ‖N‖

**Minimum for workshop conformance**

1. One **§5** exemplar package per labeled unit **before blind labeling**.
2. At least **one §6** bundle per rater/pass **before** aggregated claims.
3. Open a **§9** collision record whenever **silent disagreement** **would hide** taxonomy or audit-reading stress.

**Issue‑attachment posture ‖I‖**: fenced YAML (or maintainer‑agreed subset) — **paste surface decision** TODO‑ACP‑04 on `#187`.

**Governance Freeze v0 coupling (`#186`).** While Issue **`#186` / Freeze v0** is operative, **`FT1`** revision **`FT1-doc-0.4-governance-freeze-v0`** **`§13.1`** is the authoritative maturity lattice (G0–G3), **S4 Branch B** transitional cap (**≤ 3** **`validated`** non‑UNKNOWN **`ftc_id`** rows pending **`TODO‑METRIC‑04`** closure), and hard registry boundary (**exactly one** normative **`§9`** row: **`unknown.insufficient_evidence`**). This **`ACP`** revision (**`ACP-doc-0.2-governance-freeze-v0-crossref`**) **only** cross‑references that posture—**no** new interchange keys, **no** detector semantics, **no** **`#59`** edits, **no** **`#200`** activation—instrumentation posture remains **`§13`** / **`#192`** routing rules unchanged.

---

## §11 Workshop operational guidance ‖I‖

- Independent bundles **before** peer reveal (Round A/B pattern from `#186` planning).
- Prefer **documented split votes + collision records** **over forced consensus** when evidence is thin.
- Route instrumentation‑dominant confusion **toward `#192` narrative** tags **rather than** speculative new FTC splits.

---

## §12 Versioning, governance, change control ‖N‖

| Rule | Requirement |
|------|-------------|
| **Edits** | PR + linking Issue (`#187` **or delegated child**). |
| **Revision bump** | Update **ACP‑doc‑x.y** in §0 **and** changelog table below for substantive **‖N‖** changes. |
| **Coupling FT1** | When FT1 UNKNOWN/pairing text changes, PR updating ACP **`ft1_doc_revision_hint`** **and examples**. |
| **Tooling / CI** | **Out of scope** unless separately adopted by governance Issue.

**CHANGELOG**

| Revision | Note |
|----------|------|
| ACP-doc-0.1-skeleton | Initial interchange skeleton (**no tooling mandate**). |
| ACP-doc-0.2-governance-freeze-v0-crossref | **Governance Freeze v0**: freeze coupling paragraph (**§10**), **`protocol_doc_revision` / `ft1_doc_revision_hint`** example sync (**§§5–6, §9**) to **`FT1-doc-0.4-governance-freeze-v0`**—**no schema growth**. |

---

## §13 Relationship to #192

**‖N‖ Routing**

- If `instruments_flag` **or workshop context** shows instrumentation/reliability contamination **beyond** ordinary heuristic audit reading → set `instruments_flag: routed_to_192` **or** use `collision_kind: routed_192_instrument_anomaly` **without** asserting audit predicate verdicts here.
- **Do not mint narrative FTC solely from instrumentation noise** when bridge evidence absent (**align with FT1 §13 anti‑pattern + program notes on `#184` / `#192`**).

**‖I‖**: Align field vocabulary with `#192` maintainers; ACP stays **transport layer.**

---

## §14 Informative bibliography ‖I‖

- `governance/rp-app/failure-taxonomy-spec-v1.md` — FT1 semantics (**#186**).
- `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` — signal inventory/applicability.
- `governance/rp-app/issue-tracking-workflow.md` — §§D/F discipline.
- `governance/rp-app/round-a-strata-grid-v0.md` — Round A facilitator strata / `scenario_tags` v0 (**process only**).
- `runtime_narrative_memory_prd1.md` — `FR4` context only.

---

## §15 Deferred TODOs

| ID | Content |
|----|---------|
| **TODO‑ACP‑01** | Extend or merge `scenario_tags` post–Round A; **Round A v0** grid: `governance/rp-app/round-a-strata-grid-v0.md`. |
| **TODO‑ACP‑02** | Safe extension of `evidence_references` kinds **without duplicating AUDIT_DOCUMENTATION.** |
| **TODO‑ACP‑03** | `per_rater_digests`: hash-vs-embed convention. |
| **TODO‑ACP‑04** | Canonical Issue paste surface (**comment template vs appendix vs gist**). |
| **TODO‑ACP‑05** | One‑page cheat sheet (**‖I‖**) aligned with FT1 Annex A outline. |

---

**End ACP skeleton**
