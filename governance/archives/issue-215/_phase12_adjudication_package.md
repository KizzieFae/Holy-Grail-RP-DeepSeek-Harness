# Phase-12 — Curated stakeholder adjudication package (`#215`)

**Status:** Governance preparation artefact (**DRAFT**).  
**Authority:** Supplementary briefing for human adjudicators reviewing **`#215`**. Does **NOT** supersede matrix draft comments; does **NOT** enact product policy.

**Preserved seams:** **`#191` verbatim‑lane conclusion** orthogonal to thematic scaffolding **`#215`**; **`#214`** Tier audit artefacts usable as optional stress inputs—not merged decision scope.

---

## Curated exemplar portfolio

Grouped for review sessions. Artifact paths assume operator tree: `autogen_rp/python/rp_app/data/rp_audits/session_<NNN>/round_001/` + filename pattern `<scenario>_session<NN>_round001_turn<TT>_<role>_full.json` (underscore role slugs vary: `hannah_lovelace`, etc.).

### A. Choreography-only recurrence (HIGH alignment confidence preferred)

| ID | Session / turn / character | Observer role | Matrix-adjacent rows (conceptual) | Confidence class | Why it matters |
|----|---------------------------|---------------|-----------------------------------|-------------------|----------------|
| **E-A1** | **`743`**, Ayame / Hannah audited turns **`T08` PRE**, **`T11` CORE`** (prompt `input_messages[0]`); **Hannah** lines | Hannah = **non-recipient** to AC private beats | **Episodic interpretation / CONDITIONAL** (interpretive atmosphere); **not** authored retrieval | **`HIGH_CONFIDENCE_STRICT_PRIVATE`** window **[10,12]** per Phase-9/10 tooling | Dominant pattern: **`Saw …` witness compression** with neutral **`felt:`** framing—stakeholder baseline for “ambient observer recall” without quoted gist. |
| **E-A2** | **`749`**, Hannah **`T09`**, **`T12` POST** (scripted scan in `_p10_interpretation_severity.py`) | Hannah **observer** | Same family | **`HIGH`** window **[7,7]** | POST-only Hannah interpretations when tight private window does not intersect Hannah turn ordinals—**recurrence without shared CORE beat** across cast. |
| **E-A3** | **`755`**, Ayame **`T10`**, **`T12` POST** (episodic blocks per Phase-10 export) | Ayame focal | Focal choreography interpretation recurrence | **`HIGH`** | Illustrates **speaker-class** payloads under strict window with **sparse Hannah listing**—guards against over-indexing Hannah-only excerpts. |

### B. Lawful observable consequence framing (D-2 scaffold analogue)

| ID | Session / turn / character | Observer role | Matrix rows impacted (conceptual) | Confidence class | Why it matters |
|----|---------------------------|---------------|-------------------------------------|-------------------|----------------|
| **E-B1** | **`743` Hannah `T08`–`T11`** episodic blobs referencing **Ayame posture / Celina gestures** absent verbatim private payloads | Hannah | **CONDITIONAL ALLOW** analogue if tied to plausible witness kinematics (**O-1**) | **HIGH** choreography window | Distinguishes **witnessable staging** from **covert semantic calibration**. |

### C. Gist / “heard:” interpretation recurrence (primary severity seam)

| ID | Session / turn / character | Observer role | Matrix rows impacted (conceptual) | Confidence class | Why it matters |
|----|---------------------------|---------------|-------------------------------------|-------------------|----------------|
| **E-C1** | **`743` Hannah `T11` CORE** — Celina-linked line includes **`heard: "Hannah's co-hosting, so I'll be br…`** (truncated in prompt) | Hannah | **Gist / thematic compression** vs **Tier-1 naive social pressure** | **HIGH** | Classic **partial public-line re-import** through episodic interpretation tail—stakeholder must decide **compression severity** vs **ALLOW with guardrails**. |
| **E-C2** | **`752` Hannah `T12` POST** — `Saw Ayame and heard: "She pressed a little, asked about my personal life"` | Hannah | **Medium-risk gist sharpening** (**candidate**) | **`LOW_*` fallback window** (**session‑level**) — excerpt still manually reviewable | Single clearest scripted **`gist_bridge`** exemplar (**Phase-10**)—**severity discussion anchor** despite **messy choreography-confidence label at session rollup**. |

### D. Ambiguous compression

| ID | Session / turn | Notes | Confidence | Why adjudicate manually |
|----|----------------|-------|------------|-------------------------|
| **E-D1** | Mixed **`749` POST` Hannah excerpts** blending **staging + proxemic language** (**Exhales smoke… narrowed eyes**) | gist heuristic **ambiguous** (**may read as theatrical colour or inference**) | HIGH window | Boundary between **novelistic colour** and **covert thematic steering**. |

### E. Negative literal-anchor evidence

| ID | Cohort scope | Observation | Confidence | Why it matters |
|----|--------------|-------------|------------|----------------|
| **E-E1** | Tier A scans across **`743`**, **`748`** (`_p8` / `_p10` style substring sweeps) | No **`ZEPHYR` / `SILVER-QUILL-414`** in sampled `input_messages` bodies | **Negative evidence** (finite windows) | Sustains **literal DENY row stability** in governance narrative **without** claiming impossible forever. |
| **E-E2** | Extended MPD **`746` vs `747`** Hannah **`T11`** (`memory_private_directed`, Phase-7/8) | **`codeword` lexical carrier** persists **episodic ON vs OFF**; **not** literal ZEPHYR token in sampled windows | Pairwise **HIGH** ordinal match | Shows **carrier class orthogonal** to episodic envelope activation. |

### F. Instrumentation-confounded / unreliable for severity adjudication alone

| ID | Pattern | Why exclude or down-weight |
|----|---------|----------------------------|
| **E-F1** | Sessions **`750`–`754`** (bulk Tier A epON cohort) **`LOW_CONFIDENCE_EXPANDED_FALLBACK`** windows | Whole-arc **`CORE`** labels—**PRE/POST choreography comparators unreliable** (**Phase-9/-10**) |
| **E-F2** | **`739`‑class** rollup **`retrieval_verified_active: false`** while rollup mode ON (Phase‑7 MPD archaeology) | Distinguish **instrumentation anomaly** vs **semantic behaviour** (**do not doctrine-collapse**) |
| **E-F3** | Tier A **`bounded_token_found=True`** gate footers vs prompt-body absence | **Telemetry ≠ prompt provenance**—**do not conflate**. |

---

## Draft severity classification guidance (non‑ratified stakeholder sketch)

**Purpose:** Orientation only. Final wording belongs in matrix / PRD after **`consensus_reached`**.

### Likely tiers (illustrative language only)

| Bucket | Working description | Example hooks from portfolio |
|--------|----------------------|------------------------------|
| **Acceptable observable recurrence** | **Choreography-only** witness lines **`Saw …` / `felt:` neutral** without third-party tactical attributions extending beyond plausible witness kinematics | **E-A1**, parts of **E-B1**. |
| **Low-risk interpretation compression** | Short **public-truth or manifest-or-plausible gist** resurfacing (**co-host**, room logistics) — **themes already socially legible**, not covert plan payloads | Fragments resembling **E-C1** (**if** adjudicated as mundane). |
| **Medium-risk gist sharpening** | **Paraphrase or heard-channel** summaries that recap **relational / thematic stakes** (**personal life probe** phrasing)—**elevates tactical calibration risk** absent verbatim private text | **E-C2** (**prime review object**). |
| **High-risk semantic leakage candidate** | **Directed correlates approaching covert plan fidelity** (**bounded tokens**, role-breaking specifics, lexical fingerprints)—**NOT observed** in curated literal scans | **None admitted in portfolio** as positive literal hits—**intentionally empty row** documents negative evidence posture. |

### Evidence thresholds before escalation (governance)

1. **Minimum:** at least **one** **HIGH-confidence choreography window** session **plus** **one** independent seed **OR** manual cross-read of same exemplar by **two** stakeholder roles.  
2. **Before** elevating **gist** to **medium-risk** default: confirm **not** explainable as **public beat repetition** or **manifest continuity consequence** (**D-5** analogue).  
3. **Before** attributing to **implementation defect:** rule out **instrumentation confound** (**E-F2/F3**).  
4. **Escalation to engineering only** after **`consensus_reached`** + separate implementation issue—**out of scope** for this package.

---

## Matrix refinement candidates (non‑ratifying)

| Row / theme | Stabilization readiness | Notes |
|-------------|-------------------------|-------|
| **Literal private / bounded-token DENY** (verbatim lane **#191** inheritance) | **Relatively stable** empirically (negative samples) | Do **not** weaken—**restate as observationally supported in sampled waves**, not absolute future-proof. |
| **Authored retrieval vs episodic merge under `RETRIEVED REFERENCE MATERIAL` header** | **Ready for dedicated split language** in next matrix forward revision | Taxonomy pressure repeated Phases **7–10**. |
| **`episodic:interpretation` sub-lane** | **Requires dedicated treatment** text—**orthogonal** to authored retrieval rows | **CONDITIONAL** until exemplar adjudication closes. |
| **Interpretive atmosphere / compression** | **Unstable**—depends on **E-C1/C2** outcome | Likely **long-horizon CONDITIONAL** with exemplar library. |
| **Choreography-confidence disclaimers** | **Stabilize as meta-row** (“evidence weighting”) | Prevents over-claim from stochastic Tier A replays. |

---

## Provisional disposition-analysis briefing (NOT final)

**Trend the evidence currently appears to support (tentative):**  
Thematic / interpretive tails—especially under **episodic merge**—can recur at **choreography-heavy** severity with **occasional gist `heard:` bridges**, while **literal DENY anchors** stay **absent in sampled windows**. **Semantic isolation (#191) and architecture authority (#215/GP) remain compatible** with a **stakeholder-tuned CONDITIONAL band** for interpretive compression **rather than** a blanket **ALLOW** or **DENY**.

**What would materially change the trajectory:**  
Repeated **high-confidence** sessions showing **verbatim or near-verbatim private payloads** in non-recipient prompts; **systematic** high-risk gist lines **across** independent seeds with **HIGH** choreography confidence; **instrumentation** proving **deterministic** semantic assistance (**D-6** analogue).

**Conditions forcing stronger severity conclusions:**  
Multiple **independent human adjudicators** agreeing **E-C2-class** lines breach product comfort; **O-1** failure demonstrations on fixed exemplar set; **PRD** must/should language emerging elsewhere.

**Uncertainty:** Stochastic Tier A parse density + **fallback windows** cap **statistical confidence**; **gist** severity remains **qualitative judgement**-heavy.

---

## Governance-risk warnings (for adjudicators)

1. **Choreography-confidence traps:** **LOW** alignment labels **do not** mean “more leakage”—they mean **weaker beat alignment** for comparison.  
2. **Heuristic overreading:** `_p10_interpretation_severity.py` tags are **screening aids**, not verdicts.  
3. **Stochastic replay bias:** **Single-seed** drama variance can overweight **outlier gist** lines.  
4. **Narrator vs character:** This package **defaults to character `input_messages`**; narrator audits require **explicit cross-channel protocol** if ever introduced.  
5. **Instrumentation anomaly misuse:** **`retrieval_verified_active` skews** must not **short-circuit** semantic classification.

---

## Recommended next governance action (ONE)

**Primary:** **Stakeholder adjudication session** focused on exemplar set **E-C1 / E-C2 / E-A1** with **explicit NOT-for-agenda** list (no implementation scoping; no DENY relaxation).

**Justification:** Phase work has shifted from **volume replay** to **severity classification of known seams**; **human triage** is now the **rate-limiting step** before any matrix forward revision or micro-wave design. A matrix refinement pass or micro-wave **without** this session risks **pre-judging** **CONDITIONAL** rows on automation alone.

---

**GitHub anchor (after posting):** attach this file as Issue **`#215`** Phase-12 comment permalink per project workflow.
