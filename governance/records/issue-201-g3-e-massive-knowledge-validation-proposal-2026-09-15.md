# Issue #201 G3-E — Massive-Knowledge Validation Proposal

**Date:** 2026-09-15 (refined)  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** Refined proposal — consensus candidate; implementation **not** authorized; execution **not** authorized  
**Prior phases:** G3-A wiring · G3-B STRONG A2 · G3-C QUALIFIED A2 · G3-D complete + causal trace (`03e12f5`)

---

## Governing hypothesis

> Can the lean A2 architecture correctly and usefully operate over a massive knowledge environment using deterministic retrieval, entitlement, provenance, and bounded context projection **without** recreating routine Librarian LLM mediation or the A4 cognition bureaucracy?

**Not tested:** long-horizon RP; Plot/Scribe marginal value over accumulated story progression.

---

## Methodology preservation

- G3-E remains the **originally planned knowledge-scaling experiment** (single-beat / short-turn per K-case).
- **No** long-horizon sequences added to current G3 methodology.
- **No G3-F.** G3-E is knowledge scaling only.
- G3-D establishes four-turn local continuity only; does **not** adjudicate long-horizon Plot value.
- Plot previously showed positive **immediate-turn** marginal value; long-horizon Plot topology remains unresolved.

> Long-horizon RP validation will be designed only after completion and synthesis of the currently planned architecture-testing methodology.

---

## Arms (unchanged)

| Arm | ID | Topology |
|-----|-----|----------|
| **A2 indexed retrieval** | `a2_indexed_retrieval` | Obligation → deterministic retrieval → entitlement → ranking → bounded projection → Primary RP (Character move) → validation → commit/presentation. **No** orientation LLM, **no** Librarian mediation, **no** Plot. |
| **Lean A4 knowledge** | `lean_a4_knowledge` | D-07 ablated baseline: orientation LLM → KAR → Librarian mediation → packaging → Primary RP. **No** Plot (matched). Same corpus, stimuli, entitlements, model profiles. |

---

## Corpus (unchanged)

**Fixture root:** `governance/records/issue201-g3e-fixtures/ayame_archive_corpus_v1/`  
**Runtime lane:** pre-seeded `data/sessions/_story_knowledge/{g3e_memory_scope}/records.jsonl` + TF-IDF rebuild  
**Scale target:** ~280–320 JSONL records (retrieval difficulty, not token bulk)

| Pressure class | Approx count |
|----------------|--------------|
| Irrelevant plausible household/admin records | ~180 |
| Semantically similar distractors (wrong estate/applicant) | ~40 |
| Entity-specific authorized facts | ~35 |
| Private / role-scoped records | ~25 |
| Superseded + authoritative replacement pairs | ~12 |
| Multi-record dependency sets | ~8 groups |

**Scenario shell:** `ayame_archive_interview` — Ayame household entry evaluation with archive-consultation beats (extends frozen Ayame template; **not** G3-D longitudinal policy).

**Design:** 7 K-cases × 2 arms = **14 runs** minimum (+1 optional repetition per case if Governance wants N=2).

---

## Authoritative retrieval ordering (production — do not alter)

Per `story_knowledge_retrieval.select_story_candidates`:

1. Referent / entity constraints  
2. **`story_record_epistemically_eligible` (entitlement / `known_by`)**  
3. Eligible set E assembled  
4. Semantic ranking (TF-IDF) **only within E** when E exceeds budget  
5. Bounded projection

**Implication for K3:** A forbidden private record may never enter the ranked candidate list. Forensic proof must show the record **would be retrieval-relevant** (query overlap, referent match) and was **rejected at entitlement** (`hard_access_rejected`), not merely absent from corpus or never lexically matched.

Harness must **not** weaken production knowledge boundaries or reorder stages for observability.

---

## K1–K7 capability matrix

Each K-case is adjudicated **individually**. Obligations are heterogeneous; **no aggregate pass-rate** (e.g. `5/7`) substitutes for a capability matrix.

### Per-case outcome taxonomy

| Code | Meaning |
|------|---------|
| **PASS** | All stage gates for that K-case satisfied |
| **FAIL — retrieval** | Required record not found in retrieval stage |
| **FAIL — ranking/distractor** | Wrong record ranked above correct, or distractor projected |
| **FAIL — entitlement** | Forbidden record projected, or entitled record wrongly excluded |
| **FAIL — stale-authority resolution** | Superseded record used; authoritative revision missed |
| **FAIL — projection/budget** | Required record retrieved but dropped by budget/caps |
| **FAIL — Primary-RP consumption** | Record projected but not reflected in character move |
| **FAIL — synthesis** | Records present but not correctly combined (K6-S) |
| **MEDIATION OBLIGATION DEMONSTRATED** | Unresolved semantic conflict after correct retrieval; `mediation_would_be_required` logged on A2 |
| **INCONCLUSIVE / forensic insufficiency** | Audit chain cannot establish stage outcome |

Governance receives a **capability matrix** (K1–K7 × stage outcomes × arm), not a single score.

---

## K-case specifications

### K1 — precise old fact

**Stimulus:** Ask Ayame to cite the **2019 silver-service rule** for weekend staff.  
**Truth manifest:**

| Field | Value |
|-------|-------|
| `required_record_id` | `g3e-k1-silver-2019` |
| `query_relevance_terms` | silver service, weekend staff, 2019 |
| `depth_class` | deep_index (low TF-IDF prior without query) |

**Stage gates:** retrieval → projection → consumption (presentation cites fact).

---

### K2 — distractor resistance

**Stimulus:** Ask which **estate policy** governs tenant curfew disputes.  
**Truth manifest:**

| Field | Value |
|-------|-------|
| `required_record_id` | `g3e-k2-ayame-curfew-policy` |
| `forbidden_distractor_ids` | `g3e-distract-riverside-curfew`, `g3e-distract-annex-guest-policy` |
| `distractor_similarity_class` | high_semantic_overlap |

**Stage gates:** ranking must prefer required over distractors; forbidden IDs absent from projection.

---

### K3 — private knowledge protection (revised)

**Purpose:** Prove **entitlement enforcement**, not mere absence of retrieval.

**Stimulus (revised):** Kizzie asks whether prior financial difficulties at a **previous tenancy** would affect her application — wording that makes **Kizzie's undisclosed debt record** a **high-relevance retrieval candidate** for the archive query Ayame must answer.

**Forbidden record:** `g3e-private-kizzie-debt`  
- Content: Kizzie's undisclosed prior-debt judgment (Kizzie-private).  
- **Intentionally retrieval-relevant:** shares query terms (`financial`, `prior tenancy`, `debt`, `judgment`) with stimulus.  
- **Ayame non-entitled:** `known_by` = `kizzie` only (or equivalent epistemic gate).  
- **Kizzie entitled** (control — not projected to Ayame cognition).

**Truth manifest fields:**

```json
{
  "case_id": "K3",
  "forbidden_record_id": "g3e-private-kizzie-debt",
  "kizzie_entitled": true,
  "ayame_entitled": false,
  "expected_query_relevance": "high",
  "expected_referent_match": true,
  "forbidden_in_projection": true,
  "forbidden_in_character_manifest": true,
  "forbidden_in_presentation": true
}
```

**Required forensic chain (7 steps):**

| Step | Evidence source | Pass criterion |
|------|-----------------|----------------|
| 1. Record exists | corpus manifest | `g3e-private-kizzie-debt` in JSONL |
| 2. Retrieval-relevant | truth manifest + query_terms | Record listed in `k3_relevance_set` (curated high-overlap terms) |
| 3. Pre-entitlement encounter | harness forensic: unconstrained lexical/semantic probe **or** `referent_match=true` on record | Record **would** enter candidate pool absent entitlement filter |
| 4. Entitlement rejection | `RetrievalAccessDiagnostics.hard_access_rejected` + per-record rejection log | `story_record_epistemically_eligible` = false for viewer=Ayame; rejection counted |
| 5. Not in eligible set | retrieval forensics: `eligible_record_ids` | `g3e-private-kizzie-debt` **not** in eligible[] |
| 6. Not in Character input | actor manifest audit / contribution `record_id` scan | Forbidden ID absent from cognition package |
| 7. Not in output | presentation + move audit | No private debt content; isolation audit pass |

**Production ordering note:** Because entitlement precedes ranking, step 3 uses **equivalent forensic evidence** (referent match + query-term overlap + optional offline probe showing record ranks in unconstrained index) — **not** appearance in `ranked_ids`.

**Blocking failure:** Any breach of steps 5–7 (forbidden record in eligible set, manifest, or presentation).

---

### K4 — authorized private knowledge

**Stimulus:** Ayame asked to state **master-key custody rule** (household-private, Ayame-entitled).  
**Truth manifest:** `required_record_id: g3e-private-ayame-master-key`; `ayame_entitled: true`.

---

### K5 — superseded/stale information

**Stimulus:** Ask current **weeknight curfew**.  
**Truth manifest:**

| Field | Value |
|-------|-------|
| `authoritative_record_id` | `g3e-curfew-2024-11pm` |
| `superseded_record_id` | `g3e-curfew-2019-9pm` |
| `supersedes_link` | explicit in corpus metadata |

**Blocking failure:** Superseded record projected or cited as current authority.

---

### K6 — multi-record requirement (decomposed)

**Stimulus:** Ask whether a tenant may **host guests overnight** (requires lease clause §4 + witness-notification rule).

**Required records:**

| Record ID | Role |
|-----------|------|
| `g3e-lease-guests` | Lease clause §4 — guest prohibition/conditions |
| `g3e-witness-rule` | Witness-notification requirement |

#### K6 sub-stages (adjudicated separately)

| Sub-stage | Question | Failure code |
|-----------|----------|--------------|
| **K6-R — retrieval** | Were both required authorized records retrieved into eligible set? | FAIL — retrieval |
| **K6-P — projection** | Were both correctly projected into Primary-RP cognition with provenance? | FAIL — projection/budget |
| **K6-C — consumption** | Did Primary RP recognize/use both relevant facts in move? | FAIL — Primary-RP consumption |
| **K6-S — synthesis** | Did Primary RP correctly combine them into the required response (guests + witness)? | FAIL — synthesis |
| **K6-M — mediation necessity** | After correct retrieval, does unresolved semantic conflict remain? | MEDIATION OBLIGATION DEMONSTRATED |

**Interpretation rules:**

- K6-R + K6-P + K6-C + K6-S all pass → deterministic retrieval/direct projection **succeeds**; Librarian not earned for this case.
- K6-R/K6-P pass but K6-C/K6-S fail → **Primary-RP consumption/synthesis failure**; not retrieval failure.
- Required record absent at K6-R → classify retrieval/ranking/entitlement/projection by forensic stage.
- K6-M only if conflict remains **after** both records correctly retrieved and projected.

**A2 arm:** Log `mediation_would_be_required` if K6-M triggers; **do not** invoke Librarian. Do not rescue experimental arm.

---

### K7 — irrelevant-volume pressure

**Stimulus:** Open-ended household policy question with large eligible surface.  
**Truth manifest:** `required_record_id` (if any), `max_projected_items: 8`, `max_projected_chars: 8000`, `irrelevant_ratio_threshold: logged_not_gating`.

**Stage gates:** caps respected; irrelevant_projected_ratio recorded.

---

## Objective gates

### Blocking correctness gates (any failure stops arm/case validity for that dimension)

1. **Entitlement leakage** — forbidden `record_id` in Character manifest or presentation (K3, K5 superseded misuse, any cross-actor leak).
2. **Stale/superseded authority violation** — superseded record used as current authority (K5).
3. **Untraceable knowledge** — fact in cognition/output without `record_id` + provenance in audit chain.
4. **Knowledge boundary violation** — private/role-scoped fact reaches non-entitled actor.
5. Commit failure or empty presentation.

### Non-blocking capability gates (recorded in matrix)

- Per-K retrieval, ranking, projection, consumption, synthesis outcomes (taxonomy above).
- Budget/caps (K7; also failure code when required record dropped).
- A2 arm: `librarian_mediation_count === 0` (expected); `mediation_would_be_required` logged only, not invoked.

### Comparative gates (not blocking alone)

- Blind semantic dimensions (see rubric).
- Projected token volume, LLM call counts, wall time.

---

## Falsification and adjudication framework (revised)

### Tier 1 — Blocking correctness failures

Immediate invalidity for the affected case (and may invalidate arm-level entitlement claims):

| Failure | Examples |
|---------|----------|
| Entitlement leakage | K3 forbidden record in manifest/presentation |
| Stale authority misuse | K5 cites 9pm curfew as current |
| Untraceable knowledge | Fact in output with no provenance chain |
| Boundary violation | Kizzie-private fact in Ayame cognition |

**These are never offset by comparative performance or blind scores.**

### Tier 2 — Capability deficiencies

Recorded per K-case in capability matrix. Each failure identifies a **targeted mechanism** need:

| Deficiency | Example | Implication |
|------------|---------|-------------|
| Old-fact retrieval miss | K1 FAIL — retrieval | Indexing/query obligation gap |
| Distractor ranking miss | K2 FAIL — ranking/distractor | Ranking/entitlement refinement |
| Entitlement false exclusion | K4 FAIL — entitlement | Epistemic gate bug |
| Multi-record synthesis fail | K6-S FAIL — synthesis | Primary-RP consumption, not retrieval |
| Projection omission | K6-P FAIL — projection/budget | Bounded projection too aggressive |

**No aggregate F1 threshold.** Governance reviews the matrix holistically.

### Tier 3 — Comparative performance findings

Retained where evidence-grounded (from G3-B/C baseline: Librarian did not buy blind quality on simple beat):

| Measure | Threshold | Evidentiary basis | Effect |
|---------|-----------|-------------------|--------|
| Blind usefulness delta | A2 ≥0.25 below lean A4 on knowledge-integration adjunct | G3-B/C showed small semantic gaps matter for adjudication | Material comparative weakness |
| Distractor contamination | ≥2 cases with forbidden `record_id` in projection | Objective precision failure | Ranking/entitlement weakness (also Tier 1 if entitlement) |
| Projected tokens | A2 ≥2× lean A4 median without higher per-case precision | Tests bounded projection claim (G2 §21) | Projection/budget concern |
| LLM calls | A2 median > lean A4 without per-case objective advantage | G3 efficiency thesis | Efficiency not demonstrated |
| Mediation collapse | Lean A4 succeeds K6 with mediation; A2 logs K6-M on ≥2 cases **and** cannot answer | Tests whether A2 defers synthesis to Librarian | Topology incomplete for synthesis class |

**Pass band (prospective, not single score):** Zero Tier-1 failures; capability matrix shows no systematic Tier-2 pattern across unrelated K-classes; Tier-3 comparative findings neutral or favorable on efficiency with acceptable blind integration.

---

## Final adjudication structure

Governance receives:

1. **Capability matrix** — K1–K7 × {PASS, failure codes, INCONCLUSIVE} × arm  
2. **K6 decomposition table** — K6-R/P/C/S/M per arm  
3. **K3 entitlement forensic chain** — 7-step checklist per arm  
4. **Tier-1 blocking report** — any correctness failures (must be empty for arm validity)  
5. **Tier-3 comparative summary** — blind scores, tokens, LLM calls, wall time  
6. **Librarian decision-value ledger** (lean A4 arm only)  
7. **Prospective verdict evidence** — not rendered by Implementation AI

---

## Blind semantic rubric (unchanged)

**Packet schema:** `issue201_g3e_blind_knowledge_packet_v1`

**Dimensions (1–5):** factual/world consistency; character knowledge fidelity; natural integration of retrieved knowledge; responsiveness; character fidelity; initiative; coherence; unnecessary exposition; narrative usefulness (adjunct).

---

## Librarian decision-value accounting (unchanged)

Per `librarian_mediation` call on lean A4 arm: cost → information → consumer → decision changed → benefit. Classify: uniquely necessary | useful synthesis | duplicate/compression | unused | harmful | uncertain.

---

## Context-pressure measurements (unchanged)

Corpus size; candidate count; post-entitlement eligible count; projected records/tokens; irrelevant ratio; Primary RP input tokens.

---

## Audit chain (unchanged)

```
knowledge_need → candidate_retrieval → ranking → entitlement_decision → provenance
  → projection → cognition_input → cognition_output → validation → commit/presentation
```

K3 adds: `pre_entitlement_relevance_probe`, `hard_access_rejected` per record, `eligible_record_ids` snapshot.

---

## Plot isolation (unchanged)

**Plot absent both arms** (`skipPostCommitPlot: true`). No G3-E conclusion about Plot.

---

## Future long-horizon reservation (unchanged)

Dedicated long-horizon RP validation designed **only after** completion and synthesis of currently planned G3 methodology. **No G3 experiment number. Not designed here. Not executed.**

---

## Smallest implementation (refined)

Prior list unchanged, plus:

7. **K3 forensic extensions** in `issue201-g3e-lib.mjs`:
   - `pre_entitlement_relevance_probe` (offline/unconstrained index query — read-only, does not alter production path)
   - `hard_access_rejected` / `eligible_record_ids` capture from `RetrievalAccessDiagnostics`
   - 7-step K3 checklist emitter

8. **K6 sub-stage adjudicator** — K6-R/P/C/S/M from forensic chain + move/presentation parse

9. **Capability matrix exporter** — JSON + markdown; no aggregate pass-rate

**Not required:** production entitlement reordering, new embedding provider, Plot wiring, long sequences.

---

## Governance decisions before execution

1. Approve **refined** G3-E proposal (this document).  
2. Approve revised **K3** design and 7-step entitlement forensic chain.  
3. Approve **K6 decomposition** and per-case capability matrix adjudication.  
4. Approve **Tier-1/2/3** falsification framework (no aggregate F1).  
5. Approve corpus scale (~300 records) and Ayame archive scenario shell.  
6. Authorize implementation (separate from execution).  
7. Authorize live execution (separate explicit action).  
8. Maintain `consensus_reached` until post-G3-E adjudication.

**G3-E implementation and execution: NOT authorized by this document.**
