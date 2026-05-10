# Failure Taxonomy Spec v1 (FT1)

<!--
  FT1 governance spec: structure + selectively normative early rows.
  Consensus UNKNOWN canonical FTC is normative (**unknown.insufficient_evidence** — §11, §9).
  Remaining registry rows intentionally unfinalized until exemplar pressure-testing (#186).

  Related tracking: #186 FT1; #187 ACP interchange (audit-classification-protocol.md); #175 (Phase -1); #184 (program orchestration).
-->

## Document control (normative §0)

| Field | Value |
|-------|--------|
| **Spec ID** | FT1 |
| **Spec state** | **PARTIAL‑REGISTRY** — **UNKNOWN **`canon`** **only (**§`**`9`** **/**`**`§`**`**`11`** **)**; **`other`** FTC rows gated **until exemplar stabilization (**§**`**`13`** **)** (**not **`a`** finalized full codebook **`release`** **) **. |
| **Canonical path** | `governance/rp-app/failure-taxonomy-spec-v1.md` |
| **Authority posture** | **Interpretive / observational labeling only.** This document does **not** define continuity truth, runtime enforcement, causal certainty, orchestration policy, or detector judgments. **`FR4` continuity remains authoritative per `runtime_narrative_memory_prd1.md` (reference only)** — see §6. |

**Explicit non‑authority**

- Does **not** amend, replace, or restate **`#59`** audit signal applicability semantics, **`#67`** engineering family semantics, registry inventory rows in **`AUDIT_DOCUMENTATION.md`**, **`detector`** contracts (**Issue `#66`** family), **`outcome_record`** rules, advisory causal labels (**Issue **`#`**`29`** lane), or **`issue-tracking-workflow`** **`§`**`D`/****§`**`E`/****§`**`F`/`§`**`I` .
- **`PRD1` / **`PRD2` / roadmap** — intent / sequencing reference **only**. Product or runtime contradiction resolution remains **Issues + authoritative architecture**.

**Separation markers used in this file**

| Tag | Meaning |
|-----|---------|
| **‖N‖** | Normative (must-follow when adopting FT1 labeling on Issues or evaluation records explicitly governed by **`#`**`187` **or superseding protocol). |
| **‖I‖** | Informative (rationale / examples — not a substitute for normative bullets). |

**Document revision**

- **Current revision:** **`FT`**`1` **‑doc‑`0.3`**`‑annexb-acp-ref`** (**CHANGELOG — §12**).
- Bump **`FT`**`1` **‑doc‑`x`**`.**`**`y`** on further registry / exemplar substantive edits (**§**`**`12`** **)** **.**

---

## §1 Purpose and non‑goals ‖N‖

**Purpose**

Provide a minimum **writable contract** so operators can attach **consistent, comparable interpretive Failure Taxonomy Codes (FTCs)** (**`family.subtype`**) **plus mandatory dimensions** when triaging narrative / memory / audit observations on **GitHub Issues** (and related evaluation records), without collapsing **symptom vs hypothesized subsystem** or **interpretation vs continuity truth**.

**Non‑goals**

- **Not** runtime gates, Director policy, allowlist expansion, or enforcement logic.
- **Not** continuity authority or replacement for committed narrative state.
- **Not** **`detector`** outputs, **`#`**`59` applicability classes, or **`outcome_record`** reclassification.
- **Not** causal truth — FTCs are **hypothesis / triage orientation**, not proof of defect class.
- **Not** normative **memory‑tier** architecture (deferred beyond optional non‑normative notes).
- **Not** a duplicate of audit signal inventory tables — **crosswalk only** (**§8**).

---

## §2 Definitions and glossary ‖N‖

| Term | Definition |
|------|------------|
| **FTC** | **Failure Taxonomy Code** — primary interpretive label, syntactically **`family.subtype`** (two dot‑separated segments in v1), **ASCII**, **no deep hierarchy**, **no embedded causal ontology** in the string. |
| **Family** | Coarse **observational cluster** (first segment). |
| **Subtype** | Narrower **presentation / triage fork** (second segment) — **not** a root‑cause claim. |
| **Dimensions** | Structured sidecar fields **required** whenever an FTC is asserted (**§**`4` **enumeration** pending exemplar narrowing). |
| **Primary FTC** | Exactly **one** per labeled unit (Issue triage passage or evaluation excerpt). |
| **Secondary symptom tag** | **Optional**, **explicitly labeled symptom-only** ( **`≤`**`2` **)— must not silently stand in for primary. |
| **Hypothesis subsystem** | **Default `§`**`F` **`Layer` triage focal point** (**not** deterministic truth attribution). |
| **UNKNOWN family** | Reserved first segment **`unknown`** (**§**`3`). Canonical insufficient‑evidence **primary FTC:** **`unknown.insufficient_evidence`** (**§**`11`). |
| **`FR`**`4` **boundary** | **Continuity authoritative** semantics remain **canonical** for truth; taxonomy **references** **`PRD1`** (informative pointer only — **`runtime_narrative_memory_prd1.md`**, References). |

**TBD (exemplar / consensus):** tighten operator-facing one‑line synonyms; avoid collision with **`Layer`** **`other`** provisional use on umbrellas.

---

## §3 FTC identifier model ‖N‖

**Syntax (v1)**

- Pattern: **`^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`**
- **Exactly one** dot (**`family.subtype`**).
- **`family`** **`and`** **`subtype`** **:** lowercase **`snake_case`** components; **`registry`** (**§**`9`) holds **`normative FTC rows`; **non‑UNKNOWN** FTC rows **`stay`** gated **until** exemplar stabilization (**§**`13`) **except **early‑canonical escapes documented **`here`** (**currently **`unknown.insufficient_evidence`** **only** **).**

**Reserved UNKNOWN family ‖N‖**

- **`unknown`** (**first segment**) is **reserved** for **`§`**`11` **UNKNOWN escape FTCs**.
- **`unknown.insufficient_evidence`** is the **canonical** insufficient-evidence FTC (**§`**`11` **)** ; additional **`unknown.*`** **`subtypes`** remain **explicitly gated** (**change **`control`** §**`**`12` **)** (**no ad‑hoc **`unknown.foo`** **`without`** **`tracking`** **`Issue`).

**Prohibitions**

- **No **`a.b.c` **traces** (**no tertiary path segments**) in v1.
- **No** embedding temporal / certainty / causal tokens in slug **unless promoted by explicit gated spec revision** (**change control §**`12` **)**.
- **No** reuse of **`#`**`59` applicability enum strings **`as FTC slugs`** (**crosswalk **`§`**`8` **instead**).

---

## §4 Mandatory dimensions (schema) ‖N‖

**Rule:** Applying an FTC **without** completing **required** dimensions is **outside FT1 conformance** (**process completeness** on Issues — **does not imply runtime validation**).

**Dimension record (conceptual)**

```yaml
# Illustrative YAML shape — enum values mostly post-exemplar; UNKNOWN primary is canon (§11).
ftc_primary: "<family>.<subtype>"        # e.g. unknown.insufficient_evidence — §3, §11
dimensions:
  hypothesis_subsystem: <enum>       # REQUIRED — maps triage posture to §F home (not truth)
  evidence_grade: <enum>               # REQUIRED — corroboration posture
  temporal_scope: <enum>               # REQUIRED — temporal shape of observations
secondary_symptoms: []                 # OPTIONAL — ≤2 symptom-only adjunct tags (syntax TBD)
```

**Enums (stub — finalize values via exemplars / #187)**

| Dimension | Stub allowed values _(non-final)_ | Purpose |
|-----------|-------------------------------------|---------|
| **`hypothesis_subsystem`** | `continuity_state` **`|`** `memory` **`|`** `grounding` **`|`** `perception` **`|`** `rendering` **`|`** `response_validation` **`|`** `orchestration` **`|`** `progression` **`|`** `audit_simulation` **`|`** `application_infrastructure` **`|`** other | Mirrors primary **`§`**`F` **`Lens` **`hypothesis`; **``other`** only with narrative justification (**issue-tracking-workflow **`§`**`F` **`other`** rules). |
| **`evidence_grade`** | **`deterministic_strong`** **`|`** **`scenario_corroborated`** **`|`** **`heuristic_supported`** **`|`** **`unknown`** **`|`** _TBD refine_ | Corroboration posture for **narrow** primaries (**not** interchangeable with **`unknown.insufficient_evidence`** as primary FTC — **`§`**`11`). |
| **`temporal_scope`** | **`single_turn`** **`|`** episodic **`|`** **`session_wide_or_instrumentation` **`**|** `unknown`** | Captures temporal span of observable pattern. |

**‖N‖ **`evidence_grade`** vs UNKNOWN primary (**consensus canon**)**

1. **`ftc_primary`** **`=`** **`unknown.insufficient_evidence`** **⇒** **`dimensions.evidence_grade`** **`=`** **`unknown`** (**required pairing** ).
2. **Do not** assert a narrower **`family`** with **`evidence_grade`** **`=`** **`unknown`** instead of **`unknown.insufficient_evidence`** when evidence **cannot** responsibly support **that** narrower primary.

**TBD (**`#`**`187` **alignment):**

- Canonical **`YAML`** **vs** **markdown fenced block adoption on Issues**.
- Handling **`dimensions.contradicts_ftc_slug`** inconsistencies (**§**`10` **).

---

## §5 Interpretation discipline ‖N‖

1. **Single primary FTC** per labeled analytic unit (**Issue chunk / evaluation excerpt scope** **`TBD`** **by **`#`**`187`).
2. **Secondary symptoms** (**`≤`**`2`**) **must** **`be`** flagged **`explicitly`** **as **`symptom_only`** (**no implied causality`).
3. **FR4:** Do **not** claim continuity incorrect **solely from an FTC label** — **continuity excerpts + **`§`**`D`** **`evidence` required for **`runtime`**`** truth claims** (**upstream workflow** **`§`**`E`/****§`**`D` **remain authoritative for **`Type`** / **`Layer`**`).
4. **Signal reading order:** Operators **remain bound** **`by`** **`AUDIT_DOCUMENTATION`** **interpretation discipline** (**Signal **`id`** → applicability → predicate)** **before **`severity`/****`**`TP`**`**`**`/****`**`FP`** ` language` **|** **FTC **`never`** substitutes that order (**§`**`8` **)**.
5. **UNKNOWN** (**§`**`11` **) **preferred** **`over fabricated precision`**.

---

## §6 Runtime truth separation ‖N‖

| Artifact / authority | FTC **may** | FTC **must not** |
|----------------------|-------------|------------------|
| **Continuity authoritative state (`FR4`)** | Hypothesize **observed inconsistencies** contingent on evidence bundle | Declare replacement truth narrative |
| **Validation / progression guardrails (`guardrail` family)** | Note co‑occurrence of outcomes | Replace enforcement interpretation |
| **Audit `Signal id` rows (inventory)** | Orient triage hypotheses after class resolution | Invent applicability / silence semantics |
| **`outcome_record` rows** | Cite as factual log | Reclass as applicability signal |
| **Advisory heuristic / AI causal label** | Correlate loosely (informative Annex cue ↔ §8) | Become identical FTC |
| **`detector` structured judgments (offline)** | Cite if present | Redefine schema / verdict |

**‖I‖ Guidance:** Retrieval / memory hypotheses **stay non‑authority** **`vs`** **`continuity`** (**`PRD1`** layering — informative pointer in References).

---

## §7 **`§`**`F` **`Layer`** mapping strategy ‖N‖

- Each **registry **`row (**when populated`** **)** provides **`default_hypothesis_subsystem`** **alignment** (**not exclusive** **`Layer`** **`ownership`**).
- Tie‑break unresolved multi‑layer ambiguity **via** **`issue-tracking-workflow`** **`§`**`F` **`order` **`**—** FTC **documents default**, **workflow wins conflicts**.
- **Taxonomy **`does not`** select **`Issue`**`** **`**`Type`**` **`(`**`**`bug`/`quality`/`design_gap`**` **)** — **`§`**`**`E`**` **authority **`unchanged`**.

**Registry **`column (**future):** **`default_hypothesis_subsystem`**, **`layer_notes`**, **`forbidden_substitution_warnings`**.

---

## §8 Crosswalk (mandatory, non‑substitutive) ‖N‖

**Normative stance:** FTC labels **coordinate with** **`AUDIT_DOCUMENTATION`** **axes** **`but never replace`** **them** **.**

**Placeholder subsections (**`populate concise tables post‑exemplar` **)**

1. **`#`**`59` applicability (**always‑on **`/`**`**`conditional`**` **`/`** heuristic / advisory) — reading order reminder + **explicit non‑identity** **`with`** FTC.
2. **`#`**`67` **`engineering`**` family (**telemetry`**` **`/`** guardrail`**` **`/`** heuristic proxy **`/` aggregation) — illustrative confusion matrix (**‖I`** until data).
3. **`outcome_record` mirror rows — factual logging only; applicability blank by design (**cite registry mirror_of).
4. **`detector`** (Issue `#`**`66` **lane) — **non‑overlap** **`statement`**.
5. **Advisory causal labels (**Issue`**` **`#`**`**`29` **suite) — directional hints only (**many‑to‑many placeholder).
6. **Optional **`Tier`**` **`1`** **kernel`**` **`surface_id`** **hints** — **informative linkage table** (**no exclusivity)**.

**TBD:** short crosswalk matrices after workshop pass #1 (**≤**`**`1`**` page`**` each axis max`).

---

## §9 FTC registry (structure placeholder) ‖N‖

**Status:** **`PARTIAL‑REGISTRY`** — exactly **one early‑canonical FTC** (**`unknown.insufficient_evidence`**) **is normative** (UNKNOWN consensus **`#`**`186` **lineage**); **all other** FTC **`IDs`** stay **non‑normative** until **`§`**`**`13`** **exemplar gate** **and** an explicit registry stabilization note on **`#`**`**`186`** (or successor)**.**

**Population gate (non‑UNKNOWN rows):** Additional registry rows become normative **only** after **`§`**`**`13`** exemplar thresholds **`and`** **that** explicit stabilization **`note`**.

**Future row schema (**`columns` **)**

| Column | Description |
|--------|--------------|
| **ftc_id** | Canonical **`family.subtype`** |
| **definition** | ≤ **TBD‑word normative prose |
| **default_hypothesis_subsystem** | Default **`dimensions.hypothesis_subsystem`** (**override allowed with justification**) |
| **evidence_minimum** | Qualitative deterministic / scenario evidence guideline |
| **forbidden_substitutions** | Bulleted warnings vs audit axes |
| **crosswalk_notes** | Short anchors into §8 rows |
| **exemplar_status** | **`unset`** **``**`|`**`**`candidate`**`|` **`validated`** |
| **`deprecated`** | Boolean + successor pointer (**future**) |

**Registry table (**`early canon + shell` **)**

| ftc_id | definition | default_hypothesis_subsystem | evidence_minimum | forbidden_substitutions | crosswalk_notes | exemplar_status | deprecated |
|--------|-----------|-------------------------------|------------------|-------------------------|-----------------|---------------|-----------|
| **`unknown.insufficient_evidence`** | Insufficient‑evidence **interpretive** primary FTC: assert only when analysts **cannot** responsibly choose **any narrower** **`family.subtype`**. **Does not** establish continuity falsity (**`FR4`**, §6), audit applicability, or defect proof (§**`1`**). **`evidence_gap`** narrative required (§11). | **`other`** | **`evidence_gap`** satisfies §11 **;** enumeration **`checklist`** **`=` **`TBD`** (**`**`#`**`**`187`** **)** **. | Must not bypass **`AUDIT_DOCUMENTATION`** reading order or **`#`**`59` applicability (**§5**, **§8**). | §8 UNKNOWN row **TBD**. | **`validated`** | **`no`** |
| _Additional rows — populate post non‑UNKNOWN gate (§13)._ | | | | | | **unset** | no |

_Target row count_: **≤** **`~`**`25`**` primary FTC **`IDs`** (**program ceiling **—** refinement on **`#`**`184` **`/`**`**`#`**`**`175`**` **Issues as needed`** **).**

---

## §10 Adjudication and collisions ‖N‖

**Levels**

1. **Syntactic** — invalid slug (**§`**`3` **|** **dimension omission** (**§`**`4` **) **⇒ **`non‑conforming` **record** (**fix before filing claims** ).
2. **Semantic cross‑coding** — two plausible **narrow** primaries **⇒** **`require`** adjudication commentary **or**, when evidence **`cannot`** pick **`one`** narrow primary **`without`** speculation, assert **`unknown.insufficient_evidence`** (**§11**)**.** (**TBD** auxiliary **`FTC_ambiguity`** dimension **`/`** **`flag`** when evidence **`is`** adequate **`yet`** disagreement **`survives`** discussion**.)**
3. **Dimension vs slug mismatch** (**e.g. **``**`retrieval_*`**`** **family + **`subsystem=continuity_state` **without rationale) ⇒ **`blocked`** until reconciled (**Protocol **`#`**`187` **`may`** automate lint later — **non‑runtime** **`only`** **).

**TBD**

- Inter‑rater agreement metric (**Cohen **`κ` / % agreement) thresholds & minimum **`N`**.

---

## §11 UNKNOWN / insufficient evidence ‖N‖

**Reserved family:** **`unknown`** (**§3**).

**Canonical insufficient‑evidence primary FTC:**

```text
unknown.insufficient_evidence
```

**When to assert (**paired **`dimensions` — **`§`**`**`4`):**

Assert **`unknown.insufficient_evidence`** as **`ftc_primary`** **if and only if:**

- Analysts **cannot** pick **any** narrower **`family.subtype`** **without fabricated precision** (**explicit UNKNOWN beats sham narrow guesses** — **`§`**`**`5`).
- **All mandatory dimensions (**§**`**`4`** **)** **are** complete **`—`** **`if`** **`this`** FTC **`is`** primary, **`dimensions.evidence_grade`** **must **`be`** **`unknown`**.

**Mandatory **`evidence_gap`:** narrative listing **`attempted`** lookups (**e.g.** continuity excerpts consulted, audit **`Signal id`** → applicability path, Issue **`§`**`**`D`/`§`**`**`F`** **material**, **`in-scope`** logs**)** **; enumeration checklist **`TBD`** (**`#`**`**`187`** **)** **`**.

**Forbidden:**

- Narrow **`family.subtype`** **`with`** **`dimensions.evidence_grade`** **`=`** **`unknown`** **`instead`** **`of`** **`unknown.insufficient_evidence`** **`when`** **the bullets **`above`** **`would`** **`force`** **`UNKNOWN`** (**§**`**`4`).
- **`Do`** **`not`** use **`this`** FTC **`alone`** **`as`** **`proof`** **`of`** **`continuity`** **`errors`**, **`#`**`**`59`** applicability facts**,** **`AUDIT_DOCUMENTATION`** reading-order facts**,** deterministic defects**,** causal subsystem claims**,** **`or`** **`similar`** **(**§§**`**`1`**`**,`** **`**`6`**`,`** **`§`**`**`8`).

**Workshop signal:** **`if`** UNKNOWN **`rates`** **`are`** **`high`**, widen exemplar strata**,** refine **`adjacent`** definitions**,** **`or`** **`document`** tracked exceptions (**no **`automatic`** registry expansion**)** **`**.

---

## §12 Governance, versioning, migration ‖N‖

**Change control**

- Edits **`require`** **`PR`** + **`traceability`**`** ` link **`to`** **`tracking`**`** ` **`Issue`** (**#186 lineage **or delegated child).
- Bump **`document`**`** ` revision (**§**`**`0` **)** and append row to **`CHANGELOG`** (**stub below**) **.**

**CHANGELOG (stub)**

| Rev | Note |
|-----|------|
| FT1-doc-0.1-skeleton | Initial structure-only skeleton |
| FT1-doc-0.2-unknown-canon | Consensus: dedicated UNKNOWN family; canonical **`unknown.insufficient_evidence`**; §4 pairing rule; partial registry row (**§**`9` **)** |
| FT1-doc-0.3-annexb-acp-ref | Annex B points **`to`** **`audit-classification-protocol.md`** (**#187** / **`ACP`** skeleton) **`for`** operational interchange (**§ Annex B**) |

**Migration (**`future` **)**

| Epoch | Meaning |
|-------|---------|
| **FT1** | Current interpretive scaffold |
| **FT2** | Breaking slug / semantic reset (**requires mapping table + governance Issue**) |

_Normative tier architecture remains **explicitly **`out‑of‑scope`**** for FT1.**

---

## §13 Exemplar lifecycle (governance‑embedded ‖N‖)

**Stages**

1. **S0 — Structure acceptance** (**this **`skeleton`).
2. **S1 — Workshop round **`A`:** label **`subset`** (**`N`_A**`) using draft dimension enums (**record collisions / latency / confusion notes on **`tracking`**`).
3. **S2 — Spec patch:** revise definitions/enums/registry rows (**candidate** flag).
4. **S3 — Workshop round **`B`** stress (`N_B`).
5. **S4 — Stabilization gate:** **`inter‑rater`** **≥** **_TBD_** **_OR **_documented **_exceptions_** **_list_**.
6. **S5 — Normative registry freeze segment** (**subset validated rows only**).

**Anti‑overfitting**

- **`Cap`**`** ` added rows per **`workshop`; **defer** speculative families.
- Separate **instrumentation‑only anomalies** (**`#192` bridge**) narratives from narrative FTCs unless evidenced.

---

## References and bibliography ‖I‖ (non‑authority)

**(Informative pointers — do not supersede **`Issues`**)**

- `runtime_narrative_memory_prd1.md` — Goal / FR context (**`FR4`** anchor)
- `narrative_knowledge_ingestion_prd2.md` — downstream packet intent only
- `roadmap.md` — sequencing reference (`Phase -1`/observation posture)
- `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` — audit applicability / causal advisory / inventories
- `governance/rp-app/issue-tracking-workflow.md` — **`§`**`D`/****`**`§`**`**`F`**`/****`**`§`**`**`I` **discipline**
- `governance/rp-app/audit-classification-protocol.md` — **`#`**`187`** **/** **`ACP`** **interchange (**process bundles** **)** **`—`** **‖I‖ linkage **`to`** **`Issues`**

**Planned reciprocal pointer (**`AUDIT_DOCUMENTATION`**` **maintainers):** **`TBD`** add short **stub link** **`to`** **`this`** **`file`** (**separate **`PR`** **outside skeleton scope if not yet present **`—`** **_do not preempt maintainers _`here`_ **_without approval`).

---

## Annex A ‖I‖ Operator cheat-sheet (outline only)

**(Non‑normative)**

- **`TBD`:** one‑page **`decision`**` tree (**audit path healthy?`** **→ applicability → continuity slice → FTC family **…**`).
- Keeps **`normative`** **§**`**`§`** compact.

---

## Annex B ‖I‖ Operational interchange pointer (#187 / ACP)

**Process interchange** (exemplar package, FT1 label bundle, collision record, workshop exports) is specified in `governance/rp-app/audit-classification-protocol.md` (**ACP**, **ACP‑doc‑0.1‑skeleton**), coordinated **with** **`this`** **`FT1`** **`document`** **`revision`** **`FT1-doc-0.3-annexb-acp-ref`**.

**Non‑authority schema reminder** (**full **`keys`** **`in`** **`ACP`** **§§5–10**):**
```yaml
# See ACP-doc-0.1-skeleton §6 for authoritative label bundle (+ §5 exemplar §9 collision).
failure_taxonomy_ft1:
  ftc_primary: string   # §3; UNKNOWN: unknown.insufficient_evidence — §11
  dimensions:
    hypothesis_subsystem: string
    evidence_grade: string
    temporal_scope: string
  secondary_symptoms: []
  evidence_gap: {}      # mandatory structure when UNKNOWN primary — §11 + ACP §7
  evidence_references: []
  notes_operator: {}
```

---

## Maintenance TODOs (**`explicit`** **intentional** **markers**)

| ID | Marker |
|----|--------|
| **TODO‑ENUM‑01** | Finalize **`evidence_grade`** enums & synonyms vs **`AUDIT_DOCUMENTATION`** advisory guidance. |
| **TODO‑CROSSWALK‑03** | Fill concise §8 matrices post workshop #1 (**keep **≤`**`pages budget). |
| **TODO‑METRIC‑04** | Set **`κ`**`/agreement thresholds + **`N`_A/_N`_B **budgets (**§**`**`13` **|** **|** **|** **|` **§**`**`10` **|** **|** **|` **.** |
| **TODO‑RECIPROCAL‑POINTER‑05** | Add reciprocal pointer from **`AUDIT_DOCUMENTATION`** header / index (**coordination **`PR`**). |
| **TODO‑187‑BLOCK‑FORMAT‑06** | Paste **`surface`** **/** **`ACP`** **`TODO`**‑ACP‑04 **(**finalize **`Issues`** **`comment`** **`pattern`** **`post`** facilitator gate**)** **`;`** Annex B **`now`** **`points`** **`at`** **`audit-classification-protocol.md`** **.** |

---

**End FT1 document (**`structure + partial UNKNOWN registry` **)**
