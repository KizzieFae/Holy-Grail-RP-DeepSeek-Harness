# Issue #136 — F Action-Required Failure Attribution + Remediation Proposal

**Date:** 2026-09-07  
**Issue:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**PR:** [#137](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/137) OPEN (unmerged)  
**Phase:** Post-G4 attribution — Full-consensus steps **1** (proposal) + **3** (challenge/refinement); no implementation  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full  
**Evidence root (G4 live):** `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/`  
**Investigation anchor SHA:** `c677567`

---

## Activation state

| Field | Value |
|-------|-------|
| Branch | `issue-136-llm-inference-assessment` |
| Local HEAD | `c677567bb26ec9fcd05f0741507fa683c6177510` |
| Remote branch HEAD | `c677567` |
| PR #137 head | `c677567` |
| `origin/main` | `c04d19ca678bf23f06e4801a97db4376c74efcdb` |
| Issue state | OPEN |
| Issue status label | `implemented` (project workflow) |
| Project Status | In Progress |
| Project Workflow | Implemented |
| Priority | P3 |
| Production drift after G4 | **None** — HEAD matches G4 execution SHA |
| Production remediation in this step | **None** |
| Fresh paid/live inference in this step | **None** |

---

## Executive summary

All three G4 **F — ACTION-REQUIRED** failures share one dominant mechanism: **the fixture hazard never reached the Character decision manifest**. Forensic `scene_stimulus` and truth `committed_facts` record the cracking bracket and duty to respond, but **zero** inference attempts in any F live run contain `bracket`, `crack`, or `colleague`. Instead, the **live Director** invented unrelated opening `environment_event` prose (silver key introspection, bindery draft, library lectern), which became the sole situational cue in Character `director-context` (priority 22). The #136 behavioral invariant correctly says action/inaction should follow supplied context—but **the hazard context was not supplied** to Character at decision time.

This is **not** adequately explained as provider “action avoidance” or invariant underspecification alone. It is primarily a **decision-relevance projection / opening-stimulus packaging** failure within #136’s inference-contract scope, compounded by **live-campaign harness semantics** (fixture narrator lines run post-commit; `mockResponses` do not bind under `dsh` profile) and a **semantic-evaluator coverage gap** (no action-avoidance dimension).

---

## F run identifiers

| Rep | Run ID | Session ID | Report path |
|-----|--------|------------|-------------|
| 1 | `issue136-136-T2-F-ACTION-REQUIRED-r1-2686d44a-d755-4d28-ad37-525208661da1` | `hg-session-fa5770be-335e-457c-bc5b-8cc60a229b95` | `.../136-T2-F-ACTION-REQUIRED/rep-1/issue136-*.json` |
| 2 | `issue136-136-T2-F-ACTION-REQUIRED-r2-9ad7f075-f6df-4e89-af52-4e9f1113a414` | `hg-session-02f20375-f7af-4ac8-986a-6267dbebd08a` | `.../rep-2/...` |
| 3 | `issue136-136-T2-F-ACTION-REQUIRED-r3-4c12a8dd-2619-445d-adb0-c10e918198b4` | `hg-session-e60c8ad1-5519-496f-98c0-f26391f612a4` | `.../rep-3/...` |

Character move evidence IDs: `2f67224d`, `c3ccbdab`, `4a50a5e6` (reps 1–3).

---

## Per-run FACT → FIDELITY traces (condensed)

### Fixture truth (all reps)

- **FACT:** Support bracket visibly cracking above colleague’s station; imminent harm likely; Mara sees it; nearest capable responder; no legitimate reason to wait.
- **AUTHORITY:** `data/fixtures/issue136_tier2_fidelity/truth/136-t2-f-action-required.json` (`committed_facts`, `scene_stimulus`, `supported_envelope`).
- **Harness narrator line (post-commit mock, not pre-decision):** `NARRATOR_BY_FIXTURE['136-T2-F-ACTION-REQUIRED']` in `issue136-tier2-campaign.mjs`.

### Rep 1

| Link | Finding |
|------|---------|
| ENTITLEMENT | Fixture asserts Mara entitled to clear visual hazard + duty. |
| PROJECTION | **Absent** — full attempt corpus search: no `bracket`/`crack`/`colleague`. |
| Live Director `environment_event` | Silver key / window reflection introspection (`evidence d7d704d8`). |
| DECISION RELEVANCE | Protective response required **if** hazard present; model saw introspection-only opening. |
| FIDELITY | Mara principled/guarded — introspective key beat is consistent with **wrong** stimulus, not fixture hazard. |
| Move | Apron/key introspection; no warning or protective action. |
| Semantic QA | `overall_result: pass`, findings `[]`. |

### Rep 2

| Link | Finding |
|------|---------|
| PROJECTION | **Absent** (same corpus search). |
| Live Director `environment_event` | Cold draft / old paper / metallic scent in bindery stacks (`e1ac7ac1`). |
| Move | Investigates draft; no colleague hazard response. |
| Semantic QA | Pass, no findings. |

### Rep 3

| Link | Finding |
|------|---------|
| PROJECTION | **Absent**. |
| Live Director `environment_event` | Dim library lectern, rustling book (`a8e140ff`). |
| Move | Explicit non-approach at lectern. |
| Semantic QA | Pass, no findings. |

---

## Salience / manifest analysis

### Character manifest (all F reps)

Contributions present: `scene_state` (10), identity/expression/scene-context (18–19), `director-context` (22), response-contract (28), instruction (30). **No opening text, no hazard terms, no committed_facts projection.**

`scene-context` (~216 chars): scene progression shows **“No committed public events yet”** / phase `opening` — does not include `opening.text` from session create.

`director-context` (priority 22): JSON advisory with live `environment_event` **replacing** fixture hazard.

Behavioral invariant (priority 30): *“Ground this turn's beats and motivation in the authoritative Character and scene context already supplied; action, inaction, and change should follow from that context.”* — **cannot apply to absent hazard.**

Response contract (priority 28): structural JSON schema only; no action mandate.

### Director manifest (F rep 1 exemplar)

Includes `scene_progression` (“No committed public events yet”), Storyteller progression opportunities (“Environmental anchor”, “Inciting whisper”, “Character micro-behavior”), **no opening/stimulus/hazard**. Storyteller advisories steer atmospheric opening, not duty-bearing hazard.

### Opening packaging gap

`buildSessionCreateBody` sets `opening: { mode: 'custom', text: truth.scene_stimulus }`. Session setup stores `opening_description` and history entry `kind: opening`, but `project_scene_setup` projects `scene_premise` only — **not** `opening_description` or opening history — into Director/Character authoritative context at turn 0.

### Live campaign harness semantics

G4 ran `mode: 'live'`. `inference-substrate.mjs` uses `HgMockLlmAdapter` only when `profile.kind === 'mock'`; under `dsh`, **`mockResponses` are ignored** — Director and Narrator run live despite `mockDirectorResponses` / `mockNarratorTurnResponses` being passed. Orchestrator order: **Director → Character → Narrator**; `NARRATOR_BY_FIXTURE` prose executes **after** Character commit and does not pre-seed decision context.

---

## Control comparisons

### D (PASS 3/3)

Same projection gap: scraping/panel absent from Character manifest. Live Director invented benign ambiance (rain-damp stone, radiator). **Observational inaction satisfies D adjudication** without fixture-specific hazard — explains D pass despite missing stimulus.

### B / C (PASS)

Multi-round B: round-0 seed + committed progression gives Director letter/restitution cues aligned with adjudication. C: betrayal facts arrive via seeded/mock + committed path. **Context-driven change does not require immediate protective action** — passes when Director-supplied cues align loosely with envelope.

### F vs D asymmetry

System does **not** show generalized inaction bias in D (legitimate restraint passes). F failures are **stimulus starvation + Director substitution**, not symmetric mishandling of action vs inaction when both stimuli are equally present.

---

## Storyteller / Librarian

| Layer | Classification | Evidence |
|-------|----------------|----------|
| Librarian `deterministic_fallback` | **Unlikely causal** | 14/16 runs including all F; C rep-2 passed without fallback; fallback did not remove hazard because hazard was never injected. |
| Storyteller orientation/assessment | **Unlikely causal** | All runs `storyteller.bound=true`; finalize accepted. |
| Storyteller progression opportunities on Director manifest | **Contributory** | Opening-scene opportunities emphasize environmental/micro-behavior beats (same pattern on F and D); may reinforce Director novelty over fixture hazard, but **cannot substitute for missing opening projection**. |

---

## Semantic evaluator

Dimensions: `R02b`, `R11`, `R12`, `R14`, `R15` only (`character-semantic-evaluation.mjs`). **No action-avoidance / duty-response dimension.**

All F reps: evaluator `overall_result: pass`, findings `[]`. Failure is **not** evaluator-rejected; even with hazard present, current evaluator might not catch omission unless mapped to an existing dimension.

---

## Provider adherence

| Criterion | Assessment |
|-----------|------------|
| Structurally valid JSON move | Yes (all committed) |
| Reasoning cites supplied cues | Yes — cites Director `environment_event` and “no committed events” |
| Omits fixture hazard | Yes — because hazard not in manifest |
| Classification | **Possible provider contribution** for invented scene details, but **not primary**; dominant miss is **upstream projection + Director substitution** |

---

## Fixture / adjudication challenge (H5)

| Question | Result |
|----------|--------|
| Was action mandatory for fidelity **given fixture truth**? | **Yes** — warn/secure/help envelope is broad; stalling/avoidance unsupported. |
| Multiple faithful responses? | **Yes** — warning, repositioning, alarm, etc. |
| Over-adjudication? | **No** for fixture-intended test. **Caveat:** adjudication used fixture truth while **run stimulus diverged**; this is correct for #136 acceptance (stimulus should have been authoritative), not a reason to weaken F criteria. |

---

## Attribution matrix

| Hypothesis | Rep 1 | Rep 2 | Rep 3 | Aggregate |
|------------|-------|-------|-------|-----------|
| H1 invariant salience/underspecification | not supported | not supported | not supported | **not supported** (invariant never received hazard) |
| H2 context/projection failure | **supported** | **supported** | **supported** | **supported** |
| H3 provider inference miss | partially supported | partially supported | partially supported | **partially supported** (faithful to wrong cues) |
| H4 cognition-layer dilution | partially supported | partially supported | partially supported | **partially supported** (live Director + ST opportunities) |
| H5 fixture/adjudication problem | not supported | not supported | not supported | **not supported** |
| H6 mixed | supported | supported | supported | **supported** |

**Primary root cause:** H2 (+ H6).  
**Secondary:** H4 (Director substitution), H3 (downstream fidelity to wrong stimulus), evaluator gap.

**Rejected as primary:** H1 alone, H5.

**#136-attributable:** **Yes** — decision-relevance projection for Character inference contract.

---

## Smallest coherent remediation boundary

**Class P8 (combined bounded), led by P3:**

1. **P3 — Character/Director decision-relevance projection (production, #136 scope)**  
   Project authored opening / session bootstrap stimulus into authoritative Character (and opening Director) context when no superseding committed public events exist. Owner: Domain Host (`continuity_context_projector.py`, `character_context_projector.py`).

2. **P5 — Tier-2 harness stimulus binding (validation tooling)**  
   Ensure live G4+ campaigns cannot silently drop fixture `scene_stimulus` when `scripted_*` flags are set: either inject fixture facts into authoritative layer pre-Director, or document that live mode requires projection fix before F is testable. Owner: `issue136-tier2-campaign.mjs` + Domain projection.

3. **P4 — Semantic evaluator (optional, bounded)**  
   Only after projection fix: consider whether action-avoidance against **projected** authoritative hazard belongs in evaluator dimensions — without duplicating rubric into generation prompt.

**Explicitly not proposed:** blanket “always act”, anti-inaction rules breaking D, trait expansion, Storyteller mandate, parser weakening, DSH domain ownership.

---

## Preferred remediation proposal (detail)

| # | Item | Proposal |
|---|------|----------|
| 1 | Failure mechanism | Opening/fixture hazard not in Character manifest; live Director invents alternate `environment_event`. |
| 2 | #136 scope | Inference-contract decision-relevance projection. |
| 3 | Owner | Domain Host projection layer; harness coordination for Tier-2. |
| 4 | Conceptual change | At opening / zero committed events, surface `opening_description` (or equivalent authored bootstrap facts) as authoritative scene context for Character and Director. |
| 5 | Model-facing text | Yes — bounded authoritative opening block in manifest (not new behavioral prose). |
| 6 | Deterministic code | Yes — projection policy + tests. |
| 7 | Evaluator | Deferred optional P4; not first-line fix. |
| 8 | Expected F effect | Hazard visible at decision → invariant can apply → protective moves become reachable. |
| 9 | D regression risk | **Low** if projection is faithful to authored opening only; D opening text supports inaction. |
| 10 | A/B/C/E regression | **Low–medium** — must not over-inject stale opening after committed progression supersedes. |
| 11 | Token cost | Small (+1 bounded opening block at early turns). |
| 12 | Auditability | Improves traceability (opening visible in manifest). |
| 13 | Deterministic validation | Projection unit tests; manifest snapshot tests for F/D fixtures. |
| 14 | Minimal live revalidation | F×3 live slice after deterministic pass. |
| 15 | Full Tier-2 rerun | After F slice + D regression slice + Governance review. |

### Alternatives rejected

| Alt | Why rejected |
|-----|----------------|
| P1 adjudication-only | Misattributes failure; stimulus should have been authoritative. |
| P2 invariant text alone | Hazard absent; more prose cannot fix missing facts. |
| P7 provider-only | Wrong stimulus explains outputs; provider change without projection retests nothing. |
| P6 separate subsystem issue | No independent defect; same projection path affects F and (latently) D packaging. |

---

## Staged validation proposal (not executed)

1. **Deterministic:** pytest for opening projection into Character/Director manifests at turn 0; regression that progression supersedes opening after commits.
2. **Focused F slice:** `136-T2-F-ACTION-REQUIRED` ×3 live — verify hazard terms in Character manifest and manual adjudication.
3. **D regression slice:** `136-T2-D-INACTION` ×2 live — confirm legitimate inaction preserved.
4. **Governance review** before broader campaign.
5. **Full Tier-2 rerun** only if F+D slices pass.

**Minimum live reruns proposed:** 5 (F×3 + D×2).  
**Eventual full campaign rerun:** **Recommended** after bounded fixes and Governance approval.

---

## Issue-splitting

**Remain within #136.** Failure is decision-relevance projection for Character inference contract, not a separate subsystem with independent prioritization.

---

## Confirmations

- No production remediation performed in this step.  
- No fresh paid/live inference performed in this step.  
- #136 remains OPEN / implemented; PR #137 unmerged.  
- #144 and #146 remain CLOSED.  
- No new Issue created.

---

## Full-consensus step 3 — Authority-semantics challenge (2026-09-07)

Governance challenged whether prior **P3** (project `opening.text` into authoritative Character/Director context) conflates fixture expectation with production authority. This section records the refinement.

### Authority sources consulted

| Source | Finding |
|--------|---------|
| `docs/architecture.md` § Scene-start spine | **Persistent premise vs opener:** `scene_premise` → authoritative `scene_setup` lane; `opening_description` → `rp_history` / `recent_scene_transcript` — **must not substitute for premise in `scene_setup`**. |
| `v2/tests/test_issue_78_scene_premise_projection.py` | Tests enforce premise-in-`scene_context`, opener-in-`recent_scene_transcript` only when opening PVR attached; cast-only empty premise → **no `scene_setup`**. |
| `v2/domain_api/session_setup.py` | Custom `opening.text` → `opening_description` + `rp_history` opening entry; `scene_premise` only from `scene_setup.premise` (template path). |
| `v2/domain_api/continuity_context_projector.py` | `project_scene_setup` reads `scene_state.scene_premise` only. |
| `v2/domain_api/session_history.py` + `perceptual_visibility_projection.py` | Opening without PVR → `invalid_excluded`, **no Character transcript content**. |
| `v2/rp_runtime/src/scenario-harness/issue136-tier2-campaign.mjs` | `scene_stimulus` → `opening.text` only; `committed_facts` → forensic record only (not continuity). |
| `issue136-fixture-truth.mjs` | `committed_facts` / envelopes are adjudicator-only; not injected into session. |

### Phase 1 answers (A–E)

| Q | Answer |
|---|--------|
| **A. Is `opening.text` authoritative scenario truth?** | **No.** Presentation/bootstrap text; reaches Character via perception-filtered transcript when PVR exists. |
| **B. Is `opening_description` authoritative scenario truth?** | **No.** Same as opener; stored on `scene_state` for opening generation context, not `scene_setup`. |
| **C. Is `scene_stimulus` a production field?** | **No.** Validation-only key in `issue136_tier2_truth_v1`; harness maps it to `opening.text`. |
| **D. What owns authoritative turn-zero scene facts?** | **`scene_state.scene_premise`** (via template `scene_setup.premise`) projected through `scene_setup`; plus **committed `PublicEvent` progression** after turns; optional **scene template `initial_facts`** → scene grounding. |
| **E. What owns visible environmental facts at turn zero?** | **Perception path:** opening prose + `attach_opening_perceptual_visibility` → `recent_scene_transcript` (derived). **Persistent setup:** `scene_premise`. **Advisory (not authoritative truth):** Director `environment_event` in `director_context`. |

Architecture **confirms** Governance's premise/opener distinction; prior P3 proposal **conflicts** with it.

### F fixture construction trace

| Stage | Bracket hazard |
|-------|----------------|
| Truth `committed_facts` | PRESENT (adjudicator-only) |
| Truth `scene_stimulus` | PRESENT (validation) |
| `buildSessionCreateBody` | TRANSFORMED → `opening.text` only |
| `scene_premise` / `scene_setup` | **ABSENT** (no template) |
| `rp_history` opening entry | PRESENT (raw prose) |
| Opening PVR attachment | **ABSENT** |
| Character `recent_scene_transcript` | **DROPPED** (no PVR → excluded) |
| Character `scene_setup` / premise in `scene-context` | **ABSENT** |
| Continuity `PublicEvent` at bootstrap | **ABSENT** |
| Live Director `environment_event` | **TRANSFORMED** → unrelated cue (silver key / bindery / library) |
| Character manifest hazard terms | **ABSENT** |

**Hazard drop point (primary):** harness maps required truth to **non-authoritative opener layer without PVR**, and never maps `committed_facts` into continuity. **Secondary drop:** live Director substitutes unrelated `environment_event`.

**F classification: F5 (mixed)** — primarily **F2** (wrong authority layer) + **F3** (harness failed to initialize canonical state). Not F1 (production did not omit an authoritative fact it was given).

### D fixture trace

Same harness path: `scene_stimulus` → `opening.text` without PVR; scraping/panel absent from Character manifest. Live Director invented benign ambiance. **D classification: D2** — fixture condition never participated; generic observational inaction accidentally satisfied envelope.

### A / B / C / E validity (summary)

| Fixture | Validity | Reason |
|---------|----------|--------|
| **A** | **VALID** | Stable characterization does not require specific opening hazard; adjudication is trait-bound, not stimulus-bound. |
| **B** | **PARTIALLY VALID** | Round-0 seeded Jon move commits authoritative restitution; round-1 live benefits from committed progression, not opener. |
| **C** | **PARTIALLY VALID** | Same seeded-commit pattern for betrayal facts. |
| **E** | **VALID** | Entitlement tested via deterministic forbidden-leak detection and multi-turn structure. |

### Production counterfactual (hazard encoded correctly)

| Encoding | Character projection |
|----------|---------------------|
| **`scene_premise` via scene template / `scene_setup`** | **PRESENT** — `project_scene_setup` → `scene_context` |
| **Opening + PVR (`observable_scene`, Mara-eligible)** | **PARTIAL** — `recent_scene_transcript` (derived, perception-filtered); legitimate per #78, not `scene_setup` |
| **`committed_facts` JSON only** | **ABSENT** — no production path |
| **`opening.text` without PVR** | **ABSENT** — matches G4 evidence |

### Prior P3 proposal verdict: **REJECT**

| Risk | Assessment |
|------|------------|
| Makes opener authoritative | **Yes** — violates `docs/architecture.md` |
| Violates premise authority | **Yes** |
| Opener/premise conflicts | **High** |
| Stale opener leak | **High** after commits |
| Perception bypass | **Yes** — would skip PVR |
| Necessary if fixture encoded correctly | **No** |

**REVISE toward R1/R2:** encode fixture stimuli in `scene_premise` (template) **or** opening + PVR; do not elevate opener to `scene_setup`.

### Revised primary root cause

**Validation fixture/harness authority-encoding defect (F2/F3)**, with **contributory live Director substitution** in G4 runs. **Not** a demonstrated production `scene_setup` projector defect.

### Revised remediation: **R5 (mixed bounded)** — validation-first

1. **R1/R2 (primary):** Issue136 harness initializes canonical turn-zero facts per fixture (minimal scene templates with `premise`, or `attach_opening_perceptual_visibility` for hazard prose, or seeded environment `PublicEvent` if harness gains API).
2. **No production P3** unless a separate governed need for turn-zero authoritative facts outside template/PVR/commit paths is identified.
3. **Semantic evaluator action-avoidance:** **FOLLOW-ON WITHIN #136** only after valid fixture encoding; not driven by malformed F QA passes.

### G4 campaign validity reassessment

| Family | Classification |
|--------|----------------|
| A | VALID |
| B | PARTIALLY VALID |
| C | PARTIALLY VALID |
| D | PARTIALLY VALID (D2 — not stimulus-faithful inaction) |
| E | VALID |
| **F** | **INVALID** as production semantic failure |
| Sentinel | VALID / UNAFFECTED |

**F 0/3 must not be read as production action-avoidance defect** until fixtures encode hazard in authoritative/perceptible paths and campaign re-runs.

### Revised minimum rerun (after harness fix)

1. Deterministic harness projection tests (F/D stimulus visible in manifest).
2. **F ×3** + **D ×2** live slice.
3. Governance review before full Tier-2 rerun.

---

## Full-consensus step 5 — F/D authoritative fixture encoding (2026-09-07)

Governance authorized validation-harness correction only (no production changes).

### Implementation

| Area | Change |
|------|--------|
| Module | `v2/rp_runtime/src/scenario-harness/issue136-fixture-bootstrap.mjs` |
| Campaign | `issue136-tier2-campaign.mjs` — `attachIssue136TurnZeroPerception` after session create |
| Live slice | `issue136-character-live-slice.mjs` — same bootstrap |
| Truth | `136-t2-f-action-required.json`, `136-t2-d-inaction.json` — `turn_zero_perception: true` |
| Tests | `tests/issue136-fd-perception-bootstrap.test.mjs` |

### Encoding path (F/D)

```text
opening prose → session create → PVR (observable_scene, public)
→ recent_scene_transcript → Character manifest
```

Not promoted to `scene_setup` / `scene_premise`.

### Deterministic gate results

| Gate | Result |
|------|--------|
| F hazard in `recent_scene_transcript` | PASS |
| D condition in `recent_scene_transcript` | PASS |
| No unauthorized `scene_setup` | PASS |
| Entitlement negative control | PASS |
| Director advisory + PVR coexist | PASS |
| Campaign mock smoke | PASS |

Historical G4 evidence at `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/` preserved; prior F/D semantic claims remain invalid until live rerun.
