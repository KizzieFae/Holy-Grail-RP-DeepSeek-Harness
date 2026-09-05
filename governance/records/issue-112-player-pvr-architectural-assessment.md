# Player PVR Architectural Assessment — Issue #112

**Assessment parent Issue:** [#112 — Assess the architectural value and necessity of player PVR](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/112)  
**Audit provenance:** E2E Session Quality Audit `9065f006` — finding **SQA-03**  
**Assessment dates:** 2026-09-04 (investigation) through 2026-09-05 (disposition and artifact publication)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full (`docs/issue-bootstrap-profiles.md`)  
**Remediation authorization on #112:** NONE (assessment only; implementation delegated to successors)  
**Report commit:** *(set at PR merge — see PR for exact SHA)*  
**External review:** PR + Greptile required per #112 validation criteria

---

## Repository anchor (immutable at assessment publication)

| Field | Value |
|-------|-------|
| branch | `main` |
| HEAD SHA | `33ab790d08b4086724199481094a28dcc9dd70ce` |
| origin/main SHA | `33ab790d08b4086724199481094a28dcc9dd70ce` |
| investigation execution baseline | `2292a17b80b2470500a75935f81d281c5f99944d` |
| natural-experiment evidence anchor | `296fb61ac26fdfe3b0968678bde3516cd845e305` (session `9065f006`, Condition B) |

---

## Document map

| Section | Content type |
|---------|--------------|
| §A–§L below | **Architectural conclusions** (synthesized from evidence) |
| [Evidence lineage](#evidence-lineage) | **Evidence** pointers |
| [Assessment dimensions](#required-assessment-dimensions-matrix) | #112 criterion coverage |
| [Final disposition](#l-final-disposition) | **Decisions** |
| [Successor work](#successor-work) | **Successor Issues** |
| [Deferred work](#deferred-work) | Intentionally deferred items |

---

## A. Assessment question

> **What architectural value and necessity does player perceptual visibility record (PVR) provide, and should it remain always-on, be narrowed, redesigned, or removed?**

This assessment distinguishes **capability necessity** (whether perceptual-decomposition guarantees matter) from **implementation necessity** (whether every player turn requires full LLM decomposition).

---

## B. Natural-experiment evidence

**Source:** Session `hg-session-9065f006` — documented in [`governance/records/e2e-session-quality-audit-9065f006.md`](e2e-session-quality-audit-9065f006.md) (SQA-01/SQA-03) and fixture [`data/fixtures/audit_sqa_e2e_9065f006/`](../../data/fixtures/audit_sqa_e2e_9065f006/).

| Observation | Value |
|-------------|-------|
| Player turns | 18 |
| Usable PVR | 0/18 (`invalid_excluded`) |
| Decomposition attempts failed | 36/36 (malformed structured output) |
| User-visible RP quality | Surprisingly good/coherent |

**Interpretation (two-part):**

1. **Always-on full PVR was not necessary for every player turn in this session.** Compensating mechanisms (Director advisory `user_turn_source`, scene progression, committed Character/history, generative plausibility, participation-direct framing) sustained coherent RP despite 0% usable PVR.
2. **This did not prove PVR has no architectural value.** Designed degradation operated correctly (neutral unavailable markers, suppressed triggers/memory writes). The experiment questions **always-on implementation necessity**, not whether differentiated perceptual guarantees are ever required.

---

## C. Cost / reliability evidence

**Production profile (verified at investigation baseline `2292a17`):** `deepseek-official` / `deepseek-v4-flash`, reasoning enabled (`low`), production character-profile ceiling **4096 output tokens** (`application-settings.mjs`).

### Ceiling exhaustion (controlled)

| Experiment | Ceiling | Result | Evidence |
|------------|---------|--------|----------|
| Two-fixture × five-run (seiza/Japan + #88 mixed) | **4096** | **10/10** `max-tokens`; **0/10** JSON emitted; **0/10** contract accepted | [`issue-112-evidence-4096-ceiling-report.json`](issue-112-evidence-4096-ceiling-report.json) |
| Same fixtures | **8192** (investigation override only) | **10/10** `max-tokens`; **0/10** JSON emitted; **0/10** contract accepted | [`issue-112-evidence-8192-ceiling-report.json`](issue-112-evidence-8192-ceiling-report.json) |

### Uncapped difficult-case cost (controlled)

Five-run repeatability on seiza/Japan dense turn (`complex_dense`) with **no output cap** ([`issue-112-pvr-repeatability-report.json`](issue-112-pvr-repeatability-report.json)):

| Metric | Finding |
|--------|---------|
| Total tokens per run | ~27k–44k (27,202 – 43,870) |
| Wall-clock | ~74s–131s per run |
| `validation_accepted` | **0/5** |
| Semantic units produced | **5/5** runs produced plausible semantic units (including disputed Japan narration as `internal/private`) |
| Mechanical validity | **0/5** accepted — source accounting / contract validation failed despite semantic direction |

Three-case live cost sample at production-like settings ([`issue-112-live-cost-report.json`](issue-112-live-cost-report.json)): ordinary public ~12.6k total tokens; mixed asymmetric ~29.8k; complex dense ~22.4k.

### Semantic vs mechanical divergence

Repeatability and live-cost runs show **semantic interpretation substantially more reliable than final canonical mechanical validity**: models often assign plausible kinds/scopes while failing exact span accounting, segment reciprocity, or validator acceptance.

Reasoning traces (investigation diagnostic; see #112 Issue thread and repeatability artifacts) show substantial effort on mechanical indexing, segment boundaries, and source-accounting reciprocity — not only semantic judgment.

**Precision note:** Token figures are investigation measurements on specific fixtures and profiles; they support architectural direction but are not production SLA guarantees.

---

## D. Architectural value finding

> **Full player PVR remains architecturally necessary for turns containing information whose perceptual entitlement is not uniform across Characters.**

Representative cases requiring differentiated visibility:

- intrinsically nonperceptual narration/cognition;
- concealed or restricted observable actions;
- directed or subset communication;
- role-private material;
- mixed-entitlement player turns.

**Decision:** Remove player PVR entirely — **rejected.**

Perceptual-boundary guarantees for asymmetric viewer entitlement cannot be replaced reliably by uniform projection or generative plausibility alone.

---

## E. Always-on necessity finding

> **Full semantic PVR is not necessary for player turns whose meaningful content can safely be projected uniformly to all eligible present Characters.**

**Decision:** Keep expensive full PVR always-on — **rejected** as default architecture.

**Basis for #121:** Cheap affirmative-safety checker routes uniform-safe turns to deterministic `uniform_projection`; uncertainty/failure routes to full PVR.

---

## F. #120 contribution

**Issue:** [#120](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/120) — integrated via PR #122.

**Semantic clarification:**

> **Kind identifies perceptibility in principle; scope identifies entitlement for perceptible information.**

**Generalized `internal`:** Player-authored nonperceptual explanatory narration (e.g. seiza/Japan habits line) is **`internal`** — intrinsically nonperceptual information — **not** because it is unquoted prose mistaken for cognition, but because Characters cannot directly observe that story truth. Observable seiza posture remains `observable_event` with present/public scope.

This preserves perceptual-boundary withholding without mislabeling exposition as literal private cognition.

---

## G. #121 contribution

**Issue:** [#121](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/121) — integrated via PR #123.

**Two-path architecture (accepted):**

```text
player source
    ↓
cheap affirmative-safety checker
    ├── uniform-safe
    │      ↓
    │ deterministic uniform projection
    │
    └── complex / ambiguous / failure
           ↓
       full semantic PVR
```

**Properties:**

- Checker is **routing-only**; `reason` is audit evidence, not semantic truth.
- Failure or uncertainty **falls through to full PVR** (positive-safety design).
- Mandatory validation corpus: **12 cases × 3 repeats = 36 live calls**; **0/36 false-simple**; **0/36 false-complex** ([`v2/rp_runtime/tests/fixtures/issue121-checker-validation-report.json`](../../v2/rp_runtime/tests/fixtures/issue121-checker-validation-report.json)).
- Both paths validate through `player_perceptual_service.py` and converge on projector `hg.perceptual_visibility.v1`.

Documented in [`docs/architecture.md`](../../docs/architecture.md).

---

## H. Full-PVR redesign finding → #124

> **The semantic LLM should perform semantic interpretation; deterministic code should perform exact mechanical source-accounting construction wherever safely derivable.**

**Evidence pattern:** Uncapped and capped experiments show models producing directionally correct semantic units while failing exact canonical source accounting (see §C).

**Target architecture:**

```text
player source
    ↓
full PVR semantic LLM
    ↓
looser semantic intermediate representation
    ↓
deterministic normalization → canonical PVR record
    ↓
existing validation / persistence / projection
```

**Successor:** [#124](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/124) owns implementation.

---

## I. Missing-context finding → #125

> **Full player PVR must receive sufficient authoritative runtime scene/perception context to make legitimate viewer-entitlement decisions.**

**Evidence:** `prepare_player_decomposition_context` (`v2/domain_api/player_decomposition_context.py`) supplies only decomposition output-contract instructions — **no authoritative cast, presence, location, or perceptual-grant context**.

**Celina/Harley diagnostic (#88-shaped mixed turn):** Fixture `build_issue_88_mixed_turn_fixture()` — concealed latch work behind a closed door with `scope: private` for Celina; Harley excluded from private segment by player prose.

- **Harley exclusion** can be inferred from the player source (closed door; private action).
- **Celina inclusion** cannot be legitimately inferred from the context actually supplied to PVR inference — the model is not told Celina is the viewer behind the door or otherwise entitled.

This exposed a **context/oracle problem**, not merely LLM quality failure.

**Successor:** [#125](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/125) owns minimum-context contract and implementation.

---

## J. Inference-profile deferral

Dedicated full-PVR inference profile (reasoning level, maxTokens, timeout, retries, latency targets) is **intentionally deferred**.

**Reason:** #124 changes the workload. Current measurements reflect combined semantic + mechanical accounting in one LLM step. Re-measure after deterministic normalization removes mechanical work from the semantic LLM.

---

## K. Checker monitoring

Operational monitoring of checker **false-simple** and **false-complex** rates beyond the initial 36-call corpus is a **future operational concern**, not an immediate architectural successor.

**Disposition:** No dedicated Issue unless production evidence requires implementation. #114 (cross-runtime inference health) partially covers budget-pressure monitoring but not checker classification accuracy.

---

## L. Final disposition

| Outcome | Status |
|---------|--------|
| Remove player PVR entirely | **Rejected** |
| Keep expensive full PVR always-on | **Rejected** |
| Narrow activation with safe uniform fast path | **Accepted** — implemented by **#121** |
| Preserve full PVR for semantically complex/asymmetric turns | **Accepted** |
| Redesign full PVR semantic/mechanical boundary | **Accepted** → **#124** |
| Supply authoritative context for entitlement reasoning | **Accepted** → **#125** |
| Dedicated inference profile | **Deferred** until post-#124 measurement |

---

## Competing hypotheses evaluation

| Hypothesis | Disposition | Evidence summary |
|------------|-------------|------------------|
| H1 — PVR materially necessary | **Supported (conditional)** | Asymmetric/mixed turns require differentiated visibility; natural experiment shows degradation fragility without PVR |
| H2 — PVR useful but overbuilt | **Supported** | Mechanical accounting in LLM is expensive; semantic/mechanical split favored |
| H3 — PVR substantially redundant | **Rejected** | Natural experiment does not prove redundancy; compensating paths are not equivalent guarantees |
| H4 — PVR conditionally valuable | **Supported (primary)** | Aligns with #121 narrow activation + full PVR for complex turns |

---

## Q1 / Q2 / Q3 answers

| Question | Answer |
|----------|--------|
| **Q1 — Capability necessity** | **Yes** — perceptual-decomposition capability materially matters for asymmetric entitlement |
| **Q2 — Conditional necessity** | Complex, mixed, private, directed, nonuniform, or ambiguous visibility turns |
| **Q3 — Always-on implementation necessity** | **No** — uniform-safe turns can use deterministic uniform projection (#121) |

---

## Evidence lineage

| ID | Type | Location |
|----|------|----------|
| E1 | Audit report | [`governance/records/e2e-session-quality-audit-9065f006.md`](e2e-session-quality-audit-9065f006.md) |
| E2 | Audit fixture | [`data/fixtures/audit_sqa_e2e_9065f006/`](../../data/fixtures/audit_sqa_e2e_9065f006/) |
| E3 | Semantic-triage V1 experiment | [`issue-112-triage-report.json`](issue-112-triage-report.json); #112 Issue comment (semantic-triage experiment) |
| E4 | Five-run uncapped repeatability | [`issue-112-pvr-repeatability-report.json`](issue-112-pvr-repeatability-report.json) |
| E5 | Three-case live cost sample | [`issue-112-live-cost-report.json`](issue-112-live-cost-report.json) |
| E6 | 4096 ceiling experiment | [`issue-112-evidence-4096-ceiling-report.json`](issue-112-evidence-4096-ceiling-report.json) |
| E7 | 8192 ceiling experiment | [`issue-112-evidence-8192-ceiling-report.json`](issue-112-evidence-8192-ceiling-report.json) |
| E8 | #121 checker corpus | [`v2/rp_runtime/tests/fixtures/issue121-checker-validation-report.json`](../../v2/rp_runtime/tests/fixtures/issue121-checker-validation-report.json) |
| E9 | #120 semantic contract | PR #122; `narrative_visibility_prompt.py`; [`docs/architecture.md`](../../docs/architecture.md) |
| E10 | PVR context assembly | `v2/domain_api/player_decomposition_context.py` (code inspection) |
| E11 | #88 mixed-turn fixture | `v2/domain/modules/player_decomposition_fixtures.py` |

---

## Required assessment dimensions matrix

| # | Dimension | Finding (summary) | Primary evidence |
|---|-----------|-------------------|------------------|
| 1 | RP fidelity | Natural experiment: good RP despite 0% PVR; not proof PVR is unnecessary | E1 |
| 2 | Character responsiveness | Degradation relied on Director advisory + scene state | E1 SQA-03 |
| 3 | Semantic precision | Pre-#120: `internal` over-applied; #120 generalized semantics | E4, E9 |
| 4 | Perceptual-boundary correctness | PVR path supplies guarantees; degradation is intentionally conservative | E1 |
| 5 | Concealed/private/mixed actions | Required full PVR; checker corpus includes #88 mixed | E5, E8, E11 |
| 6 | Multi-observer behavior | Triage YES cases include multi-observer differential | E3 |
| 7 | Participation-direct behavior | Heavier scene/boilerplate reliance when PVR absent | E1 SQA-03 |
| 8 | Director dependency | Advisory `user_turn_source` practically important under PVR failure | E1 SQA-03 |
| 9 | Latency (PVR-attributable) | Difficult full PVR: ~45s–131s wall-clock in samples | E4, E5 |
| 10 | Token cost (PVR-attributable) | Production ceiling exhausted; uncapped ~27k–44k on dense turn | E4–E7 |
| 11 | Retry/failure surface | 4096/8192 exhaustion; validator rejects despite semantic output | E4–E7 |
| 12 | Implementation complexity | Combined semantic+mechanical LLM contract is complex | E4, code |
| 13 | Validation/projector complexity | Single projector; validation at `record_user_turn` | E9, docs |
| 14 | Auditability value | Execution evidence + PVR records support forensic replay | E1, E4 |
| 15 | Overlap with other lanes | Director/continuity compensate but do not replace entitlement guarantees | E1 |
| 16 | Smaller/narrower mechanism | #121 uniform path + #124 normalization split | E3, E8, disposition |

---

## Successor work

| Order | Issue | Status | Scope |
|-------|-------|--------|-------|
| 1 | [#120](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/120) | **Complete** | Semantic kind/scope contract |
| 2 | [#121](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/121) | **Complete** | Checker + uniform projection |
| 3 | [#124](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/124) | Open (P2) | Semantic/mechanical normalization |
| 4 | [#125](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/125) | Open (P2) | Authoritative runtime context |

---

## Deferred work

- Dedicated full-PVR inference profile — after #124 remeasurement
- Checker false-simple/false-complex production monitoring — unless operational evidence warrants a new Issue

---

## External verification

This assessment is committed via PR scoped to #112 documentation. **Greptile review on exact PR head is a closure gate** per #112 validation criterion 9. Merge and Issue closure require Governance authorization.
