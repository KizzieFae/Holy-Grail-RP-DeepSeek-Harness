# Round A Serialized Exemplar — Facilitator / Export Checklist v0

> **Status: HISTORICAL WORKSHOP** — Not current program-audit authority. See `governance/rp-app/audit-semantics.md`.

<!--
  Operational checklist only (#186 / #187 adjacency).
  Ephemeral v0: retire or merge after Round A / S2 gate.

  Related:
  - failure-taxonomy-spec-v1.md (FT1 — FTC semantics authority)
  - audit-classification-protocol.md (ACP — bundle interchange; pointer-first §8)
  - round-a-strata-grid-v0.md (balancing / scenario_tags v0)

  NON-goals here: runtime behavior, tooling, CI gates, detectors, FTC expansion,
  blind labeling execution, applicability truth (AUDIT_DOCUMENTATION remains authority).
-->

## Document posture

| Aspect | Position |
|--------|----------|
| **Purpose** | **Execution discipline** before first **frozen cohort**, serialized harvesting, facilitator review, and pilot blind-label prep. |
| **Authority** | **Operational / procedural ‖I‖** guidance (*not FT1 ‖N‖*). Does **not** define FTC meanings, adjudicate continuity (`FR4`), or replace applicability reads (`AUDIT_DOCUMENTATION.md`). |
| **Audience** | Facilitators, exporters/operators, reviewers/raters who touch **immutable pointers** → **ACP §5 packages**. |

---

## Canonical references (read before first cohort)

| Document | Role |
|----------|------|
| `governance/rp-app/failure-taxonomy-spec-v1.md` | **FT1** semantic authority (**‖N‖** there). Checklist ≠ taxonomy. |
| `governance/rp-app/audit-classification-protocol.md` | **ACP** §§5–8 (**packages**, pointers, UNKNOWN pairing). Bundles cite evidence; they do **not** absorb raw archives. |
| `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` | **Applicability and Signal inventory authority** (**read-order pressure** stays here — checklist does **not** replace it). |
| `governance/rp-app/round-a-strata-grid-v0.md` | **Strata quotas / flags / anti-overfitting** — selection guardrails (**not FTC law**). |
| `runtime_narrative_memory_prd1.md` (**FR4**) | Continuity truth **upstream** of workshop labels — excerpts are pointers only (**ACP §3** posture). |

---

## Facilitator pre-gates (before any freeze)

Copy this block to the **tracking Issue** (recommended) **or** project note when opening a cohort.

- [ ] **Cohort boundary named** — e.g. `round-a-serialized-cohort-YYYYMMDD`; roster is **closed** at freeze (**no silent adds** afterward).
- [ ] **Strata intent recorded** — each provisional `eu-…` mapped to **`primary_stratum`** + crossing flags (**`round-a-strata-grid-v0.md`** targets).
- [ ] **Anti-overfitting sanity** — mix **≠** “favorite clean demos”; **ambiguity_expected** band met per grid; **`famous_thread`** cap enforced.
- [ ] **No taxonomy-target picking** — do **not** select slices to rehearse predetermined FTC hypotheses (corrupts blind pressure).
- [ ] **Issue-only drift check** — every unit slated for serialized expansion has a **plan** for **narrow frozen pointers**, not Issues alone (**≥70%** still need stable Issue **`sources`** per strata grid §Source distribution).

---

## Selection & nominations

- [ ] **Nominations** include: session identifier (opaque ok), thematic **observational** stress (**not** FTC), and honest **subsystem** / layer guess (**‖I‖** only).
- [ ] **Facilitator rejects or defers** material that collapses strata diversity or violates caps (document **shortfall** vs **silent** cap violation).
- [ ] **`exemplar_unit_id` stable** — assign opaque `eu-…` early; **reuse** IDs across manifests and **ACP §5** packages **1:1**.
- [ ] **`instrumentation_192` flag sparse** — if used, **`instruments_flag`** / collision routing honors **ACP §13** (**no narrative FTC minted from noise**).

---

## Export & freeze sequence (operators / exporters)

- [ ] **Slice spec written** (**facilitator-approved**) — narrow paths / turn anchors / summary sections (**≤ ~3–5 pointer targets per unit**, not entire repo dumps).
- [ ] **Rolling pointers forbidden** — **no manifest or ACP `sources` citation** may target a **mutable** “latest session folder”, live sync path, or unpinned attachment that can change in place (**immutable blob/release/mirror revision only**).
- [ ] **Export executed** — copy **only** sanctioned subtree into staging (local or team-approved staging area); **nothing** implicitly becomes **runtime/deploy** truth.
- [ ] **`content_id` recorded** — cryptographic hash (**e.g.** SHA-256 over frozen bytes) **+** **immutable host key** (**release tag / object version / signed bundle id**) **before** any package references it.
- [ ] **Giant blobs discouraged** — if full session unavoidable, isolate to **privileged tier** (**see below**) and **still** cite **narrow** inner paths in manifest + **`evidence_references`**.

---

## Sanitization & tiering decisions

Pick **one tier per retained blob** (**document on roster**):

| Tier | Typical use |
|------|--------------|
| **sanitized_public** | Redacted excerpt pack safe for widest reviewer access |
| **privileged_mirror** | Full fidelity under ACL — raters needing it must receive access **before** claims of applicability closure |
| **hybrid** | Two immutable `content_id`s — public redacted **+** privileged full |

**Mandatory checks:**

- [ ] **Redaction summary** lists **categories** removed (never paste secret material into Issues to “prove” redaction).
- [ ] **`field_loss_flags`** (manifest) identify **predicate / applicability / Signal** readability risk when fields were stripped (**‖I‖** operational note — **not** FTC).
- [ ] **Sanitization loss is not FTC** — it is **availability / completeness** pressure for **`evidence_gap`** honesty later (**ACP §6 / §7**).
- [ ] **Access/tier failures are not automatic UNKNOWN** — if reviewers lack privileged tier despite workshop claiming completeness → **workflow / cohort failure** (**fix tier or bump version / deprecate pointer**).

---

## Manifest minimum (before ACP linkage)

One **row per `exemplar_unit_id`** (**Markdown table \| YAML snippet \| pinned comment** OK — **no validator assumed**):

- [ ] `cohort_id`
- [ ] `exemplar_unit_id`
- [ ] `content_id` (**hash + immutable label**)
- [ ] `slice_paths` (**relative paths within blob** **+ turn / section anchors if applicable**)
- [ ] `privacy_tier`
- [ ] `exemplar_package_version` (**starts at `1`** for greenfield unit linkage)
- [ ] **`redaction_summary`** and **`field_loss_flags`** when tier is **`sanitized_public`** or hybrid public leg

Anti-drift:

- [ ] **No row may reference unpublished / unfrozen blobs** (**hash must exist before merge to “frozen” state**).

---

## ACP package linkage (**§5** sanity)

Package **≠** canonical runtime record — interchange only (**ACP §0** posture).

- [ ] **`sources`** includes **≥1** stable **`github_issue`** (**or comment**) permalink where practical (**strata grid source rule**).
- [ ] **`sources`** / ancillary notes cite **immutable** **`content_id`** + **retrieval** pointer (**release \| mirror**) — **not** rolling paths.
- [ ] **`scenario_tags`** synced with strata grid selections (**material tag changes ⇒ bump `exemplar_package_version`**).
- [ ] **`exemplar_package_version` bumped** when anchors, **`content_id`**, **`slice_paths`**, strata tags, tier, **or sanitization** materially change.
- [ ] **`evidence_references`** (**ACP §8 / §6**) favor **typed short pointers** over pasting megabytes of JSON.
- [ ] **`interpretive_labels_only`** retained (**constraints** §5) — checklist does **not** authorize detector or CI mandates.

---

## Evidence-gap reminders (**operators / reviewers**)

- [ ] **`evidence_gap.attempted`** flags reflect actions **actually available** **at** reviewer’s tier (**privileged-only fields** don’t default to unchecked “false” lore).
- [ ] UNKNOWN primary (`unknown.insufficient_evidence`) still requires **`evidence_grade: unknown`** (FT1 **`/`** ACP pairing) plus a non‑vacuous **`evidence_gap`** narrative (**§6 **`/` **§7**).

---

## Review gate (**facilitator sign-off**) 

- [ ] **Manifest ↔ §5 coherence** (**every `eu-…` resolves** — no orphan blobs / orphan packages).
- [ ] **`field_loss_flags` reviewed against planned blind cohort** (**public-only raters × thin applicability** ⇒ **repair tier or narrow claims**).
- [ ] **`FR4` boundary restated**: labels **hypothesize** from frozen slices — **do not treat export JSON as continuity adjudication.**

---

## Explicit discouragements (non-exhaustive)

| Do **not** | Why |
|-----------|-----|
| **Rolling “latest audits” semantics** | **Drift destroys reproducibility / invites implicit canon.** |
| **Repo-wide archival dumps without cohort caps** | **Archival creep + privacy trap + review paralysis.** |
| **Issue-only exemplar creep** after serialized phase kicked off | **Documentation-gaming / applicability shortcut risk.** |
| **Pre-labeling FTC targets** **to “match” strata** | **Overfitting / defeats blind pressure.** |
| **Coupling manifests to deployment paths / live APIs** | **Hidden runtime coupling — evaluation inputs stay frozen artifacts.** |

---

## Versioning supersession (**operational shorthand**)

- **Wrong blob referenced?** Mint **new** **`content_id`**, bump **`exemplar_package_version`**, mark **old row** `deprecated` with `supersedes` pointer — **never** overwrite blobs in cohort memory.
- **Slice re-scoped materially?** **New `eu-…`** **preferred** vs silent edit (**clearer empirical audit trail**).

---

## Checklist lifecycle

| Moment | Action |
|--------|--------|
| **Opening cohort** | Paste **Facilitator pre-gates + cohort name + roster** onto tracking Issue (**#186** lineage or delegated child). |
| **Freeze day** | Check off **Export & freeze**, **manifest minimum**, **tiering**, **immutable IDs**. |
| **Pre harvesting / pilot** | Completed **ACP linkage + review gate** checklist blocks. |

---

**End v0 checklist**
